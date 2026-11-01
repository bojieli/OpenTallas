#!/usr/bin/env python3
"""DIE-QC-59E 11-01: QC forwarded epoch / link reset = real package pads (one-block plan fix, glue type only).

Finding (TOK-QK-2 05:17, COORD 08:5x): in the bound QC die the glue leaves u_bump_fwd_epoch / u_bump_fwd_lrst are
qfd_sigbump #(RV 0) constant cells (the as-built die has no line side for them) feeding u_d2d_rom / u_sys_face
.fwd_epoch / .fwd_link_rst_n through 5-stage landings: as bound the QC d2d end stays in link reset with no epoch and
the die can never start a token.  The KV die drives these signals off-die (sys_c u_fwb_ep / u_fwb_rs package bumps).

Fix, the same form as the QC UCIe PHY line side (phy_ucie_kv u_ucie_kv bump_ports -> die ports ucie_kv_far_*): the
two glue contents entries declare their hard-IP LINE SIDE (tools/die_plan/bind.py bump_pins):
  * module = qfd_sigbump (the actual as-built master; the entry carried the instance label, which the binder's
    hard-core match compares against the bound leaf);
  * bump_ports [{pin pad_i, dir input, width 1, die_port glue__bump_fwd_<epoch|lrst>__pad_i, params {PAD: 1}}]:
    the binder connects the bump receiver's pad_i to a glue partition port bump_bump_fwd_<x>_pad_i and a die-top
    input glue_bump_fwd_<x>_pad_i (short_id of the declared name), and binds the leaf with PAD=1 so o follows the pad
    (rtl/qwen_split/qfd_link_slots.sv qfd_sigbump; PAD=0 = the as-built constant, unchanged everywhere else).
No other field, type, bus, lane, clock, reset, outline or partition changes; the 5-stage landings stay as they are.
usage: delta_fwdpad_1101.py PLAN_IN PLAN_OUT [RECEIPT.json]   (PLAN_IN == PLAN_OUT rewrites in place)"""
import hashlib
import json
import sys
from pathlib import Path

TYPE = "glue"
MASTER = "qfd_sigbump"
BUMPS = {"u_bump_fwd_epoch": "glue__bump_fwd_epoch__pad_i", "u_bump_fwd_lrst": "glue__bump_fwd_lrst__pad_i"}
NOTE = ("DIE-QC-59E 11-01 package pad (line side of the bump receiver; the KV die drives it through the package, "
        "sys_c u_fwb_*): pad_i -> die-top input, PAD=1 so o follows the pad instead of the as-built constant")


def apply(raw):
    t = raw["partition_types"][TYPE]
    seen = {}
    for c in t.get("contents", []):
        if c.get("inst") not in BUMPS:
            continue
        if c.get("bump_ports"):
            raise SystemExit(f"refuse: {TYPE}/{c['inst']} already declares bump_ports {c['bump_ports']}")
        if c.get("module") not in (MASTER, c["inst"][2:]):
            raise SystemExit(f"refuse: {TYPE}/{c['inst']} module {c.get('module')!r} is neither the label nor {MASTER}")
        seen[c["inst"]] = dict(module_before=c.get("module"))
        c["module"] = MASTER
        c["bump_ports"] = [dict(pin="pad_i", dir="input", width=1, die_port=BUMPS[c["inst"]], params={"PAD": 1},
                                note=NOTE)]
    if set(seen) != set(BUMPS):
        raise SystemExit(f"refuse: {TYPE} contents lack {sorted(set(BUMPS) - set(seen))}")
    # no other type may already hold these die-port names
    for tn, tt in raw["partition_types"].items():
        for e in tt.get("contents", []) + tt.get("hard_cores", []):
            for b in e.get("bump_ports") or []:
                if tn != TYPE and b.get("die_port") in BUMPS.values():
                    raise SystemExit(f"refuse: die port {b['die_port']} already declared by {tn}/{e['inst']}")
    return seen


def main(argv):
    if len(argv) not in (3, 4):
        raise SystemExit(__doc__)
    pin, pout = Path(argv[1]), Path(argv[2])
    src = pin.read_bytes()
    raw = json.loads(src)
    if json.dumps(raw).encode() != src.rstrip(b"\n"):
        raise SystemExit("plan does not round-trip through json.dumps byte-exactly; refusing to rewrite")
    before = json.loads(src)
    seen = apply(raw)
    # the delta touches only the two glue contents entries
    a, b = json.loads(json.dumps(before)), json.loads(json.dumps(raw))
    ga, gb = a["partition_types"].pop(TYPE), b["partition_types"].pop(TYPE)
    assert a == b, "delta changed something outside the glue type"
    ca, cb = ga.pop("contents"), gb.pop("contents")
    assert ga == gb and len(ca) == len(cb), "delta changed glue fields other than contents"
    assert [x for x, y in zip(ca, cb) if x != y and x["inst"] not in BUMPS] == []
    out = (json.dumps(raw) + ("\n" if src.endswith(b"\n") else "")).encode()
    pout.write_bytes(out)
    rec = dict(schema="opentallas.qc_fwdpad_delta.v1", lane="DIE-QC-59E", plan_in=str(pin), plan_out=str(pout),
               sha256_before=hashlib.sha256(src).hexdigest(), sha256_after=hashlib.sha256(out).hexdigest(),
               type=TYPE, entries=seen, die_ports=BUMPS)
    if len(argv) == 4:
        Path(argv[3]).write_text(json.dumps(rec, indent=1) + "\n")
    print("PASS", rec["sha256_before"][:12], "->", rec["sha256_after"][:12])


if __name__ == "__main__":
    main(sys.argv)
