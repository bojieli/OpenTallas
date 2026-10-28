#!/bin/bash
# KV-KITS-7/PVJ: regenerate pv_join_t R0 + fR180 kits on this commit (plan hm_r26q2 1d257518), then re-apply the
# GEOM-reviewed pass1 entry reservation (kvr2_reserve.tcl, KV-CORES-R2/R6 pass1_reserve output, carried byte-identical)
# and the pass2 approved single-BUFx4 entry trunk (codex/pv-pass2-0830@826ff576d6 build_pv_trunk.py; census from the
# reviewed placed netlist = same RTL/pins/io/config). usage: build_kits.sh WT PLAN OUTDIR
# KV-KITS-7 10-28: pass2/{r0,fr180}/pv_clock_census.json sinks re-derived by pass2/census_from_synth.py from the kit's own fresh
# synthesized netlist (QK-CORES-10 DRST0 renamed err[0] $_SDFF_PN0_ -> $_DFF_P_; carried names crashed CTS in 123ab8799e77/f4fe40e9cd9b).
set -euo pipefail
W=$1; PLAN=$2; O=$3; D=results/kv_kits_7_pvj_1027
cd $W
G=physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py
for v in r0 fr180; do
  rm -rf $O/$v; mkdir -p $O/$v
  if [ $v = r0 ]; then python3 $G --core-json $D/rtl/ot_qwen_tp8_pv_join_t/ot_qwen_tp8_pv_join_t_core.json --plan $PLAN --out $O/r0 --kit-rtl /srv/opentallas-scratch2/claude/kv-cores-pv/kit_rtl; K=$O/r0/ot_qwen_tp8_pv_join_t__172.8x172.8
  else python3 $G --core-json $D/rtl/ot_qwen_tp8_pv_join_t/ot_qwen_tp8_pv_join_t_fR180_core.json --plan $PLAN --out $O/fr180 --plan-inst pv__u_g0_j --view-tag _fR180 --kit-rtl /srv/opentallas-scratch2/claude/kv-cores-pv2/kit_rtl; K=$O/fr180/ot_qwen_tp8_pv_join_t__172.8x172.8_fR180; fi
  cp $D/pass2/$v/kvr2_reserve.tcl $D/pass2/$v/pv_clock_census.json $K/
  { echo "source /work/kvr2_reserve.tcl"; cat $K/face_flops.tcl; } > $K/ff.tmp && mv $K/ff.tmp $K/face_flops.tcl
  python3 -I $D/pass2/build_pv_trunk.py $W $K $PLAN
  python3 - $W $K <<PY
import json,sys,importlib.util
from pathlib import Path
W,K=Path(sys.argv[1]),Path(sys.argv[2])
def load(n,p):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); sys.path.insert(0,str(p.parent)); s.loader.exec_module(m); return m
G=load("gk",W/"physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py")
L=load("lecm",W/"tools/die_plan/lec.py")
fz=json.loads((K/"freeze.json").read_text()); parent=fz["kit_hash"]
fz["pass2_clock_plan"]=dict(source="codex/pv-pass2-0830@826ff576d6 build_pv_trunk.py (carried, results/kv_kits_7_pvj_1027/pass2)",parent_kit_hash=parent,trunk="1xBUFx4_ASAP7_75t_R",sink_count=len(json.load(open(K/"pv_clock_census.json"))["sinks"]),added_cycles=0,pass1_reserve="kvr2_reserve.tcl carried byte-identical from GEOM-reviewed kit")
fz["kit_hash"]=G.kit_hash(K)
(K/"freeze.json").write_text(json.dumps(fz,indent=1)+"\n")
L.write_kit_provenance(K,W)
print("KIT",K.name,"parent",parent,"kit_hash",fz["kit_hash"])
PY
done
