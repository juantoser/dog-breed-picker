from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field

from app.config import Settings, get_settings


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


class FoundryRecommender:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def recommend(
        self, image_bytes: bytes, content_type: str, message: str | None
    ) -> Recommendation:
        raise NotImplementedError("Azure Foundry recommender is not wired in this iteration.")


def get_recommender(settings: Settings | None = None) -> Recommender:
    active_settings = settings or get_settings()
    if active_settings.recommender_mode == "foundry":
        return FoundryRecommender(active_settings)
    return StubRecommender()


async def recommend_breed(
    image_bytes: bytes, content_type: str, message: str | None
) -> Recommendation:
    return await get_recommender().recommend(image_bytes, content_type, message)
