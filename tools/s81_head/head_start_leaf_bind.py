#!/usr/bin/env python3
"""Bind HEAD partition START leaves while retaining physical clock-region table."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'die_plan'))
import count_align_bind as C
from head_start_leaf_frames import annotate

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('ca_plan');a.add_argument('--table',required=True);a.add_argument('--regions',required=True);a.add_argument('--die',required=True);a.add_argument('--out',required=True);a=a.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    table=json.load(open(a.table));mapping=json.load(open(a.regions))['part_region']
    b=C.bind(json.load(open(a.ca_plan)),parts=C.table_parts(table))
    v=C.verify(b)
    if v['identity_and_loop_errors'] or v['sim_window_violations']:raise ValueError(v)
    t=annotate(b,table,mapping)
    st=C.strap_ties(t['count_aligned'],json.load(open(a.die)))
    for name,data in [('bind.json',b),('regions_ca.json',t),('straps.json',st),('verify.json',v)]:
        (out/name).write_text(json.dumps(data,indent=1)+'\n')
    print(json.dumps(dict(verify=v,straps=st['summary'],relay=C.relay_summary(b))))
if __name__=='__main__':main()
