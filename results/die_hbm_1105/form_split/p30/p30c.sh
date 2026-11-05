set -e
S3=/srv/opentallas-scratch3/claude/hfs3; S2=/srv/opentallas-scratch3/claude/hfs2; W=$S3/wt; cd $W; export PYTHONDONTWRITEBYTECODE=1
Q=results/die_hbm_1105/form_split/p30; R=rtl/hbm_accel/cores_split/reform_1105s/topk
CT=$(find rtl/hbm_accel/index -name ot_hbm_idx_compact_tree.sv | head -1); echo CT $CT
ls $S2/rp28; ls $S2/rp28/new/die_plan.json
python3 -I - <<E
import json
MH=77.784; WW,HH=648.0,302.4
f="$Q/split_p30.json"; d=json.load(open(f)); e=d[0]
e["layout"]["u_fcore.u_core.u_sto"]["wh"]=[WW,HH]
Y=[24.3,116.1,207.9]
for i,m in enumerate(e["macros"]["ot_hbm_idx_topk_store"]):
    r=m["rect_um"]; y=Y[i//3]; m["rect_um"]=[r[0],y,r[2],round(y+MH,3)]
e["clock_entry"]["ot_hbm_idx_topk_store"]=[222.0,109.08]
e["macro_basis"]="HBM-FORM-SPLIT part 30c: outline 648 x 302.4; S face 4152 pins, N 1503: rows off the dense S face (y 24.3), row gaps 14 um (rows between macro rows), N gap 12.4 um; same class as KV prompt k3"
json.dump(d,open(f,"w"),indent=1)
f="physical/die_plan/hbm_arch_cores/recipes_b2.json"; d=json.load(open(f))
print("recipes had", "ot_hbm_idx_topk_store" in d)
ba=dict(defines=[],params={},util=0.45,source="HBM-FORM-SPLIT d44v part 30: tile of ot_hbm_idx_topk_link_static; bench $Q",files=["$R/ot_hbm_idx_topk_tiles.sv","$CT"])
I,T="ot_hbm_idx_topk_ingest","ot_hbm_idx_topk_store"
d[I]=dict(ba,top=I,macros=[]); d[T]=dict(ba,top=T,macros=["ot_sram_1r1w_64x512_m1_r2c2"])
json.dump(d,open(f,"w"),indent=1); open(f,"a").write("\n")
f="physical/die_plan/hbm/reset_contract.json"; x=json.load(open(f)); x["modules"]=sorted(set(x["modules"])|{I,T}); json.dump(x,open(f,"w"),indent=1); open(f,"a").write("\n")
E
rm -rf $S3/p30; mkdir -p $S3/p30; cp -al $S2/rp28/new $S3/p30/new
python3 -I - <<E
import json,os
f="$S3/p30/new/die_plan.json"; D=json.load(open(f)); n=0
for k,T in D["partition_types"].items():
  for h in T.get("hard_cores",[]):
    if h["module"]=="ot_hbm_idx_topk_link_static": h["outline_um"]=[648.0,535.68]; n+=1
os.unlink(f); json.dump(D,open(f,"w"),indent=1); open(f,"a").write("\n"); print("topk slots",n)
E
python3 -I results/die_hbm_1103/reform/mk_split.py $S3/p30/new $Q/split_p30.json $Q --only ot_hbm_idx_topk_link_static 2>&1 | tail -2 | cut -c1-340
mkdir -p $S3/f30c; python3 physical/die_plan/hbm_arch_cores/views_b2r2.py --plan $S3/p30/new/die_plan.json --out $S3/f30c/views.json 2>&1 | tail -1 | cut -c1-80
python3 -I - <<E > $S3/f30c/v.txt
import json
for v in json.load(open("$S3/f30c/views.json"))["view_list"]:
  if v["module"] in ("ot_hbm_idx_topk_ingest","ot_hbm_idx_topk_store"): print(v["view"])
E
cat $S3/f30c/v.txt; rm -rf $S3/f30c/k
for V in $(cat $S3/f30c/v.txt); do (python3 physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py --views $S3/f30c/views.json --view $V --out $S3/f30c/k --clock-pin-entry on --core-macros auto --clock-taps density 2>&1 | grep -E "no LEF|Error|^ot_" | cut -c1-200) & done; wait
for K in $S3/f30c/k/*; do echo $(basename $K) $(find $K -type f | wc -l) $(grep DIE_AREA $K/config.mk) $(sed -n 2p $K/macro_placement.tcl 2>/dev/null | cut -c1-60); ls $K/lec_async.sh; grep -n "^set OT_HOLD_STOP_PS" $K/hold_gate.tcl; done
echo DONE
