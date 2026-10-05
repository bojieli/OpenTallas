"""Reject corrupt metadata and prove the reader never requests payload ranges."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('catalogue', Path(__file__).resolve().parents[1] / 'tools/dsrom_checkpoint_header_catalogue.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


class HeaderMetadataTests(unittest.TestCase):
    def test_only_declared_header_ranges_are_requested(self):
        raw = b'{"x":{"dtype":"I8","shape":[2,2],"data_offsets":[0,4]}} '
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'one.safetensors'
            path.write_bytes(struct.pack('<Q', len(raw)) + raw + b'opaque-payload-never-requested')
            calls = []
            original = C.os.pread
            def tracked(fd, size, offset):
                calls.append((size, offset))
                self.assertLessEqual(offset + size, 8 + len(raw))
                return original(fd, size, offset)
            with patch.object(C.os, 'pread', tracked):
                prefix, actual, identity = C.read_header(path)
            self.assertEqual(calls, [(8, 0), (len(raw), 8)])
            self.assertEqual(actual, raw)
            self.assertEqual(identity['checkpoint_bytes_read'], 8 + len(raw))
            self.assertNotEqual(C.sha(actual), C.sha(prefix + actual))

    def test_reject_short_length_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'short.safetensors'
            path.write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError, 'short header length'):
                C.read_header(path)

    def test_reject_oversized_header_before_second_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'huge.safetensors'
            path.write_bytes(struct.pack('<Q', 17 * 1024**2))
            with patch.object(C.os, 'pread', wraps=C.os.pread) as reader:
                with self.assertRaisesRegex(ValueError, 'unbounded/invalid'):
                    C.read_header(path)
                self.assertEqual(reader.call_count, 1)

    def test_reject_index_shard_disagreement(self):
        header = {'x': {'dtype': 'I8', 'shape': [4], 'data_offsets': [0, 4]}}
        with self.assertRaisesRegex(ValueError, 'index/header mapping mismatch'):
            C.validate_header(header, 'a', {'x': 'b'}, 16, 20)

    def test_reject_shape_span_disagreement(self):
        header = {'x': {'dtype': 'I8', 'shape': [5], 'data_offsets': [0, 4]}}
        with self.assertRaisesRegex(ValueError, 'shape/span disagreement'):
            C.validate_header(header, 'a', {'x': 'a'}, 16, 20)

    def test_reject_outside_file_offsets(self):
        header = {'x': {'dtype': 'I8', 'shape': [5], 'data_offsets': [0, 5]}}
        with self.assertRaisesRegex(ValueError, 'outside payload'):
            C.validate_header(header, 'a', {'x': 'a'}, 16, 20)

    def test_reject_overlapping_tensor_spans(self):
        header = {key: {'dtype': 'I8', 'shape': [4], 'data_offsets': [0, 4]} for key in ['x', 'y']}
        with self.assertRaisesRegex(ValueError, 'overlap/gap'):
            C.validate_header(header, 'a', {'x': 'a', 'y': 'a'}, 16, 20)

    def test_reject_duplicate_keys_without_silent_last_value(self):
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
            C.parse(b'{"x": 1,"x": 2}')


if __name__ == '__main__':
    unittest.main()
