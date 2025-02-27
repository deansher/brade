# Enhance Brade – Plan for Claude 3.7 Sonnet Support

This document outlines our plan for enhancing Brade to support Claude 3.7 Sonnet with extended thinking capabilities.

## Summary

- We will add support for Claude 3.7 Sonnet, making it our new default Anthropic model
- We will treat Sonnet 3.7 similarly to Sonnet 3.5, with the addition of extended thinking support
- Extended thinking will be controlled via reasoning_level:
  - Level -1: Extended thinking disabled
  - Level 0: 8k token budget for extended thinking
  - Level 1: 64k token budget for extended thinking
- We will enable 128k token output via the new beta header

## Critical Constraints

1. Extended thinking requires specific configuration:
   - Must be enabled via the "thinking" parameter
   - Requires a minimum budget of 1,024 tokens
   - Budget counts against max_tokens limit
   - Thinking blocks are billed as output tokens

2. We will maintain our existing message handling:
   - Continue using system messages in our higher-level code
   - Use existing Anthropic message transformation at the lowest level
   - Keep the "Understood" message pairs pattern

3. We will enable the 128k output beta:
   - Set anthropic-beta header to "output-128k-2025-02-19"
   - This allows for substantially longer responses
   - Particularly effective with extended thinking

## Requirements

Anthropic has released Claude 3.7 Sonnet with extended thinking capabilities. We need to add support for this model to Brade in a way that:
- Makes it our new default when only ANTHROPIC_API_KEY exists
- Integrates extended thinking based on reasoning_level
- Takes advantage of 128k output capability
- Maintains compatibility with our existing Anthropic support

## Tasks

### Add Sonnet 3.7 Model Support

#### Requirements

1. Add Sonnet 3.7 model configuration to models.py
2. Configure extended thinking parameters based on reasoning_level
3. Enable 128k output beta header
4. Set appropriate defaults for the model

#### Implementation Steps

- Add Sonnet 3.7 model settings
  - Configure as reasoning model
  - Set appropriate edit format (same as Sonnet 3.5)
  - Configure default models for weak/editor roles
  - Set other model-specific parameters
  - Add beta header for 128k output

- Add tests for Sonnet 3.7 configuration
  - Test model settings
  - Test reasoning level mapping
  - Test extended thinking parameters

### Implement Extended Thinking Support

#### Requirements

1. Map reasoning levels to extended thinking parameters:
   - Level -1: Disable extended thinking
   - Level 0: Enable with 8k token budget
   - Level 1: Enable with 64k token budget

2. Keep implementation focused:
   - Add extended thinking at the appropriate level
   - Maintain compatibility with existing code
   - Follow established Anthropic patterns

3. Ensure proper test coverage:
   - Test each reasoning level
   - Verify budget settings
   - Test with and without extended thinking

#### Implementation Steps

- Add extended thinking configuration
  - Map reasoning levels to budgets
  - Handle disabled case (-1)
  - Set appropriate max_tokens

- Add focused test cases
  - Test each reasoning level
  - Verify budget settings
  - Test disabled case

### Configure Default Model Selection

#### Requirements

1. Set Sonnet 3.7 as the default Anthropic model:
   - Use when only ANTHROPIC_API_KEY exists
   - Allow explicit selection via model name

2. Maintain existing fallback logic:
   - Use o1 when OPENAI_API_KEY exists
   - Document behavior clearly

3. Ensure consistent configuration:
   - Proper edit formats
   - Appropriate model settings
   - Correct prompts and message handling

#### Implementation Steps

- Update default model selection
  - Set Sonnet 3.7 as Anthropic default
  - Maintain o1 as OpenAI default
  - Document selection logic

- Verify model settings
  - Confirm proper configuration
  - Validate edit formats
  - Test settings

- Add integration tests:
  - Test API key combinations
  - Verify default selection
  - Document behavior

### Validate Changes

#### Requirements

1. Ensure all tests pass
2. Verify changes work with Sonnet 3.7
3. Test extended thinking functionality
4. Document any limitations

#### Implementation Steps

- Run test suite
- Test with live model
- Verify extended thinking
- Document findings

## Future Considerations

1. Monitor litellm support for extended thinking
2. Watch for Anthropic API updates
3. Consider refining reasoning level mapping
4. Evaluate need for additional token budgets
