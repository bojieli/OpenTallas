#!/usr/bin/env python3
"""lane_ages_export: ctlm <-> DV W5 lane ages of a GEN die (fwd_lanes.json) for ctlm_image / dv_layer (--lane-ages).

Lane age = lane_groups lane cycles = E + 1 (the landing o register), the same rule as
results/rtl/qwen_layer_tput_1018/ctlm_prog/lane_ages_dv2f14bi.json (Q-XPF).  QW-TOKSCHED 10-20: the layer compiler
was still fed the dv2f14bi ages; this exports them from the current die (dv2f20g5r2b) so the static schedule absorbs
the die's real forwarded-lane latencies.  Also records the attention lanes dvs_W5 <-> native59 (dd / dr) and the MU
context lane for the ledger (not consumed by ctlm_image).

Usage: lane_ages_export.py --fwd <die>/out/case/fwd_lanes.json --die <name> --out <json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

NEED = {'R_CMD': 'dvw_cmd_wi', 'R_HR': 'dvw_hr_wi', 'R_SS': 'dvw_ss_wo', 'R_AG': 'dvw_ag_wo', 'R_ST': 'dvw_st_wi'}
EXTRA = {'R_DD': 'dvw_dd_wo', 'R_DR': 'dvw_dr_wi', 'R_CTX': 'dvw_mu_ctxrx_ctx_x'}


def export(fwd: Path, die: str):
    raw = fwd.read_bytes()
    lanes = {l['bid']: l for l in json.loads(raw)['lanes']}
    out = dict(schema='opentallas.qwen.ctlm-lane-ages.v1', die=die,
               why='lane age = E + 1 (landing o register) of the GEN fwd_lanes.json lane (tools/qwen_layerbench/'
                   'lane_ages_export.py, QW-TOKSCHED 10-20)',
               source=str(fwd), source_sha256=hashlib.sha256(raw).hexdigest(), lanes={})
    for k, bid in {**NEED, **EXTRA}.items():
        if bid not in lanes:
            if k in NEED:
                raise SystemExit(f'{fwd}: no lane {bid}')
            continue
        l = lanes[bid]
        out['lanes'][k] = dict(bid=bid, n=l['n'], E=l['E'], E_sta=l.get('E_sta'), K=l.get('K'),
                               E_basis=l.get('E_basis'))
        out[k] = l['E'] + 1
    out['XPF_TRANSPORT_EDGES'] = 1 + out['R_HR']
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fwd', required=True)
    ap.add_argument('--die', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    o = export(Path(a.fwd), a.die)
    Path(a.out).write_text(json.dumps(o, indent=1) + '\n')
    print(json.dumps({k: v for k, v in o.items() if k.startswith('R_')}))


if __name__ == '__main__':
    main()
