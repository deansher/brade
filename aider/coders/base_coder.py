#!/usr/bin/env python

import base64
import hashlib
import json
import locale
import logging
import math
import os
import platform
import re
import sys
import threading
import time
import traceback
from collections import defaultdict
from datetime import datetime
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import ClassVar

from aider.brade_prompts import (
    ElementLocation,
    PromptElementPlacement,
    PromptElementPosition,
)

from langfuse.decorators import langfuse_context, observe

from aider import __version__, models, urls, utils
from aider.brade_prompts import format_brade_messages
from aider.coders.base_prompts import CoderPrompts
from aider.commands import Commands
from aider.history import ChatSummary
from aider.io import ConfirmGroup, InputOutput
from aider.linter import Linter
from aider.llm import litellm
from aider.repo import ANY_GIT_ERROR, GitRepo
from aider.repomap import RepoMap
from aider.run_cmd import run_cmd
from aider.sendchat import RETRY_TIMEOUT, retry_exceptions, send_completion
from aider.utils import format_content, format_tokens, is_image_file

from ..dump import dump  # noqa: F401

logger = logging.getLogger(__name__)


class MissingAPIKeyError(ValueError):
    pass


class FinishReasonLength(Exception):
    pass


class EditBlockError(Exception):
    def __init__(self, markdown_message: str):
        super().__init__(markdown_message)
        self.markdown_message = markdown_message


def wrap_fence(name):
    return f"<{name}>", f"</{name}>"


all_fences = [
    ("``" + "`", "``" + "`"),
    wrap_fence("source"),
    wrap_fence("code"),
    wrap_fence("pre"),
    wrap_fence("codeblock"),
    wrap_fence("sourcecode"),
]


class Coder:
    """Core class that manages the interaction between the human user, LLM, and codebase.

    The Coder class orchestrates the entire chat-based code editing workflow:
    - Manages chat history and context
    - Handles file content and git repository state
    - Processes LLM responses and applies code edits
    - Coordinates commits, linting, and testing
    - Provides command processing and shell integration

    Message Lifecycle:
        cur_messages holds the messages in the current exchange, which starts with
        a user message and includes any assistant responses up until either:

        1. Message processing fails
        2. Message processing succeeds and generates file edits
        3. Message processing succeeds without file edits

        In cases 2-3, cur_messages are moved to done_messages and processing of that
        exchange is complete. In case 1, cur_messages remains in place so the exchange
        can be retried or reflected upon. The separation between cur_messages and
        done_messages is crucial for proper handling of edits, commits, and error recovery.

    The class maintains important invariants around file state and git commits:
    - Files must be explicitly added to the chat before editing
    - Auto-commits are made after successful edits
    - Dirty files are committed before edits if configured
    - Read-only files are never modified

    Key collaborators:
    - InputOutput: Handles all user interaction
    - GitRepo: Manages git repository state
    - RepoMap: Provides repository content summaries
    - Commands: Processes user commands
    - ChatSummary: Manages chat history size
    """

    gpt_prompts: ClassVar[CoderPrompts | None]
    edit_format: ClassVar[str | None]
    abs_fnames = None
    abs_read_only_fnames = None
    repo = None
    last_aider_commit_hash = None
    aider_edited_files = None
    last_asked_for_commit_time = 0
    repo_map = None
    functions = None
    num_exhausted_context_windows = 0
    num_malformed_responses = 0
    last_keyboard_interrupt = None
    num_reflections = 0
    max_reflections = 3
    edit_format = None
    # Most coders produce code edits that must be auto-applied
    produces_code_edits = True
    yield_stream = False
    temperature = 0
    auto_lint = True
    auto_test = False
    test_cmd = None
    lint_outcome = None
    test_outcome = None
    multi_response_content = ""
    partial_response_content = ""
    commit_before_message = []
    message_cost = 0.0
    message_tokens_sent = 0
    message_tokens_received = 0
    add_cache_headers = False
    cache_warming_thread = None
    num_cache_warming_pings = 0
    suggest_shell_commands = True
    ignore_mentions = None
    chat_language = None
    parent_coder = None

    @classmethod
    def create(
        self,
        main_model=None,
        edit_format=None,
        io=None,
        from_coder=None,
        summarize_from_coder=True,
        **kwargs,
    ):
        import aider.coders as coders

        if not main_model:
            if from_coder:
                main_model = from_coder.main_model
            else:
                main_model = models.ModelConfig(models.DEFAULT_MODEL_NAME)

        if edit_format == "code":
            edit_format = None
        if edit_format is None:
            if from_coder:
                edit_format = from_coder.edit_format
            else:
                edit_format = main_model.edit_format

        if not io and from_coder:
            io = from_coder.io

        if from_coder:
            use_kwargs = dict(from_coder.original_kwargs)  # copy orig kwargs

            # Shallow-copy from_coder's done_messages in case the list is mutated.
            use_done_messages = list(from_coder.done_messages)

            # If the edit format changes, we can't leave old ASSISTANT
            # messages in the chat history. The old edit format will
            # confuse the new LLM. It will likely imitate it, disobeying
            # the system prompt.
            if (
                edit_format != from_coder.edit_format
                and from_coder.produces_code_edits
                and main_model.produces_code_edits
                and use_done_messages
                and summarize_from_coder
            ):
                use_done_messages = from_coder.summarizer.summarize_all(
                    use_done_messages
                )
                io.tool_output(
                    "Summarized old chat messages because we switched between incompatible edit"
                    " formats."
                )

            # Bring along context from the old Coder
            update = dict(
                fnames=list(from_coder.abs_fnames),
                read_only_fnames=list(from_coder.abs_read_only_fnames),
                done_messages=use_done_messages,
                cur_messages=from_coder.cur_messages,
                aider_commit_hashes=from_coder.aider_commit_hashes,
                commands=from_coder.commands.clone(),
                total_cost=from_coder.total_cost,
            )

            use_kwargs.update(update)  # override to complete the switch
            use_kwargs.update(kwargs)  # override passed kwargs

            kwargs = use_kwargs

        for coder in coders.__all__:
            if hasattr(coder, "edit_format") and coder.edit_format == edit_format:
                res = coder(main_model, io, **kwargs)
                res.original_kwargs = dict(kwargs)
                return res

        raise ValueError(f"Unknown edit format {edit_format}")

    def clone(self, **kwargs):
        new_coder = Coder.create(from_coder=self, **kwargs)
        new_coder.ignore_mentions = self.ignore_mentions
        return new_coder

    def get_announcements(self):
        lines = []
        lines.append(f"Brade v{__version__}")

        # ModelConfig
        main_model = self.main_model
        weak_model = main_model.weak_model

        if weak_model is not main_model:
            prefix = "Main model"
        else:
            prefix = "ModelConfig"

        output = f"{prefix}: {main_model.name} with {self.edit_format} edit format"
        if self.add_cache_headers or main_model.caches_by_default:
            output += ", prompt cache"
        if main_model.info.get("supports_assistant_prefill"):
            output += ", infinite output"
        output += f", {main_model.max_chat_history_tokens:,} history tokens"
        lines.append(output)

        if self.edit_format == "architect":
            output = (
                f"Editor model: {main_model.editor_model.name} with"
                f" {main_model.editor_edit_format} edit format"
            )
            output += f", {main_model.max_chat_history_tokens:,} history tokens"
            lines.append(output)

        if weak_model is not main_model:
            output = f"Weak model: {weak_model.name}"
            output += f", {main_model.max_chat_history_tokens:,} history tokens"
            lines.append(output)

        # Repo
        if self.repo:
            rel_repo_dir = self.repo.get_rel_repo_dir()
            num_files = len(self.repo.get_tracked_files())

            lines.append(f"Git repo: {rel_repo_dir} with {num_files:,} files")
            if num_files > 1000:
                lines.append(
                    "Warning: For large repos, consider using --subtree-only and .aiderignore"
                )
                lines.append(f"See: {urls.large_repos}")
        else:
            lines.append("Git repo: none")

        # Repo-map
        if self.repo_map:
            map_tokens = self.repo_map.max_map_tokens
            if map_tokens > 0:
                refresh = self.repo_map.refresh
                lines.append(f"Repo-map: using {map_tokens} tokens, {refresh} refresh")
                max_map_tokens = 2048
                if map_tokens > max_map_tokens:
                    lines.append(
                        f"Warning: map-tokens > {max_map_tokens} is not recommended as too much"
                        " irrelevant code can confuse LLMs."
                    )
            else:
                lines.append("Repo-map: disabled because map_tokens == 0")
        else:
            lines.append("Repo-map: disabled")

        # Files
        for fname in self.get_inchat_relative_files():
            lines.append(f"Added {fname} to the chat.")

        if self.done_messages:
            lines.append("Restored previous conversation history.")

        return lines

    def get_reasoning_level_modifier(self):
        if hasattr(self, "parent_coder") and self.parent_coder:
            return self.parent_coder.get_reasoning_level_modifier()
        return self.reasoning_level_modifier

    def __init__(
        self,
        main_model,
        io,
        repo=None,
        fnames=None,
        read_only_fnames=None,
        show_diffs=False,
        auto_commits=True,
        dirty_commits=True,
        dry_run=False,
        map_tokens=1024,
        verbose=False,
        stream=True,
        use_git=True,
        cur_messages=None,
        done_messages=None,
        restore_chat_history=False,
        auto_lint=True,
        auto_test=False,
        lint_cmds=None,
        test_cmd=None,
        aider_commit_hashes=None,
        map_mul_no_files=8,
        commands=None,
        summarizer=None,
        total_cost=0.0,
        map_refresh="auto",
        cache_prompts=False,
        num_cache_warming_pings=0,
        suggest_shell_commands=True,
        chat_language=None,
        parent_coder=None,
    ):
        self.chat_language = chat_language
        self.reasoning_level_modifier = 0
        self.parent_coder = parent_coder
        self.commit_before_message = []
        self.aider_commit_hashes = set()
        self.rejected_urls = set()
        self.abs_root_path_cache = {}
        self.ignore_mentions = set()

        self.suggest_shell_commands = suggest_shell_commands

        self.num_cache_warming_pings = num_cache_warming_pings

        if not fnames:
            fnames = []

        if io is None:
            io = InputOutput()

        if aider_commit_hashes:
            self.aider_commit_hashes = aider_commit_hashes
        else:
            self.aider_commit_hashes = set()

        self.chat_completion_call_hashes = []
        self.chat_completion_response_hashes = []
        self.need_commit_before_edits = set()

        self.total_cost = total_cost

        self.verbose = verbose
        self.abs_fnames = set()
        self.abs_read_only_fnames = set()

        if cur_messages:
            self.cur_messages = cur_messages
        else:
            self.cur_messages = []

        if done_messages:
            self.done_messages = done_messages
        else:
            self.done_messages = []

        self.io = io
        self.reasoning_effort_modifier = 0
        self.stream = stream

        self.shell_commands = []

        if not auto_commits:
            dirty_commits = False

        self.auto_commits = auto_commits
        self.dirty_commits = dirty_commits

        self.dry_run = dry_run
        self.pretty = self.io.pretty

        self.main_model = main_model

        if cache_prompts:
            self.add_cache_headers = self.main_model.cache_control

        self.show_diffs = show_diffs

        self.commands = commands or Commands(self.io, self)
        self.commands.coder = self

        self.repo = repo
        if use_git and self.repo is None:
            try:
                self.repo = GitRepo(
                    self.io,
                    fnames,
                    None,
                    models=main_model.commit_message_models(),
                )
            except FileNotFoundError:
                pass

        if self.repo:
            self.root = self.repo.root

        for fname in fnames:
            fname = Path(fname)
            if self.repo and self.repo.ignored_file(fname):
                self.io.tool_warning(f"Skipping {fname} that matches aiderignore spec.")
                continue

            if not fname.exists():
                if utils.touch_file(fname):
                    self.io.tool_output(f"Creating empty file {fname}")
                else:
                    self.io.tool_warning(f"Cannot create {fname}, skipping.")
                    continue

            if not fname.is_file():
                self.io.tool_warning(f"Skipping {fname} that is not a normal file.")
                continue

            fname = str(fname.resolve())

            self.abs_fnames.add(fname)
            self.check_added_files()

        if not self.repo:
            self.root = utils.find_common_root(self.abs_fnames)

        if read_only_fnames:
            self.abs_read_only_fnames = set()
            for fname in read_only_fnames:
                abs_fname = self.abs_root_path(fname)
                if os.path.exists(abs_fname):
                    self.abs_read_only_fnames.add(abs_fname)
                else:
                    self.io.tool_warning(
                        f"Error: Read-only file {fname} does not exist. Skipping."
                    )

        if map_tokens is None:
            use_repo_map = main_model.use_repo_map
            map_tokens = 1024
        else:
            use_repo_map = map_tokens > 0

        max_inp_tokens = self.main_model.info.get("max_input_tokens") or 0

        if use_repo_map and self.repo:
            self.repo_map = RepoMap(
                map_tokens,
                self.root,
                self.main_model,
                io,
                self.gpt_prompts.repo_content_prefix,
                self.verbose,
                max_inp_tokens,
                map_mul_no_files=map_mul_no_files,
                refresh=map_refresh,
            )

        self.summarizer = summarizer or ChatSummary(
            [self.main_model.weak_model, self.main_model],
            self.main_model.max_chat_history_tokens,
        )

        self.summarizer_thread = None
        self.summarized_done_messages = []

        if not self.done_messages and restore_chat_history:
            history_md = self.io.read_text(self.io.chat_history_file)
            if history_md:
                self.done_messages = utils.split_chat_history_markdown(history_md)
                self.summarize_start()

        # Linting and testing
        self.linter = Linter(root=self.root, encoding=io.encoding)
        self.auto_lint = auto_lint
        self.setup_lint_cmds(lint_cmds)
        self.lint_cmds = lint_cmds
        self.auto_test = auto_test
        self.test_cmd = test_cmd

        # validate the functions jsonschema
        if self.functions:
            from jsonschema import Draft7Validator

            for function in self.functions:
                Draft7Validator.check_schema(function)

            if self.verbose:
                self.io.tool_output("JSON Schema:")
                self.io.tool_output(json.dumps(self.functions, indent=4))

    def setup_lint_cmds(self, lint_cmds):
        if not lint_cmds:
            return
        for lang, cmd in lint_cmds.items():
            self.linter.set_linter(lang, cmd)

    def show_announcements(self):
        bold = True
        for line in self.get_announcements():
            self.io.tool_output(line, bold=bold)
            bold = False

    def add_rel_fname(self, rel_fname):
        self.abs_fnames.add(self.abs_root_path(rel_fname))
        self.check_added_files()

    def drop_rel_fname(self, fname):
        abs_fname = self.abs_root_path(fname)
        if abs_fname in self.abs_fnames:
            self.abs_fnames.remove(abs_fname)
            return True

    def abs_root_path(self, path):
        """Converts a path relative to the project root into an absolute filesystem path.

        This method ensures all path operations are anchored to the project's root directory
        rather than the current working directory. It maintains a cache of computed paths
        for performance.

        Args:
            path (str|Path): A path relative to the project root directory

        Returns:
            str: An absolute filesystem path anchored to the project root

        Raises:
            ValueError: If path is None
        """
        if path is None:
            logger.exception("abs_root_path received None path")
            raise ValueError("abs_root_path received None path")

        key = path
        if key in self.abs_root_path_cache:
            return self.abs_root_path_cache[key]

        res = Path(self.root) / path
        res = utils.safe_abs_path(res)
        self.abs_root_path_cache[key] = res
        return res

    fences = all_fences
    fence = fences[0]

    def show_pretty(self):
        if not self.pretty:
            return False

        # only show pretty output if fences are the normal triple-backtick
        if self.fence != self.fences[0]:
            return False

        return True

    def get_abs_fnames_content(self):
        """Yields tuples of absolute filenames and their content for files in the chat.

        This method iterates through files that have been added to the chat session
        and retrieves their content. It handles error cases by:
        - Removing files that can't be read from the chat
        - Warning the user about dropped files

        Returns:
            Generator: Yields tuples of (absolute_filename: str, content: str)
                      for files that were successfully read.
        """
        for fname in list(self.abs_fnames):
            content = self.io.read_text(fname)

            if content is None:
                relative_fname = self.get_rel_fname(fname)
                self.io.tool_warning(f"Dropping {relative_fname} from the chat.")
                self.abs_fnames.remove(fname)
            else:
                yield fname, content

    def choose_fence(self):
        all_content = ""
        for _fname, content in self.get_abs_fnames_content():
            all_content += content + "\n"
        for _fname in self.abs_read_only_fnames:
            content = self.io.read_text(_fname)
            if content is not None:
                all_content += content + "\n"

        lines = all_content.splitlines()
        good = False
        for fence_open, fence_close in self.fences:
            if any(
                line.startswith(fence_open) or line.startswith(fence_close)
                for line in lines
            ):
                continue
            good = True
            break

        if good:
            self.fence = (fence_open, fence_close)
        else:
            self.fence = self.fences[0]
            self.io.tool_warning(
                "Unable to find a fencing strategy! Falling back to:"
                f" {self.fence[0]}...{self.fence[1]}"
            )

        return

    def get_read_only_files_content(self):
        prompt = ""
        for fname in self.abs_read_only_fnames:
            content = self.io.read_text(fname)
            if content is not None and not is_image_file(fname):
                prompt += self._format_file_content(fname, content)
        return prompt

    def get_cur_message_text(self):
        text = ""
        for msg in self.cur_messages:
            text += msg["content"] + "\n"
        return text

    def get_ident_mentions(self, text):
        # Split the string on any character that is not alphanumeric
        # \W+ matches one or more non-word characters (equivalent to [^a-zA-Z0-9_]+)
        words = set(re.split(r"\W+", text))
        return words

    def get_ident_filename_matches(self, idents):
        all_fnames = defaultdict(set)
        for fname in self.get_all_relative_files():
            base = Path(fname).with_suffix("").name.lower()
            if len(base) >= 5:
                all_fnames[base].add(fname)

        matches = set()
        for ident in idents:
            if len(ident) < 5:
                continue
            matches.update(all_fnames[ident.lower()])

        return matches

    def get_repo_map(self, force_refresh=False):
        if not self.repo_map:
            return

        cur_msg_text = self.get_cur_message_text()
        mentioned_fnames = self.get_file_mentions(cur_msg_text)
        mentioned_idents = self.get_ident_mentions(cur_msg_text)

        mentioned_fnames.update(self.get_ident_filename_matches(mentioned_idents))

        all_abs_files = set(self.get_all_abs_files())
        repo_abs_read_only_fnames = set(self.abs_read_only_fnames) & all_abs_files
        chat_files = set(self.abs_fnames) | repo_abs_read_only_fnames
        other_files = all_abs_files - chat_files

        repo_content = self.repo_map.get_repo_map(
            chat_files,
            other_files,
            mentioned_fnames=mentioned_fnames,
            mentioned_idents=mentioned_idents,
            force_refresh=force_refresh,
        )

        # fall back to global repo map if files in chat are disjoint from rest of repo
        if not repo_content:
            repo_content = self.repo_map.get_repo_map(
                set(),
                all_abs_files,
                mentioned_fnames=mentioned_fnames,
                mentioned_idents=mentioned_idents,
            )

        # fall back to completely unhinted repo
        if not repo_content:
            repo_content = self.repo_map.get_repo_map(
                set(),
                all_abs_files,
            )

        return repo_content

    def get_repo_messages(self):
        repo_messages = []
        repo_content = self.get_repo_map()
        if repo_content:
            repo_messages += [
                dict(role="user", content=repo_content),
                dict(
                    role="assistant",
                    content="Ok, I won't try and edit those files without asking first.",
                ),
            ]
        return repo_messages

    def get_readonly_files_messages(self):
        readonly_messages = []
        read_only_content = self.get_read_only_files_content()
        if read_only_content:
            readonly_messages += [
                dict(
                    role="user",
                    content=self.gpt_prompts.read_only_files_prefix + read_only_content,
                ),
                dict(
                    role="assistant",
                    content="Ok, I will use these files as references.",
                ),
            ]
        return readonly_messages

    def run_stream(self, user_message):
        self.io.user_input(user_message)
        self.init_before_message()
        yield from self.send_message(user_message)

    def init_before_message(self):
        self.aider_edited_files = set()
        self.reflected_message = None
        self.num_reflections = 0
        self.lint_outcome = None
        self.test_outcome = None
        self.shell_commands = []

        if self.repo:
            self.commit_before_message.append(self.repo.get_head_commit_sha())

    def run(self, with_message=None, preproc=True):
        self.choose_fence()
        try:
            if with_message:
                self.io.user_input(with_message)
                self.run_one(with_message, preproc)
                return self.partial_response_content

            while True:
                try:
                    user_message = self.get_input()
                    self.run_one(user_message, preproc)
                    self.show_undo_hint()
                except KeyboardInterrupt:
                    self.keyboard_interrupt()
        except EOFError:
            return

    def get_input(self):
        inchat_files = self.get_inchat_relative_files()
        read_only_files = [
            self.get_rel_fname(fname) for fname in self.abs_read_only_fnames
        ]
        all_files = sorted(set(inchat_files + read_only_files))
        edit_format = (
            "" if self.edit_format == self.main_model.edit_format else self.edit_format
        )
        return self.io.get_input(
            self.root,
            all_files,
            self.get_addable_relative_files(),
            self.commands,
            self.abs_read_only_fnames,
            edit_format=edit_format,
            reasoning_level_modifier=self.reasoning_level_modifier,
        )

    def preproc_user_input(self, inp):
        if not inp:
            return

        if self.commands.is_command(inp):
            return self.commands.run(inp)

        self.check_for_file_mentions(inp)
        self.check_for_urls(inp)

        return inp

    @observe
    def run_one(self, user_message, preproc):
        langfuse_context.update_current_observation(
            name=self.__class__.__name__,
            input=user_message,
        )
        self.init_before_message()

        if preproc:
            prompt_message = self.preproc_user_input(user_message)
        else:
            prompt_message = user_message

        if prompt_message is None:
            return

        # Adjust reasoning level based on message prefix
        if prompt_message.startswith("+"):
            self.reasoning_level_modifier = 1
            self.io.tool_output(
                f"Reasoning level modifier set to {self.reasoning_level_modifier}"
            )
            prompt_message = prompt_message[1:].lstrip()
        elif prompt_message.startswith("-"):
            self.reasoning_level_modifier = -1
            self.io.tool_output(
                f"Reasoning level modifier set to {self.reasoning_level_modifier}"
            )
            prompt_message = prompt_message[1:].lstrip()
        elif prompt_message.startswith("="):
            self.reasoning_level_modifier = 0
            self.io.tool_output(
                f"Reasoning level modifier set to {self.reasoning_level_modifier}"
            )
            prompt_message = prompt_message[1:].lstrip()

        while prompt_message:
            self.reflected_message = None
            list(self.send_message(prompt_message))

            if not self.reflected_message:
                break

            if self.num_reflections >= self.max_reflections:
                self.io.tool_warning(
                    f"Only {self.max_reflections} reflections allowed, stopping."
                )
                return

            self.num_reflections += 1
            prompt_message = self.reflected_message
        langfuse_context.update_current_observation(
            output=self.partial_response_content
        )

    def check_for_urls(self, inp):
        url_pattern = re.compile(r"(https?://[^\s/$.?#].[^\s]*[^\s,.])")
        urls = list(set(url_pattern.findall(inp)))  # Use set to remove duplicates
        added_urls = []
        group = ConfirmGroup(urls)
        for url in urls:
            if url not in self.rejected_urls:
                if self.io.confirm_ask(
                    "Add URL to the chat?", subject=url, group=group, allow_never=True
                ):
                    inp += "\n\n"
                    inp += self.commands.cmd_web(url)
                    added_urls.append(url)
                else:
                    self.rejected_urls.add(url)

        return added_urls

    def keyboard_interrupt(self):
        now = time.time()

        thresh = 2  # seconds
        if self.last_keyboard_interrupt and now - self.last_keyboard_interrupt < thresh:
            self.io.tool_warning("\n\n^C KeyboardInterrupt")
            sys.exit()

        self.io.tool_warning("\n\n^C again to exit")

        self.last_keyboard_interrupt = now

    def summarize_start(self):
        if self.verbose:
            if self.summarizer.io is None:
                sumio_description = "None"
            elif self.summarizer.io is self.io:
                sumio_description = "same as Coder.io"
            else:
                sumio_description = "unique"
            self.io.tool_output(
                f"summarize_start: self.summarizer.io is {sumio_description}"
            )
        if not self.summarizer.too_big(self.done_messages):
            return

        self.summarize_end()

        if self.verbose:
            self.io.tool_output("Starting to summarize chat history.")

        self.summarizer_thread = threading.Thread(target=self.summarize_worker)
        self.summarizer_thread.start()

    def summarize_worker(self):
        try:
            self.summarized_done_messages = self.summarizer.summarize(
                self.done_messages
            )
        except ValueError as err:
            self.io.tool_warning(err.args[0])

        if self.verbose:
            self.io.tool_output("Finished summarizing chat history.")

    def summarize_end(self):
        if self.summarizer_thread is None:
            return

        self.summarizer_thread.join()
        self.summarizer_thread = None

        self.done_messages = self.summarized_done_messages
        self.summarized_done_messages = []

    def move_back_cur_messages(self, new_user_content):
        """Moves current messages to history and optionally adds a new exchange.

        This method manages the transition of messages from active conversation (cur_messages)
        to history (done_messages). It:
        1. Appends all current messages to the history
        2. Triggers history summarization if needed
        3. Optionally adds a new user message and "Understood" assistant response to done_messages.
        4. Clears cur_messages.

        This is commonly used after successful code edits to:
        - Preserve the edit conversation in history
        - Record that changes were applied
        - Start fresh for the next exchange

        Args:
            new_user_content: Optional message to add as a user message, paired with
                an "Understood" assistant response. Often used to record system
                actions like "Changes were committed".

        Note:
            The history (done_messages) may be summarized before the new messages are added,
            if it has grown too large, but the newly added messages will be preserved verbatim.
        """
        self.done_messages = self.done_messages + self.cur_messages
        self.summarize_start()

        # TODO check for impact on image messages
        if new_user_content:
            self.done_messages += [
                dict(role="user", content=new_user_content),
                dict(role="assistant", content="Understood."),
            ]
        self.cur_messages = []

    def get_user_language(self):
        if self.chat_language:
            return self.chat_language

        try:
            lang = locale.getlocale()[0]
            if lang:
                return lang  # Return the full language code, including country
        except Exception:
            pass

        for env_var in ["LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES"]:
            lang = os.environ.get(env_var)
            if lang:
                return lang.split(".")[
                    0
                ]  # Return language and country, but remove encoding if present

        return None

    def get_platform_info(self):
        platform_text = f"- Platform: {platform.platform()}\n"
        shell_var = "COMSPEC" if os.name == "nt" else "SHELL"
        shell_val = os.getenv(shell_var)
        platform_text += f"- Shell: {shell_var}={shell_val}\n"

        user_lang = self.get_user_language()
        if user_lang:
            platform_text += f"- Language: {user_lang}\n"

        dt = datetime.now().astimezone().strftime("%Y-%m-%d")
        platform_text += f"- Current date: {dt}\n"

        if self.repo:
            platform_text += "- The user is operating inside a git repository\n"

        if self.lint_cmds:
            if self.auto_lint:
                platform_text += (
                    "- The user's pre-commit runs these lint commands, don't suggest running"
                    " them:\n"
                )
            else:
                platform_text += "- The user prefers these lint commands:\n"
            for lang, cmd in self.lint_cmds.items():
                if lang is None:
                    platform_text += f"  - {cmd}\n"
                else:
                    platform_text += f"  - {lang}: {cmd}\n"

        if self.test_cmd:
            if self.auto_test:
                platform_text += "- The user's pre-commit runs this test command, don't suggest running them: "
            else:
                platform_text += "- The user prefers this test command: "
            platform_text += self.test_cmd + "\n"

        return platform_text

    def format_prompt(self, prompt):
        """Formats a prompt template by substituting dynamic content such as fence and platform."""
        lazy_prompt = self.gpt_prompts.lazy_prompt if self.main_model.lazy else ""
        platform_text = self.get_platform_info()

        if self.suggest_shell_commands:
            shell_cmd_prompt = self.gpt_prompts.shell_cmd_prompt.format(
                platform=platform_text
            )
            shell_cmd_reminder = self.gpt_prompts.shell_cmd_reminder.format(
                platform=platform_text
            )
        else:
            shell_cmd_prompt = self.gpt_prompts.no_shell_cmd_prompt.format(
                platform=platform_text
            )
            shell_cmd_reminder = self.gpt_prompts.no_shell_cmd_reminder.format(
                platform=platform_text
            )

        prompt = prompt.format(
            name="Brade",  # Add name parameter for prompt templates
            fence=self.fence,
            lazy_prompt=lazy_prompt,
            platform=platform_text,
            shell_cmd_prompt=shell_cmd_prompt,
            shell_cmd_reminder=shell_cmd_reminder,
        )
        return prompt

    def warm_cache(self, chunks):
        if not self.add_cache_headers:
            return
        if not self.num_cache_warming_pings:
            return

        delay = 5 * 60 - 5
        self.next_cache_warm = time.time() + delay
        self.warming_pings_left = self.num_cache_warming_pings
        self.cache_warming_chunks = chunks

        if self.cache_warming_thread:
            return

        def warm_cache_worker():
            while True:
                time.sleep(1)
                if self.warming_pings_left <= 0:
                    continue
                now = time.time()
                if now < self.next_cache_warm:
                    continue

                self.warming_pings_left -= 1
                self.next_cache_warm = time.time() + delay

                kwargs = dict(self.main_model.extra_params) or dict()
                kwargs["max_tokens"] = 1

                try:
                    completion = litellm.completion(
                        model=self.main_model.name,
                        messages=self.cache_warming_chunks.cacheable_messages(),
                        stream=False,
                        **kwargs,
                    )
                except Exception as err:
                    self.io.tool_warning(f"Cache warming error: {str(err)}")
                    continue

                cache_hit_tokens = getattr(
                    completion.usage, "prompt_cache_hit_tokens", 0
                ) or getattr(completion.usage, "cache_read_input_tokens", 0)

                if self.verbose:
                    self.io.tool_output(
                        f"Warmed {format_tokens(cache_hit_tokens)} cached tokens."
                    )

        self.cache_warming_thread = threading.Timer(0, warm_cache_worker)
        self.cache_warming_thread.daemon = True
        self.cache_warming_thread.start()

        return chunks

    def process_image(self, image_path):
        """Converts an image file to base64 encoding with proper MIME type for chat inclusion"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def get_image_files_content(self):
        """Returns list of (filename, base64content) tuples for image files in chat"""
        image_files = []
        for fname in list(self.abs_fnames):
            if is_image_file(fname):
                rel_fname = self.get_rel_fname(fname)
                base64content = self.process_image(fname)
                image_files.append((rel_fname, base64content))
        return image_files

    def _format_brade_messages(self):
        """Formats messages using Brade's XML-based structure.

        This method transforms the chat context into Brade's format while maintaining
        existing caching behavior. It:
        1. Gets all content via existing ChatChunks mechanism
        2. Transforms file content into FileContent tuples
        3. Organizes everything into the new XML structure
        4. Preserves caching behavior by using warm_cache()

        Returns:
            list[ChatMessage]: The formatted sequence of messages
        """
        # Transform file content into FileContent tuples
        readonly_text_files = []
        for fname in self.abs_read_only_fnames:
            content = self.io.read_text(fname)
            if content is not None and not is_image_file(fname):
                readonly_text_files.append((self.get_rel_fname(fname), content))

        editable_text_files = []
        for fname, content in self.get_abs_fnames_content():
            if not is_image_file(fname):
                editable_text_files.append((self.get_rel_fname(fname), content))

        image_files = (
            self.get_image_files_content() if self.main_model.accepts_images else None
        )

        # Get repository map if available
        repo_map = self.get_repo_map()

        # Get platform info
        platform_info = self.get_platform_info()

        # Get task instructions and reminder from prompts
        task_instructions = ""
        task_instructions_reminder = None
        prompts = getattr(self, "gpt_prompts", None)
        if prompts and prompts.task_instructions:
            task_instructions = self.format_prompt(prompts.task_instructions)
        if prompts and prompts.system_reminder:
            task_instructions_reminder = self.format_prompt(prompts.system_reminder)

        # Get task examples from prompts
        task_examples = None
        if prompts and prompts.example_messages:
            task_examples = [
                dict(
                    role=msg["role"],
                    content=self.format_prompt(msg["content"]),
                )
                for msg in self.gpt_prompts.example_messages
            ]

        return format_brade_messages(
            system_prompt=self.format_prompt(
                prompts.main_system_core if prompts else ""
            ),
            task_instructions=task_instructions,
            done_messages=self.done_messages,
            cur_messages=self.cur_messages,
            repo_map=repo_map,
            readonly_text_files=readonly_text_files,
            editable_text_files=editable_text_files,
            image_files=image_files,
            platform_info=platform_info,
            task_examples=task_examples,
            task_instructions_reminder=task_instructions_reminder,
            context_location=ElementLocation(
                placement=PromptElementPlacement.SYSTEM_MESSAGE,
                position=PromptElementPosition.APPEND,
            ),
            task_instructions_location=ElementLocation(
                placement=PromptElementPlacement.FINAL_USER_MESSAGE,
                position=PromptElementPosition.APPEND,
            ),
            task_examples_location=ElementLocation(
                placement=PromptElementPlacement.FINAL_USER_MESSAGE,
                position=PromptElementPosition.APPEND,
            ),
            task_instructions_reminder_location=ElementLocation(
                placement=PromptElementPlacement.SYSTEM_MESSAGE,
                position=PromptElementPosition.PREPEND,
            ),
        )

    @observe
    def send_message(self, new_user_message):
        """
        Send a completion request to the language model and handle the response.

        This function handles Langfuse integration and parameter validation for litellm.completion().
        It is an internal implementation detail and should not be called directly.

        Args:
            model_config (ModelConfig): The model configuration instance to use.
            messages (list): A list of message dictionaries to send to the model.
            functions (list): A list of function definitions that the model can use.
            stream (bool): Whether to stream the response or not.
            temperature (float, optional): The sampling temperature to use. Only used if the model
                supports temperature. Defaults to None.
            extra_params (dict, optional): Additional parameters to pass to the model.
                This includes:
                - OpenAI-compatible parameters like max_tokens, top_p, etc.
                - Provider-specific parameters passed through to the provider
            provider_params (dict, optional): Provider-specific parameters to pass through.
            extra_headers (dict, optional): Provider-specific headers to pass through.
            purpose (str, optional): The purpose label for this completion request for Langfuse tracing.
                Defaults to "(unlabeled)".

        Returns:
            litellm.ModelResponse: The model's response object. The structure depends on stream mode:
                When stream=False:
                    - choices[0].message.content: The complete response text
                    - choices[0].tool_calls[0].function: Function call details if tools were used
                    - usage.prompt_tokens: Number of input tokens
                    - usage.completion_tokens: Number of output tokens
                    - usage.total_cost: Total cost in USD if available
                    - usage.prompt_cost: Input cost in USD if available
                    - usage.completion_cost: Output cost in USD if available
                When stream=True:
                    Returns an iterator yielding chunks, where each chunk has:
                    - choices[0].delta.content: The next piece of response text
                    - choices[0].delta.tool_calls[0].function: Partial function call details
                    - usage: Only available in final chunk if stream_options.include_usage=True

        Raises:
            SendCompletionError: If the API returns a non-200 status code
            InvalidResponseError: If the response is missing required fields or empty
            litellm.exceptions.RateLimitError: If rate limit is exceeded
            litellm.exceptions.APIError: For various API-level errors
            litellm.exceptions.Timeout: If the request times out
            litellm.exceptions.APIConnectionError: For network connectivity issues
            litellm.exceptions.ServiceUnavailableError: If the service is unavailable
            litellm.exceptions.InternalServerError: For server-side errors
            TypeError: If model_config is not a ModelConfig instance
        """
        user_message_prefix = new_user_message[:15] + " ..."
        langfuse_context.update_current_observation(name=f"{user_message_prefix}")
        self.cur_messages += [
            dict(role="user", content=new_user_message),
        ]

        prompt_messages = self._format_brade_messages()

        if self.verbose:
            utils.show_messages(prompt_messages, functions=self.functions)

        self.multi_response_content = ""
        if self.show_pretty() and self.stream:
            self.mdstream = self.io.get_assistant_mdstream()
        else:
            self.mdstream = None

        retry_delay = 0.125

        self.usage_report = None
        exhausted = False
        interrupted = False
        try:
            while True:
                try:
                    yield from self.send(
                        prompt_messages,
                        functions=self.functions,
                        purpose="new user message",
                    )
                    break
                except retry_exceptions() as err:
                    self.io.tool_warning(str(err))
                    retry_delay *= 2
                    if retry_delay > RETRY_TIMEOUT:
                        break
                    self.io.tool_output(f"Retrying in {retry_delay:.1f} seconds...")
                    time.sleep(retry_delay)
                    continue
                except KeyboardInterrupt:
                    interrupted = True
                    break
                except litellm.ContextWindowExceededError:
                    # The input is overflowing the context window!
                    exhausted = True
                    break
                except litellm.exceptions.BadRequestError as br_err:
                    self.io.tool_error(f"BadRequestError: {br_err}")
                    return
                except FinishReasonLength:
                    # We hit the output limit!
                    if not self.main_model.info.get("supports_assistant_prefill"):
                        exhausted = True
                        break

                    self.multi_response_content = self.get_multi_response_content()

                    if prompt_messages[-1]["role"] == "assistant":
                        prompt_messages[-1]["content"] = self.multi_response_content
                    else:
                        prompt_messages.append(
                            dict(
                                role="assistant",
                                content=self.multi_response_content,
                                prefix=True,
                            )
                        )
                except Exception as err:
                    self.io.tool_error(f"Unexpected error: {err}")
                    lines = traceback.format_exception(
                        type(err), err, err.__traceback__
                    )
                    self.io.tool_error("".join(lines))
                    return
        finally:
            if self.mdstream:
                self.live_incremental_response(True)
                self.mdstream = None

            self.partial_response_content = self.get_multi_response_content(True)
            langfuse_context.update_current_observation(
                output=self.partial_response_content
            )
            self.multi_response_content = ""

        self.io.tool_output()

        self.compute_usage()

        if exhausted:
            self.show_exhausted_error()
            self.num_exhausted_context_windows += 1
            return

        if self.partial_response_function_call:
            args = self.parse_partial_args()
            if args:
                content = args.get("explanation") or ""
            else:
                content = ""
        elif self.partial_response_content:
            content = self.partial_response_content
        else:
            content = ""

        try:
            self.reply_completed()
        except KeyboardInterrupt:
            interrupted = True

        if interrupted:
            content += "\n^C KeyboardInterrupt"
            self.cur_messages += [dict(role="assistant", content=content)]
            return

        edited = self.apply_updates()

        self.update_cur_messages()

        if edited:
            self.aider_edited_files.update(edited)
            saved_message = self.auto_commit(edited)

            if not saved_message and hasattr(
                self.gpt_prompts, "files_content_gpt_edits_no_repo"
            ):
                saved_message = self.gpt_prompts.files_content_gpt_edits_no_repo

            self.move_back_cur_messages(saved_message)

        if self.reflected_message:
            return

        if edited and self.auto_lint:
            lint_errors = self.lint_edited(edited)
            self.auto_commit(edited, context="Ran the linter")
            self.lint_outcome = not lint_errors
            if lint_errors:
                ok = self.io.confirm_ask("Attempt to fix lint errors?")
                if ok:
                    self.reflected_message = lint_errors
                    self.update_cur_messages()
                    return

        shared_output = self.run_shell_commands()
        if shared_output:
            self.cur_messages += [
                dict(role="user", content=shared_output),
                dict(role="assistant", content="Ok"),
            ]

        if edited and self.auto_test:
            test_errors = self.commands.cmd_test(self.test_cmd)
            self.test_outcome = not test_errors
            if test_errors:
                ok = self.io.confirm_ask("Attempt to fix test errors?")
                if ok:
                    self.reflected_message = test_errors
                    self.update_cur_messages()
                    return

    def reply_completed(self):
        """Post-process the LLM's response if needed.

        This method is called after the LLM's response is fully received. It is responsible for
        performing any follow-up logic that may be specific to the Coder subclass. Examples include:
        1. Processing the response content in self.partial_response_content
        2. Extracting and applying any code edits
        3. Handling any function calls
        4. Managing git commits and other side effects
        5. Updating conversation history

        The base implementation does nothing. Subclasses override this to implement their
        specific response handling logic.

        Note: The LLM's response has already been added to cur_messages by base_coder.py
        before this is called.
        """
        pass

    def show_exhausted_error(self):
        output_tokens = 0
        if self.partial_response_content:
            output_tokens = self.main_model.token_count(self.partial_response_content)
        max_output_tokens = self.main_model.info.get("max_output_tokens") or 0

        input_tokens = self.main_model.token_count(self._format_brade_messages())
        max_input_tokens = self.main_model.info.get("max_input_tokens") or 0

        total_tokens = input_tokens + output_tokens

        fudge = 0.7

        out_err = ""
        if output_tokens >= max_output_tokens * fudge:
            out_err = " -- possibly exceeded output limit!"

        inp_err = ""
        if input_tokens >= max_input_tokens * fudge:
            inp_err = " -- possibly exhausted context window!"

        tot_err = ""
        if total_tokens >= max_input_tokens * fudge:
            tot_err = " -- possibly exhausted context window!"

        res = ["", ""]
        res.append(f"ModelConfig {self.main_model.name} has hit a token limit!")
        res.append("Token counts below are approximate.")
        res.append("")
        res.append(f"Input tokens: ~{input_tokens:,} of {max_input_tokens:,}{inp_err}")
        res.append(
            f"Output tokens: ~{output_tokens:,} of {max_output_tokens:,}{out_err}"
        )
        res.append(f"Total tokens: ~{total_tokens:,} of {max_input_tokens:,}{tot_err}")

        if output_tokens >= max_output_tokens:
            res.append("")
            res.append("To reduce output tokens:")
            res.append("- Ask for smaller changes in each request.")
            res.append("- Break your code into smaller source files.")
            if "diff" not in self.main_model.edit_format:
                res.append(
                    "- Use a stronger model like gpt-4o, sonnet or opus that can return diffs."
                )

        if input_tokens >= max_input_tokens or total_tokens >= max_input_tokens:
            res.append("")
            res.append("To reduce input tokens:")
            res.append("- Use /tokens to see token usage.")
            res.append("- Use /drop to remove unneeded files from the chat session.")
            res.append("- Use /clear to clear the chat history.")
            res.append("- Break your code into smaller source files.")

        res.append("")
        res.append(f"For more info: {urls.token_limits}")

        res = "".join([line + "\n" for line in res])
        self.io.tool_error(res)

    def lint_edited(self, fnames):
        res = ""
        for fname in fnames:
            errors = self.linter.lint(self.abs_root_path(fname))

            if errors:
                res += "\n"
                res += errors
                res += "\n"

        if res:
            self.io.tool_warning(res)

        return res

    def update_cur_messages(self):
        if self.partial_response_content:
            self.cur_messages += [
                dict(role="assistant", content=self.partial_response_content)
            ]
        if self.partial_response_function_call:
            self.cur_messages += [
                dict(
                    role="assistant",
                    content=None,
                    function_call=self.partial_response_function_call,
                )
            ]

    def get_file_mentions(self, content):
        words = set(word for word in content.split())

        # drop sentence punctuation from the end
        words = set(word.rstrip(",.!;:") for word in words)

        # strip away all kinds of quotes
        quotes = "".join(['"', "'", "`"])
        words = set(word.strip(quotes) for word in words)

        addable_rel_fnames = self.get_addable_relative_files()

        mentioned_rel_fnames = set()
        fname_to_rel_fnames = {}
        for rel_fname in addable_rel_fnames:
            normalized_rel_fname = rel_fname.replace("\\", "/")
            normalized_words = set(word.replace("\\", "/") for word in words)
            if normalized_rel_fname in normalized_words:
                mentioned_rel_fnames.add(rel_fname)

            fname = os.path.basename(rel_fname)

            # Don't add basenames that could be plain words like "run" or "make"
            if (
                "/" in fname
                or "\\" in fname
                or "." in fname
                or "_" in fname
                or "-" in fname
            ):
                if fname not in fname_to_rel_fnames:
                    fname_to_rel_fnames[fname] = []
                fname_to_rel_fnames[fname].append(rel_fname)

        for fname, rel_fnames in fname_to_rel_fnames.items():
            if len(rel_fnames) == 1 and fname in words:
                mentioned_rel_fnames.add(rel_fnames[0])

        return mentioned_rel_fnames

    def check_for_file_mentions(self, content):
        mentioned_rel_fnames = self.get_file_mentions(content)

        new_mentions = mentioned_rel_fnames - self.ignore_mentions

        if not new_mentions:
            return

        added_fnames = []
        group = ConfirmGroup(new_mentions)
        for rel_fname in sorted(new_mentions):
            if self.io.confirm_ask(
                f"Add {rel_fname} to the chat?", group=group, allow_never=True
            ):
                self.add_rel_fname(rel_fname)
                added_fnames.append(rel_fname)
            else:
                self.ignore_mentions.add(rel_fname)

    def send(self, messages, model=None, functions=None, purpose="send"):
        logger = logging.getLogger(__name__)
        if not model:
            model = self.main_model

        self.partial_response_content = ""
        self.partial_response_function_call = dict()

        self.io.log_llm_history("TO LLM", self._format_brade_messages())

        if self.main_model.use_temperature:
            temp = self.temperature
        else:
            temp = None

        completion = None
        try:
            if not isinstance(model, models.ModelConfig):
                logger.error(f"Invalid model type: {type(model)}, expected ModelConfig")
                raise TypeError(f"Expected ModelConfig instance, got {type(model)}")

            extra = model.extra_params.copy() if model.extra_params else {}
            reasoning_level = 0
            reasoning_level += self.get_reasoning_level_modifier()
            hash_object, completion = send_completion(
                model,
                messages,
                functions,
                self.stream,
                temp,
                reasoning_level=reasoning_level,
                extra_params=extra,
                purpose=purpose,
            )
            self.chat_completion_call_hashes.append(hash_object.hexdigest())

            if self.stream:
                yield from self.show_send_output_stream(completion)
            else:
                self.show_send_output(completion)
        except KeyboardInterrupt as kbi:
            self.keyboard_interrupt()
            raise kbi
        except Exception as e:
            logger.exception("Error in send()")
            raise
        finally:
            self.io.log_llm_history(
                "LLM RESPONSE",
                format_content("ASSISTANT", self.partial_response_content),
            )

            if self.partial_response_content:
                self.io.ai_output(self.partial_response_content)
            elif self.partial_response_function_call:
                # TODO: push this into subclasses
                args = self.parse_partial_args()
                if args:
                    self.io.ai_output(json.dumps(args, indent=4))

            self.calculate_and_show_tokens_and_cost(messages, completion)

    def show_send_output(self, completion):
        if self.verbose:
            print(completion)

        if not completion.choices:
            self.io.tool_error(str(completion))
            return

        show_func_err = None
        show_content_err = None
        try:
            if completion.choices[0].message.tool_calls:
                self.partial_response_function_call = (
                    completion.choices[0].message.tool_calls[0].function
                )
        except AttributeError as func_err:
            show_func_err = func_err

        try:
            message = completion.choices[0].message
            if hasattr(message, "content") and isinstance(message.content, list):
                # Handle array of content blocks
                content = ""
                for block in message.content:
                    if block.get("type") not in ["thinking", "redacted_thinking", "signature"]:
                        content += block.get("text", "")
                self.partial_response_content = content
            else:
                # Handle simple string content
                self.partial_response_content = message.content or ""
        except AttributeError as content_err:
            show_content_err = content_err

        resp_hash = dict(
            function_call=str(self.partial_response_function_call),
            content=self.partial_response_content,
        )
        resp_hash = hashlib.sha1(json.dumps(resp_hash, sort_keys=True).encode())
        self.chat_completion_response_hashes.append(resp_hash.hexdigest())

        if show_func_err and show_content_err:
            self.io.tool_error(show_func_err)
            self.io.tool_error(show_content_err)
            raise Exception("No data found in LLM response!")

        show_resp = self.render_incremental_response(True)
        self.io.assistant_output(show_resp, pretty=self.show_pretty())

        if (
            hasattr(completion.choices[0], "finish_reason")
            and completion.choices[0].finish_reason == "length"
        ):
            raise FinishReasonLength()

    def is_thinking_block(self, delta):
        """Check if a delta contains a thinking block."""
        if not hasattr(delta, "type"):
            return False
        return delta.type in ["thinking_delta", "redacted_thinking", "signature_delta"]

    def show_send_output_stream(self, completion):
        for chunk in completion:
            if len(chunk.choices) == 0:
                continue

            if (
                hasattr(chunk.choices[0], "finish_reason")
                and chunk.choices[0].finish_reason == "length"
            ):
                raise FinishReasonLength()

            try:
                func = chunk.choices[0].delta.function_call
                # dump(func)
                for k, v in func.items():
                    if k in self.partial_response_function_call:
                        self.partial_response_function_call[k] += v
                    else:
                        self.partial_response_function_call[k] = v
            except AttributeError:
                pass

            try:
                delta = chunk.choices[0].delta
                if self.is_thinking_block(delta):
                    continue
                
                text = delta.content
                if text:
                    self.partial_response_content += text
            except AttributeError:
                text = None

            if self.show_pretty():
                self.live_incremental_response(False)
            elif text:
                try:
                    sys.stdout.write(text)
                except UnicodeEncodeError:
                    # Safely encode and decode the text
                    safe_text = text.encode(
                        sys.stdout.encoding, errors="backslashreplace"
                    ).decode(sys.stdout.encoding)
                    sys.stdout.write(safe_text)
                sys.stdout.flush()
                yield text

    def live_incremental_response(self, final):
        show_resp = self.render_incremental_response(final)
        self.mdstream.update(show_resp, final=final)

    def render_incremental_response(self, final):
        return self.get_multi_response_content()

    def calculate_and_show_tokens_and_cost(self, messages, completion=None):
        prompt_tokens = 0
        completion_tokens = 0
        cache_hit_tokens = 0
        cache_write_tokens = 0

        if completion and hasattr(completion, "usage") and completion.usage is not None:
            prompt_tokens = completion.usage.prompt_tokens
            completion_tokens = completion.usage.completion_tokens
            cache_hit_tokens = getattr(
                completion.usage, "prompt_cache_hit_tokens", 0
            ) or getattr(completion.usage, "cache_read_input_tokens", 0)
            cache_write_tokens = getattr(
                completion.usage, "cache_creation_input_tokens", 0
            )

            if hasattr(completion.usage, "cache_read_input_tokens") or hasattr(
                completion.usage, "cache_creation_input_tokens"
            ):
                self.message_tokens_sent += prompt_tokens
                self.message_tokens_sent += cache_hit_tokens
                self.message_tokens_sent += cache_write_tokens
            else:
                self.message_tokens_sent += prompt_tokens

        else:
            prompt_tokens = self.main_model.token_count(messages)
            completion_tokens = self.main_model.token_count(
                self.partial_response_content
            )
            self.message_tokens_sent += prompt_tokens

        self.message_tokens_received += completion_tokens

        tokens_report = f"Tokens: {format_tokens(self.message_tokens_sent)} sent"

        if cache_write_tokens:
            tokens_report += f", {format_tokens(cache_write_tokens)} cache write"
        if cache_hit_tokens:
            tokens_report += f", {format_tokens(cache_hit_tokens)} cache hit"
        tokens_report += f", {format_tokens(self.message_tokens_received)} received."

        if not self.main_model.info.get("input_cost_per_token"):
            self.usage_report = tokens_report
            return

        cost = 0

        input_cost_per_token = self.main_model.info.get("input_cost_per_token") or 0
        output_cost_per_token = self.main_model.info.get("output_cost_per_token") or 0
        input_cost_per_token_cache_hit = (
            self.main_model.info.get("input_cost_per_token_cache_hit") or 0
        )

        # deepseek
        # prompt_cache_hit_tokens + prompt_cache_miss_tokens
        #    == prompt_tokens == total tokens that were sent
        #
        # Anthropic
        # cache_creation_input_tokens + cache_read_input_tokens + prompt
        #    == total tokens that were

        if input_cost_per_token_cache_hit:
            # must be deepseek
            cost += input_cost_per_token_cache_hit * cache_hit_tokens
            cost += (
                prompt_tokens - input_cost_per_token_cache_hit
            ) * input_cost_per_token
        else:
            # hard code the anthropic adjustments, no-ops for other models since cache_x_tokens==0
            cost += cache_write_tokens * input_cost_per_token * 1.25
            cost += cache_hit_tokens * input_cost_per_token * 0.10
            cost += prompt_tokens * input_cost_per_token

        cost += completion_tokens * output_cost_per_token

        self.total_cost += cost
        self.message_cost += cost

        def format_cost(value):
            if value == 0:
                return "0.00"
            magnitude = abs(value)
            if magnitude >= 0.01:
                return f"{value:.2f}"
            else:
                return f"{value:.{max(2, 2 - int(math.log10(magnitude)))}f}"

        cost_report = (
            f"Cost: ${format_cost(self.message_cost)} message,"
            f" ${format_cost(self.total_cost)} session."
        )

        if self.add_cache_headers and self.stream:
            warning = " Use --no-stream for accurate caching costs."
            self.usage_report = tokens_report + "\n" + cost_report + warning
            return

        if cache_hit_tokens and cache_write_tokens:
            sep = "\n"
        else:
            sep = " "

        self.usage_report = tokens_report + sep + cost_report

    def compute_usage(self):
        self.message_cost = 0.0
        self.message_tokens_sent = 0
        self.message_tokens_received = 0

    def get_multi_response_content(self, final=False):
        cur = self.multi_response_content or ""
        new = self.partial_response_content or ""

        if new.rstrip() != new and not final:
            new = new.rstrip()
        return cur + new

    def get_rel_fname(self, fname):
        try:
            return os.path.relpath(fname, self.root)
        except ValueError:
            return fname

    def get_inchat_relative_files(self):
        files = [self.get_rel_fname(fname) for fname in self.abs_fnames]
        return sorted(set(files))

    def is_file_safe(self, fname):
        try:
            return Path(self.abs_root_path(fname)).is_file()
        except OSError:
            return

    def get_all_relative_files(self):
        if self.repo:
            files = self.repo.get_tracked_files()
        else:
            files = self.get_inchat_relative_files()

        # This is quite slow in large repos
        # files = [fname for fname in files if self.is_file_safe(fname)]

        return sorted(set(files))

    def get_all_abs_files(self):
        files = self.get_all_relative_files()
        files = [self.abs_root_path(path) for path in files]
        return files

    def get_addable_relative_files(self):
        all_files = set(self.get_all_relative_files())
        inchat_files = set(self.get_inchat_relative_files())
        read_only_files = set(
            self.get_rel_fname(fname) for fname in self.abs_read_only_fnames
        )
        return all_files - inchat_files - read_only_files

    def check_for_dirty_commit(self, path):
        if not self.repo:
            return
        if not self.dirty_commits:
            return
        if not self.repo.is_dirty(path):
            return

        # We need a committed copy of the file in order to /undo, so skip this
        # fullp = Path(self.abs_root_path(path))
        # if not fullp.stat().st_size:
        #     return

        self.io.tool_output(f"Committing {path} before applying edits.")
        self.need_commit_before_edits.add(path)

    def allowed_to_edit(self, path):
        """Determine if a file can be edited and handle necessary setup.

        This method manages the workflow for determining if a file can be edited and
        preparing it for editing. It handles several cases:

        1. Files already in self.abs_fnames:
           - Allowed to edit
           - May trigger dirty commit if configured

        2. New files that don't exist:
           - Requires user confirmation
           - Creates empty file
           - Adds to git repo if needed
           - Adds to self.abs_fnames

        3. Existing files not in chat or marked read-only:
           - Requires user confirmation
           - Adds to git repo if needed
           - Adds to self.abs_fnames
           - May trigger dirty commit

        The method maintains important invariants:
        - Files must be explicitly added before editing
        - New files require user confirmation
        - Git repo state is properly maintained
        - Dirty files are committed if configured

        Args:
            path (str|Path): Path to the file, relative to project root

        Returns:
            bool: True if the file can be edited, False otherwise

        Side Effects:
            - May create new files
            - May add files to git repo
            - May trigger dirty commits
            - Updates self.abs_fnames
            - Updates self.check_added_files()
        """
        full_path = self.abs_root_path(path)
        if self.repo:
            need_to_add = not self.repo.path_in_repo(path)
        else:
            need_to_add = False

        if full_path in self.abs_fnames:
            self.check_for_dirty_commit(path)
            return True

        if not Path(full_path).exists():
            if not self.io.confirm_ask("Create new file?", subject=path):
                self.io.tool_output(f"Skipping edits to {path}")
                return

            if not self.dry_run:
                if not utils.touch_file(full_path):
                    self.io.tool_error(f"Unable to create {path}, skipping edits.")
                    return

                # Seems unlikely that we needed to create the file, but it was
                # actually already part of the repo.
                # But let's only add if we need to, just to be safe.
                if need_to_add:
                    self.repo.repo.git.add(full_path)

            self.abs_fnames.add(full_path)
            self.check_added_files()
            return True

        if not self.io.confirm_ask(
            "Allow edits to file that has not been added to the chat, or was added as read-only?",
            subject=path,
        ):
            self.io.tool_output(f"Skipping edits to {path}")
            return

        if need_to_add:
            self.repo.repo.git.add(full_path)

        self.abs_fnames.add(full_path)
        self.check_added_files()
        self.check_for_dirty_commit(path)

        return True

    warning_given = False

    def check_added_files(self):
        if self.warning_given:
            return

        warn_number_of_files = 4
        warn_number_of_tokens = 20 * 1024

        num_files = len(self.abs_fnames)
        if num_files < warn_number_of_files:
            return

        tokens = 0
        for fname in self.abs_fnames:
            if is_image_file(fname):
                continue
            content = self.io.read_text(fname)
            tokens += self.main_model.token_count(content)

        if tokens < warn_number_of_tokens:
            return

        self.warning_given = True

    def prepare_to_edit(self, edits):
        """Validate and filter edits before applying them.

        This method:
        1. Validates that files can be edited (exists, in chat, not read-only)
        2. Handles new file creation with user confirmation
        3. Commits dirty files if configured
        4. Filters out edits for files that can't/shouldn't be edited

        Args:
            edits: list[Edit] - List of (path, original, updated) tuples representing
                  the proposed edits

        Returns:
            list[Edit]: Filtered list of edits that can be safely applied
        """
        res = []
        seen = dict()

        self.need_commit_before_edits = set()

        for edit in edits:
            path = edit[0]
            if path is None:
                res.append(edit)
                continue
            if path == "python":
                dump(edits)
            if path in seen:
                allowed = seen[path]
            else:
                allowed = self.allowed_to_edit(path)
                seen[path] = allowed

            if allowed:
                res.append(edit)

        self.dirty_commit()
        self.need_commit_before_edits = set()

        return res

    def apply_updates(self):
        """Processes and applies code edits from the LLM response.

        This method handles the core code modification workflow:
        1. Extracts edit blocks from LLM response
        2. Validates files can be edited
        3. Handles new file creation
        4. Applies the edits
        5. Reports results to user

        Key invariants maintained:
        - Only explicitly added files can be edited
        - New files require user confirmation
        - Files in .gitignore are skipped
        - Read-only files are never modified

        Returns:
            set: The set of files that were successfully edited
        """
        edited = set()
        try:
            edits = self.get_edits()
            edits = self.prepare_to_edit(edits)
            edited = set(edit[0] for edit in edits)
            self.apply_edits(edits)
        except EditBlockError as ebe:
            self.num_malformed_responses += 1
            self.io.tool_output(ebe.markdown_message)
            self.reflected_message = ebe.markdown_message
        except ValueError as err:
            self.num_malformed_responses += 1

            err = err.args[0]

            self.io.tool_error("The LLM did not conform to the edit format.")
            self.io.tool_output(urls.edit_errors)
            self.io.tool_output()
            self.io.tool_output(str(err))

            self.reflected_message = str(err)
            return edited

        except ANY_GIT_ERROR as err:
            self.io.tool_error(str(err))
            return edited
        except Exception as err:
            self.io.tool_error("Exception while updating files:")
            self.io.tool_error(str(err), strip=False)

            traceback.print_exc()

            self.reflected_message = str(err)
            return edited

        for path in edited:
            if self.dry_run:
                self.io.tool_output(f"Did not apply edit to {path} (--dry-run)")
            else:
                self.io.tool_output(f"Applied edit to {path}")

        return edited

    def parse_partial_args(self):
        # dump(self.partial_response_function_call)

        data = self.partial_response_function_call.get("arguments")
        if not data:
            return

        try:
            return json.loads(data)
        except JSONDecodeError:
            pass

        try:
            return json.loads(data + "]}")
        except JSONDecodeError:
            pass

        try:
            return json.loads(data + "}]}")
        except JSONDecodeError:
            pass

        try:
            return json.loads(data + '"}]}')
        except JSONDecodeError:
            pass

    # commits...

    def get_context_from_history(self, history):
        context = ""
        if history:
            # Optimize for the ArchitectCoder case. Aim to get the following messages:
            # - the architect message proposing the change
            # - the placeholder request to the editor
            # - the placeholder for the editor's response
            # - the architect message reviewing the change
            for msg in history[-4:]:
                context += "\n" + msg["role"].upper() + ": " + msg["content"] + "\n"

        return context

    def auto_commit(self, edited, context=None):
        """Automatically commits edited files to git with generated commit messages.

        This method handles the git workflow after successful edits:
        1. Skips if repo/auto-commits not configured
        2. Uses chat context to generate commit message. If not provided,
           then recent chat messages are used as the context.
        3. Commits the changes
        4. Updates conversation history
        5. Reports results to user

        The method maintains important git-related invariants:
        - Only commits explicitly edited files
        - Generates meaningful commit messages from context
        - Tracks aider commits separately
        - Supports undo functionality

        Args:
            edited: Set of files to commit
            context: Optional explicit commit context

        Returns:
            Optional[str]: Status message about the commit
        """
        if not self.repo or not self.auto_commits or self.dry_run:
            return

        if not context:
            context = self.get_context_from_history(self.cur_messages)

        try:
            res = self.repo.commit(fnames=edited, context=context, aider_edits=True)
            if res:
                self.show_auto_commit_outcome(res)
                commit_hash, commit_message = res
                return self.gpt_prompts.files_content_gpt_edits.format(
                    hash=commit_hash,
                    message=commit_message,
                )

            return self.gpt_prompts.files_content_gpt_no_edits
        except ANY_GIT_ERROR as err:
            self.io.tool_error(f"Unable to commit: {str(err)}")
            return

    def show_auto_commit_outcome(self, res):
        commit_hash, commit_message = res
        self.last_aider_commit_hash = commit_hash
        self.aider_commit_hashes.add(commit_hash)
        self.last_aider_commit_message = commit_message
        if self.show_diffs:
            self.commands.cmd_diff()

    def show_undo_hint(self):
        if not self.commit_before_message:
            return
        if self.commit_before_message[-1] != self.repo.get_head_commit_sha():
            self.io.tool_output(
                "You can use /undo to undo and discard each aider commit."
            )

    def dirty_commit(self):
        if not self.need_commit_before_edits:
            return
        if not self.dirty_commits:
            return
        if not self.repo:
            return

        self.repo.commit(fnames=self.need_commit_before_edits)

        # files changed, move cur messages back behind the files messages
        # self.move_back_cur_messages(self.gpt_prompts.files_content_local_edits)
        return True

    def get_edits(self, mode="update"):
        return []

    def apply_edits(self, edits):
        """Apply a list of edits to the files.

        This method applies the edits extracted by get_edits() to the files.
        The specific edit application logic depends on the coder implementation.

        Args:
            edits: list[Edit] - List of (path, original, updated) tuples representing
                  the edits to apply. For shell commands, path will be None.

        Returns:
            None
        """
        return

    def run_shell_commands(self):
        """Execute shell commands that were detected in the LLM response.

        Shell command handling works as follows:

        1. Command Detection:
           - During LLM response processing in find_original_update_blocks(), any code blocks
             with shell-related fences (```bash, ```sh, etc.) are captured as shell commands
             - These are stored in self.shell_commands list
             - Shell blocks are identified by fence markers like ```bash, ```sh, etc.
             - Only blocks NOT followed by a SEARCH/REPLACE block are treated as commands

        2. Configuration:
           - The suggest_shell_commands flag controls whether commands are offered for execution
           - When False, commands are still collected but not offered to run
           - This is controlled via constructor parameter and CLI flag

        3. Command Execution Flow:
           - After processing edits, run_shell_commands() is called
           - It iterates through the collected commands in self.shell_commands
           - For each command, it calls handle_shell_commands()
           - Commands are only executed if the user explicitly confirms
           - Output is captured and displayed to the user
           - Any errors are reported back to the LLM for handling

        This design separates command detection from execution decisions, allowing
        flexible control over when and whether to run shell commands while still
        capturing them for analysis.
        """
        if not self.suggest_shell_commands:
            return ""

        done = set()
        group = ConfirmGroup(set(self.shell_commands))
        accumulated_output = ""
        for command in self.shell_commands:
            if command in done:
                continue
            done.add(command)
            output = self.handle_shell_commands(command, group)
            if output:
                accumulated_output += output + "\n\n"
        return accumulated_output

    def handle_shell_commands(self, commands_str, group):
        commands = commands_str.strip().splitlines()
        command_count = sum(
            1 for cmd in commands if cmd.strip() and not cmd.strip().startswith("#")
        )
        prompt = "Run shell command?" if command_count == 1 else "Run shell commands?"
        if not self.io.confirm_ask(
            prompt,
            subject="\n".join(commands),
            explicit_yes_required=True,
            group=group,
            allow_never=True,
        ):
            return

        accumulated_output = ""
        for command in commands:
            command = command.strip()
            if not command or command.startswith("#"):
                continue

            self.io.tool_output()
            self.io.tool_output(f"Running {command}")
            # Add the command to input history
            self.io.add_to_input_history(f"/run {command.strip()}")
            exit_status, output = run_cmd(command, error_print=self.io.tool_error)
            if output:
                accumulated_output += f"Output from {command}\n{output}\n"

        if accumulated_output.strip() and not self.io.confirm_ask(
            "Add command output to the chat?", allow_never=True
        ):
            accumulated_output = ""

        return accumulated_output
