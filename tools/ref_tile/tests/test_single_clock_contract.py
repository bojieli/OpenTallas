"""Actual GEN2e source proof and real OpenSTA period/virtual-clock regression.

Run on fleet with saved_bw_safe4_spec.json's exact source bytes in ROOT.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import single_clock_contract as S
import clock_entry_constraints as C
import ref_tile as R
ROOT = Path(__file__).resolve().parents[3]
SAVED = ROOT/'results/rtl/single_clock_contract_1019/saved_bw_safe4_spec.json'

def spec():
    return json.loads(SAVED.read_text())

class Schema(unittest.TestCase):
    def test_actual_saved_bw64_source_positive(self):
        s=spec()
        self.assertEqual(len(s['single_clock_contract']['instances']),64)
        self.assertEqual(S.validate(s),1024)
        self.assertEqual(C.signoff_period(s),1024)
        self.assertEqual(R.io_budget_env(s),dict(OT_IO_IN_BUDGET_PS=204.8,OT_IO_OUT_BUDGET_PS=204.8))
        for text in (R.gen_sdc(s,1024),R.gen_signoff(s,'*','none_*'),R.gen_signoff_ffrepair(s,'*','none_*') or ''):
            if not text: continue
            self.assertIn('create_clock -name core_clk -period 1024',text)
            self.assertIn('set_clock_uncertainty -setup 60',text)
            self.assertIn('set_clock_uncertainty -hold 25',text)
            self.assertIn('ot_single_clock_check',text)
            self.assertNotIn('-period 833.333',text)
        self.assertEqual(set(S.evidence_paths(s)),set(R.referenced_paths(s,'physical/ref_tile/test')) & set(S.evidence_paths(s)))

    def test_wrong_period_root_source_params_count_hash_fail_closed(self):
        mutations=[lambda s:s['route'].update(signoff_period_ps=833.333),
          lambda s:s['route'].update(period_ps=833.333),
          lambda s:s['single_clock_contract']['source'].update(pin='pll_stream'),
          lambda s:s['single_clock_contract']['source'].update(instance='fake'),
          lambda s:s['single_clock_contract']['manifest'].update(sha256='0'*64),
          lambda s:s['single_clock_contract']['native_contract'].update(sha256='0'*64),
          lambda s:s['single_clock_contract']['instances'].pop('ctl_NW_p00'),
          lambda s:s['single_clock_contract']['instances'].update(fake='clk'),
          lambda s:s['single_clock_contract']['instances'].update(ctl_NW_p00='rst_n'),
          lambda s:s['single_clock_contract'].update(params={'BAD':1}),
          lambda s:s['single_clock_contract']['sources_sha256'].update({s['sources'][0]:'0'*64}),
          lambda s:s.update(clock='multiple_cts_roots'),
          lambda s:s.update(clock_ports=['clk','extra']),
          lambda s:s.update(sdc_extra=['fake.sdc']),
          lambda s:s['single_clock_contract'].update(period_ps=True),
          lambda s:s['single_clock_contract'].update(unrecognized=True)]
        for i,mut in enumerate(mutations):
            with self.subTest(mutant=i):
                s=spec();mut(s)
                with self.assertRaises(ValueError):C.signoff_period(s)

    def test_default833_abi_and_unguarded_override_refusal(self):
        self.assertEqual(C.signoff_period({'clock':'spine'}),833.333)
        with self.assertRaises(ValueError):C.signoff_period(dict(clock='spine',route=dict(signoff_period_ps=1024)))

class OpenSTA(unittest.TestCase):
    def test_actual_and_virtual_period_replays(self):
        s=spec();guard=S.guard(s)
        for case in ('positive','wrong_real_period','wrong_virtual_period','extra_real_root','unknown_virtual','ff_mm_positive','ff_mm_wrong_virtual'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
                w=Path(d)
                (w/'t.v').write_text('module top(input clk,d,output q); DFFHQNx1_ASAP7_75t_R ff(.CLK(clk),.D(d),.QN(q)); endmodule\n')
                cmds='create_clock -name core_clk -period 1024 [get_ports clk]\ncreate_clock -name ot_lb_v_core_clk -period 1024\nset_clock_uncertainty -setup 60 [all_clocks]\nset_clock_uncertainty -hold 25 [all_clocks]\n'+guard
                if case=='wrong_real_period':cmds+='create_clock -name core_clk -period 833.333 [get_ports clk]\n'
                if case in ('wrong_virtual_period','ff_mm_wrong_virtual'):cmds+='create_clock -name ot_lb_v_core_clk -period 833.333\n'
                if case=='extra_real_root':cmds+='create_clock -name extra -period 1024 [get_ports d]\n'
                if case=='unknown_virtual':cmds+='create_clock -name unknown -period 1024\n'
                if case.startswith('ff_mm'):
                    cmds+='source /src/tools/orfs_hold_mm.tcl\not_mm_sync_link_periods\n'
                cmds+='ot_single_clock_check\nputs "REPLAY_PASS '+case+'"\n'
                corner='FF' if case.startswith('ff_mm') else 'TT'
                flow='set P /OpenROAD-flow-scripts/flow/platforms/asap7\nread_lef $P/lef/asap7_tech_1x_201209.lef\nread_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef\nforeach l [glob $P/lib/NLDM/*RVT_'+corner+'*] {read_liberty $l}\nread_verilog /w/t.v\nlink_design top\n'+cmds
                (w/'run.tcl').write_text(flow)
                p=subprocess.run(['docker','run','--rm','-v',f'{w}:/w','-v',f'{ROOT}:/src:ro','openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/w/run.tcl'],capture_output=True,text=True)
                out=p.stdout+p.stderr
                print('STA_CASE',case,'RC',p.returncode,'\n',out)
                positive=case in ('positive','ff_mm_positive')
                if positive:
                    self.assertEqual(p.returncode,0,out);self.assertIn('REPLAY_PASS '+case,out)
                else:
                    self.assertNotEqual(p.returncode,0,out);self.assertIn('OT_SINGLE_CLOCK',out)

if __name__=='__main__':unittest.main(verbosity=2)
