from pathlib import Path
import json
import sys
import tempfile
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
old_path=sys.path[:]
try:
    sys.path.insert(0,str(ROOT/'tools'))
    import qwen_rom_combined_nearbaseline_layer_prepare as prep
finally:
    sys.path[:]=old_path


class ExistingBytesTests(unittest.TestCase):
    def test_existing_raw_exact_match_and_one_byte_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            t=Path(temp);data=np.arange(4194304,dtype='<u4')
            np.save(t/'source.npy',data);(t/'raw.bin').write_bytes(data.tobytes())
            prep.raw_matches_npy(t/'raw.bin',t/'source.npy')
            with (t/'raw.bin').open('r+b') as stream:
                stream.seek(1234567);b=stream.read(1);stream.seek(1234567);stream.write(bytes([b[0]^1]))
            with self.assertRaisesRegex(ValueError,'raw KV bytes differ'):
                prep.raw_matches_npy(t/'raw.bin',t/'source.npy')

    def test_wrong_extent_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            t=Path(temp);np.save(t/'source.npy',np.zeros(16,dtype='<u4'));(t/'raw.bin').write_bytes(bytes(64))
            with self.assertRaisesRegex(ValueError,'full KV extent'):
                prep.raw_matches_npy(t/'raw.bin',t/'source.npy')

    def test_near0_book_cannot_prepare_or_create_output(self):
        with tempfile.TemporaryDirectory() as temp:
            t=Path(temp);p=t/'old.json';p.write_text(json.dumps(dict(near_hbm_enabled=False,real_mem=True)))
            with self.assertRaisesRegex(ValueError,'NEAR1 per-layer selection'):
                prep.prepare(p,t,'unused',t,[t]*4,0,t/'output',ROOT)
            self.assertFalse((t/'output').exists())


if __name__=='__main__':unittest.main()
