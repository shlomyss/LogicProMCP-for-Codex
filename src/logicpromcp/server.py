from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .bridge import DEFAULT_STORE, start_bridge_http_server
from .midi import (
    generate_chord_track,
    generate_drum_track,
    generate_region_from_prompt,
    read_midi_file as read_smf,
    write_midi_file,
)


DEFAULT_OUTPUT_DIR = Path.home() / "Music" / "LogicProMCP"
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 8765


def read_midi_file(path: str) -> dict[str, Any]:
    """Read a Standard MIDI File exported from Logic Pro."""
    return asdict(read_smf(path))


def bridge_status() -> dict[str, Any]:
    """Show the local Logic extension bridge status."""
    return {
        "bridge_url": f"http://{BRIDGE_HOST}:{BRIDGE_PORT}",
        "ingest_endpoint": f"http://{BRIDGE_HOST}:{BRIDGE_PORT}/ingest",
        "track_count": len(DEFAULT_STORE.list_tracks()),
        "tracks": DEFAULT_STORE.list_tracks(),
    }


def list_logic_tracks() -> dict[str, Any]:
    """List Logic tracks currently visible through inserted LogicProMCP extensions."""
    return {
        "tracks": DEFAULT_STORE.list_tracks(),
        "note": "Tracks appear here after the Logic-side AUv3 bridge instance reports MIDI events.",
    }


def read_logic_track(instance_id: str) -> dict[str, Any]:
    """Read MIDI events captured from one Logic-side bridge instance."""
    try:
        return DEFAULT_STORE.read_track(instance_id)
    except KeyError:
        return {
            "error": f"No captured Logic track with instance_id {instance_id!r}",
            "known_tracks": DEFAULT_STORE.list_tracks(),
        }


def read_all_logic_tracks() -> dict[str, Any]:
    """Read all MIDI events captured from all inserted Logic-side bridge instances."""
    payload = DEFAULT_STORE.read_all_tracks()
    payload["note"] = (
        "This is all tracks visible to LogicProMCP. Logic requires the bridge AUv3 MIDI FX "
        "to be inserted on each MIDI/software-instrument track that should be readable."
    )
    return payload


def create_midi_region(
    prompt: str,
    key: str = "C minor",
    bars: int = 4,
    bpm: int = 120,
    track_name: str = "Generated Region",
    channel: int = 1,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """Create a Logic-importable MIDI region from a short musical prompt."""
    midi_channel = max(1, min(channel, 16)) - 1
    track = generate_region_from_prompt(prompt, key=key, bars=bars, bpm=bpm, channel=midi_channel)
    track = type(track)(name=track_name or track.name, notes=track.notes, channel=track.channel)
    path = _next_output_path(output_dir, track.name)
    write_midi_file(path, [track], bpm=bpm)

    return {
        "midi_file": str(path),
        "track_name": track.name,
        "bars": bars,
        "bpm": bpm,
        "logic_workflow": "Drag this .mid file into Logic Pro, or use File > Import > MIDI File.",
    }


def create_drum_region(
    prompt: str = "four on the floor drum groove",
    bars: int = 4,
    bpm: int = 120,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """Create a drum MIDI region on channel 10."""
    track = generate_drum_track(prompt=prompt, bars=bars, channel=9)
    path = _next_output_path(output_dir, "Generated Drums")
    write_midi_file(path, [track], bpm=bpm)
    return {
        "midi_file": str(path),
        "track_name": track.name,
        "bars": bars,
        "bpm": bpm,
        "logic_workflow": "Drag this .mid file into a software instrument/drum track in Logic Pro.",
    }


def create_chord_region(
    key: str = "C minor",
    bars: int = 4,
    bpm: int = 120,
    channel: int = 1,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """Create a chord progression MIDI region."""
    midi_channel = max(1, min(channel, 16)) - 1
    track = generate_chord_track(key=key, bars=bars, channel=midi_channel)
    path = _next_output_path(output_dir, f"Generated Chords {key}")
    write_midi_file(path, [track], bpm=bpm)
    return {
        "midi_file": str(path),
        "track_name": track.name,
        "bars": bars,
        "bpm": bpm,
        "logic_workflow": "Drag this .mid file into Logic Pro to create a new region.",
    }


def _next_output_path(output_dir: str | None, name: str) -> Path:
    directory = Path(output_dir).expanduser() if output_dir else DEFAULT_OUTPUT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(char if char.isalnum() else "_" for char in name).strip("_").lower()
    safe_name = safe_name or "logic_region"

    for index in range(1, 10_000):
        path = directory / f"{safe_name}_{index:03d}.mid"
        if not path.exists():
            return path
    raise RuntimeError(f"could not allocate output filename in {directory}")


def build_mcp_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise SystemExit(
            "The MCP Python SDK is not installed. Run `python -m pip install -e .` first."
        ) from exc

    mcp = FastMCP("LogicProMCP")
    mcp.tool()(bridge_status)
    mcp.tool()(list_logic_tracks)
    mcp.tool()(read_logic_track)
    mcp.tool()(read_all_logic_tracks)
    mcp.tool()(read_midi_file)
    mcp.tool()(create_midi_region)
    mcp.tool()(create_drum_region)
    mcp.tool()(create_chord_region)
    return mcp


def main() -> None:
    start_bridge_http_server(BRIDGE_HOST, BRIDGE_PORT)
    build_mcp_server().run()


if __name__ == "__main__":
    main()
