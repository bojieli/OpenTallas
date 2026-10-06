#!/usr/bin/env python3
"""Read-only W5 endpoint/clock audit; checkpoint evidence, never qualification."""
import argparse, csv, hashlib, json, re
from pathlib import Path
import signoff_analysis as so

ROOT = Path(__file__).resolve().parents[1]

def summarize(work, corner):
    # OpenSTA set_units checks library compatibility; it does not override the
    # linked library's report scale. Preserve raw reports and convert explicitly.
    log = (work/('session_'+corner+'.log')).read_text()
    units = re.search(r'^ time 1(ns|ps|s)$', log, re.M)
    if not units:
        raise ValueError('Native report time units missing')
    scale = {'ns':1000., 'ps':1., 's':1e12}[units[1]]
    with (work/corner/'clock_terminals.tsv').open() as f:
        terms=list(csv.DictReader(f,delimiter='\t'))
    clock_pins={r['pin'] for r in terms}
    with (work/corner/'gate_macro_terminals.tsv').open() as f:
        clock_pins.update(r['pin'] for r in csv.DictReader(f,delimiter='\t')
                          if r['pin'].rsplit('/',1)[-1] in {'CLK','clk'})
    classes={}; seen=set(); excluded=0; duplicates=0
    with (work/corner/'endpoints.tsv').open() as f:
        for r in csv.DictReader(f,delimiter='\t'):
            if r['endpoint'] in clock_pins:
                excluded+=1; continue
            identity=(r['endpoint'],r['mode'])
            if identity in seen:
                duplicates+=1; continue
            seen.add(identity)
            key=r['class']+'.'+r['mode']
            q=classes.setdefault(key,dict(endpoints=0,violators=0,missing_paths=0,
                functional_missing_paths=0,worst_ps=None,worst_endpoint=None))
            q['endpoints']+=1
            raw=r.get('slack_native',r.get('slack_ps'))
            if raw=='Inf':
                q['missing_paths']+=1
                q['functional_missing_paths']+=int(r['startpoint_count'])>0
            else:
                slack=float(raw)*scale; q['violators']+=slack<0
                if q['worst_ps'] is None or slack<q['worst_ps']:
                    q.update(worst_ps=slack,worst_endpoint=r['endpoint'])
    return dict(native_time_unit=units[1],native_to_ps=scale,classes=classes,
        clock_terminals=len(terms),excluded_clock_graph_rows=excluded,
        duplicate_endpoint_rows=duplicates,
        terminals_without_clock=[r['pin'] for r in terms if not r['clocks']])

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--routed', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--stage', choices=['cts', 'final'], default='cts')
    p.add_argument('--summarize-existing', action='store_true')
    a = p.parse_args()
    if a.summarize_existing:
        summary={c:summarize(a.work,c) for c in ['SS','FF']}
        (a.work/'audit_normalized.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(json.dumps(summary,indent=2)); return
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
        metadata['corners'][corner]=summarize(work,corner)
        (work/'audit.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata['corners'],indent=2))

if __name__=='__main__': main()
