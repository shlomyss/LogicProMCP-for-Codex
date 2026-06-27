# LogicProMCP

LogicProMCP is a local Model Context Protocol server plus a planned Logic Pro MIDI FX bridge for working with Logic Pro MIDI material.

The intended Logic integration is:

1. Insert a `LogicProMCP Bridge` AUv3 MIDI FX plugin on every MIDI/software-instrument track that should be readable.
2. Each plugin instance sends captured MIDI events to the local MCP sidecar.
3. The MCP server exposes the aggregated result as "all Logic tracks."
4. Generated MIDI can be written as `.mid` files first, then later sent back through a virtual MIDI/AUv3 output path.

Logic Pro does not currently expose a public project API that lets one local service directly enumerate every track and MIDI region in an open project. "Read all tracks automatically" therefore means "read all tracks that have the bridge extension inserted," ideally through a saved Logic template.

## Tools

- `bridge_status`: show the local Logic bridge receiver.
- `list_logic_tracks`: list tracks reported by Logic-side bridge instances.
- `read_logic_track`: read captured MIDI from one bridge instance.
- `read_all_logic_tracks`: read captured MIDI from all bridge instances.
- `read_midi_file`: inspect a Standard MIDI File exported from Logic.
- `create_midi_region`: create a new single-region `.mid` file from a musical prompt.
- `create_drum_region`: create a drum pattern region.
- `create_chord_region`: create a chord progression region.

## Install

```bash
cd /Users/shlomy/GIT_Repos/LogicProMCP
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

## Run MCP Server

```bash
logicpromcp
```

For Claude Desktop or another MCP client, configure the command as:

```json
{
  "mcpServers": {
    "logicpro": {
      "command": "/Users/shlomy/GIT_Repos/LogicProMCP/.venv/bin/logicpromcp"
    }
  }
}
```

## CLI Smoke Test

```bash
logicpromcp-midi create --prompt "four bar funky bass line in C minor" --out examples/funky_bass.mid
logicpromcp-midi inspect examples/funky_bass.mid
```

## Logic Workflow

- To read live/playback material from Logic: run `logicpromcp`, then insert the AUv3 bridge on every track that should be visible to the MCP server.
- To read exported material: select regions in Logic, use `File > Export > Selection as MIDI File`, then pass that `.mid` path to `read_midi_file`.
- To write a new track/region: run `create_midi_region`, then drag the generated `.mid` file into Logic or use `File > Import > MIDI File`.
- To preserve tempo and bar alignment, create generated regions at the same BPM and bar length as the Logic project.

See [docs/LOGIC_EXTENSION.md](docs/LOGIC_EXTENSION.md) for the extension bridge contract.

## Roadmap

- AUv3 MIDI FX listener for live MIDI capture per inserted track.
- Virtual MIDI output for recording generated MIDI directly into Logic.
- AppleScript/Shortcuts helper for importing generated MIDI into the frontmost Logic project.
- Region metadata sidecar files for round-tripping track names, bar ranges, prompts, and model decisions.
