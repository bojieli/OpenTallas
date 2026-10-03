import importlib.util
import itertools
import json
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('p',ROOT/'tools/prepare_dsrom_ckv_publication.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

class PublicationTests(unittest.TestCase):
    def test_all_admission_states(self):
        for pending,turn,wv,ww,cv,cw in itertools.product([False,True],repeat=6):
            chosen=p.select(pending,turn,wv,ww,cv,cw)
            ew=wv and not(pending and ww);ec=cv and not(pending and cw)
            allowed=[]
            if ew:allowed.append('w')
            if ec:allowed.append('c')
            self.assertEqual(chosen is None,not allowed)
            if chosen:self.assertIn(chosen,allowed)
            if ew and ec:self.assertEqual(chosen,'c' if turn else 'w')
    def test_nine_returned_completions_and_no_request_visibility(self):
        for stack in range(4):
            writer=p.Writer()
            for sector in range(9):
                writer.accept('c',sector);self.assertEqual(len(writer.visible),sector)
                with self.assertRaises(ValueError):writer.accept('w',sector)
                self.assertEqual(writer.complete(),'c');self.assertEqual(writer.visible[-1],('c',sector))
            self.assertEqual(len(writer.visible),9)
            with self.assertRaises(ValueError):writer.complete()
    def test_missing_completion_retains_owner(self):
        writer=p.Writer();writer.accept('c',8)
        self.assertEqual(writer.pending,('c',8));self.assertEqual(writer.visible,[])
        with self.assertRaises(ValueError):writer.accept('c',0)
        # An unrelated read grants W while the recorded writer remains C.
        self.assertEqual(p.select(True,False,True,False,False,False),'w')
        self.assertEqual(writer.complete(),'c')
    def test_no_same_edge_freed_slot_credit(self):
        self.assertIsNone(p.select(True,False,True,True,True,True))
        self.assertEqual(p.select(False,False,True,True,True,True),'w')
        self.assertEqual(p.select(False,True,True,True,True,True),'c')
    def test_source_defaultoff_and_no_response_demux_changes(self):
        copies=p.source();inner=copies['ot_chip_v41x_kv_reqmux_ckvlease_r1'];outer=copies['ot_chip_v41x_kv_rope_reqmux_ckvlease_r1']
        for text in copies.values():self.assertIn('parameter integer CKV_RX_LEASE = 0',text)
        old=(p.BASE/'inputs/ot_chip_v41x_kv_reqmux.sv').read_text()
        for line in old.splitlines():
            if any('assign '+name in line for name in ['w_sv','c_sv','w_stag','c_stag','w_sbeat','c_sbeat','w_sdata','c_sdata','s_rdy']):self.assertIn(line,inner)
        self.assertIn(': w_v[s]',inner);self.assertIn(': m_wr_done[s]',inner)
        self.assertIn('(!CKV_RX_LEASE && c_we[s])',outer)
        self.assertIn('.TAGW(TAGW-1)',outer);self.assertIn('.CKV_RX_LEASE(CKV_RX_LEASE)',outer)
        self.assertIn('m_wr_done[s] && write_pending && write_owner_c',inner)
        self.assertIn('m_wr_done[s] && write_pending && !write_owner_c',inner)
        self.assertIn('reg pending_r, owner_c_r, turn_r;',inner)
        self.assertIn('.writer_idle(writer_idle)',outer)
        self.assertIn('(|writer_fault)',outer)
    def test_mapped_cost_and_geometry_not_fullgate_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'a';b=Path(tmp)/'b';p.prepare(a);p.prepare(b)
            self.assertEqual({x.name:x.read_bytes() for x in a.iterdir()},{x.name:x.read_bytes() for x in b.iterdir()})
            model=json.loads((a/'source_plan.json').read_text())
            self.assertEqual(model['ledger']['new_mux_state_bits_per_die'],12)
            self.assertTrue(model['ledger']['already_in_eae_price']);self.assertEqual(model['instance']['own_row_sectors'],9)
            self.assertFalse(model['readiness']['connected_full512_gate']);self.assertFalse(model['readiness']['HDL_compiled'])
            with self.assertRaises(ValueError):p.prepare(a)
    def test_original_ckv_write_failure_witness_retained(self):
        oldouter=(p.BASE/'inputs/ot_chip_v41x_kv_rope_reqmux.sv').read_text();oldinner=(p.BASE/'inputs/ot_chip_v41x_kv_reqmux.sv').read_text()
        self.assertIn('&& !c_we[s]',oldouter);self.assertIn("assign c_wr_done[s] = 1'b0",oldinner)

if __name__=='__main__':unittest.main(verbosity=2)
