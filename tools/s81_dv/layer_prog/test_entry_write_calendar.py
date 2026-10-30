"""Real3920-row entry payload coverage and strict native page/transport guards."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from layer_prog.entry_write_calendar import compile_pages,encode_unsealed
from layer_prog.bound_boot import decode_check
from layer_prog.bound_control import norm_spacing

ROOT=Path(__file__).resolve().parents[3]
class EntryCalendarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entry=json.loads((ROOT/'results/token_pass/s81_entry_inputs_1021/entry_inputs_L0.json').read_text())
    def test_real_entry_each_payload_once_and_native_boot_decodes(self):
        pages=compile_pages(self.entry,first_issue=20,issue_stride=2)
        self.assertEqual(len(pages),32)
        source=[];words=0
        for p in pages:
            self.assertLessEqual(len(p['rows']),126)
            self.assertTrue(all(r['done']==r['issue']+5 and r['eng']<14 for r in p['rows']))
            w=encode_unsealed(p);decode_check(p,{'native_commands.unsealed.host_boot.memh':w})
            source.extend((t['source_write_index'],t['payload186'])for t in p['templates']);words+=len(w)
            self.assertFalse(p['native_job_sealed']);self.assertFalse(p['host_boot_complete'])
        self.assertEqual(source,[(i,w['ctl_payload186'])for i,w in enumerate(self.entry['writes'])])
        self.assertEqual(words,4*3920+32)
    def test_real_host_payload_mutant_is_caught(self):
        p=compile_pages(self.entry,first_issue=20,issue_stride=2)[0];words=encode_unsealed(p)
        words[-1]^=1<<17
        with self.assertRaisesRegex(ValueError,'template differs'):
            decode_check(p,{'native_commands.unsealed.host_boot.memh':words})
    def test_changed_row_or_slice_identity_is_refused(self):
        for key,value in [('ctl_payload186','1'),('engine','VN'),('row',1024)]:
            e=copy.deepcopy(self.entry);e['writes'][0][key]=value
            with self.assertRaises(ValueError):compile_pages(e,first_issue=20,issue_stride=2)
    def test_duplicate_row_is_refused(self):
        e=copy.deepcopy(self.entry);e['writes'].append(e['writes'][0]);e['row_count']+=1
        with self.assertRaisesRegex(ValueError,'duplicate'):compile_pages(e,first_issue=20,issue_stride=2)
    def test_unsafe_capacity_cadence_and_date_width_are_refused(self):
        for kwargs in [dict(page_commands=127),dict(issue_stride=1),dict(first_issue=(1<<24)-1)]:
            with self.assertRaises(ValueError):compile_pages(self.entry,**dict(dict(first_issue=20,issue_stride=2),**kwargs))
    def test_target5_transport_does_not_require_a_norm_cohort(self):
        self.assertEqual(norm_spacing([dict(kind='TARGET5',slice='u_s_0S',payload186=self.entry['writes'][0]['ctl_payload186'])],object()),{})
    def test_target5_label_cannot_hide_a_norm_or_missing_payload(self):
        for c in [dict(kind='TARGET5',slice='u_s_0S'),
                  dict(kind='TARGET5',slice='u_s_0S',payload186='0'),
                  dict(kind='other',slice='u_s_0S',payload186=self.entry['writes'][0]['ctl_payload186'])]:
            self.assertEqual(norm_spacing([c],object())['u_s_0S']['status'],'BLOCKED')
    def test_partial_norm_or_go_only_still_blocked(self):
        for rows in [[dict(kind='NORMR',slice='u_s_0S',leaf=i)for i in range(4)],
                     [dict(kind='XFIN_GO',slice='u_s_0S')]]:
            self.assertEqual(norm_spacing(rows,object())['u_s_0S']['status'],'BLOCKED')
    def test_existing_norm_alignment_remains_strict(self):
        rows=[dict(kind='NORMR',slice='u_s_0S',leaf=i,xr_command_pin_edge_from_age0_command=i)for i in range(5)]
        with patch('layer_prog.bound_control.xr_deskew',return_value=[4,3,2,1,0]):
            self.assertEqual(norm_spacing(rows,object())['u_s_0S']['status'],'PASS_CONTROL_SPACING')
            rows[2]['xr_command_pin_edge_from_age0_command']+=1
            self.assertEqual(norm_spacing(rows,object())['u_s_0S']['status'],'FAIL_CONTROL_SPACING')
if __name__=='__main__':unittest.main()
