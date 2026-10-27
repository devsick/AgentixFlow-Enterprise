# Task
Extract all employment and professional experience stations from the provided `documents` into a JSON object with the key `employments`.

# Reasoning Guidelines
- **Do not reconstruct the entire document in your thoughts.** Avoid exhaustive, line-by-line summaries or manual re-typing of the data during the reasoning phase.
- **Focus on mapping, not re-writing.** Use your thoughts only to resolve ambiguities, handle complex overlaps (e.g., projects within an employment), or decide how to map specific details to the schema.
- **Be concise.** Once you have identified the mapping for a station, move immediately to the output. Do not loop through every field individually in your thoughts.

# Extraction Rules
- Identify and extract data exclusively from documents that function as CVs, résumés, or professional profiles.
- Preserve the original language of the source documents throughout the extraction.
- Use the exact, original wording for all extracted content, especially for the `description` field.
- **Mandatory `company_organization`:** Every employment entry must have a non-empty `company_organization`. If no formal company name is found, use the most descriptive contextual heading or a summary of the activity (e.g., "Praktika im Rahmen des Studiums" or "diverse Büro- und Programmiertätigkeiten") to ensure this field is always populated.
- If no position is mentioned, use an empty string `""`.

# Output Format
Return a single JSON object following this schema:
{
  "employments": [
    {
      "company_organization": "string",
      "employment_start": "string",
      "employment_end": "string",
      "position": "string",
      "employment_type": "string",
      "location": "string",
      "description": "string",
      "responsibilities": ["string"],
      "own_activities": ["string"],
      "skills": ["string"],
      "methods_technologies": ["string"],
      "stakeholders_collaboration": ["string"],
      "results": ["string"],
      "measurable_results": ["string"],
      "sources": ["string"],
      "notes": ["string"],
      "open_questions": ["string"]
    }
  ]
}
