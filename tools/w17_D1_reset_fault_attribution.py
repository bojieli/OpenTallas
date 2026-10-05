"""Source-derived diagnostic model only; not an RTL simulator or actual mask capture."""
import hashlib
from pathlib import Path


def verify_pins(root, pins):
    for name, expected in pins.items():
        if hashlib.sha256((Path(root) / name).read_bytes()).hexdigest() != expected:
            raise ValueError("source pin mismatch: " + name)


def priming_timeline(extra_wait_cycles=0):
    if type(extra_wait_cycles) is not int or extra_wait_cycles < 0:
        raise ValueError("wait cycles must be a nonnegative integer")
    # All consumers sample OLD rst_s[1] at posedge; synchronizer updates in NBA.
    sync = 0
    valid = set()
    handshakes = []
    first_edge = 5500 + extra_wait_cycles * 1000
    last_edge = first_edge + 127000
    for ps in range(500, last_edge + 1, 1000):
        external_reset_released = ps >= 4000
        internal_run = bool(sync & 2)
        row = (ps - first_edge) // 1000 if ps >= first_edge else None
        ready = True  # IDLE, REFILL_CREDITS=1, no blk_v, valid region.
        if not internal_run:
            valid.clear()
        elif row is not None and ready:
            valid.add(row)
        if row is not None and ready:
            handshakes.append({"row": row, "time_ps": ps,
                               "consumer_out_of_reset": internal_run})
        sync = ((sync << 1) | 1) & 3 if external_reset_released else 0
    return {"handshakes": handshakes, "valid_rows": sorted(valid),
            "lost_rows": sorted(set(range(128)) - valid)}


def first_prefetch(valid_rows, descriptor_edge_ps=139500):
    # Source schedule SEND begins after descriptor NBA; prefetch is next edge.
    missing = 0 not in valid_rows
    return {"prefetch_edge_ps": descriptor_edge_ps + 1000,
            "row0_rejected": missing, "predicted_pf_fault_code": int(missing),
            "predicted_die_fault_mask": 0x40 if missing else 0,
            "sticky_fault_edge_ps": descriptor_edge_ps + 2000 if missing else None,
            "mask_observed": False, "service_bound": "BOUND_MISSING"}


def display_time_ps(raw_ps):
    # Verilator VL_TIME_UNITED_Q for module timeunit 1ns; log format is ps.
    if type(raw_ps) is not int or raw_ps < 0:
        raise ValueError("raw time must be a nonnegative integer")
    return ((raw_ps + 500) // 1000) * 1000


def admission(gates):
    names = ("waited", "q_gate", "m0_gate", "me_ready", "kv_ok", "kvd_v", "win_idle")
    if set(gates) != set(names) or any(type(gates[n]) is not bool for n in names):
        raise ValueError("exact typed gate packet required")
    return all(gates[n] for n in names if n != "kvd_v") and not gates["kvd_v"]


def drop_kv_ok_witness(before, after):
    if before != after:
        raise ValueError("mixed pre/NBA phases cannot qualify a predicate witness")
    expected = admission(before)
    mutant = dict(before, kv_ok=True)
    return not expected and admission(mutant)
