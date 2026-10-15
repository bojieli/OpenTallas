"""Actual OpenSTA multi-scene direct-SRAM Liberty association regression.
Run --probe OUT inside the pinned OpenROAD image via ot-run.
The explicit RC fixture is a tool regression, not routed-layout evidence.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import direct_macro_clock_entries as D
import clock_entry_constraints as C

ROOT = Path(__file__).resolve().parents[2]
MASTER = 'ot_sram_1r1w_32x546_m1'
VIEW = ROOT / 'physical/asap7_memory_macros' / MASTER


def probe(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    spec = dict(clock='entries', clock_ports=['ca', 'cb'], clock_port='ca',
                kind='cluster', children=[], macros=[dict(view=str(VIEW.relative_to(ROOT)),
                inst=f'u_{i}', clock_entry=dict(port=p, pin='clk', reference='raw_liberty_clock_pin'))
                for i, p in enumerate(('ca','cb'))])
    generated = D.load(spec, ROOT)
    (out/'clock.sdc').write_text(C.clocks(spec, 833.333))
    (out/'probe.v').write_text('module probe(input ca, cb, en, output [545:0] qa,qb);\n' +
        '\n'.join(f'{MASTER} u_{i}(.clk({p}),.r_ce_in(en),.rd_out(q{p[-1]}));'
            for i,p in enumerate(('ca','cb'))) + '\nendmodule\n')
    cases = ['positive', 'reread', 'wrong_corner', 'wrong_scene_library',
             'missing_library', 'unobserved_scene', 'redefined_scene',
             'mixed_min_max', 'duplicate_master']
    receipts = []
    for case in cases:
        script = 'read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef\n'
        script += f'read_lef {{{VIEW}/{MASTER}.lef}}\n'
        for corner in ('tt','ff'):
            script += f'read_liberty {{{VIEW}/{MASTER}_{corner}.lib}}\n'
        script += f'read_verilog {{{out}/probe.v}}\nlink_design probe\n'
        script += f'read_sdc -mode ss {{{out}/clock.sdc}}\nread_sdc -mode ff {{{out}/clock.sdc}}\n'
        definitions = f'define_scene TC -mode ss -liberty {MASTER}_tt\n'
        bindings = f'{MASTER}_tt' if case == 'wrong_scene_library' else f'{MASTER}_ff'
        if case == 'duplicate_master': bindings = f'{{{MASTER}_tt {MASTER}_ff}}'
        definitions += (f'define_scene BC -mode ff -liberty_min {MASTER}_ff -liberty_max {MASTER}_tt\n'
                        if case == 'mixed_min_max' else f'define_scene BC -mode ff -liberty {bindings}\n')
        if case == 'unobserved_scene': script += definitions
        script += generated['bindings_tcl']
        if case == 'reread':
            script += generated['bindings_tcl']
            script += 'if {[llength [trace info execution ::sta::define_scene_cmd]] != 1} {error "trace installed twice"}\n'
        if case != 'unobserved_scene': script += definitions
        if case == 'redefined_scene': script += f'define_scene BC -mode ff -liberty {MASTER}_tt\n'
        if case == 'missing_library': script += 'dict set ::ot_ce_direct_scene_libraries BC {{not_loaded} {not_loaded}}\n'
        script += 'set_mode ff\nset_scene BC\nset ::ot_ioref_scene BC\n'
        script += 'set actual [get_full_name [lindex [get_lib_cells -of_objects [get_cells u_0]] 0]]\n'
        script += f'if {{$actual ne "{MASTER}_tt/{MASTER}"}} {{error "fixture did not reproduce first-linked TT master"}}\n'
        script += f'set expected_corner {"tt" if case == "wrong_corner" else "ff"}\n'
        script += 'foreach entry $::ot_ce_direct_entries {\n'
        script += ' lassign $entry master pattern name pin libraries\n'
        script += ' ot_ce_direct_actual_libcell [lindex [get_cells $pattern] 0] $master $libraries $expected_corner\n}\n'
        script += f'puts SCENE_PROBE_PASS_{case}\nexit\n'
        path = out/f'{case}.tcl'; path.write_text(script)
        result = subprocess.run([os.environ.get('OPENROAD','openroad'),'-exit',str(path)],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out/f'{case}.log').write_text(result.stdout)
        success = result.returncode == 0 and f'SCENE_PROBE_PASS_{case}' in result.stdout
        expected = case in ('positive','reread')
        if success != expected or (not expected and 'OT_DIRECT_MACRO:' not in result.stdout):
            raise RuntimeError(f'{case}: unexpected result {result.returncode}\n{result.stdout[-3500:]}')
        receipts.append(dict(case=case, returncode=result.returncode, expected_pass=expected,
                             log_sha256=hashlib.sha256(result.stdout.encode()).hexdigest()))
    (out/'receipt.json').write_text(json.dumps(dict(cases=receipts,
        source_sha256=hashlib.sha256(Path(D.__file__).read_bytes()).hexdigest(),
        source_libraries={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in VIEW.glob('*.lib')},
        qualification='Actual OpenSTA scene association test; fixture only, no route/native-parent closure'), indent=2)+'\n')
    print('SCENE_PROBE_SUITE_PASS positive/reread and seven fail-closed mutants')


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--probe': raise SystemExit('usage: --probe OUT')
    probe(sys.argv[2])
