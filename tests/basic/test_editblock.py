# flake8: noqa: E501

import tempfile
import unittest
from pathlib import Path
import diff_match_patch

from aider.coders import Coder
from aider.coders import editblock_coder as eb
from aider.coders.editblock_coder import SearchReplaceBlockParseError
from aider.io import InputOutput
from aider.models import _ModelConfigImpl


class TestUtils(unittest.TestCase):
    """Test suite for editblock_coder.py focusing on key behaviors.

    Our testing strategy focuses on three essential aspects:

    1. Success Cases:
       - Verify that exact matches work correctly
       - Confirm only first occurrence is replaced
       - Test with representative real-world content

    2. Failure Cases:
       - Verify that similarity below 0.95 triggers failure
       - Test with realistic transcription errors
       - Confirm even minor differences fail

    3. Parsing Tests:
       - Verify filename extraction and validation
       - Test edit block parsing and validation
       - Confirm proper handling of edge cases

    Design Decision:
    We intentionally use raw diff-match-patch with a strict 0.95 similarity threshold.
    Any case that produces similarity below 0.95 (even when differences are just
    whitespace) raises a ValueError. This enforces our requirement that the LLM must
    be highly accurate in its transcription of existing code.
    """

    def setUp(self):
        self.GPT35 = _ModelConfigImpl("gpt-3.5-turbo")

    def test_strip_filename(self):
        # Test basic cases
        self.assertEqual(eb.strip_filename("file.py"), "file.py")
        self.assertEqual(eb.strip_filename(" file.py "), "file.py")

        # Test individual removals
        self.assertEqual(eb.strip_filename("#file.py"), "file.py")
        self.assertEqual(eb.strip_filename("file.py:"), "file.py")
        self.assertEqual(eb.strip_filename("`file.py`"), "file.py")

        # Test combinations
        self.assertEqual(eb.strip_filename("#file.py:"), "file.py")
        self.assertEqual(eb.strip_filename("# `file.py`"), "file.py")
        self.assertEqual(eb.strip_filename("# `file.py:"), "`file.py")

        # Test empty results
        self.assertEqual(eb.strip_filename(""), "")
        self.assertEqual(eb.strip_filename("  "), "")

    def test_find_filepath(self):
        # Test with valid_fnames provided
        valid_fnames = ["file1.py", "dir/file2.py", "path/to/file3.py"]

        # Test exact matches
        self.assertEqual(eb.find_filepath("file1.py", valid_fnames), "file1.py")
        self.assertEqual(eb.find_filepath("dir/file2.py", valid_fnames), "dir/file2.py")

        # Test basename matches
        self.assertEqual(eb.find_filepath("file2.py", valid_fnames), "dir/file2.py")
        self.assertEqual(eb.find_filepath("file3.py", valid_fnames), "path/to/file3.py")

        # Test with strippable characters
        self.assertEqual(eb.find_filepath("#file1.py:", valid_fnames), "file1.py")
        self.assertEqual(
            eb.find_filepath("`dir/file2.py`", valid_fnames), "dir/file2.py"
        )

        # Test no matches
        with self.assertRaises(eb.FileNotInContextError):
            eb.find_filepath("nonexistent.py", valid_fnames)
        self.assertIsNone(eb.find_filepath("", valid_fnames))

        # Test without valid_fnames
        self.assertEqual(eb.find_filepath("newfile.py", None), "newfile.py")
        self.assertEqual(
            eb.find_filepath("path/to/newfile.py", None), "path/to/newfile.py"
        )
        self.assertIsNone(eb.find_filepath("invalid", None))  # No extension

    def test_strip_quoted_wrapping(self):
        input_text = "filename.ext\n```\nWe just want this content\nNot the filename and triple quotes\n```"
        expected_output = (
            "We just want this content\nNot the filename and triple quotes\n"
        )
        result = eb.strip_quoted_wrapping(input_text, "filename.ext")
        self.assertEqual(result, expected_output)

    def test_strip_quoted_wrapping_no_filename(self):
        input_text = "```\nWe just want this content\nNot the triple quotes\n```"
        expected_output = "We just want this content\nNot the triple quotes\n"
        result = eb.strip_quoted_wrapping(input_text)
        self.assertEqual(result, expected_output)

    def test_strip_quoted_wrapping_no_wrapping(self):
        input_text = "We just want this content\nNot the triple quotes\n"
        expected_output = "We just want this content\nNot the triple quotes\n"
        result = eb.strip_quoted_wrapping(input_text)
        self.assertEqual(result, expected_output)

    def test_find_original_update_blocks_basic(self):
        edit = (
            "\nHere's the change:\n\n"
            "foo.txt\n"
            "```text\n"
            "<<<<<<< SEARCH\n"
            "def calculate_total(numbers):\n"
            "    total = 0\n"
            "    for num in numbers:\n"
            "        total += num\n"
            "    return total\n"
            "=======\n"
            "def calculate_total(numbers):\n"
            "    return sum(numbers)\n"
            ">>>>>>> REPLACE\n"
            "```\n\n"
            "Hope you like it!\n"
        )
        edits = list(eb.find_original_update_blocks(edit))
        self.assertEqual(
            edits,
            [
                (
                    "foo.txt",
                    "def calculate_total(numbers):\n"
                    "    total = 0\n"
                    "    for num in numbers:\n"
                    "        total += num\n"
                    "    return total\n",
                    "def calculate_total(numbers):\n" "    return sum(numbers)\n",
                )
            ],
        )

    def test_find_original_update_blocks_shell_commands(self):
        edit = (
            "\nHere's what to do:\n\n"
            "```bash\n"
            'echo "Hello"\n'
            "mv old.txt new.txt\n"
            "```\n\n"
            "And then this change:\n\n"
            "foo.txt\n"
            "```text\n"
            "<<<<<<< SEARCH\n"
            "Two\n"
            "=======\n"
            "Tooooo\n"
            ">>>>>>> REPLACE\n"
            "```\n"
        )
        edits = list(eb.find_original_update_blocks(edit))
        self.assertEqual(len(edits), 2)
        self.assertEqual(edits[0], (None, 'echo "Hello"\nmv old.txt new.txt\n'))
        self.assertEqual(edits[1], ("foo.txt", "Two\n", "Tooooo\n"))

    def test_find_original_update_blocks_new_file(self):
        edit = (
            "\nCreate a new file:\n\n"
            "path/to/new_module.py\n"
            "```text\n"
            "<<<<<<< SEARCH\n"
            "=======\n"
            "def main():\n"
            '    """Print a friendly greeting."""\n'
            '    print("Welcome to the application!")\n'
            "    return 0\n\n"
            'if __name__ == "__main__":\n'
            "    main()\n"
            ">>>>>>> REPLACE\n"
            "```\n"
        )
        edits = list(eb.find_original_update_blocks(edit))
        self.assertEqual(
            edits,
            [
                (
                    "path/to/new_module.py",
                    "",
                    (
                        "def main():\n"
                        '    """Print a friendly greeting."""\n'
                        '    print("Welcome to the application!")\n'
                        "    return 0\n\n"
                        'if __name__ == "__main__":\n'
                        "    main()\n"
                    ),
                )
            ],
        )

    def test_new_file_creation(self):
        """Test that EditBlockCoder correctly creates new files through its normal flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set up EditBlockCoder instance
            new_file = Path(tmpdir) / "new_file.txt"
            coder = Coder.create(self.GPT35, "diff", io=InputOutput(), fnames=[])

            # Simulate assistant response with new file block
            coder.partial_response_content = (
                f"{new_file}\n"
                "```text\n"
                "<<<<<<< SEARCH\n"
                "=======\n"
                "Hello, World!\n"
                ">>>>>>> REPLACE\n"
                "```\n"
            )
            coder.partial_response_function_call = dict()

            # Process the edit through normal flow
            edits = coder.get_edits()
            coder.apply_edits(edits)

            # Verify file was created with correct content
            self.assertTrue(new_file.exists())
            self.assertEqual(new_file.read_text(), "Hello, World!\n")

            # Verify final outcome shows the file creation
            final_outcome = coder.get_final_editor_outcome()
            self.assertIn("Here are all the changes that were successfully applied:", final_outcome)
            self.assertIn("Hello, World!", final_outcome)

    def test_get_final_outcome_no_changes(self):
        """Test that get_final_editor_outcome() correctly reports when no changes were made."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set up EditBlockCoder instance
            file1 = Path(tmpdir) / "file1.txt"
            with open(file1, "w", encoding="utf-8") as f:
                f.write("original content\n")

            coder = Coder.create(self.GPT35, "diff", io=InputOutput(), fnames=[str(file1)])

            # Run with no changes
            coder.run(with_message="hi")

            # Verify final outcome indicates no changes
            final_outcome = coder.get_final_editor_outcome()
            self.assertIn("No changes were applied", final_outcome)

    def test_get_final_outcome_partial_failures(self):
        """Test that get_final_editor_outcome() correctly reports both successes and failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set up test files
            file1 = Path(tmpdir) / "file1.txt"
            with open(file1, "w", encoding="utf-8") as f:
                f.write("one\ntwo\nthree\n")

            coder = Coder.create(self.GPT35, "diff", io=InputOutput(), fnames=[str(file1)])

            # Simulate one successful and one failed edit
            coder.partial_response_content = (
                f"{file1}\n"
                "```text\n"
                "<<<<<<< SEARCH\n"
                "two\n"
                "=======\n"
                "new\n"
                ">>>>>>> REPLACE\n"
                "```\n\n"
                f"{file1}\n"
                "```text\n"
                "<<<<<<< SEARCH\n"
                "does not exist\n"
                "=======\n"
                "will fail\n"
                ">>>>>>> REPLACE\n"
                "```\n"
            )
            coder.partial_response_function_call = dict()

            # Process the edits
            edits = coder.get_edits()
            try:
                coder.apply_edits(edits)
            except EditBlockError:
                pass  # Expected due to the failing block

            # Verify final outcome shows both success and failure
            final_outcome = coder.get_final_editor_outcome()
            self.assertIn("Here are all the changes that were successfully applied:", final_outcome)
            self.assertIn("two\n", final_outcome)  # Successful edit
            self.assertIn("new\n", final_outcome)  # Successful edit
            self.assertIn("1 SEARCH/REPLACE block(s) failed to match", final_outcome)

    def test_find_original_update_blocks_validation(self):
        # Test missing filename
        edit = (
            "```text\n"
            "<<<<<<< SEARCH\n"
            "Two\n"
            "=======\n"
            "Tooooo\n"
            ">>>>>>> REPLACE\n"
            "```"
        )
        with self.assertRaises(SearchReplaceBlockParseError) as cm:
            list(eb.find_original_update_blocks(edit))
        self.assertIn("filename", str(cm.exception))

        # Test unclosed block
        edit = "foo.txt\n" "```text\n" "<<<<<<< SEARCH\n" "Two\n" "=======\n" "Tooooo\n"
        with self.assertRaises(SearchReplaceBlockParseError) as cm:
            list(eb.find_original_update_blocks(edit))
        self.assertIn(
            "Block starting at line 3 has SEARCH and DIVIDER but is missing REPLACE marker",
            str(cm.exception),
        )

        # Test missing fence
        edit = (
            "foo.txt\n"
            "<<<<<<< SEARCH\n"
            "Two\n"
            "=======\n"
            "Tooooo\n"
            ">>>>>>> REPLACE\n"
        )
        with self.assertRaises(SearchReplaceBlockParseError) as cm:
            list(eb.find_original_update_blocks(edit))
        self.assertIn("must begin with a filename and a fence", str(cm.exception))

        # Test out of order markers
        edit = (
            "foo.txt\n"
            "```text\n"
            "=======\n"
            "Two\n"
            "<<<<<<< SEARCH\n"
            "Tooooo\n"
            ">>>>>>> REPLACE\n"
            "```"
        )
        with self.assertRaises(SearchReplaceBlockParseError) as cm:
            list(eb.find_original_update_blocks(edit))
        self.assertIn("not preceded by SEARCH marker", str(cm.exception))

        # Test incomplete block
        edit = "foo.txt\n" "```text\n" "<<<<<<< SEARCH\n" "Two\n" "=======\n" "```"
        with self.assertRaises(SearchReplaceBlockParseError) as cm:
            list(eb.find_original_update_blocks(edit))
        self.assertIn("missing REPLACE marker", str(cm.exception))

        # Test duplicate SEARCH
        edit = (
            "foo.txt\n"
            "```text\n"
            "<<<<<<< SEARCH\n"
            "Two\n"
            "<<<<<<< SEARCH\n"
            "=======\n"
            "Tooooo\n"
            ">>>>>>> REPLACE\n"
            "```"
        )
        with self.assertRaises(SearchReplaceBlockParseError) as cm:
            list(eb.find_original_update_blocks(edit))
        self.assertIn("previous block was not complete", str(cm.exception))

    def test_find_original_update_blocks_no_final_newline(self):
        edit = (
            "\n"
            "aider/coder.py\n"
            "```python\n"
            "<<<<<<< SEARCH\n"
            '            self.console.print("[red]^C again to quit")\n'
            "=======\n"
            '            self.io.tool_error("^C again to quit")\n'
            ">>>>>>> REPLACE\n"
            "```\n\n"
            "aider/coder.py\n"
            "```python\n"
            "<<<<<<< SEARCH\n"
            '            self.io.tool_error("Malformed ORIGINAL/UPDATE blocks, retrying...")\n'
            "            self.io.tool_error(err)\n"
            "=======\n"
            '            self.io.tool_error("Malformed ORIGINAL/UPDATE blocks, retrying...")\n'
            "            self.io.tool_error(str(err))\n"
            ">>>>>>> REPLACE\n\n"
            "aider/coder.py\n"
            "```python\n"
            "<<<<<<< SEARCH\n"
            '            self.console.print("[red]Unable to get commit message from gpt-3.5-turbo. Use /commit to try again.\\n")\n'
            "=======\n"
            '            self.io.tool_error("Unable to get commit message from gpt-3.5-turbo. Use /commit to try again.")\n'
            ">>>>>>> REPLACE\n"
            "```\n\n"
            "aider/coder.py\n"
            "```python\n"
            "<<<<<<< SEARCH\n"
            '            self.console.print("[red]Skipped commit.")\n'
            "=======\n"
            '            self.io.tool_error("Skipped commit.")\n'
            ">>>>>>> REPLACE\n"
            "```"
        )

        # Should not raise a ValueError
        list(eb.find_original_update_blocks(edit))

    def test_incomplete_edit_block_missing_filename(self):
        edit = (
            "\nNo problem! Here are the changes to patch `subprocess.check_output` "
            "instead of `subprocess.run` in both tests:\n\n"
            "tests/test_repomap.py\n"
            "```python\n"
            "<<<<<<< SEARCH\n"
            "    def test_check_for_ctags_failure(self):\n"
            '        with patch("subprocess.run") as mock_run:\n'
            '            mock_run.side_effect = Exception("ctags not found")\n'
            "=======\n"
            "    def test_check_for_ctags_failure(self):\n"
            '        with patch("subprocess.check_output") as mock_check_output:\n'
            '            mock_check_output.side_effect = Exception("ctags not found")\n'
            ">>>>>>> REPLACE\n"
            "```\n\n"
            "tests/test_repomap.py\n"
            "```python\n"
            "<<<<<<< SEARCH\n"
            "    def test_check_for_ctags_success(self):\n"
            '        with patch("subprocess.run") as mock_run:\n'
            '            mock_run.return_value = CompletedProcess(args=["ctags", "--version"], returncode=0, stdout=\'\'\'{'
            + "\n"
            '  "_type": "tag",\n'
            '  "name": "status",\n'
            '  "path": "aider/main.py",\n'
            '  "pattern": "/^    status = main()$/",\n'
            '  "kind": "variable"\n'
            "}''')\n"
            "=======\n"
            "    def test_check_for_ctags_success(self):\n"
            '        with patch("subprocess.check_output") as mock_check_output:\n'
            "            mock_check_output.return_value = '''{" + "\n"
            '  "_type": "tag",\n'
            '  "name": "status",\n'
            '  "path": "aider/main.py",\n'
            '  "pattern": "/^    status = main()$/",\n'
            '  "kind": "variable"\n'
            "}'''\n"
            ">>>>>>> REPLACE\n"
            "```\n\n"
            "These changes replace the `subprocess.run` patches with `subprocess.check_output` "
            "patches in both `test_check_for_ctags_failure` and `test_check_for_ctags_success` tests.\n"
        )

    def test_exact_match_replaces_first_occurrence_only(self):
        """Verify exact match replacement behavior.

        This test is our primary success case, validating two key requirements:
        1. An exact match is correctly identified and replaced
        2. Only the first occurrence is modified

        The test uses realistic Python code with type hints and docstrings to
        represent typical content that the LLM would process.
        """
        whole = (
            "def validate_user(user_id: str) -> bool:\n"
            "    return check_permissions(user_id)\n\n"
            "def process_data(data: dict) -> None:\n"
            "    pass\n\n"
            "def validate_user(user_id: str) -> bool:\n"
            "    return True  # Duplicate for testing\n"
        )
        part = "def validate_user(user_id: str) -> bool:\n    return check_permissions(user_id)\n"
        replace = "def validate_user(user_id: str) -> bool:\n    return is_authorized(user_id)\n"

        result = eb.replace_most_similar_chunk(whole, part, replace)

        # Verify first occurrence was replaced
        self.assertIn("return is_authorized(user_id)", result)
        # Verify second occurrence was not changed
        self.assertIn("return True  # Duplicate for testing", result)

    def test_full_edit(self):
        # Create a few temporary files
        _, file1 = tempfile.mkstemp()

        with open(file1, "w", encoding="utf-8") as f:
            f.write("one\n" "two\n" "three\n")

        files = [file1]

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(self.GPT35, "diff", io=InputOutput(), fnames=files)

        def mock_send(*args, **kwargs):
            coder.partial_response_content = (
                "\nDo this:\n\n"
                f"{Path(file1).name}\n"
                "```text\n"
                "<<<<<<< SEARCH\n"
                "two\n"
                "=======\n"
                "new\n"
                ">>>>>>> REPLACE\n"
                "```\n"
            )
            coder.partial_response_function_call = dict()
            return []

        coder.send = mock_send

        # Call the run method with a message
        coder.run(with_message="hi")

        content = Path(file1).read_text(encoding="utf-8")
        self.assertEqual(content, "one\n" "new\n" "three\n")

    def test_get_final_outcome_no_changes(self):
    # Verify final outcome shows the edit would have been made
        final_outcome = coder.get_final_editor_outcome()
        self.assertIn("Here are all the changes that were successfully applied:", final_outcome)
        self.assertIn("two\n", final_outcome)
        self.assertIn("new\n", final_outcome)

    def test_get_final_outcome_no_changes(self):
        """Test that get_final_editor_outcome() correctly reports when no changes were made."""
        # Create a temporary file
        _, file1 = tempfile.mkstemp()
        with open(file1, "w", encoding="utf-8") as f:
            f.write("test content\n")

        # Initialize coder with the file
        coder = Coder.create(self.GPT35, "diff", io=InputOutput(), fnames=[file1])

        # Run with no changes
        coder.run(with_message="hi")

        # Verify outcome indicates no changes
        final_outcome = coder.get_final_editor_outcome()
        self.assertEqual(final_outcome, "No changes were applied")

    def test_get_final_outcome_partial_failures(self):
        """Test that get_final_editor_outcome() shows only successful changes."""
        # Create test files
        _, file1 = tempfile.mkstemp()
        _, file2 = tempfile.mkstemp()
        with open(file1, "w", encoding="utf-8") as f:
            f.write("one\ntwo\nthree\n")
        with open(file2, "w", encoding="utf-8") as f:
            f.write("alpha\nbeta\ngamma\n")

        # Initialize coder
        coder = Coder.create(
            self.GPT35,
            "diff",
            io=InputOutput(),
            fnames=[file1, file2],
        )

        # Mock a response with one success and one failure
        def mock_send(*args, **kwargs):
            coder.partial_response_content = (
                f"{Path(file1).name}\n"
                "```python\n"
                "<<<<<<< SEARCH\n"
                "two\n"
                "=======\n"
                "new\n"
                ">>>>>>> REPLACE\n"
                "```\n\n"
                f"{Path(file2).name}\n"
                "```python\n"
                "<<<<<<< SEARCH\n"
                "does not exist\n"
                "=======\n"
                "will fail\n"
                ">>>>>>> REPLACE\n"
                "```\n"
            )
            coder.partial_response_function_call = dict()
            return []

        coder.send = mock_send

        # Run the coder
        coder.run(with_message="hi")

        # Verify final outcome shows only the successful change
        final_outcome = coder.get_final_editor_outcome()
        self.assertIn("Here are all the changes that were successfully applied:", final_outcome)
        self.assertIn("two\n", final_outcome)
        self.assertIn("new\n", final_outcome)
        self.assertNotIn("does not exist", final_outcome)
        self.assertNotIn("will fail", final_outcome)

    def test_repeated_edit_attempts(self):
        """Test that get_final_editor_outcome() shows only final successful changes."""
        # Create a test file
        _, file1 = tempfile.mkstemp()
        with open(file1, "w", encoding="utf-8") as f:
            f.write("one\ntwo\nthree\n")

        # Initialize coder
        coder = Coder.create(
            self.GPT35,
            "diff",
            io=InputOutput(dry_run=True),
            fnames=[file1],
            dry_run=True,
        )

        # Track multiple attempts on the same block
        coder.applied_changes = [
            {
                "path": Path(file1).name,
                "original": "two\n",
                "updated": "new\n",
                "retry_attempt": 0,
            },
            {
                "path": Path(file1).name,
                "original": "new\n",
                "updated": "newer\n",
                "retry_attempt": 1,
            },
        ]

        # Verify final outcome shows all successful changes in order
        final_outcome = coder.get_final_editor_outcome()
        self.assertIn("Here are all the changes that were successfully applied:", final_outcome)
        self.assertIn("two\n", final_outcome)  # Original content
        self.assertIn("new\n", final_outcome)  # First change
        self.assertIn("newer\n", final_outcome)  # Second change

    def test_find_original_update_blocks_multiple_same_file(self):
        edit = (
            "\nHere's the change:\n\n"
            "foo.txt\n"
            "```text\n"
            "<<<<<<< SEARCH\n"
            "one\n"
            "=======\n"
            "two\n"
            ">>>>>>> REPLACE\n\n"
            "...\n\n"
            "foo.txt\n"
            "```text\n"
            "<<<<<<< SEARCH\n"
            "three\n"
            "=======\n"
            "four\n"
            ">>>>>>> REPLACE\n"
            "```\n\n"
            "Hope you like it!\n"
        )

    def test_new_file_created_in_same_folder(self):
        edit = (
            "\n"
            "Here's the change:\n\n"
            "path/to/a/file2.txt\n"
            "```python\n"
            "<<<<<<< SEARCH\n"
            "=======\n"
            "three\n"
            ">>>>>>> REPLACE\n"
            "```\n\n"
            "another change\n\n"
            "path/to/a/file1.txt\n"
            "```python\n"
            "<<<<<<< SEARCH\n"
            "one\n"
            "=======\n"
            "two\n"
            ">>>>>>> REPLACE\n"
            "```\n\n"
            "Hope you like it!\n"
        )

        edits = list(
            eb.find_original_update_blocks(edit, valid_fnames=["path/to/a/file1.txt"])
        )
        self.assertEqual(
            edits,
            [
                ("path/to/a/file2.txt", "", "three\n"),
                ("path/to/a/file1.txt", "one\n", "two\n"),
            ],
        )

    REALISTIC_CODE = '''def validate_user(user_id: str, permissions: dict) -> bool:
    """Check if user has required permissions.
    
    Args:
        user_id: Unique identifier for the user
        permissions: Dict mapping permission names to boolean values
        
    Returns:
        True if user has all required permissions, False otherwise
    """
    if not isinstance(permissions, dict):
        raise TypeError("permissions must be a dict")
        
    required = {
        "read": True,
        "write": True,
        "admin": False
    }
    
    # Check each required permission
    for perm_name, perm_required in required.items():
        if perm_required and not permissions.get(perm_name, False):
            return False
            
    return True
'''

    def test_search_allows_minor_whitespace_differences(self):
        """Test that minor whitespace differences are allowed.

        The LLM often introduces small whitespace variations when transcribing code:
        - Extra spaces around operators
        - Different line breaks in long lines
        - Slightly different indentation

        These should still match as long as they don't change the code's meaning.
        """
        whole = self.REALISTIC_CODE
        # Introduce typical LLM whitespace variations:
        # - Extra space after function name
        # - Extra newline in docstring
        # - Extra space in type hint
        part = self.REALISTIC_CODE.replace(
            "def validate_user(user_id: str,", "def validate_user (user_id:  str,"
        ).replace("Args:\n", "Args:\n\n")
        replace = self.REALISTIC_CODE.replace("validate_user", "check_permissions")

        # Should succeed since differences are just whitespace
        result = eb.replace_most_similar_chunk(whole, part, replace)
        self.assertIn("check_permissions", result)

    def test_search_allows_minor_comment_differences(self):
        """Test that minor comment differences are allowed.

        The LLM sometimes makes small errors when transcribing comments:
        - Missing periods at end
        - Different line wrapping
        - Slightly different wording

        These should still match since they don't affect the code's behavior.
        """
        whole = self.REALISTIC_CODE
        # Introduce typical LLM comment variations:
        # - Missing period in docstring
        # - Different line wrapping
        part = self.REALISTIC_CODE.replace(
            "Returns:\n        True if user has all required permissions, False otherwise",
            "Returns:\n        True if user has all required permissions,\n        False otherwise.",
        )
        replace = self.REALISTIC_CODE.replace("validate_user", "check_permissions")

        # Should succeed since differences are just in comments
        result = eb.replace_most_similar_chunk(whole, part, replace)
        self.assertIn("check_permissions", result)

    def test_search_rejects_content_changes(self):
        """Test that substantial code content SEARCH mismatches are rejected."""
        whole = self.REALISTIC_CODE
        # Change actual code content by inserting several lines
        part = self.REALISTIC_CODE.replace(
            "    # Check each required permission\n",
            "    # Check each required permission\n"
            "    # First validate input types\n"
            "    if not isinstance(user_id, str):\n"
            "        raise TypeError('user_id must be a string')\n"
            "\n",
        )
        replace = self.REALISTIC_CODE.replace("validate_user", "check_permissions")

        with self.assertRaises(eb.NoExactMatchError) as cm:
            eb.replace_most_similar_chunk(whole, part, replace)
        self.assertIn("SEARCH/REPLACE block failed", str(cm.exception))

    def test_search_rejects_ambiguous_matches(self):
        """Test that ambiguous matches are rejected.

        If a search block could match multiple places in the file:
        - Common helper function
        - Repeated boilerplate
        - Generic error handling

        These should be rejected since we can't be sure which match the LLM intended.
        """
        # Create content with two identical functions
        whole = self.REALISTIC_CODE + "\n\n" + self.REALISTIC_CODE
        # Search for just the function signature, which appears twice
        part = "def validate_user(user_id: str, permissions: dict) -> bool:\\n"
        replace = "def check_permissions(user_id: str, permissions: dict) -> bool:\\n"

        with self.assertRaises(eb.MultipleMatchesError) as cm:
            eb.replace_most_similar_chunk(whole, part, replace)
        self.assertIn("SEARCH/REPLACE block failed", str(cm.exception))

    def test_find_match_end(self):
        """Test the find_match_end function.

        This test verifies that find_match_end correctly identifies where a match ends
        in various scenarios including:
        - Basic exact matches
        - Matches with nearby insertions/deletions
        - Matches at start/end of text
        - Edge cases like empty strings
        """
        dmp = diff_match_patch.diff_match_patch()

        # Test basic exact match
        whole = "prefix abc suffix"
        match_index = 7  # start of "abc"
        original = "abc"
        self.assertEqual(
            eb.find_match_end(dmp, whole, match_index, original), 10  # end of "abc"
        )

        # Test match with deletion right after
        whole = "prefix abcsuffix"  # missing space
        match_index = 7
        original = "abc "  # note trailing space
        self.assertEqual(
            eb.find_match_end(dmp, whole, match_index, original),
            10,  # still end of "abc"
        )

        # Test match with insertion right after
        whole = "prefix abc  suffix"  # extra space
        match_index = 7
        original = "abc"
        self.assertEqual(
            eb.find_match_end(dmp, whole, match_index, original), 10  # end of "abc"
        )

        # Test match at start
        whole = "abc suffix"
        match_index = 0
        original = "abc"
        self.assertEqual(
            eb.find_match_end(dmp, whole, match_index, original), 3  # length of "abc"
        )

        # Test match at end
        whole = "prefix abc"
        match_index = 7
        original = "abc"
        self.assertEqual(
            eb.find_match_end(dmp, whole, match_index, original), 10  # end of string
        )

    def test_build_failed_edit_error_message_candidate_found(self):
        """Test error message generation when a similar candidate is found.

        This test verifies that when a SEARCH block fails to match exactly but a similar
        candidate is found, the error message includes:
        1. The correct error type header
        2. The similarity percentage
        3. A unified diff showing the differences
        """
        original = "def foo():\n    return 42\n"
        updated = "def foo():\n    return 43\n"
        # File content is almost the same as the original (extra space before 42) to trigger a candidate match.
        file_content = "def foo():\n    return  42\n"

        class FakeIO:
            def read_text(self, fname):
                return file_content

        from aider.coders import editblock_coder as eb

        dummy = eb.EditBlockCoder.__new__(eb.EditBlockCoder)
        dummy.io = FakeIO()
        dummy.fence = ("```", "```")
        dummy.abs_root_path = lambda path: path
        failed = [
            {
                "path": "dummy.py",
                "original": original,
                "updated": updated,
                "error_type": "no_match",
                "error_context": "No successful do_replace result on any file.",
            }
        ]
        passed = []
        message = dummy._build_failed_edit_error_message(failed, passed)
        self.assertIn(
            "## SearchReplaceNo_Match: The no_match error occurred in dummy.py", message
        )
        self.assertIn("Detected similarity:", message)
        self.assertIn("Here's a diff to help you diagnose this:", message)
        self.assertNotIn("Warning:", message)

    def test_build_failed_edit_error_message_no_candidate(self):
        """Test error message generation when no similar candidate is found.

        This test verifies that when a SEARCH block fails to match and no similar
        content is found, the error message:
        1. Uses the correct error type header
        2. Indicates no similar content was found
        3. Includes appropriate guidance
        """
        original = "def foo():\n    return 42\n"
        updated = "def foo():\n    return 43\n"
        file_content = "completely different content with no similar candidate\n"

        class FakeIO:
            def read_text(self, fname):
                return file_content

        from aider.coders import editblock_coder as eb

        dummy = eb.EditBlockCoder.__new__(eb.EditBlockCoder)
        dummy.io = FakeIO()
        dummy.fence = ("```", "```")
        dummy.abs_root_path = lambda path: path
        failed = [
            {
                "path": "dummy.py",
                "original": original,
                "updated": updated,
                "error_type": "no_match",
                "error_context": "No successful do_replace result on any file.",
            }
        ]
        passed = [("dummy.py", original, updated)]
        message = dummy._build_failed_edit_error_message(failed, passed)
        self.assertIn(
            "## SearchReplaceNo_Match: The no_match error occurred in dummy.py", message
        )
        self.assertIn("The differences appear to be substantial, or the content may not exist in this file.", message)
        self.assertIn("Only resend fixed versions of the", message)

    def test_build_failed_edit_error_message_with_replace_exists_warning(self):
        """Test error message generation when REPLACE content already exists.

        This test verifies that when the REPLACE block content already exists in the
        target file, the error message includes:
        1. The appropriate warning about duplicate content
        2. Guidance about verifying if the change is still needed
        """
        original = "def foo():\n    return 42\n"
        updated = """def process_data(data: dict) -> None:
    '''Process input data with careful validation.
    
    Args:
        data: The input dictionary to process
        
    Raises:
        ValueError: If data is invalid
        RuntimeError: If processing fails
    '''
    if not isinstance(data, dict):
        raise TypeError("data must be dict")
        
    if not data:
        raise ValueError("data cannot be empty")
        
    # Process each field
    for key, value in data.items():
        validate_field(key, value)
        transform_field(key, value)
"""
        # File content includes the updated block content to trigger the warning
        file_content = (
            "def foo():\n    return 42\nadditional content\n"
            + updated
            + "\nmore content\n"
        )

        class FakeIO:
            def read_text(self, fname):
                return file_content

        from aider.coders import editblock_coder as eb

        dummy = eb.EditBlockCoder.__new__(eb.EditBlockCoder)
        dummy.io = FakeIO()
        dummy.fence = ("```", "```")
        dummy.abs_root_path = lambda path: path
        failed = [
            {
                "path": "dummy.py",
                "original": original,
                "updated": updated,
                "error_type": "no_match",
                "error_context": "No successful do_replace result on any file.",
            }
        ]
        passed = []
        message = dummy._build_failed_edit_error_message(failed, passed)
        self.assertIn(
            "Warning: The REPLACE block content already exists in dummy.py.\nPlease confirm if the SEARCH/REPLACE block is still needed.",
            message,
        )

    def test_calculate_text_similarity_exact_match(self):
        """Test that identical texts have similarity 1.0."""
        text = "def validate_user(user_id: str) -> bool:\n    return check_permissions(user_id)\n"
        from aider.coders import editblock_coder as eb

        self.assertEqual(eb.calculate_text_similarity(text, text), 1.0)

    def test_calculate_text_similarity_whitespace_variations(self):
        """Test that minor whitespace differences still give high similarity."""
        text1 = "def validate_user(user_id: str) -> bool:\n    return check_permissions(user_id)\n"
        text2 = "def validate_user (user_id:  str) -> bool:\n    return check_permissions(user_id)\n"
        from aider.coders import editblock_coder as eb

        self.assertGreater(eb.calculate_text_similarity(text1, text2), 0.95)

    def test_calculate_text_similarity_minor_differences(self):
        """Test that typical LLM transcription errors still give high similarity."""
        text1 = "def process_data(data: dict) -> None:\n    # Process the input data\n    result = transform(data)\n"
        text2 = "def process_data(data: dict) -> None:\n    # Process input data\n    result = transform(data)\n"
        from aider.coders import editblock_coder as eb

        self.assertGreater(eb.calculate_text_similarity(text1, text2), 0.95)

    def test_calculate_text_similarity_major_differences(self):
        """Test that significant content changes give low similarity."""
        text1 = "def process_data(data: dict) -> None:\n    result = transform(data)\n"
        text2 = "def validate_input(data: dict) -> bool:\n    return is_valid(data)\n"
        from aider.coders import editblock_coder as eb

        self.assertLess(eb.calculate_text_similarity(text1, text2), 0.5)

    def test_calculate_text_similarity_edge_cases(self):
        """Test edge cases like empty strings."""
        from aider.coders import editblock_coder as eb

        # Empty strings
        self.assertEqual(eb.calculate_text_similarity("", ""), 1.0)
        self.assertEqual(eb.calculate_text_similarity("some text", ""), 0.0)
        self.assertEqual(eb.calculate_text_similarity("", "some text"), 0.0)
        # Single character differences
        self.assertGreater(eb.calculate_text_similarity("a", "b"), 0.0)
        self.assertEqual(eb.calculate_text_similarity("a", "a"), 1.0)


if __name__ == "__main__":
    unittest.main()
