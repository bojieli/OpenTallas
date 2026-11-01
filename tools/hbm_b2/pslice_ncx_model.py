#!/usr/bin/env python3
"""No-cycle L-column closure candidate; estimates precede any prototype, no rate claim."""
import json


def model():
    macro_w,macro_h=94.824,41.064
    return dict(schema='opentallas.hbm-pslice-ncx-column.v1',candidate=True,
      top='ot_hbm_su_programme_pslice_c5',core_outline_um=[939.6,760.32],
      command_bits_per_cycle=2470,logical_columns=10,large_columns=3,small_columns=7,
      macro_count=3*17+7*7,macro_outline_um=[macro_w,macro_h],
      macro_area_um2=100*macro_w*macro_h,macs_per_cycle=0,
      memory_port_bytes_per_cycle=32,configuration_bits_per_cycle=280,
      source='c5e7639295724dcf76eb43a27ae588732f7cbc74:ot_hbm_su_programme_pgcol.sv',
      stale_recipe_source='d34578d6f',candidate_params=dict(SB=2470,NCX=1),
      changed_replicas='L-column index/dictionary capture enables and equal-age reset copies',
      multiplexing='same 13 dictionary banks; bank-local selects and capture enables',
      latency_delta_cycles=0,token_latency_delta_cycles=0,throughput_ratio=1.0,
      floorplan_candidate=dict(columns=7,rows=15,vertical_street_um=35,
        horizontal_street_um=8.64,used_width_um=7*macro_w+6*35,
        used_height_um=15*macro_h+14*8.64,slots=105),
      constraints='existing pins/outline/833ps TT FF; plan-local affinity and multi-taps required',
      qualification='lockstep plus seeded phase mutant; geometry review before prototype; routed signoff pending')


if __name__=='__main__':
    print(json.dumps(model(),indent=2))
