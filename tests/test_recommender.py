import json
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.recommender import FoundryRecommender, get_recommender


def _settings(**overrides) -> Settings:
    base = {
        "foundry_endpoint": "https://example.cognitiveservices.azure.com/",
        "foundry_deployment": "gpt-5.4-mini",
        "recommender_mode": "foundry",
    }
    base.update(overrides)
    return Settings(**base)


class _FakeCompletions:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.captured: dict | None = None

    async def create(self, **kwargs):
        self.captured = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(self.payload)))]
        )


class _FakeClient:
    def __init__(self, payload: dict) -> None:
        self.completions = _FakeCompletions(payload)
        self.chat = SimpleNamespace(completions=self.completions)


def test_foundry_requires_configuration() -> None:
    with pytest.raises(RuntimeError, match="FOUNDRY_ENDPOINT"):
        FoundryRecommender(_settings(foundry_endpoint=None))


@pytest.mark.anyio
async def test_foundry_parses_structured_response() -> None:
    recommender = FoundryRecommender(_settings())
    fake = _FakeClient({"breed": "Whippet", "reason": "Calm and quick.", "confidence": 0.81})
    recommender._client = fake

    result = await recommender.recommend(b"\x89PNG-bytes", "image/png", "I run a lot")

    assert result.breed == "Whippet"
    assert result.reason == "Calm and quick."
    assert result.confidence == 0.81
    assert result.source == "foundry"

    sent = fake.completions.captured
    assert sent["model"] == "gpt-5.4-mini"
    content = sent["messages"][1]["content"]
    assert content[0]["text"] == "I run a lot"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


@pytest.mark.anyio
async def test_foundry_clamps_confidence() -> None:
    recommender = FoundryRecommender(_settings())
    recommender._client = _FakeClient(
        {"breed": "Beagle", "reason": "Curious.", "confidence": 4.2}
    )

    result = await recommender.recommend(b"bytes", "image/jpeg", None)

    assert result.confidence == 1.0


@pytest.mark.anyio
async def test_foundry_uses_default_prompt_when_message_blank() -> None:
    recommender = FoundryRecommender(_settings())
    fake = _FakeClient({"breed": "Pug", "reason": "Cosy.", "confidence": 0.5})
    recommender._client = fake

    await recommender.recommend(b"bytes", "image/png", "   ")

    assert "Which dog breed suits me" in fake.completions.captured["messages"][1]["content"][0][
        "text"
    ]


@pytest.mark.anyio
async def test_foundry_rejects_empty_content() -> None:
    recommender = FoundryRecommender(_settings())
    fake = _FakeClient({})
    fake.completions.payload = {}

    async def _empty(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=""))])

    fake.completions.create = _empty
    recommender._client = fake

    with pytest.raises(RuntimeError, match="empty response"):
        await recommender.recommend(b"bytes", "image/png", None)


def test_get_recommender_selects_mode() -> None:
    assert type(get_recommender(Settings(recommender_mode="stub"))).__name__ == "StubRecommender"
    assert type(get_recommender(_settings())).__name__ == "FoundryRecommender"
