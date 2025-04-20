# Plan for Supporting Sonnet 3.7

We are collaborating to enhance our Python project as described below. We want to work efficiently in an organized way. For the portions of the code that we must change to meet our functionality goals, we want to move toward beautiful, idiomatic Python following the style guidelines in CONTRIBUTING.md. We also want to move toward more testable code with simple unit tests that cover the most important paths.

This document contain three kinds of material:
- requirements
- specific plans for meeting those requirements
- our findings as we analyze our code along the way

We write down our findings as we go, to build up context for later tasks. When a task requires analysis, we use the section header as the task and write down our findings as that section's content.

For relatively complex tasks that benefit from a prose description of our approach, we use the section header as the task and write down our approach as that section's content. We nest these sections as appropriate.

For simpler tasks that can be naturally specified in a single sentence, we move to bullet points.

We use simple, textual checkboxes at each level of task, both for tasks represented by section headers and for tasks represented by bullets. Like this:

```
### ( ) Complex Task

- (✔︎) Subtask
  - (✔︎) Subsubtask
- ( ) Another subtask
```

## Requirements

1. Make Claude 3.7 Sonnet our new default Anthropic model when only ANTHROPIC_API_KEY is present.
2. Support extended thinking (Anthropic's term for deeper reasoning) with these reasoning level behaviors:
   - Level -1: Extended thinking disabled.
   - Level 0: Enable with ~8k token budget.
   - Level 1: Enable with ~30k token budget (reduced from 64k to avoid context limit errors).
3. Set default max_tokens to 60k (reduced from 128k to avoid context limit errors), while keeping the 128k capability via anthropic-beta header.
4. Maintain compatibility with our existing Anthropic flow and patterns.
5. Continue to treat Sonnet 3.7 similarly to Sonnet 3.5, except for extended thinking support.

## (✔︎) Model Configuration

### (✔︎) Configure Model Settings
- (✔︎) Add Sonnet 3.7 configuration to models.py.  
- (✔︎) Mark it as is_reasoning_model (to allow extended thinking).  
- (✔︎) Use the same edit format as Sonnet 3.5.  
- (✔︎) Configure weak and/or editor model references.  
- (✔︎) Enable 128k output (anthropic-beta: output-128k-2025-02-19).

### (✔︎) Configure Extended Thinking Parameters
- (✔︎) Map reasoning levels: -1 => disabled, 0 => 8192 tokens, 1 => 30000 tokens.  
- (✔︎) Handle disabled case cleanly (return {}).  
- (✔︎) Set max_tokens = 60000 to avoid context limit errors with large prompts.

## (✔︎) Default Model Selection

### (✔︎) Implement Selection Logic
- (✔︎) Make Sonnet 3.7 Sonnet the default Anthropic model when only ANTHROPIC_API_KEY is present.  
- (✔︎) Keep "o1" as fallback default if OPENAI_API_KEY or multiple keys exist.  
- (✔︎) Allow users to override with --model as usual.

### (✔︎) Ensure Configuration Consistency
- (✔︎) Confirm all references and prompts match the 3.7 default model name.  
- (✔︎) Double-check multi-model behavior with 3.7 as the new default.

## ( ) Extended Thinking Integration

### (✔︎) Implement Core Functionality
- (✔︎) Provide "thinking" parameter for Anthropic calls.  
- (✔︎) Insert or skip "thinking" blocks based on reasoning_level.  
- (✔︎) In lines with 3.5 approach, updated for 3.7.  

### (✔︎) Handle Extended Thinking Blocks
- (✔︎) Modify show_send_output_stream() to detect and filter thinking blocks:
  - (✔︎) Check chunk.choices[0].delta for "thinking_delta" or "redacted_thinking" blocks
  - (✔︎) Skip these blocks instead of adding to partial_response_content
  - (✔︎) Ensure thinking blocks never reach message history or user display
  - (✔︎) Maintain normal handling of text and function call blocks
- (✔︎) Consider similar filtering for non-streaming path in show_send_output()
- (✔︎) Consider similar filtering for non-streaming path in show_send_output()

### ( ) Manage Token Usage
- ( ) Final review or adjustments for 128k outputs vs. context window.  
- ( ) Confirm correct handling for "thinking" tokens within max_tokens.  
- ( ) Possibly refine context checks or streaming guidelines.

## ( ) Testing Strategy

### ( ) Unit / Integration Tests
- ( ) Tests specifically for 3.7 configuration and behavior.  
- ( ) Confirm default selection logic in main.py picks 3.7.  
- ( ) Validate extended thinking with each reasoning level and redacted blocks.  
- ( ) Test the 128k token capability, at least to verify no errors on large responses.  

### ( ) Edge Cases
- ( ) Confirm reasoning level -1 (no thinking) behaves exactly like standard.  
- ( ) Confirm streaming behavior with extended thinking.  
- ( ) Confirm all invariants (like partial blocks) remain intact.

## Future Considerations

1. Investigate performance and cost of extended thinking in real usage.
2. Possibly refine or expand reasoning level mappings to more levels.
3. Document best practices for 128k outputs, including streaming for large responses.
4. Expand or refine test coverage for real-world scenarios.
5. Watch for any further changes in Anthropic extended thinking or tooling.
