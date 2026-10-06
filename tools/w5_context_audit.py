#!/usr/bin/env python3
"""Read-only W5 endpoint/clock audit; checkpoint evidence, never qualification."""
import argparse, csv, hashlib, json
from pathlib import Path
import signoff_analysis as so

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--routed', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--stage', choices=['cts', 'final'], default='cts')
    a = p.parse_args()
    res = so.find_results_dir(a.routed, a.stage).resolve()
    work = a.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    pins = {s: hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in
            ['tools/w5_context_audit.py', 'tools/w5_context_audit.tcl',
             'tools/signoff_analysis.py', 'tools/run_abi3_physical.py', 'tools/orfs_allcorner_spef.py']}
    metadata = dict(stage=a.stage, qualification=False, energy_credit=False,
                    parasitics='placement estimated' if a.stage=='cts' else 'routed SPEF',
                    source_pins=pins, corners={})
    metadata['checkpoint'] = {n: so.sha256_file(res/n) for n in so.STAGE_FILES[a.stage] if n}
    for corner in ['SS', 'FF']:
        libs = so.macro_libs(so.block_macros(res), corner)
        mounts = {str(res): '/so_res:ro', str(work): '/so_out',
                  str(so.MACRO_DIR.resolve()): so.MACRO_MOUNT+':ro'}
        script = so.session_script('/so_res', '/so_out/'+corner, corner, stage=a.stage,
                                   stages=(), extra_libs=[c for _, c in libs])
        script += '\nset_thread_count 4\n'+(ROOT/'tools/w5_context_audit.tcl').read_text()
        (work/('audit_'+corner+'.tcl')).write_text(script)
        log = so.run_session(script, mounts, work/('session_'+corner+'.log'), timeout_s=None)
        assert 'W5_ENDPOINT_AUDIT_COMPLETE' in log, 'Incomplete audit; raw failure preserved'
        classes = {}
        with (work/corner/'endpoints.tsv').open() as f:
            for r in csv.DictReader(f, delimiter='\t'):
                key=r['class']+'.'+r['mode']
                q=classes.setdefault(key, dict(endpoints=0,violators=0,missing_paths=0,functional_missing_paths=0,worst_ps=None,worst_endpoint=None))
                q['endpoints']+=1
                if r['slack_ps']=='Inf':
                    q['missing_paths']+=1
                    q['functional_missing_paths']+=int(r['startpoint_count'])>0
                else:
                    slack=float(r['slack_ps']);q['violators']+=slack<0
                    if q['worst_ps'] is None or slack<q['worst_ps']:
                        q.update(worst_ps=slack,worst_endpoint=r['endpoint'])
        with (work/corner/'clock_terminals.tsv').open() as f:
            terms=list(csv.DictReader(f,delimiter='\t'))
        metadata['corners'][corner]=dict(classes=classes,clock_terminals=len(terms),
                                       terminals_without_clock=[r['pin'] for r in terms if not r['clocks']])
        (work/'audit.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata['corners'],indent=2))

if __name__=='__main__': main()
