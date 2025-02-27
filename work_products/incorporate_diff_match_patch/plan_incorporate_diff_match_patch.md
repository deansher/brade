# Plan for Incorporating diff-match-patch Into editblock_coder.py

We are collaborating to enhance our Python project as described below. We want to work efficiently in an organized way. For the portions of the code that we must change to meet our functionality goals, we want to move toward beautiful, idiomatic Python code with modern type hints.

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

### Use diff-match-patch to improve search/replace block matching

Change editblock_coder.py to more reliably apply search/replace blocks by using the diff-match-patch library for soft matches between the search block and the target content. Choose tolerances to accurately handle three situations:

- If the differences between search block and target content are just minor LLM inaccuracies, such as extra spaces or line breaks, small missing comments, or slight punctuation differences, then the search block should still match the target content.

- If the differences are large enough to suggest that the LLM doesn't accurately see the target content, then this should not match.

- In an intermediate case, if the search block doesn't uniquely match one region of the target file, or if it is unclear whether the LLM clearly saw its intended match target, then this should not match.

Given how we prompt the LLM, it usually produces search blocks that cover tens of lines of the target file. In our experience, the LLM normally makes only a few, small mistakes in its transcription of existing content into the search block. Our algorithms and tests should expect this level of accuracy.

In less common cases where it makes more or larger mistakes, that usually does mean the LLM failed to "see" the target file accurately. For example, maybe it overlooked an entire small function when reproducing the "search" text. We do want to treat these cases as "no match" and retry.

In rare cases, the LLM might try to replace just one or several lines of the target file. In these cases, we should expect the LLM to be very accurate in what it wants to replace. If the LLM's search block appears multiple times in the file, we should reject this.

Our intuition is that when the LLM accurately sees what it wants to replace in the target file but just makes mistakes in the transcription, the match is probably something like 0.95, or even 0.99.

Initially, as the simplest thing that might work, we want to use diff-match-patch algorithms directly, rather than layering normalization or our own heuristics above it.

### Simplify the code

Simplify the code by removing homegrown heuristics.

### Improve error handling

When the match fails, provide clearer feedback to the LLM (i.e. to the editor assistant).

When the match fails and we retry ("reflection"), retain the entire dialog (all messages) between the editor assistant and the business logic in the chat history so that `ArchitectCoder`'s review pass fully understands what happened.

### Update tests

Correspondingly update tests.

## Tasks

### (✔︎) Integrate diff‐match‐patch into editblock_coder.py

- (✔︎) Replace the existing homegrown fuzzy matching in replace_most_similar_chunk with diff‐match‐patch based matching.
- (✔︎) Configure matching tolerances so that:
  - Minor differences (extra spaces, inconsistent line breaks, slight punctuation variations) are tolerated.
  - Significant mismatches are rejected.
  - Ambiguous or non-unique matches are flagged as failures.
- (✔︎) Update error handling to provide clear feedback when no match is found.

### (✔︎) Update and Expand Unit Tests

- (✔︎) Revise tests in tests/basic/test_editblock.py to reflect the new matching behavior.
- (✔︎) Add tests for:
  - Tolerance of minor inaccuracies.
  - Rejection of significant mismatches.
  - Detection of ambiguous matches.
- (✔︎) Confirm that error messages clearly identify match failures.

### ( ) Enhance Feedback and Dialog Logging

- ( ) Retain full dialog history during reflection so that ArchitectCoder’s review sees complete context.
- ( ) Update logs to indicate how diff‐match‐patch interpreted the search/replace block.

### ( ) Code Cleanup and Documentation

- (✔︎) Remove obsolete heuristics and matching hacks.
- (✔︎) Add inline documentation in editblock_coder.py on diff‐match‐patch integration and tolerance settings.
- (✔︎) Update overall project documentation to describe the new matching mechanism.

