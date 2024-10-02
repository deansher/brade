from aider.coders.editblock_coder import EditBlockCoder
from aider.coders.brade_prompts import BradePrompts

class BradeCoder(EditBlockCoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.brade_prompts = BradePrompts()
        self.edit_format = "diff"

    def fmt_system_prompt(self, prompt):
        return self.brade_prompts.make_main_system_prompt(self.done_messages, self.cur_messages)

    def format_chat_chunks(self):
        chunks = super().format_chat_chunks()
        
        # Replace example messages
        chunks.examples = self.brade_prompts.make_example_messages(self.done_messages, self.cur_messages)

        # Replace repo content prefix
        chunks.repo = [
            dict(role="user", content=self.brade_prompts.make_repo_content_prefix(self.done_messages, self.cur_messages) + self.get_repo_map()),
            dict(role="assistant", content="Understood. I'll keep this repository structure in mind."),
        ]

        # Replace files content prefix
        chunks.chat_files = [
            dict(role="user", content=self.brade_prompts.make_files_content_prefix(self.done_messages, self.cur_messages) + self.get_files_content()),
            dict(role="assistant", content=self.brade_prompts.make_files_content_assistant_reply(self.done_messages, self.cur_messages)),
        ]

        # Replace read-only files prefix
        chunks.readonly_files = [
            dict(role="user", content=self.brade_prompts.make_read_only_files_prefix(self.done_messages, self.cur_messages) + self.get_read_only_files_content()),
            dict(role="assistant", content="I'll use these read-only files as reference."),
        ]

        # Replace system reminder
        chunks.reminder = [
            dict(role="system", content=self.brade_prompts.make_system_reminder(self.done_messages, self.cur_messages)),
        ]

        return chunks
