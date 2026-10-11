from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.settings.config_store import config_store

class ChatAgent:
    def __init__(self, api_key: str = None):
        # Lade das Profil aus der Konfiguration
        profile = config_store.llm_profiles.get("oogabooga")
        if not profile:
            raise ValueError("LLM Profile 'oogabooga' not found in config.")

        # Nutze den übergebenen API Key oder den aus der Config
        effective_api_key = api_key or profile.get("api_key", "sk-no-key-provided")

        # Initialisiere das LLM mit den Settings aus der config.json
        self.llm = ChatOpenAI(
            base_url=profile["url"],
            model=profile["model"],
            api_key=effective_api_key,
            temperature=0.7,
            streaming=True  # Zwingend für das Streaming von Content und Thinking
        )
        self.system_prompt = ""

    async def set_api_key(self, api_key: str):
        """Setzt den API Key für den LLM-Client."""
        self.llm.api_key = api_key

    async def set_system_prompt(self, prompt_text: str):
        self.system_prompt = prompt_text

    async def run(self, messages: list):
        """
        Führt den LLM-Aufruf asynchron aus. 
        Der Aufruf erfolgt über das LLM-Objekt selbst, um via astream_events 
        die Granularität für Content, Reasoning und Tool-Calls zu erhalten.
        """
        full_messages = []
        if self.system_prompt:
            full_messages.append(SystemMessage(content=self.system_prompt))
        full_messages.extend(messages)
        
        result = await self.llm.ainvoke(full_messages)
        return result