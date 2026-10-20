# Task

Process exclusively the certificates substantiated in the provided documents. If certificates are present, create or update the page `031-Zertifikate` in the specified Nextcloud Collective.

## Inputs

- Collective: {{$flow.state.collective}}
- Documents: {{$flow.state.documents}}

Use {{$flow.state.collective.id}} as the Collective ID. The documents are located in {{$flow.state.documents.documents}}. Use exclusively the provided document contents and do not reload them.

## Mandatory Use of Nextcloud Tools

Use the actually available Nextcloud Collectives tools for all work on the Collective.

- Check the specified collective and determine the existing pages.
- Identify all actually substantiated certificates in the provided documents.
- If certificates are present, check if the page `031-Zertifikate` already exists.
- If the page exists, use its actual Page ID and overwrite the content completely.
- If the page does not exist, create it with the exact name `031-Zertifikate` and verify successful creation.
- Write the complete page content using the corresponding Nextcloud tool.
- Check whether the write operation was successful based on the actual tool response.

Never invent or guess Page IDs. Use exclusively actual values from tool responses. A planned tool call is not an executed action. Report success only if the actual creation or update and writing were confirmed.

If no certificates are substantiated in the documents, do not create or update a page. Return `success: true` and empty arrays for `pages` and `open_questions` upon successful check.

## Identifying and Merging Certificates

- Identify all actually substantiated certificates in the provided documents.
- Merge information from multiple documents only if it is clearly recognizable that they concern the same certificate.
- Do not invent certificates and do not supplement missing information with assumptions.
- Adopt existing formulations and sentences as verbatim as possible. Do not create new substantive statements.
- Maintain the exact filenames and paths of the used source documents.

## Content of the 031-Zertifikate Page

Use the following structure:

# Zertifikate

## <Certificate Name>
- Provider:
- Date:
- Validity:
- Certificate number (if relevant):

Create a separate `## <Certificate>` section for each substantiated certificate.

- Fill in only information that emerges from the provided documents. In particular, do not invent certificate names, providers, dates, validity periods, or certificate numbers.
- If a detail is not documented, leave the corresponding field empty or omit it.

At the end of the page, add the following Sources section:

## Quellen
- 

## Notes
<Only substantiated notes; otherwise leave empty>

## Open Questions

If details regarding a certificate are missing or unclear, capture them as open questions in the Output JSON metadata. Do not write these questions into the page content.

All questions must be uniquely assigned to the actual `page_id` of the `031-Zertifikate` page.

Formulate concrete, factual questions. Do not invent answers. If no open questions exist, return an empty `questions` array for the page.

## Processing and Error Handling

- Process all identified certificates consistently on the common page `031-Zertifikate`.
- If certificates are present:
    - Create or update the page.
    - Write the complete content.
    - Verify the successful write operation.
    - If successful, return the actual Page ID and the actual page name.
- If creation, update, or writing fails:
    - Set `success: false`.
    - Do not include an unconfirmed page in `pages`.
    - Return `open_questions` as an empty array if no successfully processed page exists.
    - Do not invent a Page ID.
- If no certificates are substantiated and the check is successfully completed, return `success: true`, `pages: []`, and `open_questions: []`.

## Output

Return exclusively the complete JSON object according to the defined Structured Output. No Markdown and no additional explanations outside the JSON object.

`success` may only be `true` if either no certificates were found and the check was successful, or the required page was actually created or updated, fully described, and the write operation was confirmed.

The page contents themselves do not belong in the Output JSON. This contains exclusively the processing result and the metadata.
