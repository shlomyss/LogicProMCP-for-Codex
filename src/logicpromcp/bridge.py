from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Lock, Thread
import time
from typing import Any
from urllib.parse import urlparse


@dataclass
class BridgeEvent:
    event_type: str
    tick: int
    channel: int | None = None
    pitch: int | None = None
    velocity: int | None = None
    duration: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class BridgeTrack:
    instance_id: str
    name: str
    source: str
    last_seen: float
    events: list[BridgeEvent] = field(default_factory=list)

    @property
    def note_count(self) -> int:
        return sum(1 for event in self.events if event.event_type == "note")

    @property
    def channels(self) -> list[int]:
        return sorted({
            event.channel for event in self.events if event.channel is not None
        })


class BridgeStore:
    def __init__(self) -> None:
        self._tracks: dict[str, BridgeTrack] = {}
        self._lock = Lock()

    def reset(self) -> None:
        with self._lock:
            self._tracks.clear()

    def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        instance_id = str(payload.get("instance_id") or payload.get("track_id") or "").strip()
        if not instance_id:
            raise ValueError("payload must include instance_id or track_id")

        track_name = str(payload.get("track_name") or payload.get("name") or instance_id)
        source = str(payload.get("source") or "logic-auv3")
        events_payload = payload.get("events") or []
        if not isinstance(events_payload, list):
            raise ValueError("events must be a list")

        events = [_parse_event(event) for event in events_payload]
        now = time.time()
        with self._lock:
            track = self._tracks.get(instance_id)
            if track is None:
                track = BridgeTrack(
                    instance_id=instance_id,
                    name=track_name,
                    source=source,
                    last_seen=now,
                )
                self._tracks[instance_id] = track
            track.name = track_name
            track.source = source
            track.last_seen = now
            track.events.extend(events)

        return {
            "instance_id": instance_id,
            "track_name": track_name,
            "accepted_events": len(events),
        }

    def list_tracks(self) -> list[dict[str, Any]]:
        with self._lock:
            tracks = list(self._tracks.values())

        return [
            {
                "instance_id": track.instance_id,
                "name": track.name,
                "source": track.source,
                "note_count": track.note_count,
                "channels": track.channels,
                "last_seen": track.last_seen,
            }
            for track in sorted(tracks, key=lambda item: item.name.lower())
        ]

    def read_track(self, instance_id: str) -> dict[str, Any]:
        with self._lock:
            track = self._tracks.get(instance_id)
            if track is None:
                raise KeyError(instance_id)
            events = list(track.events)

        return {
            "instance_id": track.instance_id,
            "name": track.name,
            "source": track.source,
            "note_count": track.note_count,
            "channels": track.channels,
            "events": [_event_to_dict(event) for event in events],
        }

    def read_all_tracks(self) -> dict[str, Any]:
        return {
            "track_count": len(self.list_tracks()),
            "tracks": [self.read_track(track["instance_id"]) for track in self.list_tracks()],
        }


DEFAULT_STORE = BridgeStore()


def start_bridge_http_server(host: str = "127.0.0.1", port: int = 8765, store: BridgeStore = DEFAULT_STORE) -> ThreadingHTTPServer:
    handler = _handler_factory(store)
    server = ThreadingHTTPServer((host, port), handler)
    thread = Thread(target=server.serve_forever, name="logicpromcp-bridge", daemon=True)
    thread.start()
    return server


def _parse_event(payload: Any) -> BridgeEvent:
    if not isinstance(payload, dict):
        raise ValueError("each event must be an object")

    return BridgeEvent(
        event_type=str(payload.get("type") or "note"),
        tick=int(payload.get("tick") or payload.get("start") or 0),
        channel=_optional_int(payload.get("channel")),
        pitch=_optional_int(payload.get("pitch")),
        velocity=_optional_int(payload.get("velocity")),
        duration=_optional_int(payload.get("duration")),
        raw=payload,
    )


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _event_to_dict(event: BridgeEvent) -> dict[str, Any]:
    return {
        "type": event.event_type,
        "tick": event.tick,
        "channel": event.channel,
        "pitch": event.pitch,
        "velocity": event.velocity,
        "duration": event.duration,
        "raw": event.raw,
    }


def _handler_factory(store: BridgeStore):
    class BridgeRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/health":
                self._send_json({"ok": True, "service": "LogicProMCP bridge"})
                return
            if path == "/tracks":
                self._send_json({"tracks": store.list_tracks()})
                return
            self.send_error(404)

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path == "/reset":
                store.reset()
                self._send_json({"ok": True})
                return
            if path != "/ingest":
                self.send_error(404)
                return

            try:
                length = int(self.headers.get("content-length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                response = store.ingest(payload)
            except Exception as exc:  # noqa: BLE001 - HTTP boundary returns errors as JSON.
                self._send_json({"ok": False, "error": str(exc)}, status=400)
                return

            self._send_json({"ok": True, **response})

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return BridgeRequestHandler
