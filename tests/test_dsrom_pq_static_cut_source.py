"""Source-interface checks only; deliberately not an RTL numerical verdict."""
import hashlib
import json
import re
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

class SourceContract(unittest.TestCase):
    def test_manifest_pins(self):
        record=json.loads((ROOT/'results/rtl/dsrom_field_address_lookahead_20261005/pq_static_cut_join.json').read_text())
        for path,sha in record['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),sha,path)
    def test_live_tag_and_cut(self):
        s=(ROOT/'rtl/v41die/ot_v41_fieldtop_pq_static_cut_w17w10.sv').read_text()
        self.assertIn('`ifdef RT_CUT',s)
        self.assertIn('.f_go_tag(c_tag)',s)
        self.assertIn('assign fb_go_tag = c_tag;',s)
        self.assertIn('fr_row',s)
    def test_no_old_header_tag_fallback(self):
        s=(ROOT/'tools/runtime/dsrom/s81_minimum_qe_pq_static.cpp').read_text()
        self.assertIn('#ifndef DSROM_S81_PQ_TAGGED_MODEL',s)
        self.assertIn('model.go_tag=actual_go_tag;',s)
        self.assertIn('pair->drive(drive,cut.fb_go_tag)',s)
        self.assertIn('issued_go_tag=cut.fb_go_tag',s)
        check=s.index('"PQ foreign native root tag"')
        normalize=s.index('s.row &= 0x3fff',check)
        self.assertLess(check,normalize)
    def test_decoder_boundaries(self):
        s=(ROOT/'rtl/v41rom/ot_v41_elem_pq_tags_rowfix.sv').read_text()
        self.assertIn("RW'({27'd0,cfg_a}-(NSEG+1))",re.sub(r"\s+","",s))
        # cfg_a is five bits; the source legal second-row range fits NSEG<=10.
        for n in range(1,11):
            for seg in range(n):
                addr=2*n+1+seg
                self.assertLessEqual(addr,31)
                self.assertEqual(addr-(n+1),n+seg)
        self.assertEqual(24-(8+1),15)
        self.assertNotEqual(8+(24&7)-1,15)
    def test_same_state_decoder_only(self):
        old=(ROOT/'rtl/v41rom/ot_v41_elem_pq_tags.sv').read_text()
        new=(ROOT/'rtl/v41rom/ot_v41_elem_pq_tags_rowfix.sv').read_text()
        new=new.replace('ot_v41_elem_pq_tags_rowfix','ot_v41_elem_pq_tags')
        new=new.replace("RW'({27'd0, cfg_a} - (NSEG + 1))","RW'(NSEG+cfg_a[SW-1:0]-1)")
        # Added explanatory comments do not change hardware.
        strip=lambda x: re.sub(r'\s+','',re.sub(r'//[^\n]*','',x))
        self.assertEqual(strip(new),strip(old))

if __name__=='__main__': unittest.main()
