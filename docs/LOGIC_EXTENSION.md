# Logic Extension Bridge

The target Logic integration is an AUv3 MIDI FX extension named `LogicProMCP Bridge`.

## Important Constraint

Logic Pro does not expose a public extension API that allows one plugin or MCP server to automatically enumerate every MIDI region across an open project. An extension can observe MIDI routed through that extension.

For "read all tracks" behavior, the bridge must be present on every MIDI/software-instrument track that should be readable. The practical setup is:

1. Add `LogicProMCP Bridge` as a MIDI FX plugin on each relevant track.
2. Save that as a Logic template.
3. Use the MCP tool `read_all_logic_tracks`; it aggregates every bridge instance that has reported events.

## Data Flow

```text
Logic track 1 -> AUv3 MIDI FX bridge instance --\
Logic track 2 -> AUv3 MIDI FX bridge instance ----> 127.0.0.1:8765 -> MCP tools
Logic track N -> AUv3 MIDI FX bridge instance --/
```

## Bridge HTTP Contract

The MCP server starts a local HTTP receiver:

```text
POST http://127.0.0.1:8765/ingest
GET  http://127.0.0.1:8765/tracks
GET  http://127.0.0.1:8765/health
POST http://127.0.0.1:8765/reset
```

Example payload from one AUv3 instance:

```json
{
  "instance_id": "logic-track-bass-uuid",
  "track_name": "Bass",
  "source": "logic-auv3",
  "events": [
    {
      "type": "note",
      "tick": 0,
      "duration": 240,
      "channel": 1,
      "pitch": 48,
      "velocity": 92
    }
  ]
}
```

## MCP Tools

- `bridge_status`: shows the local bridge endpoint and currently captured tracks.
- `list_logic_tracks`: lists all Logic-side bridge instances that reported events.
- `read_logic_track`: reads one captured track by `instance_id`.
- `read_all_logic_tracks`: aggregates all captured track event data.

## AUv3 Notes

The AUv3 target should:

- Be a MIDI FX audio unit so Logic can insert it before an instrument.
- Pass incoming MIDI through unchanged.
- Copy incoming note/controller events into a small buffer.
- Periodically send buffered events to `http://127.0.0.1:8765/ingest`.
- Let the user set a track name/label in the plugin UI because Logic may not expose the host track name to the plugin.

The extension is the next major build step. The Python side now has the receiver and MCP aggregation tools that the extension will talk to.
