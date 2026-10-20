# Muster: Agent & Node Implementierung (Profile Management)

Dieses Dokument beschreibt das standardisierte Schema für die Erstellung neuer Agenten und deren Anbindung an den Graph innerhalb des `profile_management` Flows.

## 1. Die Agent-Struktur (`agents/<agent_name>/<agent_name>.py`)

Jeder Agent ist eine eigenständige Klasse, die für eine spezifische Teilaufgabe verantwortlich ist.

### A. Template-Code (Vollständiges Muster)

Verwende diesen Code als Basis. Ersetze `<AgentName>` und die spezifischen Felder entsprechend deiner Aufgabe.

```python
from typing import Any, Dict, Optional
import json
import re
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
    AIMessage,
)

from src.settings.config_store import config_store
from src.settings.reasoning_chat_openai import ReasoningChatOpenAI

class <AgentName>:
    """
    Dokumentiere hier kurz die Aufgabe des Agenten.
    """

    # 1. Liste der erlaubten MCP-Tools
    ALLOWED_TOOLS = [
        "tool_name_1",
        "tool_name_2",
    ]

    # 2. Pfad zum System Prompt (relativ zur Datei)
    PROMPT_PATH = Path(__file__).with_name("<agent_name>_systemprompt.md")

    # 3. Limit für Tool-Aufrufe in einer Runde
    MAX_TOOL_ROUNDS = 10

    def __init__(self):
        # System Prompt beim Start laden
        with self.PROMPT_PATH.open("r", encoding="utf-8") as file:
            self.system_prompt = file.read()

        self._init_llm()

    def _init_llm(self) -> None:
        """Konfiguriert die LLM-Klasse basierend auf dem Profil."""
        profile = config_store.llm_profiles.get("oogabooga")

        if not profile:
            raise ValueError("LLM Profile 'oogabooga' not found in configuration.")

        # Entscheidung zwischen Reasoning- und Standard-LLM
        LLMClass = (
            ReasoningChatOpenAI
            if getattr(profile, "type", None) == "reasoning"
            else ChatOpenAI
        )

        self.llm = LLMClass(
            base_url=profile.url,
            api_key=profile.api_key,
            model=profile.model,
            temperature=0.7,
            streaming=True,
            stream_usage=True,
            use_responses_api=False,
            extra_body=profile.extra_body,
        )

    def _parse_json_content(self, content: Any) -> Dict[str, Any]:
        """Extrahiert ein JSON-Objekt aus der LLM-Antwort (unterstützt Markdown-Blocks)."""
        if isinstance(content, list):
            content = "".join(block.get("text", "") for block in content if isinstance(block, dict))

        if not isinstance(content, str):
            raise ValueError("LLM response content is not a string.")

        # Versuche JSON aus Markdown Code-Blocks zu extrahieren
        match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1)
        else:
            # Fallback: Suche nach ersten { und letztem }
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                content = content[start:end + 1]

        return json.loads(content)

    @staticmethod
    def _extract_usage(response: Any) -> Dict[str, int]:
        """Extrahiert und normalisiert die Token-Nutzung."""
        usage = response.response_metadata.get("token_usage", {})
        if not usage:
            usage = getattr(response, "usage_metadata", None) or {}

        return {
            "total_tokens": int(usage.get("total_tokens", 0)),
            "prompt_tokens": int(usage.get("prompt_tokens", usage.get("input_tokens", 0))),
            "completion_tokens": int(usage.get("completion_tokens", usage.get("output_tokens", 0))),
        }

    async def run(
        self,
        last_message: str,
        mcp_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Führt die Agenten-Logik aus."""
        if mcp_client is None:
            raise ValueError("MCP client is missing from the graph state.")

        # 1. Tools laden und einschränken
        tools = await mcp_client.get_tools(allowed_names=self.ALLOWED_TOOLS)
        tools_by_name = {tool.name: tool for tool in tools}

        if not tools_by_name:
            raise RuntimeError(f"No permitted MCP tools available for <AgentName>.")

        # 2. LLM mit Tools verbinden
        llm_with_tools = self.llm.bind_tools(tools)

        # 3. Initialer Message-Stack
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=last_message),
        ]

        total_usage = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}

        # 4. Tool-Execution-Loop
        for _ in range(self.MAX_TOOL_ROUNDS):
            response = await llm_with_tools.ainvoke(messages)
            
            # Usage tracken
            usage = self._extract_usage(response)
            for key in total_usage:
                total_usage[key] += usage[key]

            # Falls keine Tool-Calls mehr kommen -> Finale Antwort
            if not response.tool_calls:
                return {
                    "data": self._parse_json_content(response.content),
                    "usage": total_usage,
                    "raw_content": response.content,
                }

            # Tool-Call verarbeiten
            messages.append(response)
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
                tool_call_id = tool_call["id"]

                if tool_name not in tools_by_name:
                    raise PermissionError(f"Tool '{tool_name}' is not allowed.")

                tool_result = await tools_by_name[tool_name].ainvoke(tool_args)
                
                # Resultat in String umwandeln für ToolMessage
                result_content = tool_result if isinstance(tool_result, str) else json.dumps(
                    tool_result, ensure_ascii=False, default=str
                )

                messages.append(ToolMessage(
                    content=result_content,
                    tool_call_id=tool_call_id,
                    name=tool_name,
                ))

        raise RuntimeError(f"Maximum tool-calling rounds exceeded ({self.MAX_TOOL_ROUNDS}).")
```

### B. Klassendefinition & Attribute
- **`ALLOWED_TOOLS`**: Eine Liste von Strings, die die Namen der MCP-Tools enthält, die dieser Agent nutzen darf.
- **`PROMPT_PATH`**: Ein `pathlib.Path`, der auf die Markdown-Datei des System-Prompts zeigt.
- **`MAX_TOOL_ROUNDS`**: Ein Integer (Standard: `10`), der die Schleifenanzahl begrenzt.

### C. Initialisierung & LLM
- Der Agent nutzt `config_store.llm_profiles.get("oogabooga")`.
- **LLM-Klasse**: Automatische Wahl zwischen `ReasoningChatOpenAI` und `ChatOpenAI` basierend auf dem Profil.
- **Parameter**: `temperature=0.7`, `streaming=True`, `stream_usage=True`.

### D. Die `run`-Methode (Kern-Logik)
1. **Tool-Einschränkung**: Tools werden über `mcp_client.get_tools(allowed_names=...)` geladen.
2. **Message-Historie**: `SystemMessage` (aus Datei) + `HumanMessage` (User-Input).
3. **Loop**: Iteriert über `ainvoke` -> `tool_calls` -> `ToolMessage` -> `ainvoke`.
4. **Parsing**: Die finale Antwort wird via `_parse_json_content` in ein Dictionary umgewandelt.
5. **Rückgabe**: Ein Dictionary mit `"data"`, `"usage"` und `"raw_content"`.

---

## 2. Die Node-Struktur (`nodes/<agent_name>_node.py`)

Der Node ist die Schnittstelle zum LangGraph-State.

### A. Template-Code (Vollständiges Muster)

```python
from typing import Any, Dict
from langchain_core.messages import AIMessage, HumanMessage
from src.graphs.profile_management.state import ProfileManagementState
from src.graphs.profile_management.agents.<agent_name>.<agent_name> import <AgentName>

class <AgentName>Node:
    """
    Node, der den <AgentName> Agenten aufruft und das Ergebnis in den State schreibt.
    """

    def __init__(self):
        self.agent = <AgentName>()

    async def __call__(
        self,
        state: ProfileManagementState,
    ) -> Dict[str, Any]:

        # 1. Letzte User-Nachricht finden
        last_message = next(
            (
                message.content
                for message in reversed(state["messages"])
                if isinstance(message, HumanMessage)
            ),
            None,
        )

        if last_message is None:
            return {
                "metadata": {**state.get("metadata", {}), "error": "No user message found."},
                "messages": [AIMessage(content="Error: No user message found.")]
            }

        # 2. MCP Client aus dem State holen
        client = state.get("mcp_client")

        try:
            # 3. Agent ausführen
            result = await self.agent.run(
                last_message=last_message,
                mcp_client=client,
            )

            data = result["data"]
            # Hier: Spezifisches Mapping der 'data' in den State (z.B. 'collective')
            # Beispiel:
            # return {"collective": data, "messages": [AIMessage(content="Success")]}
            
            # Platzhalter für das spezifische Mapping:
            return {
                "messages": [AIMessage(content="Task completed successfully.")],
                # Füge hier die Felder hinzu, die der Agent in den State schreiben soll
                **data 
            }

        except Exception as exc:
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "error": f"<AgentName> failed: {exc}",
                },
                "messages": [AIMessage(content=f"Error: {exc}")]
            }
```

### B. Node-Logik
1. **Input**: Extrahiert `HumanMessage` und `mcp_client` aus dem `state`.
2. **Agent-Call**: Ruft `await self.agent.run(...)` auf.
3. **Error-Handling**: Fehler werden in `metadata` und als `AIMessage` im State gespeichert.
4. **State-Update**: Das Dictionary, das zurückgegeben wird, muss die Keys enthalten, die im `ProfileManagementState` definiert sind (z.B. `collective`, `user_info`, etc.).

---

## 3. Zusammenfassende Checkliste für neue Agenten

1. [ ] **Agent-Ordner** erstellt mit `.py` und `_systemprompt.md`.
2. [ ] **System Prompt** im Markdown-File definiert (strikte JSON-Vorgabe!).
3. [ ] **`ALLOWED_TOOLS`** in der Agent-Klasse exakt definiert.
4. [ ] **`_init_llm`** implementiert (mit `ReasoningChatOpenAI` Check).
5. [ ] **`run`-Loop** mit Tool-Handling und `MAX_TOOL_ROUNDS` implementiert.
6. [ ] **Node-Klasse** erstellt, die den Agenten in `__init__` hält.
7. [ ] **Node `__call__`** implementiert, die `last_message` und `mcp_client` aus dem State zieht.
8. [ ] **State-Update** im Node sicherstellen (Mapping von Agent-Daten auf State-Keys).
