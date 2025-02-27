# Plan for Switching to Low-Level Langfuse SDK

As I (Dean) edit this on December 9, 2024, I doubt it's a good idea.

Brade and Dean are using this document to support their collaborative process. Brade is an AI software engineer collaborating with Dean through the Brade application. We are working together to enhance the Brade application's code. This is an interesting recursive situation where Brade is helping improve her own implementation.

We want to work efficiently in an organized way. For the portions of the code that we must change to meet our functionality goals, we want to move toward beautiful, idiomatic Python code. We also want to move toward more testable code with simple unit tests that cover the most important paths.

This document is a living record of our work. It contains:

- Requirements that define what we want to achieve
- Specific plans for meeting those requirements
- Our findings as we analyze our code
- Our learnings as we complete tasks

As we work, we:

- Check off tasks as we complete them (✅)
- Document what we learn under each task
- Revise our plans based on what we learn
- Add new tasks as we discover them

For major steps of the work (each top-level bullet of each "### ( ) task" section) we follow this process:

- Make sure our plan is current.
- Make sure we have the information we need for our next step.
  - Writing down any new findings in this document.
  - Correct anything we previously misunderstood.
- Make sure existing unit tests pass.
- Consider whether to add unit tests or do manual testing before making the code changes.
- Make the code changes.
- Run the unit tests.
- Manually validate the change.
- Document what we learned.

We only intend for this plan to cover straightforward next steps to our next demonstrable milestone. We'll extend it as we go.

We write down our findings as we go, to build up context for later tasks. When a task requires analysis, we use the section header as the task and write down our findings as that section's content.

For relatively complex tasks that benefit from a prose description of our approach, we use the section header as the task and write down our approach as that section's content. We nest these sections as appropriate.

For simpler tasks that can be naturally specified in a single sentence, we move to bullet points.

We use simple, textual checkboxes at each level of task, both for tasks represented by section headers and for tasks represented by bullets. Like this:

```
### ( ) Complex Task.

- (✅) Subtask
  - (✅) Subsubtask
  - Added support for X
  - Discovered Y needs to be handled differently
- ( ) Another subtask
```

## Requirements

Rework our Langfuse integration to cleanly and thoroughly use the low-level Python SDK. In our current integration, we mostly use decorators. This has proven awkward and we want to move away from it. 

Here are some specific requirements:

- Continue capturing the useful information that we capture today.
- Cleanly capture streamed model responses as `output` of "generation" traces.
- Create a module aider/langfuse_utils.py that provides our own customized abstractions around Langfuse. (We may even define some of our own decorators here, if we see ways to use them more ergonomically.)
- Follow project conventions as documented in CONTRIBUTING.md.

## Tasks

### (✅) Document the current state of our Langfuse integration.

Our current Langfuse integration is primarily based on decorators from the Langfuse Python SDK. Here are the key aspects:

1. Configuration
   - We configure Langfuse in main.py using environment variables
   - We use langfuse_context.configure() to set up the integration
   - We have a LazyLiteLLM class in llm.py that manages Langfuse initialization

2. Core Tracing
   - We use @observe decorators extensively, especially in sendchat.py
   - The @observe decorator automatically creates traces and spans
   - We use langfuse_context.update_current_observation() to add details
   - We capture:
     - Input messages and output responses
     - Model name and parameters
     - Usage statistics (tokens, costs)
     - Timing information

3. Key Files
   - llm.py: Configures Langfuse and manages initialization
   - sendchat.py: Uses decorators to trace LLM interactions
   - main.py: Configures Langfuse via environment variables
   - base_coder.py: Uses decorators to trace high-level operations

4. Limitations of Current Approach
   - Decorator-based approach can be awkward for complex flows
   - Stream handling could be cleaner
   - Some duplication of configuration logic
   - No centralized place for our Langfuse abstractions
   - Initialization is spread across multiple files

### (✅) Document the design of our reworked integration.

1. We will create a new module `aider/langfuse_utils.py` that provides clean abstractions around the Langfuse low-level SDK. 

2. Context Managers
   - Use context managers to cleanly manage trace/span lifecycles
   - Automatically handle start/end times
   - Support both sync and async contexts
   - Handle exceptions properly

3. Configuration
   - Move all Langfuse configuration into langfuse_utils.py
   - Provide a clean interface for initialization
   - Support both environment variables and explicit configuration

4. Stream Handling
   - Clean abstractions for handling streaming responses
   - Properly capture streamed output in traces
   - Support progress callbacks

5. Migration Strategy
   1. Create langfuse_utils.py with core abstractions
   2. Start with one narrow piece of functionality
   3. Gradually migrate existing code
   4. Remove old decorator-based code
   5. Clean up initialization logic

### ( ) Comment out existing Langfuse integration.

This task prepares us to migrate to our new langfuse_utils-based approach by commenting out existing Langfuse code. We'll do this methodically to maintain visibility into what needs to be migrated.

1. ( ) Document existing tracing points

Capture the following information in this section of our plan:

   - For each file with Langfuse integration:
     - List each tracing point
     - Note what information it captures
     - Note any special handling (e.g., streaming)
     - Note any dependencies on the tracing

2. ( ) Comment out initialization code
   - Use this format: `# TODO(langfuse): <description of what needs to be migrated>`
   - Comment out in this order:
     - llm.py Langfuse initialization
     - main.py Langfuse configuration
     - Other initialization points

3. ( ) Comment out tracing points
   - One file at a time, in this order:
     - sendchat.py (core LLM interaction)
     - base_coder.py (high-level operations)
     - Any remaining files
   - For each file:
     - Comment out @observe decorators
     - Comment out langfuse_context usage
     - Test that basic functionality still works
     - Note any broken functionality in existing_tracing.md

4. ( ) Validation
   - Run all tests
   - Do basic manual testing
   - Verify all TODO(langfuse) items are findable
   - Update existing_tracing.md with any new findings

5. ( ) Clean up
   - Remove any commented code that won't be migrated
   - Move any useful comments into design docs

### ( ) Rework one narrow piece of our integration.

Implement this using `langfuse_utils` APIs that we find we wish we had. Just scaffold them for now.

### ( ) Rework a second piece of our integration.

### ( ) Thoughtfully revise the `langfuse_utils` module API.

### ( ) Implement the `langfuse_utils` module.

### ( ) Finish migrating to our new approach.

