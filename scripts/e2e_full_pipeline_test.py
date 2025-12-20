#!/usr/bin/env python3
"""
End-to-end pipeline test for VidSynth backend.

This script calls the full API sequence for a single video:
assets -> import (optional) -> segment -> theme expand/analyze -> sequence -> export
and verifies filesystem artifacts along the way.
"""

from __future__ import annotations

import argparse
import http.client
import json
import mimetypes
import os
from pathlib import Path
import time
import urllib.parse
import urllib.request
import uuid


def log(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    LOG_LINES.append(line)


def write_report(path: Path, summary: dict) -> None:
    path.write_text("\n".join(LOG_LINES + ["", "SUMMARY", json.dumps(summary, indent=2)]), encoding="utf-8")


def http_request(method: str, url: str, *, json_body: dict | None = None, headers: dict | None = None, timeout: int = 60):
    if headers is None:
        headers = {}
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body, dict(resp.headers)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body, dict(exc.headers)


def build_multipart(files: list[tuple[str, Path]]) -> tuple[bytes, str]:
    boundary = f"----VidSynthBoundary{uuid.uuid4().hex}"
    body = bytearray()
    for field_name, file_path in files:
        filename = file_path.name
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8")
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(file_path.read_bytes())
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), boundary


def upload_video(base_url: str, video_path: Path) -> None:
    log("API POST /api/import/videos (multipart)")
    body, boundary = build_multipart([("files", video_path)])
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    status, resp_body, _ = http_request("POST", f"{base_url}/api/import/videos", headers=headers, timeout=300)
    log(f"-> status={status} body={resp_body[:400]}")


def collect_sse(base_url: str, duration: int = 5, max_events: int = 5) -> list[dict]:
    parsed = urllib.parse.urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = "/api/events"
    events: list[dict] = []
    conn = http.client.HTTPConnection(host, port, timeout=duration)
    log("API GET /api/events (SSE snapshot)")
    try:
        conn.request("GET", path, headers={"Accept": "text/event-stream"})
        resp = conn.getresponse()
        start = time.time()
        while time.time() - start < duration and len(events) < max_events:
            try:
                line = resp.readline()
            except Exception:
                break
            if not line:
                break
            text = line.decode("utf-8", errors="replace").strip()
            if text.startswith("data:"):
                payload = text[5:].strip()
                try:
                    events.append(json.loads(payload))
                except json.JSONDecodeError:
                    continue
    finally:
        conn.close()
    log(f"-> events={len(events)} sample={events[:2]}")
    return events


def wait_for_status(path: Path, *, timeout: int = 900, poll_interval: float = 2.0) -> dict | None:
    start = time.time()
    last_payload = None
    while time.time() - start < timeout:
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                last_payload = payload
                status = payload.get("status")
                progress = payload.get("progress")
                log(f"status={status} progress={progress}")
                if status in {"done", "cached", "error"}:
                    return payload
        time.sleep(poll_interval)
    return last_payload


def inspect_clips(clips_path: Path) -> dict:
    if not clips_path.exists():
        return {"ok": False, "reason": "clips.json missing"}
    try:
        payload = json.loads(clips_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "reason": "clips.json invalid json"}
    if not isinstance(payload, list) or not payload:
        return {"ok": False, "reason": "clips.json empty"}
    sample = payload[:3]
    for entry in sample:
        if not isinstance(entry, dict):
            return {"ok": False, "reason": "clips.json entry not dict"}
        for key in ("clip_id", "t_start", "t_end"):
            if key not in entry:
                return {"ok": False, "reason": f"clips.json missing {key}"}
    return {"ok": True, "count": len(payload), "sample": sample}


def inspect_scores(scores_path: Path, video_id: str, workspace_root: Path) -> dict:
    if not scores_path.exists():
        return {"ok": False, "reason": "scores.json missing"}
    try:
        payload = json.loads(scores_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "reason": "scores.json invalid json"}
    scores_map = payload.get("scores", {})
    entries = scores_map.get(video_id) if isinstance(scores_map, dict) else None
    if not isinstance(entries, list) or not entries:
        return {"ok": False, "reason": "scores.json missing entries for video"}
    missing_thumbs = 0
    for entry in entries:
        thumb_rel = entry.get("thumb_url")
        if not thumb_rel:
            missing_thumbs += 1
            continue
        thumb_path = workspace_root / thumb_rel
        if not thumb_path.exists():
            missing_thumbs += 1
    return {
        "ok": True,
        "count": len(entries),
        "missing_thumbnails": missing_thumbs,
        "sample": entries[:3],
    }


def inspect_edl(edl_path: Path) -> dict:
    if not edl_path.exists():
        return {"ok": False, "reason": "edl.json missing"}
    try:
        payload = json.loads(edl_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "reason": "edl.json invalid json"}
    if not isinstance(payload, list) or not payload:
        return {"ok": False, "reason": "edl.json empty"}
    for entry in payload[:3]:
        if not isinstance(entry, dict):
            return {"ok": False, "reason": "edl.json entry not dict"}
        for key in ("video_id", "t_start", "t_end"):
            if key not in entry:
                return {"ok": False, "reason": f"edl.json missing {key}"}
    return {"ok": True, "count": len(payload), "sample": payload[:3]}


def inspect_output(output_path: Path) -> dict:
    if not output_path.exists():
        return {"ok": False, "reason": "output.mp4 missing"}
    size = output_path.stat().st_size
    if size <= 0:
        return {"ok": False, "reason": "output.mp4 empty"}
    return {"ok": True, "size_bytes": size}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("VIDSYNTH_API_BASE", "http://127.0.0.1:8000"))
    parser.add_argument("--video", default="TheBestRunningShoes.mp4")
    parser.add_argument("--theme", default="running shoes")
    parser.add_argument("--force-upload", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    workspace_root = Path(os.environ.get("VIDSYNTH_WORKSPACE_ROOT", repo_root / "workspace")).resolve()
    video_path = workspace_root / "videos" / args.video
    video_id = Path(args.video).stem

    summary: dict = {"errors": [], "warnings": []}

    log(f"repo_root={repo_root}")
    log(f"workspace_root={workspace_root}")
    log(f"base_url={args.base_url}")

    if not video_path.exists():
        summary["errors"].append(f"video missing: {video_path}")
        log(f"ERROR video missing: {video_path}")
        write_report(repo_root / "E2E_REPORT.md", summary)
        return 1

    # assets list
    status, body, _ = http_request("GET", f"{args.base_url}/api/assets")
    log(f"API GET /api/assets -> status={status}")
    log(f"body={body[:400]}")
    assets_payload = []
    try:
        assets_payload = json.loads(body) if status == 200 else []
    except json.JSONDecodeError:
        summary["warnings"].append("assets response invalid json")

    asset_found = any(isinstance(item, dict) and item.get("id") == video_id for item in assets_payload)
    log(f"asset_found={asset_found}")

    if args.force_upload or not asset_found:
        upload_video(args.base_url, video_path)
        status, body, _ = http_request("GET", f"{args.base_url}/api/assets")
        log(f"API GET /api/assets (after upload) -> status={status}")
        log(f"body={body[:400]}")
    else:
        log("skip upload: asset already present")

    collect_sse(args.base_url, duration=3, max_events=3)

    # segmentation
    log("API POST /api/segment")
    seg_payload = {"video_ids": [video_id], "force": True}
    status, body, _ = http_request("POST", f"{args.base_url}/api/segment", json_body=seg_payload)
    log(f"-> status={status} body={body[:400]}")

    seg_status_path = workspace_root / "segmentation" / video_id / "status.json"
    seg_status = wait_for_status(seg_status_path, timeout=1200)
    if not seg_status:
        summary["errors"].append("segmentation status missing")
    elif seg_status.get("status") == "error":
        summary["errors"].append(f"segmentation error: {seg_status.get('message')}")

    clips_path = workspace_root / "segmentation" / video_id / "clips.json"
    clips_check = inspect_clips(clips_path)
    log(f"clips_check={clips_check}")
    if not clips_check.get("ok"):
        summary["errors"].append(f"clips_check failed: {clips_check.get('reason')}")

    collect_sse(args.base_url, duration=3, max_events=5)

    # theme expand
    log("API POST /api/theme/expand")
    expand_payload = {"theme_text": args.theme}
    status, body, _ = http_request("POST", f"{args.base_url}/api/theme/expand", json_body=expand_payload)
    log(f"-> status={status} body={body[:400]}")
    try:
        expand_data = json.loads(body) if status == 200 else {}
    except json.JSONDecodeError:
        expand_data = {}
        summary["warnings"].append("theme expand invalid json")

    positives = expand_data.get("positives") or [args.theme]
    negatives = expand_data.get("negatives") or []

    # theme analyze
    log("API POST /api/theme/analyze")
    analyze_payload = {
        "theme": args.theme,
        "positives": positives,
        "negatives": negatives,
        "video_ids": [video_id],
        "force": True,
    }
    status, body, _ = http_request("POST", f"{args.base_url}/api/theme/analyze", json_body=analyze_payload)
    log(f"-> status={status} body={body[:400]}")
    theme_slug = None
    try:
        analyze_data = json.loads(body) if status == 200 else {}
        theme_slug = analyze_data.get("theme_slug") or None
    except json.JSONDecodeError:
        summary["warnings"].append("theme analyze invalid json")

    if not theme_slug:
        theme_slug = args.theme.lower().replace(" ", "_")

    theme_status_path = workspace_root / "themes" / theme_slug / "status.json"
    theme_status = wait_for_status(theme_status_path, timeout=1200)
    if not theme_status:
        summary["errors"].append("theme status missing")
    elif theme_status.get("status") == "error":
        summary["errors"].append(f"theme analyze error: {theme_status.get('message')}")

    scores_path = workspace_root / "themes" / theme_slug / "scores.json"
    scores_check = inspect_scores(scores_path, video_id, workspace_root)
    log(f"scores_check={scores_check}")
    if not scores_check.get("ok"):
        summary["errors"].append(f"scores_check failed: {scores_check.get('reason')}")
    if scores_check.get("missing_thumbnails", 0) > 0:
        summary["warnings"].append(f"missing thumbnails: {scores_check.get('missing_thumbnails')}")

    status, body, _ = http_request("GET", f"{args.base_url}/api/theme/{theme_slug}/result")
    log(f"API GET /api/theme/{theme_slug}/result -> status={status} body={body[:400]}")

    collect_sse(args.base_url, duration=3, max_events=5)

    # sequence
    log("API POST /api/sequence")
    seq_payload = {
        "theme": args.theme,
        "theme_slug": theme_slug,
        "params": {
            "upper_threshold": 0.2,
            "lower_threshold": 0.21,
            "min_duration": 2.0,
            "max_duration": 6.0,
            "merge_gap": 1.0,
        },
        "force": True,
        "video_ids": [video_id],
    }
    status, body, _ = http_request("POST", f"{args.base_url}/api/sequence", json_body=seq_payload)
    log(f"-> status={status} body={body[:400]}")

    seq_status_path = workspace_root / "edl" / theme_slug / "status.json"
    seq_status = wait_for_status(seq_status_path, timeout=600)
    if not seq_status:
        summary["errors"].append("sequence status missing")
    elif seq_status.get("status") == "error":
        summary["errors"].append(f"sequence error: {seq_status.get('message')}")

    edl_path = workspace_root / "edl" / theme_slug / video_id / "edl.json"
    edl_check = inspect_edl(edl_path)
    log(f"edl_check={edl_check}")
    if not edl_check.get("ok"):
        summary["errors"].append(f"edl_check failed: {edl_check.get('reason')}")

    status, body, _ = http_request("GET", f"{args.base_url}/api/sequence/{theme_slug}/{video_id}/edl")
    log(f"API GET /api/sequence/{theme_slug}/{video_id}/edl -> status={status} body={body[:400]}")

    collect_sse(args.base_url, duration=3, max_events=5)

    # export
    log("API POST /api/export")
    export_payload = {
        "theme": args.theme,
        "theme_slug": theme_slug,
        "video_id": video_id,
        "force": True,
    }
    status, body, _ = http_request("POST", f"{args.base_url}/api/export", json_body=export_payload, timeout=120)
    log(f"-> status={status} body={body[:400]}")

    export_status_path = workspace_root / "exports" / theme_slug / video_id / "status.json"
    export_status = wait_for_status(export_status_path, timeout=1800)
    if not export_status:
        summary["errors"].append("export status missing")
    elif export_status.get("status") == "error":
        summary["errors"].append(f"export error: {export_status.get('message')}")

    status, body, _ = http_request("GET", f"{args.base_url}/api/export/{theme_slug}/{video_id}")
    log(f"API GET /api/export/{theme_slug}/{video_id} -> status={status} body={body[:400]}")

    output_path = workspace_root / "exports" / theme_slug / video_id / "output.mp4"
    output_check = inspect_output(output_path)
    log(f"output_check={output_check}")
    if not output_check.get("ok"):
        summary["errors"].append(f"output_check failed: {output_check.get('reason')}")

    # final assets snapshot
    status, body, _ = http_request("GET", f"{args.base_url}/api/assets")
    log(f"API GET /api/assets (final) -> status={status}")
    log(f"body={body[:400]}")

    summary["success"] = not summary["errors"]
    summary["video_id"] = video_id
    summary["theme_slug"] = theme_slug
    summary["clips_check"] = clips_check
    summary["scores_check"] = scores_check
    summary["edl_check"] = edl_check
    summary["output_check"] = output_check
    write_report(repo_root / "E2E_REPORT.md", summary)
    log("report written: E2E_REPORT.md")
    return 0 if summary["success"] else 2


LOG_LINES: list[str] = []

if __name__ == "__main__":
    raise SystemExit(main())
