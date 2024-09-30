# Plan for Adding Langfuse Tracing

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
### ( ) Complex Task

- (✅) Subtask
  - (✅) Subsubtask
- ( ) Another subtask
```

## Requirements

1. Integrate Langfuse tracing into our project to monitor LLM interactions.
2. Capture key information such as inputs, outputs, timings, and model usage.
3. Implement the integration incrementally, verifying each step before proceeding to the next.
4. Maintain the current style and structure of the codebase.

## (✅) Identify Source Files with LLM Interactions

### Findings

We have identified the following source files that are most likely to contain LLM interactions:

1. **`aider/sendchat.py`**:
   - Contains functions like `send_completion` and `simple_send_with_retries`.
   - These functions handle sending messages to the LLM and processing responses.
   - Likely the main interface with the LLM API.

2. **`aider/llm.py`**:
   - Defines the `LazyLiteLLM` class.
   - Manages the loading and use of the `litellm` module, which interacts with the LLM.
   - Important for understanding how the LLM is initialized and used within the application.

3. **`aider/coders/base_coder.py`**:
   - Contains the `Coder` class, which manages interactions with the user and the LLM.
   - Methods like `send_message`, `send`, and `apply_updates` may involve LLM calls.
   - Essential for inserting tracing at the right points to capture LLM interactions in the context of user sessions.

## (✅) Analyze LLM Interaction Points

### Findings

After reviewing the identified files, we've found the main points of interaction with the LLM:

- In `aider/sendchat.py`:
  - The `send_completion` function calls `litellm.completion` to send messages to the LLM and receive responses.
  - The `simple_send_with_retries` function also interacts with the LLM but is a helper function.

- In `aider/llm.py`:
  - The `LazyLiteLLM` class lazily loads the `litellm` module, which is used throughout the application for LLM interactions.

- In `aider/coders/base_coder.py`:
  - The `send_message` method prepares messages and calls `self.send` to interact with the LLM.
  - The `send` method invokes `send_completion` from `aider.sendchat` to perform the LLM call.
  - The `apply_updates` method processes the LLM's responses and applies changes to the codebase.

These are the key points where we'll integrate Langfuse tracing to capture LLM interactions.

### Integration Approach

We will start by adding tracing to the `send_completion` function in `aider/sendchat.py`, as it is the main function that interacts with the LLM.

We will use the `@observe()` decorator from Langfuse, specifying `as_type="generation"` to capture LLM generations.

## (✅) Implement Tracing in `send_completion` Function

- (✅) Import Langfuse decorators in `aider/sendchat.py`.
- (✅) Decorate the `send_completion` function with `@observe(as_type="generation")`.
- (✅) Update the function to capture inputs and outputs.

### Implementation Details

1. **Import Langfuse Decorators**

   Added the following import at the top of `aider/sendchat.py`:

   ```python
   from langfuse.decorators import observe, langfuse_context
   ```

2. **Decorate `send_completion` Function**

   Decorated the `send_completion` function:

   ```python
   @observe(as_type="generation")
   def send_completion(
       model_name,
       messages,
       functions,
       stream,
       temperature=0,
       extra_params=None,
   ):
       # Existing code...
   ```

3. **Capture Inputs and Outputs**

   Within the function, updated the tracing context to capture relevant information:

   ```python
   # Before calling litellm.completion
   langfuse_context.update_current_observation(
       input={
           'model_name': model_name,
           'messages': messages,
           'functions': functions,
           'stream': stream,
           'temperature': temperature,
           'extra_params': extra_params,
       },
       model=model_name,
   )

   # Perform the LLM call
   res = litellm.completion(**kwargs)

   # After receiving the response
   langfuse_context.update_current_observation(
       output=res.choices,
       usage={
           'input': res.usage.prompt_tokens,
           'output': res.usage.completion_tokens,
       },
   )
   ```

## ( ) Configure Langfuse Client Using Existing `.env` Loading Mechanism

- ( ) Ensure Langfuse API keys are included in the `.env` file.
- ( ) Update the sample `.env` file to include Langfuse configuration fields.
- ( ) Verify that the existing `.env` loading mechanism loads these variables properly.
- ( ) Initialize the Langfuse client in the application using the loaded environment variables.

### Implementation Details

1. **Update Sample `.env` File**

   Update the sample `.env` file (`aider/website/assets/sample.env`) to include the Langfuse configuration variables, so users know to set them:

   ```ini
   ##########################################################
   # Sample aider .env file.
   # Place at the root of your git repo.
   # Or use `aider --env <fname>` to specify.
   ##########################################################

   # ... existing content ...

   #################
   # Langfuse Configuration:

   ## Langfuse API Public Key
   #LANGFUSE_PUBLIC_KEY=

   ## Langfuse API Secret Key
   #LANGFUSE_SECRET_KEY=

   ## Langfuse Host URL (default: https://cloud.langfuse.com)
   #LANGFUSE_HOST=https://cloud.langfuse.com

   # ... rest of content ...
   ```

2. **Verify Existing `.env` Loading Mechanism**

   The project already has a mechanism to load environment variables from `.env` files. In `aider/main.py`, the function `load_dotenv_files` handles this:

   ```python
   def load_dotenv_files(git_root, dotenv_fname, encoding="utf-8"):
       dotenv_files = generate_search_path_list(
           ".env",
           git_root,
           dotenv_fname,
       )
       loaded = []
       for fname in dotenv_files:
           try:
               if Path(fname).exists():
                   load_dotenv(fname, override=True, encoding=encoding)
                   loaded.append(fname)
           except OSError as e:
               print(f"OSError loading {fname}: {e}")
           except Exception as e:
               print(f"Error loading {fname}: {e}")
       return loaded
   ```

   Since this mechanism loads environment variables before the main application runs, Langfuse can access its configuration via `os.environ`.

3. **Initialize Langfuse Client Using Environment Variables**

   In the main entry point of the application (`aider/main.py`), after the environment variables have been loaded, we will initialize the Langfuse client.

   **In `aider/main.py`:**

   Add the following import at the top of the file:

   ```python
   from langfuse.decorators import langfuse_context
   ```

   Then, after loading the environment variables (i.e., after calling `load_dotenv_files`), configure the Langfuse context:

   ```python
   # Existing code...

   # Load environment variables
   loaded_dotenvs = load_dotenv_files(git_root, args.env_file, args.encoding)

   # Configure Langfuse context using environment variables
   langfuse_context.configure()

   # Rest of the code...
   ```

   The `langfuse_context.configure()` method will automatically read the necessary configuration from the environment variables.

4. **Ensure Langfuse Initialization Happens at the Correct Place**

   Make sure that the Langfuse context is configured after the environment variables are loaded but before any LLM interactions occur. This ensures that the
tracing is properly initialized and captures all LLM interactions.

