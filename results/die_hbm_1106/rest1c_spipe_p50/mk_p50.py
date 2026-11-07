#!/usr/bin/env python3
"""HBM-FORM-TIMING-13 d44v part 50 (plan-owner approved DIE-HBM-82 11-06): plan-of-record edits for the rest_1c
scalar-data pin cycle.  Run after gen_p50.py.  Idempotent.
  * recipes_b2.json: + ot_hgi_sfu_split3_ctl_rest_1c__spipe1 (= rest_1c recipe + define OT_REST1C_SCALAR_PIPE1)
  * d44v/corelat/cycles_rest1c_spipe_1106.tsv: u_core_u_vm_scalar_data +1, every other port 0
  * d44v/compiler_core_delta.json: pending_not_folded row
  * d44v/part50_event.json, README paragraph, SHA256SUMS rows
No geometry, pin table, clock entry or conn change: die_plan.json / core pin files / sidecars are untouched.
    mk_p50.py REPO"""
import hashlib
import json
import sys
from pathlib import Path

R = Path(sys.argv[1])
D = R / "physical/die_plan/hbm/plan_of_record/d44v"
CORE = "ot_hgi_sfu_split3_ctl_rest_1c"
FORM = CORE + "__spipe1"
DEF = "OT_REST1C_SCALAR_PIPE1"
BUS = "u_core_u_vm_scalar_data"
WHY = ("vA (TT -81.68 ps, 119 endpoints) and vB2 (TT -92.83 ps, 126 endpoints) both failed TT only on rest flops -> "
       "32-fanout select + AO222 3:1 mux -> ~350 ps of wire -> the u_core_u_vm_scalar_data output face (792 ps data "
       "at 833 ps); two strikes -> RE-FORM with one pin cycle")
PROOF = ("results/die_hbm_1106/rest1c_spipe_p50/PROOF.txt: yosys equiv gold (part-37 rest_1c + 1 register on "
         f"{BUS}) vs {FORM} PASS, default text vs part 37 exact PASS, mutant (2 scalar bits swapped) FAIL")

# recipe
rp = R / "physical/die_plan/hbm_arch_cores/recipes_b2.json"
rec = json.loads(rp.read_text())
base = dict(rec[CORE])
base["defines"] = [DEF]
base["source"] = (f"HBM-FORM-TIMING-13 d44v part 50 (plan-owner approved DIE-HBM-82 11-06): {CORE} + define {DEF} = "
                  f"PIN CYCLE +1 on {BUS}[127:0] (register between the rest core and the port), every other port "
                  f"exact; {PROOF}")
rec[FORM] = base
rp.write_text(json.dumps(rec, indent=2) + "\n")

# corelat
cl = D / "corelat/cycles_rest1c_spipe_1106.tsv"
cl.write_text("core\tsub_block\tport_or_bus\tdir\tadded_cycles\tnote\n"
              f"{CORE}\t\t{BUS}\tport\t1\tHBM-FORM-TIMING-13 part 50: recipe {FORM} (define {DEF}); {WHY}; {PROOF}\n"
              f"{CORE}\t\tall other outputs (incl. seam_d)\tport\t0\tpart 50: exact\n")

# compiler delta
cp = D / "compiler_core_delta.json"
cd = json.loads(cp.read_text())
cd["pending_not_folded"]["HBM-FORM-TIMING-13 rest_1c scalar pipe (part 50)"] = (
    f"{CORE} {BUS} +1 (corelat/cycles_rest1c_spipe_1106.tsv): the scalar_load -> scalar_data response of the SFU ctl "
    f"arrives one cycle later at vm; applies when the {FORM} form ({DEF}) is the built form; fold into the vm scalar "
    "response latency at the next ext_census regen (TOK lane). Owner 12.21: tok/s loss from closure fixes accepted")
cp.write_text(json.dumps(cd, indent=1) + "\n")

# event
ev = {
    "schema": "opentallas.hbm_plan_event.part50",
    "by": "HBM-FORM-TIMING-13 11-06, plan-owner approved DIE-HBM-82 (owner 11-03: pin cycles are a cheap lever)",
    "core": CORE,
    "change": f"PIN CYCLE +1 on {BUS}[127:0] via recipe {FORM} (define {DEF}); outline, pins, clock entry, conns unchanged",
    "why": WHY,
    "rtl": "rtl/hbm_accel/cores_split/ot_hgi_sfu_core_split3/ot_hgi_sfu_split3_ctl_rest_1c.sv (gen_p50.py; default = wire)",
    "proof": PROOF,
    "pin_cycles": f"corelat/cycles_rest1c_spipe_1106.tsv: {BUS} +1; all other ports exact",
    "geometry": "none: die_plan.json, core pin files, clock_entries, core_conns untouched (G0/G0C NEW 0 by construction)",
    "replay": "results/die_hbm_1106/rest1c_spipe_p50/replay_p50.sh",
}
(D / "part50_event.json").write_text(json.dumps(ev, indent=1) + "\n")

# README
rd = D / "README.md"
txt = rd.read_text()
para = (f"Event part 50 (HBM-FORM-TIMING-13 11-06, plan-owner approved DIE-HBM-82): {CORE} PIN CYCLE +1 on {BUS}[127:0] "
        f"for the RE-FORM recipe {FORM} (define {DEF}, one register between the rest core and the port; default text = "
        "wire, part-37 function). Two TT strikes on the same reach class (vA -81.68, vB2 -92.83 ps into the "
        "vm_scalar_data face). No geometry change. corelat/cycles_rest1c_spipe_1106.tsv; compiler_core_delta pending row; "
        "part50_event.json; proof + replay results/die_hbm_1106/rest1c_spipe_p50.\n")
if "Event part 50 " not in txt:
    rd.write_text(txt.rstrip("\n") + "\n\n" + para)

# SHA256SUMS
sp = D / "SHA256SUMS"
rows = [l for l in sp.read_text().splitlines() if l.strip()]
names = [l.split("  ", 1)[1] for l in rows]
for rel in ("README.md", "compiler_core_delta.json", "part50_event.json", "corelat/cycles_rest1c_spipe_1106.tsv"):
    h = hashlib.sha256((D / rel).read_bytes()).hexdigest()
    if rel in names:
        rows[names.index(rel)] = f"{h}  {rel}"
    else:
        rows.append(f"{h}  {rel}"); names.append(rel)
sp.write_text("\n".join(rows) + "\n")
print("part 50 written")
