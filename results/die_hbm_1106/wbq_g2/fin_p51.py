#!/usr/bin/env python3
"""DIE-HBM-82-EP6 d44v part 51 packaging (after mk_p51.py): recipes, reset contract modules, pin-cycle rows (all 0), event
record, README line, SHA256SUMS.   fin_p51.py REPO RTL_COMMIT"""
import copy, gzip, hashlib, json, sys
from pathlib import Path
R, RC = Path(sys.argv[1]), sys.argv[2]
D = R / "physical/die_plan/hbm/plan_of_record/d44v"
ROOT, M0, M1 = "ot_wbq_root", "ot_wbq_root_g0", "ot_wbq_root_g1"
TB = "cores/ot_wbq_root_g__216x129.6__d44v_p51.json"
LAT = "corelat/cycles_wbq_g2_1106.tsv"
sha = lambda b: hashlib.sha256(b).hexdigest()
rp = R / "physical/die_plan/hbm_arch_cores/recipes_b2.json"
REC = json.loads(rp.read_text())
assert M0 not in REC and M1 not in REC
for g, m in ((0, M0), (1, M1)):
    r = copy.deepcopy(REC[ROOT])
    r.update(top=m, macros=["ot_sram_1r1w_128x256_m1_r0c0_g256"], defines=[], params={}, source_commit=RC, read_at_commit=True, util=0.45,
             source=f"DIE-HBM-82-EP6 d44v part 51 (plan-owner approved DIE-HBM-82 11-06 19:1x): lane group {g} of ot_wbq_root "
                    f"(lanes {4 * g}-{4 * g + 3}, 4 x ot_sram_1r1w_128x256_m1_r0c0_g256); slot glue ot_wbq_root_g2 = ot_wbq_root (OT_WBQ_N1M) "
                    "cycle-exact: results/die_hbm_1106/wbq_g2/eq_g2.sh (yosys induction) + bench_g2.sh (lock-step)")
    REC[m] = r
rp.write_text(json.dumps(REC, indent=1 if rp.read_text().startswith("{\n \"") else 2) + "\n")
cp = R / "physical/die_plan/hbm/reset_contract.json"
C = json.loads(cp.read_text())
C["modules"] = sorted(set(C["modules"]) | {M0, M1})
cp.write_text(json.dumps(C, indent=1) + "\n")
(D / LAT).write_text(
    "core\tsub_block\tport_or_bus\tdir\tadded_cycles\tnote\n"
    + "".join(f"{m}\t\t{p}\tport\t0\tpart 51 lane-group split of ot_wbq_root: no seam, every pin on the edge of the ot_wbq_root pin it replaces "
              f"(yosys induction EQ vs ot_wbq_root OT_WBQ_N1M)\n" for m in (M0, M1) for p in ("g_v", "g_d", "g_credit", "wd", "control")))
ev = {"schema": "opentallas.hbm_plan_event.part51", "by": "DIE-HBM-82-EP6 11-06 (DIE-HBM-82 19:1x: SPLIT ot_wbq_root, grow declined)",
      "core": ROOT, "instances": 16, "types": ["q_hub_nw", "q_hub_ne"], "slot_um": [432.0, 129.6], "slot_kept": True,
      "tiles_root_frame": {"u_g0": [[0.0, 0.0], [216.0, 129.6]], "u_g1": [[216.0, 0.0], [216.0, 129.6]]},
      "tables": {m: {"pins_file": TB, "sha256": sha((D / TB).read_bytes())} for m in (M0, M1)},
      "glue": "rtl/hbm_accel/cores_split/reform_1105b/ot_wbq_split.sv ot_wbq_root_g2 (u_rK = u_g0 ot_wbq_root_g0 + u_g1 ot_wbq_root_g1)",
      "proof": "results/die_hbm_1106/wbq_g2: eq_g2.sh yosys equiv_make/struct/simple/induct PASS (17131 equiv cells), mutants FAIL; "
               "bench_g2.sh lock-step 40000 cycles PASS, 4 mutants FAIL",
      "pin_cycles": f"{LAT}: 0 everywhere", "rtl_commit": RC,
      "sidecars": "core_conns (core:<root> -> both groups; g1 root_ready unused), clock taps + centre entries per group, core_macros per group",
      "designs_removed": [ROOT], "designs_added": [M0, M1], "replay": "results/die_hbm_1106/wbq_g2/replay_p51.sh"}
(D / "part51_event.json").write_text(json.dumps(ev, indent=1) + "\n")
rd = D / "README.md"
rd.write_text(rd.read_text().rstrip("\n") + "\n\nEvent part 51 (DIE-HBM-82-EP6, plan-owner approved DIE-HBM-82 11-06): ot_wbq_root (16 instances, "
              "wiring-bound at GRT) -> its two lane groups in the same 432x129.6 slot: ot_wbq_root_g0 / ot_wbq_root_g1 216x129.6 "
              "(4 x 128x256 one-mask-pin macros each, own group pick + credit, fill/copy control replicated; no seam, 0 pin cycles, "
              "corelat/cycles_wbq_g2_1106.tsv); glue ot_wbq_root_g2; yosys induction EQ + lock-step in results/die_hbm_1106/wbq_g2; part51_event.json.\n")
S = D / "SHA256SUMS"
L = [l.split(None, 1) for l in S.read_text().splitlines() if l.strip()]
cur = {}
for f in list(D.glob("*")) + list(D.glob("cores/*")) + list(D.glob("corelat/*")):
    if f.is_file() and f.name not in ("SHA256SUMS", "README.md"):
        n = str(f.relative_to(D)).removesuffix(".gz")
        b = f.read_bytes()
        cur[n] = sha(gzip.decompress(b) if f.name.endswith(".gz") else b)
names = {n for _, n in L}
ch = 0
for i, (a, n) in enumerate(L):
    if n in cur and cur[n] != a:
        L[i] = [cur[n], n]
        ch += 1
add = [n for n in (TB, "part51_event.json", LAT) if n not in names]
L += [[cur[n], n] for n in add]
S.write_text("".join(f"{a}  {n}\n" for a, n in L))
print("SHA256SUMS changed", ch, "added", add)
