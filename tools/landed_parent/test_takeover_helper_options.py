"""Pure source-generation checks for individually opted-in helper options."""
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import lp
sys.path.insert(0, str(lp.ROOT / 'tools/ref_tile'))
import clock_entry_constraints as ce


class HelperOptions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=lp.ROOT/'tools/landed_parent')
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        (self.d/'child.sv').write_text(lp.SELFTEST_CHILD)
        (self.d/'top.sv').write_text(lp.SELFTEST_TOP)
        rel = self.d.relative_to(lp.ROOT)
        self.spec = dict(top='lpt_top', sources=[str(rel/'top.sv')], child_sources=[str(rel/'child.sv')],
                         out_dir=str(rel), clock_ports=['clk'], clock_pins=['clk'],
                         reset_port='rst_n', reset_pins=['rst_n'],
                         regions=[dict(name='ra', insts=['u0','u3'], centre=[0,0]),
                                  dict(name='rb', insts=['u1','u2'], centre=[900,0])])

    def generated(self, spec, cls=lp.Parent):
        model = cls(spec)
        plan = model.plan()
        rtl, rt = model.emit(plan, 'lpt_top_lp')
        return model, plan, rtl, rt, model.record(plan, 'lpt_top_lp', rt)

    def test_default_bytes_match_main(self):
        path = self.d/'baseline.py'
        path.write_text(subprocess.check_output(['git','-C',str(lp.ROOT),'show',
                        '799eebe53:tools/landed_parent/lp.py'],text=True))
        loader = importlib.util.spec_from_file_location('lp_main_baseline', path)
        before = importlib.util.module_from_spec(loader);loader.loader.exec_module(before)
        before.ROOT = lp.ROOT
        for options in ({}, {'landing_chunk_bits':24}):
            spec = dict(self.spec, **options)
            old, op, ortl, ort, orecord = self.generated(spec, before.Parent)
            new, np, nrtl, nrt, nrecord = self.generated(spec)
            self.assertEqual((nrtl,new.sdc(np,'lpt_top_lp'),new.tb(np,'lpt_top_lp',nrt),nrecord),
                             (ortl,old.sdc(op,'lpt_top_lp'),old.tb(op,'lpt_top_lp',ort),orecord))

    def test_regional_ports_have_no_shared_reset_root(self):
        spec = dict(self.spec,regional_reset_ports={'stages':2,'why':'source test'})
        model, plan, rtl, rt, rec = self.generated(spec)
        self.assertNotIn('u_lpr_root',rtl)
        for region in ('ra','rb'):
            self.assertIn(f'input wire rst_n_{region}',rtl)
            self.assertIn(f'.d(rst_n_{region})',rtl)
        self.assertEqual(rec['reset']['root_region'],None)
        self.assertEqual(rec['reset']['regional_ports'],{'ra':'rst_n_ra','rb':'rst_n_rb'})
        actual = sum(map(int,re.findall(r'ot_pl_pad #\(\.W\(1\), \.N\((\d+)\)\) u_lpr\w* ',rtl)))
        self.assertEqual(rec['flops']['reset'],actual)
        self.assertTrue(lp.audit(spec,rtl)['ok'])
        self.assertNotIn('reset-hop pairs',str(rec['die_obligations']))

    def test_reset_lead_emits_real_early_node_and_late_mutant(self):
        spec = dict(self.spec,landing_reset_lead=True)
        model,plan,rtl,rt,rec = self.generated(spec)
        self.assertIn('(MUT == 5) ? lpr_ra : lpr_ra_l',rtl)
        self.assertIn('.rsi(lpr_ra_lw)',rtl)
        self.assertTrue(rec['landing_implementation']['reset_lead'])
        self.assertTrue(lp.audit(spec,rtl)['ok'])
        self.assertNotIn('MUT == 5', model.emit(plan,'lpt_top_lp',mut=False)[0])

    def test_no_mcp_plain_record_propagates_through_final_helper(self):
        model,plan,rtl,rt,rec = self.generated(dict(self.spec,landing_mcp=False))
        self.assertNotIn('set_multicycle_path',model.sdc(plan,'lpt_top_lp'))
        self.assertTrue(rec['landing_implementation']['no_data_multicycle'])
        self.assertNotIn('compensated_phase_T',rec['landing_implementation'])
        (self.d/'record.json').write_text(json.dumps(rec))
        actual = ce.landed_sdc({'kind':'cluster','clock':'multiple_cts_roots','landed_record':str(self.d/'record.json'),
                                'children':[{'view':'unused'}], 'clock_data_paths':'related_same_frequency',
                                'top':rec['top'],'clock_ports':['ck_ra','ck_rb'],'clock_port':'ck_ra'},lp.ROOT)
        self.assertNotIn('set_multicycle_path',actual)
        self.assertIn('no_data_multicycle',actual)

    def test_unlanded_input_port_is_rejected(self):
        spec = dict(self.spec,port_regions={'x':'ra'})
        model = lp.Parent(spec)
        rtl = model.emit(model.plan(),'lpt_top_lp')[0]
        rtl = rtl.replace('.b(x__l_rb)', '.b(x)')
        self.assertFalse(lp.audit(spec,rtl)['ok'])
        self.assertTrue(any('port:x' in f for f in lp.audit(spec,rtl)['fails']))

    @unittest.skipUnless(shutil.which('tclsh'), 'tclsh required')
    def test_sdff_folding_is_explicit_optin_and_before_prep(self):
        source = lp.ROOT/'physical/common_flow/ot_rst_copies.tcl'
        old = self.d/'old_reset.tcl'
        old.write_text(subprocess.check_output(['git','-C',str(lp.ROOT),'show',
                       '799eebe53:physical/common_flow/ot_rst_copies.tcl'],text=True))
        def calls(path, enabled=None):
            script = """set ::env(OT_RST_COPIES_MAX) 32
set ::env(RESULTS_DIR) .
unset -nocomplain ::env(SYNTH_HIERARCHICAL) ::env(SYNTH_CHECKPOINT) ::env(OT_RST_COPIES_SDFF)
set ::commands {}
proc yosys {args} {lappend ::commands $args}
rename exec real_exec
proc exec {args} {return MOCK_PYTHON}
"""
            if enabled is not None:
                script += 'set ::env(OT_RST_COPIES_SDFF) ' + str(enabled) + '\n'
            script += 'source {' + str(path) + '}\nforeach c $::commands {puts "CALL:$c"}\n'
            out = subprocess.check_output(['tclsh'],input=script,text=True)
            return [x.removeprefix('CALL:') for x in out.splitlines() if x.startswith('CALL:')]
        baseline = calls(old)
        self.assertEqual(calls(source),baseline)
        self.assertEqual(calls(source,0),baseline)
        opted = calls(source,1)
        self.assertEqual(opted[:2],baseline[:2])
        self.assertEqual(opted[2:6],['opt_expr','opt_clean','opt_dff -nodffe','opt_clean'])
        self.assertEqual(opted[6:],baseline[2:])

    def test_unsupported_joint_reset_options_fail_closed(self):
        for other in ({'regional_reset_ports':{'stages':2}}, {'landing_reset_forest':True,'landing_chunk_bits':24}):
            with self.assertRaisesRegex(SystemExit,'not implemented'):
                lp.Parent(dict(self.spec,landing_reset_lead=True,**other))


if __name__ == '__main__':
    unittest.main()
