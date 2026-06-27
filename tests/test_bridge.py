import unittest

from logicpromcp.bridge import BridgeStore


class BridgeStoreTests(unittest.TestCase):
    def test_ingests_and_lists_multiple_logic_tracks(self):
        store = BridgeStore()
        store.ingest({
            "instance_id": "bass-track",
            "track_name": "Bass",
            "events": [
                {"type": "note", "tick": 0, "duration": 240, "channel": 1, "pitch": 48, "velocity": 100}
            ],
        })
        store.ingest({
            "instance_id": "keys-track",
            "track_name": "Keys",
            "events": [
                {"type": "note", "tick": 0, "duration": 480, "channel": 1, "pitch": 60, "velocity": 88},
                {"type": "note", "tick": 0, "duration": 480, "channel": 1, "pitch": 64, "velocity": 88},
            ],
        })

        all_tracks = store.read_all_tracks()

        self.assertEqual(all_tracks["track_count"], 2)
        self.assertEqual(sum(track["note_count"] for track in all_tracks["tracks"]), 3)


if __name__ == "__main__":
    unittest.main()
