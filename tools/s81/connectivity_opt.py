#!/usr/bin/env python3
"""Rank actual pin bundles and screen footprint-preserving orientation changes.

Inputs must be a canonical generated pin-align plan and its actual LEFs.
Proposals are never applied: clocks, PG symmetry and native timing need approval
from the concrete master contract, not an orientation inferred from its outline.
"""
import argparse
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import types

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'tools/hier_contract'))
import pin_align as PA

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan', type=Path)
    ap.add_argument('--lef', action='append', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--reach', type=float, default=500.)
    a = ap.parse_args()
    raw = a.plan.read_bytes()
    p = json.loads(gzip.decompress(raw) if a.plan.suffix == '.gz' else raw)
    pins = PA.read_pins([(gzip.decompress(f.read_bytes()).decode() if f.suffix == '.gz' else f.read_text()) for f in a.lef])
    ii = {}
    for row in p['insts']:
        # Both pin-align compact format and generator full Inst records.
        ii[row[0]] = types.SimpleNamespace(name=row[0], master=row[1], x=row[2], y=row[3], orient=row[6] if len(row)>6 else row[4])
    missing, edges, incidence = [], [], {}
    def points(n, port, bits, orientation=None):
        it = copy.copy(ii[n])
        if orientation: it.orient = orientation
        w, h, ps = pins[it.master]
        names = p.get('pins', {}).get(n+'|'+port, PA.default_names(n, port, bits))
        return [PA.place(it,w,h,ps[k]) for k in names]
    def measure(e, change=None):
        src,dst=e['ends']; n,ori=change or (None,None)
        aa=points(*src,e['bits'],ori if src[0]==n else None)
        bb=points(*dst,e['bits'],ori if dst[0]==n else None)
        ll=[abs(x[0]-y[0])+abs(x[1]-y[1]) for x,y in zip(aa,bb)]
        q=PA.bundle(aa,bb)
        return dict(sum_bit_um=sum(ll), mean_um=sum(ll)/len(ll), max_um=max(ll),
                    required_stages_lower_bound=max(0,math.ceil(max(ll)/a.reach)-1),
                    alignment=q)
    for bid,cls,bits,ends in p['buses']:
        if cls in PA.EXEMPT_CLS or len(ends)<2: continue
        for load in ends[1:]:
            e=dict(bus=bid, cls=cls, bits=bits, ends=[ends[0],load], traffic=None, criticality=None)
            try: e.update(measure(e))
            except (KeyError, ValueError, ZeroDivisionError) as ex:
                missing.append(dict(bus=bid,ends=e['ends'],error=str(ex)));continue
            edges.append(e)
            for n,_ in e['ends']: incidence.setdefault(n,[]).append(e)
    proposals=[]
    # Evaluate each flip against ALL incident actual bundles, not one attractive edge.
    for n,ee in incidence.items():
        before=sum(e['sum_bit_um'] for e in ee)
        worst=max(e['max_um'] for e in ee)
        for ori in ['R0','MX','MY','R180']:
            if PA.ORI[ori]==PA.ORI[ii[n].orient]:continue
            mm=[measure(e,(n,ori)) for e in ee]
            after=sum(e['sum_bit_um'] for e in mm)
            if after>=before:continue
            proposals.append(dict(instance=n,master=ii[n].master,before_orientation=ii[n].orient,
                orientation=ori, before_sum_bit_um=before, after_sum_bit_um=after,
                saved_bit_um=before-after,before_max_um=worst,after_max_um=max(m['max_um'] for m in mm),
                before_alignment_failures=sum(e['alignment']['verdict']=='FAIL' for e in ee),
                after_alignment_failures=sum(m['alignment']['verdict']=='FAIL' for m in mm),
                incident_bundles=len(ee),footprint_collision_delta=0,
                status='GEOMETRIC_PROPOSAL_ONLY: actual LEF symmetry/PG/clock/reset/native timing legality unverified'))
    edges.sort(key=lambda e:e['sum_bit_um'],reverse=True)
    proposals.sort(key=lambda e:e['saved_bit_um'],reverse=True)
    out=dict(schema='opentallas.s81.connectivity_optimization.v1',
        plan_sha256=hashlib.sha256(raw).hexdigest(),
        lef_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in a.lef},
        canonical_scope='Caller must provide exact2417/BF519/PHW10 generated plan; no reduced vehicle qualifies',
        bundles_measured=len(edges),missing=missing,top20_routes=edges[:20],
        total_sum_bit_um=sum(e['sum_bit_um'] for e in edges),worst_um=max((e['max_um'] for e in edges),default=None),
        orientation_proposals=proposals[:100],
        missing_data=['source-pinned traffic rates and critical path calendar','clock/PG master orientation legality',
                      'aggregate window routing cuts including through traffic','translations/home swaps and stack order require placement changes and halo audit',
                      'measured per-pin reach may be less than500um; stage count is geometric lower bound'])
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(out,indent=1)+'\n')
    print(json.dumps(dict(measured=len(edges),missing=len(missing),proposals=len(proposals))))

if __name__=='__main__':main()
