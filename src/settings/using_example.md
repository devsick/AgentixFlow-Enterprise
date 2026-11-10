## Using Example

```python
# Import:
from agents.backend.src.settings.config_store import config_store

# Zugriff auf einzelne Werte:
print(config_store.mcp_server["nextcloud-mcp"].type)   # -> "http"
print(config_store.mcp_server["nextcloud-mcp"].url)     # -> "http://nextcloud-mcp:8000/mcp"
print(config_store.llm_profiles["oogabooga"].model)     # -> "Qwen3.8-35B-A3B-IQ2_M.gguf"

# Zugriff über settings:
print(config_store.settings.mcp_server)
print(config_store.settings.llm_profiles)
```