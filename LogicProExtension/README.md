# LogicProMCP Bridge AUv3 Target

This folder is reserved for the Logic-side AUv3 MIDI FX extension.

The first Swift target should implement:

- MIDI FX pass-through.
- Per-instance ID generation.
- User-editable track label.
- Buffered note/controller capture.
- Local HTTP POST to `http://127.0.0.1:8765/ingest`.

The MCP server already exposes the receiving side through `logicpromcp.bridge`.

## Why Per-Track?

Logic can host MIDI FX plugins on individual tracks. It does not provide one global third-party extension point that reads every track/region in the project automatically. To make the MCP server see all tracks, use a Logic template with this bridge inserted on every MIDI/software-instrument track.
