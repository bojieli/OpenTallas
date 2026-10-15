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
        for relationship in [None,dict(kind='asynchronous'),dict(kind='same_pll_fixed_phase',ratio=[4,3],phase_ps=0)]:
            m=copy.deepcopy(s);m.update(clock_data_paths='related_same_frequency',clock_relationship=relationship)
            with self.assertRaises(ValueError):CE.domains(m)

    def test_related_pll_ratio_admits_only_a_noncore_four_thirds_domain(self):
        s=spec();s['clock_entry_domains']['response']['ratio']=[4,3]
        s.update(clock_data_paths='related_pll_ratio',clock_relationship=dict(kind='same_pll_fixed_phase',ratio=[4,3],phase_ps=0))
        self.assertEqual(CE.domains(s)['response']['ratio'],[4,3])
        clocks=CE.clocks(s,833.333)
        self.assertIn('create_clock -name ot_entry_1 -period 1111.110666667',clocks)
        self.assertIn('create_clock -name ot_io_response -period 1111.110666667',clocks)
        text=CE.generate(s,ROOT)
        self.assertIn('set ::ot_ce_related_data 1',text);self.assertIn('io_budget_ps 222.222',text)
        self.assertNotIn('set_false_path',text);self.assertNotIn('set_clock_groups',text)
        for mutate in [lambda x:x['clock_entry_domains']['core'].update(ratio=[4,3]),
                       lambda x:x['clock_entry_domains']['response'].update(ratio=[3,4]),
                       lambda x:x['clock_entry_domains']['response'].update(ratio=[1,1]),
                       lambda x:x.update(clock_relationship=dict(kind='same_pll_fixed_phase',ratio=[1,1],phase_ps=0)),
                       lambda x:x.update(clock_relationship=dict(kind='same_pll_fixed_phase',ratio=[4,3],phase_ps=10)),
                       lambda x:x.update(clock_data_paths='related_same_frequency'),
                       lambda x:x.update(clock_data_paths='independent',clock_relationship=None)]:
            m=copy.deepcopy(s);mutate(m)
            if m.get('clock_relationship') is None:m.pop('clock_relationship',None)
            with self.assertRaises(ValueError):CE.domains(m)

    def test_explicit_leaf_signoff_period_and_budget(self):
        s=spec();s['route']={'period_ps':1111.111,'signoff_period_ps':1111.111}
        self.assertEqual(CE.signoff_period(s),1111.111)
        self.assertIn('io_budget_ps 222.222',CE.generate(s,ROOT))
        route=RT.gen_sdc(s,1111.111);signoff=RT.gen_signoff(s,'*','none_*')
        for text in (route,signoff):
            self.assertIn('-period 1111.111000000',text)
            self.assertIn('set_clock_uncertainty -setup 60',text)
            self.assertIn('set_clock_uncertainty -hold 25',text)
        self.assertIn('set_input_delay 222.222',route)
        for value in (0,-1,float('nan'),float('inf'),True,'1111.111'):
            m=copy.deepcopy(s);m['route']['signoff_period_ps']=value
            with self.assertRaises(ValueError):CE.signoff_period(m)
        m=copy.deepcopy(s);m['route']['period_ps']=1200
        with self.assertRaises(ValueError):CE.signoff_period(m)
        m=copy.deepcopy(s);m['clock']='cts'
        with self.assertRaises(ValueError):CE.signoff_period(m)

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

    def test_route_and_formal_cts_use_the_same_single_boundary_owner(self):
        import pre_route_gate as G
        s=spec();s.update(params={},route={},macros=[])
        cmd=RT.gen_job(s,'physical/generated_two_roots','deadbeef',[])['stages']['route']['cmd']
        self.assertIn("OT_CTS_FIX_HOOKS='"+RT.clock_fix_hooks(s)+"'",cmd)
        self.assertNotIn('link_budget_hook.tcl',cmd)
        gate=G.gate_route_clock_hooks('export OT_ORFS_CORNER_OVERRIDE=TC\n',s)
        self.assertIn("OT_CTS_FIX_HOOKS='"+RT.clock_fix_hooks(s)+"'",gate)
        s['clock']='cts'
        self.assertEqual(G.gate_route_clock_hooks('unchanged',s),'unchanged')
        self.assertEqual(RT.route_prefix(s),RT.ROUTE_PREFIX)
        self.assertIn('link_budget_hook.tcl',RT.route_prefix(s))

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
            if mutant=='serial':s['route']={'period_ps':1111.111,'signoff_period_ps':1111.111}
            # Mount the fixture on an existing source directory beneath the read-only repo.
            kd='tools/ref_tile/tests'
            if mutant in ('related','related_wrong_input','related_cut'):
                s.update(clock_data_paths='related_same_frequency',clock_relationship=dict(kind='same_pll_fixed_phase',ratio=[1,1],phase_ps=0))
            if mutant in ('related_pll','related_pll_cut'):
                s['clock_entry_domains']['response']['ratio']=[4,3]
                s.update(clock_data_paths='related_pll_ratio',clock_relationship=dict(kind='same_pll_fixed_phase',ratio=[4,3],phase_ps=0))
            if mutant=='related_wrong_input':
                s['clock_entry_domains']['core']['inputs']=['rsp'];s['clock_entry_domains']['response']['inputs']=['req']
            if mutant in ('async_reset','async_reset_data'):
                s['clock_entry_domains']['core']['inputs'].append('rst_n');s['reset_ports']=['rst_n']
            if mutant=='declared_reset':s['reset_ports']=['req']
            if mutant=='wrong_input':
                s['clock_entry_domains']['core']['inputs']=['rsp'];s['clock_entry_domains']['response']['inputs']=['req']
            if mutant=='wrong_output':
                s['clock_entry_domains']['core']['outputs']=['zo'];s['clock_entry_domains']['response']['outputs']=['qo']
            if mutant=='unknown_port':s['clock_entry_domains']['core']['inputs']=['req','missing']
            if mutant.startswith('tie'):s['clock_entry_domains']['core']['outputs'].append('th')
            if generated:
                for name,text in RT.gen_hooks(s,kd).items():(w/name).write_text(text)
                (w/'signoff.sdc').write_text(RT.gen_signoff(s,'*','none_*'))
            cells='\n'.join(f'DFFHQNx1_ASAP7_75t_R r{i} (.CLK(ck_req),.D({"z0" if mutant.startswith("related") and i==1 else "req"}),.QN(q{i}));' for i in range(16))
            cells+='\n'+'\n'.join(f'DFFHQNx1_ASAP7_75t_R s{i} (.CLK(ck_rsp),.D({"q0" if mutant=="cross_data" or mutant.startswith("related") and i==0 else "rsp"}),.QN(z{i}));' for i in range(4))
            if mutant in ('async_reset','async_reset_data'):
                cells=cells.replace('DFFHQNx1_ASAP7_75t_R r0 (.CLK(ck_req),.D(req),.QN(q0));',
                    'DFFASRHQNx1_ASAP7_75t_R r0 (.CLK(ck_req),.D(req),.RESETN(rst_n),.SETN(1\'b1),.QN(q0));')
                cells=cells.replace('DFFHQNx1_ASAP7_75t_R s0 (.CLK(ck_rsp),.D(rsp),.QN(z0));',
                    'DFFASRHQNx1_ASAP7_75t_R s0 (.CLK(ck_rsp),.D('+('rst_n' if mutant=='async_reset_data' else 'rsp')+'),.RESETN(rst_n),.SETN(1\'b1),.QN(z0));')
            extra=',rst_n' if mutant in ('async_reset','async_reset_data') else ''
            src={'tie':'tc','tie_port':'req','tie_reg':'z1'}.get(mutant)
            tie=(',th','\nwire tc;TIEHIx1_ASAP7_75t_R t0 (.H(tc));BUFx2_ASAP7_75t_R b0 (.A('+src+'),.Y(th));') if src else ('','')
            # Multi-input gate of constants is constant; one live input is not.
            gate={'tie_gate':'tl','tie_gate_port':'req'}.get(mutant)
            if gate:tie=(',th','\nwire tc,tl;TIEHIx1_ASAP7_75t_R t0 (.H(tc));TIELOx1_ASAP7_75t_R t1 (.L(tl));NAND2xp33_ASAP7_75t_R g0 (.A(tc),.B('+gate+'),.Y(th));')
            # Input-side constant: a register D fed by a buffered tie (Engram/K0 style).
            if mutant=='constant_data':
                cells=cells.replace('DFFHQNx1_ASAP7_75t_R s3 (.CLK(ck_rsp),.D(rsp),.QN(z3));',
                    'wire kl,kd;TIELOx1_ASAP7_75t_R t2 (.L(kl));BUFx2_ASAP7_75t_R b2 (.A(kl),.Y(kd));DFFHQNx1_ASAP7_75t_R s3 (.CLK(ck_rsp),.D(kd),.QN(z3));')
                assert '.D(kd)' in cells
            constant_case=mutant in ('constant','constant_nonconstant','constant_case_analysis')
            if constant_case:
                source='req' if mutant!='constant' else 'tie_zero'
                cells+='\nTIELOx1_ASAP7_75t_R arbitrary_name(.L(tie_zero));\n'
                cells+=f'BUFx2_ASAP7_75t_R preserved_buffer(.A({source}),.Y(zo));\n'
            (w/'t.v').write_text('module top(input ck_req,ck_rsp,req,rsp'+extra+',output qo,zo'+tie[0]+');\n'+cells+tie[1]+'\nassign qo=q0;'+('' if constant_case else 'assign zo=z0;')+'endmodule\n')
            (w/'clocks.tcl').write_text(CE.clocks(s,s['route'].get('period_ps',833.333)))
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
write_sdc -no_timestamp /w/final.sdc
puts "MULTI_ROOT_RESULT PASS"
'''
            if generated:
                flow=flow.replace('set ::ot_ce_cts_roots {ck_req ck_rsp}\nsource /src/physical/common_flow/clock_entries.tcl',
                                  f'source /src/{kd}/pre_cts.tcl\n'+'\n'.join('source /src/'+h for h in RT.clock_fix_hooks(s).split()))
                flow=flow.replace('source /w/entry.tcl\n# A repeated stage replays measured references, not the previous compensation.\nsource /w/entry.tcl',
                    'set ::env(MAX_ROUTING_LAYER) M5\n'+'\n'.join(f'source /src/{kd}/{n}' for n in
                    ['post_cts.tcl','pre_grt.tcl','post_grt.tcl','pre_drt.tcl','post_drt.tcl','pre_fill.tcl','post_fill.tcl','signoff.sdc']))
            if mutant=='physical_tap':
                flow=flow.replace('set ::ot_ce_cts_roots',r'''set tap [odb::dbInst_create [ord::get_db_block] [[ord::get_db] findMaster TAPCELL_ASAP7_75t_R] physical_tap]
$tap setLocation 10000 90000
$tap setPlacementStatus FIRM
set cells [get_cells physical_tap]
if {"NULL" ni [get_lib_cells -of_objects $cells]} {error "fixture missing actual LEF-only cell"}
set ::ot_ce_cts_roots''',1) if not generated else flow.replace(f'source /src/{kd}/pre_cts.tcl',r'''set tap [odb::dbInst_create [ord::get_db_block] [[ord::get_db] findMaster TAPCELL_ASAP7_75t_R] physical_tap]
$tap setLocation 10000 90000
$tap setPlacementStatus FIRM
if {"NULL" ni [get_lib_cells -of_objects [get_cells physical_tap]]} {error "fixture missing actual LEF-only cell"}
'''+f'source /src/{kd}/pre_cts.tcl',1)
            if mutant=='extra_alias':
                flow=flow.replace('source /w/entry.tcl','create_clock -name unexpected_alias -period 833.333\nsource /w/entry.tcl',1)
            if mutant in ('related_cut','related_pll_cut'):
                flow=flow.replace('source /w/entry.tcl','set_false_path -from [get_clocks ot_entry_0] -to [get_clocks ot_entry_1]\nsource /w/entry.tcl',1)
            if mutant=='constant_case_analysis':
                flow=flow.replace('source /w/entry.tcl','set_case_analysis 0 [get_ports req]\nsource /w/entry.tcl',1)
            flow='try {\n'+flow+'\n} on error {message options} {puts stderr [dict get $options -errorinfo];exit 1}\n'
            (w/'run.tcl').write_text(flow)
            p=subprocess.run(['docker','run','--rm','-v',f'{w}:/w','-v',f'{ROOT}:/src:ro','-v',f'{w}:/src/{kd}:ro',IMAGE,OR,'-no_init','-exit','/w/run.tcl'],capture_output=True,text=True,timeout=60)
            output=p.stdout+p.stderr
            if p.returncode==0 and generated:
                # Assert every max/min budget after the actual route hook stack
                # and repeated signoff, so excluding the legacy overlay cannot
                # silently remove or change the explicit domain constraints.
                refs={d:(float(lo),float(hi)) for d,lo,hi in re.findall(
                    r'OT_ENTRIES DOMAIN (\w+) [^\n]*boundary=([\d.eE+-]+)\.\.([\d.eE+-]+)',output)}
                final=(w/'final.sdc').read_text()
                for port,domain,direction in [('req','core','input'),('rsp','response','input'),('qo','core','output'),('zo','response','output')]:
                    lo,hi=refs[domain];clock=CE.virtual_clock(domain)
                    values=re.findall(r'set_'+direction+r'_delay ([\d.eE+-]+) -clock \[get_clocks \{'+clock+r'\}\] -(min|max) -add_delay \[get_ports \{'+port+r'\}\]',final)
                    self.assertEqual(len(values),2,final)
                    actual={kind:float(value) for value,kind in values}
                    r=s['clock_entry_domains'][domain]['ratio'];budget=round(CE.signoff_period(s)*r[0]/r[1]*0.2,3)
                    expected={'min':lo,'max':budget+hi+90} if direction=='input' else {'min':-lo-50,'max':budget-hi+90}
                    for kind in ['min','max']:self.assertAlmostEqual(actual[kind],expected[kind],places=2)
            if p.returncode==0 and mutant=='serial':
                periods=[float(x) for x in re.findall(r'create_clock -name \S+ -period ([\d.]+)',(w/'final.sdc').read_text())]
                self.assertEqual(len(periods),4)
                for period in periods:self.assertAlmostEqual(period,1111.111,places=3)
            return p.returncode,output
    def test_actual_serial_profile_hooks_and_numeric_io(self):
        rc,out=self.run_flow('serial',generated=True);self.assertEqual(rc,0,out[-8000:])
        self.assertIn('OWNERSHIP PASS roots=2 registers=20',out)

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
    def test_die_strap_tie_output_is_constant_not_a_domain(self):
        rc,out=self.run_flow('tie');self.assertEqual(rc,0,out[-8000:])
        self.assertIn('OT_MULTI_ROOT LIBERTY_CONSTANT th -> th',out)
        # A buffered port passthrough still fails closed; a buffered other-domain register is refused by name.
        rc,out=self.run_flow('tie_port');self.assertNotEqual(rc,0,out[-8000:])
        rc,out=self.run_flow('tie_reg');self.assertNotEqual(rc,0,out[-8000:])
        self.assertIn('output th has wrong or unregistered source domain',out)

    def test_liberty_function_gate_of_constants_and_live_input(self):
        rc,out=self.run_flow('tie_gate');self.assertEqual(rc,0,out[-8000:])
        self.assertIn('LIBERTY_CONSTANT',out)
        rc,out=self.run_flow('tie_gate_port');self.assertNotEqual(rc,0,out[-8000:])
        self.assertIn('output th has wrong or unregistered source domain',out)

    def test_input_side_constant_register_data(self):
        rc,out=self.run_flow('constant_data');self.assertEqual(rc,0,out[-8000:])
        self.assertIn('OWNERSHIP PASS',out)

    def test_actual_liberty_constant_output_and_nonconstant_mutants(self):
        rc,out=self.run_flow('constant',generated=True);self.assertEqual(rc,0,out[-8000:])
        self.assertIn('LIBERTY_CONSTANT',out)
        for mutant in ('constant_nonconstant','constant_case_analysis'):
            rc,out=self.run_flow(mutant);self.assertNotEqual(rc,0,out[-5000:])
            self.assertIn('wrong or unregistered source domain',out)

    def test_generated_hooks_with_actual_lef_only_tap(self):
        rc,out=self.run_flow('physical_tap',generated=True);self.assertEqual(rc,0,out[-8000:])
        self.assertIn('MULTI_ROOT_RESULT PASS',out)

    def test_actual_liberty_shared_async_reset_and_data_mutant(self):
        rc,out=self.run_flow('async_reset',generated=True);self.assertEqual(rc,0,out[-8000:])
        self.assertIn('async_control_pins=4',out)
        rc,out=self.run_flow('async_reset_data');self.assertNotEqual(rc,0,out[-8000:])
        self.assertIn('input rst_n has wrong domain',out)

    def test_explicit_related_crossings_keep_both_sta_directions(self):
        rc,out=self.run_flow('related',generated=True);self.assertEqual(rc,0,out[-8000:])
        for pair in ['core -> response','response -> core']:
            self.assertIn('RELATED_PATH '+pair+' max slack=',out)
            self.assertIn('RELATED_PATH '+pair+' min slack=',out)
        for mutant in ['related_wrong_input','related_cut']:
            rc,out=self.run_flow(mutant);self.assertNotEqual(rc,0,out[-8000:]);self.assertIn('OT_MULTI_ROOT',out)

    def test_related_pll_ratio_crossings_keep_both_sta_directions(self):
        rc,out=self.run_flow('related_pll',generated=True);self.assertEqual(rc,0,out[-8000:])
        self.assertIn('OT_ENTRIES DOMAIN response 1111.11',out)
        for pair in ['core -> response','response -> core']:
            self.assertIn('RELATED_PATH '+pair+' max slack=',out)
            self.assertIn('RELATED_PATH '+pair+' min slack=',out)
        rc,out=self.run_flow('related_pll_cut');self.assertNotEqual(rc,0,out[-8000:]);self.assertIn('OT_MULTI_ROOT',out)

    def test_reset_declaration_does_not_waive_or_reclassify_data(self):
        rc,out=self.run_flow('declared_reset');self.assertEqual(rc,0,out[-7000:])
        self.assertIn('OWNERSHIP PASS',out)

    def test_generated_hooks_and_signoff_replay(self):
        rc,out=self.run_flow(generated=True);self.assertEqual(rc,0,out[-7000:])
        self.assertGreaterEqual(out.count('OT_MULTI_ROOT OWNERSHIP PASS'),9)
        self.assertIn('MULTI_ROOT_RESULT PASS',out)

    def test_bad_graph_and_io_declarations_rejected(self):
        for mutant in ['wrong_input','wrong_output','unknown_port','cross_data','extra_alias']:
            with self.subTest(mutant=mutant):
                rc,out=self.run_flow(mutant);self.assertNotEqual(rc,0,out[-6000:]);self.assertIn('OT_MULTI_ROOT',out)

if __name__=='__main__':unittest.main()
