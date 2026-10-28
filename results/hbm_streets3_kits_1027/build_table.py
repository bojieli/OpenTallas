#!/usr/bin/env python3
"""HBM-STREETS-3 KIT: per-module table of the C18 NO-VIEW hard-core modules.
  build_table.py C18_VIEWS(census) R7_MK_RESULT C18_MK_RESULT ANNOT.json OUT_PREFIX
ANNOT.json = {module: {owner, live, action, note, preflight, queue_id}} (hand-entered from OWNERS/ot-run/docker/lane tails)."""
import json, sys, re
census, r7, c18, annot, out = sys.argv[1:6]
C = [c for c in json.load(open(census)) if c["status"] != "VIEWED"]
R7 = json.load(open(r7)); M = json.load(open(c18)); A = json.load(open(annot))
C19 = [r"^hfd_hgi_vms_glue_nw_t$", r"^hnx_vms_bank_q0_faces", r"^ot_hbm_hc_root_static__tail.*_rest", r"idx_query_static",
       r"idx_score_hcol_h[01]$", r"idx_vm_query_static_n12", r"sm_vm_wr_q_t_lanes4", r"static_cfg_collar_idx256r",
       r"su_static_cxport_ij_q", r"svc_vm_kshare_splitstrap", r"svc_wb_kport_q", r"xp_aq_tree13_fmt", r"hfd_coll_q2n2_vm_core",
       r"hfd_coll_q3_(body|vm)_core", r"hgi_coll_gq_(issue|land)", r"coll_inj_idx_join_rg", r"tkm_m_tp192__root",
       r"dma_back_static_vp4_banks_cp", r"sfu_core_split3__(ctl|opstore_a)$", r"sm_xload_cl2_(bdring|ctlx)", r"xload_xq_pegress",
       r"hnx_idxn_keybuf_slice"]
rows = []
for c in C:
    m = c["module"]; a = A.get(m, {})
    aff = any(re.search(p, m) for p in C19)
    r7r = R7.get(m, "not in R7 wave")
    r7cls = ("OK" if "rc=0" in r7r else next((k for k in ("NO_RECIPE", "PORT_MISMATCH", "MAP_AMBIGUOUS", "ENTRY_NOT_UNIQUE", "MACRO_PLACEMENT")
                                            if k in r7r), "EXCLUDED/NOT-RUN"))
    g = M.get(m)
    if isinstance(g, list):
        c18cls = ",".join(sorted({x["cls"] for x in g})); kits = [x["kit"] for x in g if x.get("kit")]
        c18msg = " || ".join(x["msg"][:200] for x in g if x["cls"] != "OK")
    elif isinstance(g, dict):
        c18cls, kits, c18msg = g["cls"], [], g["msg"]
    else:
        c18cls, kits, c18msg = ("not generated (WAIT-C19)" if aff else "not generated"), [], ""
    action = a.get("action") or ("WAIT-C19" if aff else "?")
    rows.append(dict(module=m, instances=c["inst"], outline_um=c["outlines"], pins_files=c["pins_files"], c19_affected=aff,
                     live_job_or_queue=a.get("live", "none"), owner=a.get("owner", ""), r7_gen=r7cls, r7_msg=r7r[:240],
                     c18_gen=c18cls, c18_msg=c18msg[:300], c18_kits=kits, preflight=a.get("preflight", ""),
                     action=action, note=a.get("note", "")))
json.dump(dict(schema="hbm_streets3.native_view_kits.v1", plan="intel2:/srv/opentallas-scratch2/claude/hbm-streets2-1027/c18/die_plan.json (6a711a87b7e7)",
               src="origin/main abbbffac9b (flow == hbm canary abbbffac9 live; 47ce1af8bc98 released differs only in tools/die_plan/lec.py)",
               generator="physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py --trial via mk_c18.py (views_c18.json from views_b2r2.py)",
               modules=len(rows), instances=sum(r["instances"] for r in rows), rows=rows), open(out + ".json", "w"), indent=1)
cols = ["module", "instances", "outline_um", "c19_affected", "live_job_or_queue", "owner", "r7_gen", "c18_gen", "preflight", "action", "note"]
with open(out + ".tsv", "w") as f:
    f.write("\t".join(cols) + "\n")
    for r in rows:
        f.write("\t".join(json.dumps(r[k]) if isinstance(r[k], (list, bool)) else str(r[k]) for k in cols) + "\n")
import collections
print(collections.Counter(r["action"].split()[0] + (" " + r["action"].split()[1] if r["action"].startswith("BLOCKED") else "") for r in rows))
