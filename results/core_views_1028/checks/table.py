import json, collections, csv, sys
S = "/srv/opentallas-scratch2/claude/core-views-1-1028"
early = json.load(open(f"{S}/early_out.json"))
own = {}
for row in open(f"{S}/OWNERS_snapshot.tsv"):
    if row.startswith("#") or row.startswith("die\t"): continue
    f = row.rstrip("\n").split("\t")
    if len(f) > 5 and f[2] == "core":
        own[(f[0], f[1])] = dict(state=f[3], owner=f[4], live=f[5], evidence=f[8] if len(f) > 8 else "")
match = {"s81": "match_s81_s10.json", "qwen_compute": "match_qc_k2b12.json", "qwen_kvsys": "match_kv_main.json",
         "s81_head": "match_head_main.json"}
views = {"s81": "results/core_views_1028/s81 (NEW)", "qwen_compute": "results/core_views_1028/qwen_compute (NEW)",
         "qwen_kvsys": "physical/ref_tile/kv3_head_eighth_e{1,5}/views (existing)", "s81_head": "results/die_head_1027/views (existing)"}
plans = {"s81": "plan_s10 (intel2 die-s81-10/plan, DIE-S81-15 basis)", "qwen_compute": "qc_k2b_phase12 (DIE-QC-16 t11i basis)",
         "qwen_kvsys": "origin/main die_plan.json", "s81_head": "origin/main die_plan.json", "hbm": "origin/main hbm_arch/B2n"}
NOVIEW = {"dsdv_eng_rr_h1": "signed, committed view has no LEF/ETM (run data needed)",
          "dsfd_su_t_rxsb": "signed, committed view has no LEF/ETM (run data needed)",
          "ot_dsrom_su_hcpost_lane_pr": "signed, committed view has no LEF/ETM (run data needed)",
          "qfd_dv_s5_su8_rst3": "OWNERS SIGNED but DEMOTED 10-27 (routed LEC KEEP FAIL, retired record); closed run has no pins/freeze -> no view",
          "dsfd_qbank_N": "SIGNED-UNVERSIONED retime record only; no view exported (no kit pins/freeze in record dir, UNCHECKED)",
          "ot_hbm_static_cfg_collar_idx256r": "SIGNED-UNVERSIONED; not in the B2n plan"}
out = []
summ = []
for die in ("s81", "qwen_compute", "hbm", "qwen_kvsys", "s81_head"):
    m = json.load(open(f"{S}/{match[die]}")) if die in match else {}
    rows = []
    for mod, v in early[die].items():
        o = own.get(("hbm" if die == "hbm" else die, mod), {})
        st = o.get("state", "not in OWNERS")
        signed = "yes" if st == "SIGNED" else ("unversioned" if st == "SIGNED-UNVERSIONED" else "no")
        if mod in m:
            inst = m[mod].get("instances", {})
            ok = inst.get("canonical", 0) + sum(n for k, n in inst.items() if k.startswith("mirror"))
            tot = sum(inst.values())
            bad = [k for k in inst if k.startswith("MISMATCH")]
            view = f"yes, pins match {ok}/{tot}" + (f" ({bad[0][10:]})" if bad else "")
        else:
            view = "no" + (f" -- {NOVIEW[mod]}" if mod in NOVIEW else "")
        rows.append(dict(mod=mod, inst=v["inst"], early=v["early_taps"], ins_ff=v["max_ins_ff"], signed=signed, view=view,
                         state=st, owner=o.get("owner", "")))
    rows.sort(key=lambda r: (-r["early"], -r["inst"], r["mod"]))
    e = [r for r in rows if r["early"]]
    ev = sum(r["early"] for r in e if r["view"].startswith("yes") and "/" in r["view"] and r["view"].split("match ")[1].split("/")[0] == r["view"].split("/")[1].split(" ")[0])
    summ.append((die, len(rows), len(e), sum(r["early"] for r in e), ev, sum(1 for r in rows if r["signed"] != "no"),
                 sum(1 for r in rows if r["view"].startswith("yes"))))
    out.append(f"\n## {die}  (plan: {plans[die]}; views: {views.get(die, 'none')})\n")
    out.append("| core module | inst | early taps | max FF ins ps | signed | view (gate pin match) | OWNERS state | owner |")
    out.append("|---|---|---|---|---|---|---|---|")
    show = rows if die != "hbm" else [r for r in rows if r["early"] or r["signed"] != "no"]
    for r in show:
        out.append(f"| {r['mod']} | {r['inst']} | {r['early'] or '-'} | {round(r['ins_ff'],1) if r['early'] else '-'} | {r['signed']} | {r['view']} | {r['state']} | {r['owner']} |")
    if die == "hbm":
        c = collections.Counter(r["state"] for r in rows if r["early"])
        out.append(f"\nHBM early-tapped modules by OWNERS state: {dict(c)}; non-early modules omitted ({len(rows)-len(show)}).")
print("SUMMARY die modules early_mods early_taps early_taps_with_matched_view signed views")
for s in summ: print(*s)
open(f"{S}/CORE-VIEWS-table.md", "w").write("\n".join(out) + "\n")
