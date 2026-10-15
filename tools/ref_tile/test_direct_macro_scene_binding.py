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
    # holdmm_*: tools/orfs_hold_mm.tcl's FF sign-off SDC context. Scenes TC (mode ss) and
    # BC (mode ff) exist, set_mode ff is active and the shim sets ::ot_ioref_scene BC,
    # and ot_mm_sync never calls set_scene: set_mode ff alone must select scene BC.
    # holdmm_bc_tt_library: same context, BC wrongly bound to the TT Liberty.
    holdmm=['holdmm_bc','holdmm_bc_tt_library']
    # default_*: the multi-mode route's synthesis SDC read (read_liberty TT then FF, no scene defined,
    # read_sdc -mode ss): the unscened default binds max TT / min FF. Admitted pre-CTS only.
    default=['default_prects','default_postcts']
    cases=['pass','wrong_scene','wrong_cell','missing_arc','wrong_clock','wrong_source','mixed_minmax']+holdmm+default
    for case in cases:
        libs={c:str(original/f'{MASTER}_{c}.lib') for c in D.CORNERS}
        if case in variants:libs['ff']=str(out/f'{case}.lib')
        script='read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef\n'
        script+=f'read_lef {{{original}/{MASTER}.lef}}\n'
        script+=''.join(f'read_liberty {{{v}}}\n' for v in ((libs['tt'],libs['ff']) if case in default else libs.values()))
        script+=f'read_verilog {{{out}/probe.v}}\nlink_design probe\n'
        for mode in (('ss',) if case in default else ('tt','ff','ss')):
            script+=f'set_mode {mode}\n'+C.clocks(s,833.333)
            script+='set_propagated_clock [all_clocks]\n'
            script+='set_input_delay 0 -clock core_clk [get_ports en]\nset_output_delay 0 -clock core_clk [all_outputs]\n'
        if case in holdmm:
            script+=f'define_scene TC -mode ss -liberty {{{libs["tt"]}}}\n'
            script+=f'define_scene BC -mode ff -liberty {{{libs["tt" if case=="holdmm_bc_tt_library" else "ff"]}}}\n'
        for c in (() if case in holdmm+default else D.CORNERS):
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
        if case in default:
            script+=f'set ::ot_ref_pre_cts {int(case=="default_prects")}\n'
            script+='if {[get_property [sta::cmd_scene] name] ne "default"} {error "fixture: expected the unscened default"}\n'
            script+='set rows [ot_ce_direct_rows tt]\nif {[llength $rows]!=2} {error "missing raw SRAM rows"}\nputs SCENE_BINDING_PASS_tt\nexit\n'
            corners=()
        if case in holdmm:
            script+='set_scene TC\nsta::worst_slack_cmd max\nset_mode ff\n'
            script+='set ::ot_ioref_scene BC\n'
            script+='if {[get_property [sta::cmd_scene] name] ne "BC"} {error "OT_DIRECT_MACRO: set_mode ff did not select scene BC"}\n'
            script+='puts "HOLDMM_CMD_SCENE [get_property [sta::cmd_scene] name]"\n'
            script+='set rows [ot_ce_direct_rows ff]\n'
            script+='if {[llength $rows]!=2} {error "missing raw SRAM rows"}\n'
            script+='puts SCENE_BINDING_PASS_ff\nexit\n'
            corners=()
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
        expect=case in ('pass','holdmm_bc','default_prects')
        ok=run.returncode==0 and all(f'SCENE_BINDING_PASS_{c}' in run.stdout for c in (corners or (('tt',) if case in default else ('ff',))))
        if ok != expect:raise RuntimeError(f'{case}: unexpected admission\n{run.stdout[-3000:]}')
        if not expect and 'OT_DIRECT_MACRO:' not in run.stdout and 'OT_ENTRIES:' not in run.stdout:raise RuntimeError(f'{case}: unrelated failure\n{run.stdout[-3000:]}')
        receipts.append(dict(case=case,returncode=run.returncode,expected_admitted=expect))
    (out/'receipt.json').write_text(json.dumps(receipts,indent=2)+'\n')
    print('ACTUAL_SCENE_BINDING_SUITE_PASS TT/FF/SS, hold-mm BC context, pre-CTS default scene and eight mutants')


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--openroad-probe':probe(sys.argv[2])
    else:unittest.main()
