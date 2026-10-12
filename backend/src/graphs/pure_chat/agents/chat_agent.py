from src.shared.reasoning_chat_openai import ReasoningChatOpenAI
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

        # Entscheide, welche Klasse zu verwenden ist basierend auf dem Profil-Typ
        if profile.type == "reasoning":
            LLMClass = ReasoningChatOpenAI
        else:
            LLMClass = ChatOpenAI

        # Initialisiere das LLM
        # Wir verwenden nun direkt das extra_body aus dem Profil für maximale Flexibilität
        self.llm = LLMClass(
            base_url=profile.url,
            model=profile.model,
            api_key=effective_api_key,
            temperature=0.7,
            streaming=True,
            stream_usage=True,
            use_responses_api=False,
            extra_body=profile.extra_body
        )
        self.system_prompt = ""

    async def set_api_key(self, api_key: str):
        """Setzt den API Key für den LLM-Client."""
        self.llm.api_key = api_key

    async def set_system_prompt(self, prompt_text: str):
        """Setzt den System Prompt."""
        self.system_prompt = prompt_text

    async def run(self, messages: list):
        """
        Führt den LLM-Aufruf asynchron aus. 
        """
        full_messages = []
        if self.system_prompt:
            full_messages.append(SystemMessage(content=self.system_prompt))
        full_messages.extend(messages)

        result = await self.llm.ainvoke(full_messages)
        return result
