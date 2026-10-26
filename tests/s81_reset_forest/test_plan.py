import copy
import importlib.util
from pathlib import Path
import unittest
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('reset_forest', ROOT/'tools/s81/reset_forest.py')
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)


def fixture():
    d = dict(schema='s81.reset-forest.input.v1', source_sha256='1'*64, model_sha256='2'*64,
             placement_sha256='3'*64, pins={}, sites=[], pair_checks={}, domains={
                 'stream':dict(clock_delivery='phi_minus_R', period_ps=833.333,
                               setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                               max_edge_um=500, wire_ps_per_um=.76, skew_ps=90,
                               max_fanout=4, max_delay_cycles=64)},
             nets=[dict(id='rst_stream', root='root', sinks=['near','far'], root_release='qualified_domain_edge',root_epoch='cold_or_warm_restart',root_release_cycle=0)])
    def pin(name, x, direction):
        d['pins'][name] = dict(xy_um=[x,0], exact_placed_pin=True, domain='stream', clock='ck',
                              direction=direction, launch_ps=100, capture_ps=100, direction_source_sha256='1'*64, instance=name, port='reset')
    pin('root',0,'output')
    pin('near',120,'input'); pin('far',1100,'input')
    for sid,x,role,sinks in [('n',100,'terminal',['near']), ('a',400,'branch',[]),
                              ('b',800,'branch',[]), ('f',1050,'terminal',['far'])]:
        pin(sid+'i',x,'input'); pin(sid+'o',x+1,'output')
        d['sites'].append(dict(id=sid,domain='stream',clock='ck',role=role,net='rst_stream',
                               sinks=sinks,area_um2=100,reserved_nonoverlap=True, delay_views={str(k):dict(source_sha256='1'*64,view_sha256='4'*64,area_um2=100,input_pin=sid+'i',output_pin=sid+'o') for k in (1,4,7)}, **{'in':sid+'i','out':sid+'o'}))
    for a,p in d['pins'].items():
        for z,q in d['pins'].items():
            if p['direction']=='output' and q['direction']=='input':
                d['pair_checks'][a+'->'+z]=dict(source_sha256='1'*64, placement_sha256='3'*64, ff_hold_slack_ps=25,
                                               recovery_slack_ps=25, removal_slack_ps=25)
    return d


class PlannerTest(unittest.TestCase):
    def test_balanced_release_and_coverage(self):
        p=rf.plan(fixture()); self.assertEqual(p['covered_sinks'],2)
        n=p['nets'][0]; self.assertEqual(n['release_cycles'],9)
        self.assertEqual({x['site']:x['delay_cycles'] for x in n['nodes']},dict(a=1,b=1,f=1,n=7))
        self.assertTrue(all(e['length_um']<=500 for e in n['edges']))

    def test_independent_roots_share_domain_calendar(self):
        d=fixture()
        for new,old in [('root2','root'),('near2','near'),('gi','ni'),('go','no')]:
            d['pins'][new]=copy.deepcopy(d['pins'][old]); d['pins'][new]['xy_um'][0]+=3000
        site=copy.deepcopy(d['sites'][0]); site.update(id='g',net='rst_second',sinks=['near2'])
        site['in']='gi'; site['out']='go'
        for v in site['delay_views'].values(): v.update(input_pin='gi',output_pin='go')
        d['sites'].append(site)
        d['nets'].append(dict(id='rst_second',root='root2',sinks=['near2'],root_release='qualified_domain_edge',root_epoch='cold_or_warm_restart',root_release_cycle=0))
        for a in ['root2','go']:
            for z in ['gi','near2']:
                d['pair_checks'][a+'->'+z]=dict(source_sha256='1'*64,placement_sha256='3'*64,
                                               ff_hold_slack_ps=25,recovery_slack_ps=25,removal_slack_ps=25)
        result=rf.plan(d)
        self.assertEqual([n['release_cycles'] for n in result['nets']],[9,9])
        self.assertEqual(result['nets'][1]['nodes'][0]['delay_cycles'],7)

    def test_missing_parameter_view_rejected(self):
        d=fixture(); d['sites'][0]['delay_views'].pop('7')
        with self.assertRaisesRegex(rf.PlanError,'exact delay-parameter'): rf.plan(d)

    def test_complete_model_coverage(self):
        d=fixture(); model={'buses':[['rst_stream','reset',1,[['root','reset'],['near','reset'],['far','reset']]]]}
        rf.verify_model_coverage(d,model)
        model['buses'].append(['missing','col_reset',1,[['r','o'],['s','i']]])
        with self.assertRaisesRegex(rf.PlanError,'coverage mismatch'): rf.verify_model_coverage(d,model)

    def test_rtl_emission(self):
        result=rf.plan(fixture()); rtl=rf.emit_rtl(result)
        self.assertEqual(rtl.count('ot_s81_reset_leaf #'),4)
        self.assertEqual(len(result['nets'][0]['sink_port_map']),2)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td); (path/'forest.sv').write_text(rtl)
            (path/'tb.sv').write_text('''`timescale 1ns/1ps
module tb;
reg ck=0; always #5 ck=~ck;
reg rs=1; wire [1:0] out;
ot_s81_reset_forest_candidate dut(ck,rs,out);
integer i;
initial begin
#1 rs=0; #0.1; if(out!==0) $fatal(1,"generated async assertion");
@(negedge ck); rs=1;
for(i=1;i<=10;i=i+1) begin
@(posedge ck); #0.1;
if(out!==(i>=9 ? 2'b11 : 2'b00)) $fatal(1,"generated exact release");
end
$finish; end
endmodule
''')
            subprocess.run(['iverilog','-g2012','-s','tb','-o',str(path/'sim'),
                            str(ROOT/'rtl/dsrom_sys/s81_reset_forest/ot_s81_reset_leaf.sv'),
                            str(path/'forest.sv'),str(path/'tb.sv')],check=True)
            subprocess.run(['vvp',str(path/'sim')],check=True)

    def test_missing_pin_anchor_mutant(self):
        d=fixture(); d['pins']['far']['exact_placed_pin']=False
        with self.assertRaisesRegex(rf.PlanError,'exact placed pin'): rf.plan(d)

    def test_far_sink_mutant(self):
        d=fixture(); d['pins']['far']['xy_um']=[1900,0]
        with self.assertRaisesRegex(rf.PlanError,'unreachable local sink'): rf.plan(d)

    def test_unreachable_branch_mutant(self):
        d=fixture(); d['sites']=[s for s in d['sites'] if s['id']!='a']
        with self.assertRaisesRegex(rf.PlanError,'unreachable terminal'): rf.plan(d)

    def test_domain_crossing_mutant(self):
        d=fixture(); d['pins']['far']['clock']='serial'
        with self.assertRaisesRegex(rf.PlanError,'crossing'): rf.plan(d)

    def test_coverage_mutant(self):
        d=fixture(); d['sites'][-1]['sinks']=[]
        with self.assertRaisesRegex(rf.PlanError,'exactly cover'): rf.plan(d)

    def test_recovery_removal_hold_mutants(self):
        for gate in ['ff_hold_slack_ps','recovery_slack_ps','removal_slack_ps']:
            d=fixture()
            for p in d['pair_checks'].values(): p[gate]=-1
            with self.assertRaisesRegex(rf.PlanError,'unreachable'): rf.plan(d)

    def test_setup_pair_budget_mutant(self):
        d=fixture(); d['pins']['root']['launch_ps']=800
        with self.assertRaisesRegex(rf.PlanError,'unreachable'): rf.plan(d)

    def test_async_root_mutant(self):
        d=fixture(); d['nets'][0]['root_release']='asynchronous'
        with self.assertRaisesRegex(rf.PlanError,'fixed calendar'): rf.plan(d)


if __name__=='__main__': unittest.main()
