#!/usr/bin/env python3
"""HBM DS die: latency recompose for the margin-first view rule (owner 2026-10-06, CLAUDE HBM-ABSTRACTS).

The margin-first rule adds register stages inside the die block views.  This prices them on the per-token path with
the same die-level path model as tools/hbm_accel_die_price.py (one-way cycles per path class x per-token occurrences
from the matched DS composition, Qwen 8K stage crossings), on a committed GRT wire record (default: the r16g adopted
wire_stages.json basis), and reports the delta against the same record priced without the adders.

Cycle ledger (per fork report, 2026-10-06; edit LEDGER when a fork records a measured change):
  meso crossing        +3 per meso / mcast / cdist downstream FIFO crossing (pin capture, readout, pin launch; stations
                       src16 f833ed394, FIFO campaign 307e2da66) -> MESO_CYC 2 -> 5 on every meso-crossing path
  gather (a2)          +2 on the SM -> SU result gather path (once per barrier)
  cdist b launch       +2 on the control-distribution launch (release / issue direction, once per barrier)
  forward / launch stations: 0
  spine face_stages 3 -> 5 (fd828b957) on the six interim wrappers: +4 per face traversal (barrier stays fs3 +2):
                         barrier: arrive in + release out          +4 per barrier       (measured: bm2_pd45 record)
                         collective endpoint: SU -> coll, coll -> SU +4 per collective
                         collective endpoint <-> SerDes macros      +4 per switch crossing
                         VM multicast root: SU -> VM -> x face       +4 per serial x load
                         router: SU -> router -> stream service      +4 per expert fetch
                         cmdproc: issue face                         +2 per SM group (one per barrier)
  actquant (hfd_quant) +9 core + 2 in + 2 out face stages = +13 per sequential invocation.  In the matched DS gate
                       composition every activation quant is fused into an SU chain (sufused:*), so the standalone
                       quantiser is OFF the per-token path (0 invocations); the bound row charges it on every fused
                       quant point (hc_pre_norm 80, q_norm_kv_row 40, swiglu 40, final_norm 1 = 161).
  loader               off the per-token path (boot / weight load)

    python3 tools/hbm_die_views_recompose.py [--grt-work DIR] [--out results/rtl/hbm_accel_die_views_20261006/recompose_margin.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_accel_die_fp as F  # noqa: E402
import hbm_accel_die_price as PR  # noqa: E402

# spine face_stages 5 (fd828b957: pin flop + 4 stages, +2 per face over face_stages 3) on the six interim wrappers
# (router, quant, cmdproc, loader, coll, vm); the closed barrier view stays at face_stages 3 (+4 round trip, measured)
LEDGER = dict(meso_extra=3, gather=2, cdist=2, barrier=4, coll=8, serdes=8, vm=8, router=8, cmdproc=4, quant=17,
              quant_points_bound=161, quant_points_gate=0)


def priced(m, grt_work, meso):
    PR.MESO_CYC = meso
    rp = PR.routed_paths(m, grt_work)
    cm = PR.class_max(rp)
    out = {}
    for key in ('stages_430', 'stages_430_median_bundle', 'stages_430_manhattan'):
        out[key] = PR._price(m, rp, cm, key)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--grt-work', type=Path, required=True, help='GRT case dir holding wirelength.csv')
    ap.add_argument('--out', type=Path, default=ROOT / 'results/rtl/hbm_accel_die_views_20261006/recompose_margin.json')
    a = ap.parse_args(argv)
    m = F.build_model() if hasattr(F, 'build_model') else None
    if m is None:
        import hbm_die_views as V
        m = V.model()[0]
    hz = F.CLK_HZ
    base = priced(m, a.grt_work, 2)
    marg = priced(m, a.grt_work, 2 + LEDGER['meso_extra'])
    PR.MESO_CYC = 2
    rec = dict(schema='opentallas.hbm_die_views_recompose.v1', ledger=LEDGER, grt_work=str(a.grt_work), bases={})
    for key in base:
        b, g = base[key]['compositions']['ds_matched'], marg[key]['compositions']['ds_matched']
        n = b['counts']
        extra = dict(
            meso_paths_us=round(g['added_us'] - b['added_us'], 3),
            gather=n.get('barrier', 0) * LEDGER['gather'],
            cdist=n.get('barrier', 0) * LEDGER['cdist'],
            barrier=n.get('barrier', 0) * LEDGER['barrier'],
            coll=n.get('coll_terms', 0) * LEDGER['coll'],
            serdes=n.get('coll_crossings', 0) * LEDGER['serdes'],
            vm=n.get('x_first_load', 0) * LEDGER['vm'],
            router=n.get('expert_fetch', 0) * LEDGER['router'],
            cmdproc=n.get('barrier', 0) * LEDGER['cmdproc'])
        cyc = sum(v for k, v in extra.items() if k != 'meso_paths_us')
        us_gate = round(extra['meso_paths_us'] + cyc / hz * 1e6, 3)
        us_bound = round(us_gate + LEDGER['quant'] * LEDGER['quant_points_bound'] / hz * 1e6, 3)
        gate = b['rows']['gate']
        ar0, mtp0, tau = gate['AR_priced_us'], gate['MTP_step_priced_us'], gate['tau']
        rows = {}
        for tag, us in (('gate_quant_off_path', us_gate), ('bound_quant_on_every_fused_point', us_bound)):
            rows[tag] = dict(added_us=us, AR_us=round(ar0 + us, 3), AR_delta_pct=round(100 * us / ar0, 2),
                             AR_tok_s=round(1e6 / (ar0 + us), 1), MTP_step_us=round(mtp0 + us, 3),
                             MTP_delta_pct=round(100 * us / mtp0, 2), MTP_tok_s=round(tau * 1e6 / (mtp0 + us), 1))
        qb, qm = base[key]['qwen_8k'], marg[key]['qwen_8k']
        qwen = {}
        for dn_ in qb:
            if dn_ == 'scope':
                continue
            d0, d1 = qb[dn_], qm[dn_]
            st = sum(s_['count'] * s_['crossings'] for s_ in d0['stages'])
            add = (d1['priced_cycles'] - d0['priced_cycles']) + st * (LEDGER['serdes'] + LEDGER['coll'])
            qwen[dn_] = dict(priced_cycles=d0['priced_cycles'], margin_cycles=d0['priced_cycles'] + add, added_cycles=add,
                             delta_pct=round(100 * add / d0['priced_cycles'], 2),
                             ar_tok_s=d0['ar_tok_s_priced'], ar_tok_s_margin=round(hz / (d0['priced_cycles'] + add), 1))
        rec['bases'][key] = dict(counts=n, extra_cycles=extra, ds_wire_priced=dict(AR_us=ar0, MTP_step_us=mtp0, tau=tau,
                                                                                    AR_tok_s=gate['AR_tok_s_priced'],
                                                                                    MTP_tok_s=gate['MTP_tok_s_priced']),
                                 ds_margin=rows, qwen_8k=qwen)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: dict(extra=v['extra_cycles'], ds=v['ds_margin'], qwen=v['qwen_8k']) for k, v in rec['bases'].items()},
                     indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
