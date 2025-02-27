# Plan for Simplifying EditBlockCoder's Search/Replace Block Parsing

Brade and Dean are using this document to support their collaborative process. Brade is an AI software engineer collaborating with Dean through the Brade application. We are working together to enhance the Brade application's code. This is an interesting recursive situation where Brade is helping improve her own implementation.

We want to work efficiently in an organized way. For the portions of the code that we must change to meet our functionality goals, we want to move toward beautiful, idiomatic Python code. We also want to move toward more testable code with simple unit tests that cover the most important paths.

This document contains three kinds of material:

- requirements
- specific plans for meeting those requirements
- our findings as we analyze our code along the way

For major step of the work, (each top-level bullet of each "### ( ) task" section) we will follow this process:

- Make sure our plan is current.
- Make sure we have the information we need for our next step.
  - Writing down any new findings in this document.
  - Correct anything we previously misunderstood.
- Make sure existing unit tests pass.
- Consider whether to add unit tests or do manual testing before making the code changes.
- Make the code changes.
- Run the unit tests.
- Manually validate the change.

We only intend for this plan to cover straightforward next steps to our next demonstrable milestone. We'll extend it as we go.

We write down our findings as we go, to build up context for later tasks. When a task requires analysis, we use the section header as the task and write down our findings as that section's content.

For relatively complex tasks that benefit from a prose description of our approach, we use the section header as the task and write down our approach as that section's content. We nest these sections as appropriate.

For simpler tasks that can be naturally specified in a single sentence, we move to bullet points.

We use simple, textual checkboxes at each level of task, both for tasks represented by section headers and for tasks represented by bullets. Like this:

```
### ( ) Complex Task.

- (✅) Subtask
  - (✅) Subsubtask
- ( ) Another subtask
```

## Requirements

The current EditBlockCoder uses complex heuristics to parse search/replace blocks, which has become difficult to maintain. With the stronger LLM models now available, we can simplify this significantly.

### Core Requirements

1. Implement straightforward, strict parsing of search/replace blocks
   - Clear, explicit format requirements for the LLM to follow
   - No complex heuristics or fuzzy matching
   - Simple retry mechanism if parsing fails

2. Maintain backward compatibility where reasonable
   - Keep the existing search/replace block format unchanged
   - Preserve the ability to create new files with empty search sections
   - Continue supporting shell commands

3. Improve error handling
   - Clear, actionable error messages when parsing fails
   - Explicit retry mechanism rather than complex fallback logic

4. Enhance testability
   - Simpler code should be easier to test thoroughly
   - Focus on testing the core parsing logic
   - Add tests for error cases and retry mechanisms

## Tasks

### (✅) Document how this works today.

The edit block functionality is implemented in `editblock_coder.py` and tested in `test_editblock.py`. Each edit block has a file path followed by a body.

#### File Path Requirements

- Must be alone on a line before the opening fence
- Can be stripped of trailing colons, leading #, and surrounding backticks/asterisks
- For new files, an empty SEARCH section is allowed
- The path can be relative to project root
- The path must be valid (either match an existing file or be a new file path)

#### Body Requirements

- Opening fence (e.g. ```python) - language specifier is optional
- "<<<<<<< SEARCH" line (5+ < characters)
- Search content (can be empty for new files)
- "=======" line (5+ = characters)
- Replace content
- ">>>>>>> REPLACE" line (5+ > characters)
- Closing fence (```)

##### Search Content Requirements

- For existing files, must match exactly (including whitespace)
- Exception: The code has special handling for leading whitespace mismatches
- Exception: Can handle "..." lines that match between search and replace sections

#### Multiple Blocks:

- Multiple blocks for the same file are allowed
- Each block is processed independently
- Only the first match in a file is replaced

### (✅) List simplifications that we want to apply as individual refactorings.

1. Improve the `find_filename` function:
   - Simplify the logic for finding filenames
   - Make the function more focused by removing some of the flexible filename matching
   - Add better documentation of what filename formats are actually supported

2. Simplify the `find_original_update_blocks` function:
   - Split into smaller functions for better readability and testability
   - Extract shell command handling into a separate function
   - Extract filename handling into a separate function
   - Improve error handling to be more consistent

3. Improve the `replace_most_similar_chunk` function:
   - Remove the fuzzy matching code that is currently disabled
   - Simplify the function to focus on exact matches and whitespace handling
   - Move the "..." handling to a separate function

4. Improve the `do_replace` function:
   - Simplify the logic for handling new files
   - Make the error handling more consistent
   - Add better documentation of the function's behavior

5. Improve test organization:
   - Group tests by functionality
   - Add more focused unit tests for the smaller functions
   - Add more test cases for error conditions
   - Add tests for the shell command handling

### ( ) Improve the `find_filename` function

### ( ) Simplify the `find_original_update_blocks` function

#### ( ) Extract helper functions for cleaner code organization
- ( ) Extract `process_shell_block` helper to handle shell code blocks
- ( ) Extract `process_edit_block` helper to handle SEARCH/REPLACE blocks
- ( ) Extract `validate_edit_block` helper to check block structure

#### ( ) Improve error handling and messages
- ( ) Add clear error messages for each validation step
- ( ) Use custom exceptions for different error types
- ( ) Add context to error messages (line numbers, relevant content)

#### ( ) Simplify the main loop logic
- ( ) Reduce nesting depth in main loop
- ( ) Use early returns to handle special cases
- ( ) Clarify the block parsing state machine

#### ( ) Improve documentation
- ( ) Add clear docstrings explaining block format requirements
- ( ) Document error conditions and handling
- ( ) Add examples in docstrings showing valid formats