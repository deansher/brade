# Plan for `BradeCoder`

Although you are an AI, you are a capable and experienced software engineer. You and I often collaborate on projects. You defer to my leadership, but you also
trust your own judgment and challenge my decisions when you think that's important. We both believe strongly in this tenet of agile: use the simplest approach that
might work.

We are collaborating to enhance our Python project as described below. We want to work efficiently in an organized way. For the portions of the code that we must
change to meet our functionality goals, we want to move toward beautiful, idiomatic Python code. We also want to move toward more testable code with simple unit
tests that cover the most important paths.

This document contains three kinds of material:

- requirements
- specific plans for meeting those requirements
- our findings as we analyze our code along the way

We only intend for this plan to cover straightforward next steps to our next demonstrable milestone. We'll extend it as we go.

We write down our findings as we go, to build up context for later tasks. When a task requires analysis, we use the section header as the task and write down our
findings as that section's content.

For relatively complex tasks that benefit from a prose description of our approach, we use the section header as the task and write down our approach as that
section's content. We nest these sections as appropriate.

For simpler tasks that can be naturally specified in a single sentence, we move to bullet points.

We use simple, textual checkboxes at each level of task, both for tasks represented by section headers and for tasks represented by bullets. Like this:

```
### ( ) Complex Task.

- (✅) Subtask
  - (✅) Subsubtask
- ( ) Another subtask
```

## Requirements

This project is a fork of a project called aider. We want our changes to be minimally invasive to existing code to reduce merge conflicts when we pull updates from upstream.

Our fork introduces an AI persona named Brade, with extensive prompt changes to make Brade interact and perform differently than aider's (very basic) persona. So far, we have made these changes by editing prompts throughout aider's `Coder` subclasses. But now, instead, we want to introduce a new `Coder` subclass called `BradeCoder`:

- `BradeCoder` will be a subclass of `EditBlockCoder`.
- `BradeCoder` will now handle the "diff" edit format instead of `EditBlockCoder` handling it.
- `BradeCoder` will rely on a new `BradePrompts` class for its prompts as much as reasonably feasible, instead of referencing them from other coder or prompt classes.
  - Initially, the prompts in `BradePrompts` will be identical to the ones we are currently using for `EditBlockCoder`. (These are largely defined in `EditBlockPrompts` and `CoderPrompts`.)
  - `BradePrompts` will not be a subclass of `CoderPrompts`, because we will use a different approach to prompt generation.
  - Our new approach to prompt generation in `BradePrompts` will be to invoke a method that takes the current chat history as an argument and returns the prompt. (In early versions, we will ignore the chat history argument.)
  - We will name these prompt generations like `make_foo_prompt`. 
  - For example, instead of just referencing `main_system` to get the main system prompt, we will now invoke the method `make_main_system_prompt`.
- `BradeCoder` will use a subordinate architect model. See [Subordinate Architect Model](#subordinate-architect-model) for details.

### Bootstrapping Process

We use `brade` in our own development. Right now, we use the `architect` edit format. So we want to keep that working well, with the new prompts that we have already introduced, until `BradeCoder` is good enough to supplant it.

### Subordinate Architect Model

Having experimented with `ArchitectCoder` and its use of a subordinate `editor_coder`, we see many benefits, but we want `BraderCoder` to organize the architect versus editor role differently.

We've experimented with using o1-preview as our architect. It generates a lot of material. And it appears to be material that will help the `editor_coder` a lot.

But it also generates considerably more material than the user wants to review. The user would be happier with an overview that helps them understand the proposed direction and either say yes or give feedback.

Plus, conversation with the architect/editor combination is awkward. The `[Y]es` or `[N]o` decision that we ask the user to make on the transition from architect to editor is unnatural and hard to understand.

Putting all this together, we have decided to make `BradeCoder` the speaking and listening voice in all conversations with the user, and having it delegate to the architect model (not to an architect coder) when it needs expert input.  `BradeCoder` will decide when to invoke the architect model. When it does invoke the architect model, it will keep the architect model's full output to itself, just using it as a resource both for conversation with the user and for coding.

## (✅) Investigate how chat history is managed and represented in aider.

Understanding how chat history is managed in aider is crucial for implementing `BradeCoder` and `BradePrompts`, especially since `BradePrompts` will generate
prompts based on the current chat history.

### Chat History Management in Aider

The chat history in aider is primarily managed within the `Coder` class in `aider/coders/base_coder.py`. Here's how it works:

#### Key Components:

1. **Attributes Managing Chat History:**
   - **`done_messages`:**
     - A list that stores all the messages that have been exchanged in the conversation so far.
     - Each message is a dictionary with `role` and `content` keys.
     - Example:
       ```python
       {
           "role": "user" or "assistant",
           "content": "The message content."
       }
       ```
   - **`cur_messages`:**
     - A list that holds the current set of messages being processed.
     - After each interaction, messages from `cur_messages` are moved to `done_messages`.

2. **Message Flow:**
   - **User Input:**
     - Captured using the `get_input` method.
     - The input is preprocessed and then added to `cur_messages` with the role `"user"`.
   - **Assistant Response:**
     - Generated in the `send_message` method.
     - The assistant's reply is added to `cur_messages` with the role `"assistant"`.
   - **Updating Chat History:**
     - After each interaction, `cur_messages` is appended to `done_messages`, and `cur_messages` is cleared for the next interaction.

3. **Message Structure:**
   - Messages are represented as dictionaries with `role` and `content`.
   - Consistent structure allows for easy manipulation and formatting of messages for the model.

#### Summarization:

- **Chat History Summarization:**
  - Implemented using the `ChatSummary` class in `aider/history.py`.
  - Summarization helps manage token limits by condensing the chat history when it becomes too long.
  - Methods involved:
    - `summarize_start`: Initiates summarization in a separate thread.
    - `summarize_worker`: Performs the actual summarization.
    - `summarize_end`: Replaces `done_messages` with the summarized content once summarization is complete.

#### Interaction with Prompts:

- **Formatting Messages for the Model:**
  - The `format_messages` method in `Coder` prepares the messages to be sent to the model.
  - It creates a `ChatChunks` object that organizes messages into sections:
    - System prompts
    - Example messages
    - Summarized `done_messages`
    - `cur_messages`
  - This organized structure allows for flexible prompt construction and efficient token usage.

- **Prompt Generation:**
  - The `fmt_system_prompt` method formats system-level prompts.
  - The assistant's behavior can be adjusted by modifying these prompts or by adding new ones.

#### Key Methods:

- **`run`:**
  - The main loop that captures user input and processes the assistant's responses.
- **`run_one`:**
  - Handles a single interaction between the user and the assistant.
- **`send_message`:**
  - Sends the prepared messages to the model and handles the assistant's response.
  - Updates `cur_messages` with the assistant's reply.
- **`update_cur_messages`:**
  - Appends the assistant's final response to `cur_messages`.

### Implications for `BradePrompts`

- **Access to Chat History:**
  - `BradePrompts` can utilize both `done_messages` and `cur_messages` to generate context-aware prompts.
  - This allows for dynamic prompt generation based on the entire conversation history.

- **API Design:**
  - Prompt generation methods in `BradePrompts` should accept the chat history as a parameter.
  - Example method signature:
    ```python
    def make_main_system_prompt(self, done_messages, cur_messages):
        # Generate the main system prompt using the chat history.
    ```

- **Integration with `BradeCoder`:**
  - `BradeCoder` can pass the chat history to `BradePrompts` when generating prompts.
  - Ensures that prompts are always up-to-date with the latest conversation context.

### Conclusion

By understanding how aider manages and represents chat history, we can effectively design `BradePrompts` to generate prompts that are contextually relevant. The
use of `done_messages` and `cur_messages` provides a clear structure for accessing the conversation history, and integrating this with `BradeCoder` will enhance
the assistant's ability to generate appropriate responses based on the entire chat history.

## (✅) Scaffold Brade classes.

This first version will not yet use a subordinate architect model. Instead, it will behave like `EditBlockCoder` does today.

- (✅) Define the API for `BradePrompts`.
- (✅) Write an initial version of `BradePrompts`.
- (✅) Write an initial version of `BradeCoder`.
- (✅) Incorporate the material from `CoderPrompts.brade_persona_prompt` into `BradePrompts`.


## (✅) Change higher-level code to have `BradeCoder` handle the "diff" edit format instead of `EditBlockCoder`.

## (✅) Review `EditBlockCoder`, identifying any needed improvements to `BradeCoder` to make it a solid subclass.

### Overview of `EditBlockCoder`

`EditBlockCoder` is a subclass of `Coder` that uses search/replace blocks for code modifications. It leverages a specific edit format (in this case, `"diff"`) and
utilizes prompts defined in `EditBlockPrompts`.

#### Key Features of `EditBlockCoder`:

- **Edit Format**: Specifies `edit_format = "diff"`, indicating it operates using diff-based edits.
- **Prompts**: Uses `EditBlockPrompts` for generating prompts and system messages.
- **Methods**:
  - `get_edits`: Parses the assistant's response to extract edits (search/replace blocks).
  - `apply_edits`: Applies the extracted edits to the target files.
- **Error Handling**: Provides detailed error messages when edits fail to apply, helping the user understand and rectify issues.

#### Implementation Details:

- **Initialization**:
  - Inherits from `Coder` and initializes with necessary arguments and keyword arguments.
  - Sets up the `edit_format` and initializes `gpt_prompts` with `EditBlockPrompts`.
- **Prompt Generation**:
  - Relies on `EditBlockPrompts` for system prompts, example messages, file content prefixes, etc.
- **Edit Parsing and Application**:
  - The `get_edits` method extracts edits from the assistant's response.
  - The `apply_edits` method applies these edits to the files, handling any discrepancies or errors.

### Review of `BradeCoder` in Relation to `EditBlockCoder`

`BradeCoder` is intended to be a subclass of `EditBlockCoder` that introduces custom prompt generation using `BradePrompts`. The goal is to maintain the core
functionality of `EditBlockCoder` while customizing the assistant's behavior and prompts.

#### Goals:

- **Functional `BradeCoder`**: A subclass that correctly inherits from `EditBlockCoder` and functions seamlessly with the new prompt generation system.
- **Robust Editing Capabilities**: Ensures that code edits are accurately parsed and applied, maintaining the reliability of the assistant.
- **Enhanced User Experience**: Error messages and assistant responses align with `Brade`'s persona, providing a consistent and engaging user experience.
- **Foundation for Future Development**: The codebase is well-structured for the planned integration of the subordinate architect model.

#### Observations:

1. **Inheritance Structure**:
   - `BradeCoder` correctly inherits from `EditBlockCoder`.
   - It sets `edit_format = "diff"`, matching `EditBlockCoder`.

2. **Custom Prompts**:
   - Initializes `brade_prompts` as an instance of `BradePrompts`.
   - Overrides methods such as `fmt_system_prompt` and `format_chat_chunks` to use `BradePrompts` for prompt generation.

3. **Methods from `EditBlockCoder`**:
   - Does not explicitly override `get_edits` or `apply_edits`, relying on inheritance from `EditBlockCoder`.
   - By inheriting these methods, `BradeCoder` should maintain the core edit parsing and application functionality.

#### Identified Improvements Needed:

1. **Proper Initialization in `BradeCoder`**:

   - **Issue**: The `__init__` method in `BradeCoder` only calls `super().__init__(*args, **kwargs)` without ensuring all necessary attributes are initialized.
   - **Improvement**: Ensure that all attributes from both `EditBlockCoder` and `Coder` are properly initialized. This includes setting up `edit_format`,
`gpt_prompts`, and any other necessary configurations.

2. **Consistency in Prompt Usage**:

   - **Issue**: While `BradeCoder` overrides prompt generation methods, it must ensure that all prompts required by `EditBlockCoder` are appropriately provided by
`BradePrompts`.
   - **Improvement**: Verify that `BradePrompts` includes all the necessary prompts (e.g., `files_content_prefix`, `system_reminder`, etc.) that `EditBlockCoder`
expects from `EditBlockPrompts`.

3. **Method Overrides and Customizations**:

   - **Issue**: If `BradePrompts` significantly changes the format or content of the prompts, methods like `get_edits` in `EditBlockCoder` may not parse the
assistant's responses correctly.
   - **Improvement**: Review the `get_edits` and `apply_edits` methods to ensure they work seamlessly with the outputs generated using `BradePrompts`. If
necessary, override these methods in `BradeCoder` to handle any differences.

4. **Error Handling Alignment**:

   - **Issue**: Error messages and handling in `EditBlockCoder` are tailored to its prompt styles.
   - **Improvement**: Adjust error handling in `BradeCoder` to align with `Brade`'s persona and ensure that users receive coherent and helpful feedback.

5. **Testing and Validation**:

   - **Issue**: Changes in prompts and potential method overrides may introduce unforeseen issues.
   - **Improvement**: Implement comprehensive testing for `BradeCoder` to ensure all functionalities work as intended and that it is robust against unexpected
inputs.

## ( ) Improve `BradeCoder` to Ensure It Is a Solid Subclass of `EditBlockCoder`

**Objective**: Enhance `BradeCoder` to fully leverage the functionalities of `EditBlockCoder` while incorporating custom prompt generation through `BradePrompts`.

### Tasks:

- ( ) **Ensure Proper Initialization in `BradeCoder`**

   - **Adjust the `__init__` Method**:
     - Modify `BradeCoder`'s `__init__` method to explicitly initialize all required attributes.
     - Call `super().__init__()` with appropriate arguments to ensure that both `EditBlockCoder` and `Coder` are correctly initialized.
     - Example:
       ```python
       class BradeCoder(EditBlockCoder):
           def __init__(self, *args, **kwargs):
               super().__init__(*args, **kwargs)
               self.edit_format = "diff"
               self.brade_prompts = BradePrompts()
       ```

- ( ) **Verify and Update Prompt Attributes**

   - **Ensure All Prompts are Available in `BradePrompts`**:
     - Review `BradePrompts` to confirm it includes all necessary prompt attributes and methods that `EditBlockCoder` expects.
     - Add any missing prompts or methods to `BradePrompts`.
   - **Align Prompt Formats**:
     - Ensure that the output formats from `BradePrompts` match what `EditBlockCoder`'s methods expect, particularly in terms of parsing edits.

- ( ) **Override Methods if Necessary**

   - **Adjust `get_edits` Method**:
     - If the assistant's response format has changed due to different prompts, override `get_edits` in `BradeCoder` to correctly parse edits.
     - Ensure that it can handle any new response structures introduced by `BradePrompts`.
   - **Adjust `apply_edits` Method**:
     - If the method of applying edits needs customization, override `apply_edits` to accommodate any changes.

- ( ) **Update Error Handling**

   - **Customize Error Messages**:
     - Modify error messages in `BradeCoder` to reflect `Brade`'s persona and communication style.
     - Ensure that error feedback is clear, helpful, and consistent with the assistant's overall behavior.
   - **Maintain Robustness**:
     - Ensure that error handling gracefully manages unexpected situations without causing crashes or undefined behavior.

- ( ) **Implement Comprehensive Testing**

   - **Unit Tests**:
     - Write unit tests specifically for `BradeCoder` to validate its methods and behaviors.
     - Test scenarios including successful edits, parsing failures, and error handling.
   - **Integration Tests**:
     - Test `BradeCoder` within the larger application to ensure it interacts correctly with other components.
     - Verify end-to-end functionality from user input to file modification.

- ( ) **Prepare for Architect Model Integration**

   - **Design for Extensibility**:
     - Ensure that `BradeCoder`'s structure allows for easy integration of the subordinate architect model in future updates.
     - Consider adding placeholders or design patterns that facilitate this addition without significant refactoring.

- ( ) **Documentation and Code Comments**

   - **Update Docstrings**:
     - Provide clear docstrings for all methods in `BradeCoder`, explaining their purpose and any overrides from the superclass.
   - **Document Differences**:
     - Clearly document any differences in behavior or implementation from `EditBlockCoder`.
     - Include explanations for why certain methods were overridden or customized.

## ( ) Introduce "situation analysis" into `BraderCoder`'s prompt generation.

## ( ) Revert our prompt-related changes to other `FooCoder` and `FooPrompts` classes.

Compare our `brade` branch with the `main` branch from upstream and revert `FooCoder` and `FooPrompts` changes to the extent reasonably feasible.
