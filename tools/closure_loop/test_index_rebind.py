import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import closure_loop as cl
import rebind_index_budget as rb


class IndexRebindTests(unittest.TestCase):
    def job(self):
        ins=dict(ss=1132,ff=766,target_ss=1154,target_ff=779,grade='measured')
        return dict(name=rb.ALLOWED[0],status='NEEDS_BUDGET',host='host',run='/run',stage_idx=0,
                    spec=dict(budget=dict(master='hfd_index_q_b1',preserve_full_sheet=True,sheet_sha256=''),
                              stages={'calibrate': {'cmd':'true','base':'/base'}}),
                    budget=dict(sheets_ref='old',insertion=ins),
                    calibration=dict(env=dict(CK_SS_MEAN=1130,CK_SS_MIN=1100,CK_SS_MAX=1147,
                                               CK_FF_MEAN=764,CK_FF_MIN=733,CK_FF_MAX=778)))

    def test_full_sheet_is_not_rewritten_from_measured_mean(self):
        j=self.job(); sheet=json.dumps({'clock':{'internal_insertion':j['budget']['insertion']}})
        j['spec']['budget']['sheet_sha256']=hashlib.sha256(sheet.encode()).hexdigest()
        files={'budget_sheet.json':sheet,'budget_route.sdc':'full contract','_ref':'approved'}
        with patch.object(cl,'budget_files',return_value=files) as generate, patch.object(cl,'ssh'):
            self.assertIsNone(cl.budget_check(j))
        self.assertIsNone(generate.call_args.kwargs['insertion_override'])
        self.assertEqual(j['budget']['insertion_used']['ss'],1132)

    def test_maximum_excess_blocks_even_when_mean_passes(self):
        for corner in ('SS','FF'):
            j=self.job();j['calibration']['env'][f'CK_{corner}_MAX']=2000
            with patch.object(cl,'budget_files') as generate, patch.object(cl,'ssh') as remote:
                self.assertIn('boundary maximum',cl.budget_check(j))
            generate.assert_not_called();remote.assert_not_called()

    def test_digest_mismatch_prevents_remote_mutation(self):
        j=self.job()
        with patch.object(cl,'budget_files',return_value={'budget_sheet.json':'changed'}),patch.object(cl,'ssh') as remote:
            with self.assertRaises(ValueError):cl.budget_check(j)
        remote.assert_not_called()

    def test_scope_and_snapshot_guards(self):
        j=self.job();h=copy.deepcopy(j);b=dict(bound_sheets_ref='old',boundary_max_above_approved_target_ps=0,
                                             mean_gate_pass=True,corrected_binding=dict(insertion=j['budget']['insertion']))
        sheet={'clock':{'internal_insertion':j['budget']['insertion']}}
        rb.validate(j,h,b,sheet)
        for key,value in [('name','hbm_idxq_b0_e8b5132fb_r18b'),('status','RUNNING'),('host','other'),
                          ('audited_budget_rebind',{'already':True})]:
            with self.assertRaises(ValueError):rb.validate(dict(j,**{key:value}),h,b,sheet)

    def test_remote_archive_preserves_failed_sdcs_and_is_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);c=root/'cl';c.mkdir();(c/'calibrate.a1.rc').write_text('0')
            (c/'budget_route.sdc').write_text('failed SDC');(c/'budget_sheet.json').write_text('failed sheet')
            j=dict(run=td,stage_tag='calibrate.a1')
            p=dict(job=j,binding={},audit_commit='audit',files={'budget_route.sdc':'approved SDC',
                   'budget_sheet.json':'approved complete sheet','_ref':'approved'})
            command=['python3','-c',rb.REMOTE,json.dumps(p)]
            r=subprocess.run(command,capture_output=True,text=True,check=True)
            receipt=json.loads(r.stdout);d=Path(receipt['directory'])
            self.assertEqual((d/'historical/cl/budget_route.sdc').read_text(),'failed SDC')
            self.assertEqual((c/'budget_route.sdc').read_text(),'approved SDC')
            self.assertEqual(json.loads((d/'historical_state.json').read_text()),j)
            r=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0)
            self.assertEqual((d/'historical/cl/budget_route.sdc').read_text(),'failed SDC')


if __name__=='__main__':unittest.main()
