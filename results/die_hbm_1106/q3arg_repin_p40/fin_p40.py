#!/usr/bin/env python3
"""DIE-HBM-82 d44v part 40 packaging (after mk_p40.py): pin-cycle row, compiler delta, event record, README line,
SHA256SUMS.   fin_p40.py REPO"""
import gzip, hashlib, json, sys
from pathlib import Path
R = Path(sys.argv[1])
D = R / "physical/die_plan/hbm/plan_of_record/d44v"
NEW = "cores/ot_hfd_coll_q3_edge_arg__276.48x43.2__d44v_repin_hg8.json"
CYC = "corelat/cycles_q3arg_fpipe_1106.tsv"
sha = lambda b: hashlib.sha256(b).hexdigest()

# declared pin cycles of the HBM-GAPS-9 pin-cycle form (claude/hbm-gaps-9-q3fp-1106@6305fade5a)
(D / CYC).write_text(
    "core\tsub_block\tport_or_bus\tdir\tadded_cycles\tnote\n"
    "ot_hfd_coll_q3_edge_arg\t\tfault\tport\t1\tHBM-GAPS-9 pin-cycle form, part 40: recipe ot_hfd_coll_q3_edge_arg__fpipe "
    "(define OT_Q3ARG_FAULT_PIPE, two-stage duplicate check ot_hgi_coll_argmax_static_fp); fault-only (not priced); "
    "equiv_induct 7357/7357 + lock-step bench 200k cycles, mutants caught (over_cap_split/reform_1106/q3_edge_arg_repin/fault_pipe)\n"
    "ot_hfd_coll_q3_edge_arg\t\tout_v,out_flit\tport\t0\tpart 40: exact (all other outputs unchanged)\n")
cd = D / "compiler_core_delta.json"
K = json.loads(cd.read_text())
K["pending_not_folded"]["HBM-GAPS-9 q3_edge_arg fault pipe (part 40)"] = (
    "ot_hfd_coll_q3_edge_arg fault +1 (corelat/cycles_q3arg_fpipe_1106.tsv): fault-only flag, no data-path or tok/s change; "
    "applies when the __fpipe form (OT_Q3ARG_FAULT_PIPE) is the built form; fold at the next ext_census regen")
cd.write_text(json.dumps(K, indent=1) + "\n")

ev = {"schema": "opentallas.hbm_plan_event.part40",
      "by": "DIE-HBM-82 11-06 (COORD 13:37 RULINGS (1) + DIE-HBM-81 plan-owner ruling 13:37)",
      "core": "ot_hfd_coll_q3_edge_arg", "instances": ["q_hub_nw u_hb_coll_Q_edge__q0__arg"],
      "change": "same-slot re-pin: the 547 S-face M5 pins (y 0.096) spread in x 8.664-267.816 on M5 tracks, bit order kept; "
                "outline 276.48x43.2, origin, orient, track offset, 425 E-face M4 pins and the centre clk pin / clock entry unchanged",
      "why": "GRT-0232 corner overflow on vA + vB with the d44v_split table (547 S pins packed into x 138-276 next to 425 E pins)",
      "tables": {"ot_hfd_coll_q3_edge_arg": {
          "pins_file_from": "cores/ot_hfd_coll_q3_edge_arg__276.48x43.2__d44v_split.json",
          "pins_file": NEW, "sha256": sha((D / NEW).read_bytes()), "view": "ot_hfd_coll_q3_edge_arg@9ae65807400d",
          "made_by": "physical/die_plan/hbm/over_cap_split/reform_1106/q3_edge_arg_repin/repin_q3_edge_arg.py (HBM-GAPS-8 6edc0ba242, deterministic)",
          "gate_kit": "epyc5 /srv/opentallas-scratch2/claude/hbm-gaps-8/q3/ot_hfd_coll_q3_edge_arg_vA/ot_hfd_coll_q3_edge_arg_9ae65807400d (ROUTED, GRT0, DRC 0, ant 0)"}},
      "sidecars": "none changed: core_conns are by pin name; the clock tap / clock_entries point is the unchanged core centre",
      "pin_cycles": CYC + ": fault +1 (HBM-GAPS-9 form, recipe ot_hfd_coll_q3_edge_arg__fpipe, define OT_Q3ARG_FAULT_PIPE, "
                    "claude/hbm-gaps-9-q3fp-1106@6305fade5a); out_v / out_flit exact",
      "replay": "results/die_hbm_1106/q3arg_repin_p40/replay_p40.sh"}
(D / "part40_event.json").write_text(json.dumps(ev, indent=1) + "\n")

rd = D / "README.md"
rd.write_text(rd.read_text().rstrip("\n") + "\n\nEvent part 40 (DIE-HBM-82 11-06, COORD 13:37 RULINGS (1) / DIE-HBM-81 13:37): "
              "ot_hfd_coll_q3_edge_arg (q_hub_nw u_hb_coll_Q_edge__q0__arg) takes the HBM-GAPS-8 same-slot re-pin table "
              "(cores/ot_hfd_coll_q3_edge_arg__276.48x43.2__d44v_repin_hg8.json, sha 9ae65807400d, byte for byte): S-face M5 pins spread "
              "in x only; outline, origin, E pins and clock entry unchanged; no sidecar change. PIN CYCLES fault +1 for the HBM-GAPS-9 "
              "__fpipe form (corelat/cycles_q3arg_fpipe_1106.tsv); part40_event.json; replay results/die_hbm_1106/q3arg_repin_p40.\n")

# SHA256SUMS: update changed rows, add new files
S = D / "SHA256SUMS"
L = [l.split(None, 1) for l in S.read_text().splitlines() if l.strip()]
cur = {}
for f in list(D.glob("*")) + list(D.glob("cores/*")) + list(D.glob("corelat/*")):
    if f.is_file() and f.name not in ("SHA256SUMS", "README.md"):
        n = str(f.relative_to(D)).removesuffix(".gz")
        b = f.read_bytes()
        cur[n] = sha(gzip.decompress(b) if f.name.endswith(".gz") else b)
names = {n for _, n in L}
ch = []
for i, (a, n) in enumerate(L):
    if n in cur and cur[n] != a:
        L[i] = [cur[n], n]
        ch.append(n)
add = [n for n in (NEW, "part40_event.json", CYC) if n not in names]
L += [[cur[n], n] for n in add]
S.write_text("".join(f"{a}  {n}\n" for a, n in L))
print("SHA256SUMS changed", ch, "added", add)
