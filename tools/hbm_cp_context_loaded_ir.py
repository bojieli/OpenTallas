#!/usr/bin/env python3
"""Loaded SS/FF child-grid analysis of the retained CP route; vectorless activity."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import signoff_analysis as analysis


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--orfs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    results = analysis.find_results_dir(args.orfs).resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    record = dict(schema='hbm.cp.context.loaded-ir.v1',
        inputs={n: sha(results/n) for n in ('6_final.odb','6_final.sdc','6_final.spef')},
        activity='OpenSTA vectorless input activity 0.1, propagated; clocks from actual retained SDC',
        source='Ideal supply at existing child PG boundary pins; parent-grid drop excluded',
        grid_rebuilt=False, source_phase_ps=0, setup_ps=60, hold_ps=25,
        workload_peak_qualified=False, adopted=False, corners={})
    for corner in ('SS','FF'):
        script = analysis.session_script('/cp_results', '/cp_output/'+corner,
            corner, stages=('power',), ir_sources=('PINS',), derate=0)
        # Actual extracted RC deck is shared by SS/FF; each standalone session
        # loads that corner's libraries and annotates the routed SPEF directly.
        script = script.replace('set_cmd_units -time ns -power W',
            'set_clock_latency 0 [all_clocks]\nset_propagated_clock [all_clocks]\n'
            'set_cmd_units -time ns -power W')
        path = output/f'{corner}.tcl'
        path.write_text(script)
        command = ['docker','run','--rm','-v',str(results)+':/cp_results:ro',
            '-v',str(output)+':/cp_output',analysis.IMAGE,
            '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',
            '-threads','1','-no_init','-exit','/cp_output/'+path.name]
        proc = subprocess.run(command, capture_output=True, text=True)
        text = proc.stdout+proc.stderr
        (output/f'{corner}.log').write_text(text)
        parsed = analysis.parse_session(text)
        power = parsed.get('power.total.total_w')
        rails = parsed['ir']
        valid = (proc.returncode == 0 and '[ERROR' not in text and
            isinstance(power, (int,float)) and power > 0 and
            {r.get('net') for r in rails} == {'VDD','VSS'} and
            all(isinstance(r.get('worst_ir_drop_v'),(int,float)) for r in rails))
        record['corners'][corner] = dict(exit=proc.returncode,
            nonzero_loaded_analysis_complete=valid, total_power_w=power,
            rails=rails, raw_log=str(output/f'{corner}.log'))
        (output/'loaded_ir.json').write_text(json.dumps(record,indent=2)+'\n')
        if not valid:
            raise RuntimeError('Incomplete loaded IR; preserve '+str(output/f'{corner}.log'))
    print(json.dumps(record,indent=2))


if __name__ == '__main__':
    main()
