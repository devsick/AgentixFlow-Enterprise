# Task

Process exclusively the degree programs, vocational training, and further training substantiated in the provided documents. If corresponding information is present, create or update the page `030-Ausbildung` in the specified Nextcloud Collective.

## Inputs

- Collective: {{$flow.state.collective}}
- Documents: {{$flow.state.documents}}

Use {{$flow.state.collective.id}} as the Collective ID. The documents are located in {{$flow.state.documents.documents}}. Use exclusively the provided document contents and do not reload them.

## Mandatory Use of Nextcloud Tools

Use the actually available Nextcloud Collectives tools for all work on the Collective.

- Check the specified collective and determine the existing pages.
- Identify all substantiated education, degree, and training information in the provided documents.
- If such information is present, check if the page `030-Ausbildung` already exists.
- If the page exists, use its actual Page ID and overwrite the content completely.
- If the page does not exist, create it with the exact name `030-Ausbildung` and verify successful creation.
- Write the complete page content using the corresponding Nextcloud tool.
- Check whether the write operation was successful based on the actual tool response.

Never invent or guess Page IDs. Use exclusively actual values from tool responses. A planned tool call is not an executed action.

If no education, degree, or further training information is substantiated, do not create or update a page and return empty arrays upon successful check.

## Identifying and Merging Information

Identify all actually substantiated:
- Degree programs
- Vocational training
- Further training

- Merge information from multiple documents only if it is clearly recognizable that they concern the same training/education.
- Do not invent educational segments and do not supplement missing information with assumptions.
- Adopt existing formulations and sentences as verbatim as possible. Do not create new substantive statements.
- Maintain the exact filenames and paths of the source documents.

## Content of the 030-Ausbildung Page

Use the following structure:

# Ausbildung

## Studium
- Institution:
- Period:
- Degree:
- Field of study:

## Vocational Training
- Institution:
- Period:
- Degree:

## Further Training
- Provider:
- Period:
- Degree:

- Fill in only substantiated information. In particular, do not invent degree programs, institutions, periods, degrees, fields of study, vocational training, further training, or providers.
- If a category contains no substantiated information, leave it out. If an education is substantiated but individual details are missing, leave these fields empty instead of supplementing them.

## Sources
List all used source documents with exact filename and path at the end of the template.

## Notes
<Only substantiated notes; otherwise leave empty>

## Open Questions

Capture missing or unclear information as open questions in the Output JSON metadata. Do not write these questions into the page content.

Since all education information is located on a single common page, all open questions must be uniquely assigned to the actual `page_id` of the `030-Ausbildung` page.

Formulate concrete, factual questions. Do not invent answers. If no open questions exist, return an empty `questions` array for the page.

## Processing and Error Handling

- Process all education information consistently and write the complete page content in a single, continuous writing operation.
- If education information is present and the page is successfully created or updated and described, return `success: true` and the actual page in `pages`.
- If creation, update, or writing fails:
    - Return `success: false`.
    - Do not include an unconfirmed page in `pages`.
    - Do not invent a Page ID.
    - Return `open_questions` as an empty array if no successfully processed page exists.
- If no education, degree, or further training information is substantiated and the check is successfully completed, return `success: true` with empty arrays for `pages` and `open_questions`.

## Output

Return exclusively the complete JSON object according to the defined Structured Output. No Markdown and no additional explanations outside the JSON object.

`success` may only be `true` if either no corresponding information was found and the check was successful, or the required page was actually created or updated, fully described, and the write operation was confirmed.

The page contents themselves do not belong in the Output JSON. This contains exclusively the processing result and the metadata.
