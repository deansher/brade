# Plan for Adding Heuristics for Quotes and Lists

Although you are an AI, you are a capable and experienced software engineer. You and I often collaborate on projects. You defer to my leadership, but you also trust your own judgment and challenge my decisions when you think that's important. We both believe strongly in this tenant of agile: use the simplest approach that might work.

We are collaborating to enhance our TypeScript project as described below. We want to work efficiently in an organized way. For the portions of the code that we must change to meet our functionality goals, we want to move toward beautiful, idiomatic TypeScript code. We also want to move toward more testable code with simple unit tests that cover the most important paths.

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

- (✅) Subtask
  - (✅) Subsubtask
- ( ) Another subtask
```

## Requirements

1. Implement a heuristic for quotes where ALEX explains it's not a search engine and can't provide reliable quotes.
2. Implement heuristics for lists that detect cases where the user's request means ALEX's response will need to include a list.
3. Update the prompting logic to allow lists when appropriate and provide clear instructions when lists are not allowed.
4. Ensure the new heuristics integrate seamlessly with the existing `initialHeuristicManager` in `ChatLogicProvider.ts`.
5. Maintain the current style and structure of heuristics implementation.

## ( ) Analyze Existing Heuristics

Before implementing the new heuristics, let's analyze the existing heuristics in `ChatLogicProvider.ts` to understand the current structure and implementation.

### Existing Heuristics Analysis

The `initialHeuristicManager` in `ChatLogicProvider.ts` contains several sections of heuristics. One comparable example is the `bookRecommendationGoalCode`:

```typescript
export const bookRecommendationGoalCode = userGoalSection.add(
  "Your coachee wants book recommendations."
);
```

This heuristic is part of the `userGoalSection` and is used to detect when a user is asking for book recommendations.

Key observations:
1. Heuristics are added to specific sections (e.g., `userGoalSection`) of the `initialHeuristicManager`.
2. Each heuristic is defined using the `add` method of the section.
3. The heuristic description is a simple string that describes the user's intent or the situation.

The new heuristics for quotes and lists will follow a similar structure but will have some key differences:

1. The quotes heuristic will focus on detecting requests for quotes and trigger a specific response from ALEX.
2. The lists heuristics will detect situations where a list is appropriate in ALEX's response, rather than detecting a specific user request.
3. The lists heuristics will influence the prompting logic to allow or disallow lists in ALEX's responses.

## ( ) Implement Quotes Heuristic

- ( ) Add a new heuristic to the `userGoalSection` for detecting quote requests
- ( ) Update the prompting logic to handle the quotes heuristic

### Quotes Heuristic Implementation

We'll add the following heuristic to the `userGoalSection`:

```typescript
export const quoteRequestGoalCode = userGoalSection.add(
  "Your coachee is asking for quotes or requesting you to provide specific quotations."
);
```

This heuristic will be used to detect when a user is asking for quotes, allowing us to trigger a specific response from ALEX explaining that it's not a search engine and can't provide reliable quotes.

Certainly! I'll draft these two additional sections for our plan:

### ( ) Add two examples of the new quote heuristic in `chatExamples`

- ( ) Create the first example of a quote request scenario
- ( ) Create the second example of a quote request scenario
- ( ) Add both examples to the `chatExamples` object in `ChatLogicProvider.ts`

We'll add the following examples to the `chatExamples` object:

```typescript
quoteRequest1: {
  chat: [
    {
      role: "user",
      content: "Can you give me some quotes about leadership from famous CEOs?",
      initialHeuristics: [
        quoteRequestGoalCode,
        lackingContextSituationCode,
        ragFocus1UserMsg,
      ],
    },
  ],
},

quoteRequest2: {
  chat: [
    {
      role: "user",
      content: "I need a good quote about teamwork for my presentation. Any suggestions?",
      initialHeuristics: [
        quoteRequestGoalCode,
        lackingContextSituationCode,
        ragFocus1UserMsg,
      ],
    },
  ],
},
```

These examples will help illustrate how the `quoteRequestGoalCode` heuristic should be activated in different quote request scenarios.

## ( ) Implement Lists Heuristics

- ( ) Add new heuristics to the `userGoalSection` for detecting list-appropriate situations
- ( ) Update the prompting logic to handle the lists heuristics

### Lists Heuristics Implementation

We'll add the following heuristics to the `userGoalSection`:

```typescript
export const explicitListRequestGoalCode = userGoalSection.add(
  "Your coachee has explicitly asked you to make a list."
);

export const writingWithListGoalCode = userGoalSection.add(
  "Your coachee is asking for help with writing something, and the best way to write it will use a list."
);
```

These heuristics will be used to detect situations where a list is appropriate in ALEX's response, allowing us to adjust the prompting logic accordingly.

### ( ) Add two examples of each new list-appropriate-situation heuristic in `chatExamples`

- ( ) Create two examples for the explicit list request heuristic
- ( ) Create two examples for the writing with list heuristic
- ( ) Add all examples to the `chatExamples` object in `ChatLogicProvider.ts`

We'll add the following examples to the `chatExamples` object:

```typescript
explicitListRequest1: {
  chat: [
    {
      role: "user",
      content: "Can you give me a list of the top 5 qualities of effective leaders?",
      initialHeuristics: [
        explicitListRequestGoalCode,
        canHelpSituationCode,
        ragFocus1UserMsg,
      ],
    },
  ],
},

explicitListRequest2: {
  chat: [
    {
      role: "user",
      content: "Please provide a bullet-point list of ways to improve team communication.",
      initialHeuristics: [
        explicitListRequestGoalCode,
        canHelpSituationCode,
        ragFocus1UserMsg,
      ],
    },
  ],
},

writingWithList1: {
  chat: [
    {
      role: "user",
      content: "I need help writing an email to my team about our quarterly goals. Can you assist?",
      initialHeuristics: [
        writingWithListGoalCode,
        lackingContextSituationCode,
        ragFocus1UserMsg,
      ],
    },
  ],
},

writingWithList2: {
  chat: [
    {
      role: "user",
      content: "Help me draft an agenda for our upcoming leadership retreat.",
      initialHeuristics: [
        writingWithListGoalCode,
        lackingContextSituationCode,
        ragFocus1UserMsg,
      ],
    },
  ],
},
```

These examples will help illustrate how the `explicitListRequestGoalCode` and `writingWithListGoalCode` heuristics should be activated in different scenarios where a list might be appropriate in ALEX's response.

## ( ) Update Prompting Logic

- ( ) Modify the `makeOpeningSystemMessageForResponse` function to handle the new heuristics
- ( ) Update the `HOW_TO_RESPOND_HEADING` content to include instructions for quotes and lists

### Prompting Logic Update

**Note from Dean: 3.5 Sonnet is incorrect in its original answer wwhere it said to add the new prompting code to `howToRespondContent`. Instead, we should tell it to look at how the conditional prompts are handled for other heuristics.**

#### Hmm, let's ask Sonnet that question now:

##### Dean

Please study @plan-for-adding-heuristics-for-quotes-and-lists.md and @ChatLogicProvider.ts . Study where we have placed the conditional logic for other heuristic-code-driven prompts. With those examples in mind, where should we place the conditional logic for the new heuristics?

##### Sonnet

After studying both files, I can see that the conditional logic for heuristic-code-driven prompts is typically placed in the `makeInitialHeuristicsPrompt` function within `ChatLogicProvider.ts`. This function takes the `requestContext` and `heuristics` as parameters and returns an object with `initialHeuristicsPrompt` and `focusPromptOnNarrowHeuristic`.

For the new heuristics related to quotes and lists, we should follow the same pattern. Here's where and how we should add the conditional logic:

1. In the `makeInitialHeuristicsPrompt` function in `ChatLogicProvider.ts`.

2. We should add new conditional blocks for each of the new heuristics, similar to how other heuristics are handled. For example:

```typescript
function makeInitialHeuristicsPrompt(
  requestContext: RequestContext,
  heuristics: HeuristicCodeSet<"initialHeuristics">
): {
  initialHeuristicsPrompt: string;
  focusPromptOnNarrowHeuristic: boolean;
} {
  let prompt = "";

  // ... existing code ...

  if (heuristics.has(quoteRequestGoalCode)) {
    prompt += trimLines(`
      <p>
      Your coachee has asked for quotes or specific quotations. Explain that you're not a search engine and can't provide reliable quotes.
      Offer to help in other ways related to their goal, such as discussing the topic or providing general information from your knowledge.
      </p>
    `);
    return {
      initialHeuristicsPrompt: prompt,
      focusPromptOnNarrowHeuristic: true,
    };
  }

  if (heuristics.has(explicitListRequestGoalCode) || heuristics.has(writingWithListGoalCode)) {
    prompt += trimLines(`
      <p>
      In this case, it's appropriate to include a list in your response if it helps address your coachee's request effectively.
      Format any lists using 'ul' and 'li' tags for clarity.
      </p>
    `);
  } else {
    prompt += trimLines(`
      <p>
      Avoid using lists in your response. Instead, present information in a conversational, narrative format.
      If you need to present multiple points, do so within the flow of your paragraphs.
      </p>
    `);
  }

  // ... rest of the existing code ...

  return {
    initialHeuristicsPrompt: prompt,
    focusPromptOnNarrowHeuristic: false,
  };
}
```

This approach keeps the new heuristics consistent with the existing pattern in the codebase. It allows for specific instructions to be added to the prompt based on the detected heuristics, which will guide the AI's response in the subsequent steps of the conversation.

#### What Sonnet said originally (INCORRECT)

We'll modify the `makeOpeningSystemMessageForResponse` function to include logic for handling the new heuristics. Here's an example of how we might update the `HOW_TO_RESPOND_HEADING` content:

```typescript
let howToRespondContent: (string | StructuredContent)[] = [
  // ... existing content ...
];

if (initialHeuristics.has(quoteRequestGoalCode)) {
  howToRespondContent.push(
    trimLines(`
      <p>
      Your coachee has asked for quotes or specific quotations. Explain that you're not a search engine and can't provide reliable quotes.
      Offer to help in other ways related to their goal, such as discussing the topic or providing general information from your knowledge.
      </p>
    `)
  );
}

if (initialHeuristics.has(explicitListRequestGoalCode) || initialHeuristics.has(writingWithListGoalCode)) {
  howToRespondContent.push(
    trimLines(`
      <p>
      In this case, it's appropriate to include a list in your response if it helps address your coachee's request effectively.
      Format any lists using 'ul' and 'li' tags for clarity.
      </p>
    `)
  );
} else {
  howToRespondContent.push(
    trimLines(`
      <p>
      Avoid using lists in your response. Instead, present information in a conversational, narrative format.
      If you need to present multiple points, do so within the flow of your paragraphs.
      </p>
    `)
  );
}

// ... rest of the function ...
```

This update will provide clear instructions to ALEX based on the active heuristics, allowing for appropriate handling of quote requests and the use of lists when necessary.

## ( ) Implement Unit Tests

- ( ) Create unit tests for the new quotes heuristic
- ( ) Create unit tests for the new lists heuristics
- ( ) Update existing tests if necessary to accommodate the new heuristics

### Unit Tests Implementation

We'll add new unit tests to `ChatLogicProvider.test.ts` to ensure the new heuristics are working correctly. Here's an example of what these tests might look like:

```typescript
describe('Quotes and Lists Heuristics', () => {
  test('Quote request heuristic is activated', () => {
    const chatHistory = [
      { role: 'user', content: 'Can you give me a quote about leadership?' },
    ];
    const heuristics = chooseHeuristics(/* ... */);
    expect(heuristics.has(quoteRequestGoalCode)).toBe(true);
  });

  test('Explicit list request heuristic is activated', () => {
    const chatHistory = [
      { role: 'user', content: 'Please give me a list of leadership qualities.' },
    ];
    const heuristics = chooseHeuristics(/* ... */);
    expect(heuristics.has(explicitListRequestGoalCode)).toBe(true);
  });

  test('Writing with list heuristic is activated', () => {
    const chatHistory = [
      { role: 'user', content: 'Help me write an email outlining our project goals.' },
    ];
    const heuristics = chooseHeuristics(/* ... */);
    expect(heuristics.has(writingWithListGoalCode)).toBe(true);
  });
});
```

These tests will help ensure that our new heuristics are being activated correctly based on user input.

## ( ) Perform Manual Testing

- ( ) Test the quotes heuristic with various user inputs
- ( ) Test the lists heuristics with different scenarios
- ( ) Verify that ALEX's responses are appropriate based on the active heuristics

## ( ) Code Review and Refinement

- ( ) Review the implemented changes for code quality and consistency
- ( ) Refine the implementation based on review feedback
- ( ) Ensure all tests are passing

## ( ) Final Testing and Deployment

- ( ) Perform final round of testing in a staging environment
- ( ) Deploy the changes to production
- ( ) Monitor initial performance and user feedback
