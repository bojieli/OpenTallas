"""Opt-in two-net/per-core window generation; no physical solve."""
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import infra_pg as G
import die_trial as D
import test_pg_window_phase as F


class WindowAPI(unittest.TestCase):
    def test_canonical_two_net_load_conservation_and_executed_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            m, _ = F.Phase().window(tmp, [], [('VDD',150.,150.)],
                                     nets=('VDD','VSS'), loads=[([100,100,150,150],4.)])
            self.assertEqual(m['nets'], ['VDD','VSS'])
            self.assertEqual(m['power_map'], 'loads')
            self.assertIsNone(m['est_worst_mv'])
            self.assertEqual(m['est_regions_mv'], {})
            self.assertEqual(m['est_detail']['status'], 'NOT RUN')
            self.assertIn('explicit loads', m['scope'])
            self.assertAlmostEqual(m['power_w'], .01)
            self.assertEqual(m['bump_pad_um'],70.)
            text=(Path(tmp)/'kit/psm/psm.tcl').read_text()
            powers=re.findall(r'set_pdnsim_inst_power -inst \S+ -power (\S+)',text)
            self.assertAlmostEqual(sum(map(float,powers)),.01,places=7)
            tail=text[text.index('foreach n {VDD VSS}'):]
            for failure in ('none','check','solve'):
                with self.subTest(failure=failure):
                    header='set t0 [clock seconds]\n'
                    header+='proc check_power_grid {args} {'+('error bad_check' if failure=='check' else 'return')+'}\n'
                    header+='proc analyze_power_grid {args} {'+('if {[lindex $args 1] eq "VSS"} {error bad_solve}' if failure=='solve' else 'return')+'}\n'
                    run=Path(tmp)/f'{failure}.tcl';run.write_text(header+tail)
                    r=subprocess.run(['tclsh',str(run)],capture_output=True,text=True)
                    self.assertEqual(r.returncode==0,failure=='none',r.stderr)
                    self.assertEqual('OT_DONE' in r.stdout,failure=='none')
                    if failure=='none':
                        self.assertIn('OT_PSM_OK VDD',r.stdout);self.assertIn('OT_PSM_OK VSS',r.stdout)
                    if failure=='solve':
                        self.assertIn('OT_PSM_OK VDD',r.stdout);self.assertIn('OT_PSM_FAIL VSS',r.stdout)

    def test_default_is_explicit_vdd_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,_=F.Phase().window(tmp,[],[('VDD',150.,150.)])
            self.assertEqual(m['nets'],['VDD'])
            self.assertEqual(m['power_map'],'region model')
            self.assertIn('diagnostic',m['supply_metric'])
            text=(Path(tmp)/'kit/psm/psm.tcl').read_text()
            self.assertIn('foreach n {VDD} { if {[catch {analyze_power_grid',text)

    def test_bad_net_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'unique VDD/VSS'):
                F.Phase().window(tmp,[],[],nets=('VDD','bad'))

    def test_legacy_reporter_never_claims_combined_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'irwin.json').write_text(json.dumps(dict(nets=['VDD','VSS'],ir_budget_mv=35)))
            with patch.object(D,'psm_report',return_value=dict(status='OK',worst_ir_drop_mv=1.)):
                result=G.report(p)
            self.assertEqual(result['ir_verdict'],'NOT RUN')
            self.assertIn('co-located',result['supply_metric'])


if __name__=='__main__':
    unittest.main()
