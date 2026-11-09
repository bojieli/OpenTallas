#!/usr/bin/env python3
"""stn_transport_params: the per-slice station result shift of a bound QC plan, for the compiler (DV_STN_TRANSPORT).

QC-TRANSPORT-FIX-4 11-09.  With the bind hook qc_fabric_transport on (asbuilt key qc_fabric_transport), every station
region r of slice s joins its four stream words E(r) edges later than the as-built (zero-transport) station, and the
r_d results of all 8 regions meet at ctl on region 0's r_v (RD_PAD aligns them to the latest region, region 0).  So the
slice's station result reaches ctl

    result(s) = max_r (E(r) + r_d lane(r))      edges later than the as-built ages (dv_lower_mat l8_ar) assume,

and every stream word reaches its station at least

    word(s) = min_r min(E(r) + 14 - SKEW_S(r), E(r) - HI_PAD(r) + 14 - SKEW_N(r), E(r) - HI_PAD(r))  (near S, near N, far N)

edges later (far S = E(r) itself is never the smallest).  The STN config itself reaches every region C(s) edges later
(u_r*.cfg_*_p landed stages, one value per slice required), so the STN command moves by

    cfg(s) = word(s) - C(s)                    and still reaches each region as far ahead of its first word as as-built.

The last region output of the station is r_v (tail1: r_v <= vs[0]; RD_PAD delays only the r_d data after it, r_idx and
r_last are not delayed), E(r) edges later; the next config reaches the region C(s) later, so the STN window grows by

    busy(s) = max_r E(r) - C(s)                edges (dv_lower_mat lo; the command time already carries cfg(s)).
Inputs, both from the bind directory: param_regen.json (record.qc_fabric_transport.slices: the hook's own table) and
bus_groups.json (landing members u_ctl.r_d[64 r +: 64] landed_stages = the r_d lane; u_r*.cfg_*_p landed minus
as-built = C).  Fail closed on any gap.

  python3 stn_transport_params.py BIND_DIR --out stn_transport.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = 'opentallas.qwen.dv-stn-transport.v1'
SLICES = ['W5', 'W4', 'W3', 'W2', 'W1', 'W0', 'E0', 'E1', 'E2', 'E3', 'E4', 'E5']
SKEW0 = 14


class ParamError(ValueError):
    pass


def rd_lanes(bus_groups):
    out = {}
    for g in bus_groups['landing']:
        for m in g['members']:
            sink, port, bits = g['sink'], m['sink_port'], m['sink_bits'][0]
            if port == 'r_d' and sink.endswith('.u_core.u_sub.u_ctl') and bits[1] - bits[0] == 63 and bits[0] % 64 == 0:
                key = (sink.split('.')[0][4:], bits[0] // 64)
                if key in out and out[key] != m['landed_stages']:
                    raise ParamError(f'{key}: two r_d lane depths {out[key]} / {m["landed_stages"]}')
                out[key] = m['landed_stages']
    return out


CFG_PINS = ('cfg_v_p', 'cfg_mode_p', 'cfg_wsrc_p', 'cfg_nwords_p', 'cfg_sbase_p', 'cfg_kcm1_p')


def cfg_lanes(bus_groups):
    """slice -> the one landed-minus-as-built shift of every STN config pin of its 8 regions (fail closed otherwise)"""
    seen = {}
    for g in bus_groups['landing']:
        sink = g['sink']
        parts = sink.split('.')
        if len(parts) != 4 or parts[1:3] != ['u_core', 'u_sub'] or not parts[3].startswith('u_r'):
            continue
        for m in g['members']:
            if m['sink_port'] in CFG_PINS:
                seen.setdefault((parts[0][4:], parts[3], m['sink_port']), set()).add(m['landed_stages'] - m['asbuilt_stages'])
    out = {}
    for s in SLICES:
        keys = [(s, f'u_r{r}', p) for r in range(8) for p in CFG_PINS]
        miss = [k for k in keys if k not in seen]
        if miss:
            raise ParamError(f'{s}: no landing for STN config pins {miss[:3]}')
        v = set().union(*(seen[k] for k in keys))
        if len(v) != 1:
            raise ParamError(f'{s}: STN config pin shifts {sorted(v)} (one value per slice required)')
        out[s] = v.pop()
    return out


def derive(record, lanes, cfg_pin):
    slices = {}
    for s in SLICES:
        if s not in record['slices']:
            raise ParamError(f'{s}: not in the hook record')
        rows = record['slices'][s]['regions']
        rd, cfg = [], []
        for r in range(8):
            q = rows[str(r)] if str(r) in rows else rows[r]
            if (s, r) not in lanes:
                raise ParamError(f'{s} r{r}: no u_ctl.r_d lane in bus_groups')
            e, sks, skn, hi = q['E'], q['SKEW_S'], q['SKEW_N'], q['HI_PAD']
            rd.append(e + lanes[(s, r)])
            cfg.append(min(e + SKEW0 - sks, e - hi + SKEW0 - skn, e - hi))
            if r and rd[0] - rd[-1] != q['RD_PAD']:
                raise ParamError(f'{s} r{r}: RD_PAD {q["RD_PAD"]} != region-0 lead {rd[0] - rd[-1]}')
        if rd[0] != max(rd):
            raise ParamError(f'{s}: region 0 is not the latest r_d ({rd})')
        c = cfg_pin[s]
        if min(cfg) - c < 0:
            raise ParamError(f'{s}: a stream word arrives earlier than the moved STN config ({cfg}, config pins +{c})')
        busy = max((rows[str(r)] if str(r) in rows else rows[r])['E'] for r in range(8)) - c
        slices[s] = dict(result=rd[0], cfg=min(cfg) - c, busy=busy, rd=rd, word_regions=cfg, cfg_pin=c)
    return slices


def build(bind_dir):
    b = Path(bind_dir)
    pr = json.loads((b / 'param_regen.json').read_text())
    rec = pr.get('record', {}).get('qc_fabric_transport')
    if not rec:
        raise ParamError(f'{b}/param_regen.json: no qc_fabric_transport record (bind without the hook key)')
    bg = json.loads((b / 'bus_groups.json').read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()       # noqa: E731
    return dict(schema=SCHEMA, tool='tools/qwen_layerbench/stn_transport_params.py', rule=__doc__.split('\n\n')[1],
                sources={str(b / 'param_regen.json'): sha(b / 'param_regen.json'), str(b / 'bus_groups.json'): sha(b / 'bus_groups.json')},
                slices=derive(rec, rd_lanes(bg), cfg_lanes(bg)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bind_dir')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    d = build(a.bind_dir)
    Path(a.out).write_text(json.dumps(d, indent=1) + '\n')
    print(json.dumps({s: (v['result'], v['cfg'], v['busy']) for s, v in d['slices'].items()}))


if __name__ == '__main__':
    main()
