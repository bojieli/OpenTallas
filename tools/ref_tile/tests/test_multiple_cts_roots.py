"""Two real, independently delivered samefrequency leaf clocks and IO references."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import clock_entry_constraints as CE
import ref_tile as RT
ROOT = Path(__file__).resolve().parents[3]
IMAGE='openroad/orfs:latest'
OR='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'

def spec():
    return dict(name='two_roots',top='top',kind='tile',sources=[],pins={'S':['req','rsp'],'N':['qo','zo'],'W':['ck_req','ck_rsp']},
                clock='multiple_cts_roots',clock_port='ck_req',clock_ports=['ck_req','ck_rsp'],children=[],reset_ports=[],
                clock_entry_domains=dict(core=dict(ratio=[1,1],ports=['ck_req'],inputs=['req'],outputs=['qo']),
                                         response=dict(ratio=[1,1],ports=['ck_rsp'],inputs=['rsp'],outputs=['zo'])))

def available():
    return bool(shutil.which('docker')) and subprocess.run(['docker','image','inspect',IMAGE],capture_output=True).returncode==0

class Schema(unittest.TestCase):
    def test_leaf_requires_explicit_samefrequency_single_root_domains(self):
        s=spec()
        self.assertEqual(len(CE.domains(s)),2)
        for mutate in [lambda x:x.pop('clock_entry_domains'),lambda x:x.update(kind='cluster'),
                       lambda x:x['clock_entry_domains']['response'].update(ratio=[4,3]),
                       lambda x:x['clock_entry_domains']['core'].update(inputs=['*'])]:
            m=copy.deepcopy(s);mutate(m)
            with self.assertRaises(ValueError):CE.domains(m)
        text=CE.generate(s,ROOT)
        self.assertNotIn('set_false_path',text);self.assertNotIn('set_clock_groups',text)
        self.assertIn('ot_ce_leaf_ownership',text)

    def test_load_spec_and_generated_stage_coverage(self):
        s=spec()
        with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
            json.dump(s,f);f.flush();loaded=RT.load_spec(f.name)
        self.assertEqual(RT.clock_ports(loaded),['ck_req','ck_rsp'])
        hooks=RT.gen_hooks(loaded,'physical/generated_two_roots')
        for name in ['pre_grt.tcl','post_cts.tcl','post_grt.tcl','pre_drt.tcl','post_drt.tcl','pre_fill.tcl','post_fill.tcl']:
            self.assertIn('clock_entry.sdc',hooks[name])
            self.assertNotIn('io_ref_skew.sdc',hooks[name])
            self.assertNotIn('post_plain.tcl',hooks[name])
        self.assertIn('clock_entry.sdc',hooks['pre_cts.tcl'])
        self.assertNotIn('pre_cts_skew.tcl',hooks['pre_cts.tcl'])

    def test_each_actual_root_clock_rule_and_missing_census(self):
        import pre_route_gate as G
        def record(n=4,hi=100):
            rows=[dict(source='ck_req',clock='ot_entry_0',tt=dict(all=dict(n=16,min=80,max=100))),
                  dict(source='ck_rsp',clock='ot_entry_1',tt=dict(all=dict(n=n,min=70,max=hi)))]
            out='textbook_lint: INFO clock_roots max_root_sinks=16 root=port:ck_req\n'
            out+=''.join('GATE_CK_DOMAIN '+json.dumps(x)+'\n' for x in rows)
            return out
        self.assertEqual(G.clock_record(record(),True,spec())['verdict'],'PASS')
        self.assertEqual(len(G.clock_record(record(),True,spec())['per_root']),2)
        self.assertEqual(G.clock_record(record(n=16001,hi=400),True,spec())['verdict'],'REFUSE')
        self.assertEqual(G.clock_record(record(),False,spec())['verdict'],'REFUSE')
        missing=record().splitlines()[0]+'\n'
        self.assertEqual(G.clock_record(missing,True,spec())['verdict'],'REFUSE')

@unittest.skipUnless(available(),'real OpenROAD ORFS image required')
class Physical(unittest.TestCase):
    def run_flow(self,mutant='',generated=False):
        with tempfile.TemporaryDirectory() as d:
            w=Path(d);s=spec();s.update(params={},route={},macros=[])
            kd='physical/generated_two_roots'
            if generated:
                for name,text in RT.gen_hooks(s,kd).items():(w/name).write_text(text)
                (w/'signoff.sdc').write_text(RT.gen_signoff(s,'*','none_*'))
            if mutant=='wrong_input':
                s['clock_entry_domains']['core']['inputs']=['rsp'];s['clock_entry_domains']['response']['inputs']=['req']
            if mutant=='wrong_output':
                s['clock_entry_domains']['core']['outputs']=['zo'];s['clock_entry_domains']['response']['outputs']=['qo']
            if mutant=='unknown_port':s['clock_entry_domains']['core']['inputs']=['req','missing']
            cells='\n'.join(f'DFFHQNx1_ASAP7_75t_R r{i} (.CLK(ck_req),.D(req),.QN(q{i}));' for i in range(16))
            cells+='\n'+'\n'.join(f'DFFHQNx1_ASAP7_75t_R s{i} (.CLK(ck_rsp),.D({"q0" if mutant=="cross_data" else "rsp"}),.QN(z{i}));' for i in range(4))
            (w/'t.v').write_text('module top(input ck_req,ck_rsp,req,rsp,output qo,zo);\n'+cells+'\nassign qo=q0;assign zo=z0;endmodule\n')
            (w/'clocks.tcl').write_text(CE.clocks(s,833.333))
            (w/'entry.tcl').write_text('set ::ot_ce_require_wire 1\n'+CE.generate(s,ROOT))
            flow=r'''
set_thread_count 2
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach l [glob $P/lib/NLDM/*RVT_TT*] {read_liberty $l}
read_verilog /w/t.v
link_design top
initialize_floorplan -die_area {0 0 100 100} -core_area {5.4 5.4 94.6 94.6} -site asap7sc7p5t
source $P/openRoad/make_tracks.tcl
place_pins -hor_layers M4 -ver_layers M5
source /w/clocks.tcl
set_input_delay 10 -clock core_clk [get_ports {req rsp}]
set_output_delay 10 -clock core_clk [get_ports {qo zo}]
source $P/setRC.tcl
set u [[ord::get_db_block] getDbUnitsPerMicron]
set k 0
foreach i [[ord::get_db_block] getInsts] {
  $i setLocation [expr {int((15+12*($k%4))*$u)}] [expr {int((15+12*($k/4))*$u)}]
  $i setPlacementStatus PLACED;incr k
}
detailed_placement
set ::ot_ce_cts_roots {ck_req ck_rsp}
source /src/physical/common_flow/clock_entries.tcl
clock_tree_synthesis -sink_clustering_enable -buf_list BUFx4_ASAP7_75t_R -root_buf BUFx4_ASAP7_75t_R
estimate_parasitics -placement
source /w/entry.tcl
# A repeated stage replays measured references, not the previous compensation.
source /w/entry.tcl
puts "MULTI_ROOT_RESULT PASS"
'''
            if generated:
                flow=flow.replace('set ::ot_ce_cts_roots {ck_req ck_rsp}\nsource /src/physical/common_flow/clock_entries.tcl',
                                  f'source /src/{kd}/pre_cts.tcl')
                flow=flow.replace('source /w/entry.tcl\n# A repeated stage replays measured references, not the previous compensation.\nsource /w/entry.tcl',
                    'set ::env(MAX_ROUTING_LAYER) M5\n'+'\n'.join(f'source /src/{kd}/{n}' for n in
                    ['post_cts.tcl','pre_grt.tcl','post_grt.tcl','pre_drt.tcl','post_drt.tcl','pre_fill.tcl','post_fill.tcl','signoff.sdc']))
            (w/'run.tcl').write_text(flow)
            p=subprocess.run(['docker','run','--rm','-v',f'{w}:/w','-v',f'{ROOT}:/src:ro','-v',f'{w}:/src/{kd}:ro',IMAGE,OR,'-no_init','-exit','/w/run.tcl'],capture_output=True,text=True,timeout=60)
            return p.returncode,p.stdout+p.stderr
    def test_actual_roots_and_distinct_references(self):
        rc,out=self.run_flow();self.assertEqual(rc,0,out[-7000:])
        self.assertIn('ck_req sinks=16',out);self.assertIn('ck_rsp sinks=4',out)
        self.assertIn('OWNERSHIP PASS roots=2 registers=20',out)
        refs=re.findall(r'COMP tt (ck_\w+) -> \S+ wire=([\d.eE+-]+) R=([\d.eE+-]+) latency=([\d.eE+-]+) phi=([\d.eE+-]+)',out)
        self.assertEqual(len(refs),4,out[-5000:])
        self.assertNotAlmostEqual(float(refs[0][2]),float(refs[1][2]),places=3)
        for _,wire,r,lat,phi in refs:self.assertAlmostEqual(float(wire)+float(r)+float(lat),float(phi),places=6)
        for a,b in zip(refs[:2],refs[2:]):
            self.assertEqual(a[0],b[0])
            for x,y in zip(a[1:],b[1:]):self.assertAlmostEqual(float(x),float(y),places=8)
    def test_generated_hooks_and_signoff_replay(self):
        rc,out=self.run_flow(generated=True);self.assertEqual(rc,0,out[-7000:])
        self.assertGreaterEqual(out.count('OT_MULTI_ROOT OWNERSHIP PASS'),9)
        self.assertIn('MULTI_ROOT_RESULT PASS',out)

    def test_bad_graph_and_io_declarations_rejected(self):
        for mutant in ['wrong_input','wrong_output','unknown_port','cross_data']:
            with self.subTest(mutant=mutant):
                rc,out=self.run_flow(mutant);self.assertNotEqual(rc,0,out[-6000:]);self.assertIn('OT_MULTI_ROOT',out)

if __name__=='__main__':unittest.main()
