#!/usr/bin/env python3
"""HBM-BIND2 (2026-10-25): schedule-aware fit of the hub -> root lane (L74 / L74m) with ot_hbm_b2_beat_tx/rx
(rtl/hbm_accel/die_glue/b2/ot_hbm_b2_beat_link.sv: a valid-qualified word crosses LW = ceil(W / BEATS) wires + 1 beat-0
flag in BEATS beats, word latency BEATS + 1 edges, words of one group >= BEATS edges apart or a sticky schedule fault).

    python3 tools/hbm_b2/l74_beats.py --die TOP/die_b2.v --census-map B2n_census_map.json --extra-parts '{"b2_ep1_root":"root"}' \
        --lane-width 1875 --out l74_beats.json

Every hub -> root source bit (unique source bits, as b2_delays.py counts lane traffic) is put in one group:
  * a SERIALISABLE group (GROUPS below): a word with its own valid qualifier, sinks read the payload only with the
    valid; `cadence` = the schedule spacing the compiler must guarantee for BEATS (the binding is legal only if the
    producer's static schedule never issues two words of the group closer than BEATS edges);
  * every other bit is a LEVEL / PULSE / line-rate signal that crosses unserialised (faults, status, obs, SU scalar
    tree, HC partial sums, the ep_S1 SerDes TX frames at 0.8 frame/edge).
Groups made of several independent words (idx_vm_rr: 8 banks) serialise per word (FLAGS beat-0 flags, per-word
ceil).  Output per hub and BEATS 1..4: wires = level bits + sum(ceil(W / BEATS) + 1) over the serialised groups, fit vs the lane.
"""
import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2_top as T  # noqa: E402

# group -> (source inst regex, source port regex, valid ports, cadence note)
GROUPS = {
    'tkx_del': (r'hb_coll_NW', r'tkx_del_(flit|slot|valid)', ['tkx_del_valid'],
                'TKM delivery flits (4 slots / edge at line rate): needs the compiler to space deliveries >= BEATS'),
    'tkx_cfg': (r'hb_coll_NW', r'tkx_(start|arg_mode|cfg_\w+)', ['tkx_start'],
                'TKM op start + config: once per top-k op (sparse); MUST share the tkx_del latency (start vs delivery '
                'alignment), i.e. both groups serialised with the same BEATS or tkx_del padded'),
    'vms_cr': (r'hb_vms_NW', r'cr', ['cr'], 'VM ring responses to argmax / idx root ctl: one per request; spacing = the '
               'clients\' request spacing (CR_RT / ACK re-derived +BEATS+1)'),
    'idx_vm_rr': (r'vmb_NE\d', r'rr4', ['rr4'], 'NE VM bank read responses to the root idx share (8 banks x 257 b): the '
                  'share\'s read issue spacing per bank must be >= BEATS (VM_RT / VM_RT_EXTRA +BEATS+1)'),
    'idx_rq': (r'hb_idx__op_NE', r'vm_rq', ['vm_rq'], 'op_NE index read requests to the root share'),
    'host_cfg_a': (r'hleaf_NE', r'a_(cfg|desc|launch)\w*', ['a_cfg_v', 'a_desc_v', 'a_launch_v'],
                   'host cfg / desc / launch copy a: host VC spacing HMIN 10 >= BEATS (sparse)'),
}


FLAGS = {'idx_vm_rr': 8}      # independent words per group (each its own tx/rx pair)


def ser_w(g, w, B):
    n = FLAGS.get(g, 1)
    return w if B == 1 else n * (math.ceil(w / n / B) + 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--die', required=True)
    ap.add_argument('--census-map', required=True)
    ap.add_argument('--extra-parts', default='{}')
    ap.add_argument('--lane-width', type=int, required=True)
    ap.add_argument('--lane', default='L74')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    die = T.Die(a.die, [])
    cm = json.loads(Path(a.census_map).read_text())
    extra = json.loads(a.extra_parts)

    def part(n):
        if n in extra:
            return extra[n]
        if n in cm['parts']:
            return cm['parts'][n]
        for rx, g in cm['rules']:
            if re.search(rx, n):
                return cm['groups'][g][0]
        return None
    src_bits = collections.defaultdict(set)    # hub -> {(si, sp, bit)}
    for ki, i in die.insts.items():
        if part(ki) != 'root':
            continue
        for kp, e in i['conns'].items():
            if die.dirs.get(e) == 'output':
                continue
            try:
                segs = die.resolve(T.parse_expr(e, die.widths))
            except Exception:
                continue
            for s, _ in segs:
                if s[0] == 'n' and s[1] in die.driver:
                    si, sp = die.driver[s[1]]
                    p = part(si)
                    if p in ('NW_hub', 'NE_hub'):
                        src_bits[p].update((si, sp, b) for b in range(s[2], s[3] + 1))
    out = dict(schema='opentallas.hbm_b2.l74_beats.v1', lane=a.lane, lane_width=a.lane_width, rule=__doc__.split('\n\n')[0],
               hubs={})
    for hub, bits in sorted(src_bits.items()):
        grp = collections.defaultdict(int)
        lvl = collections.Counter()
        for si, sp, b in bits:
            g = next((k for k, (ri, rp, _, _) in GROUPS.items() if re.fullmatch(ri, si) and re.fullmatch(rp, sp)), None)
            if g:
                grp[g] += 1
            else:
                lvl[f'{si}.{sp}'] += 1
        level = sum(lvl.values())
        fit = {}
        for B in (1, 2, 3, 4):
            ser = {g: ser_w(g, w, B) for g, w in grp.items()}
            tot = level + sum(ser.values())
            fit[B] = dict(wires=tot, fits=tot <= a.lane_width, serialised=ser)
        # smallest set of groups to serialise at each BEATS (largest first) that fits
        mins = {}
        for B in (2, 3, 4):
            chosen, tot = [], level + sum(grp.values())
            for g, w in sorted(grp.items(), key=lambda x: -x[1]):
                if tot <= a.lane_width:
                    break
                chosen.append(g); tot += ser_w(g, w, B) - w
            mins[B] = dict(groups=chosen, wires=tot, fits=tot <= a.lane_width)
        out['hubs'][hub] = dict(need_unserialised=len(bits), level_bits=level, level_top=lvl.most_common(8),
                                groups={g: dict(width=w, cadence=GROUPS[g][3], valid=GROUPS[g][2]) for g, w in grp.items()},
                                all_serialised=fit, minimal=mins)
    Path(a.out).write_text(json.dumps(out, indent=1))
    for hub, h in out['hubs'].items():
        print(hub, 'need', h['need_unserialised'], 'level', h['level_bits'],
              {B: (v['wires'], v['fits']) for B, v in h['all_serialised'].items()},
              {B: (v['groups'], v['wires'], v['fits']) for B, v in h['minimal'].items()})


if __name__ == '__main__':
    main()
