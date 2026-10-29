#!/usr/bin/env python3
"""DIE-QC-33 BIND: prepare the approved QC functional candidate exactly as
results/token_pass/qc_functional_0845/prepare.py (codex 63d7fd532), PLUS the TOK-QC-2 generator rule that prepare.py
omitted: physical/die_plan/qwen_compute/bind/ca_pair_rule.py (both directions of each collective relay pair RS_j get
the same count) applied to the native CA bind_clock BEFORE its sched_lat values enter the plan and BEFORE
annotate_table, then count_align_bind.verify (identity, loops, ring guards).  Without it the strict bind fails
PARAM_REGEN coll_regen.py RS0: core->face 20 vs face->core 21 (failed_2 run).
    prepare_paired.py OUT_DIR      (reads results/token_pass/qc_functional_0845/inputs/*.json.gz)"""
import gzip, json, sys
from pathlib import Path
R = Path(__file__).resolve().parents[3]
I = R / "results/token_pass/qc_functional_0845/inputs"
O = Path(sys.argv[1]); O.mkdir(parents=True, exist_ok=True)
rd = lambda n: json.loads(gzip.decompress((I / (n + ".gz")).read_bytes()))
wr = lambda n, o: (O / n).write_text(json.dumps(o, indent=1) + "\n")
raw = rd("plan.json"); ca = rd("native_ca.json"); side = rd("sidecar_previous.json"); ab = rd("asbuilt_previous.json")
sys.path.insert(0, str(R / "tools/die_plan")); sys.path.insert(0, str(R / "physical/die_plan/qwen_compute/bind"))
import count_align_bind as CAB, clock_landing_plan as CLP, ca_pair_rule as PR
pair_rec = PR.apply(ca, side)
v = CAB.verify(ca, samples=500)
if v["identity_and_loop_errors"] or v["sim_window_violations"] or v["sim_below_need"]:
    sys.exit(f"pair rule broke the CA bind: {v}")
wr("pair_rule.json", dict(pairs=pair_rec, verify={k: v[k] for k in v if not isinstance(v[k], (list, dict))}))
ports = {p["id"]: p for p in raw["ports"]}
assert len(side["ports"]) == len(ca["ports"]) == 2525
changed = []
for row in side["ports"]:
    pid = row["port"]; p = ports[pid]; c = ca["ports"][pid]
    assert (p["src"]["part"], p["dst"]["part"], p["width"]) == (row["src"], row["dst"], row["width"])
    old = raw["clock"]["landing_network"]["count_aligned_cycles"][pid]; new = c["sched_lat"]
    assert old == row["added_cycles"]
    if old != new:
        changed.append(dict(port=pid, lane=row["lane"], before=old, after=new, delta=new - old))
    row["added_cycles"] = new
    raw["clock"]["landing_network"]["count_aligned_cycles"][pid] = new
side = CAB.annotate_table(side, ca, root_settle_cycles=64, strap_form=True)
old_straps = {k: v.get("count_straps", []) for k, v in raw["partition_types"].items()}
CLP._ca_strap_pins(raw, side)
wr("count_strap_delta.json", {k: dict(before=old_straps[k], after=t.get("count_straps", []))
                              for k, t in raw["partition_types"].items() if old_straps[k] != t.get("count_straps", [])})
side["note"] = "Current native perimeter1 CA table + TOK-QC-2 ca_pair_rule + exact data endpoints (DIE-QC-33 BIND); no physical adoption"
raw["note"] += " | CODEX functional candidate: native perimeter1 CA data counts and actual native START provider; explicit coherent HEAD/ROPE profile | DIE-QC-33: + ca_pair_rule"
rel = str(O.resolve().relative_to(R.resolve()))
ab["base"] = "../../.."
ab["map_file"] = "../../../physical/die_plan/qwen_compute/bind/asbuilt_map_p6.json"
ab["clock_landing_table"] = rel + "/sidecar.json"
ab["land_r8"] = "results/token_pass/qc_functional_0845/inputs/r8_previous.json"
ab["land_r8_extra"] = ["results/token_pass/qc_functional_0845/inputs/cb16_previous.json", "results/token_pass/qc_head_loop_1029/candidate_inner.json"]
ab["qwen_head_prepare_profile"] = json.loads((R / "results/token_pass/qc_head_profile_1029/candidate_profile.json").read_text())["qwen_head_prepare_profile"]
ab["note"] += " | CODEX current native CA/START + explicit approved coherent HEAD_CONTEXT/ROPE/L_CONTEXTS=1 and INNER witness4to8 | DIE-QC-33 + ca_pair_rule"
wr("plan.json", raw); wr("sidecar.json", side); wr("asbuilt.json", ab)
wr("ca_cycle_delta.json", dict(status="SOURCE_CANDIDATE_NOT_ADOPTED", changed_ports=len(changed),
                               aggregate_port_cycles=sum(r["delta"] for r in changed), rows=changed,
                               model_price="aggregate port cost is not token latency"))
print("PREPARED", len(raw["partitions"]), len(raw["partition_types"]), len(changed), sum(r["delta"] for r in changed),
      "PAIR", json.dumps([dict(pair=r["pair"], chains=r["chains"], target=r["target"], steps=len(r["steps"])) for r in pair_rec]),
      "VERIFY", {k: v[k] for k in ("identity_and_loop_errors", "sim_window_violations", "sim_min_margin_low_ps", "sim_min_margin_high_ps")})
