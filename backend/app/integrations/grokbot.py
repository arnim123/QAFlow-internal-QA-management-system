"""GrokBot is an external executor. This client is not implemented.

GrokBot may retrieve an approved set only. It cannot approve, edit cases,
see drafts, or change the master repository. Auth scheme is unset
(see docs/OPEN_QUESTIONS.md).
"""


class GrokBotClient:
    def __init__(self, base_url: str, auth_scheme: str) -> None:
        self.base_url = base_url
        self.auth_scheme = auth_scheme

    def submit_results(self, payload: dict[str, object]) -> None:
        raise NotImplementedError("GrokBot integration is not implemented")
