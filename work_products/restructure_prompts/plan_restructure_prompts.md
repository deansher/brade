# Plan for Restructuring Brade's Prompts

Brade and Dean are using this document to support their collaborative process. Brade is an AI software engineer collaborating with Dean through the Brade application. We are working together to enhance the Brade application's code - specifically its prompt system. This is an interesting recursive situation where Brade is helping improve her own implementation.

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

- (✔︎) Subtask
  - (✔︎) Subsubtask
- ( ) Another subtask
```

## Requirements

- Restructure our prompts to optimize for Claude 3.5 Sonnet v2.
- Follow the guidelines in [Claude 3.5 Prompting Guide](../anthropic_docs/claude_prompting_guide.md).
- Structure our final user message for each completion call as follows:
  - An opening sentence that tells the model to expect supporting material followed by the user's message.
  - Supporting material organized as simple XML.
  - The user's message.
- Drop the `<SYSTEM>` markers we currently use.
- Improve clarity of prompt contents.
- Improve the overall flow of prompts and content across the chat message sequence, to make it
  easier for the model to understand what is going on.

### New Message Structure

Aider's existing code generates a sequence of system messages, user messages, and assistant messages as its prompt to the LLM. Some of these messages come directly from the history of user and assistant messages in the chat. But there are many others.  The sequence of prompt messages is constructed by `BaseCoder.format_chat_chunks` in collaboration with `ChatChunks`.

We will do this differently. Our message sequence will be much simpler:

- A single system message designed according to Anthropic's prompt recommendations for Claude models.
- `Coder.done_messages`
- `Coder.cur_messages`, except we transform the final user message as explained in [New User Message Structure](#new-user-message-structure).

#### Semantic Markers Approach

We chose to use semantic XML-like markers rather than strict XML for several key reasons:

1. **Simplicity and Readability**
   - Markers clearly indicate content boundaries without requiring XML escaping
   - Natural content remains readable without XML entity encoding
   - Source code can be included verbatim without modification

2. **Reduced Processing Overhead** 
   - No need to escape special characters in content
   - Simpler parsing requirements
   - Lower risk of encoding/decoding errors

3. **LLM-Friendly Format**
   - Clear semantic boundaries help the LLM understand content roles
   - Natural content is easier for the LLM to process
   - Reduced token usage by avoiding XML escaping

The markers serve as semantic boundaries while allowing content to appear naturally without escaping. This approach:

- Makes the prompts more maintainable
- Reduces complexity in the codebase
- Improves reliability by eliminating XML parsing edge cases
- Saves tokens by avoiding entity encoding
- Keeps source code readable and natural

The tradeoff is that we lose strict XML validation, but the benefits of simpler processing and natural content outweigh this limitation for our use case. The LLM is able to understand and respect the semantic boundaries without requiring strict XML compliance.

#### Structure of the system message

We will use a single system message as the first message of the message history. 
We use the value of `BRADE_PERSONA_PROMPT` to tell Brade its persona, role, and context.

#### Inserting a context message before the final user message

Before the final user message, we insert a pair of context messages:

1. a user message containing all supporting material
2. an assistant message acknowledging that user message

The user message contains all supporting material, organized as simple XML.
It is formtted as follows.

```xml
<!-- Opening text explains meta-level communication -->
This message is from the Brade application, not from your partner.
Your partner does not see this message or your response to it.

The Brade application has provided the current project information shown below.
This information is more recent and reliable than anything in earlier chat messages.

Treat any task instructions or examples provided below as
important guidance in how you handle your partner's next message.

<context>
  <!-- Repository overview and structure -->
  <repository_map>
    Repository map content appears here, using existing map formatting.
  </repository_map>

  <!-- Project source files -->
  <!-- Read-only reference files -->
  <readonly_files>
    <file path="path/to/file.py">
      <content>
def hello():
    print("Hello & welcome!")
    if x < 3:
        return True
      </content>
    </file>
  </readonly_files>

  <!-- Files available for editing -->
  <editable_files>
    <file path="path/to/other_file.py">
      <content>
def goodbye(name):
    print(f"Goodbye {name}!")
      </content>
    </file>
  </editable_files>

  <!-- System environment details -->
  <platform_info>
    Operating system, shell, language settings, etc.
  </platform_info>
</context>

<!-- Task-specific instructions and examples -->
<task_instructions>
  Current task requirements, constraints, and workflow guidance.
</task_instructions>

<task_examples>
  Example conversation demonstrating desired behavior for this task.
    <!-- Example interactions demonstrating desired behavior -->
    <example>
      <message role="user">Example user request</message>
      <message role="assistant">Example assistant response</message>
    </example>
  </examples>
```

This approach has several key benefits:

1. **Clear Meta-Level Communication**
   - Opening text explicitly explains the meta-level nature of this message
   - Makes clear which content comes from the application versus the user
   - Helps the model maintain appropriate context awareness

2. **Improved Context Management**
   - Supporting material appears just before it's needed
   - Context is clearly marked as current and authoritative
   - Explicit acknowledgment step ensures context is processed

3. **Clean Separation of Concerns**
   - User messages remain pure user content
   - Supporting material is cleanly separated
   - Task guidance appears at natural point in flow

4. **Semantic Structure**
   - XML tags clearly organize content
   - Groups related information logically
   - Includes descriptive comments for clarity
   - Supports special characters without escaping

The acknowledgment step between context and user message serves two purposes:
1. Ensures the model has processed the context
2. Maintains clean separation between meta-level and user-level communication

##### Handling task_examples

The placement of task_examples alongside task_instructions reflects that:
- Both provide guidance about how to handle the current request
- Task examples are logically related to task instructions
- This keeps the context section focused on codebase and environment
- Examples specific to the current task complement the general examples in the system message

In base_prompts.py, `example_messages` is defined as an empty list in `CoderPrompts`, and then subclasses like `EditBlockPrompts` override it with a list of dicts that match the `ChatMessage` type (having "role" and "content" keys).

For example, in editblock_prompts.py we see:

```python
example_messages = [
    dict(
        role="user",
        content="Change get_factorial() to use math.factorial",
    ),
    dict(
        role="assistant",
        content="""To make this change..."""
    ),
    # More examples...
]
```

So we can pass these example messages directly to `format_brade_messages()` since they already match the `ChatMessage` type. 
`format_brade_messages()` will be responsible for formatting these messages as documented above and placing them in the 
`<task_examples>` section of the final user message.

## Current State Analysis

### Key Findings
- Our system prompts contain much material that should be in user messages
- We lack consistent structure for document content
- Our `<SYSTEM>` markers don't align with XML best practices
- We mix instructions with content in ways that make the chat history harder to follow
- Our current approach makes it hard to validate prompt structure

### Current Pain Points
- Hard to verify prompt structure is correct
- Duplicate content between system and user messages
- Inconsistent formatting makes maintenance harder
- Chat history becomes confusing when instructions mix with content

## Inventory of Current Prompt Material

### System Messages in base_prompts.py

#### Core Role and Persona (BRADE_PERSONA_PROMPT)
- Expert software engineer identity
- Collaboration style and approach
- Core beliefs about software development
- Understanding of relative strengths/weaknesses

#### Task Instructions (main_system)
- Code editing requirements
- File handling rules
- Response format specifications
- Example conversations
- Platform-specific details

### User Message Components

#### Document Content Messages
- Source code files content
- Read-only reference files
- Repository map information
- File status notifications

#### Control Messages
- File addition notifications
- Git commit notifications
- Command processing results

### Current Message Flow
- System message sets role and task framework
- Repository and file content provided
- User query or request
- Assistant response with edits

## Analysis of Current Approach

### System Messages Issues

Our current system prompts contain:
- Role definition and persona characteristics
- Task instructions and requirements
- Output format specifications
- Example conversations
- Platform-specific information

This violates the guide's recommendation that system prompts should focus solely on:
- Defining Claude's role/expertise
- Setting fundamental context
- Establishing basic behavioral parameters

### Document Handling Issues

Currently we:
- Mix instructions with document content
- Use inconsistent document organization
- Place documents after instructions in some cases
- Use `<SYSTEM>` markers that don't align with XML structure

### Task Structure Issues

Our current approach:
- Combines role definition with task instructions in system messages
- Lacks clear separation between instructions and data
- Uses markdown-style formatting instead of XML
- Places queries before supporting content

## Prompt Improvements to Track

### Precision About Edit Blocks
- Need to be more precise in prompts about how edit blocks are handled
- Edit blocks are automatically applied and committed by the Brade application
- I (Brade) should understand this is automated, not manual
- Important for accurate mental model of the system

### Clarity About Roles and Relationships
- Clarify that I am Brade, an AI collaborating through the Brade application
- Make clear that you are Dean, my human partner
- Acknowledge the recursive nature of improving my own implementation
- Maintain professional but friendly collaboration style

### Additional Improvements
- (Add more improvements as we discover them)

## Testing Strategy

### Unit Tests
- Add tests for XML schema validation
- Add tests for content placement rules
- Add tests for role separation

### Integration Tests
- Test basic code editing still works
- Test file handling still works
- Test git integration still works
- Test command processing still works

### Manual Testing Checklist
- Check Langfuse logs to verify prompt structure
- Basic code editing with different models
- File handling operations (add/remove/modify)
- Git operations (commit/status/diff)
- Command processing for all command types
- Error handling and recovery
- Multi-file edits
- Long conversations with history

## Backward Compatible Example Messages

### Current Example Message Handling
The current approach in `chat_chunks.py` handles example messages in two ways:
- For models that use system messages, examples are embedded in the system message
- For other models, examples are added as separate messages after the system message
- The `Model.examples_as_sys_msg` flag controls this behavior

### New Example Message Handling
The Brade format will handle examples differently:
- Examples are included in the `<task_examples>` section of the final user message
- This provides clearer semantic structure
- Follows Claude prompting guidelines for document organization
- Allows examples to be cached with other context

### Transition Strategy
To maintain backward compatibility while transitioning:
1. Keep existing example message logic in `chat_chunks.py`
2. Add new example handling in `format_brade_messages.py`
3. Use `Model.use_brade_prompt_structure` flag to control which approach is used
4. Gradually transition models to new format
5. Eventually deprecate old format once all models support new structure

### Testing Strategy
- Add unit tests for both formats in parallel
- Test example message handling with both approaches
- Verify examples appear in correct location for each format
- Test caching behavior with examples in both formats
- Add integration tests to verify model behavior with both formats

## Analysis of Current and Planned Prompt Structure

This analysis examines each piece of information that flows through ChatChunks to build the prompt. For each item we explain what it is, where it comes from, and where it belongs in both the current and new structures. The order follows ChatChunks' message assembly sequence.

### System Role and Context
**Description**: Core definition of Brade's role, expertise, and behavioral parameters  
**Source**: System messages populated by `CoderPrompts` classes  
**Current**: First messages in sequence via `ChatChunks.system`  
**New**: Single system message at start of sequence

### Example Conversations  
**Description**: Sample exchanges demonstrating desired behavior  
**Source**: `ChatChunks.examples` populated by `CoderPrompts` classes  
**Current**: After system messages, either embedded or separate  
**New**: `<examples>` section in final user message

### Read-only Files
**Description**: Reference files not to be modified  
**Source**: `ChatChunks.readonly_files` from `Coder.abs_read_only_fnames`  
**Current**: After examples  
**New**: `<readonly_files>` section in final user message

### Repository Map
**Description**: Overview of repository structure and content  
**Source**: `ChatChunks.repo` from `RepoMap.get_repo_map()`  
**Current**: After read-only files  
**New**: `<repository_map>` section in final user message

### Done Messages
**Description**: Previous conversation exchanges  
**Source**: `ChatChunks.done` from `Coder.done_messages`  
**Current**: After repo content  
**New**: After opening system message, before transformed final user message

### Chat Files
**Description**: Current content of files being edited  
**Source**: `ChatChunks.chat_files` from `Coder.abs_fnames`  
**Current**: After done messages  
**New**: `<editable_files>` section in final user message

### Current Exchange
**Description**: Active conversation messages  
**Source**: `ChatChunks.cur` from `Coder.cur_messages`  
**Current**: After chat files  
**New**: After done messages, with final user message transformed to add context

### Reminder Messages
**Description**: Additional context and instructions  
**Source**: `ChatChunks.reminder` from various prompts  
**Current**: At end of sequence  
**New**: `<task_instructions>` section in final user message

### Platform Info
**Description**: System details and configuration  
**Source**: `Coder.get_platform_info()`  
**Current**: Mixed into system message  
**New**: `<platform_info>` section in final user message

This analysis reveals how our new structure will:
- Properly separate role definition into system message
- Preserve conversation flow through done messages
- Transform final user message to include all context
- Organize supporting content clearly and consistently
- Follow Claude prompting best practices

## Analysis of Current and Planned Event Messages

This section analyzes how we handle event messages - pairs of messages that document system actions like file additions, git commits, and command output. We examine the current implementation, identify issues, and plan improvements.

### Current Implementation

The codebase currently uses several types of event message pairs:

#### File Addition Events
- Generated in `Commands.cmd_add()`
- User message announces files added to chat
- Assistant acknowledges with "Ok"
- Example:
  ```
  USER: Added main.py to the chat
  ASSISTANT: Ok.
  ```

#### Git Commit Events  
- Generated in `Coder.auto_commit()`
- User message includes commit hash and message
- Assistant acknowledges
- Example:
  ```
  USER: I committed the changes with git hash abc123 & commit msg: Updated factorial
  ASSISTANT: Ok.
  ```

#### Shell Command Output
- Generated in `Commands.cmd_run()`
- User message contains command output
- Assistant acknowledges and may respond to output
- Example:
  ```
  USER: Output from pytest:
        test_factorial.py::test_basic FAILED
  ASSISTANT: I see the test failed. Let me help fix that.
  ```

#### Auto-Commit Events
- Generated after successful edits
- User message documents the auto-commit
- Assistant acknowledges
- Similar format to manual commits

#### Local Edit Events
- Generated when files change outside the chat
- User message notes external changes
- Assistant acknowledges
- Example:
  ```
  USER: Your partner edited the files themself.
  ASSISTANT: Ok.
  ```

### Current Issues

1. **Inconsistent Formatting**
   - Event messages use varying formats
   - Some include structured data, others just text
   - No standard way to parse event types

2. **Cluttered Chat History**
   - Many simple acknowledgment messages
   - Events mixed with substantive conversation
   - Hard to filter events from discussion

3. **Limited Context**
   - Events don't clearly link to affected files
   - Missing important metadata
   - Temporal relationship between events unclear

4. **Poor Machine Readability**
   - No consistent structure for automated processing
   - Events embedded in natural language
   - Hard to extract event data programmatically

### Planned Improvements

1. **Structured Event Format**
   - Move events to `<system_actions>` section
   - Use consistent XML structure:
     ```xml
     <action type="git_commit" hash="abc123">
       Updated factorial function
     </action>
     ```
   - Include all relevant metadata as attributes

2. **Event Categories**
   - Define standard event types:
     - file_add
     - git_commit
     - command_output
     - auto_commit
     - local_edit
   - Each type has specific required attributes

3. **Temporal Organization**
   - Keep older events in done_messages
   - Recent events in `<system_actions>`
   - Clear ordering within sections
   - Timestamps where appropriate

4. **Rich Metadata**
   - File paths affected
   - Command context
   - Error states
   - Related events
   - User intentions

5. **Implementation Plan**
   - Define XML schema for events
   - Update event generation code
   - Migrate existing events
   - Add validation
   - Update tests

This improved structure will:
- Make events machine readable
- Preserve important context
- Reduce chat noise
- Support better tooling
- Enable event filtering and analysis

## Implementation Strategy

### (✓) Inventory files that contain prompts.

#### Core Prompt Files
- **base_prompts.py**
  - Path: aider/coders/base_prompts.py
  - Purpose: Defines base CoderPrompts class with core prompts used by all coders
  - Contains: Main system prompts, example messages, file handling prompts
  
#### Editor-Specific Prompts
- **editblock_prompts.py**
  - Path: aider/coders/editblock_prompts.py
  - Purpose: Prompts for edit block style code modifications
  - Contains: Search/replace block format rules and examples

- **editblock_fenced_prompts.py**
  - Path: aider/coders/editblock_fenced_prompts.py
  - Purpose: Variation of edit block prompts using fenced code blocks
  - Contains: Example messages with fenced formatting

- **editor_editblock_prompts.py**
  - Path: aider/coders/editor_editblock_prompts.py
  - Purpose: Specialized prompts for editor mode using edit blocks
  - Contains: Simplified system prompts without shell commands

#### Whole File Prompts
- **wholefile_prompts.py**
  - Path: aider/coders/wholefile_prompts.py
  - Purpose: Prompts for whole file editing mode
  - Contains: File listing format rules and examples

- **editor_whole_prompts.py**
  - Path: aider/coders/editor_whole_prompts.py
  - Purpose: Editor mode prompts for whole file editing
  - Contains: Simplified system prompts for whole file edits

#### Function-Based Prompts
- **wholefile_func_prompts.py**
  - Path: aider/coders/wholefile_func_prompts.py
  - Purpose: Function-based prompts for whole file editing
  - Contains: write_file function definition and usage

- **single_wholefile_func_prompts.py**
  - Path: aider/coders/single_wholefile_func_prompts.py
  - Purpose: Single file version of function-based prompts
  - Contains: Simplified write_file function prompts

#### Special Purpose Prompts
- **architect_prompts.py**
  - Path: aider/coders/architect_prompts.py
  - Purpose: Prompts for architect mode planning and analysis
  - Contains: Two-step planning and implementation process

- **ask_prompts.py**
  - Path: aider/coders/ask_prompts.py
  - Purpose: Prompts for question answering mode
  - Contains: Code analysis and explanation prompts

- **help_prompts.py**
  - Path: aider/coders/help_prompts.py
  - Purpose: Prompts for help and documentation mode
  - Contains: Aider usage and documentation assistance

- **brade_prompts.py**
  - Path: aider/coders/brade_prompts.py
  - Purpose: Specialized prompts for Brade persona
  - Contains: Enhanced collaboration and personality traits

#### Unified Diff Prompts
- **udiff_prompts.py**
  - Path: aider/coders/udiff_prompts.py
  - Purpose: Prompts for unified diff style editing
  - Contains: Diff format rules and examples

### (✓) Further Prep for Prompt Restructuring
- (✓) Create backup copies of all prompt files before making changes
- (✓) Analyze common patterns and shared content across prompt files


## Implementation Tasks

### (✓) Enhance Documentation of Current State

- (✓) Revise chat_chunks.py to full Brade style
  - Add complete modern type hints
  - Add thorough internal documentation
  - Document relationships with other components
  - Document invariants and design decisions

- (✓) Document base_coder.py while maintaining Aider style
  - Keep existing code style to support mechanical merges
  - Add high-level docstrings and comments to document:
    - Overall class responsibilities
    - Key workflows and data flows
    - Integration points with other components
    - Important invariants and assumptions
  - Focus on larger comments rather than line-level documentation
  - Preserve existing code structure and style

The key goal is to document our current state while being strategic about which files we move to Brade style versus maintaining merge compatibility with upstream.

## Separating Role Definition from Task Instructions

This section tracks our work on restructuring prompts to properly separate role definition (which belongs in system messages) from task instructions (which belong in user messages).

### (✓) Initial Implementation

- (✓) Created format_brade_messages.py in Brade style
  - Implements XML-based message structure
  - Separates context from user message
  - Follows Claude prompting guidelines
  - Includes comprehensive unit tests

- (✓) Added Model.use_brade_prompt_structure flag
  - Controls when to use new prompt structure
  - Allows gradual rollout of changes

- (✓) Modified base_coder.py to use new structure
  - Added conditional logic for prompt formatting
  - Maintains backward compatibility
  - Preserves merge compatibility with upstream

### (✔︎) Restructure Prompt Files

The goal is to separate role definition from task instructions across all prompt files:

- (✔︎) architect_prompts.py
  - Move core architect role definition to system prompt
  - Move task workflow instructions to user message

We will emulate what we did in architect_prompts.py for the remaining prompt files.

```
class ArchitectPrompts(CoderPrompts):
    @property
    def task_instructions(self) -> str:
        """Task-specific instructions for the architect workflow."""
        return """
Reply to your partner in the same language that they are speaking.
You will satisfy your partner's request in two steps:

...
```

- (✔︎) editblock_prompts.py and editor_editblock_prompts.py
- (✔︎) wholefile_prompts.py and variants
- (✔︎) ask_prompts.py
- (✔︎) help_prompts.py
- (✔︎) udiff_prompts.py

## (✔︎) When Brade prompting is enabled, replace the use of `ChatChunks` with new logic.

### (✔︎) Introduce a flag `Model.use_brade_prompt_structure`.

### (✔︎) Introduce an `if Model.use_brade_prompt_structure` at the right point in `base_coder.py`.

### (✔︎) Implement a function `format_brade_messages` in a new file `format_brade_messages.py`.

This will be invoked from `base_coder.py` when `Model.use_brade_prompt_structure` is true, replacing
the current use of `ChatChunks`. Invocation of `_format_brade_messages` will replace the current body
of `Coder.

We will invoke `format_brade_messages` very differently from how we use `ChatChunks`. Its function signature
will have a parameter for each piece of information that is needed for constructing the prompt messages. 
Each parameter will have its own appropriate data type. We'll take into account the convenience for 
`_format_brade_messages`, given the information it has in instance variables of `Coder`. We'll make 
`format_brade_messages`'s API as natural and expressive as we can, taking into account both good Python style 
and the style and patterns of the rest of the code base.

- (✔︎) Scaffold `format_brade_messages.py` with a function `format_brade_messages` that does nothing for now. Write this in Brade code style.

- (✔︎) Implement the first, simple unit tests for `format_brade_messages` (which will of course fail for now) so Dean can review and adjust course.

- (✔︎) Write `format_brade_messages` to pass these first unit tests.

- (✔︎) Write `format_brade_messages` to pass all unit tests.

## ( ) Improve unit tests for `format_brade_messages` to make them an elegant specification of the Brade prompt structure.

### Goals and Approach

The unit tests for `format_brade_messages` should serve as both validation and documentation. They should:
- Clearly specify the expected structure and behavior of Brade prompts
- Make it easy to understand the prompt structure by reading the tests
- Provide good coverage of edge cases and error conditions
- Follow Python best practices for unit testing
- Support mechanical merging with upstream where feasible

### Phase 1: Core Functionality and Basic Structure

Focus on essential functionality and basic message structure validation.

#### Core Message Structure
- (✔︎) Test system message handling
  - Verify single system message at start
  - Check proper role definition content
  - Validate separation from task instructions

- (✔︎) Test basic conversation flow
  - Verify done_messages appear after system message
  - Check cur_messages handling before final message
  - Test simple message sequence with minimal content

#### Essential Context Sections
- (✔︎) Test minimal file content handling
  - Basic readonly_files section structure
  - Basic editable_files section structure
  - Simple file content preservation

- ( ) Test repository map basics
  - Basic XML wrapping
  - Simple content preservation

#### Critical Error Cases
- ( ) Test basic input validation
  - Type checking for required parameters
  - Handling of None for optional parameters
  - Basic error message clarity

### Phase 2: Comprehensive Structure and Content

Build on Phase 1 to ensure thorough handling of all content types.

#### Message Structure
- ( ) Test final user message transformation
  - Opening sentence about supporting material
  - Full XML structure validation
  - All sections present in correct order

#### Context Sections
- ( ) Test comprehensive file handling
  - Complex file content scenarios
  - Empty/None cases for both file types
  - Path validation and preservation

- ( ) Test platform info handling
  - XML structure validation
  - Content preservation
  - Empty/None cases

#### Task Guidance
- ( ) Test task instructions handling
  - XML structure validation
  - Content preservation
  - Empty/None cases

- ( ) Test task examples handling
  - Example pair validation
  - XML transformation
  - Multiple examples
  - Empty/None cases

### Phase 3: Edge Cases and Integration

Focus on robustness, real-world scenarios, and backward compatibility.

#### Error Handling
- ( ) Test advanced error cases
  - Complex invalid inputs
  - Malformed file content
  - Unusual characters
  - Oversized inputs
  - Boundary conditions

#### Integration
- ( ) Test with real-world examples
  - Complex file content
  - Typical conversation patterns
  - Common error scenarios

- ( ) Test backward compatibility
  - Existing message history
  - Legacy format examples
  - Mixed old/new format conversations

#### Performance and Scale
- ( ) Test with large inputs
  - Many files
  - Long conversation history
  - Complex XML structures


