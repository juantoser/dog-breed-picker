from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, Field

from app.config import Settings, get_settings

if TYPE_CHECKING:
    from openai import AsyncAzureOpenAI


class Recommendation(BaseModel):
    breed: str
    reason: str
    confidence: float = Field(ge=0, le=1)
    source: str


class Recommender(Protocol):
    async def recommend(
        self, image_bytes: bytes, content_type: str, message: str | None
    ) -> Recommendation:
        ...


@dataclass(frozen=True)
class BreedProfile:
    breed: str
    trait: str
    activity: str


class StubRecommender:
    _breeds = [
        BreedProfile("Golden Retriever", "warm, friendly energy", "walks and weekend adventures"),
        BreedProfile("Shiba Inu", "independent, expressive style", "curious exploring"),
        BreedProfile("Border Collie", "bright, focused personality", "games and active routines"),
        BreedProfile("Cavalier King Charles Spaniel", "gentle, affectionate presence", "cozy companionship"),
        BreedProfile("Australian Shepherd", "playful, outdoorsy spark", "hikes and training games"),
        BreedProfile("French Bulldog", "charming, easygoing vibe", "city strolls and couch time"),
        BreedProfile("Labrador Retriever", "sunny, dependable spirit", "fetch and social outings"),
        BreedProfile("Poodle", "clever, polished flair", "learning tricks and meeting people"),
        BreedProfile("Dachshund", "bold, quirky confidence", "short walks and big opinions"),
        BreedProfile("Samoyed", "bright, cheerful expression", "snowy walks and friendly greetings"),
    ]

    async def recommend(
        self, image_bytes: bytes, content_type: str, message: str | None
    ) -> Recommendation:
        digest = hashlib.sha256(
            image_bytes + content_type.encode("utf-8") + (message or "").encode("utf-8")
        ).digest()
        profile = self._breeds[int.from_bytes(digest[:2], "big") % len(self._breeds)]
        confidence = 0.72 + (digest[2] / 255) * 0.2
        message_hint = " Your note helped tune the vibe." if message else ""
        reason = (
            f"You give off {profile.trait}, which is a great match for a {profile.breed}. "
            f"This breed tends to enjoy {profile.activity}.{message_hint}"
        )
        return Recommendation(
            breed=profile.breed,
            reason=reason,
            confidence=round(confidence, 2),
            source="stub",
        )


SYSTEM_PROMPT = (
    "You are a warm, playful assistant for a demo app that suggests which dog breed "
    "suits a person, based on the vibe of the photo they share. "
    "Look at the overall style, energy and mood of the photo -- never guess at identity, "
    "age, ethnicity, health or any other sensitive attribute, and never describe the "
    "person's appearance in a judgemental way. "
    "Pick one real, well-known dog breed and explain the match in one or two friendly "
    "sentences that reference the mood or style you picked up on. "
    "Keep it light: this is entertainment, not analysis. "
    "If the photo has no person in it, still pick a fun breed and say you went on the "
    "mood of the picture instead."
)

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "dog_breed_recommendation",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "breed": {
                    "type": "string",
                    "description": "The recommended dog breed name.",
                },
                "reason": {
                    "type": "string",
                    "description": "One or two friendly sentences explaining the match.",
                },
                "confidence": {
                    "type": "number",
                    "description": "Playful confidence score between 0 and 1.",
                },
            },
            "required": ["breed", "reason", "confidence"],
            "additionalProperties": False,
        },
    },
}


class FoundryRecommender:
    """Recommends a breed using a vision model deployed on Microsoft Foundry.

    Authenticates with ``DefaultAzureCredential`` so it uses the App Service
    managed identity in Azure and the developer's ``az login`` locally. No API
    keys are stored anywhere.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.foundry_endpoint or not settings.foundry_deployment:
            raise RuntimeError(
                "FOUNDRY_ENDPOINT and FOUNDRY_DEPLOYMENT must be set when "
                "RECOMMENDER_MODE=foundry."
            )
        self.settings = settings
        self._client: AsyncAzureOpenAI | None = None

    def _get_client(self) -> AsyncAzureOpenAI:
        if self._client is None:
            from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
            from openai import AsyncAzureOpenAI as _AsyncAzureOpenAI

            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default",
            )
            self._client = _AsyncAzureOpenAI(
                azure_endpoint=self.settings.foundry_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=self.settings.foundry_api_version,
            )
        return self._client

    async def recommend(
        self, image_bytes: bytes, content_type: str, message: str | None
    ) -> Recommendation:
        data_url = f"data:{content_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        user_text = (
            message.strip()
            if message and message.strip()
            else "Which dog breed suits me, based on this photo?"
        )

        client = self._get_client()
        completion = await client.chat.completions.create(
            model=self.settings.foundry_deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            response_format=RESPONSE_SCHEMA,
            max_completion_tokens=self.settings.foundry_max_tokens,
        )

        content = completion.choices[0].message.content
        if not content:
            raise RuntimeError("Foundry returned an empty response.")

        payload = json.loads(content)
        confidence = float(payload.get("confidence", 0.75))
        return Recommendation(
            breed=str(payload["breed"]),
            reason=str(payload["reason"]),
            confidence=round(min(max(confidence, 0.0), 1.0), 2),
            source="foundry",
        )

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


def get_recommender(settings: Settings | None = None) -> Recommender:
    active_settings = settings or get_settings()
    if active_settings.recommender_mode == "foundry":
        return FoundryRecommender(active_settings)
    return StubRecommender()


@lru_cache
def _default_recommender() -> Recommender:
    """Cached singleton so the Foundry client and credential are reused."""
    return get_recommender()


async def recommend_breed(
    image_bytes: bytes, content_type: str, message: str | None
) -> Recommendation:
    return await _default_recommender().recommend(image_bytes, content_type, message)


async def shutdown_recommender() -> None:
    recommender = _default_recommender()
    closer = getattr(recommender, "aclose", None)
    if closer is not None:
        await closer()
    _default_recommender.cache_clear()
