# Task

Process exclusively the employments / professional stations substantiated in the provided documents. Create a separate page in the specified Nextcloud Collective for each identified employment or update a matching existing page.

## Inputs

- Collective: {{$flow.state.collective}}
- Documents: {{$flow.state.documents}}
- Already processed projects: {{$flow.state.projects}}

Use {{$flow.state.collective.id}} as the Collective ID. The documents are located in {{$flow.state.documents.documents}}. Use exclusively the document contents provided there and do not reload them.

## Mandatory Use of Nextcloud Tools

Use the actually available Nextcloud Collectives tools for all Collective and page operations.

- Check the specified collective and determine the existing pages.
- For each employment, check if a matching page already exists.
- If existing pages are found, use their actual Page ID and actual page name.
- If no matching page exists, determine the next available number in the employment pages range and create the page using the designated naming scheme.
- Verify successful creation before writing the page content.
- Write the complete page content using the corresponding Nextcloud tool.
- Check whether the write operation was successful based on the actual tool response.

Never invent, guess, or adopt Page IDs from examples. A planned tool call is not an executed action. Success may only be reported if creation or update and writing were actually successfully confirmed.

## Identifying and Merging Employments

- Identify all actually substantiated employments and professional stations in all provided documents.
- Process each employment individually and sequentially.
- Merge information from multiple documents only if it is clearly recognizable that they concern the same employment.
- Do not invent employments and do not split an employment into multiple stations without clear evidence.
- Adopt existing formulations and sentences as verbatim as possible. Do not create new substantive statements and do not interpret missing information.
- Maintain the exact filenames and paths of the used sources.

## One Page per Employment

For each identified employment:

- Search for an already existing matching page in the Collective.
- If a matching page exists, use its actual Page ID and overwrite the page content completely. This is the initial creation of content for this processing step; existing content may be replaced.
- If no matching page exists, determine the next available number in the employment pages range.
- Use the schema `020-Employment-<Company>-<Position>` for new pages. Continue the numbering with the next available number. Existing page numbers must not be changed or renumbered.
- Create the page with an available Nextcloud tool and verify the actual creation.
- Afterwards, write the complete content of the page and confirm the successful write operation.

## Content of the Employment Page

Use exactly this structure:

# Employment: –

## Master Data
- Company:
- Position:
- Period:
- Location:
- Type of Employment:

## Role
- Responsibilities
- Tasks
- Projects
- Results and Successes
- Methods / Technologies
- Stakeholders / Collaboration
- Sources
- Notes

- Fill in only information that is substantiated by the provided documents. Adopt existing formulations as unchanged as possible. In particular, do not invent employers, positions, periods, locations, types of employment, responsibilities, tasks, results, technologies, or stakeholders.
- If information is not documented, leave the respective field empty or use an empty list structure. Do not replace missing information with assumptions.

## Project References
- In the Projects section, use only project pages whose actual page name and Page ID are confirmed by the existing Collective pages or by successfully processed entries in {{$flow.state.projects}}.
- Preferably use the already existing project names in the format `[[010-Project-...]]`.
- Link an employment to a project only if the assignment is clearly evident from the documents.
- Do not invent project names, page numbers, or project assignments.
- If no clear assignment is substantiated, leave the section empty.

## Sources
- List all used source documents with the exact filename and path. Use exclusively documents from {{$flow.state.documents.documents}}.

## Open Questions
- Capture missing or unclear information as open questions in the metadata of the Output JSON. Do not write open questions into the page content.
- Each open-questions group must be uniquely assigned to the corresponding employment page via the actual `page_id`. Formulate concrete, factual questions without inventing answers or assumptions. For every successfully processed employment page, output an entry, even if its `questions` array is empty.

## Processing and Error Handling

- Process all identified employments sequentially. Complete one employment fully before starting the next.
- If an employment cannot be successfully created, updated, and described:
    - Set the overall result to `success: false`.
    - Do not include the failed employment as a successfully processed page in `pages`.
    - Do not invent a Page ID and do not output an unconfirmed page as successful.
    - Continue with the remaining employments if possible.
    - Retain all already successfully processed entries in `pages` and `open_questions`.
- If no employments are substantiated in the documents and the check is successfully completed, return `success: true` along with empty arrays for `pages` and `open_questions`.

## Output

Output exclusively a valid JSON object that corresponds to the defined Structured Output. No Markdown, no explanations, and no additional text outside the JSON object.

`success` may only be `true` if all identified employments were successfully created or updated, fully described, and their write operations were actually confirmed. If at least one employment could not be successfully processed, `success` must be `false`.

The page contents themselves do not belong in the Output JSON. Output only the processing result and the metadata.
