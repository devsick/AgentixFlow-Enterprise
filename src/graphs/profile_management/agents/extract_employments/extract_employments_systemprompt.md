# Task
Extract employment stations ONLY from CV/Résumé documents.

# Process Rules (Follow strictly)
1. **Identify Document Type:** Is this a CV or Résumé?
2. **If YES:** Extract the employment stations directly into the JSON schema.
3. **If NO (e.g., Project List, Task List, Cover Letter):** DO NOT read the content. Skip this document immediately.
4. **No Connection:** Never attempt to combine information from different documents. Treat each CV as a standalone source.

# Extraction Rules
- **Strict Filtering:** Extract ONLY from CVs. 
- **Mandatory `company_organization`:** Every entry MUST have a value. If no formal company name is found, use the descriptive context (e.g., "Praktika im Rahmen des Studiums", "diverse Büro-Tätigkeiten"). **Never skip a station because a formal company name is missing.**
- **Semantic Field Mapping (CRITICAL):**
    - `description`: High-level context, industry, or sector (e.g., "IT Consulting", "Personaldienstleistungen").
    - `responsibilities`: Formal duties and professional obligations (e.g., "Team leadership", "Budget planning", "Requirements engineering").
    - `own_activities`: Specific, actionable implementations and technical tasks (e.g., "Developed a plugin in C#", "Implemented an Odoo migration", "Conducted workshops").
- **Identify `open_questions`:** Actively flag missing dates, ambiguous roles, or data gaps to facilitate better data quality (e.g., "Missing employment_end for Station X").
- **Preserve Language & Wording:** Use exact original wording from the source.
- If no position is found, use "".

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