# Plan for Indentation-Tolerant Search/Replace Blocks

We are collaborating to enhance our EditBlockCoder to better handle indentation differences between SEARCH blocks and actual file content. This document outlines our strategy for implementing this feature while maintaining backward compatibility and following good software engineering practices.

## Requirements

1. Handle cases where SEARCH blocks have different indentation than file content.
2. Match content with consistent indentation differences.
3. Apply REPLACE blocks with appropriate indentation adjustment.
4. Maintain high accuracy by avoiding false positives.
5. Preserve backward compatibility with existing functionality.
6. Add comprehensive test coverage for the new feature.

## (✓) Analysis of Current Implementation

### (✓) Current Search/Replace Matching Process
- The `replace_most_similar_chunk` function in `editblock_coder.py` is responsible for matching SEARCH blocks against file content.
- It uses Google's diff-match-patch library with a threshold of 0.05 (95% accuracy required).
- Current matching doesn't have special handling for consistent indentation differences.
- The `calculate_text_similarity` function measures similarity between texts using Levenshtein distance.

### (✓) Common Indentation Mismatch Patterns
- SEARCH block consistently has more indentation than the file content.
- SEARCH block consistently has less indentation than the file content.
- SEARCH and file use different indentation styles (tabs vs. spaces).
- Indentation varies within the SEARCH block (perhaps due to copy/paste from different sources).

## ( ) Design Approach

### ( ) Indentation Normalization Strategies
- ( ) Create functions to normalize whitespace while preserving relative indentation.
- ( ) Build tools to detect consistent indentation patterns across multiple lines.
- ( ) Implement algorithms to reapply indentation after matching.

### ( ) Two-Phase Matching Process
- ( ) Attempt exact matching first (preserving backward compatibility).
- ( ) If exact matching fails, try indentation-normalized matching.
- ( ) When a normalized match succeeds, determine the appropriate indentation adjustment.
- ( ) Apply the replacement with adjusted indentation.

### ( ) Similarity Threshold Management
- ( ) Consider different similarity thresholds for indentation-normalized matching.
- ( ) Implement safeguards against false positives in normalized matching.
- ( ) Provide clear diagnostics when indentation issues are detected.

## ( ) Implementation Plan

### ( ) Indentation Utilities
- ( ) Add `normalize_indentation` function to strip consistent leading whitespace.
- ( ) Implement `detect_indentation_pattern` to identify consistent indentation differences.
- ( ) Create `reindent_text` to apply consistent indentation to replacement text.

### ( ) Enhanced Matching Logic
- ( ) Modify `replace_most_similar_chunk` to incorporate indentation-tolerant matching.
- ( ) Add fallback path that tries normalized matching when exact matching fails.
- ( ) Preserve indentation pattern information when a normalized match succeeds.
- ( ) Apply appropriate indentation to replacement text.

### ( ) Improved Error Messages
- ( ) Enhance error reporting to detect and explain indentation issues.
- ( ) Add indentation-specific troubleshooting guidance.
- ( ) Include indentation analysis in diagnostic output.

## ( ) Testing Strategy

### ( ) Unit Tests
- ( ) Test basic indentation scenarios:
  - ( ) Matching with more indentation in SEARCH than file.
  - ( ) Matching with less indentation in SEARCH than file.
  - ( ) Matching with mixed indentation styles.
- ( ) Test edge cases:
  - ( ) Empty lines and whitespace-only lines.
  - ( ) First line with no indentation.
  - ( ) Inconsistent indentation within blocks.
- ( ) Test complex scenarios:
  - ( ) Multi-paragraph blocks with mixed content.
  - ( ) Code with comments and blank lines.
  - ( ) Multiple indentation changes within one block.

### ( ) Integration Tests
- ( ) Verify changes don't break existing functionality.
- ( ) Test end-to-end with realistic scenarios.
- ( ) Add regression tests for known indentation issues.

## ( ) Detailed Implementation Tasks

### ( ) Indentation Normalization
- ( ) Implement `get_common_indent` to find minimum common whitespace.
- ( ) Create `strip_common_indent` to normalize indentation.
- ( ) Add `indent_lines` to apply specified indentation to text.

### ( ) Match With Indent Tolerance
- ( ) Add indent-normalized variant of `replace_most_similar_chunk`.
- ( ) Ensure indent normalization preserves blank lines.
- ( ) Implement logic to store and apply indentation patterns.

### ( ) Error Handling Improvements
- ( ) Detect when indentation appears to be the primary issue.
- ( ) Add specific guidance for indentation problems in error messages.
- ( ) Include normalized text comparison in detailed diagnostics.

## ( ) Code Review Criteria
- ( ) Maintains backward compatibility.
- ( ) Handles edge cases correctly.
- ( ) Provides useful error messages.
- ( ) Has comprehensive test coverage.
- ( ) Follows Python best practices and project style guide.

## Future Considerations
1. Consider extending this approach to handle other whitespace variations (line endings, trailing spaces).
2. Explore optional auto-correction for simple indentation issues.
3. Add configuration options for indentation sensitivity levels.
4. Investigate more sophisticated pattern recognition for complex indentation issues.
5. Consider visual diffing in error outputs to better illustrate indentation problems.
