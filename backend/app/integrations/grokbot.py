"""GrokBot is an external executor. This client is not implemented.

GrokBot may retrieve an approved set only. It cannot approve, edit cases,
see drafts, or change the master repository. Auth scheme is unset
(see docs/OPEN_QUESTIONS.md).

A result posted back to QAFlow must pass
`app.services.acceptance.accept_execution_result` before it is stored.
It remains an AI result until a tester confirms or overrides it.
"""


class GrokBotClient:
    def __init__(self, base_url: str, auth_scheme: str) -> None:
        self.base_url = base_url
        self.auth_scheme = auth_scheme

    def submit_results(self, payload: dict[str, object]) -> None:
        raise NotImplementedError("GrokBot integration is not implemented")
