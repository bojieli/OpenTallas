#!/usr/bin/env python3
"""H-PLANSTUDY (owner requirement 10-17): can the array of plan (c) (8-SM dies, 2x the dies) keep a ONE-TIER
(single switch crossing) multi-plane fabric?  Same per-die and per-link assumptions as HBM-NET 10-16
(results/arch/hbm_switch_sensitivity_1016, tools/hgi_sim/ds_switch_planes.py):

  * every die has 32 x 100G lanes to the scale-up fabric (unchanged per die; the 8-SM die keeps the d4f SerDes);
  * one switch chip per plane, Tomahawk-Ultra class: 512 x 100G SerDes = 51.2 Tb/s, ports of w lanes;
    P = 32 / w planes (one port per die per plane), at most 512 / w dies per plane chip (one tier);
  * crossing = PHY/FEC 100 + TU 250 (with FEC, Broadcom's 256 x 200G pod figure) + 2 x 3 m twinax 27.6 = 377.6 ns.

Per plan: G dies in the DS TP group, the minimum port width that reaches all G dies in one tier, planes, chips,
cables, and the crossing latency adders that the port width / package / cable length bring:
  FEC codeword accumulation: one RS(544,514) codeword (5,440 b) is collected before decode at every receiver
  (switch ingress and die ingress); at w lanes of 106.25 Gb/s it takes 5440 / (106.25 w) ns.  The 377.6 ns budget
  carries it at the 200G (w = 2) port; a narrower port adds the difference twice per crossing.
  Receiver-port drain beyond the model's delivery term (plane_rows, small collective classes): the worst excess.
  Cable reach: dies per package and packages per rack -> racks; links that leave the central + adjacent racks need
  AEC (+40..80 ns a crossing, LATENCY_SOURCES.md).
  Two-tier Clos when one tier is impossible: 3 chips a crossing = 3 x 377.6 = 1,132.8 ns (HBM-NET convention).

    python3 tools/hgi_sim/array_net_1017.py OUT.json
"""
import json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hgi_sim import ds_switch_planes as SP  # noqa: E402

LANES_DIE, SERDES_CHIP = 32, 512
X0 = 377.6
FEC_W2 = 5440 / (106.25 * 2)


def fabric(G, w):
    P = LANES_DIE // w
    ok = G <= SERDES_CHIP // w
    rows = SP.plane_rows(G, w) if ok else []
    small = [r for r in rows if not r['cls'].startswith('index TOPK')]
    excess = max([r['port_drain_ns'] - r['model_delivery_ns'] for r in small] + [0.0])
    topk = next((r for r in rows if r['cls'].startswith('index TOPK')), None)
    fec = 5440 / (106.25 * w)
    return dict(G=G, port_lanes=w, port_gbps=100 * w, planes=P, chips=P, ports_per_chip=SERDES_CHIP // w,
                ports_used_per_chip=G, one_tier=ok, cables=G * P, lanes_cabled=G * LANES_DIE,
                fec_codeword_ns=round(fec, 1), fec_add_per_crossing_ns=round(2 * max(0.0, fec - FEC_W2), 1),
                small_class_drain_excess_ns=round(excess, 1),
                topk_merge=dict(bytes=topk['bytes'], port_drain_ns=topk['port_drain_ns'],
                                model_delivery_ns=topk['model_delivery_ns'],
                                switch_buffer_if_unpaced_KB=topk['switch_buffer_if_unpaced_KB']) if topk else None)


def racks(G, dies_per_pkg, pkgs_per_rack=(32, 48)):
    pk = math.ceil(G / dies_per_pkg)
    r = [math.ceil(pk / n) for n in pkgs_per_rack]
    # switch shelf in the centre rack: centre + 2 adjacent racks are copper (<= 2.6 m), the rest need AEC
    far = [max(0, x - 3) / x for x in r]
    return dict(dies_per_package=dies_per_pkg, packages=pk, racks=r, share_links_over_3m=[round(f, 2) for f in far])


def main():
    out = dict(schema='opentallas.hbm_plan_study_1017.array_net.v1', rule=__doc__, plans={})
    for name, G in (('a', 192), ('b', 192), ('c', 384)):
        cases = [fabric(G, w) for w in (4, 2, 1)]
        one = [c for c in cases if c['one_tier']]
        best = one[0] if one else None             # widest port that still reaches every die (fewest planes)
        pk = [racks(G, d) for d in ((2, 4) if G > 192 else (2,))]
        rec = dict(G=G, fabrics=cases, chosen=best, packaging=pk)
        if best:
            x = X0 + best['fec_add_per_crossing_ns'] + best['small_class_drain_excess_ns'] * 0  # drain hidden: see note
            rec['crossing_ns'] = dict(
                copper=round(X0 + best['fec_add_per_crossing_ns'], 1),
                copper_note='377.6 + FEC accumulation at the narrower port (switch + die receiver)',
                with_aec=[round(X0 + best['fec_add_per_crossing_ns'] + a, 1) for a in (40, 80)],
                aec_note='if packages spill past the centre + adjacent racks (share_links_over_3m > 0): +40..80 ns AEC',
                two_tier=round(3 * X0, 1))
        out['plans'][name] = rec
    c = out['plans']['c']
    out['verdict_c'] = dict(
        one_tier_possible=bool(c['chosen']),
        how=('384 dies need 512 / w >= 384, i.e. w = 1: 100G single-lane ports, 32 planes = 32 TU chips (384 of 512 '
             'ports used), 12,288 single-lane cables (4x the 192-die array\'s 3,072 two-lane cables, 2x its lanes)') if c['chosen'] else 'no',
        caveat=('the 512 x 100G single-lane port mode is printed for Tomahawk 5; for TU it is plausible but not confirmed '
                'in a primary source (HBM-NET README section 1). Without it 384 dies need a 2-tier Clos.'),
        package_option=('4 dies (each 1 stack) per package: 96 packages, 2-3 racks, all copper; 2 dies per package: '
                        '192 packages, 4-6 racks, 33-50% of links need AEC'))
    print(json.dumps(out, indent=1))
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
