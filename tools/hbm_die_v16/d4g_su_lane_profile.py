#!/usr/bin/env python3
"""LH-GEN2E 10-19: emitted-topology SU/SFU/HC LG lane profile of a d4g contract (post S5 landing, post S8b l12_banklat).

Source rule (results/arch/hbm_su_topology_profile_1019, codex 708d112f3): the GEN2c+l12 SW0 basis is READ_RETURN 18 /
WRITE_RETURN 15 (lanes read 4/3, 5/2; write 3/4; + bank face 1 + bank 6/3 + SU 4).  The emitted GEN2e S4/S5 expansion
must regenerate these paths on the NEW geometry and either pad to the 18/15 budget (l12_banklat does) or be repriced.
This tool reads the contract through d4g_bank_latency.check (the same graph the LAT class of the functional bind uses)
and writes, per LG client (SU pgslice_lg, SFU tap, HC tap term) and per bank: request / return lane edges, l12 pad
stages, round trip, param have / want.  It is the hand-off to the static schedule (TOK.HDS.PRICE): every cycle above the
source basis is listed as a priced delta, never absorbed silently.

    d4g_su_lane_profile.py CONTRACT.json[.gz] --out PROFILE.json [--stage post_landing|final] [--require-budget]
--require-budget: exit 1 unless every SU pgslice_lg client has READ_RETURN 18 / WRITE_RETURN 15 and LAT PASS
(the final GEN2e contract must match the profile the native record23 arithmetic and the token calendar were built on).
"""
import argparse, hashlib, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4g_bank_latency as L  # noqa: E402

LG = {'ot_hbm_su_static_pgslice_lg': (18, 15), 'ot_hgi_sfu_lg_pair_tap_leaf': (24, 21),
      'ot_hgi_sfu_lg_pair_tap_leaf_term': (32, 29)}
PARAM = {'rd': 'READ_RETURN', 'wr': 'WRITE_RETURN'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('contract'); ap.add_argument('--out', required=True); ap.add_argument('--stage', default='final')
    ap.add_argument('--require-budget', action='store_true')
    a = ap.parse_args()
    c = L.load(a.contract)
    rows, summ = L.check(c)
    out, bad = [], []
    for r in rows:
        if r['master'] not in LG or r['kind'] not in PARAM:
            continue
        budget = LG[r['master']][0 if r['kind'] == 'rd' else 1]
        banks = [dict(bank=p['bank'], bank_port=p['bank_port'], lane_rq=p['lane_rq'], lane_rr=p['lane_rr'], rt=p['rt'],
                      pin=p['pin'], via=p.get('via'), unresolved=[n for n in p['notes'] if 'NO_E' in n][:2])
                 for p in r.get('paths', [])]
        have = r.get('have')
        row = dict(client=r['client'], master=r['master'], kind=r['kind'], param=PARAM[r['kind']], have=have,
                   want=r.get('want'), budget=budget, lat_status=r['status'], banks=banks,
                   delta_over_budget=(have - budget) if isinstance(have, int) else None, bad=r['bad'][:3])
        out.append(row)
        if r['master'] == 'ot_hbm_su_static_pgslice_lg' and (have != budget or r['status'] != 'PASS'):
            bad.append(f"{r['client']}.{PARAM[r['kind']]} have {have} want {r.get('want')} budget {budget} LAT {r['status']}")
    raw = Path(a.contract).read_bytes()
    su = [o for o in out if o['master'] == 'ot_hbm_su_static_pgslice_lg']
    rep = dict(schema='opentallas.hbm.d4g.su_lane_profile.v1', stage=a.stage, contract=str(a.contract),
               contract_sha256=hashlib.sha256(raw).hexdigest(), basis='codex 708d112f3 su_SW0_gen2c_l12_source_profile (18/15)',
               lat_summary=summ, su_clients=len(su), su_at_budget=sum(o['have'] == o['budget'] for o in su),
               max_delta_over_budget=max([o['delta_over_budget'] or 0 for o in out] or [0]),
               verdict='PASS' if not bad else 'FAIL', violations=bad, rows=out,
               schedule_handoff='every row with delta_over_budget > 0 is a priced cycle delta for TOK.HDS.PRICE / token calendar')
    Path(a.out).write_text(json.dumps(rep, indent=1))
    print(f"SU_LANE_PROFILE {a.stage} {rep['verdict']} su_clients={len(su)} at_budget={rep['su_at_budget']} "
          f"max_delta={rep['max_delta_over_budget']} lat_fail={summ['fail']}")
    for b in bad[:8]:
        print('  ', b)
    sys.exit(1 if (a.require_budget and bad) else 0)


if __name__ == '__main__':
    main()
