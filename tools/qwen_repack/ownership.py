#!/usr/bin/env python3
"""Project actual failed-parent sink ownership onto the held45-entry RTL; no placement/timing claim."""
import argparse,csv,gzip,json,re
from collections import Counter
from pathlib import Path

def destination(root,name):
    n=name.replace('\\','')
    if root=='ck':
        leaf=re.search(r'g_sl\[(\d+)\].g_hd\.(g_tx|g_lrr)',n)
        if leaf:return 'ck_tx'+leaf.group(1)
        for prefix,clock in [('n_a_q[','ck_fa0'),('n_b_q[','ck_fa1'),('t_out[','ck_fa2'),('n_y[','ck_fa3'),('fy_q','ck_fa3'),('mis_q','ck_fa3'),('tap_q[','ck_fa4'),('tile_id_q[','ck_fa4'),('reset_q','ck_fa4'),('go$','ck_fa4')]:
            if n.startswith(prefix):return clock
        return 'ck'
    bank=re.fullmatch(r'ck_rp([0-4])',root)
    if not bank:raise ValueError('unassigned original clock root '+root)
    if '.g_rqr.gs_q[' in n:return 'ck_rqr0'
    if '.g_rqr.gn_q[' in n:return 'ck_rqr1'
    if '.g_pair[1].' in n or '.g_ok.u_r1/' in n:return 'ck_rp'+str(int(bank.group(1))+5)
    return root

def project(path):
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'rt') as stream:rows=list(csv.DictReader(stream,delimiter='\t'))
    seen=set();counts=Counter();bounds={};out=[]
    for r in rows:
        if r['cell'] in seen:raise ValueError('duplicate actual sink '+r['cell'])
        seen.add(r['cell']);clock=destination(r['root'],r['cell']);counts[clock]+=1
        x,y=float(r['x_um']),float(r['y_um']);b=bounds.setdefault(clock,[x,y,x,y]);b[0]=min(b[0],x);b[1]=min(b[1],y);b[2]=max(b[2],x);b[3]=max(b[3],y)
        out.append({**r,'candidate_clock':clock})
    if len(counts)!=26:raise ValueError(f'expected26 soft roots, got{len(counts)}')
    return dict(state='PROJECTED ownership only, actual original25-entry placement; not45-entry CTS/native proof',actual_sinks=len(rows),roots={c:dict(sinks=n,original_bbox_um=bounds[c]) for c,n in sorted(counts.items())}),out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('tsv');p.add_argument('out');a=p.parse_args();summary,rows=project(a.tsv);d=Path(a.out);d.mkdir(parents=True,exist_ok=True)
    (d/'ownership_projection.json').write_text(json.dumps(summary,indent=1)+'\n')
    with gzip.open(d/'sink_ownership_projected.tsv.gz','wt') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
    print(json.dumps(summary,indent=1))
if __name__=='__main__':main()
