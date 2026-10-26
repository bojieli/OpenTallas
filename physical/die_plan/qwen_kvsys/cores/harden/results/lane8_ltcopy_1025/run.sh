#!/bin/bash
# run on epyc1: bash run.sh  (W = worktree with LT_COPY, P = proof dir)
set -u
W=/srv/opentallas-scratch2/claude/wt/kvc2-rtl; P=/srv/opentallas-scratch2/claude/kv-cores-1025r/ltcopy_proof
K=/srv/opentallas-scratch2/claude/kv-cores-1025r/heads/h5m8/e6/kv3_head_eighth_e6__216x216/rtl
V="docker run --rm -i --memory 16g --cpus 4 -u 1000:1000 -e CCACHE_DISABLE=1 -e HOME=/tmp --entrypoint verilator -v /srv/opentallas-scratch2/claude:/srv/opentallas-scratch2/claude -w /srv/opentallas-scratch2/claude/kv-cores-1025r/ltcopy_proof verilator/verilator:v5.032"
cd $P
git -C $W show origin/main:rtl/hdc/nearhbm/ot_qkh_subtiles.sv | python3 -c "
import sys,re; s=sys.stdin.read()
s=re.sub(r'\`ifdef KVD_HMUT\n.*?\n\`else\n(.*?)\`endif\n', r'\1', s, flags=re.S)
s=s.replace('module ot_qkh_lane8 #(','module ot_qkh_lane8_ref #(')
s=s[:s.index('module ot_qkh_ktree')]      # only the lane8 leaf
print(s)" > src/ot_qkh_lane8_ref.sv
python3 - "$W/rtl/hdc/nearhbm/ot_qkh_subtiles.sv" > src/ot_qkh_lane8_new.sv <<'PY'
import sys; s=open(sys.argv[1]).read(); print(s[:s.index('// ---------------------------------------------------------------------------------------------------------------------\n// ot_qkh_ktree')])
PY
DEPS="$K/ot_rst_relay.sv $K/ot_hdc_delay.sv $K/ot_qwen_nearhbm_prod.sv $K/ot_hdc_fp32_add_lat_nr.sv $K/ot_hdc_fp32_add_lat.sv $K/ot_hdc_prefix.sv $K/ot_hdc_fastfp.sv $K/ot_hdc_fp32_mul_lat.sv"
for v in nominal mutant; do
  D=; [ $v = mutant ] && D=+define+KVD_HMUT
  rm -rf obj_$v
  $V --binary --timing -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_lane8_ltcopy -Mdir $P/obj_$v $D \
     $P/tb_lane8_ltcopy.sv $P/src/ot_qkh_lane8_ref.sv $P/src/ot_qkh_lane8_new.sv $DEPS -j 4 > $P/build_$v.log 2>&1 || { echo "build $v failed"; tail -20 $P/build_$v.log; continue; }
  docker run --rm --memory 4g -v $P:$P -w $P verilator/verilator:v5.032 bash -c "$P/obj_$v/Vtb_lane8_ltcopy +N=6000" > $P/$v.log 2>&1 || true
  # verilator image has entrypoint verilator; fall back
  grep -q MITER $P/$v.log || docker run --rm --memory 4g --entrypoint $P/obj_$v/Vtb_lane8_ltcopy -v $P:$P -w $P verilator/verilator:v5.032 +N=6000 > $P/$v.log 2>&1
  echo "$v: $(grep -E 'MITER|MISMATCH' $P/$v.log | tail -3)"
done
