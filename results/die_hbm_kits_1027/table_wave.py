#!/usr/bin/env python3
"""DIE-HBM-3/KITS: kit wave table for any run_wave.sh wave (generalises table_c20.py; fix kits + WAIT-C20f rows).
   table_wave.py WAVEDIR OUTPREFIX PLACE_JSON   (PLACE_JSON: {module: "place-only <ot-heavy id>"} or "-")"""
import json, glob, collections, os, sys
D, OUT, PJ = sys.argv[1], sys.argv[2], sys.argv[3]
place = json.load(open(PJ)) if PJ != "-" else {}
R = {}
for f in glob.glob(f"{D}/kits/mk_c20_result_batch_0*.json"):
    R.update(json.load(open(f)))
fixk = {}
for k in glob.glob(f"{D}/kits_fix/*/freeze.json"):
    n = os.path.basename(os.path.dirname(k)); m = n.rsplit("_", 2)[0]
    fixk[m] = os.path.dirname(k)
hold = {"ot_hbm_hc_root_static__hcp_sys1": "HELD Codex/HBM-CORES HCP CMD_RST + LEC owner",
        "ot_hbm_su_static_pgslice_lg__pretree": "HELD Codex pretree CTS staged codex-hbm-cores-0815/pretree_cts_1011",
        "ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap": "HELD open R8 ASK terminal tile_up_in=0 tie ruling",
        "hnx_rp3lp3h_n": "BLOCKED OVER_400K (split plan rp3lp3h_split_plan.json)",
        "hnx_rp3lp3h_s": "BLOCKED OVER_400K (split plan rp3lp3h_split_plan.json)"}
def pf_of(kit, sub):
    p = f"{D}/{sub}/{os.path.basename(kit)}.json"
    if not os.path.exists(p): return None, []
    j = json.load(open(p)); return j.get("verdict"), sorted({i.split(":")[0] for i in j.get("issues", [])})
rows, c = [], collections.Counter()
for m, o in sorted(R.items()):
    for v in (o if isinstance(o, list) else [o]):
        cls, kit, sub = v["cls"], v.get("kit"), "preflight"
        if m in fixk: cls, kit, sub = "OK(fix)", fixk[m], "preflight_fix"
        pf, iss = pf_of(kit, sub) if kit else (None, [])
        if m in place and pf == "PASS": act = place[m]
        elif m in hold: act = hold[m]
        elif not cls.startswith("OK"): act = f"BLOCKED {cls}"
        elif pf == "PASS": act = "PASS (no action)"
        else: act = "BLOCKED PREFLIGHT " + ";".join(iss)
        c[" ".join(act.split(" ")[:2]) if not act.startswith("BLOCKED PREFLIGHT") else "BLOCKED PREFLIGHT"] += 1
        rows.append(dict(module=m, view=v.get("view"), gen=cls, kit=kit, preflight=pf, issues=iss, action=act,
                         msg=(v.get("msg") or "")[:200]))
for m in open(f"{D}/wait_c20f.txt").read().split():
    rows.append(dict(module=m, gen="NOT_GENERATED", action="WAIT-C20f (L12 split / vms_glue +106.272 um)")); c["WAIT-C20f"] += 1
for m in ("ot_hbm_hc_root_static__tailx_sk_steady", "ot_hbm_idx_topk_link_static"):
    rows.append(dict(module=m, gen="NOT_GENERATED", action="OWNED-LIVE CODEX")); c["OWNED-LIVE"] += 1
json.dump(dict(wave=D, counts=c, rows=rows), open(OUT + ".json", "w"), indent=1)
with open(OUT + ".tsv", "w") as f:
    f.write("module\tgen\tpreflight\tissues\taction\tkit\n")
    for r in rows:
        f.write("\t".join([r["module"], r["gen"], str(r.get("preflight")), ";".join(r.get("issues") or []), r["action"],
                           os.path.basename(r.get("kit") or "")]) + "\n")
print(len(rows), dict(c))
