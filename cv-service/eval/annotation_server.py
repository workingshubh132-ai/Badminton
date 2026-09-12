"""
Simple annotation server for M5.5 ground-truth labeling.

Minimal web interface for annotating court corners and player bboxes.

Usage:
    python -m eval.annotation_server --port 5000 --dataset-dir cv-service/eval/datasets
"""

from __future__ import annotations

import argparse
import base64
import json
from io import BytesIO
from pathlib import Path

import cv2
from flask import Flask, jsonify, request, send_file

from .dataset import DatasetManager
from .schemas import (
    AnnotationMetadata,
    BoundingBox,
    CourtCorners,
    FrameAnnotation,
    PlayerAnnotation,
    PlayerIdentity,
    VideoQuality,
)


def create_app(dataset_dir: str | Path) -> Flask:
    """Create Flask app for annotation."""
    app = Flask(__name__)
    dataset = DatasetManager(dataset_dir)

    # ========================================================================
    # ENDPOINTS
    # ========================================================================

    @app.route("/")
    def index():
        """List unannotated clips."""
        unannotated = dataset.list_unannotated_clips()
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>M5.5 Annotation Tool</title>
            <style>
                body {{ font-family: sans-serif; margin: 20px; }}
                .clip-list {{ margin: 20px 0; }}
                .clip-item {{
                    padding: 10px; margin: 5px 0;
                    border: 1px solid #ccc; cursor: pointer;
                    background: #f5f5f5;
                }}
                .clip-item:hover {{ background: #e0e0e0; }}
                h1 {{ color: #333; }}
            </style>
        </head>
        <body>
            <h1>M5.5 Ground Truth Annotation</h1>
            <p>Annotate badminton footage for evaluation.</p>
            <h2>Clips Needing Annotation ({len(unannotated)})</h2>
            <div class="clip-list">
        """

        for clip_id in unannotated[:20]:  # Show first 20
            html += f'<div class="clip-item" onclick="window.location.href=\'/annotate?clip_id={clip_id}\'">'
            metadata = dataset.get_clip_metadata(clip_id)
            html += f"{clip_id}<br/>"
            html += f"Duration: {metadata['end_seconds'] - metadata['start_seconds']:.1f}s"
            html += "</div>"

        if len(unannotated) > 20:
            html += f"<p>... and {len(unannotated) - 20} more</p>"

        html += """
            </div>
        </body>
        </html>
        """
        return html

    @app.route("/annotate")
    def annotate():
        """Annotation interface for a clip."""
        clip_id = request.args.get("clip_id")
        if not clip_id:
            return "Missing clip_id", 400

        clip_path = dataset.get_clip_path(clip_id)
        if not clip_path.exists():
            return f"Clip not found: {clip_id}", 404

        # Load existing annotation if present
        existing = dataset.load_annotation(clip_id)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Annotate {clip_id}</title>
            <style>
                body {{ font-family: sans-serif; margin: 20px; }}
                #canvas {{ border: 1px solid #000; display: block; margin: 20px 0; }}
                .controls {{ margin: 20px 0; }}
                button {{ padding: 8px 12px; margin: 5px; cursor: pointer; }}
                button:hover {{ background: #e0e0e0; }}
                .info {{ background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 4px; }}
                #status {{ margin: 10px 0; padding: 10px; background: #ffffcc; border: 1px solid #ccc; }}
            </style>
        </head>
        <body>
            <h1>Annotate: {clip_id}</h1>

            <div class="info">
                <p>Instructions:</p>
                <ul>
                    <li>Click 4 points to mark court corners (top-left, top-right, bottom-right, bottom-left)</li>
                    <li>Drag to draw player bounding boxes</li>
                    <li>Use controls to assign identity and on-court status, and mark quality</li>
                    <li><b>Box everyone visible</b>, including spectators and officials — mark those as Bystander so participant classification can be scored against them</li>
                </ul>
            </div>

            <div class="controls">
                <label>Quality:
                    <select id="quality">
                        <option value="good">Good</option>
                        <option value="acceptable" selected>Acceptable</option>
                        <option value="poor">Poor</option>
                        <option value="unusable">Unusable</option>
                    </select>
                </label>
                <br/><br/>
                <label>Identity (for next box):
                    <select id="player-identity">
                        <option value="unknown" selected>Unknown</option>
                        <option value="athlete">Athlete</option>
                        <option value="opponent">Opponent</option>
                    </select>
                </label>
                &nbsp;&nbsp;
                <label>On court? (for next box):
                    <select id="player-participant">
                        <option value="unknown" selected>Unknown</option>
                        <option value="participant">Participant (playing)</option>
                        <option value="non_participant">Bystander (spectator/official)</option>
                    </select>
                </label>
                <br/><br/>
                <button onclick="undoBox()">Undo Last Box</button>
                <button onclick="clearBoxes()">Clear Boxes</button>
                <br/><br/>
                <button onclick="markCourtCorners()">Mark Court Corners</button>
                <button onclick="clearCourtCorners()">Clear Court</button>
                <button onclick="prevFrame()">← Previous Frame</button>
                <button onclick="nextFrame()">Next Frame →</button>
                <button onclick="saveAnnotation()" style="background: #4CAF50; color: white;">Save Annotation</button>
                <button onclick="goBack()" style="background: #999;">Back to List</button>
            </div>

            <div id="status"></div>
            <canvas id="canvas" width="1280" height="720"></canvas>
            <p>Frame: <span id="frame-num">0</span> / <span id="frame-total">0</span></p>

            <script>
                const clipId = "{clip_id}";
                let currentFrameIndex = 0;
                let frames = [];
                let courtCorners = [];
                let markers = [];
                let markerMode = false;

                async function loadFrames() {{
                    const response = await fetch(`/api/clip/${{clipId}}/frames`);
                    frames = await response.json();
                    document.getElementById('frame-total').textContent = frames.length;
                    if (frames.length > 0) {{
                        drawFrame(0);
                    }}
                }}

                function drawFrame(index) {{
                    currentFrameIndex = Math.max(0, Math.min(index, frames.length - 1));
                    document.getElementById('frame-num').textContent = currentFrameIndex;
                    const canvas = document.getElementById('canvas');
                    const ctx = canvas.getContext('2d');

                    const img = new Image();
                    img.onload = function() {{
                        ctx.drawImage(img, 0, 0);
                        drawCourtCorners(ctx);
                        drawMarkers(ctx);
                    }};
                    img.src = frames[currentFrameIndex].dataUrl;
                }}

                function drawCourtCorners(ctx) {{
                    if (courtCorners.length === 0) return;
                    ctx.strokeStyle = '#00ff00';
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    for (let i = 0; i < courtCorners.length; i++) {{
                        const p = courtCorners[i];
                        ctx.arc(p.x, p.y, 5, 0, 2 * Math.PI);
                        if (i === 0) ctx.moveTo(p.x, p.y);
                        else ctx.lineTo(p.x, p.y);
                    }}
                    if (courtCorners.length === 4) {{
                        ctx.lineTo(courtCorners[0].x, courtCorners[0].y);
                    }}
                    ctx.stroke();
                    // Draw labels
                    const labels = ['TL', 'TR', 'BR', 'BL'];
                    for (let i = 0; i < courtCorners.length; i++) {{
                        ctx.fillStyle = '#00ff00';
                        ctx.font = '12px Arial';
                        ctx.fillText(labels[i], courtCorners[i].x + 10, courtCorners[i].y + 10);
                    }}
                }}

                function drawMarkers(ctx) {{
                    markers.forEach(marker => {{
                        const colour = marker.participant === 'participant' ? '#00e5ff'
                                     : marker.participant === 'non_participant' ? '#ff9800'
                                     : '#ff0000';
                        ctx.strokeStyle = colour;
                        ctx.lineWidth = 2;
                        ctx.strokeRect(marker.x1, marker.y1, marker.x2 - marker.x1, marker.y2 - marker.y1);
                        ctx.fillStyle = colour;
                        ctx.font = '12px Arial';
                        ctx.fillText(marker.identity + ' / ' + marker.participant, marker.x1, marker.y1 - 5);
                    }});
                }}

                function undoBox() {{ markers.pop(); drawFrame(currentFrameIndex); }}
                function clearBoxes() {{ markers = []; drawFrame(currentFrameIndex); }}

                function markCourtCorners() {{
                    markerMode = !markerMode;
                    if (markerMode) {{
                        alert('Click 4 points on the canvas: top-left, top-right, bottom-right, bottom-left');
                    }}
                }}

                function clearCourtCorners() {{
                    courtCorners = [];
                    drawFrame(currentFrameIndex);
                }}

                let dragStart = null;
                const canvasEl = document.getElementById('canvas');

                canvasEl.addEventListener('mousedown', function(e) {{
                    if (markerMode) return;  // marking court corners, not boxes
                    const rect = this.getBoundingClientRect();
                    dragStart = {{x: e.clientX - rect.left, y: e.clientY - rect.top}};
                }});

                canvasEl.addEventListener('mouseup', function(e) {{
                    if (markerMode || !dragStart) return;
                    const rect = this.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const y = e.clientY - rect.top;
                    const x1 = Math.min(dragStart.x, x), x2 = Math.max(dragStart.x, x);
                    const y1 = Math.min(dragStart.y, y), y2 = Math.max(dragStart.y, y);
                    dragStart = null;
                    if (x2 - x1 < 4 || y2 - y1 < 4) return;  // a click, not a box
                    markers.push({{
                        x1: x1, y1: y1, x2: x2, y2: y2,
                        identity: document.getElementById('player-identity').value,
                        participant: document.getElementById('player-participant').value
                    }});
                    drawFrame(currentFrameIndex);
                }});

                canvasEl.addEventListener('click', function(e) {{
                    if (!markerMode) return;
                    const rect = this.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const y = e.clientY - rect.top;
                    courtCorners.push({{x, y}});
                    if (courtCorners.length === 4) {{
                        markerMode = false;
                        alert('Court corners marked');
                        drawFrame(currentFrameIndex);
                    }} else {{
                        drawFrame(currentFrameIndex);
                    }}
                }});

                function prevFrame() {{ drawFrame(currentFrameIndex - 1); }}
                function nextFrame() {{ drawFrame(currentFrameIndex + 1); }}

                function goBack() {{ window.location.href = '/'; }}

                async function saveAnnotation() {{
                    // Normalise against the actual canvas, not an assumed 1280x720.
                    const W = canvasEl.width, H = canvasEl.height;
                    const annotation = {{
                        clip_id: clipId,
                        version: '1.0',
                        frames: [{{
                            frame_index: 0,
                            timestamp_seconds: 0,
                            quality: document.getElementById('quality').value,
                            court_corners: courtCorners.length === 4 ? {{
                                top_left: [courtCorners[0].x / W, courtCorners[0].y / H],
                                top_right: [courtCorners[1].x / W, courtCorners[1].y / H],
                                bottom_right: [courtCorners[2].x / W, courtCorners[2].y / H],
                                bottom_left: [courtCorners[3].x / W, courtCorners[3].y / H],
                            }} : null,
                            players: markers.map(m => ({{
                                identity: m.identity,
                                participant: m.participant,
                                bbox: {{
                                    x1: m.x1 / W, y1: m.y1 / H,
                                    x2: m.x2 / W, y2: m.y2 / H
                                }}
                            }}))
                        }}]
                    }};

                    const response = await fetch(`/api/clip/${{clipId}}/annotation`, {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify(annotation)
                    }});

                    if (response.ok) {{
                        document.getElementById('status').textContent = '✓ Annotation saved';
                        setTimeout(() => {{ window.location.href = '/'; }}, 1000);
                    }} else {{
                        document.getElementById('status').textContent = '✗ Save failed';
                    }}
                }}

                loadFrames();
            </script>
        </body>
        </html>
        """
        return html

    @app.route("/api/clip/<clip_id>/frames")
    def get_frames(clip_id: str):
        """Get video frames as dataURLs for annotation."""
        clip_path = dataset.get_clip_path(clip_id)
        if not clip_path.exists():
            return {"error": "Clip not found"}, 404

        cap = cv2.VideoCapture(str(clip_path))
        frames = []
        frame_count = 0
        target_fps = 2  # Sample at 2 FPS for speed

        while frame_count < 20:  # Max 20 frames
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # Encode to JPEG
            _, buffer = cv2.imencode(".jpg", frame)
            frame_b64 = base64.b64encode(buffer).decode()
            frames.append({
                "frameIndex": frame_count - 1,
                "dataUrl": f"data:image/jpeg;base64,{frame_b64}",
            })

        cap.release()
        return jsonify(frames)

    @app.route("/api/clip/<clip_id>/annotation", methods=["POST"])
    def save_annotation(clip_id: str):
        """Save annotation for a clip."""
        data = request.json
        dataset.save_annotation(clip_id, data)
        return {"success": True}

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Start M5.5 annotation server.")
    parser.add_argument("--port", type=int, default=5000, help="Server port")
    parser.add_argument("--dataset-dir", default="cv-service/eval/datasets", help="Dataset directory")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")

    args = parser.parse_args()
    app = create_app(args.dataset_dir)

    print(f"Starting annotation server on http://{args.host}:{args.port}")
    print(f"Dataset: {args.dataset_dir}")
    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
