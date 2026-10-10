#!/usr/bin/env python3
"""Commit a completed exact gate and queue only the eight modeled reticle-fit BF jobs.

This producer performs no PNR itself. The closure loop admits every route against
actual host capacity. Run in its own clean pinned worktree; retain until DONE.
"""
import argparse, hashlib, json, pathlib, subprocess, time

CASES = ('mutant_dp','mutant_recut','mutant_pinlat','mutant_tcg','mutant_xst','mutant_fxst')


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs)


def publish(root, inbox, state):
    expected = json.loads((root/'tools/s81/bf_compact_job_templates/source_hashes.json').read_text())
    for relative, digest in expected.items():
        assert hashlib.sha256((root/relative).read_bytes()).hexdigest() == digest, relative
    for label in ('220','242'):
        d=json.loads((root/f'results/rtl/s81_bf_compact_20261010/reticle/compact{label}_legal.json').read_text())
        assert d['variant']['die_um']==[33000.,26000.] and d['variant']['pairs']==1792
        assert d['legality_python']['overlaps']==d['legality_python']['outside']==d['generated_pin_clashes']==0
    remote='/srv/opentallas-scratch2/scratch/codex/bf-tcg-pinlat-c8a5b4352'
    result=run(['ssh','-o','ControlPath=none','-o','ConnectTimeout=15','ot-epyc3',
                f'test -s {remote}/compact-bench.rc && cat {remote}/compact-bench/terminal.json && echo && cat {remote}/compact-bench.rc'],timeout=45)
    rows=result.stdout.strip().splitlines(); assert rows[-1]=='rc=0'
    proof=json.loads('\n'.join(rows[:-1])); assert proof['pass'] and proof['source_commit'].startswith('c8a5b4352')
    assert proof['cases']['positive']['ok']
    assert all(proof['cases'][k]['ok'] and any('DIFF' in m for m in proof['cases'][k]['markers']) for k in CASES)
    evidence=root/'results/rtl/s81_bf_compact_20261010/bench';evidence.mkdir(parents=True,exist_ok=True)
    full=evidence/'full.json'
    if full.exists(): assert json.loads(full.read_text())==proof, 'immutable exact proof differs'
    else: full.write_text(json.dumps(proof,indent=2)+'\n')
    manifest=evidence/'manifest.json'
    manifest.write_text(json.dumps(dict(source_commit='c8a5b43521238462656bf9583bd30ad78d3be660',
        source_hashes=expected,gate='positive exact + six true DIFF mutants',
        mechanism='native HCOL1/PINLAT1 full pair; generated front byte-identical after regeneration',
        rows=456,value_assertions=912,partial_added_edges_vs_full948=1,
        measured_lag_ns=dict(min=5.831,max=14.994,mean=9.090),physical_qualified=False),indent=2)+'\n')
    branch=run(['git','branch','--show-current'],cwd=root).stdout.strip()
    assert branch=='codex/bf-tcg-pinlat-20261010'
    names=[str(p.relative_to(root)) for p in (full,manifest)]
    run(['git','add','--sparse',*names],cwd=root)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=root).returncode:
        run(['git','commit','-m','Validate compact full BF HCOL plus PINLAT exact gate and six true DIFF mutants'],cwd=root)
    gate_file=state/'gate_source_commit'
    if gate_file.exists(): gate_commit=gate_file.read_text().strip()
    else:
        gate_commit=run(['git','rev-parse','HEAD'],cwd=root).stdout.strip();gate_file.write_text(gate_commit+'\n')
    specs=[]
    for template in sorted((root/'tools/s81/bf_compact_job_templates').glob('bfh_*.json')):
        d=json.loads(template.read_text());d['source']['commit']=gate_commit
        p=root/'tools/closure_loop/jobs'/f"{d['name']}.json"
        if p.exists(): assert json.loads(p.read_text())==d, 'immutable queued spec differs'
        else: p.write_text(json.dumps(d,indent=2)+'\n')
        specs.append(p)
    run(['git','add',*[str(p.relative_to(root)) for p in specs]],cwd=root)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=root).returncode:
        run(['git','commit','-m','Queue eight exact gated reticle-fit BF hardened column and front variants'],cwd=root)
    run(['git','push','origin',branch],cwd=root,timeout=120)
    inbox.mkdir(parents=True,exist_ok=True)
    for p in specs:
        dst=inbox/p.name
        if dst.exists(): assert dst.read_bytes()==p.read_bytes(), 'existing inbox spec differs'
        else:
            temporary=inbox/(p.name+'.tmp');temporary.write_bytes(p.read_bytes());temporary.replace(dst)
    (state/'DONE.json').write_text(json.dumps(dict(gate_commit=gate_commit,jobs=[p.stem for p in specs],
        source_pinned=True,admission='closure loop host guard',physical_qualified=False),indent=2)+'\n')
    print('QUEUED',len(specs),'gate source',gate_commit,flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=pathlib.Path,required=True)
    ap.add_argument('--inbox',type=pathlib.Path,required=True);ap.add_argument('--state',type=pathlib.Path,required=True)
    a=ap.parse_args();a.state.mkdir(parents=True,exist_ok=True)
    while not (a.state/'DONE.json').exists():
        try: publish(a.root,a.inbox,a.state)
        except Exception as error: print(time.strftime('%Y-%m-%d %H:%M:%S'),repr(error),flush=True)
        if not (a.state/'DONE.json').exists(): time.sleep(60)

if __name__=='__main__':main()
