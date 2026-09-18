from fastapi.testclient import TestClient

from app.main import MAX_IMAGE_BYTES, app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_serves_static_index() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Dog Breed Picker" in response.text


def test_recommend_accepts_image() -> None:
    response = client.post(
        "/api/recommend",
        data={"message": "I like hiking."},
        files={"image": ("self.png", b"\x89PNG\r\n\x1a\nstub-image", "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"breed", "reason", "confidence", "source"}
    assert payload["breed"]
    assert payload["reason"]
    assert 0 <= payload["confidence"] <= 1
    assert payload["source"] == "stub"


def test_recommend_is_deterministic() -> None:
    files = {"image": ("self.png", b"\x89PNG\r\n\x1a\nsame-image", "image/png")}

    first = client.post("/api/recommend", files=files)
    second = client.post(
        "/api/recommend",
        files={"image": ("self.png", b"\x89PNG\r\n\x1a\nsame-image", "image/png")},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_recommend_rejects_non_image() -> None:
    response = client.post(
        "/api/recommend",
        files={"image": ("notes.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 400
    assert "image" in response.json()["detail"]


def test_recommend_rejects_large_image() -> None:
    response = client.post(
        "/api/recommend",
        files={"image": ("large.jpg", b"0" * (MAX_IMAGE_BYTES + 1), "image/jpeg")},
    )

    assert response.status_code == 400
    assert "5 MB" in response.json()["detail"]
