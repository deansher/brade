import difflib
from difflib import SequenceMatcher, unified_diff
import math
import re
import sys
import diff_match_patch
from pathlib import Path

from aider import utils

from ..dump import dump  # noqa: F401
from .base_coder import Coder, EditBlockError
from .editblock_prompts import EditBlockPrompts

import logging

logger = logging.getLogger(__name__)


class MissingFilenameError(Exception):
    pass


class SearchReplaceImplementationError(Exception):
    pass


class FileNotInContextError(Exception):
    """Raised when a SEARCH/REPLACE block refers to a file not available in context."""
    def __init__(self, path):
        message = f"The file '{path}' is not available in the current context."
        super().__init__(message)
        self.path = path


class SearchReplaceBlockParseError(Exception):
    """Raised when a SEARCH/REPLACE block has syntax or validation errors.

    This includes:
    - Missing or incorrect file path
    - Missing or incorrect fence markers
    - Incorrect marker order (SEARCH/DIVIDER/REPLACE)
    - Other syntax/format violations
    """

    def __init__(self, message, path=None, content=None):
        super().__init__(message)
        self.path = path
        self.content = content  # Store the problematic content


class NoExactMatchError(Exception):
    def __init__(self, candidate=None, message=""):
        super().__init__(message)
        self.candidate = candidate


class MultipleMatchesError(Exception):
    pass


# Get handlers from root logger to bypass its level filter
for handler in logging.getLogger().handlers:
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

DEFAULT_FENCE = ("`" * 3, "`" * 3)

# fuzzy matching tolerance using diff-match-patch


class EditBlockCoder(Coder):
    """A coder that uses search/replace blocks for code modifications.

    This coder specializes in making precise, controlled changes to code files using
    a search/replace block format. It can operate either as a top-level coder taking
    requests directly from users, or as a subordinate implementing changes specified
    by another coder.

    # Architectural Design Decisions

    ## Role Independence
    EditBlockCoder maintains strict focus on implementation:
    - Handles direct requests or specified changes
    - Makes no assumptions about larger processes
    - Stays focused on precise implementation
    - Flags issues rather than making decisions

    ## Core Competency
    Expertise in search/replace block format:
    - Exact matching of existing code
    - Precise replacement specification
    - Careful handling of whitespace and context
    - Support for file creation and deletion

    ## Implementation Notes
    - Uses search/replace blocks for all file modifications
    - Validates changes before applying them
    - Reports issues without attempting resolution
    - Maintains consistent format across all changes

    Attributes:
        edit_format: The edit format identifier for this coder type ("diff")
        gpt_prompts: The prompts configuration for this coder
    """

    edit_format = "diff"
    gpt_prompts = EditBlockPrompts()

    # Maps error types to their explanations and fix suggestions
    ERROR_TYPE_DETAILS = {
        "multiple_matches": {
            "why_failed": [
                "- The SEARCH text matched multiple places in the file.",
                "- This means we can't be sure which occurrence you want to modify.",
            ],
            "how_to_fix": [
                "- Add more lines of context around your SEARCH block to uniquely identify the intended match.",
                "- Include distinctive nearby code, comments, or blank lines that only appear near your target.",
                "- Look for unique function signatures, class definitions, or comments that can anchor your selection.",
                "- If modifying similar code blocks, make your SEARCH more specific to the intended block.",
            ],
        },
        "missing_filename": {
            "why_failed": [
                "- The path is missing or invalid.",
                "- Make sure the file path is listed above the fence and spells a valid filename.",
                "- This will also happen if you try to edit a file that is not provided in <brade:context>...</brade:context>.",
            ],
            "how_to_fix": [
                "- Ensure the file path appears alone on the line before the opening fence.",
                "- Check that the path exactly matches a file provided in <brade:context>.",
                "- If the file you want to edit is not provided, ask for it.",
                "- For new files, make sure the path includes a valid file extension.",
                "- Double-check for typos in the filename and path.",
            ],
        },
        "file_not_in_context": {
            "why_failed": [
                "- The file isn't included in the <brade:context> section.",
                "- We can only edit files that are provided in context.",
            ],
            "how_to_fix": [
                "- Ask your partner to share this file.",
                "- Use the appropriate command to add the file to context.",
                "- Check for typos in the filename and path.",
                "- If creating a new file, ensure it has a valid file extension.",
            ],
        },
        "no_match": {
            "why_failed": [
                "- The SEARCH text did not match exactly.",
                "- This usually means there are small differences between your SEARCH block and the file content.",
            ],
            "how_to_fix": [
                "- Copy the exact content from the latest file version in <brade:context>.",
                "- Match whitespace, indentation, and comments precisely.",
                "- If you see a similarity percentage, check the diff for small discrepancies.",
                "- If the file content has changed, update your SEARCH block to match.",
                "- Consider breaking your change into smaller, simpler edits.",
            ],
        },
        "parse_error": {
            "why_failed": [
                "- The SEARCH/REPLACE block format is incorrect.",
                "- This could be missing markers, wrong order, or invalid syntax.",
            ],
            "how_to_fix": [
                "- Ensure each block has exactly one SEARCH, DIVIDER, and REPLACE marker in that order.",
                "- Check that markers are spelled correctly: <<<<<<< SEARCH, =======, >>>>>>> REPLACE",
                "- Verify the file path is on its own line before the opening fence.",
                "- Make sure the code fence markers are properly placed.",
            ],
        },
    }

    def get_edits(self):
        """Extract edit blocks from the LLM response.

        This method extracts edit blocks from the LLM's response content in
        self.partial_response_content. The format of the edit blocks depends on
        the specific coder implementation (e.g. EditBlockCoder uses search/replace blocks).

        Returns:
            list[Edit]: List of (path, original, updated) tuples representing the edits.
                     For shell commands, path will be None.
        """
        content = self.partial_response_content

        # Get both editable and read-only filenames
        valid_fnames = list(self.get_inchat_relative_files())
        if self.abs_read_only_fnames:
            for fname in self.abs_read_only_fnames:
                valid_fnames.append(self.get_rel_fname(fname))

        try:
            # Parse the edit blocks
            edits = list(
                find_original_update_blocks(
                    content,
                    self.fence,
                    valid_fnames,
                )
            )

            self.shell_commands += [edit[1] for edit in edits if edit[0] is None]
            edits = [edit for edit in edits if edit[0] is not None]

            return edits

        except FileNotInContextError as exc:
            failed = [
                {
                    "path": exc.path,
                    "original": "",
                    "updated": "",
                    "error_type": "file_not_in_context",
                    "error_context": str(exc),
                }
            ]
            raise EditBlockError(self._build_failed_edit_error_message(failed, []))
            
        except SearchReplaceBlockParseError as exc:
            # Use the explicit path and content from the exception
            path = getattr(exc, 'path', None)
            error_content = getattr(exc, 'content', None)
            
            failed = [
                {
                    "path": path,
                    "original": "",
                    "updated": "",
                    "error_type": "parse_error",
                    "error_context": str(exc),
                }
            ]
            raise EditBlockError(self._build_failed_edit_error_message(failed, []))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.applied_changes = []  # Track successful changes

    def apply_edits(self, edits):
        """Apply a list of edits to the files.

        This method applies the edits extracted by get_edits() to the files.
        It handles various error cases and collects detailed error information.

        Args:
            edits: list[Edit] - List of (path, original, updated) tuples representing
                  the edits to apply.

        Raises:
            EditBlockError: If any edits fail, with detailed error information.

        The error information for each failed edit is a dictionary with:
        - path: The file path that was targeted
        - original: The SEARCH block content
        - updated: The REPLACE block content
        - error_type: The type of error ("missing_filename", "no_match", "multiple_matches")
        - error_context: Additional details about what went wrong
        """
        failed = []
        passed = []

        for edit in edits:
            path, original, updated = edit
            full_path = self.abs_root_path(path)
            content = self.io.read_text(full_path)

            logger.debug(
                f"apply_edits: about to call do_replace with self.fence={self.fence}"
            )
            try:
                new_content = do_replace(
                    full_path, content, original, updated, fence=self.fence
                )
                if not new_content:
                    # try patching any of the other files in the chat
                    for alt_path in self.abs_fnames:
                        alt_content = self.io.read_text(alt_path)
                        new_content = do_replace(
                            alt_path, alt_content, original, updated, fence=self.fence
                        )
                        if new_content:
                            full_path = alt_path
                            break

                if new_content:
                    self.io.write_text(full_path, new_content)
                    passed.append(edit)
                    # Track successful changes
                    self.applied_changes.append({
                        "path": path,
                        "original": original,
                        "updated": updated,
                        "retry_attempt": len(self.applied_changes),
                    })
                else:
                    raise NoExactMatchError(
                        message="No successful do_replace result on any file."
                    )

            except MissingFilenameError as exc:
                failed.append(
                    {
                        "path": path,
                        "original": original,
                        "updated": updated,
                        "error_type": "missing_filename",
                        "error_context": str(exc),
                    }
                )

            except NoExactMatchError as exc:
                failed.append(
                    {
                        "path": path,
                        "original": original,
                        "updated": updated,
                        "error_type": "no_match",
                        "error_context": str(exc),
                    }
                )

            except MultipleMatchesError as exc:
                failed.append(
                    {
                        "path": path,
                        "original": original,
                        "updated": updated,
                        "error_type": "multiple_matches",
                        "error_context": str(exc),
                    }
                )

        if failed:
            raise EditBlockError(self._build_failed_edit_error_message(failed, passed))

    def get_final_editor_outcome(self) -> str:
        """Return a consolidated summary of all successful edits.

        This method returns a single string that summarizes all changes that were
        successfully applied, including any retries and lint fixes. The summary
        uses SEARCH/REPLACE blocks to show exactly what content was changed.

        Returns:
            str: A message describing all changes made, or indicating that no changes
                were successfully applied.
        """
        if not self.applied_changes:
            return "No changes were applied"

        response = ["Here are all the changes that were successfully applied:\n"]
        
        # Group changes by file
        changes_by_file = {}
        for change in self.applied_changes:
            path = change["path"]
            if path not in changes_by_file:
                changes_by_file[path] = []
            changes_by_file[path].append(change)

        # Build blocks for each file's changes
        for path, changes in changes_by_file.items():
            for change in changes:
                response.extend([
                    f"\n{path}",
                    f"{self.fence[0]}python",
                    "<<<<<<< SEARCH",
                    change["original"],
                    "=======",
                    change["updated"],
                    ">>>>>>> REPLACE",
                    f"{self.fence[1]}\n",
                ])

        return "".join(response)

    def run(self, with_message=None, preproc=True):
        """Override run to use build_final_response for the final message."""
        super().run(with_message, preproc)
        if self.applied_changes:
            self.partial_response_content = self.get_final_editor_outcome()

    def _build_failed_edit_error_message(self, failed, passed):
        """Build a clear, structured markdown error message for each failing block.

        This method generates detailed error messages for failed SEARCH/REPLACE blocks.
        It handles different error types with specific guidance for each:

        Error Types:
        - missing_filename: Path is missing or invalid
        - no_match: SEARCH text didn't match file content
        - multiple_matches: SEARCH text matched multiple locations
        - parse_error: Syntax or validation errors in the SEARCH/REPLACE block

        For no_match errors, it attempts to find similar content and shows:
        - Similarity percentage
        - Unified diff with closest matching content
        - Warning if REPLACE content already exists

        Args:
            failed: List of failed edit dictionaries with:
                   - path: Target file path
                   - original: SEARCH block content
                   - updated: REPLACE block content
                   - error_type: Type of failure
                   - error_context: Additional error details
            passed: List of successful (path, original, updated) tuples

        Returns:
            str: A formatted markdown error message
        """
        messages = [
            f"# {len(failed)} SEARCH/REPLACE block(s) failed to match!",
            "",
            f"The other {len(passed)} block(s) were applied successfully. Do not resubmit those.",
            "",
        ]

        for item in failed:
            path = item["path"]
            original = item["original"]
            updated = item["updated"]
            error_type = item.get("error_type", "no_match")
            error_context = item.get("error_context", None)
            
            # Start a new message section for this failing block
            block_message = []
            block_message.append(
                f"## SearchReplace{error_type.title()}: The {error_type} error occurred" + 
                (f" in {path}" if path else "")
            )
            
            # Get file content for non-parse errors
            full_path = None
            content = None
            if path and error_type != "parse_error":
                full_path = self.abs_root_path(path)
                content = self.io.read_text(full_path)

            # Different handling for parse errors vs. other errors
            if error_type == "parse_error":
                # For parse errors, show the error message instead of an empty block
                block_message.append("### Error Details")
                block_message.append(f"```\n{error_context}\n```")
            else:
                # Show the failing SEARCH/REPLACE block for other error types
                block_message.append("### Offending SEARCH/REPLACE Block")
                block_message.append(
                    f"{path}\n"
                    f"{self.fence[0]}python\n"
                    f"<<<<<<< SEARCH\n{original}=======\n{updated}>>>>>>> REPLACE\n"
                    f"{self.fence[1]}"
                )

            # Explain why it failed
            block_message.append("### Why This Failed")
            error_details = self.ERROR_TYPE_DETAILS.get(error_type, {
                "why_failed": [
                    "- Encountered an unknown error type.",
                    f"- error_context: {error_context}",
                ],
                "how_to_fix": [
                    "- Review the error details carefully.",
                    "- Check that your SEARCH/REPLACE block follows the required format.",
                    "- If the problem persists, please report this as a potential bug.",
                ],
            })
            
            if error_type == "no_match":
                candidate = find_similar_lines(original, content)
                if candidate:
                    similarity_ratio = SequenceMatcher(
                        None, original, candidate
                    ).ratio()
                    similarity_percent = similarity_ratio * 100
                    diff_lines = list(
                        unified_diff(
                            original.splitlines(keepends=True),
                            candidate.splitlines(keepends=True),
                            fromfile="your SEARCH block",
                            tofile="closest match in file content",
                        )
                    )
                    diff_text = "".join(diff_lines)
                    block_message.extend([
                        *error_details["why_failed"],
                        f"- Detected similarity: {similarity_percent:.0f}%",
                        f"- Here's a diff to help you diagnose this:\n```\n{diff_text}\n```",
                    ])
                else:
                    block_message.extend([
                        "- The SEARCH text did not match any content in the file.",
                        "- The differences appear to be substantial, or the content may not exist in this file.",
                        "- Double-check that you're searching in the correct file and that the content exists.",
                    ])
            else:
                block_message.extend(error_details["why_failed"])

            def _should_warn_about_existing(updated_text):
                """Check if we should warn about REPLACE content already existing.

                Only warns if the REPLACE content has 10 or more non-empty lines.
                This threshold helps avoid warnings about common code patterns
                like exception handling blocks while still catching substantial
                duplicated sections.
                """
                if not updated_text or not updated_text.strip():
                    return False

                lines = [line for line in updated_text.splitlines() if line.strip()]
                return len(lines) >= 10

            # Check if substantial REPLACE content already exists
            if content and _should_warn_about_existing(updated):
                block_message.append(
                    f"\nWarning: The REPLACE block content already exists in {path}.\n"
                    "Please confirm if the SEARCH/REPLACE block is still needed.\n"
                    "If it is not needed after all, then you can just leave this one out.\n"
                    "But if you are deliberately duplicating existing content, then you can ignore this warning."
                )

            # Add tips on how to fix
            block_message.append("### How to Fix")
            error_details = self.ERROR_TYPE_DETAILS.get(error_type, {
                "why_failed": [
                    "- Encountered an unknown error type.",
                    f"- error_context: {error_context}",
                ],
                "how_to_fix": [
                    "- Review the error details carefully.",
                    "- Check that your SEARCH/REPLACE block follows the required format.",
                    "- If the problem persists, please report this as a potential bug.",
                ],
            })
            
            # Copy the how_to_fix list so we don't modify the ERROR_TYPE_DETAILS constant
            how_to_fix = list(error_details["how_to_fix"])
            
            # Add specific fence format information for parse errors
            if error_type == "parse_error":
                fence_example = f"{self.fence[0]}python ... {self.fence[1]}"
                how_to_fix.append(f"- Use the correct fence format for this project: {fence_example}")
                
            block_message.extend(how_to_fix)

            messages.append("\n\n".join(block_message))

        # Add a correct format example for parse errors
        if any(item.get("error_type") == "parse_error" for item in failed):
            messages.append("\n## Correct Format Example")
            example = (
                f"filename.py\n"
                f"{self.fence[0]}python\n"
                f"<<<<<<< SEARCH\n"
                f"def example():\n"
                f"    return True\n"
                f"=======\n"
                f"def example():\n"
                f"    return False\n"
                f">>>>>>> REPLACE\n"
                f"{self.fence[1]}"
            )
            messages.append(example)

        # Summaries
        summary = []
        if passed:
            pblocks = "block" if len(passed) == 1 else "blocks"
            blocks_str = "block" if len(failed) == 1 else "blocks"
            summary.extend([
                f"# {len(passed)} SEARCH/REPLACE {pblocks} were applied successfully.",
                f"Only resend fixed versions of the {blocks_str} that failed.",
            ])
            # Track successful edits by file
            successful_files = {}
            for p, _, _ in passed:
                successful_files[p] = successful_files.get(p, 0) + 1
            for path, count in successful_files.items():
                blocks = "block" if count == 1 else "blocks"
                summary.append(f"Applied {count} {blocks} to {path}")

        note = (
            "Note: The SEARCH section must match existing content exactly, including whitespace,\n"
            "indentation, and formatting."
        )

        return "\n\n".join(messages + [""] + ([note] if failed else []) + summary)


def prep(content):
    if content and not content.endswith("\n"):
        content += "\n"
    lines = content.splitlines(keepends=True)
    return content, lines


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two text blocks using diff-match-patch.

    Uses Levenshtein distance normalized by max(len(text2), 2) to produce
    a similarity score between 0 and 1, where:
    - 1.0 means the texts are identical
    - 0.0 means the texts are completely different
    - Values in between indicate partial similarity

    For single-character differences (e.g. "a" vs "b"), the similarity
    will be 0.5 since we use 2 as the minimum denominator. This helps
    detect potential transcription errors in short strings while maintaining
    our usual similarity thresholds for longer content.

    Args:
        text1: First text to compare
        text2: Second text to compare (used as denominator for normalization)

    Returns:
        float: Similarity score between 0 and 1
    """
    # Handle empty string cases
    if text2 == "":
        return 1.0 if text1 == "" else 0.0

    dmp = diff_match_patch.diff_match_patch()
    diffs = dmp.diff_main(text1, text2)
    dmp.diff_cleanupSemantic(diffs)
    distance = dmp.diff_levenshtein(diffs)
    # Scale by max(len(text2), 2) to give single-character differences a similarity of 0.5
    return 1 - (distance / max(len(text2), 2))


def find_match_end(dmp, whole, match_index, original):
    """Find where a match ends in the whole text.

    Uses diff-match-patch to analyze differences and find the endpoint of a match,
    taking into account potential insertions and deletions.

    Args:
        dmp: diff_match_patch instance to use
        whole: The complete text being searched
        match_index: Starting index of the match
        original: The pattern being matched

    Returns:
        int: The index where this match ends
    """
    # Example of how this works:
    # Consider:
    #   whole = "x"*50 + "abcdefg" + "z"*50  # target file content
    #   original = "x"*40 + "abd_efg" + "z"*40  # search text
    #
    # 1. match_main() finds best match location in whole:
    #    - match_index = 10 gives best alignment:
    #      whole:    "x"*10 + "x"*40 + "abcdefg" + "z"*50
    #      original: -------- + "x"*40 + "abd_efg" + "z"*40
    #    - Despite length differences, it finds match due to 0.05 threshold
    #
    # 2. diff_main() compares window of whole with original:
    #    - Window starts at match_index = 10
    #    - Window length is 2*len(original) = 174 chars
    #    - Window contains: "x"*40 + "abcdefg" + "z"*50 + (next file content)
    #    - Original: "x"*40 + "abd_efg" + "z"*40
    #    - Returns these diffs:
    #      [(0,  "x"*40 + "ab"), # eq: match
    #       (-1, "c"),           # del: only in whole
    #       (0, "d"),            # eq: match
    #       (1, "_"),            # ins: only in original
    #       (0, "efg" + "z"*40), # eq: match
    #       (-1, "z"*10 + (next file content)), # del: only in whole
    #
    # 3. Walk through diffs tracking two positions:
    #    - whole_chars: counts through whole's window
    #    - last_equal_endpoint: number of matched chars of whole
    #    - We count these characters of whole:
    #      - "x"*40 + "ab" + "c" + "d" + "efg" + "z"*40
    #
    # 4. Final match_end = match_index + last_equal_endpoint
    #    - Points to just after "z"*40 in whole
    #    - Ignores remainder of whole, which doesn't match original
    #    - Exactly captures the region that matches original

    diffs = dmp.diff_main(
        whole[match_index : match_index + 2 * len(original)], original
    )
    dmp.diff_cleanupSemantic(diffs)
    whole_chars = 0
    last_equal_endpoint = 0
    for op, text in diffs:
        if op == 0:  # equal text
            whole_chars += len(text)
            last_equal_endpoint = whole_chars
        elif op == -1:  # deletion text
            whole_chars += len(text)
    return match_index + last_equal_endpoint


def replace_most_similar_chunk(whole, original, updated):
    """
    Uses diff-match-patch to perform fuzzy matching and patching for the search block.

    The matching strategy:
    1. Uses match_main to find all potential matches
    2. Requires 95% accuracy and rejects ambiguous matches
    3. Uses diff analysis to find match boundaries

    Returns the new content with the matched region replaced by `updated`.
    Raises NoExactMatchError if no sufficiently accurate match is found
    or MultipleMatchesError if multiple good matches are found.
    """
    dmp = diff_match_patch.diff_match_patch()
    dmp.Match_Threshold = 0.05  # Require 95% accuracy
    dmp.Match_Distance = sys.maxsize  # Allow matches anywhere in file

    if not original:
        logger.debug(
            "SEARCH block is empty; appending REPLACE block to the end of the file"
        )
        return whole + updated

    # Find all potential matches
    matches = []
    remaining = whole
    offset = 0
    while True:
        match_index = dmp.match_main(remaining, original, 0)
        if match_index == -1:
            break
        match_end = find_match_end(dmp, remaining, match_index, original)
        # Safeguard against infinite loop
        if match_end <= match_index:
            raise SearchReplaceImplementationError(
                "Infinite loop risk: match_end did not advance past match_index."
            )

        # Calculate match quality
        similarity_ratio = calculate_text_similarity(
            remaining[match_index:match_end], original
        )

        if similarity_ratio >= 0.95:  # Same threshold as Match_Threshold
            matches.append((match_index + offset, match_end + offset, similarity_ratio))

        # Search in remaining text after this match
        remaining = remaining[match_end:]
        offset += match_end

    if not matches:
        logger.debug("SEARCH block not found in file content")
        logger.debug(f"search_text:\\n{original}\\nwhole:\\n{whole}")
        raise NoExactMatchError(
            candidate=None,
            message=(
                "SEARCH/REPLACE block failed: No sufficiently accurate match found.\\n"
                "The search text may have transcription errors. Check for:\\n"
                "- Extra or missing spaces\\n"
                "- Different line breaks or indentation\\n"
                "- Missing or altered punctuation\\n"
                f"Search text was: {original!r}"
            ),
        )

    if len(matches) > 1:
        logger.debug(f"Multiple matches found: {matches}")
        raise MultipleMatchesError(
            "SEARCH/REPLACE block failed: Multiple good matches found.\\n"
            "The search text matches multiple locations in the file.\\n"
            "Please provide additional lines of context in the SEARCH block to ensure a unique match.\\n"
            f"Search text was: {original!r}"
        )
    match_index, match_end, _ = matches[0]
    return whole[:match_index] + updated + whole[match_end:]


def strip_quoted_wrapping(res, fname=None, fence=DEFAULT_FENCE):
    """
    Given an input string which may have extra "wrapping" around it, remove the wrapping.
    For example:

    filename.ext
    ```
    We just want this content
    Not the filename and triple quotes
    ```
    """
    if not res:
        return res

    res = res.splitlines()

    if fname and res[0].strip().endswith(Path(fname).name):
        res = res[1:]

    if res[0].startswith(fence[0]) and res[-1].startswith(fence[1]):
        res = res[1:-1]

    res = "\n".join(res)
    if res and res[-1] != "\n":
        res += "\n"

    return res


def do_replace(fname, content, original, updated, fence=None):
    logger.debug(
        f"do_replace: {fname}\nSEARCH:\n{original}\nREPLACE:\n{updated}\nfence={fence}"
    )
    original = strip_quoted_wrapping(original, fname, fence)
    updated = strip_quoted_wrapping(updated, fname, fence)
    logger.debug("do_replace: stripped original and updated content")
    logger.debug(f"do_replace: {fname}\nSEARCH:\n{original}\nREPLACE:\n{updated}")
    fname = Path(fname)

    # does it want to make a new file?
    if not fname.exists() and not original.strip():
        logger.debug(f"do_replace: creating new file {fname}")
        fname.touch()
        return updated

    if content is None:
        logger.debug(f"do_replace: content is None for {fname}")
        return

    if not original.strip():
        # append to existing file, or start a new file
        logger.debug(f"do_replace: appending to {fname}")
        new_content = content + updated
        return new_content
    else:
        logger.debug(f"do_replace: replacing in {fname}")
        new_content = replace_most_similar_chunk(content, original, updated)
        if new_content is None:
            raise NoExactMatchError(
                "No matching content found in file. Check that the SEARCH block exactly matches the file content with only minor allowable differences."
            )
        # Allow empty REPLACE blocks (deletions) and no-change edits
        if not updated.strip() or new_content == content:
            return new_content
        return new_content


HEAD = r"^<{5,9} SEARCH\s*$"
DIVIDER = r"^={5,9}\s*$"
UPDATED = r"^>{5,9} REPLACE\s*$"

HEAD_ERR = "<<<<<<< SEARCH"
DIVIDER_ERR = "======="
UPDATED_ERR = ">>>>>>> REPLACE"

separators = "|".join([HEAD, DIVIDER, UPDATED])

split_re = re.compile(r"^((?:" + separators + r")[ ]*\n)", re.MULTILINE | re.DOTALL)


missing_file_path_err = (
    "Missing or incorrect file path. The path must be alone on the line"
    " before the opening fence. If this search/replacement block modifies existing"
    " content, then the path must exactly match an existing file that is provided"
    " in <brade:context>...</brade:context>.\n"
)


def strip_filename(filename):
    """Clean up a file path by stripping certain surrounding characters.

    Returns:
        str: the file path with strippable characters stripped, which might then be empty
    """
    filename = filename.strip()
    if filename.startswith("#"):
        filename = filename[1:]
    if filename.endswith(":"):
        filename = filename[:-1]
    filename = filename.strip()
    if filename.startswith("`") and filename.endswith("`"):
        filename = filename[1:-1]

    return filename


def check_marker_order(content):
    """Validate that SEARCH/REPLACE markers appear in the correct order.

    This function checks that any SEARCH/REPLACE markers in the content appear in
    the correct sequence: SEARCH → DIVIDER → REPLACE. It helps catch malformed
    blocks early with clear error messages.

    Args:
        content (str): The content to check for markers

    Raises:
        ValueError: If markers are found out of order or incomplete, with details
                  about the location and nature of the error
    """
    lines = content.splitlines()
    head_pattern = re.compile(HEAD)
    divider_pattern = re.compile(DIVIDER)
    updated_pattern = re.compile(UPDATED)

    # Track state for each block
    state = 0  # 0=expect SEARCH, 1=expect DIVIDER, 2=expect REPLACE
    block_start_line = None

    for i, line in enumerate(lines, 1):
        is_head = head_pattern.match(line.strip())
        is_divider = divider_pattern.match(line.strip())
        is_updated = updated_pattern.match(line.strip())

        if is_head and state == 0:
            state = 1
            block_start_line = i
        elif is_head:
            context = "\n".join(lines[max(0, i - 3) : min(len(lines), i + 2)])
            raise SearchReplaceBlockParseError(
                f"Found '<<<<<<< SEARCH' on line {i} but previous block was not complete:\n"
                f"{context}\n"
                f"Each block must have exactly one SEARCH, DIVIDER, and REPLACE marker in that order."
            )
        elif is_divider and state == 1:
            state = 2
        elif is_divider:
            context = "\n".join(lines[max(0, i - 3) : min(len(lines), i + 2)])
            raise SearchReplaceBlockParseError(
                f"Found '=======' on line {i} but not preceded by SEARCH marker:\n"
                f"{context}\n"
                f"Each block must have exactly one SEARCH, DIVIDER, and REPLACE marker in that order."
            )
        elif is_updated and state == 2:
            state = 0
        elif is_updated:
            context = "\n".join(lines[max(0, i - 3) : min(len(lines), i + 2)])
            raise SearchReplaceBlockParseError(
                f"Found '>>>>>>> REPLACE' on line {i} but not preceded by DIVIDER:\n"
                f"{context}\n"
                f"Each block must have exactly one SEARCH, DIVIDER, and REPLACE marker in that order."
            )

    if state == 1:
        raise SearchReplaceBlockParseError(
            f"Block starting at line {block_start_line} has SEARCH but is missing DIVIDER and REPLACE markers.\n"
            "Each block must have exactly one SEARCH, DIVIDER, and REPLACE marker in that order."
        )
    elif state == 2:
        raise SearchReplaceBlockParseError(
            f"Block starting at line {block_start_line} has SEARCH and DIVIDER but is missing REPLACE marker.\n"
            "Each block must have exactly one SEARCH, DIVIDER, and REPLACE marker in that order."
        )


def find_original_update_blocks(content, fence=DEFAULT_FENCE, valid_fnames=None):
    """Parse search/replace blocks from the content.

    The actual requirements for search/replace blocks are more flexible than what we tell the model:

    File Path Requirements:
    - Must be alone on a line before the opening fence
    - Can be stripped of trailing colons, leading #, and surrounding backticks/asterisks
    - For new files, an empty SEARCH section is allowed
    - The path can be relative to project root
    - The path must be valid (either match an existing file or be a new file path)
    - For existing files, path must match a filename in valid_fnames
      or a FileNotInContextError will be raised

    Block Structure Requirements:
    - Opening fence (e.g. ```python) - language specifier is optional
    - "<<<<<<< SEARCH" line (5+ < characters)
    - Search content (can be empty for new files)
    - "=======" line (5+ = characters)
    - Replace content
    - ">>>>>>> REPLACE" line (5+ > characters)
    - Closing fence (```)

    Search Content Requirements:
    - For existing files, must match exactly (including whitespace)
    - Exception: The code has special handling for leading whitespace mismatches
    - Exception: Can handle "..." lines that match between search and replace sections

    Multiple Blocks:
    - Multiple blocks for the same file are allowed
    - Each block is processed independently
    - Only the first match in a file is replaced

    Args:
        content (str): The content to parse for search/replace blocks
        fence (tuple): Opening and closing fence markers
        valid_fnames (list): Combined list of editable and read-only filenames that can be edited
        
    Raises:
        FileNotInContextError: If a file path is specified that isn't in valid_fnames
    """
    # First validate overall marker ordering
    check_marker_order(content)
    lines = content.splitlines(keepends=True)
    i = 0

    head_pattern = re.compile(HEAD)
    divider_pattern = re.compile(DIVIDER)
    updated_pattern = re.compile(UPDATED)

    while i < len(lines):
        line = lines[i]

        # Check for shell code blocks
        shell_starts = [
            "```bash",
            "```sh",
            "```shell",
            "```cmd",
            "```batch",
            "```powershell",
            "```ps1",
            "```zsh",
            "```fish",
            "```ksh",
            "```csh",
            "```tcsh",
        ]
        next_is_editblock = i + 1 < len(lines) and head_pattern.match(
            lines[i + 1].strip()
        )

        if (
            any(line.strip().startswith(start) for start in shell_starts)
            and not next_is_editblock
        ):
            shell_content = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                shell_content.append(lines[i])
                i += 1
            if i < len(lines) and lines[i].strip().startswith("```"):
                i += 1  # Skip the closing ```

            yield None, "".join(shell_content)
            continue

        # Check for SEARCH/REPLACE blocks
        if head_pattern.match(line.strip()):
            try:
                if i < 2:
                    raise SearchReplaceBlockParseError(
                        "Each SEARCH/REPLACE block must begin with a filename and a fence; "
                        f"Found a {HEAD} on line {i}"
                    )
                if i < 2 or not lines[i - 1].startswith(fence[0]):
                    raise SearchReplaceBlockParseError(
                        "Each SEARCH/REPLACE block must begin with a filename and a fence.\n"
                        f"""Expected "{fence[0]}" at the start of line {i - 1}, but got this:\n"""
                        f"{lines[i - 1]!r}\n"
                    )

                filepath_line = lines[i - 2]
                if not strip_filename(filepath_line) and i >= 3:
                    filepath_line = lines[i - 3]
                is_new_file = i + 1 < len(lines) and divider_pattern.match(
                    lines[i + 1].strip()
                )
                if is_new_file:
                    use_valid_fnames = None
                else:
                    use_valid_fnames = valid_fnames
                filepath = find_filepath(filepath_line, use_valid_fnames)
                if not filepath:
                    raise SearchReplaceBlockParseError(
                        missing_file_path_err.format(fence=fence)
                    )

                original_text = []
                i += 1
                while i < len(lines) and not divider_pattern.match(lines[i].strip()):
                    original_text.append(lines[i])
                    i += 1

                if i >= len(lines) or not divider_pattern.match(lines[i].strip()):
                    raise SearchReplaceBlockParseError(f"Expected `{DIVIDER_ERR}`")

                updated_text = []
                i += 1
                while i < len(lines) and not (
                    updated_pattern.match(lines[i].strip())
                    or divider_pattern.match(lines[i].strip())
                ):
                    updated_text.append(lines[i])
                    i += 1

                if i >= len(lines) or not (
                    updated_pattern.match(lines[i].strip())
                    or divider_pattern.match(lines[i].strip())
                ):
                    raise SearchReplaceBlockParseError(
                        f"Expected `{UPDATED_ERR}` or `{DIVIDER_ERR}`"
                    )

                yield filepath, "".join(original_text), "".join(updated_text)

            except SearchReplaceBlockParseError as e:
                processed = "".join(lines[: i + 1])
                err = str(e)
                raise SearchReplaceBlockParseError(f"{processed}\n^^^ {err}")

        i += 1


def looks_like_filepath(filepath):
    """Determine if a string looks like a valid file path.
    
    Uses several heuristics to check if a string appears to be a valid file path:
    1. Has a file extension
    2. Matches a known extensionless file pattern
    3. Contains path separators
    
    Args:
        filepath (str): The string to check
        
    Returns:
        bool: True if the string appears to be a valid file path
    """
    # Check for file extension (most common case)
    if Path(filepath).suffix:
        return True
        
    # Check for common extensionless files
    known_extensionless = {
        'Makefile', 'Dockerfile', 'README', 'LICENSE', 
        '.gitignore', '.env'
    }
    
    # Get the last part of the path (handles both "folder/file" and just "file")
    basename = Path(filepath).name
    
    # Known extensionless files or hidden files (starting with .)
    if basename in known_extensionless or basename.startswith('.'):
        return True
    
    # If it has path separators, it looks like a file path
    if '/' in filepath or '\\' in filepath:
        return True
        
    return False


def find_filepath(line, valid_fnames):
    """Find a file path in line.

    The file path must be alone on the line, optionally preceded by # or
    surrounded by backticks.

    If valid_fnames is provided, the stripped file path must be in the list.

    Args:
        line (str): the line that may contain the file path
        valid_fnames (list): List of valid file paths to match against
           If empty or not provided, then any syntactically valid file path is accepted.

    Returns:
        str: The found file path, or None if no valid file path found
        
    Raises:
        FileNotInContextError: If the file path has a valid syntax but is not in valid_fnames
    """
    filepath = strip_filename(line)
    if not filepath:
        return None

    # For existing files, require an exact match
    if valid_fnames:
        # Check for exact match first
        if filepath in valid_fnames:
            return filepath

        # Check for basename match
        for valid_fname in valid_fnames:
            if filepath == Path(valid_fname).name:
                return valid_fname
        
        # If it looks like a file path but doesn't match any valid files
        if looks_like_filepath(filepath):
            raise FileNotInContextError(filepath)

    # For new files, require a valid file path pattern
    elif looks_like_filepath(filepath):
        return filepath

    return None


def find_similar_lines(
    search_text: str, content_text: str, threshold: float = 0.6
) -> str:
    """
    Use diff-match-patch to locate a candidate snippet in content_text that is similar
    to search_text. Returns the candidate snippet if the similarity is above the threshold,
    otherwise returns an empty string.
    """
    dmp = diff_match_patch.diff_match_patch()
    match_index = dmp.match_main(content_text, search_text, 0)
    if match_index == -1:
        return ""
    candidate = content_text[match_index : match_index + len(search_text)]
    similarity = calculate_text_similarity(candidate, search_text)
    if similarity < threshold:
        return ""
    return candidate


def main():
    history_md = Path(sys.argv[1]).read_text()
    if not history_md:
        return

    messages = utils.split_chat_history_markdown(history_md)

    for msg in messages:
        msg = msg["content"]
        edits = list(find_original_update_blocks(msg))

        for fname, before, after in edits:
            # Compute diff
            diff = difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile="before",
                tofile="after",
            )
            diff = "".join(diff)
            dump(before)
            dump(after)
            dump(diff)


if __name__ == "__main__":
    main()
