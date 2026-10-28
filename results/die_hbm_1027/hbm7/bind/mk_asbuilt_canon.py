#!/usr/bin/env python3
"""DIE-HBM-7 (2026-10-28): as-built partition map for the CANONICAL four-role HBM source (Codex canonical_storage,
hbm_current_native_top, 375 leaves) on plan C20j.  Diagnostic map, no plan adoption (COORD 06:51 (3)).

Map rules, in order (no invented placement):
  1. census_map.json parts: leaf -> partition; local name = plan content 'u_' + name with NW/NE -> Q (as DIE-HBM-6).
  2. census_map slice rules (one leaf over several partitions): OPEN; they need dissolve + per-child rules.
  3. FOLD CONTRACT slots (native_vms_four_role_contract: NWq0->SW, NEq0->SE, NWq1->NW, NEq1->NE; the 8-SM fold
     accepted by COORD 06:51): a south-role leaf X_SW / X_SE takes the q0 slot of the hub its role is folded into
     (NW_hub / NE_hub), its north twin X_NW / X_NE the q1 slot.  Hub hard cores carry __q0/__q1 instance halves; a plan
     content without halves (vmb banks) gives the S role the first FREE same-module content of that hub.
  4. Anything else is reported 'needs_plan_slot' (not bound).
Usage: mk_asbuilt_canon.py --plan C20J_DIR --base-ab canonical asbuilt.json --die top.sv --out OUT"""
import argparse,collections,json,re
from pathlib import Path
INST_RE=re.compile(r"^\s+(\w+)\s*(?:#\((?:.|\n)*?\))?\s+(\w+)\s*\(\n",re.M)
QT=re.compile(r"_(NW|NE|SW|SE)(?=\d|_|$)")
ROLE_HUB={"NW":("NW_hub","q1"),"SW":("NW_hub","q0"),"NE":("NE_hub","q1"),"SE":("NE_hub","q0")}
def canon_mod(m):
  m=re.sub(r"__pv\d+$","",m);return re.sub(r"(_rc|_s|_h|_sp2|_p|2|_nw2?_t|_nw_t|_sw_t|_e_t|_w2)$","",m)
ap=argparse.ArgumentParser()
for k in ("--plan","--base-ab","--die","--out"): ap.add_argument(k,required=True)
a=ap.parse_args()
P=json.load(open(Path(a.plan)/"die_plan.json"));CM=json.load(open(Path(a.plan)/"census_map.json"))
leaves={i:m for m,i in INST_RE.findall(open(a.die).read())}
ptype={pp["name"]:pp["type"] for pp in P["partitions"]}
rules=[(re.compile(x),g) for x,g in CM["rules"]]
rep=collections.defaultdict(list);parts={};free={}
def cont_of(pn): return {c["inst"]:c for c in P["partition_types"][ptype[pn]].get("contents",[])}
def hard_of(pn): return {h["inst"] for h in P["partition_types"][ptype[pn]].get("hard_cores",[])}
for pn in ptype: free[pn]=set(cont_of(pn))
by_part=collections.defaultdict(list);rest=[]
for i,m in sorted(leaves.items()):
  if i in CM["parts"]: by_part[CM["parts"][i]].append(i);continue
  g=next((g for rx,g in rules if rx.search(i)),None)
  if g: rep["slice_open"].append([i,m,CM["groups"][g]]);continue
  rest.append(i)
for pn,insts in sorted(by_part.items()):
  t=P["partition_types"][ptype[pn]];cont=cont_of(pn)
  if t.get("hard") and len(cont)==1:
    for i in insts: parts[i]=[pn,next(iter(cont))] if len(insts)==1 else pn
    continue
  for i in insts:
    c1="u_"+QT.sub("_Q",i)
    if c1 in free[pn]: parts[i]=[pn,c1];free[pn].discard(c1);rep["census"].append(i);continue
    mm=re.match(r"(.*?)(\d+)$",c1);hit=None
    if mm and pn.startswith("NE_"):                     # NE replicas of per-SM services: index - 4 / - 16 (DIE-HBM-6 rule)
      k=int(mm.group(2));w=len(mm.group(2));d=16 if "_ctl_" in c1 else 4
      c2=f"{mm.group(1)}{k-d:0{w}d}"
      if k-d>=0 and c2 in free[pn]: hit=c2
    if hit: parts[i]=[pn,hit];free[pn].discard(hit);rep["census_index_shift"].append([i,pn,hit]);continue
    cand=[c for c in free[pn] if canon_mod(cont[c]["module"])==canon_mod(leaves[i])]
    if len(cand)==1: parts[i]=[pn,cand[0]];free[pn].discard(cand[0]);rep["census_module_match"].append([i,pn,cand[0]])
    else: parts[i]=pn;rep["census_no_local_name"].append([i,pn,sorted(cand)])
# 3. fold-contract slots
for i in rest:
  m=QT.search(i);role=m.group(1) if m else None
  if role in ROLE_HUB:
    pn,half=ROLE_HUB[role];cont=cont_of(pn);hard=hard_of(pn);c1="u_"+QT.sub("_Q",i)
    if c1 in cont and f"{c1}__{half}" in hard:
      parts[i]=[pn,c1];rep["fold_half"].append([i,leaves[i],pn,f"{c1}__{half}"]);continue
    if i.startswith("vmb_"):                            # S-role bank k -> the hub's second bank hard core u_vmb_Q<k>_mu1
      k=re.search(r"(\d+)$",i).group(1);h=f"u_vmb_Q{k}_mu1"
      if h in hard: parts[i]=[pn,h];rep["fold_bank_slot"].append([i,leaves[i],pn,h]);continue
    if i.startswith("hb_idx__s_"):
      g=f"g_hb_idx__s_{'NW' if role=='SW' else 'NE'}";rep["slice_open_fold"].append([i,leaves[i],CM["groups"][g]]);continue
    # vmb-style: base content index k (Q<k>) or its _mu1 twin, first free same-module content
    cand=sorted(c for c in free[pn] if canon_mod(cont[c]["module"])==canon_mod(leaves[i]))
    km=re.search(r"(\d+)$",i)
    pref=[c for c in cand if km and re.search(rf"Q{km.group(1)}(_mu1)?$",c)]
    pick=(pref or cand or [None])[0]
    if pick: parts[i]=[pn,pick];free[pn].discard(pick);rep["fold_free_slot"].append([i,leaves[i],pn,pick]);continue
  if re.match(r"u_mu_fused_n4_(nw|ne)$",i):
    pn="NW_hub" if i.endswith("nw") else "NE_hub"
    if "u_mu_fused_n4" in hard_of(pn): parts[i]=[pn,"u_mu_fused_n4"];rep["mu_n4_slot"].append([i,pn]);continue
  if i in ("hb_ckgen","u_mu_fused_programme","u_mu_fused_root","b2_ep1_root"):
    parts[i]="root";rep["root_proposed_needs_plan_content"].append([i,leaves[i]]);continue
  rep["needs_plan_slot"].append([i,leaves[i],role])
base=json.load(open(a.base_ab))
ab=dict(base);ab["note"]=("DIE-HBM-7 10-28: canonical four-role source mapped onto C20j: census_map parts + 8SM-fold-contract slots "
  "(S role -> q0 half of the folded hub, N role -> q1); slice rules OPEN; diagnostic, no plan adoption. "
  "Generated by results/die_hbm_1027/hbm7/bind/mk_asbuilt_canon.py. Base note: "+base.get("note",""))
ab.pop("map",None);ab["map_file"]="asbuilt_map_canon.json"
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
json.dump(ab,open(out/"asbuilt_canon.json","w"),indent=1)
json.dump(dict(note="DIE-HBM-7 canonical map (census parts + fold-contract slots; slice rules OPEN)",parts=parts,rules=[]),open(out/"asbuilt_map_canon.json","w"),indent=1)
summ={k:len(v) for k,v in rep.items()};summ["leaves"]=len(leaves);summ["mapped"]=len(parts)
json.dump(dict(summary=summ,**rep),open(out/"asbuilt_canon_report.json","w"),indent=1)
print(json.dumps(summ));[print(" ",k,v) for k in ("needs_plan_slot","fold_half","fold_free_slot","census_no_local_name") for v in rep.get(k,[])]
