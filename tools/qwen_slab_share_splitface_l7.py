#!/usr/bin/env python3
"""Item7 prescribed CTS-hold fallback; identical faces, LAT7 charged once."""
import argparse
import json
import shlex

import qwen_slab_share_splitface as predecessor


def model():
    r = predecessor.model()
    r.update(variant='s570_l7_splitface_m7', recipe_variant_index=2,
             mul_lat=7, additional_cycles_vs_inherited_lat6=217,
             inherited_postscale_cycles_vs_lat5_per_token=434,
             added_token_latency_ns_at_1p2ghz=217 / 1.2,
             trigger='LAT6 splitface CTS RSZ-0060 after 33614 hold buffers',
             area_is_frame_reservation_not_mapped_LAT7_cell_area=True,
             timeout_policy={'synth': 'unlimited', 'flow': 'unlimited'})
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['args', 'model'])
    a = p.parse_args()
    print(shlex.join(predecessor.args(570.24)) if a.mode == 'args'
          else json.dumps(model(), indent=2))


if __name__ == '__main__':
    main()
