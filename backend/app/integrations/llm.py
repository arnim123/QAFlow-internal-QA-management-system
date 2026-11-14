"""LLM provider used for draft generation only. Not implemented.

Provider, model, and credentials are settings and default to empty.
Generated text is a draft until a human acts on it.
"""


class LlmClient:
    def __init__(self, provider: str, model: str) -> None:
        self.provider = provider
        self.model = model

    def generate_draft(self, prompt: str) -> str:
        raise NotImplementedError("LLM integration is not implemented")
