import unittest
from pathlib import Path
from types import SimpleNamespace

from transcribe import MAX_BYTES, collect_segments, timestamp, transcribe_file, validate_upload


class TranscriberTests(unittest.TestCase):
    def test_input_validation(self):
        self.assertEqual(validate_upload("../../запись.MP4", 100), ".mp4")
        for name, size in [("x.txt", 1), ("x.mp3", 0), ("x.m4a", MAX_BYTES + 1)]:
            with self.assertRaises(ValueError):
                validate_upload(name, size)

    def test_lazy_segments_and_progress(self):
        segments = iter([
            SimpleNamespace(text=" Привет. ", start=0, end=2),
            SimpleNamespace(text=" ", start=2, end=3),
            SimpleNamespace(text="Мир!", start=3, end=10),
        ])
        progress = []
        result = collect_segments(segments, SimpleNamespace(duration=10, language="ru"), progress.append)
        self.assertEqual(result.text, "Привет.\nМир!")
        self.assertEqual(result.timed_text, "[00:00:00 — 00:00:02] Привет.\n[00:00:03 — 00:00:10] Мир!")
        self.assertEqual(progress[-1], 1.0)
        self.assertEqual(progress, sorted(progress))

    def test_empty_recording(self):
        result = collect_segments([], SimpleNamespace(duration=0, language="en"))
        self.assertEqual(result.text, "")

    def test_decode_error_is_not_swallowed(self):
        class BrokenModel:
            def transcribe(self, *args, **kwargs):
                def broken():
                    raise ValueError("Invalid audio")
                    yield
                return broken(), SimpleNamespace(duration=1, language="ru")
        with self.assertRaisesRegex(ValueError, "Invalid audio"):
            transcribe_file(BrokenModel(), Path("invalid.mp4"), None)

    def test_timestamp(self):
        self.assertEqual(timestamp(3661.9), "01:01:01")


if __name__ == "__main__":
    unittest.main()
