import tempfile
import unittest
from pathlib import Path

from diagnose_vm_word import collect, make


class WordProbeTest(unittest.TestCase):
    def test_exact_drive_preservation_and_bit_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "original"
            source.mkdir()
            drive = (1 << 62) | (1 << 60) | (7 << 44) | 3
            check = (2 << 62) | (1 << 60) | (32803 << 44) | (24 << 32) | 2727
            for name, values in dict(hdr=[drive, check, 3 << 62], val=[99, 0x123, 0],
                                     msk=[0, (1 << 256) - 1, 0]).items():
                (source / f"{name}.mem").write_text("".join(f"{v:x}\n" for v in values))
            (source / "vm_pre.txt").write_text("0 0 0 0123\n")
            output = Path(td) / "probe"
            make(source, output, 2727, 32803, 260)
            headers = [int(x, 16) for x in (output / "hdr.mem").read_text().split()]
            values = [int(x, 16) for x in (output / "val.mem").read_text().split()]
            self.assertEqual([(h, v) for h, v in zip(headers, values) if h >> 62 == 1],
                             [(drive, 99)])
            self.assertEqual((output / "vm_pre.txt").read_bytes(), (source / "vm_pre.txt").read_bytes())
            observed = (1 << 255) | 0x123
            log = Path(td) / "run.log"
            log.write_text("".join(f"SLICE_REC rec={b} cyc=2727 "
                                   f"{'FAIL' if observed >> b & 1 else 'COMMIT_OK'}\n"
                                   for b in range(256)))
            result = collect(output, log)
            self.assertEqual(int(result["observed"], 16), observed)
            self.assertFalse(result["matches_original"])
            self.assertFalse(result["qualifies_full_token"])
            log.write_text(log.read_text().splitlines()[0] + "\n")
            with self.assertRaisesRegex(ValueError, "incomplete word"):
                collect(output, log)
            with self.assertRaisesRegex(ValueError, "capacity"):
                make(source, Path(td) / "too_small", 2727, 32803, 257)


if __name__ == "__main__":
    unittest.main()
