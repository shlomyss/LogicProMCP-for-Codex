from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import struct
from typing import Iterable


DEFAULT_PPQ = 480


@dataclass(frozen=True)
class Note:
    pitch: int
    start: int
    duration: int
    velocity: int = 88
    channel: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.pitch <= 127:
            raise ValueError("pitch must be between 0 and 127")
        if self.start < 0:
            raise ValueError("start must be >= 0")
        if self.duration <= 0:
            raise ValueError("duration must be > 0")
        if not 0 <= self.velocity <= 127:
            raise ValueError("velocity must be between 0 and 127")
        if not 0 <= self.channel <= 15:
            raise ValueError("channel must be between 0 and 15")


@dataclass(frozen=True)
class Track:
    name: str
    notes: list[Note] = field(default_factory=list)
    channel: int = 0


@dataclass(frozen=True)
class MidiSummary:
    path: str
    format_type: int
    ppq: int
    track_count: int
    tracks: list[dict]


NOTE_NAMES = {
    "C": 0,
    "C#": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "EB": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "BB": 10,
    "B": 11,
}

MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]
MAJOR_CHORD = [0, 4, 7]
MINOR_CHORD = [0, 3, 7]


def bpm_to_tempo_meta(bpm: int) -> bytes:
    micros_per_quarter = round(60_000_000 / bpm)
    return micros_per_quarter.to_bytes(3, "big")


def parse_key(key: str) -> tuple[int, bool]:
    parts = key.strip().replace("-", " ").split()
    if not parts:
        return 0, False
    root = NOTE_NAMES.get(parts[0].upper(), 0)
    minor = any(part.lower().startswith("min") or part.lower() == "m" for part in parts[1:])
    return root, minor


def note_number(name: str, octave: int = 4) -> int:
    normalized = name.strip().upper()
    if normalized not in NOTE_NAMES:
        raise ValueError(f"unknown note name: {name}")
    return 12 * (octave + 1) + NOTE_NAMES[normalized]


def write_midi_file(path: str | Path, tracks: Iterable[Track], bpm: int = 120, ppq: int = DEFAULT_PPQ) -> Path:
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    track_list = list(tracks)

    chunks = [_build_conductor_track(bpm)]
    chunks.extend(_build_note_track(track) for track in track_list)

    header = b"MThd" + struct.pack(">IHHH", 6, 1 if len(chunks) > 1 else 0, len(chunks), ppq)
    body = b"".join(b"MTrk" + struct.pack(">I", len(chunk)) + chunk for chunk in chunks)
    output_path.write_bytes(header + body)
    return output_path


def read_midi_file(path: str | Path) -> MidiSummary:
    midi_path = Path(path).expanduser().resolve()
    data = midi_path.read_bytes()
    offset = 0

    if data[offset:offset + 4] != b"MThd":
        raise ValueError("not a Standard MIDI File")
    offset += 4
    header_length = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4
    format_type, track_count, ppq = struct.unpack(">HHH", data[offset:offset + 6])
    offset += header_length

    tracks = []
    for index in range(track_count):
        if data[offset:offset + 4] != b"MTrk":
            raise ValueError(f"missing MTrk chunk at track {index}")
        offset += 4
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
        chunk = data[offset:offset + length]
        offset += length
        tracks.append(_summarize_track(index, chunk))

    return MidiSummary(
        path=str(midi_path),
        format_type=format_type,
        ppq=ppq,
        track_count=track_count,
        tracks=tracks,
    )


def generate_region_from_prompt(prompt: str, key: str = "C minor", bars: int = 4, bpm: int = 120, channel: int = 0) -> Track:
    text = prompt.lower()
    if "drum" in text or "beat" in text:
        return generate_drum_track(prompt, bars=bars, channel=9)
    if "chord" in text or "pad" in text or "progression" in text:
        return generate_chord_track(key=key, bars=bars, channel=channel)
    if "bass" in text:
        return generate_bass_track(key=key, bars=bars, channel=channel)
    return generate_melody_track(key=key, bars=bars, channel=channel)


def generate_drum_track(prompt: str = "", bars: int = 4, channel: int = 9) -> Track:
    notes: list[Note] = []
    beat = DEFAULT_PPQ
    sixteenth = beat // 4
    total_steps = bars * 16
    text = prompt.lower()
    busy_hats = "funk" in text or "busy" in text or "dance" in text

    for step in range(total_steps):
        tick = step * sixteenth
        if step % 4 == 0:
            notes.append(Note(36, tick, sixteenth, 108, channel))
        if step % 8 == 4:
            notes.append(Note(38, tick, sixteenth, 96, channel))
        if busy_hats or step % 2 == 0:
            velocity = 70 if step % 4 else 82
            notes.append(Note(42, tick, sixteenth, velocity, channel))
        if "open" in text and step % 16 == 14:
            notes.append(Note(46, tick, sixteenth * 2, 78, channel))

    return Track(name="Generated Drums", notes=notes, channel=channel)


def generate_chord_track(key: str = "C minor", bars: int = 4, channel: int = 0) -> Track:
    root, minor = parse_key(key)
    scale = MINOR_SCALE if minor else MAJOR_SCALE
    quality = MINOR_CHORD if minor else MAJOR_CHORD
    progression = [0, 5, 3, 4] if minor else [0, 4, 5, 3]
    notes: list[Note] = []
    bar_ticks = DEFAULT_PPQ * 4

    for bar in range(bars):
        degree = progression[bar % len(progression)]
        chord_root = 48 + root + scale[degree % len(scale)]
        start = bar * bar_ticks
        for interval in quality:
            notes.append(Note(chord_root + interval, start, bar_ticks, 82, channel))
        notes.append(Note(chord_root + 12, start, bar_ticks, 68, channel))

    return Track(name=f"Generated Chords {key}", notes=notes, channel=channel)


def generate_bass_track(key: str = "C minor", bars: int = 4, channel: int = 0) -> Track:
    root, minor = parse_key(key)
    scale = MINOR_SCALE if minor else MAJOR_SCALE
    pattern = [0, 0, 4, 5, 0, 6, 5, 4]
    notes: list[Note] = []
    eighth = DEFAULT_PPQ // 2

    for step in range(bars * 8):
        degree = pattern[step % len(pattern)]
        pitch = 36 + root + scale[degree % len(scale)]
        if step % 4 == 3:
            pitch += 12
        notes.append(Note(pitch, step * eighth, eighth, 94 if step % 2 == 0 else 76, channel))

    return Track(name=f"Generated Bass {key}", notes=notes, channel=channel)


def generate_melody_track(key: str = "C minor", bars: int = 4, channel: int = 0) -> Track:
    root, minor = parse_key(key)
    scale = MINOR_SCALE if minor else MAJOR_SCALE
    pattern = [0, 2, 4, 5, 4, 2, 1, 2, 0, 4, 6, 5, 4, 2, 0, 1]
    notes: list[Note] = []
    eighth = DEFAULT_PPQ // 2

    for step in range(bars * 8):
        if step % 8 in {6}:
            continue
        degree = pattern[step % len(pattern)]
        pitch = 60 + root + scale[degree % len(scale)]
        duration = eighth * 2 if step % 8 == 7 else eighth
        notes.append(Note(pitch, step * eighth, duration, 86, channel))

    return Track(name=f"Generated Melody {key}", notes=notes, channel=channel)


def _build_conductor_track(bpm: int) -> bytes:
    events = [
        (0, b"\xff\x51\x03" + bpm_to_tempo_meta(bpm)),
        (0, b"\xff\x58\x04\x04\x02\x18\x08"),
        (0, b"\xff\x2f\x00"),
    ]
    return _encode_events(events)


def _build_note_track(track: Track) -> bytes:
    events: list[tuple[int, bytes]] = [(0, _meta_text(0x03, track.name))]

    for note in track.notes:
        on_status = bytes([0x90 | note.channel])
        off_status = bytes([0x80 | note.channel])
        events.append((note.start, on_status + bytes([note.pitch, note.velocity])))
        events.append((note.start + note.duration, off_status + bytes([note.pitch, 0])))

    end_tick = max((note.start + note.duration for note in track.notes), default=0)
    events.append((end_tick, b"\xff\x2f\x00"))
    return _encode_events(sorted(events, key=lambda item: (item[0], item[1][0] == 0x80)))


def _encode_events(events: Iterable[tuple[int, bytes]]) -> bytes:
    output = bytearray()
    last_tick = 0
    for absolute_tick, payload in events:
        output.extend(_var_len(absolute_tick - last_tick))
        output.extend(payload)
        last_tick = absolute_tick
    return bytes(output)


def _meta_text(kind: int, text: str) -> bytes:
    encoded = text.encode("utf-8")
    return bytes([0xFF, kind]) + _var_len(len(encoded)) + encoded


def _var_len(value: int) -> bytes:
    if value < 0:
        raise ValueError("variable-length value must be >= 0")
    buffer = value & 0x7F
    value >>= 7
    while value:
        buffer <<= 8
        buffer |= ((value & 0x7F) | 0x80)
        value >>= 7

    output = bytearray()
    while True:
        output.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            break
    return bytes(output)


def _read_var_len(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    while True:
        byte = data[offset]
        offset += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, offset


def _summarize_track(index: int, chunk: bytes) -> dict:
    offset = 0
    tick = 0
    running_status = None
    track_name = f"Track {index + 1}"
    note_count = 0
    channels: set[int] = set()
    pitches: list[int] = []
    end_tick = 0

    while offset < len(chunk):
        delta, offset = _read_var_len(chunk, offset)
        tick += delta
        status = chunk[offset]

        if status < 0x80 and running_status is not None:
            status = running_status
        else:
            offset += 1
            if status < 0xF0:
                running_status = status

        if status == 0xFF:
            meta_type = chunk[offset]
            offset += 1
            length, offset = _read_var_len(chunk, offset)
            payload = chunk[offset:offset + length]
            offset += length
            if meta_type == 0x03:
                track_name = payload.decode("utf-8", errors="replace")
            if meta_type == 0x2F:
                end_tick = max(end_tick, tick)
                break
            continue

        if status in {0xF0, 0xF7}:
            length, offset = _read_var_len(chunk, offset)
            offset += length
            continue

        event_type = status & 0xF0
        channel = status & 0x0F
        data_length = 1 if event_type in {0xC0, 0xD0} else 2
        payload = chunk[offset:offset + data_length]
        offset += data_length

        if event_type == 0x90 and len(payload) == 2 and payload[1] > 0:
            note_count += 1
            channels.add(channel + 1)
            pitches.append(payload[0])
            end_tick = max(end_tick, tick)

    return {
        "index": index,
        "name": track_name,
        "note_count": note_count,
        "channels": sorted(channels),
        "lowest_pitch": min(pitches) if pitches else None,
        "highest_pitch": max(pitches) if pitches else None,
        "end_tick": end_tick,
    }
