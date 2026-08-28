import pytest

from app.detection import PersonDetector


@pytest.fixture(scope="session")
def person_detector():
    """Model load is the expensive part (~1s); share one instance across
    the whole test session rather than reloading per test."""
    detector = PersonDetector()
    yield detector
    detector.close()
