from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .midi import generate_region_from_prompt, read_midi_file, write_midi_file


def main() -> None:
    parser = argparse.ArgumentParser(prog="logicpromcp-midi")
    subcommands = parser.add_subparsers(dest="command", required=True)

    create = subcommands.add_parser("create", help="create a MIDI region file")
    create.add_argument("--prompt", required=True)
    create.add_argument("--key", default="C minor")
    create.add_argument("--bars", type=int, default=4)
    create.add_argument("--bpm", type=int, default=120)
    create.add_argument("--channel", type=int, default=1)
    create.add_argument("--track-name", default="Generated Region")
    create.add_argument("--out", required=True)

    inspect = subcommands.add_parser("inspect", help="inspect a MIDI file")
    inspect.add_argument("path")

    args = parser.parse_args()
    if args.command == "create":
        track = generate_region_from_prompt(
            args.prompt,
            key=args.key,
            bars=args.bars,
            bpm=args.bpm,
            channel=max(1, min(args.channel, 16)) - 1,
        )
        track = type(track)(name=args.track_name, notes=track.notes, channel=track.channel)
        path = write_midi_file(Path(args.out), [track], bpm=args.bpm)
        print(json.dumps({"midi_file": str(path), "track_name": track.name}, indent=2))
    elif args.command == "inspect":
        print(json.dumps(asdict(read_midi_file(args.path)), indent=2))


if __name__ == "__main__":
    main()
