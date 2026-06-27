# Architecture

LogicProMCP has three layers:

- MIDI core: standard-library MIDI reading, summarizing, and generation.
- Logic bridge receiver: local HTTP receiver that aggregates events from Logic-side extension instances.
- MCP adapter: exposes the core as Model Context Protocol tools.

## Current Data Flow

```text
Logic track with AUv3 bridge
  -> local bridge receiver on 127.0.0.1:8765
  -> read_all_logic_tracks MCP tool
  -> agent analysis
  -> create_midi_region MCP tool
  -> generated .mid file
  -> Logic Pro import / drag and drop
```

Standard MIDI File import/export remains available as a fallback because it works with Logic Pro today and does not depend on extension hosting.

## Why Not Direct Project Editing Yet?

Logic Pro does not provide a public API for reading every track and MIDI region from an open project, nor a public API for inserting a generated region at an arbitrary timeline position. Direct project mutation would require relying on private file formats or brittle UI automation.

The extension-based interpretation of "all tracks" is: all tracks that host a LogicProMCP bridge instance. A saved Logic template can make this feel automatic in normal use.

## Live Bridge Options

### AUv3 MIDI FX

An AUv3 MIDI FX plugin can be inserted on tracks and can observe/generate MIDI passing through those tracks. This is the best path for live capture and generated MIDI playback inside Logic. It still needs one plugin instance per track that should be visible to the bridge.

### Virtual MIDI

A CoreMIDI virtual source can send generated notes into Logic. The user can record that input onto a new Software Instrument track. This is reliable for writing notes but does not read existing regions.

### macOS Automation

AppleScript, Shortcuts, and Accessibility scripting can activate Logic and trigger import flows. This can reduce manual steps, but it must be treated as an optional helper because UI scripting can break when windows, language, or Logic versions differ.

## Next Milestones

1. Add sidecar JSON files with prompt, intended track name, BPM, key, bar count, and generated file path.
2. Add CoreMIDI virtual output for live recording into Logic.
3. Build AUv3 MIDI FX capture/generator.
4. Add optional AppleScript import helper.
