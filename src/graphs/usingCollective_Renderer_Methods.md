# `collective_functions.py` – Architecture and usage of callbacks

## 1. Purpose of this file

`collective_functions.py` contains the common logic for importing entries into a Collective.

The file is designed to function independently of the type of data being imported. For example, it knows neither the domain structure of a project nor that of an employment.

The respective Node defines:

- which data is imported,
- which fields are relevant for validation,
- how an entry's name is formed,
- how a single entry page is represented as Markdown,
- which configuration is used for the import.

`collective_functions.py` then takes over the common processing:

- checking configuration,
- validating entries,
- searching for or creating an overview page,
- determining entry names via the configured callback,
- composing page titles,
- searching for existing pages or creating new pages,
- writing and verifying Markdown content,
- returning results and errors.

**Basic principle:** The Node describes the domain-specific details. `collective_functions.py` controls the general import process.

---

## 2. The principle of callback functions

A callback is a function that is not executed immediately, but is first passed to another function. This other function calls it later when needed.

In this project, the callback functions are passed via `CollectiveConfig`.

This is important because `import_collective_entries()` does not need to know which specific Node triggered the import.

### Example: Projects Node

In `extract_project_agent_node.py`, the configuration is created, for example, like this:

```python
config = CollectiveConfig(
    mode="overview_with_entries",
    overview_title=self.OVERVIEW_TITLE,
    entry_prefix=self.PROJECT_PREFIX,
    first_entry_number=self.FIRST_PROJECT_NUMBER,
    scalar_fields=self.PROJECT_SCALAR_FIELDS,
    list_fields=self.PROJECT_LIST_FIELDS,
    get_entry_name=self._project_name,
    render_entry=self._render_project_markdown,
    render_overview=self._render_overview_markdown,
    graph_id=state.get("graph_id"),
    run_id=state.get("run_id"),
)
```

The crucial lines are:

```python
get_entry_name=self._project_name,
render_entry=self._render_project_markdown,
```

Here, the methods are passed as function references.

Note that there are **deliberately no parentheses after the method name**. The functions should not be executed at this point.

### Example: Employments Node

The Employments Node uses the same common import function, but passes different callbacks:

```python
config = CollectiveConfig(
    mode="overview_with_entries",
    overview_title=self.OVERVIEW_TITLE,
    entry_prefix=self.EMPLOYMENT_PREFIX,
    first_entry_number=self.FIRST_EMPLOYMENT_NUMBER,
    scalar_fields=self.EMPLOYMENT_SCALAR_FIELDS,
    list_fields=self.EMPLOYMENT_LIST_FIELDS,
    get_entry_name=self._employment_name,
    render_entry=self._render_employment_markdown,
    render_overview=self._render_overview_markdown,
    graph_id=state.get("graph_id"),
    run_id=state.get("run_id"),
)
```

This way, `collective_functions.py` receives different functions for employments than for projects, without requiring a distinction between these data types within the common function.

---

## 3. Process when calling `import_collective_entries()`

The Node calls the common import function:

```python
imported = await import_collective_entries(
    client=mcp_client,
    collective_id=collective_id,
    entries=projects,
    config=config,
)
```

For employments, `entries=raw_employments` is passed accordingly.

The process within the common import function is simplified:

```python
validated_entries = validate_entries(entries, config)

for index, entry in enumerate(validated_entries):
    entry_number = config.first_entry_number + index

    entry_name = config.get_entry_name(entry)

    prefix = str(config.entry_prefix or "").strip("-_ ")
    name = str(entry_name).strip()

    title = (
        f"{entry_number:03d}-"
        f"{prefix + '-' if prefix else ''}"
        f"{name}"
    )

    content = config.render_entry(entry, config)

    # Subsequently:
    # - search for existing page or create new page
    # - update page
    # - write and verify Markdown
```

This example illustrates the callback principle. The actual function also includes error handling, logging, and further processing steps.

### What happens during the name callback?

At this line:

```python
entry_name = config.get_entry_name(entry)
```

the callback is actually executed.

- For Projects, `_project_name(entry)` is called.
- For Employments, `_employment_name(entry)` is called.

Which function is called is already specified in the configuration of the respective Node.

Therefore, the common import function does not need to check the class name of the Node or contain conditions like `if project` or `if employment`.

### What happens during the Markdown callback?

At this line:

```python
content = config.render_entry(entry, config)
```

the configured Markdown renderer is executed.

- For Projects, `_render_project_markdown()` should generate the project page.
- For Employments, `_render_employment_markdown()` should generate the employment page.

**Important:** The current call passes two arguments: `entry` and `config`. Therefore, the configured renderer method must match this signature.

---

## 4. Mandatory callback interfaces

In order for new Nodes to work reliably with `collective_functions.py`, the passed functions must accept the expected arguments.

### 4.1 `get_entry_name`

Expected call:

```python
entry_name = config.get_entry_name(entry)
```

Expected signature:

```python
def get_entry_name(entry: dict) -> str:
    ...
```

The function receives exactly one entry and returns its domain-specific name.

Example for Projects:

```python
@staticmethod
def _project_name(entry: dict) -> str:
    name = entry.get("project_name", "").strip()

    if not name:
        raise ValueError("Project is missing 'project_name'.")

    return sanitize_page_name(name)
```

Example for Employments:

```python
@staticmethod
def _employment_name(entry: dict) -> str:
    company = entry.get("company_organization", "").strip()
    position = entry.get("position", "").strip()

    parts = [part for part in (company, position) if part]
    name = " - ".join(parts)

    start = entry.get("employment_start", "").strip() or "?"
    end = entry.get("employment_end", "").strip() or "present"

    return sanitize_page_name(f"{name} ({start}-{end})")
```

The examples illustrate that the domain-specific name formation remains in the Node. The common import function does not need to know these details.

### 4.2 `render_entry`

Expected call:

```python
content = config.render_entry(entry, config)
```

Expected signature for a normal function:

```python
def render_entry(entry: dict, config: CollectiveConfig) -> str:
    ...
```

For an instance method, the implicit parameter `self` must also be taken into account:

```python
def _render_entry(
    self,
    entry: dict,
    config: CollectiveConfig,
) -> str:
    ...
```

For a `@staticmethod`, only the two explicit parameters are required.

**Caution with `@classmethod`:** A class method also receives the implicit parameter `cls`. A method with the signature `def _render_project_markdown(cls, entry)` will therefore not automatically accept the current call with `entry` and `config`. The signatures must match.

### 4.3 `render_overview`

The configuration can also contain a callback for the overview representation:

```python
render_overview=self._render_overview_markdown,
```

The desired interface depends on how the callback is used. The method shown so far expects:

```python
def _render_overview_markdown(entries: list[dict]) -> str:
    ...
```

**Current implementation status:** In the version of `import_collective_entries()` shown so far, `config.render_overview` is not called. Specifying it in the configuration alone does not yet cause the overview content to be rendered or written.

This callback should therefore not be confused with the actual entry page rendering function that is executed.

---

## 5. Meaning of the other configuration fields

The following fields describe the import and are not to be confused with callback functions.

| Configuration field | Meaning |
|---|---|
| `mode` | Sets the intended import mode. |
| `overview_title` | Title of the parent overview page. |
| `entry_prefix` | Prefix for the entry page titles. |
| `first_entry_number` | First running number of the entries. |
| `scalar_fields` | Names of fields with single values. |
| `list_fields` | Names of fields with list values. |
| `get_entry_name` | Callback for determining the entry name. |
| `render_entry` | Callback for creating the Markdown content of an entry page. |
| `render_overview` | Intended callback for creating the overview Markdown. |
| `graph_id` | Context for graph/node monitoring. |
| `run_id` | Context for assignment to a run. |

`scalar_fields` and `list_fields` describe the expected data structure. They do not automatically determine the headings or the order of sections in the Markdown. This design is handled in the respective renderer.

---

## 6. Rules for new Nodes

If a new Node is to use the same import function, the following rules apply.

1. **Define own data fields.**  
   The Node sets its `scalar_fields` and `list_fields` according to the data schema.

2. **Provide own name callback.**  
   The method must accept a single entry and return a suitable name.

3. **Provide own Markdown renderer.**  
   The method creates the complete Markdown content of a single entry page and must accept the signature used by `collective_functions.py`.

4. **Store callbacks in `CollectiveConfig`.**  
   The function references are passed without calling parentheses.

5. **Call the common import function.**  
   The Node passes the client, collective ID, entries, and configuration to `import_collective_entries()`.

6. **Do not add domain-specific special cases to `collective_functions.py`.**  
   Changes to the domain-specific name formation or individual Markdown layout belong fundamentally in the respective Node. The common import function remains responsible for the import process.

Example of the pattern:

```python
config = CollectiveConfig(
    mode="overview_with_entries",
    overview_title=self.OVERVIEW_TITLE,
    entry_prefix=self.ENTRY_PREFIX,
    first_entry_number=self.FIRST_ENTRY_NUMBER,
    scalar_fields=self.SCALAR_FIELDS,
    list_fields=self.LIST_FIELDS,
    get_entry_name=self._entry_name,
    render_entry=self._render_entry_markdown,
    render_overview=self._render_overview_markdown,
    graph_id=state.get("graph_id"),
    run_id=state.get("run_id"),
)

result = await import_collective_entries(
    client=mcp_client,
    collective_id=collective_id,
    entries=entries,
    config=config,
)
```

The names of the constants and methods here are placeholders and must match the respective Node.

---

## 7. Common sources of error

### Callback accidentally executed

Wrong:

```python
get_entry_name=self._project_name(entry)
```

Here, the method would be called already when creating the configuration. Furthermore, `entry` might not even be available at this point.

Right:

```python
get_entry_name=self._project_name
```

The method is only called later by `collective_functions.py`.

### Callback signature does not match

If the caller passes two arguments, but the function only accepts one, a `TypeError` occurs.

Therefore, always compare the actual call in `collective_functions.py` with the method signature in the Node.

### Page titles are cleaned twice or in the wrong place

The name callbacks should clean the domain-specific entry names if this is part of their intended task. Other titles, for example overview titles, may require a separate cleaning path.

### Configuration alone does not execute a function

Specifying

```python
render_overview=self._render_overview_markdown
```

does not execute the method. The corresponding callback must be explicitly called later.

---

## 8. Summary

The architecture is based on a clear division of tasks:

- **Node:** Knows the domain data and defines the appropriate callbacks.
- **`CollectiveConfig`:** Transports the function references and the import parameters.
- **`collective_functions.py`:** Calls the callbacks at the intended locations and controls the common import process.
- **`collective_pages.py`:** Provides functions for searching, creating, and managing Collective pages.