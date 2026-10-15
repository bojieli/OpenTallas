"""Static ABI of the S81 VM sequencer engine 12 (rtl/dsrom_sys/s81_ph/vm/dsfd_vm_seq_static.sv).

The compiler assigns every command cycle and counter slot; the RTL never waits.  This module encodes the 24-bit
engine argument and validates an engine-12 calendar against the RTL's fixed timing rules, so a program that would
raise a fault in silicon is rejected offline.  Cycles are engine pin cycles (stream clock).

  arg[23:21] = code; codes 0..3 = counter slot.
    ARM   slot: [20] client (0 SU, 1 HC), [19:10] base row / 16, [9:0] nrows - 1
    CHECK slot: [20] client, [19:10] = [9:0] = 0x3FF
  codes 4..7: native legacy VM ops, forwarded unchanged.
  Every command's done leaves the engine DLAT cycles after its pin.
"""

DLAT = 6
NSLOT = 4
ROWS = 16384
CHECK_FIELD = 0x3FF


def arm_arg(slot, client, base_row, nrows):
    if not 0 <= slot < NSLOT:
        raise ValueError(f"slot {slot} outside 0..{NSLOT - 1}")
    if client not in ("su", "hc"):
        raise ValueError(f"client {client}")
    if base_row % 16 or not 1 <= nrows <= 1024 or base_row < 0 or base_row + nrows > ROWS:
        raise ValueError("ARM range must be 16-row aligned, 1..1024 rows, inside 16384 rows")
    return (slot << 21) | (int(client == "hc") << 20) | ((base_row // 16) << 10) | (nrows - 1)


def check_arg(slot, client):
    if not 0 <= slot < NSLOT:
        raise ValueError(f"slot {slot} outside 0..{NSLOT - 1}")
    return (slot << 21) | (int(client == "hc") << 20) | (CHECK_FIELD << 10) | CHECK_FIELD


def validate(commands, commits=(), reads=()):
    """commands: [{cycle, kind: arm|check|native, slot, client, base_row, nrows}];
    commits: [(cycle, row)] actual native commit observations of operand rows; reads: [(cycle, row)].
    Returns (done_cycles, errors).  Rules mirror the RTL fault set (fault number in brackets)."""
    errors, done = [], {}
    by_cycle = {}
    for i, c in enumerate(commands):
        if c["cycle"] in by_cycle:
            errors.append(f"two engine-12 commands at cycle {c['cycle']}")
        by_cycle[c["cycle"]] = i
        done[i] = c["cycle"] + DLAT
    live = {}            # slot -> (arm cycle, lo, hi, client)
    windows = []         # (lo, hi, arm cycle, check cycle) of every verified arm
    for i in sorted(by_cycle.values(), key=lambda k: commands[k]["cycle"]):
        c = commands[i]
        t = c["cycle"]
        if c["kind"] == "native":
            continue
        s = c["slot"]
        if c["kind"] == "arm":
            arm_arg(s, c["client"], c["base_row"], c["nrows"])
            lo, hi = c["base_row"], c["base_row"] + c["nrows"]
            if s in live:
                errors.append(f"[4] ARM slot {s} at {t} before its CHECK")
            for o, (ta, olo, ohi, _) in live.items():
                if o != s and olo < hi and lo < ohi:
                    errors.append(f"[5] ARM slot {s} at {t} overlaps live slot {o}")
            live[s] = (t, lo, hi, c["client"])
        elif c["kind"] == "check":
            if s not in live:
                errors.append(f"[2] CHECK slot {s} at {t} not armed")
                continue
            ta, lo, hi, cl = live.pop(s)
            if cl != c["client"]:
                errors.append(f"[3] CHECK slot {s} at {t} client mismatch")
            windows.append((lo, hi, ta, t))
        else:
            errors.append(f"unknown kind {c['kind']}")
    for s, (ta, lo, hi, _) in live.items():
        errors.append(f"slot {s} armed at {ta} never CHECKed")
    for lo, hi, ta, tc in windows:
        rows = {}
        for cy, row in commits:
            if lo <= row < hi and ta < cy <= tc:
                rows[row] = rows.get(row, 0) + 1
            elif lo <= row < hi and cy == ta:
                errors.append(f"commit of row {row} at its ARM cycle {ta} is not counted (ARM pin + 1)")
        # word coverage is checked by the RTL (16 elements / row); here: every row must be committed in-window
        missing = [r for r in range(lo, hi) if r not in rows]
        if missing:
            errors.append(f"[0] arm {lo}..{hi} at {ta}: {len(missing)} rows not committed by CHECK {tc}")
        for cy, row in reads:
            if lo <= row < hi and ta < cy <= tc:
                errors.append(f"[7] read of row {row} at {cy} before its CHECK {tc}")
    return done, errors
