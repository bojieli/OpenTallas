"""Leaf hybrid clocks retain native ownership and actual raw-memory guards."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ref_tile as RT
import clock_entry_constraints as CE
from test_direct_macro_clock_entries import MASTER, VIEW

ROOT = Path(__file__).resolve().parents[3]


def spec():
    return dict(name='tile_hybrid_raw', top='top', kind='tile', sources=[],
        clock='hybrid_entries', clock_port='ck', clock_ports=['ck','rom'],
        clock_cts_roots=['ck'], pins={'W':['ck','rom','d','en'],'E':['q','qa']},
        clock_data_paths='related_same_frequency',
        clock_relationship=dict(kind='same_pll_fixed_phase',ratio=[1,1],phase_ps=0),
        clock_entry_domains=dict(core=dict(ratio=[1,1],ports=['ck'],inputs=['d'],outputs=['q']),
            memory=dict(ratio=[1,1],ports=['rom'],inputs=['en'],outputs=['qa'])),
        macros=[dict(view=VIEW, inst='u_m', count=1,
            clock_entry=dict(port='rom',pin='clk',reference='raw_liberty_clock_pin'))])


class Schema(unittest.TestCase):
    def load(self,s):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'spec.json';p.write_text(json.dumps(s))
            return RT.load_spec(str(p))

    def test_tile_explicit_raw_coverage_and_leaf_ownership(self):
        s=self.load(spec())
        text=CE.generate(s,ROOT)
        self.assertIn('set ::ot_ce_leaf_roots 1',text)
        self.assertIn('ot_ce_leaf_ownership $covered_in $covered_out',text)
        self.assertIn('foreach root $::ot_ce_ports',text)
        self.assertNotIn('set_false_path',text)
        self.assertEqual(RT.layer_contract(s, None)['pg_layer'],'M5')

    def test_refuse_missing_raw_owner_and_custom_hooks(self):
        for kind in ('missing','custom','children','missing_domain','wildcard'):
            s=spec()
            if kind=='missing':s['macros'][0].pop('clock_entry')
            if kind=='custom':s['boundary_tcl']=['anything.tcl']
            if kind=='children':s['children']=[dict(view='unproved')]
            if kind=='missing_domain':s.pop('clock_entry_domains')
            if kind=='wildcard':s['clock_entry_domains']['core']['inputs']=['*']
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.load(s)


def probe(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    receipts=[]
    for case in ('pass','macro_on_cts','std_on_raw','wrong_input_domain','wrong_scene'):
        s=spec()
        if case=='wrong_input_domain':
            s['clock_entry_domains']['core']['inputs']=['en']
            s['clock_entry_domains']['memory']['inputs']=['d']
        cells='\n'.join(f'DFFHQNx1_ASAP7_75t_R r{i}(.CLK({"rom" if case=="std_on_raw" and i==0 else "ck"}),.D(d),.QN(q{i}));' for i in range(16))
        (out/'t.v').write_text('module top(input ck,rom,d,en,output q,output [545:0] qa);\n'+cells+
            f'\n{MASTER} u_m(.clk({"ck" if case=="macro_on_cts" else "rom"}),.r_ce_in(en),.rd_out(qa));\nassign q=q0;endmodule\n')
        (out/'clocks.tcl').write_text(CE.clocks(s,833.333))
        (out/'entries.tcl').write_text('set ::ot_ce_require_wire 1\n'+CE.generate(s,ROOT))
        libcorner='ff' if case=='wrong_scene' else 'tt'
        text=f'''
set_thread_count 2
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef {{{ROOT/VIEW/ (MASTER+'.lef')}}}
foreach l [glob $P/lib/NLDM/*RVT_TT*] {{read_liberty $l}}
read_liberty {{{ROOT/VIEW/ (MASTER+'_'+libcorner+'.lib')}}}
read_verilog {{{out/'t.v'}}}
link_design top
initialize_floorplan -die_area {{0 0 300 200}} -core_area {{5.4 5.4 294.6 194.4}} -site asap7sc7p5t
source $P/openRoad/make_tracks.tcl
place_pins -hor_layers M4 -ver_layers M5
source {{{out/'clocks.tcl'}}}
source $P/setRC.tcl
set u [[ord::get_db_block] getDbUnitsPerMicron]
set k 0
foreach i [[ord::get_db_block] getInsts] {{
  if {{[$i getName] eq "u_m"}} {{$i setLocation [expr {{100*$u}}] [expr {{90*$u}}];$i setPlacementStatus FIRM}} else {{
    $i setLocation [expr {{(15+12*($k%4))*$u}}] [expr {{(15+12*($k/4))*$u}}];$i setPlacementStatus PLACED;incr k
  }}
}}
detailed_placement
set ::ot_ce_cts_roots {{ck}}
source /src/physical/common_flow/clock_entries.tcl
set_propagated_clock [get_clocks ot_entry_*]
clock_tree_synthesis -sink_clustering_enable -buf_list BUFx4_ASAP7_75t_R -root_buf BUFx4_ASAP7_75t_R
estimate_parasitics -placement
set ::ot_ce_corner tt
source {{{out/'entries.tcl'}}}
puts TILE_HYBRID_RAW_PASS
'''
        p=out/f'{case}.tcl';p.write_text(text)
        run=subprocess.run([os.environ.get('OPENROAD','openroad'),'-no_init','-exit',str(p)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=120)
        (out/f'{case}.log').write_text(run.stdout)
        ok=run.returncode==0 and 'TILE_HYBRID_RAW_PASS' in run.stdout
        if ok!=(case=='pass'):raise RuntimeError(f'{case}: unexpected result\n{run.stdout[-7000:]}')
        if case!='pass' and not any(x in run.stdout for x in ('OT_HYBRID:','OT_ENTRIES:','OT_DIRECT_MACRO:','OT_MULTI_ROOT:')):
            raise RuntimeError(f'{case}: unrelated failure\n{run.stdout[-3000:]}')
        receipts.append(dict(case=case,rc=run.returncode,expected_pass=case=='pass'))
    (out/'receipt.json').write_text(json.dumps(receipts,indent=2)+'\n')
    print('TILE_HYBRID_RAW_SUITE_PASS')


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--openroad-probe':probe(sys.argv[2])
    else:unittest.main()
