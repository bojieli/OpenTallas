import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import hbrom_gate as H

class VerdictTest(unittest.TestCase):
    def test_fail_closed_exactness_and_coverage(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);gold=p/'gold.hex';gold.write_text('3f800000\n40000000\n')
            manifest=p/'manifest.json';manifest.write_text('{}')
            case=dict(operation=0,expected_fp32=str(gold),expected_sha256=H.digest(gold),
                      manifest=str(manifest),manifest_sha256=H.digest(manifest),rows=2,issued_records=16,
                      format='fp4',logical_K=2304)
            prep=p/'preparation.json';prep.write_text(json.dumps(dict(cases=[case])))
            good='R 0 0 3f800000\nR 0 1 40000000\nM 0 requests 16 responses 16 consumed 16 results 2 fault 0 feed_fault 0 released 1 macro_spacing_failures 0 capture_count 64\n'
            out=p/'out.txt';out.write_text(good)
            self.assertEqual(H.verify(prep,out)['status'],'PASS')
            mutants=[good.replace('40000000','40000001'),good.replace('R 0 1 40000000\n',''),
                     good+'R 0 1 40000000\n',good+'R 0 2 00000000\n',
                     good.replace('capture_count 64','capture_count 60'),
                     good.replace('macro_spacing_failures 0','macro_spacing_failures 1'),
                     good.replace('released 1','released 0')]
            for text in mutants:
                out.write_text(text);self.assertEqual(H.verify(prep,out)['status'],'FAIL')
            gold.write_text('0\n0\n')
            with self.assertRaises(ValueError):H.verify(prep,out)
if __name__=='__main__':unittest.main()
