# Task

Process exclusively the skills and competencies substantiated in the provided documents. If corresponding information is present, create or update the page `032-Skills` in the specified Nextcloud Collective.

## Inputs

- Collective: {{$flow.state.collective}}
- Documents: {{$flow.state.documents}}

Use {{$flow.state.collective.id}} as the Collective ID. The documents are located in {{$flow.state.documents.documents}}. Use exclusively the provided document contents and do not reload them.

## Mandatory Use of Nextcloud Tools

Use the actually available Nextcloud Collectives tools for all work on the Collective.

- Check the specified collective and determine the existing pages.
- Identify all actually substantiated skills and competencies in the provided documents.
- If skills or competencies are present, check if the page `032-Skills` already exists.
- If the page exists, use its actual Page ID and overwrite the content completely.
- If the page does not exist, create it with the exact name `032-Skills` and verify successful creation.
- Write the complete page content using the corresponding Nextcloud tool.
- Check whether the write operation was successful based on the actual tool response.

Never invent, guess, or adopt Page IDs from examples. A planned tool call is not an executed action. Report success only if the actual creation or update and writing were confirmed.

If no skills or competencies are substantiated in the documents, do not create or update a page. Return `success: true` and empty arrays for `pages` and `open_questions` upon successful check.

## Identifying and Merging Skills and Competencies

Identify all actually substantiated:
- Professional competencies
- Technical competencies
- Methods
- Tools and technologies
- Knowledge
- Language skills
- Other explicitly substantiated competencies

- Merge information from multiple documents only if it is clearly recognizable that they concern the same skill or competency.
- Do not invent skills and do not supplement missing information with assumptions. Do not derive a competency solely from an activity, position, education, or project unless it is explicitly or clearly substantiated.
- Do not invent competency levels, seniority, ratings, certifications, or experiences.
- Adopt existing formulations and terms as verbatim as possible. Do not create new substantive statements. If only a skill term is mentioned, adopt only that term and do not add an unsubstantiated description.
- Maintain the exact filenames and paths of the used source documents.

## Content of the 032-Skills Page

Use the following structure:

# Skills

## Professional Skills
### Category:
### Description / substantiated formulation:
### Context / evidence:

## Technical Skills
### Category:
### Description / substantiated formulation:
### Context / evidence:

## Methods
### Description / substantiated formulation:
### Context / evidence:

## Tools / Technologies
### Description / substantiated formulation:
### Context / evidence:

## Languages
### Description / substantiated formulation:
### Context / evidence:

## Other substantiated competencies
### <Skill / Competency>
### Description / substantiated formulation:
### Context / evidence:

- Use only categories for which corresponding information is actually present in the documents. Create a separate section for each substantiated skill or competency.
- Fill in only information that is substantiated by the documents. If a category or detail is not substantiated, leave it out. If a skill appears multiple times, merge the evidence if it is clearly the same skill.
- At the end of the page, add the following section:

## Sources
- 

## Notes
<Only substantiated notes; otherwise leave empty>

## Open Questions

If details regarding a skill or competency are missing or unclear, capture them as open questions in the Output JSON metadata. Do not write these questions into the page content.

Since all skills are on a single common page, all questions must be uniquely assigned to the actual `page_id` of the `032-Skills` page.

Formulate concrete, factual questions. Do not invent answers. If no open questions exist, return an empty `questions` array for the page.

## Processing and Error Handling

- Process all identified skills and competencies consistently on the common page `032-Skills`.
- If skills or competencies are present:
    - Create or update the page.
    - Write the complete content.
    - Verify the successful write operation.
    - If successful, return the actual Page ID and the actual page name.
- If creation, update, or writing fails:
    - Set `success: false`.
    - Do not include an unconfirmed page in `pages`.
    - Return `open_questions` as an empty array if no successfully processed page exists.
    - Do not invent a Page ID.
- If no skills or competencies are substantiated and the check is successfully completed, return `success: true`, `pages: []`, and `open_questions: []`.

## Output

Return exclusively the complete JSON object according to the defined Structured Output. No Markdown and no additional explanations outside the JSON object.

`success` may only be `true` if either no skills or competencies were found and the check was successful, or the required page was actually created or updated, fully described, and the write operation was confirmed.

The page contents themselves do not belong in the Output JSON. This contains exclusively the processing result and the metadata.
