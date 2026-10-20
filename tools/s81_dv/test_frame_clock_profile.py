"""Actual-source refusal and narrowly synthetic clock-profile coupons."""
import copy
import json
from pathlib import Path
import tempfile
import shutil
import hashlib
import unittest
import frame_clock_profile as F

FORWARD='''pin("ck_o") { direction : output; timing() { related_pin : "ck";
 timing_type : combinational; timing_sense : positive_unate;
 cell_rise(t) { values("11,12"); } cell_fall(t) { values("13,14"); }
 rise_transition(t) { values("2,3"); } fall_transition(t) { values("3,4"); }
 }}'''

def coupon():
    return 'pin("ck") { direction : input; clock : true; }'+''.join(
        f'pin("i[{k}]") {{ direction : input; timing() {{ related_pin : "ck"; timing_type : setup_rising; }} '
        'timing() { related_pin : "ck"; timing_type : hold_rising; } }' for k in range(276))+FORWARD

class Profile(unittest.TestCase):
    def test_actual_main_view_is_refused_at_both_corners(self):
        p=F.profile(F.ROOT)
        self.assertEqual(p['child_clock_pin_coverage'],8)
        self.assertEqual(p['status'],'REFUSED')
        self.assertEqual(len(p['errors']),2)
        self.assertTrue(all('ck->ck_o' in e for e in p['errors']))
        with self.assertRaises(ValueError): F.sdc(p,833.333)

    def test_true_clock_arc_and_writer_checks_are_required(self):
        text=coupon()
        self.assertFalse(F.hard_view(text,['ck'],['i'],('ck','ck_o'))['errors'])
        for bad in (text.replace('positive_unate','negative_unate'),
                    text.replace('combinational','rising_edge'),
                    text.replace('related_pin : "ck";\n timing_type : combinational', 'related_pin : "ck_o";\n timing_type : combinational'),
                    text.replace('hold_rising','hold_falling'),
                    text.replace('pin("i[275]")','pin("i[276]")'),
                    text.replace('cell_fall(t)','absent(t)'),
                    text.replace('values("11,12")','values("nan,12")'),
                    text.replace('values("11,12")','values("-1,12")')):
            with self.subTest(bad=bad[-120:]):
                self.assertTrue(F.hard_view(bad,['ck'],['i'],('ck','ck_o'))['errors'])

    def test_emitter_declares_each_real_root_without_data_waiver(self):
        p=F.profile(F.ROOT)
        # Synthetic emitter-only coupon: no production-view rewrite is made.
        p['errors']=[]
        text=F.sdc(p,833.333)
        self.assertEqual(text.count('create_clock -name'),4)
        for k in range(4): self.assertIn(f'[get_ports {{xk[{k}]}}]',text)
        for forbidden in ('set_false_path','set_multicycle_path','create_generated_clock','set_max_delay'):
            self.assertNotIn(forbidden,text)
        for bad in (0,-1,float('nan'),None,True):
            with self.assertRaises(ValueError): F.sdc(p,bad)

    def test_regenerated_manifest_cannot_hide_wrong_lane_clock_or_data(self):
        source=F.ROOT/'rtl/dsrom_sys/s81_dv/frame_l4/col_h9_l4.sv'
        text=source.read_text()
        for old,new in (('.ck(xk[0])','.ck(xk[1])'),('.xk(xk)','.xk(lk)'),
                        ('.ck_o(xok[0])','.ck_o(xok[1])')):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                (root/'physical').symlink_to(F.ROOT/'physical',target_is_directory=True)
                for rel in ('rtl/dsrom_sys/s81_dv/frame_l4/col_h9_l4.sv',
                            'rtl/dsrom_sys/s81_dv/frame_l4/frame_l4.json',
                            'rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv',
                            'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv'):
                    target=root/rel; target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(F.ROOT/rel,target)
                mutated=text.replace(old,new,1)
                self.assertNotEqual(text,mutated)
                (root/'rtl/dsrom_sys/s81_dv/frame_l4/col_h9_l4.sv').write_text(mutated)
                manifest=root/'rtl/dsrom_sys/s81_dv/frame_l4/frame_l4.json'
                record=json.loads(manifest.read_text())
                record['emitted']['col_h9_l4.sv']=hashlib.sha256(mutated.encode()).hexdigest()
                manifest.write_text(json.dumps(record))
                p=F.profile(root)
                self.assertTrue(p['source_lineage_errors'])
                self.assertEqual(p['child_clock_pin_coverage'],0)
                with self.assertRaises(ValueError): F.sdc(p,833.333)

    def test_second_actual_frame_has_same_eight_clock_pin_contract(self):
        p=F.profile(F.ROOT,'col_h10_l4')
        self.assertEqual(len(p['errors']),2)
        self.assertEqual([x['root'] for x in p['external_roots']],[f'xk[{k}]' for k in range(4)])

if __name__=='__main__': unittest.main()
