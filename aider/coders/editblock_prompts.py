# flake8: noqa: E501

from .base_prompts import CoderPrompts


class EditBlockPrompts(CoderPrompts):
    shell_cmd_prompt = """
4. *Concisely* suggest any shell commands the user might want to run in ```bash blocks.

Just suggest shell commands this way, not example code.
Only suggest complete shell commands that are ready to execute, without placeholders.
Only suggest at most a few shell commands at a time, not more than 1-3.

Use the appropriate shell based on the user's system info:
{platform}
Examples of when to suggest shell commands:

- If you changed a self-contained html file, suggest an OS-appropriate command to open a 
  browser to view it to see the updated content.
- If you changed a CLI program, suggest the command to run it to see the new behavior.
- If you added a test, suggest how to run it with the testing tool used by the project.
- Suggest OS-appropriate commands to delete or rename files/directories, or other file 
  system operations.
- If your code changes add new dependencies, suggest the command to install them.
- Etc.
"""

    no_shell_cmd_prompt = """
Keep in mind these details about the user's platform and environment:
{platform}
"""
    example_messages = [
        dict(
            role="user",
            content="Change get_factorial() to use math.factorial",
        ),
        dict(
            role="assistant",
            content="""To make this change we need to modify `mathweb/flask/app.py` to:

1. Import the math package.
2. Remove the existing factorial() function.
3. Update get_factorial() to call math.factorial instead.

Here are the *SEARCH/REPLACE* blocks:

mathweb/flask/app.py
{fence[0]}python
<<<<<<< SEARCH
from flask import Flask
=======
import math
from flask import Flask
>>>>>>> REPLACE
{fence[1]}

mathweb/flask/app.py
{fence[0]}python
<<<<<<< SEARCH
def factorial(n):
    "compute factorial"

    if n == 0:
        return 1
    else:
        return n * factorial(n-1)

=======
>>>>>>> REPLACE
{fence[1]}

mathweb/flask/app.py
{fence[0]}python
<<<<<<< SEARCH
    return str(factorial(n))
=======
    return str(math.factorial(n))
>>>>>>> REPLACE
{fence[1]}
""",
        ),
        dict(
            role="user",
            content="Refactor hello() into its own file.",
        ),
        dict(
            role="assistant",
            content="""To make this change we need to modify `main.py` and make a new file 
`hello.py`:

1. Make a new hello.py file with hello() in it.
2. Remove hello() from main.py and replace it with an import.

Here are the *SEARCH/REPLACE* blocks:

hello.py
{fence[0]}python
<<<<<<< SEARCH
=======
def hello():
    "print a greeting"

    print("hello")
>>>>>>> REPLACE
{fence[1]}

main.py
{fence[0]}python
<<<<<<< SEARCH
def hello():
    "print a greeting"

    print("hello")
=======
from hello import hello
>>>>>>> REPLACE
{fence[1]}
""",
        ),
    ]

    system_reminder = """IMPORTANT REMINDER: our "fence" characters vary
from request to request. Right now they are: {fence[0]} and {fence[1]}.
Use these when building SEARCH/REPLACE blocks.
"""

    @property
    def task_instructions(self) -> str:
        """Task-specific instructions for the edit block workflow."""
        return """# SEARCH/REPLACE Block Format

For each change you want to make to a project file, you must provide a *SEARCH/REPLACE* block.
The SEARCH block must match existing content exactly, line-by-line, except in the special case
of creating a new file. The REPLACE block must contain your new or revised content.

 Every SEARCH/REPLACE block must strictly follow this format:

 1. **File Path**
    - Must be the full, relative file path (from project root) on a line by itself immediately *above* the opening fence.
    - No extra characters (quotes, asterisks, etc.) are allowed.

 2. **Code Fence**
    - Use the provided fence format exactly (e.g. `{fence[0]}python` to start and `{fence[1]}` to end).
    - The fence format may be triple backticks (```) or another format like <source>
    - The language specifier (e.g. "python") should match the target file's extension.

 3. **SEARCH Block**
    - Begins with a line exactly reading `<<<<<<< SEARCH`.
    - For existing files, the SEARCH block must match the current file content *exactly* (including whitespace, comments, and indentation).
    - For new files, leave the SEARCH block empty.

 4. **Divider**
    - A single line exactly reading `=======` separates the SEARCH and REPLACE sections.

 5. **REPLACE Block**
    - Contains the new content that will replace the matched text.
    - Ends with a line exactly reading `>>>>>>> REPLACE`.

 # Important Soft Guidelines

 - **Minimal Context:** Use just enough surrounding context (about 5-10 lines) to accurately identify the target text.
 - **Isolated Changes:** Each block should focus on a single logical change; avoid mixing unrelated changes.
 - **Preserve Format:** Do not alter indentation, remove comments, or change spacing unless it's part of the intended edit.
 - **Exact Matching:** The SEARCH part must be a verbatim copy of whole lines of the existing file content.

## Example 1

utils/echo.py
{fence[0]}python
<<<<<<< SEARCH
def echo(msg):
    "print a message"

    print(msg)
=======
def echo(msg):
    "print a message"

    print("Echo: " + msg)
>>>>>>> REPLACE
{fence[1]}

## Special Cases

1. **Creating New File**
   - Use empty SEARCH section
   - Put new content in REPLACE section
   - Use full path from project root

2. **Just Inserting Code**
   - SEARCH section must still match enough context to locate insertion point

3. **Deleting Code**
   - SEARCH section must unambiguously match a region of the file that contains
     the lines to be deleted
   - REPLACE section must omit the lines to be deleted, potentially meaning it is empty

4. **Moving Code**
   - Use two blocks:
     1. Delete from original location
     2. Insert at new location

## Example 2

To make this change we need to modify `main.py` and make a new file
`hello.py`:

1. Make a new hello.py file with hello() in it.
2. Remove hello() from main.py and replace it with an import.

Here are the *SEARCH/REPLACE* blocks:

friendly/output/hello.py
{fence[0]}python
<<<<<<< SEARCH
=======
def hello():
    "print a greeting"

    print("hello")
>>>>>>> REPLACE
{fence[1]}

app/main.py
{fence[0]}python
<<<<<<< SEARCH
def hello():
    "print a greeting"

    print("hello")
=======
from hello import hello
>>>>>>> REPLACE
{fence[1]}
"""
