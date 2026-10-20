"""Source contract tests; no physical phase or gate qualification is implied."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import lp

class Entries(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=lp.ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.rel = str(self.root.relative_to(lp.ROOT))
        (self.root/'child.sv').write_text(lp.SELFTEST_CHILD)
        (self.root/'top.sv').write_text(lp.SELFTEST_TOP)
        (self.root/'insertion.json').write_text('{"source_contract_fixture":true}')
        self.spec = dict(top='lpt_top',_spec_path=self.rel+'/spec.json',out_dir=self.rel,sources=[self.rel+'/top.sv'],
            child_sources=[self.rel+'/child.sv'],clock_ports=['clk'],clock_pins=['clk'],
            reset_port='rst_n',reset_pins=['rst_n'],landing_mcp=False,
            regions=[dict(name='ra',insts=['u0','u3'],centre=[0,0]),dict(name='rb',insts=['u1','u2'],centre=[900,0])])
        self.row = dict(inst='u0',pin='clk',port='ck_head',physical_child=dict(view=self.rel,
            clock_pin='clk',reference_file=self.rel+'/insertion.json',
            sha256=hashlib.sha256((self.root/'insertion.json').read_bytes()).hexdigest(),
            reference_ps=dict(tt=650,ff=500)), effective_phase=dict(region='ra',contract='die_phi_minus_R',residual_ps=dict(tt=60,ff=50)))

    def artifacts(self, mod, spec):
        m=mod.Parent(spec);p=m.plan();rtl,rt=m.emit(p,'lpt_top_lp')
        return [rtl,m.sdc(p,'lpt_top_lp'),m.tb(p,'lpt_top_lp',rt),json.dumps(m.record(p,'lpt_top_lp',rt),sort_keys=True),m.bench_sh('lpt_top_lp',self.rel,p)]

    def test_default_all_artifact_bytes(self):
        old=self.root/'old_lp.py'
        old.write_bytes(subprocess.check_output(['git','show','aa8c09720:tools/landed_parent/lp.py'],cwd=lp.ROOT))
        spec=importlib.util.spec_from_file_location('old_lp',old);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        mod.ROOT=lp.ROOT
        for options in ({}, dict(landing_mcp=True), dict(landing_chunk_bits=24,landing_reset_forest=True,landing_reset_lead=True), dict(landing_chunk_bits=24,landing_writer='n32',landing_direct_timing=True)):
            with self.subTest(options=options):
                spec=dict(self.spec,**options)
                self.assertEqual(self.artifacts(mod,spec),self.artifacts(lp,spec))
        self.assertEqual(self.artifacts(lp,self.spec),self.artifacts(lp,dict(self.spec,entry_pins=[])))

    def test_entry_preserves_plan_and_checks_exact_connectivity(self):
        m=lp.Parent(dict(self.spec,entry_pins=[self.row]));p=m.plan();rtl,rt=m.emit(p,'lpt_top_lp')
        self.assertEqual(p,lp.Parent(self.spec).plan())
        self.assertIn('.clk(ck_head)',rtl)
        self.assertIn('input wire ck_head',rtl)
        self.assertTrue(lp.audit(m.S,rtl)['ok'])
        self.assertFalse(lp.audit(m.S,rtl.replace('.clk(ck_head)','.clk(ck_ra)'))['ok'])
        self.assertFalse(lp.audit(m.S,rtl.replace('input wire ck_head','input wire [0:0] ck_head'))['ok'])
        self.assertFalse(lp.audit(m.S,rtl.replace('.clk(ck_rb)','.clk(ck_head)',1))['ok'])
        unland=m.emit(m.plan(mut_unland=True),'lpt_top_lp')[0]
        self.assertFalse(lp.audit(m.S,unland)['ok'])
        self.assertEqual(m.record(p,'lpt_top_lp',rt)['entry_pins'],[self.row])
        self.assertIn('.ck_head(clk)',m.tb(p,'lpt_top_lp',rt))
        sdc=m.sdc(p,'lpt_top_lp')
        self.assertIn('create_clock -name ck_head',sdc)
        for forbidden in ('set_clock_latency','set_clock_groups','set_false_path','set_multicycle_path'):
            self.assertNotIn(forbidden,sdc)

    def test_three_hard_child_entries(self):
        (self.root/'child.sv').write_text("module hr(input wire ck_head,ck_pm0,ck_pm1,rst_n,input wire x,output wire y); assign y=x; endmodule")
        (self.root/'top.sv').write_text("module hr_top(input wire clk,rst_n,x,output wire y); hr u_hr(.ck_head(clk),.ck_pm0(clk),.ck_pm1(clk),.rst_n(rst_n),.x(x),.y(y)); endmodule")
        rows=[]
        for pin in ('ck_head','ck_pm0','ck_pm1'):
            row=copy.deepcopy(self.row);row.update(inst='u_hr',pin=pin,port=pin)
            row['physical_child']['clock_pin']=pin;rows.append(row)
        spec=dict(self.spec,top='hr_top',clock_pins=['ck_head','ck_pm0','ck_pm1'],regions=[dict(name='ra',insts=['u_hr'])],entry_pins=rows)
        m=lp.Parent(spec);p=m.plan();rtl,rt=m.emit(p,'hr_top_lp')
        self.assertTrue(lp.audit(spec,rtl)['ok'])
        for pin in ('ck_head','ck_pm0','ck_pm1'):
            self.assertIn(f'.{pin}({pin})',rtl)
        self.assertFalse(lp.audit(spec,rtl.replace('.ck_pm0(ck_pm0)','.ck_pm0(ck_pm1)'))['ok'])
        sdc=m.sdc(p,'hr_top_lp')
        self.assertLess(sdc.index('create_clock -name ck_pm1'),sdc.index('get_clocks ck_pm0'))
        self.assertIn('set_clock_uncertainty -setup 180 -from [get_clocks ck_head] -to [get_clocks ck_pm0]',sdc)

    def test_reject_incomplete_or_inexact_contract(self):
        mutations=[lambda r:r.update(inst='u*'),lambda r:r.update(pin='a'),lambda r:r.update(port='ck_ra'),
            lambda r:r.update(extra=True),lambda r:r['physical_child'].pop('view'),
            lambda r:r['physical_child'].update(sha256='0'*64),
            lambda r:r['physical_child']['reference_ps'].pop('ff'),
            lambda r:r['physical_child']['reference_ps'].update(tt=float('nan')),
            lambda r:r['effective_phase'].update(region='rb'),
            lambda r:r['effective_phase']['residual_ps'].update(ff=81),
            lambda r:r['effective_phase']['residual_ps'].update(tt=-1)]
        for mutate in mutations:
            row=copy.deepcopy(self.row);mutate(row)
            with self.subTest(row=row),self.assertRaises(SystemExit):
                lp.Parent(dict(self.spec,entry_pins=[row]))
        with self.assertRaises(SystemExit):lp.Parent(dict(self.spec,entry_pins=[self.row,self.row]))
        with self.assertRaises(SystemExit):lp.Parent(dict(self.spec,entry_pins=[self.row],landing_mcp=True))

if __name__=='__main__':unittest.main()
