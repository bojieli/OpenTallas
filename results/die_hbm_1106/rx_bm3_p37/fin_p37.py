#!/usr/bin/env python3
"""DIE-HBM-81 d44v part 37 packaging (after mk_p37.py): recipes, reset contract modules, pin-cycle rows, compiler delta,
event record, README line, SHA256SUMS.   fin_p37.py REPO"""
import gzip, hashlib, json, sys
from pathlib import Path
R = Path(sys.argv[1])
D = R / "physical/die_plan/hbm/plan_of_record/d44v"
GH = R / "physical/die_plan/hbm/over_cap_split/reform_1106/rx_bm3/gen_hg7"
REST, BM = "ot_pdie_serdes_rx_bm3_rest", "ot_pdie_serdes_rx_bm_native"
TR, TB = f"cores/{REST}__197.856x345.6__hg7_modelA.json", f"cores/{BM}__95.904x106.56__hg7_modelA.json"
sha = lambda b: hashlib.sha256(b).hexdigest()

# recipes (HBM-GAPS-7 GEN recipes; residual SEAM 7 = the signed vB form)
rp = R / "physical/die_plan/hbm_arch_cores/recipes_b2.json"
REC = json.loads(rp.read_text())
rb = json.loads((GH / "recipe_bm.json").read_text())[BM]
rr = json.loads((GH / "recipe_res.json").read_text())[REST]
rr["params"]["SEAM"] = 7
for r_, what in ((rb, "BM child x3; kit --face-in-stage ^(S|ld|rs_n)$=1 (vB BM input relay)"),
                 (rr, "residual SEAM 7 (BM round trip with the vB BM input relay)")):
    r_["source"] = (f"DIE-HBM-81 d44v part 37 (plan-adopted): HBM-GAPS-7 11-06 RX BM3 vB safe form from Codex d727c112224 "
                    f"(58e1b7b1825), GEN claude/hbm-gaps-7-rxbm3-1106@992171836f; {what}")
assert BM not in REC and REST not in REC
REC[BM], REC[REST] = rb, rr
rp.write_text(json.dumps(REC, indent=2) + "\n")

# reset contract module list (every hard-core module of the plan)
cp = R / "physical/die_plan/hbm/reset_contract.json"
C = json.loads(cp.read_text())
C["modules"] = sorted(set(C["modules"]) | {REST, BM})
cp.write_text(json.dumps(C, indent=1) + "\n")

# declared pin cycles (vs the part 20 rx form); bench gen_hg7/bench/runD.log BMIN 2 SEAM 7 rxd 7 fd 7 PASS (gold +7, p20 +2)
(D / "corelat/cycles_rxbm3_1106.tsv").write_text(
    "core\tsub_block\tport_or_bus\tdir\tadded_cycles\tnote\n"
    f"{REST}\t\trx\tport\t5\tHBM-GAPS-7 RX BM3 vB (BM relay + SEAM 7), part 37: rx data gold +7 vs p20 form +2; bench gen_hg7/bench/runD.log PASS, SEAM 6/8 + BMIN 3 FAIL\n"
    f"{REST}\t\tst[0]\tport\t5\tuncorrectable flag into st[0] +5 (fault edge gold +7); the TX-fault path into st[0] is unchanged (+2, part 20)\n"
    f"{REST}\t\tst[1]\tport\t0\tlock: exact\n")
cd = D / "compiler_core_delta.json"
K = json.loads(cd.read_text())
K["pending_not_folded"]["HBM-GAPS-7 RX BM3 (part 37)"] = (
    "ot_pdie_serdes_rx_bm3_rest rx / st[0] +5 on every inbound SerDes crossing (corelat/cycles_rxbm3_1106.tsv); "
    "fold into S2 extra COLL_XING and ext/crossing_latency at the next ext_census regen (TOK lane). Owner 12.21: tok/s loss from closure fixes accepted")
cd.write_text(json.dumps(K, indent=1) + "\n")

ev = {"schema": "opentallas.hbm_plan_event.part37", "by": "DIE-HBM-81 11-06 (COORD 11:00 (2): adopt the BM3 split as a plan event)",
      "core": "ot_pdie_serdes_rx", "instances": ["NW_io u_lk_N0__rx", "q_spb0 u_lk_S0__rx", "q_spb0__physical_v1 u_lk_S0__rx",
                                                  "vsN0 u_lk_S1__rx", "NE_io u_lk_N2__rx"],
      "slot_um": [302.4, 345.6], "slot_kept": True,
      "tiles_rx_frame": {"u_rest": [[104.544, 0.0], [197.856, 345.6]], "u_bm0": [[0.0, 4.32], [95.904, 106.56]],
                         "u_bm1": [[0.0, 119.52], [95.904, 106.56]], "u_bm2": [[0.0, 234.72], [95.904, 106.56]]},
      "tables": {REST: {"pins_file": TR, "sha256": sha((D / TR).read_bytes()), "view": f"{REST}@7826e3baf53d"},
                 BM: {"pins_file": TB, "sha256": sha((D / TB).read_bytes()), "view": f"{BM}@cefde5fe417d",
                      "signed_kit": "epyc5 /srv/opentallas-scratch3/claude/hbm-gaps-7/rxgen/kits/ot_pdie_serdes_rx_bm_native_cefde5fe417d-vB/eco_hg7/i2 (re-signed cs-hbm, kind:resign, routed LEC EQ)"}},
      "glue": "results/die_hbm_1106/rx_bm3_p37/ot_pdie_serdes__p37comp.sv (u_rx = ot_pdie_serdes_rx__p37: u_rest + u_bm0..2)",
      "proof": "lock-step bench of the face-shelled kit form vs gold: physical/die_plan/hbm/over_cap_split/reform_1106/rx_bm3/gen_hg7/bench (runD BMIN 2 SEAM 7 PASS 9000 edges; SEAM 6/8, BMIN 3 FAIL)",
      "pin_cycles": "corelat/cycles_rxbm3_1106.tsv: rx +5, st[0] uncorrectable +5, st[1] 0 (vs part 20)",
      "sidecars": "core_conns / clock_entries / taps / internal_stations: u_lk_X__rx -> u_lk_X__rx__rest (all outer ports live on the residual); BMs: own entries + seam conns",
      "designs_removed": ["ot_pdie_serdes_rx"], "designs_added": [REST, BM],
      "replay": "results/die_hbm_1106/rx_bm3_p37/replay_p37.sh"}
(D / "part37_event.json").write_text(json.dumps(ev, indent=1) + "\n")

rd = D / "README.md"
rd.write_text(rd.read_text().rstrip("\n") + "\n\nEvent part 37 (DIE-HBM-81, COORD 11-06 11:00 (2)): ot_pdie_serdes_rx (5 instances) -> HBM-GAPS-7 RX BM3 vB form "
              "in the same slot: residual ot_pdie_serdes_rx_bm3_rest 197.856x345.6 (E) + 3 x ot_pdie_serdes_rx_bm_native 95.904x106.56 (W column); "
              "Model-A tables; PIN CYCLES rx/st[0] +5 (corelat/cycles_rxbm3_1106.tsv); part37_event.json; replay results/die_hbm_1106/rx_bm3_p37.\n")

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
ch = 0
for i, (a, n) in enumerate(L):
    if n in cur and cur[n] != a:
        L[i] = [cur[n], n]
        ch += 1
add = [n for n in (TR, TB, "part37_event.json", "corelat/cycles_rxbm3_1106.tsv") if n not in names]
L += [[cur[n], n] for n in add]
S.write_text("".join(f"{a}  {n}\n" for a, n in L))
print("SHA256SUMS changed", ch, "added", add)
