# Plan for `BradeCoder`

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

This project is a fork of a project called aider. We want our changes to be minimally invasive to existing code to reduce merge conflicts when we pull updates from upstream.

Our fork introduces an AI persona named Brade, with extensive prompt changes to make Brade interact and perform differently than aider's (very basic) persona. So far, we have made these changes by editing prompts throughout aider's `Coder` subclasses. But now, instead, we want to introduce a new `Coder` subclass called `BradeCoder`:

- `BradeCoder` will now handle the "diff" edit format instead of `EditBlockCoder` handling it.
- `BradeCoder` will rely on a new `BradePrompts` class for its prompts as much as reasonably feasible, instead of referencing them from other coder or prompt classes.
  - Initially, the prompts in `BradePrompts` will be identical to the ones we are currently using for `EditBlockCoder`. (These are largely defined in `EditBlockPrompts` and `CoderPrompts`.)
  - `BradePrompts` will not be a subclass of `CoderPrompts`, because we will use a different approach to prompt generation.
  - Our new approach to prompt generation in `BradePrompts` will be to invoke a method that takes the current chat history as an argument and returns the prompt. (In early versions, we will ignore the chat history argument.)
  - We will name these prompt generations like `make_foo_prompt`. 
  - For example, instead of just referencing `main_system` to get the main system prompt, we will now invoke the method `make_main_system_prompt`.
- `BradeCoder` will construct its own internal `EditBlockCoder` and will reuse its code to the extent reasonably feasible by delegating to it.
- `BradeCoder` will use a subordinate architect model. See [Subordinate Architect Model](#subordinate-architect-model) for details.

### Subordinate Architect Model

Having experimented with `ArchitectCoder` and its use of a subordinate `editor_coder`, we see many benefits, but we want `BraderCoder` to organize the architect versus editor role differently.

We've experimented with using o1-preview as our architect. It generates a lot of material. And it appears to be material that will help the `editor_coder` a lot.

But it also generates considerably more material than the user wants to review. The user would be happier with an overview that helps them understand the proposed direction and either say yes or give feedback.

Plus, conversation with the architect/editor combination is awkward. The `[Y]es` or `[N]o` decision that we ask the user to make on the transition from architect to editor is unnatural and hard to understand.

Putting all this together, we have decided to make `BradeCoder` the speaking and listening voice in all conversations with the user, and having it delegate to the architect model (not to an architect coder) when it needs expert input.  `BradeCoder` will decide when to invoke the architect model. When it does invoke the architect model, it will keep the architect model's full output to itself, just using it as a resource both for conversation with the user and for coding.

## ( ) Investigate how chat history is managed and represented in aider.

Because our prompt generation methods will take the chat history as an argument, we must understand how the chat history is represented and managed in the current aider codebase and then how to represent it as an argument.

## ( ) Define the API for `BradePrompts`.

## ( ) Write an initial version of `BradePrompts`.

## ( ) Write an initial version of `BradeCoder`.

This first version will not yet use a subordinate architect model. Instead, it will behave like `EditBlockCoder` does today.

## ( ) Change higher-level code to have `BradeCoder` handle the "diff" edit format instead of `EditBlockCoder`.

## ( ) Introduce "situation analysis" into `BraderCoder`'s prompt generation.

## ( ) Revert our prompt-related changes to other `FooCoder` and `FooPrompts` classes.

Compare our `brade` branch with the `main` branch from upstream and revert `FooCoder` and `FooPrompts` changes to the extent reasonably feasible.
