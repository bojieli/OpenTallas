#!/usr/bin/env python3
"""Require real class masters and complete native bindings for every emitted lane."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qwen_split import fwd_lane_classes as C
from qwen_tp8.bind_real import die_ports


def audit(die,bind):
    ports,count=die_ports(die)
    failures=[];instances=0;used=[]
    for master in sorted(count):
        if not master.startswith(tuple(f'qfd_{f}_' for f in C.FAMS+C.RST_FAMS)):continue
        instances+=count[master];used.append(master)
        try: row=C.classify(master)
        except SystemExit as ex:
            failures.append(f'{master}: unsupported width: {ex}');continue
        if row is None or row['cls']!=master:
            failures.append(f'{master}: source does not emit a canonical closed class');continue
        for p in ('a','b'):
            if ports[master].get(p)!=row['class_bits']:
                failures.append(f'{master}.{p}: emitted width {ports[master].get(p)} != class {row["class_bits"]}')
        r=bind.get('masters_detail',{}).get(master,{})
        if not r.get('bound'):
            failures.append(f'{master}: no native binding ({r.get("reason","missing bind row")})')
        if r.get('instances')!=count[master]:failures.append(f'{master}: binding instance count mismatch')
        if r.get('inputs_without_die_net'):failures.append(f'{master}: open inputs {r["inputs_without_die_net"]}')
        if set(r.get('libs',{}))!={'tt','ff','ss'}:failures.append(f'{master}: native TT/FF/SS views incomplete')
        if not r.get('insertion'):failures.append(f'{master}: native insertion metadata missing')
    if not instances:failures.append('no forwarded lane instances: cannot certify class binding')
    return dict(schema='opentallas.qwen.fwd-class-bind.v1',verdict='FAIL' if failures else 'PASS',
                lane_instances=instances,class_masters=used,unbound_or_invalid=len(failures),failures=failures)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--die',required=True,type=Path);ap.add_argument('--bind',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    r=audit(a.die,json.loads(a.bind.read_text()));a.out.write_text(json.dumps(r,indent=1)+'\n')
    print(f'FWD_CLASS_BIND {r["verdict"]} instances={r["lane_instances"]} classes={len(r["class_masters"])} failures={len(r["failures"])}')
    return int(r['verdict']!='PASS')
if __name__=='__main__':raise SystemExit(main())
