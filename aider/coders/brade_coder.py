from aider.coders.editblock_coder import EditBlockCoder
from aider.coders.brade_prompts import BradePrompts
from aider.coders.chat_sitrep import ChatSitrep


class BradeCoder(EditBlockCoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.edit_format = "diff"
        self.brade_prompts = BradePrompts()

    def fmt_system_prompt(self, prompt):
        sitrep = ChatSitrep()
        return self.brade_prompts.make_main_system_prompt(sitrep)

    def format_chat_chunks(self):
        sitrep = ChatSitrep()
        chunks = super().format_chat_chunks()
        chunks.examples = self.brade_prompts.make_example_messages(sitrep)
        chunks.repo = [
            dict(role="user", content=self.brade_prompts.make_repo_content_prefix(sitrep) + self.get_repo_map()),
            dict(role="assistant", content="Understood. I'll keep this repository structure in mind."),
        ]
        chunks.chat_files = [
            dict(role="user", content=self.brade_prompts.make_files_content_prefix(sitrep) + self.get_files_content()),
            dict(role="assistant", content=self.brade_prompts.make_files_content_assistant_reply(sitrep)),
        ]
        chunks.readonly_files = [
            dict(role="user", content=self.brade_prompts.make_read_only_files_prefix(sitrep) + self.get_read_only_files_content()),
            dict(role="assistant", content="I'll use these read-only files as reference."),
        ]
        chunks.reminder = [
            dict(role="system", content=self.brade_prompts.make_system_reminder(sitrep)),
        ]
        return chunks
