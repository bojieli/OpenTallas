#!/usr/bin/env python3
"""TOK-QK-XD3 10-26: raw/{tp8,xdie,ovl4u}_result.json + constants -> result.json (+ deltas vs XD2 and vs the priced ledger)."""
import json, sys
D = sys.argv[1]
t = json.load(open(D + "/raw/tp8_result.json")); x = json.load(open(D + "/raw/xdie_result.json")); o = json.load(open(D + "/raw/ovl4u_result.json"))
c = json.load(open(D + "/constants/constants_v7_peer_b23h2.json")); k = json.load(open(D + "/constants/constants_kv_b23h2.json"))
b = {s: json.load(open(f"{D}/raw/bound_txdp_{s}.json")) for s in ("qc", "kv", "kv_stale")}
XD2 = dict(C2K_cmd=77, K2C_r31=77, roundtrip_cmd_to_r31=1933, exposed_d2d_per_layer=155, period_per_layer=7056,
           decode_layers_L1_35_total=246960, token_E_incl_argmax=23147, agg_cycles_per_token=87539.1, agg_tok_s=13708.2)
PRICED = dict(period_per_layer=7056, roundtrip_cmd_to_r31=1827, qc_cycles_per_token_rederived_v7=296341,
              qc_cycles_per_token_v7_priced=289321)
xc, tc, oc = x["cycles"], t["cycles"], o["cycles"]
agg = oc.get("aggregate_cycles_per_token"); tps = oc.get("aggregate_tok_s_833ps")
meas = dict(C2K_cmd=xc.get("C2K_cmd"), C2K_q31=xc.get("C2K_q31"), K2C_r31=xc.get("K2C_r31"), K2C_status=xc.get("K2C_status"),
            roundtrip_cmd_to_r31=xc.get("roundtrip_cmd_to_r31"), exposed_d2d_per_layer=xc.get("exposed_d2d_per_layer"),
            period_per_layer=xc.get("period_per_layer"), X_per_layer=xc.get("X_per_layer"),
            decode_layers_L1_35_total=xc.get("decode_layers_L1_35_total"), token_E_incl_argmax=tc.get("token_E_incl_argmax"),
            agg_cycles_per_token=agg, agg_tok_s=tps)
def d(a, b_):
    return None if a is None or b_ is None else round(a - b_, 1)
s = dict(schema="opentallas.token_pass.qc_kv_link.v2", lane="TOK-QK-XD3", date=sys.argv[2],
 assembly_commit="5832e672235d955164c31991b09f3cee96ee4de2",
 qc_bind=dict(source="codex/qc-phase-2209@13f33606a v7 final (strict bind)", bound_sha=c["bound_sha"]),
 kv_peer=dict(source="claude/tok-kv-b23h-1026@c6602a6ae8 b23h2 strict bind (plan c20ef31508 + PATH-KV rebase-0010 hook a795ac1cb6 regen_kv_2350 + kvchk 0b8b9727a8); interim die: batch-0115@650841e1ef strict bind b28 FAILED (EMIT parent ID kv3_hg strap_bsel decl)",
              bound_sha=k["bound_sha"]),
 bound_txdp=dict(qc=b["qc"]["word"], kv=b["kv"]["word"], kv_stale_b19_mutant=b["kv_stale"]["word"],
                 source="tools_bound/bound_txdp.py: the D2D master instance parameter in BINDDIR/rtl (u_d2d_rom / u_d2d_kv) == param_regen.json"),
 txdp_gate=x.get("pair_image", {}).get("txdp_bound_gate"),
 regen_constants=dict(tool="claude/tok-qk-kvchk2-1026@aac29eda2d", qc_peer=c["verdict"], kv=k["verdict"]),
 constants={kk: c["constants"][kk]["value"] for kk in ("COLL_LS", "COLL_BENCH_ARGS", "XDIE_DIE_STAGES", "D2D_KV_TX_LAT", "D2D_TXDP_K", "D2D_TXDP_C")},
 measured=meas, xd2=XD2, delta_vs_xd2={kk: d(meas.get(kk), v) for kk, v in XD2.items()}, priced=PRICED,
 delta_vs_priced=dict(period_per_layer=d(meas["period_per_layer"], PRICED["period_per_layer"]),
                      roundtrip_cmd_to_r31=d(meas["roundtrip_cmd_to_r31"], PRICED["roundtrip_cmd_to_r31"])),
 tp8=dict(verdict=t["verdict"], cases=len(t["runs"]), ok=sum(r["ok"] for r in t["runs"].values()), cycles=tc, mutants=t["mutants"]),
 xdie=dict(verdict=x["verdict"], configs=len(x["runs"]), ok=sum(r["ok"] for r in x["runs"].values()), cycles=xc, mutants=x["mutants"],
           txdp_mutants={n: dict(got=r.get("got"), txdp_gate=r.get("txdp_gate"), sim_got=r.get("sim_got"), line=r.get("txdp_bound"))
                         for n, r in x["runs"].items() if n.startswith("cur_bound")}),
 ovl4u=dict(verdict=o["verdict"], cycles=oc, mutants=o["mutants"]))
json.dump(s, open(D + "/result.json", "w"), indent=1); print(json.dumps(dict(measured=meas, d_xd2=s["delta_vs_xd2"], d_priced=s["delta_vs_priced"], txdp=s["xdie"]["txdp_mutants"]), indent=1))
