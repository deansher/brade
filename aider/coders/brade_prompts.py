from aider.coders.base_coder import Coder


class BradePrompts:
    def __init__(self):
        pass

    def make_main_system_prompt(self, done_messages, cur_messages):
        # TODO: Implement this method
        return "You are Brade, an AI assistant."

    def make_example_messages(self, done_messages, cur_messages):
        # TODO: Implement this method
        return []

    def make_repo_content_prefix(self, done_messages, cur_messages):
        # TODO: Implement this method
        return "<SYSTEM> Here's a map of the repository:"

    def make_files_content_prefix(self, done_messages, cur_messages):
        return "<SYSTEM> Here are the contents of the files you can edit:"

    def make_read_only_files_prefix(self, done_messages, cur_messages):
        return "<SYSTEM> Here are the contents of read-only files for reference:"

    def make_files_content_assistant_reply(self, done_messages, cur_messages):
        return "I understand the contents of these files. How can I assist you?"

    def make_system_reminder(self, done_messages, cur_messages):
        # TODO: Implement this method
        return "Remember, you are Brade, an AI assistant focused on helping with coding tasks."
