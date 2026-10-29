"""DIE-HBM-10 C25b: SW/SE fold map side data (TOK-HBM-3 ASK, COORD default YES). S role = q0 half of the folded hub
(ROLES NWq0->SW, NEq0->SE, NWq1->NW, NEq1->NE; four_role_calendar.py). Each S net of the TOK-HBM-2 census is mapped to the
plan instance that serves it: the __q0 copy of the family in the same hub partition, only where the plan has exactly one
such copy (MAPPED); otherwise UNMAPPED with the candidates (needs the binder's as-built map), never guessed.
usage: mk_fold_map.py PLAN_JSON CENSUS_JSON OUT_JSON"""
import json, sys, re, hashlib, collections
plan, cen, out = sys.argv[1:4]
P = json.load(open(plan)); T = P["partition_types"]; C = json.load(open(cen))
HUB = {"SW": ("NW_hub", "q_hub_nw"), "SE": ("NE_hub", "q_hub_ne")}
FAM = {"hb_dbk": "u_hb_dbk_Q__q0", "smw": "u_smw_Q__q0", "xl_ctl": "u_xl_Q_ctl__q0"}   # unique plan __q0 copies
rows = []
for r in C["nets"]:
    m = re.match(r"(\w+?)_(SW|SE)(\w*?)__(\w+)$", r["net"])
    fam, role, idx, port = m.group(1), m.group(2), m.group(3), m.group(4)
    key = fam + (idx if idx.startswith("_") else "")
    part, tn = HUB[role]
    insts = {h["inst"] for h in T[tn]["hard_cores"]}
    row = dict(net=r["net"], width=r["width"], role=role, partition=part, port=port,
               n_role_template=(r.get("mirror_driver") or {}).get("instance"))
    tgt = FAM.get(key)
    if not r.get("mirror_driver"):
        row.update(status="NO_PROVIDER", why="no N-role mirror driver (svg_S*: SM key lines of stack 1); the 8-SM release has no S-role SM")
    elif tgt and tgt in insts:
        row.update(status="MAPPED", serving_instance=f"{part}.{tgt}", serving_port=port,
                   basis="family's unique __q0 copy in the same hub (S role = q0 half)")
    else:
        cand = sorted(i for i in insts if "__q0" in i and fam.split("_")[0][:4] in i.replace("_", ""))
        row.update(status="UNMAPPED", candidates=cand[:8],
                   why="the plan has no unique q0-half copy of this family; the serving instance needs the binder's as-built map")
    rows.append(row)
cnt = collections.Counter(x["status"] for x in rows)
doc = dict(schema="opentallas.hbm.s_role_fold_map.v1", plan=plan, plan_sha256=hashlib.sha256(open(plan, "rb").read()).hexdigest(),
           census=cen, roles={"NWq0": "SW", "NEq0": "SE", "NWq1": "NW", "NEq1": "NE"},
           constraints="no SW/SE hub rebuild; HBM 8 SMs; IDX single-row calendar", counts=dict(cnt), nets=rows)
json.dump(doc, open(out, "w"), indent=1)
print(dict(cnt), sum(x["width"] for x in rows if x["status"] == "MAPPED"), "bits mapped")
