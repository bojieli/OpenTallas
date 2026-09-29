#!/usr/bin/env python3
"""V4.1 HBM region preflight for the W11 quarter-per-stack RING key layout.

Re-runs the capacity arithmetic of tools/v41_hbm_region_preflight.py (whose
record, results/arch/v41_hbm_region_preflight.json, stays as it is: status
capacity_mismatch for the replicated key layout) with the key placement and
widths of the W11 ring layout (ot_hdc_v41x_idx_ring_ranges / _ring_kwr /
_kstream_ring), and ties the verdict to the RTL gate record
results/rtl/w11_idx_ring_gate.json.  Writes a NEW record,
results/arch/w11_v41_hbm_region_preflight_ring.json.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import v41_hbm_region_preflight as base  # noqa: E402

OUT = ROOT / "results/arch/w11_v41_hbm_region_preflight_ring.json"
GATE = "results/rtl/w11_idx_ring_gate.json"
RING_SOURCES = ("rtl/hdc/v41x/ot_hdc_v41x_idx_ring_ranges.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_ring_kwr.sv",
                "rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_ring.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_quarter_join.sv",
                "rtl/rom/ot_rom_pkg_ctrl_x.sv", "rtl/chip/ot_chip_v41x_die.sv",
                "tools/v41_hbm_region_preflight.py", "tools/w11_v41_hbm_region_preflight_ring.py", GATE)


def sha(p: str) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def build() -> dict:
    ref = base.build()                       # asserts the legacy sources it reads
    gate = json.loads((ROOT / GATE).read_text())
    assert gate["status"] == "pass" and all(gate["verdicts"].values())
    full = next(c for c in gate["cases"] if c["name"] == "full_shape")
    p = full["parameters"]
    ranges = (ROOT / RING_SOURCES[0]).read_text()
    assert "parameter integer HW=23, UW=10, RSB=64, RTAIL=32" in ranges
    ctrl = (ROOT / RING_SOURCES[4]).read_text()
    die = (ROOT / RING_SOURCES[5]).read_text()
    assert ".USER_W(FULL_SHAPE ? 10 : 8)" in die and "MAXU     = FULL_SHAPE ? 866 : 16" in die
    assert re.search(r"K_HAW\s*=\s*FULL_SHAPE \? 30 : 28", die)
    assert "parameter integer USER_W       = 8" in ctrl

    inp = ref["inputs"]
    usable = ref["capacity"]["usable_bytes_per_stack"]
    rows_die = inp["rows_per_die_per_user"]
    rsb, rtail = p["RSB"], p["RTAIL"]
    slots = rsb * 1024 + rtail
    ublk = rsb * 17 + (1 + (rtail + 63) // 64 if rtail else 0)
    key_ring_bytes = ublk * 4096
    per_user = key_ring_bytes + ref["per_stack_per_user_bytes"]["ckv_striped"] + ref["per_stack_per_user_bytes"]["window"]
    users_ring = usable // per_user
    model_users = ref["capacity"]["users_model_striped_keys"]
    # longest quarter of any count N <= rows_die: quarter 3 = N - 3 Qs, Qs = 8 floor(N / 32)
    longest = max(n - 3 * (8 * (n // 32)) for n in range(rows_die - 64, rows_die + 1))
    longest = max(longest, 8 * (rows_die // 32))
    key_region_sectors = model_users * ublk * 128
    stack_sectors = inp["stack_capacity_bytes"] // 32
    rec = {
        "schema": "w11_v41_hbm_region_preflight_ring_v1",
        "status": "capacity_match" if users_ring >= model_users else "capacity_mismatch",
        "supersedes_for_ring_layout": "results/arch/v41_hbm_region_preflight.json (replicated keys: 551 users)",
        "scope": "1M ratio-1 layer-20 die; keys in the W11 quarter-per-stack ring layout (each stack holds one "
                 "position quarter: striped, not replicated); CKV and window as in the reference preflight",
        "inputs": inp,
        "ring": {"super_blocks": rsb, "tail_keys": rtail, "slots": slots,
                 "longest_quarter_keys": longest, "fits": longest <= slots,
                 "blocks_per_user_per_stack": ublk, "key_bytes_per_user_per_stack": key_ring_bytes,
                 "model_striped_key_bytes_per_user_per_stack": ref["per_stack_per_user_bytes"]["key_striped"],
                 "tail_overhead_bytes_per_user_per_stack": key_ring_bytes - ref["per_stack_per_user_bytes"]["key_striped"]},
        "capacity": {"usable_bytes_per_stack": usable, "per_user_bytes_per_stack": per_user,
                     "users_ring_layout": users_ring, "users_model": model_users,
                     "users_replicated_reference": ref["capacity"]["users_current_replicated_keys"],
                     "model_users_fit": users_ring >= model_users},
        "widths": {"sector_address_bits": p["AW"], "block_counter_bits": p["HW"],
                   "key_region_sectors_for_model_users": key_region_sectors,
                   "key_region_bits": (key_region_sectors - 1).bit_length(),
                   "stack_sectors": stack_sectors, "stack_sector_bits": (stack_sectors - 1).bit_length(),
                   "user_id_bits": p["UW"], "user_id_bits_needed": (model_users - 1).bit_length(),
                   "controller_user_id_bits_full_shape": 10,
                   "die_hbm_sector_address_bits_full_shape": 30},
        "rtl_evidence": {"gate_record": GATE, "full_shape_users": sorted({r["user"] for r in full["reads"]}),
                         "keys_checked": full["checked_keys"], "max_sector_address": full["max_sector_address"],
                         "key_region_base_block": p["KB"],
                         "key_region_top_sector": (p["KB"] + model_users * ublk) * 128 - 1},
        "isolation": {"standalone_multiuser_key_address_isolation": True,
                      "die_integrated": False,
                      "reason": "the ring gate writes and reads four users (0, 481, 551, 865) of an 866-user "
                                "region with every HBM request checked against its user's region; the die "
                                "(ot_chip_v41x_die) still uses the replicated key path and ties the key user base low"},
        "source_sha256": {s: sha(s) for s in RING_SOURCES},
    }
    assert rec["ring"]["fits"]
    assert rec["widths"]["user_id_bits"] >= rec["widths"]["user_id_bits_needed"]
    assert rec["widths"]["stack_sector_bits"] <= rec["widths"]["sector_address_bits"]
    assert rec["rtl_evidence"]["key_region_top_sector"] < (1 << p["AW"])
    return rec


def main() -> None:
    rec = build()
    if OUT.exists():
        raise SystemExit(f"{OUT} exists; records are never overwritten")
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(rec["status"], rec["capacity"])


if __name__ == "__main__":
    main()
