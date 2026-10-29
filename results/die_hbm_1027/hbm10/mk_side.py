"""DIE-HBM-10 C25b side data for TOK-HBM-4/5: per-role reset legs, provider legs, host_write_interval, plan sha.
usage: mk_side.py PLAN_DIR [OFFSETS_JSON]"""
import json, sys, hashlib, os
D = sys.argv[1]; OFF = sys.argv[2] if len(sys.argv) > 2 else None
P = json.load(open(f"{D}/die_plan.json")); T = P["partition_types"]; po = {p["name"]: p for p in P["partitions"]}
sha = hashlib.sha256(open(f"{D}/die_plan.json", "rb").read()).hexdigest()
off = json.load(open(OFF)) if OFF and os.path.exists(OFF) else None
def die(part, xy):
    o = po[part]["origin_um"]; W = T[po[part]["type"]]["outline_um"][0]
    x = W - xy[0] if po[part].get("orient") == "MY" else xy[0]     # MY: mirrored about the partition's vertical axis
    return [round(o[0] + x, 3), round(o[1] + xy[1], 3)]
ROLE = {"SW": ("NW_hub", "q0"), "NW": ("NW_hub", "q1"), "SE": ("NE_hub", "q0"), "NE": ("NE_hub", "q1"), "root": ("root", None)}
legs = {}
for r, (part, half) in ROLE.items():
    t = T[po[part]["type"]]["reset"]
    legs[f"reset_{r}"] = dict(partition=part, half=half, tap_die_um=die(part, t["tap_um"]), sync_stages=t["sync_stages"],
                              local_release_edges=3 if r != "root" else 6,
                              release_cycle=(off.get(part) if isinstance(off, dict) else None) if off else None,
                              release_basis="reset_tree.py offsets (wavefront) on this plan" if off else
                              "PENDING: reset_tree.py offsets still running (c25b_rt/offsets_c25a.json); SW/NW share the NW_hub release, SE/NE the NE_hub release")
hl = die("NW_hub", [4916.16 + 34.56, 768.96 + 34.56])
pg = next(c for c in T["root"]["hard_cores"] if c["inst"] == "u_mu_fused_program")
pgS = die("root", [pg["origin_um"][0] + pg["outline_um"][0] / 2, pg["origin_um"][1]])
L = abs(hl[0] - pgS[0]) + abs(hl[1] - pgS[1]); n_rep = int(-(-L // 450)) - 1
prov = {
 "host_to_provider": dict(src="NW_hub.u_hleaf_Q (ot_hbm_host_cfg_leaf_nw)", dst="root.u_mu_fused_program cfg/desc/launch (S face)",
                          length_um=round(L, 1), form="repeated lane (combinational repeaters every 450 um, standard repeater rule, no new check), boot only",
                          repeaters=n_rep, status="SIDE DATA: plan lane + ports to be adopted in C25c (needs the hub->root port window and a G0 run)"),
 "provider_to_root": dict(src="u_mu_fused_program.job*/wsc/pk5/pb5 (N face)", dst="u_mu_fused_root S face", length_um=17.28, cycles=0,
                          form="abutted, same partition, core_conns direct", status="IN PLAN"),
 "root_to_provider": dict(src="u_mu_fused_root.done/fault/busy", dst="u_mu_fused_program.root_*", length_um=17.28, cycles=0, status="IN PLAN"),
 "down_NW/NE, up_NW/NE": dict(lanes={k: v["cycles"] for k, v in P["latency"]["lanes"].items() if k.startswith("N4")}, status="IN PLAN (N4U/N4D_NW/NE)"),
}
doc = dict(schema="opentallas.hbm.c25b_side.v1", plan=f"{D}/die_plan.json", plan_sha256=sha, plan_sha8=sha[:8],
           roles={"NWq0": "SW", "NEq0": "SE", "NWq1": "NW", "NEq1": "NE"}, reset_contract_edges=64, reset_legs=legs,
           provider_legs=prov,
           host_write_interval=dict(value=None, status="PENDING", formula="ceil((t_wire(host_to_provider) + t_ack) / T_stream) + 1 cycles; "
                                    f"wire est {L:.0f} um x 0.3659 ps/um = {L*0.3659/1000:.2f} ns one way (UNCHECKED shared wire model)"),
           svg_S_candidates=dict(nets=[f"svg_SW{i}__sm_packet" for i in range(8)], form="nkeys=0 tie CANDIDATE only if the token pass stays bit-exact (not asserted here)"),
           fold_map="c25b_s_role_fold_map.json (20 MAPPED / 60 UNMAPPED / 8 NO_PROVIDER) SUPERSEDED by the binder q0-half instance map (TOK-HBM-4 ruling)")
json.dump(doc, open(f"{D}/c25b_side.json", "w"), indent=1)
print(sha[:8], round(L, 1), n_rep, {k: v["tap_die_um"] for k, v in legs.items()})
