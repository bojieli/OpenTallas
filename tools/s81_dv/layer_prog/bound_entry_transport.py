#!/usr/bin/env python3
"""Actual XR command/target5 fields to current VP input pins, without DL defaults."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

# Explicit production XR output fields. Local XR decode and VP execution are
# separate measured stages; these records price only actual bound transport.
FIELDS=(('c_v',1),('c_d',160),('sw_v',1),('sw_a',10),('sw_m',8),('sw_d',256))


def collect(die):
    rows=[]
    for sl in sorted(die.slices()):
        xrs=[n for n,u in die.units.items() if n.startswith(sl+'.') and u['master'] in ('ot_s81sl_xrt1','ot_s81sl_xrt3')]
        vps=[n for n,u in die.units.items() if n.startswith(sl+'.') and u['master']=='ot_s81sl_vp']
        if len(xrs)!=1 or len(vps)!=5:
            rows.append(dict(status='BLOCKED',slice=sl,reason='need one retained atomic XR and five actual VP source units',xr_units=xrs,vp_units=vps));continue
        xr=xrs[0];used=set()
        for leaf in range(5):
            # Identify leaf ordinal by the actual source driver and bound sinks,
            # never by normalising path spellings or assuming generated indices.
            matches=[]
            for vp in vps:
                try:r=die.route(xr,'sw_v',vp,'sw_v',source_lsb=leaf,width=1)
                except (KeyError,ValueError):continue
                matches.append((vp,r))
            if len(matches)!=1 or matches[0][0] in used:
                rows.append(dict(status='BLOCKED',slice=sl,leaf=leaf,reason='actual sw_v source does not identify one unique VP',matching_vps=[v for v,_ in matches]));continue
            vp,_=matches[0];used.add(vp)
            try:
                fields={p:die.route(xr,p,vp,p,source_lsb=(0 if p=='c_d' else width*leaf),width=width) for p,width in FIELDS}
                command={fields[p]['age_edges'] for p in ('c_v','c_d')}
                store={fields[p]['age_edges'] for p in ('sw_v','sw_a','sw_m','sw_d')}
                if len(command)!=1 or len(store)!=1:
                    raise ValueError('current valid and payload fields have incoherent bound ages')
                rows.append(dict(status='PASS',slice=sl,leaf=leaf,xr=xr,vp=vp,
                    command_transport_edges=command.pop(),target5_transport_edges=store.pop(),fields=fields,
                    local_vp_store_commit_edges=None,local_hload_readiness_edges=None,local_gain_readiness_edges=None))
            except (KeyError,ValueError) as exc:
                rows.append(dict(status='BLOCKED',slice=sl,leaf=leaf,xr=xr,vp=vp,reason=str(exc)))
    return dict(schema='opentallas.s81.bound_entry_transport.v1',
        verdict='PASS_BOUND_TRANSPORT' if len(rows)==80 and all(r['status']=='PASS' for r in rows) else 'BLOCKED',
        die_sha256=die.die_sha,source_asbuilt_sha256=die.inventory['source_asbuilt_sha256'],
        leaves=rows,legacy_geometry_used=False,legacy_dl_depth_used=False,
        scope='XR output pin event to actual VP input pin event; local decode/commit/execution and reset/clock phase remain separate',
        readiness_qualified=False,native_job_sealed=False,full_token=False,added_rtl_cycles=0)


def main():
    from layer_prog.bound_die import BoundDie
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('bound','inventory','out'):ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists():raise ValueError('preserve prior verdict; use a fresh output')
    rec=collect(BoundDie(a.bound,a.inventory))
    a.out.write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps(dict(verdict=rec['verdict'],leaves=len(rec['leaves']),blocked=sum(r['status']!='PASS' for r in rec['leaves']))))
    return 0 if rec['verdict']=='PASS_BOUND_TRANSPORT' else 2


if __name__=='__main__':raise SystemExit(main())
