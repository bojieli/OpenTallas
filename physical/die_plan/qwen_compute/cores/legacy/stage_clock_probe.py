#!/usr/bin/env python3
"""Stage a reviewed south-spread placement for real CTS/GRT clock probing."""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source');ap.add_argument('out');ap.add_argument('clock_source')
    a=ap.parse_args();src=Path(a.source);out=Path(a.out);cs=Path(a.clock_source)
    if out.exists():raise SystemExit('refuse to overwrite a candidate')
    if json.loads((src/'face_guard.json').read_text()).get('verdict')!='PASS':raise SystemExit('source face guard failed')
    clock_files=['clock_leaf_balance.tcl','clock_grt.tcl','cts_post.tcl','clock_family.tcl','pair_skew.tcl']
    for n in clock_files:
        if not (cs/n).is_file():raise SystemExit(f'clock hook missing before staging: {cs/n}')
    out.mkdir(parents=True)
    subprocess.run(['rsync','-aL','--exclude=run','--exclude=signoff*','--exclude=*.log','--exclude=placed.csv',str(src)+'/',str(out)+'/'],check=True)
    base=next(src.glob('run/results/asap7/*/base'));dst=out/base.relative_to(src);dst.mkdir(parents=True)
    for p in base.iterdir():
        if p.is_file() and (p.name.startswith(('1_','2_','3_')) or p.name=='clock_period.txt'):shutil.copy2(p,dst/p.name)
    if not (dst/'3_place.odb').exists():raise SystemExit('no placed source checkpoint')
    for n in ['objects','logs','reports']:
        d=out/'run'/n/'asap7'/base.parent.name/'base';d.mkdir(parents=True)
        if n=='objects':shutil.copytree(src/'run'/n/'asap7'/base.parent.name/'base',d,dirs_exist_ok=True)
    for n in clock_files:shutil.copy2(cs/n,out/n)
    p=out/'config.mk';s=p.read_text();s=re.sub(r'^export HOLD_SLACK_MARGIN = .*$', 'export HOLD_SLACK_MARGIN = 5',s,flags=re.M)
    s=re.sub(r'^export POST_GLOBAL_ROUTE_TCL = .*$', 'export POST_GLOBAL_ROUTE_TCL = /work/clock_grt.tcl',s,flags=re.M);p.write_text(s)
    (out/'CLOCK_PROBE.json').write_text(json.dumps({'source':str(src),'clock_hook_source':str(cs),'additional_cycles':0,'scope':'CTS+GRT only; bind measured I and TT/FF preflight before DRT'},indent=2)+'\n')


if __name__=='__main__':main()
