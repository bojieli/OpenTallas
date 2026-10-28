#!/usr/bin/env python3
"""DIE-HBM/KITS: C20 kit wave table.  table_c20.py WAVEDIR OUTPREFIX"""
import json, glob, collections, os, sys
D, OUT = sys.argv[1], sys.argv[2]
R = {}
for f in glob.glob(f"{D}/kits/mk_c20_result_batch_0*.json"):
    R.update(json.load(open(f)))
enq = {"ot_hgi_qw_dec": "df22c7ce3c4c", "ot_hgi_coll_gq_issue": "2ca0576a683f",
       "ot_hgi_coll_tkm_tp192_tile_core__idpin__strap": "064319ed237e"}
hold = {"hfd_hgi_vms_glue_nw_t": "HELD outline 1.19 mm2, no synth cell count (<=400k unproven)",
        "ot_hbm_hc_root_static__hcp_sys1": "HELD Codex/HBM-CORES HCP CMD_RST + LEC owner",
        "ot_hbm_su_static_pgslice_lg__pretree": "HELD Codex pretree CTS staged codex-hbm-cores-0815/pretree_cts_1011",
        "ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap": "HELD open R8 ASK terminal tile_up_in=0 tie ruling",
        "hnx_rp3lp3h_n": "BLOCKED OVER_400K (split plan rp3lp3h_split_plan.json)",
        "hnx_rp3lp3h_s": "BLOCKED OVER_400K (split plan rp3lp3h_split_plan.json)"}
rows, c = [], collections.Counter()
for m, o in sorted(R.items()):
    for v in (o if isinstance(o, list) else [o]):
        pf, iss = None, []
        if v.get("kit"):
            p = f"{D}/preflight/{os.path.basename(v['kit'])}.json"
            if os.path.exists(p):
                j = json.load(open(p))
                pf, iss = j.get("verdict"), sorted({i.split(":")[0] for i in j.get("issues", [])})
        if m in enq:
            act = f"ENQUEUED trial {enq[m]}"
        elif m in hold:
            act = hold[m]
        elif v["cls"] != "OK":
            act = f"BLOCKED {v['cls']}"
        else:
            act = "BLOCKED PREFLIGHT " + ";".join(iss)
        c[" ".join(act.split(" ")[:2]) if not act.startswith("BLOCKED PREFLIGHT") else "BLOCKED PREFLIGHT"] += 1
        rows.append(dict(module=m, view=v.get("view"), gen=v["cls"], kit=v.get("kit"), preflight=pf, issues=iss,
                         action=act, msg=(v.get("msg") or "")[:200]))
for m in ("ot_hbm_hc_root_static__tailx_sk_steady", "ot_hbm_idx_topk_link_static"):
    rows.append(dict(module=m, gen="NOT_GENERATED", action="OWNED-LIVE CODEX")); c["OWNED-LIVE"] += 1
json.dump(dict(wave=D, counts=c, rows=rows), open(OUT + ".json", "w"), indent=1)
with open(OUT + ".tsv", "w") as f:
    f.write("module\tgen\tpreflight\tissues\taction\n")
    for r in rows:
        f.write("\t".join([r["module"], r["gen"], str(r.get("preflight")), ";".join(r.get("issues") or []), r["action"]]) + "\n")
print(len(rows), dict(c))
