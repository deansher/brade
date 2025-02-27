# Enhance Repomap – Updated Plan for o3-mini Support and Message Transformation

This document outlines our progress and remaining work toward enhancing Brade to support the o3-mini model and its associated message conversion.

## Critical Constraints (unchanged)

1. litellm does not yet support "developer" messages  
2. o3-mini no longer supports "system" messages  
3. We must handle this conflict by:
   - Continuing to use "system" messages in our own code  
   - Converting them to simple "user" messages at the lowest level in sendchat.py  
   - (This conversion is simpler than the Anthropic conversion)  
   - No need for message pairs or "Understood" responses  
4. We will revisit this design after litellm adds support for "developer" messages  

## Summary  
- The core tasks for adding o3-mini support and the simpler message transformation have been completed.  
- The default model selection logic now sets o3-mini as the primary default if OPENAI_API_KEY is present and uses Claude when only ANTHROPIC_API_KEY exists.  
- Integration testing of API key combinations along with live model testing remain as essential items for further validation.  
- Additional refined integration tests and live validations will be moved to a future work section.

## Critical Constraints

1. litellm does not yet support "developer" messages
2. o3-mini no longer supports "system" messages
3. We must handle this conflict by:
   - Continuing to use "system" messages in our own code
   - Converting them to simple "user" messages at the lowest level, in sendchat.py
   - Similar to but simpler than our Anthropic message conversion
   - No need for message pairs or "Understood" responses
4. We will revisit this design after litellm adds support for "developer" messages

## Requirements

OpenAI has released a new model, o3-mini. We need to add support for this model to the Brade application. We will add support for the o3-mini model in a way that is consistent with our existing support for other models.

As our MVP, we'll use o3-mini as the default model in all cases except when only ANTHROPIC_API_KEY exists. This means:
- o1 is the default model, even when no API keys are present (supporting use with OpenAI proxies)
- Claude 3.5 Sonnet is only used when ANTHROPIC_API_KEY exists but OPENAI_API_KEY does not

OpenAI's documentation states:

> Developer messages are the new system messages: Starting with o1-2024-12-17, reasoning models support developer messages rather than system messages, to align with the chain of command behavior described in the model spec.

Due to the Critical Constraints above, we will still support "system" messages in all of our code above a certain lowest level. At that low-level point, we will convert them as needed for the target model. We already do a conversion for Anthropic messages in `transform_messages_for_anthropic` in sendchat.py. We will add an analogous conversion for o3-mini messages.

We won't change our own coding abstractions yet. Before doing that, we'll see what direction litellm's API goes with this.

## Tasks

### (✔︎) Add o3-mini Model Support

#### Requirements

1. Add o3-mini model configuration to models.py
2. Configure o3-mini as a reasoning model
3. Set appropriate defaults for the model
4. Ensure proper test coverage

#### Implementation Steps

- (✔︎) Add o3-mini model settings
  - (✔︎) Configure as reasoning model
  - (✔︎) Set appropriate edit format
  - (✔︎) Configure default models for weak/editor roles
  - (✔︎) Set other model-specific parameters

- (✔︎) Add tests for o3-mini configuration
  - (✔︎) Test model settings
  - (✔︎) Test default configurations

### (✔︎) Implement Message Transformation

#### Requirements

1. Add support for converting system messages to user messages
   - Simple one-to-one conversion of each system message to a user message
   - Preserve the original order of messages
   - No special handling or message combining needed

2. Keep implementation simple and focused
   - Convert system messages to user messages at the lowest level
   - Maintain compatibility with existing code above that layer
   - No need to follow the more complex Anthropic pattern

3. Ensure proper test coverage with focused test cases
   - Test one-to-one conversion of system messages
   - Verify message order is preserved
   - No need to test message combining or special cases

#### Implementation Steps

- (✔︎) Add message transformation function
  - (✔︎) Create transform_messages_for_o3 in sendchat.py
  - (✔︎) Implement simple system-to-user conversion
  - (✔︎) Preserve message order

- (✔︎) Add focused test cases
  - (✔︎) Test basic system-to-user conversion
  - (✔︎) Test order preservation
  - (✔︎) Test mixed message types

### (✔︎) Configure Default Model Selection

#### Requirements

1. Set o3-mini as the primary default model:
   - Use for all roles in ArchitectCoder (primary, editor, reviewer)
   - Use as default for all other use cases
   - Use o1 whenever OPENAI_API_KEY is present

2. Implement fallback logic:
   - Use latest Claude 3.5 Sonnet when only ANTHROPIC_API_KEY exists
   - Document the fallback behavior clearly in code comments

3. Ensure consistent configuration:
   - Proper edit formats for each role
   - Appropriate model settings
   - Correct prompts and message handling

#### Implementation Steps

- (✔︎) Update default model selection in main.py
  - (✔︎) Add clear comments explaining the default model strategy
  - (✔︎) Implement API key availability checks
  - (✔︎) Set o1 as primary default
  - (✔︎) Configure Claude 3.5 Sonnet fallback

- (✔︎) Verify model settings in models.py
  - (✔︎) Confirm o3-mini is properly configured for all roles
  - (✔︎) Validate edit formats for each role
  - (✔︎) Test model settings

- (✔︎) Add systematic integration tests for API key combinations:
  - (✔︎) Verify behavior with both OPENAI_API_KEY and ANTHROPIC_API_KEY present, ensuring o1 is selected.
  - (✔︎) Verify fallback behavior with only ANTHROPIC_API_KEY set, ensuring Claude 3.5 Sonnet is used.
  - (✔︎) Document observed behavior and any discrepancies.

### (✔︎) Validate Changes

#### Requirements

1. Ensure all tests pass
2. Verify changes work with o3-mini model
3. Confirm compatibility with existing models
4. Document any known limitations

#### Implementation Steps

- (✔︎) Run existing test suite
- (✔︎) Add integration tests
- (✔︎) Test with live o3-mini model
- ( ) Document findings and limitations

## Switch from o3-mini to o1

#### Requirements

1. Make o1 the default OpenAI model
   - ✓ Use o1 whenever OPENAI_API_KEY is present (see main.py model selection)
   - ✓ Keep Claude 3.5 Sonnet as default when only ANTHROPIC_API_KEY exists (see main.py model selection)

2. Handle o1's streaming limitations
   - ✓ Disable streaming for o1 since it's not yet supported (see ModelSettings for o1)
   - ✓ Add clear warning when streaming is requested but not available (see main.py streaming check)

3. Configure o1's reasoning effort mapping
   - ✓ Map reasoning_level=0 to "medium" reasoning effort (see _OpenAiReasoningConfigImpl.map_reasoning_level)
   - ✓ Map negative levels to "low" (see _OpenAiReasoningConfigImpl.map_reasoning_level)
   - ✓ Map positive levels to "high" (see _OpenAiReasoningConfigImpl.map_reasoning_level)

#### Implementation Steps

- (✓) Update model settings in models.py
  - (✓) Configure o1 as default OpenAI model
  - (✓) Set streaming=False for o1
  - (✓) Update reasoning level mapping for o1

- (✓) Modify default model selection in main.py
  - (✓) Use o1 when OPENAI_API_KEY exists
  - (✓) Keep Claude fallback when only ANTHROPIC_API_KEY exists
  - (✓) Add warning for unsupported streaming

- (✓) Add tests
  - (✓) Test default model selection logic
  - (✓) Test streaming behavior
  - (✓) Test reasoning level mapping
