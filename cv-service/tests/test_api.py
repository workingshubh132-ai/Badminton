from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

FIXTURE = Path(__file__).resolve().parent.parent / "eval" / "fixtures" / "synthetic_court_01.mp4"


@pytest.mark.integration
class TestApi:
    @classmethod
    @pytest.fixture(scope="class")
    def client(cls):
        # TestClient as a context manager runs the app's lifespan (model
        # load) once for the whole class, not once per test.
        with TestClient(app) as c:
            yield c

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["model_loaded"] is True

    def test_analyze_missing_video_path_returns_404(self, client):
        resp = client.post(
            "/analyze", json={"video_id": "vid_1", "video_path": "/nonexistent/path.mp4"}
        )
        assert resp.status_code == 404

    def test_analyze_real_fixture_returns_structured_result(self, client):
        if not FIXTURE.exists():
            pytest.skip("Run eval/fixtures/generate_synthetic_fixture.py first.")
        resp = client.post(
            "/analyze",
            json={"video_id": "vid_1", "video_path": str(FIXTURE), "sampling_fps": 2.0},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["quality"]["status"] == "GOOD"
        assert body["calibration"]["status"] == "SUCCESS"
        assert "processing_metadata" in body

    def test_analyze_rejects_wrong_internal_token_when_configured(self, client, monkeypatch):
        monkeypatch.setattr("app.main.INTERNAL_TOKEN", "expected-secret")
        resp = client.post(
            "/analyze",
            json={"video_id": "vid_1", "video_path": str(FIXTURE)},
            headers={"X-Internal-Token": "wrong-secret"},
        )
        assert resp.status_code == 401
