#!/bin/bash
# Actual controller + actual SRAM buffer, same-edge comparison to recovered b79 source.
# Canonical TP192 vector cases come from existing hgi_coll_tkm_tp192_vectors.py.
set -euo pipefail
out=${1:?output};vec=${2:?existing-vector-directory};mut=${MUT:-0}
mkdir -p "$out"
p=rtl/hbm_accel/generic/collective/tkm
sources=("$p/bench/tb_tkm_ctl_exactedge.sv" "$p/bench/ctl_recovered_b79.sv" "$p/ot_hgi_coll_tkm_ctl.sv" "$p/ot_hgi_coll_tkm_buffer.sv" rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
sha256sum "${sources[@]}" "$0" > "$out/sources.sha256"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$v" --binary --timing -j 8 -O1 -Wno-fatal -Wno-TIMESCALEMOD -Wno-WIDTH --top-module tb_tkm_ctl_exactedge -GMUT="$mut" --Mdir "$out/obj" "${sources[@]}" > "$out/build.log" 2>&1
if [ "$mut" != 0 ];then
 set +e
 "$out/obj/Vtb_tkm_ctl_exactedge" +DIR="$vec/syn_sel" > "$out/mutant.log" 2>&1
 rc=$?
 set -e
 if [ "$rc" != 0 ] && grep -q 'TKM_CTL_EXACTEDGE FAIL' "$out/mutant.log";then echo "TKM_CTL_EXACTEDGE MUTANT $mut REJECTED";exit 0;fi
 echo "TKM_CTL_EXACTEDGE MUTANT $mut ESCAPED";exit 1
fi
for case_ in syn_sel syn_cand rank128_zeros;do
 "$out/obj/Vtb_tkm_ctl_exactedge" +DIR="$vec/$case_" > "$out/$case_.log" 2>&1
 grep 'TKM_CTL_EXACTEDGE PASS' "$out/$case_.log"
done
"$out/obj/Vtb_tkm_ctl_exactedge" +DIR="$vec/syn_sel" +NOUT=65 > "$out/partial65.log" 2>&1
grep 'TKM_CTL_EXACTEDGE PASS' "$out/partial65.log"
echo TKM_CTL_EXACTEDGE_ALL_PASS
