#!/usr/bin/env python3
"""TOK-QK-XD4 10-26: raw/{xdie,ovl4u}_result.json (+ carried XD3 tp8) + constants -> result.json, deltas vs XD3 and priced."""
import json, sys
D = sys.argv[1]
x = json.load(open(D + "/raw/xdie_result.json")); o = json.load(open(D + "/raw/ovl4u_result.json"))
t = json.load(open(D + "/raw/tp8_result_carried_xd3.json"))
c = json.load(open(D + "/constants/constants_v7_peer_b48.json"))
b = {s: json.load(open(f"{D}/raw/bound_txdp_{s}.json")) for s in ("qc", "kv", "kv_stale")}
XD3 = dict(C2K_cmd=77, C2K_q31=78, K2C_r31=77, K2C_status=73, roundtrip_cmd_to_r31=1933, exposed_d2d_per_layer=155,
           period_per_layer=7056, X_per_layer=8, decode_layers_L1_35_total=246960, agg_cycles_per_token=87539.1, agg_tok_s=13708.2)
PRICED = dict(period_per_layer=7056, roundtrip_cmd_to_r31=1827)
xc, oc = x["cycles"], o["cycles"]
meas = dict(C2K_cmd=xc["C2K_cmd"], C2K_q31=xc["C2K_q31"], K2C_r31=xc["K2C_r31"], K2C_status=xc["K2C_status"],
            roundtrip_cmd_to_r31=xc["roundtrip_cmd_to_r31"], exposed_d2d_per_layer=xc["exposed_d2d_per_layer"],
            period_per_layer=xc["period_per_layer"], X_per_layer=xc["X_per_layer"],
            decode_layers_L1_35_total=xc["decode_layers_L1_35_total"], L0_X=xc.get("L0_X"), L0_period=xc.get("L0_period"),
            agg_cycles_per_token=oc["aggregate_cycles_per_token"], agg_tok_s=oc["aggregate_tok_s_833ps"])
d = lambda a, b_: None if a is None or b_ is None else round(a - b_, 1)
s = dict(schema="opentallas.token_pass.qc_kv_link.v2", lane="TOK-QK-XD4", date=sys.argv[2],
 grade="RTL-functional source assembly (Verilator 5.050); link stage only, not a whole-token / G5 claim",
 assembly_commit="5832e672235d955164c31991b09f3cee96ee4de2",
 qc_bind=dict(source="codex/qc-phase-2209@13f33606a v7 final (strict bind); the ONEQC landing final bind does not exist yet", bound_sha=c["bound_sha"]),
 kv_peer=dict(source="codex/kv-land-1026@c01a6f445 B48 strict bind (160 parts/82 types/430554 bits, 0 errors), epyc1 SCRATCH/codex-kv-land-1026/b48",
              seams="KS 68,68,66,66,66 / SK 67,67"),
 bound_txdp=dict(qc=b["qc"]["word"], kv=b["kv"]["word"], kv_stale_mutant_b23h2=b["kv_stale"]["word"]),
 txdp_gate=x.get("pair_image", {}).get("txdp_bound_gate"),
 regen_constants=dict(tool="codex/kv-constants-0733@aef421fbd", qc_peer_b48=c["verdict"],
                      kv_b48="not rerun here: Codex constants_b48_image (same checker) 38 OK / 4 WARN, all 128 PC833"),
 constants={k: c["constants"][k]["value"] for k in ("COLL_LS", "COLL_BENCH_ARGS", "XDIE_DIE_STAGES", "D2D_KV_TX_LAT", "D2D_TXDP_K", "D2D_TXDP_C")},
 measured=meas, xd3=XD3, delta_vs_xd3={k: d(meas.get(k), v) for k, v in XD3.items()}, priced=PRICED,
 delta_vs_priced={k: d(meas[k], v) for k, v in PRICED.items()},
 tp8=dict(verdict=t["verdict"], carried="XD3 receipt: QC-only collective, inputs (QC v7 bind, COLL_LS 407, mu_cal) unchanged; not rerun"),
 xdie=dict(verdict=x["verdict"], configs=len(x["runs"]), cycles=xc, mutants=x["mutants"]),
 ovl4u=dict(verdict=o["verdict"], cycles=oc, mutants=o["mutants"]),
 runs=dict(xdie="epyc2 ot-run unit oth-ubuntu-3400920-1793039862 exit 0", ovl4u="epyc2 ot-run unit oth-ubuntu-3401508-1793039862 exit 0",
           regen="epyc1 direct (python, light)"))
json.dump(s, open(D + "/result.json", "w"), indent=1)
print(json.dumps(dict(measured=meas, d_xd3=s["delta_vs_xd3"], d_priced=s["delta_vs_priced"]), indent=1))
