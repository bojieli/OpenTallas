# QC-A0-KITS-12: NK both-reset anchor projection = reviewed NL reset6 FF anchors (same instance names in the NK synth)
# NL anchors that fall under the NODE child + halo are NOT anchored (GPL places them by connectivity off the macro).
# v2 (after DPL-0033 in the 1.944-um street x388.10..390.04 between rawfault+halo and NODE halo): also unanchor that street; NX0 = rawfault east edge 383.664.
# projected west off the NODE child + 4.32 um halo, plus the reset-capture anchors of nk_both_reset_contract.json.
import re,json,sys
from pathlib import Path
R=Path("/srv/opentallas-scratch2/claude/qc-a0-kits-12-1029");D=R/"nk_place"
v=next((D/"run/results/asap7").glob("*/base/1_synth.v")).read_text()
names={m.replace("\\","") for m in re.findall(r"^\s*\S+\s+(\\\S+)\s+\(",v,re.M)}
NX0,NX1,NY0,NY1=383.664,394.488+47.52+4.32,688.656-4.32,688.656+432.0+4.32
WEST=NX0-1.2
over={"u_g.g_rst_native.q$_DFF_P_":(312.878,669.996),"u_g.t_out_reset_q$_DFF_P_":(136.728,874.935),
 "u_g.t_out\\[512\\]$_SDFF_PN0_":(19.5,989.5),"u_g.t_out\\[513\\]$_SDFF_PN0_":(20.5,990.5),
 "u_g.n_y\\[512\\]$_SDFF_PN0_":(8.0,1102.5),"u_g.n_y\\[513\\]$_SDFF_PN0_":(8.0,1103.5),
 "u_g.fy_q$_SDFF_PN0_":(8.0,759.5),"u_g.mis_q$_SDFF_PN0_":(8.0,760.5)}
rows=[];moved=[];skipped=[]
for line in Path("/srv/opentallas-scratch2/claude/codex-qc-a0-0251/nl_anchors_reset6.tsv").read_text().splitlines():
    n,x,y=line.split("\t");x=float(x);y=float(y)
    if n in over: continue
    if n.replace("\\","") not in names: skipped.append(n); continue
    if NX0<=x<=NX1 and NY0<=y<=NY1: moved.append([n,x,y]); continue  # under NODE+halo: left to GPL (connectivity), no pile
    rows.append((n,x,y))
for n,(x,y) in over.items():
    assert n.replace("\\","") in names, n
    rows.append((n,x,y))
(D/"anchor_targets.tsv").write_text("".join(f"{n}\t{x}\t{y}\n" for n,x,y in rows))
(D/"anchor_projection.json").write_text(json.dumps(dict(kept=len(rows),unanchored_under_node=len(moved),missing_in_nk=len(skipped),unanchored=moved,missing=skipped[:200],overrides=over),indent=1))
print("ANCHORS",len(rows),"UNANCHORED_UNDER_NODE",len(moved),"MISSING",len(skipped))
