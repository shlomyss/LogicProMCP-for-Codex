from dataclasses import asdict
import tempfile
from pathlib import Path
import unittest

from logicpromcp.midi import generate_region_from_prompt, read_midi_file, write_midi_file


class MidiTests(unittest.TestCase):
    def test_write_and_read_generated_bass_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            track = generate_region_from_prompt("four bar funky bass line", key="C minor", bars=4)
            path = write_midi_file(Path(tmp) / "bass.mid", [track], bpm=120)

            summary = read_midi_file(path)

        self.assertEqual(summary.track_count, 2)
        self.assertEqual(summary.ppq, 480)
        self.assertGreater(summary.tracks[1]["note_count"], 0)
        self.assertTrue(summary.tracks[1]["name"].startswith("Generated Bass"))

    def test_midi_summary_is_json_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            track = generate_region_from_prompt("simple melody", key="D major", bars=2)
            path = write_midi_file(Path(tmp) / "melody.mid", [track], bpm=100)

            payload = asdict(read_midi_file(path))

        self.assertTrue(payload["path"].endswith("melody.mid"))
        self.assertEqual(payload["tracks"][1]["channels"], [1])


if __name__ == "__main__":
    unittest.main()
