# Enhance Brade – Plan for Claude 3.7 Sonnet Support

This document outlines our plan for enhancing Brade to support Claude 3.7 Sonnet with extended thinking capabilities.

## Summary

We will add support for Claude 3.7 Sonnet, making it our new default Anthropic model. While we'll treat it similarly to Sonnet 3.5 in most ways, we'll add support for its extended thinking capabilities (similar to how we handle o3). Key aspects:

- Make Sonnet 3.7 the default model when only ANTHROPIC_API_KEY exists
- Configure extended thinking based on reasoning_level:
  - Level -1: Extended thinking disabled
  - Level 0: Enable with 8k token budget
  - Level 1: Enable with 64k token budget
- Enable 128k token output via anthropic-beta header
- Maintain compatibility with existing Anthropic support patterns

## Critical Constraints

1. Extended thinking configuration:
   - Must be enabled via the "thinking" parameter
   - Requires minimum budget of 1,024 tokens
   - Budget counts against max_tokens limit
   - Thinking blocks are billed as output tokens
   - Must handle both normal and redacted thinking blocks

2. Message handling requirements:
   - Continue using system messages in higher-level code
   - Use existing Anthropic message transformation
   - Maintain "Understood" message pairs pattern
   - Preserve thinking blocks during tool use

3. Output capabilities:
   - Enable 128k output via anthropic-beta header
   - Set header to "output-128k-2025-02-19"
   - Particularly valuable with extended thinking
   - Consider streaming for very long outputs

## Implementation Plan

### 1. Model Configuration

#### Model Settings
- Add Sonnet 3.7 configuration to models.py
- Set as reasoning model (like o3)
- Use same edit format as Sonnet 3.5
- Configure appropriate weak/editor models
- Enable 128k output beta header

#### Extended Thinking Parameters
- Map reasoning levels to budgets:
  - Level -1: thinking parameter omitted
  - Level 0: thinking.budget_tokens = 8192
  - Level 1: thinking.budget_tokens = 65536
- Handle disabled case cleanly
- Set appropriate max_tokens limits

### 2. Default Model Selection

#### Selection Logic
- Make Sonnet 3.7 default when only ANTHROPIC_API_KEY exists
- Maintain o1 as default when OPENAI_API_KEY exists
- Allow explicit model selection to override defaults

#### Configuration Consistency
- Ensure proper edit formats
- Set appropriate model parameters
- Maintain correct prompts and messages

### 3. Extended Thinking Integration

#### Core Implementation
- Add thinking parameter handling
- Support both normal and redacted blocks
- Preserve blocks during tool use
- Handle streaming appropriately

#### Token Management
- Track thinking token usage
- Account for budget in max_tokens
- Handle context window calculations
- Support 128k output capability

### 4. Testing Strategy

#### Unit Tests
- Test model configuration
- Verify reasoning level mapping
- Check extended thinking parameters
- Validate default selection logic

#### Integration Tests
- Test with live model
- Verify extended thinking at each level
- Check 128k output functionality
- Validate tool use with thinking

#### Edge Cases
- Test disabled extended thinking
- Verify redacted block handling
- Check streaming behavior
- Validate token calculations

## Future Considerations

1. Performance Monitoring
   - Track extended thinking effectiveness
   - Monitor token usage patterns
   - Evaluate streaming performance

2. Potential Enhancements
   - Refine reasoning level mapping
   - Add more granular control options
   - Optimize token budget allocation

3. Maintenance
   - Monitor litellm support updates
   - Watch for Anthropic API changes
   - Track model performance metrics

4. Documentation
   - Update user documentation
   - Add extended thinking examples
   - Document best practices
   - Maintain troubleshooting guides
