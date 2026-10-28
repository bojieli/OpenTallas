#!/bin/bash
# DIE-KV-9 step 3: kit-rtl + ring swap + abc-map cell count for every kv3_pv* type (rings W>=1000 black-boxed)
set -u
WT=/srv/opentallas-scratch2/claude/wt/die-kv-6; R=/srv/opentallas-scratch2/claude/die-kv-9-1028/pvcount; B=/srv/opentallas-scratch2/claude/die-kv-8-1028/bind_s2
P=$WT/results/die_kv_7_1028/event_ectl/plan.json; RC=$WT/physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_kv8.json
mkdir -p $R; cd $WT
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
for t in "$@"; do
  K=$R/kit_$t
  python3 tools/die_plan/bind.py kit-rtl $P --out $B --type $t --kit $K --asbuilt $RC > $R/$t.kitrtl.log 2>&1 || { echo "$t KITRTL_FAIL"; continue; }
  top=$(python3 -c "import json;print(json.load(open(\"$K/kit_rtl.json\"))[\"module\"])" 2>/dev/null || ls $K/*_bound.sv | head -1 | xargs basename | sed s/_bound.sv//)
  bnd=$K/${top}_bound.sv
  python3 results/die_kv_9_1028/ring_swap.py $bnd $K/swap_bound.sv $K/ring_stub.sv > $R/$t.swap.json || { echo "$t SWAP_FAIL"; continue; }
  { for f in $(cat $K/kit_rtl.f | grep -v "^#"); do
      case $f in *_bound.sv) echo "read_verilog -sv $K/swap_bound.sv";; *) echo "read_verilog -sv $f";; esac; done
    echo "read_verilog -sv $K/ring_stub.sv"
    echo "blackbox ot_qwen_tp8_pv_slice_t ot_qwen_tp8_pv_join_t"
    echo "hierarchy -top $top"; echo "synth -top $top"
    echo "dfflibmap -liberty $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib"
    echo "abc -liberty $L/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz -liberty $L/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz -liberty $L/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz -liberty $L/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz"
    echo "opt_clean"; echo "tee -o $R/$t.stat stat -top $top"; } > $R/$t.ys
  echo "$t ys ready $(cat $R/$t.swap.json)"
done
