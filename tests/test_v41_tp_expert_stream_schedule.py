"""Data readiness may change timing but cannot change the MoE arithmetic order."""

import json
import struct
from pathlib import Path

from tools.v41_tp_expert_stream_schedule import build, schedule

ROOT = Path(__file__).resolve().parents[1]


def _f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def _bf16_rne(x):
    bits = struct.unpack("<I", struct.pack("<f", _f32(x)))[0]
    # Test finite values; the schedule never changes the target NaN policy.
    assert bits & 0x7f800000 != 0x7f800000
    return struct.unpack("<f", struct.pack("<I", (bits + 0x7fff + ((bits >> 16) & 1)) & 0xffff0000))[0]


def _ordered_sum(expert_values, completion):
    # The readiness order can differ, but each expert result is committed by
    # expert ID, and the shared expert is last.  Mirror the golden's BF16
    # per-expert boundary and FP32 ordered accumulation.
    ready = {expert: _bf16_rne(expert_values[expert]) for expert in completion}
    accum = ready[0]
    for expert in range(1, 7):
        accum = _f32(accum + ready[expert])
    return struct.pack("<f", accum)


def test_grouped_schedules_preserve_order_and_bound():
    values = [0.1993, -0.0338, 0.1519, 0.00127, -0.3526, 0.0109, 0.0156]
    serial = _ordered_sum(values, range(7))
    for group in (1, 2, 3, 7):
        s = schedule(4948, 102, group_size=group)
        assert s["arithmetic_order"] == list(range(7))
        assert s["vm_minimum_cycles"] == 1064
        assert s["scheduled_completion_cycles"] <= s["serial_completion_cycles"]
        assert _ordered_sum(values, s["arithmetic_order"]) == serial
    assert schedule(4948, 102, group_size=7)["hidden_w2_cycles"] == 0


def test_record_is_current_and_only_a_small_bound():
    rec = build()
    pinned = json.loads((ROOT / "results/arch/v41_tp_expert_stream_schedule.json").read_text())
    assert rec == pinned
    assert rec["points"]["1048576"]["by_ready_group"]["1"]["gain_fraction"] < 0.05
    assert rec["points"]["1048576"]["by_ready_group"]["7"]["gain_fraction"] == 0
