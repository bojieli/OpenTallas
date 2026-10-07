#!/usr/bin/env python3
"""Price field capacity before building mixed-q/BF S81 die candidates.

This is a floorplan capacity gate, not a routed or performance-qualified result.
The emitted die plans supply actual hop/cycle costs before any physical run.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_s81_fulldie as F

BASE = ('--gen r8 --rev r9 --elem-h 198.72 --cc-reach-um 215 --vch-interleave --link-fix '
        '--corr-interleave --hop-fix --meso-d8 --cfifo-v2 --hc-xface --link-split --sel-xstg '
        '--pin-relay --ch-heights 259.2,302.4,388.8,388.8,302.4,259.2,259.2 '
        '--bf-per-region 4 --geometry-fix --vch-w 1641.6 --hc-corr 1512 '
        '--hub-column-width 1728 --su-mm2 25.61188')


def model():
    variants = []
    for label, qh, proposed in (('uniform198', None, 2048), ('mixed183', 183.60, 2304),
                                 ('mixed221', 221.4, 2048)):
        opts = BASE + f' --pairs {proposed}' + (f' --q-elem-h {qh}' if qh else '')
        F.apply_options(F.die_options(argparse.ArgumentParser()).parse_args(opts.split()))
        band = F.up(F.EDGE, F.GY) + F.PHY_H + 8.64 + F.CTRL_D + 8.64 + F.SVC_D
        available = (F.DIE[1] - 2 * band - 2 * F.FIELD_MARGIN - sum(F.chh(t) for t in range(F.TIERS + 1))) / F.TIERS
        rng, _ = F.frame_plan_r8()
        layouts = [F.pack_frame(range(*rng[r]), F.bf_sites(), set()) for r in rng]
        proposed_fit = F._frames_fit(F.SLOTS8, F.SLOT_H8)
        # Same flat BF map and return-tree packing on every region; do not move BF payload ownership.
        maximum = 0
        for n in range(F.ROOTS * 4, proposed + 1):
            F.set_pairs(n)
            if F._frames_fit(F.SLOTS8, F.SLOT_H8):
                maximum = n
        F.set_pairs(maximum)
        stages = math.ceil(81 * 2417 / maximum)
        variants.append(dict(
            name=label, requested_pairs=proposed, bf_pairs=512, q_frame_um=qh or 198.72,
            bf_frame_um=198.72, requested_fits=proposed_fit,
            maximum_pairs_at_this_geometry=maximum, field_frame_available_um=available,
            field_frame_reserved_um=F.column_height(),
            maximum_requested_slot_height_sum_um=max(sum(hs) for _, _, hs in layouts),
            maximum_requested_return_strip_um=max((2 * len(es) - 1) * F.NODE_FRAME[1] for es, _, _ in layouts),
            requested_slot_order_first_region=[dict(pair=p, kind=k, slot=s, lane=l) for p, k, s, l in layouts[0][0]],
            requested_slot_offsets_um=layouts[0][1], requested_slot_heights_um=layouts[0][2],
            layer_stages_nominal_inventory_scenario=stages, layer_dies_TP4_nominal_inventory_scenario=4 * stages,
            extra_stage_hops_nominal_inventory_scenario=max(0, stages-81),
            capacity_basis='Legacy S81 decision inventory81 x2417 allocated pairs per TP rank. Capacity scenario only; actual released-checkpoint remapping is required',
            geometry_options=opts.replace(f'--pairs {proposed}', f'--pairs {maximum}'),
            hub_column_width_um=1728, su_reservation_mm2=25.61188,
            softmax_leaf_reservation_mm2_at_55pct=22.445346,
            su_remaining_area_for_other_operators_mm2=25.61188-22.445346,
            geometry_plan_required=True, physical_run_ready=False,
            missing=['actual hop counts and composed latency from this geometry',
                     'source-matched final PQ and BF views', 'native clock/enable contracts if BF is half-rate',
                     'released-checkpoint mapping to resized stage count', 'clock tree, IO budgets and energy composition']))
    files = ['tools/s81/mixed_geometry.py', 'tools/dsrom_s81_fulldie.py', 'tools/uarch_model.py']
    return dict(schema='opentallas.s81.mixed-geometry-sizing.v1', physical_adoption=False,
                objective='preserve field arithmetic/order and widen capacity through extra dies when needed',
                source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},
                variants=variants)


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args=ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    record=model()
    args.out.write_text(json.dumps(record, indent=1)+'\n')
    print(json.dumps([{k:v[k] for k in ('name','requested_fits','maximum_pairs_at_this_geometry',
                                      'layer_stages_nominal_inventory_scenario')} for v in record['variants']]))
