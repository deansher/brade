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

## Design Approach

### Architecture Overview

We'll implement a two-phase matching approach that:

1. **Preserves Backward Compatibility**: Always attempts exact matching first
2. **Uses Progressive Enhancement**: Only applies normalization when needed
3. **Maintains Clear Separation of Concerns**: Each function has a single responsibility
4. **Provides Robust Error Handling**: Gives specific guidance for indentation issues

The key components are:
- **Core Indentation Utilities**: Low-level functions to analyze and manipulate indentation
- **Indentation Pattern Analysis**: Tools to detect consistent indentation patterns
- **Enhanced Matching Logic**: Two-phase matching process with proper indentation handling
- **Improved Error Messages**: Specific guidance for indentation-related issues

## Implementation Plan

### Core Indentation Utilities

#### 1. Implement `get_common_indent` Function

```python
def get_common_indent(lines: list[str]) -> str:
    """
    Find minimum common leading whitespace across non-empty lines.
    
    Args:
        lines: List of strings representing lines of text
        
    Returns:
        str: The common indentation string (spaces or tabs)
    """
```

- [ ] Implement function to find common leading whitespace in a list of lines
- [ ] Handle empty lines by ignoring them in calculations
- [ ] Return empty string if any non-empty line has no indentation
- [ ] Add unit tests for various indentation patterns

#### 2. Implement `strip_common_indent` Function

```python
def strip_common_indent(text: str) -> tuple[str, str]:
    """
    Normalize indentation by removing common leading whitespace.
    
    Args:
        text: Multi-line text to normalize
        
    Returns:
        tuple[str, str]: (Normalized text, common indentation that was removed)
    """
```

- [ ] Split text into lines
- [ ] Find common indent using get_common_indent()
- [ ] Remove this indent from each non-empty line
- [ ] Preserve empty lines unchanged
- [ ] Return both normalized text and the removed common indent
- [ ] Add unit tests for various indentation scenarios

### Indentation Pattern Analysis

#### 3. Implement `detect_indent_pattern` Function

```python
def detect_indent_pattern(original: str, matched: str) -> dict:
    """
    Analyze indentation differences between original and matched text.
    
    Args:
        original: Original search text
        matched: Text that matched in the file
        
    Returns:
        dict: Indentation pattern information
    """
```

- [ ] Compare original and matched text line-by-line
- [ ] Detect indentation type (spaces, tabs, mixed)
- [ ] Calculate average indentation depth 
- [ ] Return comprehensive indentation pattern information
- [ ] Add unit tests for different indentation patterns

#### 4. Implement `reindent_text` Function

```python
def reindent_text(text: str, indent_pattern: dict) -> str:
    """
    Apply indentation pattern to normalized text.
    
    Args:
        text: Text to reindent
        indent_pattern: Indentation pattern dict
        
    Returns:
        str: Text with applied indentation pattern
    """
```

- [ ] Apply indentation pattern to text
- [ ] Preserve relative indentation relationships
- [ ] Handle empty lines appropriately
- [ ] Add unit tests for verifying proper indentation application

### Enhanced Matching Logic

#### 5. Implement `normalized_match_and_replace` Function

```python
def normalized_match_and_replace(whole: str, original: str, updated: str) -> str:
    """Match and replace with normalization of indentation."""
```

- [ ] Normalize indentation in search text and file content
- [ ] Find match locations in normalized texts
- [ ] Determine original indentation pattern at match location
- [ ] Apply equivalent indentation to replacement text
- [ ] Perform replacement with properly indented text
- [ ] Add unit tests for indentation-aware matching

#### 6. Modify `replace_most_similar_chunk` Function

- [ ] First try exact matching (current behavior)
- [ ] On failure, try indentation-normalized matching
- [ ] Maintain high threshold (95%) for both methods
- [ ] Return early if exact matching succeeds
- [ ] Add unit tests to verify the two-phase approach

#### 7. Update `do_replace` Function

- [ ] Pass appropriate context to replace_most_similar_chunk
- [ ] Ensure proper handling of indentation information
- [ ] Add unit tests for indentation-aware replacements

### Error Reporting Improvements

#### 8. Update `_build_failed_edit_error_message` Method

- [ ] Detect when indentation appears to be the main issue
- [ ] Add specific guidance for indentation problems
- [ ] Include normalized text comparison in diagnostics
- [ ] Update error message templates for indentation-specific advice
- [ ] Add unit tests for indentation-specific error messages

## Testing Strategy

### Unit Tests

#### Core Indentation Utilities Tests

- [ ] Test `get_common_indent` with:
  - [ ] Consistent indentation
  - [ ] Varying indentation
  - [ ] Mix of empty and non-empty lines
  - [ ] Tabs vs spaces indentation
  - [ ] No indentation
  - [ ] Edge cases (single line, empty input)

- [ ] Test `strip_common_indent` with similar variations

#### Indentation Pattern Detection Tests

- [ ] Test `detect_indent_pattern` with:
  - [ ] More indentation in SEARCH than file
  - [ ] Less indentation in SEARCH than file
  - [ ] Different indentation types (spaces vs tabs)
  - [ ] Mixed indentation styles
  - [ ] Complex multi-level indentation

- [ ] Test `reindent_text` with similar variations

#### Enhanced Matching Tests

- [ ] Test both phases of matching:
  - [ ] Exact matches (should use fast path)
  - [ ] Indentation-only differences (should normalize)
  - [ ] Cases with both content and indentation differences

#### Error Message Tests

- [ ] Test improved error messages for:
  - [ ] Indentation-only failures
  - [ ] Mixed content and indentation failures
  - [ ] Verify helpful guidance is provided

### Integration Tests

- [ ] Test end-to-end process with:
  - [ ] Real-world code examples
  - [ ] Complex indentation patterns
  - [ ] Multi-paragraph blocks
  - [ ] Multiple language types

- [ ] Regression tests for known indentation issues

## Code Review Criteria

- [ ] Maintains backward compatibility
- [ ] Handles edge cases correctly
- [ ] Provides useful error messages
- [ ] Has comprehensive test coverage
- [ ] Follows Python best practices and project style guide

## Future Considerations

1. Extend this approach to handle other whitespace variations (line endings, trailing spaces)
2. Explore optional auto-correction for simple indentation issues
3. Add configuration options for indentation sensitivity levels
4. Investigate more sophisticated pattern recognition for complex indentation issues
5. Consider visual diffing in error outputs to better illustrate indentation problems
