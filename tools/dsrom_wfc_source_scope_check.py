#!/usr/bin/env python3
"""Routine SOURCE union equivalence and electrical eligibility; no timing relaxation."""
import argparse, hashlib, json
from pathlib import Path
import dsrom_wfc_split_physical as L

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--case', type=Path, required=True)
    p.add_argument('--final', action='store_true')
    a = p.parse_args()
    sta = json.loads((a.case / 'wf_sta.json').read_text())
    oracle = json.loads((a.case / 'wfc_source_corner_sta.json').read_text())
    modes = ('incontext', 'reg2reg', 'region', 'die150')
    c = sta['corners']
    tt = min(c['TT'][m]['setup_wns_ps'] for m in modes)
    ff = min(c['FF'][m]['hold_wns_ps'] for m in modes)
    equivalent = abs(tt-oracle['setup_tt']['worst_slack_ps']) <= .1 and abs(ff-oracle['hold_ff']['worst_slack_ps']) <= .1
    base = next(a.case.rglob('results/asap7/*/base/6_final.odb')).parent
    fresh = all(sta['artifacts_sha256'][f] == hashlib.sha256((base/f).read_bytes()).hexdigest() for f in ('6_final.odb','6_final.sdc','6_final.spef'))
    for name in ('setup_tt','setup_ss','hold_ff'):
        r = oracle[name]
        fresh = fresh and not r.get('errors') and all(r.get(k+'_sha256') == hashlib.sha256((base/f).read_bytes()).hexdigest() for k,f in (('odb','6_final.odb'),('spef','6_final.spef'),('sdc','6_final.sdc')))
    drv = json.loads((a.case/'wf_drv_TT.json').read_text()) | {'FF':json.loads((a.case/'wf_drv.json').read_text())['FF']}
    electrical = all(drv[k]['done'] and not any(drv[k]['violators'].values()) for k in ('TT','FF'))
    done = all(c[k].get('done') and c[k].get('exit') == 0 for k in ('TT','FF'))
    final = a.final or (base/'6_final.odb.pre_eco').exists()
    # mtp-lead 2026-10-09: TC electrical is a FINAL condition like FF hold.  Pre-ECO the post-route hold ECO (with its
    # opt-in DRV repair, cl/hold_eco_opts.env REPAIR_DRV=1) still rebuilds the netlist and wires, so a pre-ECO slew miss
    # must not stop the loop from reaching it (hold_only() requires no failed check); the installed (final) result must
    # be electrically clean.  Unchanged for a final verdict.
    ok = equivalent and fresh and (electrical or not final) and done and tt >= 0 and L.case_record(a.case)['drc_errors'] == 0 and (not final or ff >= 0)
    print(json.dumps(dict(eligible=ok, final=final, union_equivalent=equivalent, fresh=fresh, tc_electrical_clean=electrical, tt=tt, ff=ff, block_ff_preserved=c['FF']['block']['hold_wns_ps'], modes=modes)))
    if not ok: raise SystemExit(1)
if __name__ == '__main__': main()
