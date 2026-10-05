#!/usr/bin/env python3
"""Measure retained KC8 boundary nets; never reroute or rewrite original evidence.

This is a diagnostic of the historical register harness, not parent signoff.
One SS/FF liberty scene per process annotates the retained extracted SPEF.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TCL = r'''
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(PROBE_CORNER)_*.lib*]] {read_liberty $f}
read_db $::env(PROBE_ODB)
read_sdc $::env(PROBE_SDC)
read_spef $::env(PROBE_SPEF)
set_propagated_clock [all_clocks]
report_units
set selected {}
foreach cell [get_cells *] {
    set name [get_full_name $cell]
    if {[string match {rst_q*} $name]} {lappend selected $cell}
    if {[regexp {^u_l\.q\[([0-9]+)\]} $name -> bit] &&
        ($bit == 0 || ($bit >= 673 && $bit < 705) || $bit >= 748)} {
        lappend selected $cell
    }
}
if {![llength $selected]} {error "Missing retained boundary launch cells"}
foreach cell $selected {
    puts "PROBE_CELL [get_full_name $cell]"
    foreach pin [get_pins -of_objects $cell] {
        if {[get_property $pin direction] == "output"} {
            foreach net [get_nets -of_objects $pin] {
                report_net -digits 6 [get_full_name $net]
            }
        }
    }
}
puts "PROBE_CLOCK_AND_CAPTURE"
report_checks -from $selected -path_delay max -group_path_count 4 -format full_clock_expanded -digits 4
report_checks -from $selected -path_delay min -group_path_count 4 -format full_clock_expanded -digits 4
puts "PROBE_DONE"
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results', type=Path, required=True)
    ap.add_argument('--original-groups', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    res = a.results.resolve()
    a.out.mkdir(parents=True, exist_ok=False)
    artifacts = {f'6_final.{ext}': res / f'6_final.{ext}' for ext in ('odb', 'sdc', 'spef')}
    hashes = {name: sha(p) for name, p in artifacts.items()}
    original = json.loads(a.original_groups.read_text())
    if hashes != original['artifacts_sha256']:
        raise SystemExit('Retained artifacts differ from original groups record')
    sources = ['tools/dsrom_reindex_context_probe.py', 'tools/run_abi3_physical.py',
               'tools/orfs_allcorner_spef.py',
               'rtl/experimental/dsrom_reindex_kc7_20261005/ot_hdc_v41x_idx_kgather_kc7.sv',
               'rtl/experimental/dsrom_reindex_kc7_20261005/ot_hdc_v41x_idx_kgctl_kc7_ctx.sv',
               'rtl/dsrom_sys/integration/ot_hdc_v41x_idx_kgather_ps.sv',
               'rtl/dsrom_sys/integration/ot_dsrom_reindex_chain.sv',
               'rtl/hdc/v41x/ot_hdc_v41x_sel_mdrop.sv']
    record = dict(artifacts_sha256=hashes, source_sha256={p: sha(ROOT / p) for p in sources},
                  parent_qualified=False, new_route=False, corners={})
    script = a.out.resolve() / 'probe.tcl'
    script.write_text(TCL)
    for corner in ('SS', 'FF'):
        cmd = ['docker', 'run', '--rm', '-v', f'{res}:/retained:ro',
               '-v', f'{a.out.resolve()}:/probe:ro', '-e', f'PROBE_CORNER={corner}']
        for ext in ('ODB', 'SDC', 'SPEF'):
            cmd += ['-e', f'PROBE_{ext}=/retained/6_final.{ext.lower()}']
        cmd += ['openroad/orfs:latest', 'bash', '-lc',
                'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; '
                'openroad -exit -no_splash /probe/probe.tcl']
        run = subprocess.run(cmd, capture_output=True, text=True)
        log = run.stdout + run.stderr
        path = a.out / f'{corner.lower()}.log'
        path.write_text(log)
        record['corners'][corner.lower()] = dict(exit=run.returncode, sha256=sha(path),
                                                complete='PROBE_DONE' in log and '[ERROR' not in log)
    record['artifacts_unchanged'] = hashes == {name: sha(p) for name, p in artifacts.items()}
    (a.out / 'record.json').write_text(json.dumps(record, indent=2) + '\n')
    if not record['artifacts_unchanged'] or not all(c['exit'] == 0 and c['complete'] for c in record['corners'].values()):
        raise SystemExit('Boundary diagnostic incomplete; retain failure logs')


if __name__ == '__main__':
    main()
