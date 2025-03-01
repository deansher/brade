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

## Refined Approach: Line-Level Indentation Normalization

After further analysis, we've decided to implement a more direct approach using line-level indentation normalization. This approach maintains a 1:1 line correspondence between original and normalized text, making it easier to map matches back to the original content.

### Key Concept: Relative Indentation Markers

We'll normalize indentation by replacing each line's leading whitespace with a marker that indicates its relative indentation compared to the previous line. For example:

```python
def example():
    x = 1
    if x > 0:
        print("positive")
    else:
        print("non-positive")
```

Would be normalized to:

```
[[=]]def example():
[[+4]]x = 1
[[=]]if x > 0:
[[+4]]print("positive")
[[-4]]else:
[[+4]]print("non-positive")
```

Where `[[+4]]` indicates "indent 4 spaces more than previous line" and `[[-4]]` indicates "indent 4 spaces less than previous line". This preserves the code structure while normalizing away absolute indentation differences.

### Normalized Matching Algorithm

```python
def normalized_match_and_replace(file_content: str, search_text: str, replace_text: str, 
                               similarity_threshold: float = 0.5) -> tuple[str, bool]:
    """
    Match and replace text with normalization for indentation differences.
    
    Uses relative indentation markers to normalize text, then performs matching
    while maintaining 1:1 line correspondence with original text.
    
    Args:
        file_content: The entire file content to search within
        search_text: The text to search for (may have different indentation than file)
        replace_text: The text to replace the matched content with
        similarity_threshold: Minimum similarity score required for a match
        
    Returns:
        tuple[str, bool]: (Modified file content, success flag)
    """
    # Phase 1: Normalize both texts with relative indentation markers
    # --------------------------------------------------------------
    normalized_file = encode_relative_indentation(file_content)
    normalized_search = encode_relative_indentation(search_text)
    
    # Phase 2: Use diff-match-patch to find the best match
    # ----------------------------------------------------
    dmp = diff_match_patch()
    
    # Configure the matcher
    dmp.Match_Threshold = similarity_threshold
    dmp.Match_Distance = 1000  # Adjust as needed
    
    # Find the best match location
    match_loc = dmp.match_main(normalized_file, normalized_search, 0)
    
    if match_loc == -1:
        return file_content, False
    
    # Phase 3: Map match to original line ranges
    # ------------------------------------------
    # Since we have 1:1 line correspondence, we can map directly using line numbers
    
    # Get the lines before our match to count line numbers
    lines_before_match = normalized_file[:match_loc].count('\n')
    match_line_count = normalized_search.count('\n') + 1
    
    # Get original content lines
    file_lines = file_content.splitlines()
    
    # Extract the matched region in the original text
    start_line = lines_before_match
    end_line = start_line + match_line_count
    matched_original = '\n'.join(file_lines[start_line:end_line])
    
    # Phase 4: Prepare replacement with proper indentation
    # ---------------------------------------------------
    # Analyze indentation pattern of matched text
    indent_pattern = analyze_indentation_pattern(matched_original)
    
    # Apply appropriate indentation to replacement text
    indented_replacement = apply_indentation_pattern(replace_text, indent_pattern)
    
    # Phase 5: Perform the replacement
    # -------------------------------
    result_lines = file_lines.copy()
    result_lines[start_line:end_line] = indented_replacement.splitlines()
    result = '\n'.join(result_lines)
    
    return result, True

def encode_relative_indentation(text: str) -> str:
    """
    Encode text with relative indentation markers.
    
    This preserves the structural relationship between lines while
    normalizing away absolute indentation differences.
    
    Args:
        text: Source text
        
    Returns:
        str: Text with relative indentation markers
    """
    lines = text.splitlines()
    normalized_lines = []
    prev_indent = 0
    
    for line in lines:
        # Skip empty lines or preserve them without modification
        if not line.strip():
            normalized_lines.append("")
            continue
        
        # Calculate line indentation
        indent = len(line) - len(line.lstrip())
        
        # Calculate relative change from previous line
        rel_indent = indent - prev_indent
        
        # Create normalized line with relative indent marker
        if rel_indent == 0:
            marker = "[[=]]"
        else:
            marker = f"[[{rel_indent:+d}]]"
        
        normalized_lines.append(f"{marker}{line.lstrip()}")
        
        # Update prev_indent for next line
        prev_indent = indent
    
    return '\n'.join(normalized_lines)

def analyze_indentation_pattern(text: str) -> dict:
    """
    Analyze the indentation pattern of a text block.
    
    Args:
        text: Text block to analyze
        
    Returns:
        dict: Information about indentation pattern
    """
    lines = text.splitlines()
    base_indent = None
    indent_structure = []
    
    for line in lines:
        if not line.strip():
            # Skip empty lines
            indent_structure.append(None)
            continue
            
        # Get line indentation
        indent = len(line) - len(line.lstrip())
        
        # If this is the first non-empty line, set as base
        if base_indent is None:
            base_indent = indent
            relative_indent = 0
        else:
            relative_indent = indent - base_indent
            
        indent_structure.append(relative_indent)
    
    return {
        "base_indent": " " * (base_indent or 0),
        "structure": indent_structure
    }

def apply_indentation_pattern(text: str, pattern: dict) -> str:
    """
    Apply an indentation pattern to text.
    
    Args:
        text: Text to indent
        pattern: Indentation pattern (from analyze_indentation_pattern)
        
    Returns:
        str: Text with applied indentation pattern
    """
    lines = text.splitlines()
    result_lines = []
    base_indent = pattern["base_indent"]
    
    # First, normalize the replacement text to get its own structure
    normalized_replacement = encode_relative_indentation(text)
    replacement_lines = normalized_replacement.splitlines()
    
    for i, line in enumerate(lines):
        if not line.strip():
            # Preserve empty lines
            result_lines.append("")
            continue
            
        # Get indentation for this line
        if i < len(pattern["structure"]) and pattern["structure"][i] is not None:
            # If we have a pattern for this line, use it
            indent_level = pattern["structure"][i]
            line_indent = base_indent + " " * indent_level
        else:
            # Otherwise, use base indentation
            line_indent = base_indent
            
        # Add indented line
        result_lines.append(f"{line_indent}{line.lstrip()}")
    
    return '\n'.join(result_lines)

## Implementation Plan

### Core Indentation Utilities

#### ( ) Implement `get_common_indent` Function

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

- ( ) Implement function to find common leading whitespace in a list of lines
- ( ) Handle empty lines by ignoring them in calculations
- ( ) Return empty string if any non-empty line has no indentation
- ( ) Add unit tests for various indentation patterns

#### ( )Implement `strip_common_indent` Function

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

- ( ) Split text into lines
- ( ) Find common indent using get_common_indent()
- ( ) Remove this indent from each non-empty line
- ( ) Preserve empty lines unchanged
- ( ) Return both normalized text and the removed common indent
- ( ) Add unit tests for various indentation scenarios

### Indentation Pattern Analysis

#### ( ) Implement `detect_indent_pattern` Function

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

- ( ) Compare original and matched text line-by-line
- ( ) Detect indentation type (spaces, tabs, mixed)
- ( ) Calculate average indentation depth 
- ( ) Return comprehensive indentation pattern information
- ( ) Add unit tests for different indentation patterns

#### ( )Implement `reindent_text` Function

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

- ( ) Apply indentation pattern to text
- ( ) Preserve relative indentation relationships
- ( ) Handle empty lines appropriately
- ( ) Add unit tests for verifying proper indentation application

### Enhanced Matching Logic

#### ( ) Implement `normalized_match_and_replace` Function

```python
def normalized_match_and_replace(whole: str, original: str, updated: str) -> str:
    """Match and replace with normalization of indentation."""
```

- ( ) Normalize indentation in search text and file content
- ( ) Find match locations in normalized texts
- ( ) Determine original indentation pattern at match location
- ( ) Apply equivalent indentation to replacement text
- ( ) Perform replacement with properly indented text
- ( ) Add unit tests for indentation-aware matching

#### ( ) Modify `replace_most_similar_chunk` Function

- ( ) First try exact matching (current behavior)
- ( ) On failure, try indentation-normalized matching
- ( ) Maintain high threshold (95%) for both methods
- ( ) Return early if exact matching succeeds
- ( ) Add unit tests to verify the two-phase approach

#### ( ) Update `do_replace` Function

- ( ) Pass appropriate context to replace_most_similar_chunk
- ( ) Ensure proper handling of indentation information
- ( ) Add unit tests for indentation-aware replacements

### Error Reporting Improvements

#### ( ) Update `_build_failed_edit_error_message` Method

- ( ) Detect when indentation appears to be the main issue
- ( ) Add specific guidance for indentation problems
- ( ) Include normalized text comparison in diagnostics
- ( ) Update error message templates for indentation-specific advice
- ( ) Add unit tests for indentation-specific error messages

## Testing Strategy

### Unit Tests

#### ( ) Core Indentation Utilities Tests

- ( ) Test `get_common_indent` with:
  - ( ) Consistent indentation
  - ( ) Varying indentation
  - ( ) Mix of empty and non-empty lines
  - ( ) Tabs vs spaces indentation
  - ( ) No indentation
  - ( ) Edge cases (single line, empty input)

- ( ) Test `strip_common_indent` with similar variations

#### ( ) Indentation Pattern Detection Tests

- ( ) Test `detect_indent_pattern` with:
  - ( ) More indentation in SEARCH than file
  - ( ) Less indentation in SEARCH than file
  - ( ) Different indentation types (spaces vs tabs)
  - ( ) Mixed indentation styles
  - ( ) Complex multi-level indentation

- ( ) Test `reindent_text` with similar variations

#### ( ) Enhanced Matching Tests

- ( ) Test both phases of matching:
  - ( ) Exact matches (should use fast path)
  - ( ) Indentation-only differences (should normalize)
  - ( ) Cases with both content and indentation differences

#### ( ) Error Message Tests

- ( ) Test improved error messages for:
  - ( ) Indentation-only failures
  - ( ) Mixed content and indentation failures
  - ( ) Verify helpful guidance is provided

### ( ) Integration Tests

- ( ) Test end-to-end process with:
  - ( ) Real-world code examples
  - ( ) Complex indentation patterns
  - ( ) Multi-paragraph blocks
  - ( ) Multiple language types

- ( ) Regression tests for known indentation issues

## Code Review Criteria

- Maintains backward compatibility
- Handles edge cases correctly
- Provides useful error messages
- Has comprehensive test coverage
- Follows Python best practices and project style guide

## Future Considerations

1. Extend this approach to handle other whitespace variations (line endings, trailing spaces)
2. Explore optional auto-correction for simple indentation issues
3. Add configuration options for indentation sensitivity levels
4. Investigate more sophisticated pattern recognition for complex indentation issues
5. Consider visual diffing in error outputs to better illustrate indentation problems
