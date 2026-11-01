#!/usr/bin/env python3
"""DIE-KV-60 ctlin (COORD 11-01 09:1x, KV-FN-7 shared class): one face capture register per external boot input bit.

    python3 kvsctl_boot_capture.py LEAF.sv OUT.sv [--ledger L.json]     (or kvsctl_current_profile.py --boot-capture)

Why: the ctl kit's face_guard 'shared' class beyond the 48 constant o_hroot flops (KV-FN-7 keepdc_b fails_B, 101 bits)
is the boot stream fanning straight into u_boot logic: boot_pr 75 + boot_pr[142] + boot_image_epoch 16 +
boot_image_target 4 + boot_image_ready + boot_image_fault, and d2d__svc[23] (u_boot execution_active).  boot_pr[74] is a
per-cycle write strobe with its address / data, so a static / false-path declaration (strap form) does not apply: the
pins carry a live 833 ps path.  The industry form is a pin capture register.

Form: every EXTERNAL input of u_boot (boot__boot_pr live bits [74:0] + [142], boot_image_target / ready / fault /
epoch / digest, execution_active = d2d__svc[23]) passes one plain capture flop (no reset: an exact one-edge delay,
the same as one more relay stage on the boot leg), so u_boot sees its whole outside world one edge later and every
u_boot-internal loop (sink_applied, configured, diecfg sealed/fault) keeps its timing.  Cost: boot only, +1 edge on
the one-time boot (the bb6d423642 (a) +1 boot-landing class); mission schedule +0.  boot_pr[141:75] are the
measured-dead bits (kvsctl_dead_drop): left uncaptured.  digest has no face_guard failure but is captured too, so the
boot group stays edge-aligned.  Applied to BOTH gold and gate of the materializer (like the +1 dcfg landings), so the
face / profile proofs compare like with like.
"""
import argparse
import json
from pathlib import Path

INST = "u_boot (.ck(ck), .rst_n(rst_n), "
CONN = [  # (u_boot port, original actual, capture reg, width)
    ("boot_pr", "boot__boot_pr", "cb_boot_pr", 143),
    ("boot_image_target", "boot__boot_image_target", "cb_boot_image_target", 4),
    ("boot_image_ready", "boot__boot_image_ready", "cb_boot_image_ready", 1),
    ("boot_image_fault", "boot__boot_image_fault", "cb_boot_image_fault", 1),
    ("boot_image_epoch", "boot__boot_image_epoch", "cb_boot_image_epoch", 16),
    ("boot_image_digest", "boot__boot_image_digest", "cb_boot_image_digest", 64),
    ("execution_active", "d2d__svc[23:23]", "cb_execution_active", 1),
]
DEAD_PR = (75, 141)            # boot_pr bits measured dead (not captured; passed through unchanged)
MARK = "DIE-KV-60 ctlin boot capture"


def apply(text):
    if MARK in text:
        raise ValueError("boot capture already applied")
    lines = text.split("\n")
    hit = [i for i, l in enumerate(lines) if INST in l and "qkd_static_kv_boot_dispatch" in l]
    if len(hit) != 1:
        raise ValueError(f"expected one u_boot boot_dispatch instance line, found {len(hit)}")
    i = hit[0]
    line = lines[i]
    regs, assigns = [], []
    for port, actual, reg, w in CONN:
        old = f".{port}({actual})"
        if line.count(old) != 1:
            raise ValueError(f"u_boot .{port} is not connected to {actual} (re-derive the capture set)")
        line = line.replace(old, f".{port}({reg})")
        if reg == "cb_boot_pr":
            lo, hi = DEAD_PR
            regs.append(f"reg [{lo - 1}:0] cb_boot_pr_lo; reg cb_boot_pr_142;")
            assigns.append(f"cb_boot_pr_lo <= {actual}[{lo - 1}:0]; cb_boot_pr_142 <= {actual}[142];")
            regs.append(f"wire [142:0] cb_boot_pr = {{cb_boot_pr_142, {actual}[{hi}:{lo}], cb_boot_pr_lo}};")
        else:
            regs.append(f"reg [{w - 1}:0] {reg};" if w > 1 else f"reg {reg};")
            assigns.append(f"{reg} <= {actual};")
    block = [f"    // {MARK} (COORD 11-01 09:1x, KV-FN-7 shared class): one plain capture flop per external u_boot input",
             "    // bit (exact one-edge delay = one more boot-leg relay stage; boot +1 edge, mission +0; dead boot_pr[141:75]",
             "    // pass through).  physical/die_plan/qwen_kvsys/cores/harden/kvsctl_boot_capture.py"]
    block += ["    " + r for r in regs]
    block += ["    always @(posedge ck) begin " + " ".join(assigns) + " end"]
    lines[i:i + 1] = block + [line]
    bits = sum(w for _, _, _, w in CONN) - (DEAD_PR[1] - DEAD_PR[0] + 1)
    ledger = dict(transform=MARK, captured_bits=bits, dead_uncaptured="boot_pr[141:75]", boot_cycles_added=1,
                  mission_cycles_added=0, reset="none (plain capture = relay stage)",
                  ports=[dict(port=p, actual=a, reg=r, width=w) for p, a, r, w in CONN])
    return "\n".join(lines), ledger


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("leaf")
    ap.add_argument("out")
    ap.add_argument("--ledger")
    a = ap.parse_args()
    text, led = apply(Path(a.leaf).read_text())
    Path(a.out).write_text(text)
    if a.ledger:
        Path(a.ledger).write_text(json.dumps(led, indent=1) + "\n")
    print(json.dumps({k: v for k, v in led.items() if k != "ports"}))


if __name__ == "__main__":
    main()
