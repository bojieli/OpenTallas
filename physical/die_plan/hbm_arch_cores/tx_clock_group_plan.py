#!/usr/bin/env python3
"""Exact TX chain membership + compact guides for a NEW native clock form.
Input is the actual current source's placed.csv, not a hand-written guessed list.
No physical tool is launched. Review the diagram and one fresh PLACE before CTS.
"""
import argparse,csv,json,re
from collections import defaultdict
from pathlib import Path

def plan(csvfile):
    enc=defaultdict(list); out=defaultdict(list)
    for row in csv.DictReader(open(csvfile)):
        name=row['name']; n=name.replace('\\','')
        a=re.fullmatch(r'u_enc.d([0-8])\[(\d+)\]\$_DFF_P_',n)
        b=re.fullmatch(r'u_ptx.l\[(\d+)\]\[(\d+)\]\$_(?:S?DFF_[A-Z0-9_]+)',n)
        c=re.fullmatch(r'u_enc.p_d\[(\d+)\]\$_DFF_P_',n)
        if a:enc[int(a[2])].append(name)
        if b:out[int(b[2])].append(name)
        if c:out[int(c[1])].append(name)
    if set(enc)!=set(range(512)) or any(len(v)!=9 for v in enc.values()):raise ValueError('current TX nine-stage encoder chain membership changed')
    if set(out)!=set(range(544)) or any(len(v)!=4 for v in out.values()):raise ValueError('current TX p_d + three adapter-stage chain membership changed')
    groups=[];boxes=[]
    for family,rows in [('enc',enc),('ptx',out)]:
        for bit,names in sorted(rows.items()):
            col=bit%32; row=bit//32
            if family=='enc':x=10+5.4*col;y=7+3.24*row;w=4.32;h=2.16
            else:x=230+4.32*col;y=10+2.7*row;w=3.24;h=1.62
            name=f'{family}_{bit}';groups.append(dict(name=name,members=sorted(names)))
            boxes.append(dict(name=name,prefixes=[n.replace('\\','') for n in sorted(names)],box_um=[round(x,3),round(y,3),round(x+w,3),round(y+h,3)]))
    manifest=dict(schema='opentallas.core_atomic_clock_groups.v1',module='ot_s81hd_sc_tx',max_sinks=16,max_radius_um=20,groups=groups)
    guides=dict(boxes=boxes)
    return manifest,guides

def main():
    ap=argparse.ArgumentParser();ap.add_argument('placed_csv');ap.add_argument('outdir');a=ap.parse_args()
    manifest,guides=plan(a.placed_csv);out=Path(a.outdir);out.mkdir(parents=True,exist_ok=True)
    (out/'clock_groups.json').write_text(json.dumps(manifest,indent=1)+'\n')
    (out/'reg_guides.json').write_text(json.dumps(guides,indent=1)+'\n')
    print(f'{len(manifest["groups"])} branches, {sum(len(g["members"]) for g in manifest["groups"])} sinks, max {max(len(g["members"]) for g in manifest["groups"])} sinks/atomic branch')
if __name__=='__main__':main()
