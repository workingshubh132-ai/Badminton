import os
from pathlib import Path

SERVICE_NAME = "badminton-cv-service"
ENGINE_VERSION = "0.1.0"

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
PERSON_DETECTOR_MODEL_PATH = MODELS_DIR / "efficientdet_lite0.tflite"
PERSON_DETECTOR_MODEL_VERSION = "efficientdet_lite0-float32-1"

# Shared secret between the Next.js app and this internal service. This
# service is never meant to be internet-facing (see docs/CV_ARCHITECTURE.md
# "Security") — this header is defense-in-depth against a stray local
# process on the same host calling it, not internet-facing authentication.
INTERNAL_TOKEN = os.environ.get("CV_SERVICE_TOKEN")

DEFAULT_SAMPLING_FPS = 2.0
DEFAULT_MAX_SAMPLED_FRAMES = 600
COURT_CALIBRATION_MAX_FRAMES = 8

PERSON_DETECTION_SCORE_THRESHOLD = 0.35

# BWF doubles court boundary — the outermost lines, and the ones most likely
# to be visually prominent regardless of whether the match is singles or
# doubles. Real-world meters.
COURT_WIDTH_M = 6.1
COURT_LENGTH_M = 13.4

# Quality thresholds. Each one is documented as provisional in
# docs/CV_ARCHITECTURE.md "Acceptance thresholds" — chosen from general
# video-analysis practice, not validated against a labeled badminton
# dataset (none exists yet). Revisit once eval/ has real footage.
MIN_ACCEPTABLE_WIDTH = 640
MIN_GOOD_WIDTH = 1280
MIN_ACCEPTABLE_FPS = 15.0
MIN_GOOD_FPS = 24.0
MAX_BLANK_FRAME_RATIO = 0.3
MAX_DECODE_FAILURE_RATIO = 0.1

# --- M5.5.1 participant classification -------------------------------------
# A person is only a "court participant" if their footpoint lands inside the
# play area. Players legitimately run past the lines, so the play area is the
# doubles court plus a margin; the margin is deliberately tighter than
# video_point_to_court's 2.0m projection sanity margin, because courtside
# officials sit just beyond the lines and must not be swept in.
PLAY_AREA_MARGIN_M = 1.5

# Fraction of a track's court-positioned detections that must fall inside the
# play area before the track can be called a participant.
PARTICIPANT_MIN_INSIDE_RATIO = 0.7
# At or below this, the track is confidently off-court (spectator/official).
# Between the two thresholds the answer is UNKNOWN, never a guess.
NON_PARTICIPANT_MAX_INSIDE_RATIO = 0.2

# Fraction of the sampled timeline a track must span. Someone walking through
# shot briefly is not a participant.
PARTICIPANT_MIN_TIMELINE_COVERAGE = 0.25

# Metres a track's footpoint must travel across the court. Seated line judges
# sit inside the margin but do not move; players cover ground. Used only to
# withhold a PARTICIPANT verdict, never to assert NON_PARTICIPANT.
PARTICIPANT_MIN_COURT_DISPLACEMENT_M = 1.0
