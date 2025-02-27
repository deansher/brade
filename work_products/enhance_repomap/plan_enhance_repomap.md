# Enhance Repomap

Brade and Dean are using this document to support their collaborative process. Brade is an AI software engineer collaborating with Dean through the Brade application. We are working together to enhance the Brade application's code. This is an interesting recursive situation where Brade is helping improve her own implementation.

We want to work efficiently in an organized way. For the portions of the code that we must change to meet our functionality goals, we want to move toward beautiful, idiomatic Python code. We also want to move toward more testable code with simple unit tests that cover the most important paths.

This document contains three kinds of material:

- requirements
- specific plans for meeting those requirements
- our findings as we analyze our code along the way

For major step of the work, (each top-level bullet of each "### ( ) task" section) we will follow this process:

- Make sure our plan is current.
- Make sure we have the information we need for our next step.
  - Writing down any new findings in this document.
  - Correct anything we previously misunderstood.
- Make sure existing unit tests pass.
- Consider whether to add unit tests or do manual testing before making the code changes.
- Make the code changes.
- Run the unit tests.
- Manually validate the change.

We only intend for this plan to cover straightforward next steps to our next demonstrable milestone. We'll extend it as we go.

We write down our findings as we go, to build up context for later tasks. When a task requires analysis, we use the section header as the task and write down our findings as that section's content.

For relatively complex tasks that benefit from a prose description of our approach, we use the section header as the task and write down our approach as that section's content. We nest these sections as appropriate.

For simpler tasks that can be naturally specified in a single sentence, we move to bullet points.

We use simple, textual checkboxes at each level of task, both for tasks represented by section headers and for tasks represented by bullets. Like this:

```
### ( ) Complex Task.

- (✅) Subtask
  - (✅) Subsubtask
- ( ) Another subtask
```

## Requirements

We will improve the repo map in small, safe steps. We'll do this gradually over a period of time, making a few careful changes and then getting practical experience with the effect of those enhancements before proceeding further. We will update this plan and `test_repomap.py` at each step.

## Tasks

### ( ) Add Documentation Context

Tree-sitter can identify documentation comments. We should show these above definitions to provide better context about purpose and usage.

#### Requirements

1. Documentation comments should be shown above their associated definitions
2. Support common documentation formats:
   - Python docstrings (""" and ''')
   - JavaScript/TypeScript // and /* */ comments
   - Java/C++ /** */ comments
   - Other language-specific formats

#### Implementation Steps

- ( ) Analyze tree-sitter query files to identify which already capture doc comments
- ( ) Modify tree-sitter queries as needed to capture doc comments
- ( ) Update TreeContext to:
  - ( ) Associate doc comments with their definitions
  - ( ) Include doc comments in context display
  - ( ) Handle multi-line comments appropriately
- ( ) Add test cases for:
  - ( ) Python docstrings
  - ( ) JavaScript/TypeScript comments
  - ( ) Multi-line comment formatting
  - ( ) Edge cases (multiple comments, nested definitions)

### ( ) Add Relationship Context

Tree-sitter can identify inheritance and implementation relationships. We should show these to help understand code organization.

#### Requirements

1. For classes, show:
   - Parent classes they inherit from
   - Interfaces they implement
   - Inner classes/methods they contain
2. Support common OOP languages:
   - Python class inheritance
   - TypeScript/JavaScript class extends
   - Java/C++ class inheritance
   - Interface implementations

#### Implementation Steps

- ( ) Analyze tree-sitter query files to identify relationship captures
- ( ) Modify queries as needed to capture relationships
- ( ) Update TreeContext to:
  - ( ) Track parent/child class relationships
  - ( ) Track interface implementations
  - ( ) Show relationships in rendered output
- ( ) Add test cases for:
  - ( ) Basic inheritance
  - ( ) Multiple inheritance
  - ( ) Interface implementation
  - ( ) Nested class definitions
