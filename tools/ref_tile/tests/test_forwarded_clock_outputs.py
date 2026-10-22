"""Exact hard-clock feedthrough metadata and loaded-netlist guards."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
import test_forwarded_soft_clocks as T
import forwarded_clock_outputs as O


def fixture(root):
    s=T.soft_spec(root)
    s['clock_entry_domains']['core']['outputs'].append('fc')
    s['forwarded_clock_outputs']=[dict(input='xk[0]',output='fc',inst='f0',master='fwd',input_pin='CLK',output_pin='CO')]
    for c in T.CE.CORNERS:
        p=root/'fwd'/f'fwd_{c}.lib';t=p.read_text()
        extra='''pin(CO) { direction : output; timing() { related_pin : "CLK";
        timing_type : combinational; timing_sense : positive_unate;
        cell_rise(scalar) {values("10");} cell_fall(scalar) {values("10");} } }'''
        t=t.replace('    pin(Q)',extra+'\n    pin(Q)');p.write_text(t)
    return s


class Spec(unittest.TestCase):
    def test_exact_liberty_and_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);s=fixture(r)
            self.assertEqual(len(O.contract(s,r)),1)
            text=T.CE.generate(T.K.load(r,s),r)
            self.assertIn('set ::ot_ce_fwd_outputs [dict create {fc}',text)
            self.assertEqual(len(T.CE.forwarded_pre_cts_tcl(s,text)),3)
            self.assertIn('set ::ot_ce_fwd_outputs ',T.CE.clocks(s,833.333))

    def test_no_opt_in_bytes_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);s=T.soft_spec(r)
            a=T.CE.generate(T.K.load(r,s),r);s['forwarded_clock_outputs']=[]
            self.assertEqual(a,T.CE.generate(T.K.load(r,s),r))

    def test_reject_bad_pair_or_data_pin(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);s=fixture(r)
            for key,value in [('input','d'),('output','y'),('inst','f1'),('master','fwd2'),('input_pin','D'),('output_pin','Q')]:
                bad=copy.deepcopy(s);bad['forwarded_clock_outputs'][0][key]=value
                # y is a declared data output but lacks a source-backed named pair in runtime;
                # syntax can declare it, while data output Q is rejected by actual Liberty.
                if key=='output':continue
                with self.subTest(key=key),self.assertRaises(ValueError):O.contract(bad,r)
            for rows in [None,{},s['forwarded_clock_outputs']*2]:
                bad=copy.deepcopy(s);bad['forwarded_clock_outputs']=rows
                with self.subTest(rows=rows),self.assertRaises(ValueError):O.contract(bad,r)

    def test_reject_gated_or_noncombinational_liberty(self):
        for change in [('positive_unate','negative_unate'),('timing_type : combinational','timing_type : rising_edge'),('timing_sense : positive_unate;','timing_sense : positive_unate; when : "D";')]:
            with tempfile.TemporaryDirectory() as d:
                r=Path(d);s=fixture(r)
                p=r/'fwd/fwd_tt.lib';p.write_text(p.read_text().replace(*change))
                with self.subTest(change=change),self.assertRaises(ValueError):O.contract(s,r)


@unittest.skipUnless(T.os.environ.get('OT_FRRST_FLEET_TEST')=='1' and T.K.available(), 'fleet OpenROAD required')
class Actual(unittest.TestCase):
    def flow(self, mutant=''):
        F=T.F
        old_fixture,old_rtl=F.fixture,F.RTL
        def wrapped(root, fwd2=None):
            s=old_fixture(root,fwd2)
            s['clock_entry_domains']['core']['outputs'].append('fc')
            s['pins']['E'].append('fc')
            s['forwarded_clock_outputs']=[dict(input='xk[0]',output='fc',inst='f0',master='fwd',input_pin='CLK',output_pin='CO')]
            if mutant=='undeclared':s.pop('forwarded_clock_outputs')
            if mutant=='data_output':s['forwarded_clock_outputs'][0]['output']='w0'
            for c in T.CE.CORNERS:
                p=root/'fwd'/f'fwd_{c}.lib'
                extra='''pin(CO) { direction : output; timing() { related_pin : "CLK";
                  timing_type : combinational; timing_sense : positive_unate;
                  cell_rise(scalar) {values("10");} cell_fall(scalar) {values("10");} } }'''
                p.write_text(p.read_text().replace('    pin(Q)',extra+'\n    pin(Q)'))
            p=root/'fwd/fwd.lef'
            p.write_text(p.read_text().replace('END fwd END LIBRARY','PIN CO DIRECTION OUTPUT ; USE CLOCK ; PORT LAYER M4 ; RECT 9.8 0.7 9.9 0.8 ; END END CO\nEND fwd END LIBRARY'))
            return s
        try:
            F.fixture=wrapped
            F.RTL=old_rtl.replace('output w2);','output w2, output fc);').replace('.Q(w0));','.Q(w0), .CO(fc0));').replace('endmodule','BUFx2_ASAP7_75t_R output_buf (.A(fc0), .Y(fc));\nendmodule')
            if mutant=='wrong_source':
                F.RTL=F.RTL.replace('fwd f0(.CLK(xk[0])','fwd f0(.CLK(xk[1])')
            if mutant=='gated':
                F.RTL=F.RTL.replace('BUFx2_ASAP7_75t_R output_buf (.A(fc0), .Y(fc));','AND2x2_ASAP7_75t_R bad_gate (.A(fc0), .B(d), .Y(fc));')
            if mutant=='multidriver':
                F.RTL=F.RTL.replace('endmodule','BUFx2_ASAP7_75t_R bad_driver (.A(d), .Y(fc));\nendmodule')
            return T.Actual().flow('stage_restart')
        finally:
            F.fixture,F.RTL=old_fixture,old_rtl

    def test_actual_pair_and_fresh_cts(self):
        rc,out=self.flow();self.assertEqual(rc,0,out[-8000:])
        self.assertIn('OT_FORWARDED_OUTPUT preserved xk[0] -> fc through=f0',out)

    def test_actual_source_and_logic_refusals(self):
        for m in ('undeclared','wrong_source','data_output','gated','multidriver'):
            with self.subTest(mutant=m):
                rc,out=self.flow(m);self.assertNotEqual(rc,0,out[-8000:])
                self.assertRegex(out,r'OT_FORWARDED_(OUTPUT|SOFT)')

if __name__=='__main__':unittest.main()
