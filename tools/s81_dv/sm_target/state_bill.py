#!/usr/bin/env python3
"""Count this component's scalar/packed state declarations; no synthesis claim."""
import hashlib
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[3]
src = root / 'rtl/dsrom_sys/s81_dv/sm_target/dsdv_sm_so_target.sv'
state = {}
for line in src.read_text().splitlines():
    line = line.split('//')[0].strip()
    m = re.fullmatch(r'reg\s*(?:\[(\d+):(\d+)\])?\s+([^;]+);', line)
    if m:
        width = abs(int(m[1])-int(m[2]))+1 if m[1] else 1
        for name in m[3].split(','):
            state[name.strip()] = width
    m = re.fullmatch(r'output reg\s*(?:\[(\d+):(\d+)\])?\s+(\w+),?', line)
    if m:
        state[m[3]] = abs(int(m[1])-int(m[2]))+1 if m[1] else 1
# `bad` is explicitly an always-@* result, not storage.
state.pop('bad')
assert sum(state.values()) == 2729, state
rec = dict(
    verdict='DECLARED_STATE_ONLY_NOT_MAPPED_OR_PHYSICALLY_QUALIFIED',
    source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
    state_bits=state, total_ff_per_head=sum(state.values()),
    total_ff_16_targets=16*sum(state.values()),
    target_macros_per_head=4, target_macros_16_heads=64,
    target_payload_bits_per_head=8192, target_payload_bits_all_heads=131072,
    additional_pre_SO_transpose_macros=128,
    target_plus_transpose_macro_count=192,
    target_plus_transpose_payload_bits=393216,
    target_macros_historical_area_per_head_um2=4*552.40704,
    target_macros_historical_area_16_heads_um2=64*552.40704,
    macro_family='historical b65718325 ot_sram_1r1w_32x64_m1; no new physical qualification',
    useful_write_bits_per_cycle_per_head=256,
    read_bits_per_cycle_per_head=256,
    read_cycles_per_job=32, unique_beats_per_head=8,
    unique_beats_per_rank=128, delivered_beats_at_16_destinations=1024,
    gather_output_boundary_bits=1053,
    independent_config_bits=114,
    logic_MACs_per_cycle=0,
    physical_reset_select_copies=None,
    mapped_std_area_um2=None, macro_clock_cap_fF=None,
    source_expanded_all_driver_fanout=None, maximum_wire_um=None,
    actual_parent_accepted_owner_source=None,
    parent_accepted_destination_retire=None,
    composed_SU_latency=None, composed_MU_schedule=None,
)
out = root/'results/rtl/s81_sm_target_1020/declared_state.json'
out.write_text(json.dumps(rec, indent=2, sort_keys=True)+'\n')
print('declared FF/head', sum(state.values()), 'SRAM/head 4; physical and parent composition HOLD')
