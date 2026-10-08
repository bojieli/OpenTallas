#!/usr/bin/env python3
"""Export a signed-off rb station as a die view: abstract LEF + SS/FF ETM Liberty.

Uses the routed 6_final.odb, RCX SPEF and the measured-insertion signoff SDC
(signoff.py). Output: <run>/view/{<cell>.lef, <cell>_ss.lib, <cell>_ff.lib, view.json}.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path

TCL = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(LIBC)_*.lib*]] { read_liberty $f }
read_db $::env(ODB)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
if {$::env(LEF) != ""} { write_abstract_lef -bloat_occupied_layers $::env(LEF) }
write_timing_model -library_name $::env(CELL)_$::env(LIBC) -cell_name $::env(CELL) $::env(LIB)
puts EXPORT_DONE
"""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--cell', required=True); a = ap.parse_args()
    run = a.run.resolve()
    odb = next(run.rglob('results/asap7/*/base/6_final.odb'))
    case = next(p for p in odb.parents if (p/'config.mk').is_file())
    view = case/'view'; view.mkdir(exist_ok=True)
    (case/'tk_export.tcl').write_text(TCL)
    rel = lambda q: '/work/'+str(Path(q).relative_to(case))
    logs = {}
    for libc in ('SS', 'FF'):
        lef = view/f'{a.cell}.lef' if libc == 'SS' else ''
        lib = view/f'{a.cell}_{libc.lower()}.lib'
        cmd = ['docker', 'run', '--rm', '-v', f'{case}:/work', '-e', f'LIBC={libc}', '-e', f'ODB={rel(odb)}',
               '-e', f'SDC={rel(case/"signoff.sdc")}', '-e', f'SPEF={rel(odb.parent/"6_final.spef")}',
               '-e', f'LEF={rel(lef) if lef else ""}', '-e', f'LIB={rel(lib)}', '-e', f'CELL={a.cell}',
               'openroad/orfs:asap7lock', 'bash', '-lc',
               'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /work/tk_export.tcl']
        p = subprocess.run(cmd, capture_output=True, text=True)
        logs[libc] = p.stdout[-2000:]+p.stderr[-2000:]
        assert 'EXPORT_DONE' in p.stdout, logs[libc]
    files = sorted(view.glob(f'{a.cell}*'))
    rec = dict(cell=a.cell, odb=str(odb), signoff=json.loads((run/'signoff.json').read_text())['accept'],
               files={f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
    (view/'view.json').write_text(json.dumps(rec, indent=2)+'\n')
    print(json.dumps(rec, indent=2))


if __name__ == '__main__':
    main()
