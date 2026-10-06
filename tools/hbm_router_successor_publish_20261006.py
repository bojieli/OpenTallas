#!/usr/bin/env python3
"""Publish the sole collector's completed evidence without launching any job."""
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
CENTRAL=Path('/home/ubuntu/OpenTallas')
R=Path('results/physical/hbm_die_abstracts_20261006/compute/router_pipeline_r2')
OUT=ROOT/R/'route-r2/terminal'
TOOLS=['tools/hbm_router_successor_collect_20261006.py',
       'tools/hbm_router_successor_publish_20261006.py']

def git(root,*args):
    return subprocess.check_output(['git',*args],cwd=root,text=True).strip()

def main():
    assert ROOT==Path('/home/ubuntu/wt-hbm-router-successor-20261006')
    while not (OUT/'collection.json').is_file():
        time.sleep(30)
    # Audit the terminal raw files with the latest collector implementation.
    spec=importlib.util.spec_from_file_location('actual_collector',ROOT/TOOLS[0])
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    raw=json.loads((OUT/'collection.json').read_text())
    for p,h in raw['sha256'].items():
        assert hashlib.sha256((OUT/p).read_bytes()).hexdigest()==h,p
    # The already-running collector predates the final-netlist exclusion.
    # Keep the original on E1 and its hash, rather than commit a bulk copy.
    bulk='orfs/results/asap7/carson_router_successor/base/6_final.v'
    if bulk in raw['sha256']:
        raw['retained_remote_only_sha256']={bulk:raw['sha256'].pop(bulk)}
        (OUT/bulk).unlink()
        (OUT/'collection.json').write_text(json.dumps(raw,indent=2)+'\n')
    route=json.loads((OUT/'route.json').read_text())
    assert (OUT/'terminal.exit').is_file()
    verdict=module.review(OUT,route)
    (OUT/'verdict.json').write_text(json.dumps(verdict,indent=2)+'\n')
    prep=ROOT/R/'source_preparation.json'
    v=json.loads(prep.read_text())
    v.update(status=verdict['status'],actual_terminal='route-r2/terminal/verdict.json',
             physical_closed=False,parent_qualified=False,route_launch_allowed=False)
    prep.write_text(json.dumps(v,indent=2)+'\n')
    paths=[str(R/'route-r2/terminal'),str(R/'source_preparation.json')]+TOOLS
    git(ROOT,'add','--',*paths)
    git(ROOT,'commit','-m','Collect actual successor routed terminal classes and loaded boundary scope')
    commit=git(ROOT,'rev-parse','HEAD')
    protected=['results/arch/measured_scoreboard/README.md',
               'results/arch/measured_scoreboard/scoreboard.json']
    with Path('/tmp/opentallas-central-main-merge.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        before={p:hashlib.sha256((CENTRAL/p).read_bytes()).hexdigest() for p in protected}
        index={p:git(CENTRAL,'ls-files','-s','--',p) for p in protected}
        git(CENTRAL,'cherry-pick','-X','ours',commit)
        assert before=={p:hashlib.sha256((CENTRAL/p).read_bytes()).hexdigest() for p in protected}
        assert index=={p:git(CENTRAL,'ls-files','-s','--',p) for p in protected}
    git(ROOT,'fetch','origin','main')
    git(ROOT,'merge','-X','ours','origin/main')
    git(ROOT,'push','origin','HEAD:main')
    published=git(ROOT,'rev-parse','HEAD')
    corners=verdict.get('corners',{})
    ss=corners.get('ss',{}).get('metrics_raw',{}).get('OT_WS','UNAVAILABLE')
    ff=corners.get('ff',{}).get('metrics_raw',{}).get('OT_WS','UNAVAILABLE')
    if ss!='UNAVAILABLE':ss=f'{float(ss)*1e12:.6f}ps'
    if ff!='UNAVAILABLE':ff=f'{float(ff)*1e12:.6f}ps'
    line=(f'CARSON REAL successor route-r2 TERMINAL {verdict["status"]} '
          f'native_rc{route["flow_returncode"]} SSsetup{ss}/FFhold{ff} '
          f'actualbufferedutil{verdict.get("actual_buffered_cell_utilization","UNAVAILABLE")} '
          f'MAIN{published} {R}/route-r2/terminal/verdict.json +all native/corner reports '
          'and actualfinalSDC boundary; externalfull73clock/IO conditionalOPEN, parentOPEN. '
          'All source/ODB/SPEF/buildobjects retained E1 route-r2; no route/gold/synth/STA replay, '
          'no new source variant. Actual failing-class/source diagnosis required before successor.\n')
    with Path('/tmp/claude-review-20261003/codex_notes.txt').open('a') as f:
        f.write('\n'+line)
    for thread in ['01a10d79-dbea-74d1-972f-7a8c76a0dae1',
                   '01a10dba-5786-7d01-b636-797f591b5657',
                   '01a10dba-5675-7043-8349-28565e5e1688']:
        subprocess.run(['codex','queue','--thread',thread,'--message',line],check=True)
    print(line,flush=True)

if __name__=='__main__':main()
