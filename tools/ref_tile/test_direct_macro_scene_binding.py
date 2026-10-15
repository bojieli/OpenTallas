"""Actual OpenSTA scene-mapped raw SRAM guard regression.

Run --openroad-probe OUT inside the exact ORFS image, admitted via ot-run.
No path exceptions or substituted scene libraries are used.
"""
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import unittest
import direct_macro_clock_entries as D
import clock_entry_constraints as C
from test_direct_macro_clock_entries import ROOT, MASTER, VIEW, spec


class SourceBinding(unittest.TestCase):
    def test_accessor_source_is_in_consumed_closure(self):
        import source_binding as SB
        files = {'tools/ref_tile/direct_macro_clock_entries.py': b'',
                 'tools/ref_tile/sta_scene_binding.cc': b'// source',
                 'tools/ref_tile/unrelated.cc': b'// unused'}
        used = SB.consumed_closure(files, ['tools/ref_tile/direct_macro_clock_entries.py'], [], re.compile(r'(tools/[^ ]+)'))
        self.assertEqual(used, set(files)-{'tools/ref_tile/unrelated.cc'})

    def test_accessor_source_is_embedded_and_bound(self):
        result = D.load(spec(), ROOT)
        for c in D.CORNERS:
            self.assertIn(result['entries'][0]['corners'][c]['sha256'], result['bindings_tcl'])
        self.assertIn('ot_sta_scene_binding $cellname $libpin', result['bindings_tcl'])
        self.assertNotIn('get_lib_cells -quiet -of_objects', result['bindings_tcl'])
        self.assertIn('accessor ABI/load failed', result['bindings_tcl'])


def probe(out):
    out = Path(out).resolve(); out.mkdir(parents=True, exist_ok=True)
    s = spec(); generated = D.load(s, ROOT)
    (out/'source_manifest.json').write_text(json.dumps(generated['entries'], indent=2)+'\n')
    (out/'probe.v').write_text('module probe(input ca, cb, en, output [545:0] qa,qb);\n' +
        '\n'.join(f'{MASTER} u_{i}(.clk({p}),.r_ce_in(en),.rd_out(q{p[-1]}));'
                  for i,p in enumerate(('ca','cb'))) + '\nendmodule\n')
    original = ROOT/VIEW
    variants = {'missing_arc': ('timing_type : hold_rising', 'timing_type : recovery_rising'),
                'wrong_clock': ('clock : true', 'clock : false'),
                'wrong_source': ('/*', '/* changed source ')}
    # Comment-only mutation keeps semantics intact and must fail source identity.
    for name, (a,b) in variants.items():
        text=(original/f'{MASTER}_ff.lib').read_text()
        text = text+'\n/* source digest mutant */\n' if name=='wrong_source' else text.replace(a,b)
        (out/f'{name}.lib').write_text(text)
    receipts=[]
    cases=['pass','wrong_scene','wrong_cell','missing_arc','wrong_clock','wrong_source','mixed_minmax']
    for case in cases:
        libs={c:str(original/f'{MASTER}_{c}.lib') for c in D.CORNERS}
        if case in variants:libs['ff']=str(out/f'{case}.lib')
        script='read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef\n'
        script+=f'read_lef {{{original}/{MASTER}.lef}}\n'
        script+=''.join(f'read_liberty {{{v}}}\n' for v in libs.values())
        script+=f'read_verilog {{{out}/probe.v}}\nlink_design probe\n'
        for mode in ('tt','ff','ss'):
            script+=f'set_mode {mode}\n'+C.clocks(s,833.333)
            script+='set_propagated_clock [all_clocks]\n'
            script+='set_input_delay 0 -clock core_clk [get_ports en]\nset_output_delay 0 -clock core_clk [all_outputs]\n'
        for c in D.CORNERS:
            if c=='ff' and case=='mixed_minmax':
                script+=f'define_scene FF -mode ff -liberty_min {{{libs["tt"]}}} -liberty_max {{{libs["ff"]}}}\n'
            else:script+=f'define_scene {c.upper()} -mode {c} -liberty {{{libs[c]}}}\n'
        script+=C.BODY[:C.BODY.index('# Match ck_insertion.py')]+generated['bindings_tcl']
        script+='set ::ot_ce_ports {ca cb}\nset ::ot_ce_cts_roots {}\nset ::ot_ce_source_domains {ca core cb core}\nset ::ot_ce_domains {core {clock core_clk}}\n'
        # This fixture targets bindings; clock wire is ideal, not a routed claim.
        script+='set ::ot_ce_require_wire 0\n'
        if case=='wrong_cell':
            script+='set e [lindex $::ot_ce_direct_entries 0];lset e 0 wrong_master;lset ::ot_ce_direct_entries 0 $e\n'
        corners=D.CORNERS if case=='pass' else ('ff',)
        for c in corners:
            scene='TT' if case=='wrong_scene' else c.upper()
            script+=f'set_scene {scene}\nsta::worst_slack_cmd max\n'
            script+=f'set rows [ot_ce_direct_rows {c}]\n'
            script+='if {[llength $rows]!=2} {error "missing raw SRAM rows"}\n'
            script+=f'puts SCENE_BINDING_PASS_{c}\n'
        script+='exit\n'
        path=out/f'{case}.tcl';path.write_text(script)
        run=subprocess.run([os.environ.get('OPENROAD','openroad'),'-no_init','-exit',str(path)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        (out/f'{case}.log').write_text(run.stdout)
        ok=run.returncode==0 and all(f'SCENE_BINDING_PASS_{c}' in run.stdout for c in corners)
        if ok != (case=='pass'):raise RuntimeError(f'{case}: unexpected admission\n{run.stdout[-3000:]}')
        if case!='pass' and 'OT_DIRECT_MACRO:' not in run.stdout:raise RuntimeError(f'{case}: unrelated failure\n{run.stdout[-3000:]}')
        receipts.append(dict(case=case,returncode=run.returncode,expected_admitted=case=='pass'))
    (out/'receipt.json').write_text(json.dumps(receipts,indent=2)+'\n')
    print('ACTUAL_SCENE_BINDING_SUITE_PASS TT/FF/SS and six mutants')


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--openroad-probe':probe(sys.argv[2])
    else:unittest.main()
