# Task

Create a persistent page in the target Collective from the collected open questions.

The previously collected processing results are located in the following Flow-State variables:

- {{$flow.state.person}}
- {{$flow.state.projects}}
- {{$flow.state.employments}}
- {{$flow.state.education}}
- {{$flow.state.certificates}}
- {{$flow.state.skills}}
- {{$flow.state.sources}}

The target Collective is located in:

{{$flow.state.collective}}

Analyze exclusively the current content of these Flow-State variables. Extract all existing `open_questions` from them.

Do not invent questions, do not answer questions, and do not supplement information that is not contained in the Flow-State variables.

## Collective and Page Management

You must use the actually available Nextcloud Collectives tools for all work on the Collective.

Use the Collective specified in {{$flow.state.collective}}. Use its actual ID from {{$flow.state.collective.id}}.

Check with the available Nextcloud tools if the page `004-OpenQuestions` already exists.

- If the page does not exist, create it in the specified Collective.
- If the page already exists, overwrite its previous content completely with the current state from the Flow-State variables.

Use exclusively actual values from tool responses.

Never create, guess, or adopt a Page ID from examples.

- If an existing page is found, use the actual returned Page ID.
- If a new page is created, use the actual Page ID returned by the tool.

Write the complete Markdown content into the page using the designated Nextcloud tool.

Verify the successful write operation based on the actual tool response. Read the stored content again if possible and check if it matches the intended content.

Do not set `success` in a Flow-variable, as this agent does not generate a Flow-variable. Do not claim success unless the writing process was actually confirmed by a real tool response.

This processing is part of the initial workflow. It is not a step-by-step maintenance of an existing Open-Questions page. The previous content is completely replaced by the current state.

## Purpose of the Page

The page `004-OpenQuestions` serves as a permanent repository of questions and tasks for the later maintenance workflow.

Questions must be stored exclusively in a structured, traceable way, along with a processing status. They must neither be answered nor interpreted.

The later maintenance workflow can load this page during every run and specifically address open questions.

## Rules for Extraction

Adopt every open question found in the following Flow-State variables under `open_questions`:

- {{$flow.state.person}}
- {{$flow.state.projects}}
- {{$flow.state.employments}}
- {{$flow.state.education}}
- {{$flow.state.certificates}}
- {{$flow.state.skills}}
- {{$flow.state.sources}}

Observe the following rules:

- No existing open question may be omitted.
- The existing `question`-text must be adopted unchanged.
- The existing `context`-text must be adopted unchanged.
- Questions must not be summarized, reformulated, corrected, or changed in content.
- Assign each question to the area it originated from in the Flow-State variable.
- If a question belongs to a specific page, adopt the actual `page_name` and the actually confirmed `page_id` from the associated Flow-State variable.
- If no Page ID is present, do not invent or derive one from the page name. Omit the Page ID field in this case.
- If no page name is present, do not invent one. Omit the page field in this case.
- Do not create additional questions based on contexts, missing information, or your own conclusions.
- Do not change the contents of the original Flow-State variables.

If a Flow-State variable does not contain `open_questions` or the list is empty, do not adopt any questions from it.

## Page Structure

Create the page with the following Markdown structure. Adjust the number of questions and sub-sections to the actual data present. Do not create empty question entries.

# Offene Fragen

This page contains open information questions from the initial processing of the profile.

The questions will be processed in the later maintenance workflow.

## Bearbeitungsstatus

- [ ] = open
- [x] = resolved

---

## Person

### Question 1
- [ ] **Question:** <unchanged question-text>
- **Context:** <unchanged context-text>
- **Source / Area:** Person
- **Status:** open

---

## Projekte

### <Actual Project Name>

#### Question 1
- [ ] **Question:** <unchanged question-text>
- **Context:** <unchanged context-text>
- **Source / Area:** Project
- **Page:** <actual page name, if present>
- **Page-ID:** <actual page_id, if present>
- **Status:** open

---

## Anstellungen

### <Actual Employment>

#### Question 1
- [ ] **Question:** <unchanged question-text>
- **Context:** <unchanged context-text>
- **Source / Area:** Employment
- **Page:** <actual page name, if present>
- **Page-ID:** <actual page_id, if present>
- **Status:** open

---

## Ausbildung

### Question 1
- [ ] **Question:** <unchanged question-text>
- **Context:** <unchanged context-text>
- **Source / Area:** Education
- **Page:** <actual page name, if present>
- **Page-ID:** <actual page_id, if present>
- **Status:** open

---

## Zertifikate

### Question 1
- [ ] **Question:** <unchanged question-text>
- **Context:** <unchanged context-text>
- **Source / Area:** Certificates
- **Page:** <actual page name, if present>
- **Page-ID:** <actual page_id, if present>
- **Status:** open

---

## Skills

### Question 1
- [ ] **Question:** <unchanged question-text>
- **Context:** <unchanged context-text>
- **Source / Area:** Skills
- **Page:** <actual page name, if present>
- **Page-ID:** <actual page_id, if present>
- **Status:** open

---

## Quellen

### Question 1
- [ ] **Question:** <unchanged question-text>
- **Context:** <unchanged context-text>
- **Source / Area:** Sources
- **Page:** <actual page name, if present>
- **Page-ID:** <actual page_id, if present>
- **Status:** open

---

## Zusammenfassung

- Total Open Questions: <actual count>
- Open: <actual count>
- Resolved: 0

### Structuring Rules

- Use the actual name from the associated Flow-State data for projects and employments, if present.
- Group multiple questions from the same page under a common page or project name if the assignment is clearly evident from the data.
- Number the questions within the respective group sequentially.
- Adopt all questions exactly once.
- If an area contains no open questions, no empty question section for that area should be created.
- Sections and field labels must be uniform and easy to read.
- Leave non-existent metadata out instead of inventing it.

### Processing Status

Every newly adopted question initially receives the status:
- [ ]

Additionally, the status must be:
Status: open

No question may be marked as resolved in the initial workflow.
The initial workflow does not answer open questions and does not change their substantive meaning.
The checkbox is a persistent processing state for the later maintenance workflow. Only the later maintenance workflow may set a checkbox to - [x] after successful processing and change the status to resolved.

The summary must be calculated from the actually adopted questions:
- Total Open Questions: Total number of all adopted questions.
- Open: Number of all newly adopted questions that have the status "open".
- Resolved: Always 0 in the initial workflow.

### No Open Questions

If no open questions are present in any of the following Flow-State variables:

- {{$flow.state.person}}
- {{$flow.state.projects}}
- {{$flow.state.employments}}
- {{$flow.state.education}}
- {{$flow.state.certificates}}
- {{$flow.state.skills}}
- {{$flow.state.sources}}

still create or overwrite the page.
Then use exactly the following content:

# Offene Fragen

No open questions from the initial processing are present.

## Zusammenfassung

- Total Open Questions: 0
- Open: 0
- Resolved: 0

### Do Not Create New Questions

This subagent must not create any additional questions.
Only questions that are already present under `open_questions` in the following Flow-State variables may be adopted:

- {{$flow.state.person}}
- {{$flow.state.projects}}
- {{$flow.state.employments}}
- {{$flow.state.education}}
- {{$flow.state.certificates}}
- {{$flow.state.skills}}
- {{$flow.state.sources}}

Do not supplement questions based on perceived missing information, personal assessments, or the overall task context.

## Error Handling

If the target collective cannot be found, a required page cannot be created or updated, or the write operation is not successfully confirmed, do not claim that the task was successfully completed.

Use exclusively the actually available Nextcloud-Collectives-Tools and their documented parameters. Never invent tool names, IDs, or tool results.

## Output

Output exclusively the complete JSON object according to the defined Structured Output. No Markdown and no additional explanations outside the JSON object.

`success` may only be `true` if either no questions were found and the check was successful, or the required page was actually created or updated, fully described, and the write operation was confirmed.

The page contents themselves do not belong in the Output JSON. This contains exclusively the processing result and the metadata.
