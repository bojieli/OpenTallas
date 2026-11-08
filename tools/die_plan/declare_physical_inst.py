#!/usr/bin/env python3
"""DIE-HBM-90-TNAME 11-07: plan event that declares the bound leaf name of a hard core whose plan inst differs from it.

Cause (HBM class (i), root kit_rtl "core clock clk_c12: expected one bound leaf u_mu_fused_program, got 0"): the
C25b plan rows of the fused host programme say u_mu_fused_program, while the as-built RTL of record (bind inputs
t11_top.sv: ot_hnx_fused_host_program u_mu_fused_programme) and the bind map (t5_map.json parts:
u_mu_fused_programme -> root u_mu_fused_programme) name it u_mu_fused_programme, so the bound leaf is
u_u_mu_fused_programme.  The plan side is stale.

The fix uses the plan's own field for this case (DIE-QC-69, gen_phys.content_physical_identity): the hard_cores[] row
gets physical_inst NEW and physical_master = its module.  The logical plan identity (inst, contents[], clock tap names,
core_conns.json) stays, so the die-wide native bind receipt (kit_topology native_contract, which digests every type's
clock taps) stays valid and the bind of record need not be re-run; kit-rtl, core_tap_rows and the kit placement read
the physical identity.

Applied only when all of these hold (else the tool fails closed, nothing written):
  1. type T has exactly one hard_cores[] row with inst OLD, and it has no physical_inst / physical_master yet;
  2. the bound RTL module of T (--bound-rtl DIR) has exactly one leaf u_NEW (or NEW), and no leaf u_OLD / OLD;
  3. that leaf's master is the row's module (same core, only the name differs).
PIN CYCLES 0, no logic change; every other field byte for byte unchanged.

    declare_physical_inst.py PLAN_IN PLAN_OUT LEDGER --type T --old OLD --new NEW --bound-rtl DIR
"""
import argparse
import gzip
import json
import re
import sys
from pathlib import Path


def bound_rtl_file(rtl_dir, raw, tn):
    mod = raw["partition_types"][tn].get("module", "")
    for name in (f"{mod}__{tn}.sv", f"hbm_arch_{tn}.sv", f"{mod}.sv"):
        f = Path(rtl_dir) / name
        if f.is_file():
            return f
    return None


def leaves(txt, name):
    """[master] of every leaf instance `name` in the text."""
    return re.findall(r"^[ \t]+(\w+)(?:[ \t]+#\([^\n]*\))?[ \t]+" + re.escape(name) + r"[ \t]*\(", txt, re.M)


def apply(raw, tn, old, new, rtl_dir):
    """-> (raw, ledger); SystemExit when a precondition fails."""
    T = raw["partition_types"]
    if tn not in T:
        raise SystemExit(f"declare_physical_inst: no type {tn}")
    rows = [c for c in T[tn].get("hard_cores", []) or [] if c.get("inst") == old]
    bad = []
    if len(rows) != 1:
        bad.append(f"{tn}: {len(rows)} hard_cores rows {old}, expected 1")
    elif "physical_inst" in rows[0] or "physical_master" in rows[0]:
        bad.append(f"{tn}: {old} already declares a physical identity")
    f = bound_rtl_file(rtl_dir, raw, tn)
    masters = []
    if f is None:
        bad.append(f"{tn}: no bound RTL in {rtl_dir}")
    else:
        txt = f.read_text()
        masters = leaves(txt, "u_" + new) + leaves(txt, new)
        if len(masters) != 1:
            bad.append(f"{tn}: bound RTL {f.name} has {len(masters)} leaf u_{new}/{new}, expected 1")
        elif rows and masters[0] != rows[0].get("module"):
            bad.append(f"{tn}: bound leaf u_{new} is {masters[0]}, the plan core is {rows[0].get('module')}")
        if leaves(txt, "u_" + old) + leaves(txt, old):
            bad.append(f"{tn}: bound RTL {f.name} still has a leaf u_{old}/{old}")
    if bad:
        raise SystemExit("declare_physical_inst: fail closed, nothing written:\n  " + "\n  ".join(bad))
    row = rows[0]
    row["physical_inst"], row["physical_master"] = new, row["module"]
    i = T[tn]["hard_cores"].index(row)
    ledger = dict(schema="opentallas.declare_physical_inst.v1", type=tn, inst=old, physical_inst=new,
                  physical_master=row["module"], bound_rtl=str(f), bound_leaf_master=masters[0],
                  plan_fields=[f"partition_types.{tn}.hard_cores.{i}.physical_inst",
                               f"partition_types.{tn}.hard_cores.{i}.physical_master"])
    return raw, ledger


def _load(p):
    p = Path(p)
    return json.loads(gzip.open(p).read() if p.suffix == ".gz" else p.read_text())


def _dump(obj, p):
    p = Path(p)
    data = json.dumps(obj).encode()
    if p.suffix == ".gz":
        with gzip.GzipFile(p, "wb", mtime=0) as g:
            g.write(data)
    else:
        p.write_bytes(data)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("ledger")
    ap.add_argument("--type", required=True)
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--bound-rtl", required=True)
    a = ap.parse_args(argv)
    raw, ledger = apply(_load(a.plan_in), a.type, a.old, a.new, a.bound_rtl)
    note = f"DIE-HBM-90-TNAME declare_physical_inst {a.type} {a.old} -> bound leaf {a.new}"
    raw["note"] = note + " <- " + raw.get("note", "") if raw.get("note") else note
    _dump(raw, a.plan_out)
    Path(a.ledger).write_text(json.dumps(ledger, indent=1, sort_keys=True) + "\n")
    print(note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
