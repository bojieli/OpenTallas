#!/bin/bash
# TOKj-KV 10-23: build the KV die-slice vehicle (whole bound top + PHY bench models + tb) with Verilator 5.050.
#   build.sh VDIR OUT [lint]     VDIR = staged vehicle dir (stage_src.sh output: files.f incdirs.f hostside.f src/)
# The staged lists carry the staging host's absolute prefix; they are re-rooted to VDIR here (fleet copies).
set -u
H=$(cd "$(dirname "$0")" && pwd); V=$(readlink -f $1); O=$(mkdir -p $2 && readlink -f $2); MODE=${3:-build}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
if [ -z "${NOREGEN:-}" ] || [ ! -f $O/vl.f ]; then   # NOREGEN=1: keep the lists (incremental hierarchical re-run)
P0=$(head -1 $V/files.f | sed 's#/src/.*##')
for f in files.f incdirs.f hostside.f; do sed "s#$P0#$V#g" $V/$f > $O/$f; done
# the analog PLL model -> bench copy (no free-running delays; same lock law)
grep -v '/qkd_pll_analog_model.sv$' $O/files.f > $O/f.tmp && mv $O/f.tmp $O/files.f
# hierarchical Verilator blocks = every bound partition type except the PHY-model hosts (phy_*, sys_SD*, sys_c: their PHY
# bench models read the bench far ends by hierarchical reference) -> the top only wires lanes (monolithic: > 400 GB)
TOPF=$(grep '/qwen_kvsys_bound_top.sv$' $O/files.f); RD=$(dirname $TOPF)
# KV-TOK 10-24: Verilator 5.050 inlines every hier_block module that has parameters -> top without the (== default)
# overrides + partition types with header localparams (exact; strip_default_params.py); the lists point at those copies
if [ "${HIER:-1}" = 1 ]; then
  python3 $H/strip_default_params.py $TOPF $RD $O/top_s || exit 2
  sed -i -E "s#^$RD/((qwen_kvsys_bound_top|kv3_[A-Za-z0-9_]+)\.sv)\$#$O/top_s/\1#" $O/files.f
  sed -i "s#^-y $RD\$#-y $O/top_s\n-y $RD#" $O/incdirs.f
fi
{ echo '`verilator_config'; for m in $(grep -ho '^module kv3_[A-Za-z0-9_]*' $RD/kv3_*.sv | awk '{print $2}' | sort -u); do
    case $m in kv3_phy*|kv3_sys_SD*|kv3_sys_c_part) ;; *) echo "hier_block -module \"$m\"";; esac; done; } > $O/hier.vlt
R=$(cd $H/../../.. && pwd)
IMGD=${D2D_IMG:-$R/physical/die_plan/qwen_kvsys/boot_v36/image_kv41}   # the pair image the KV boot image carries
# TOK-QK/D dfi-core: a top without HBM clock inputs (kv43/apply_D.sh, owner decision 14) -> the bench drives none
DFI=$(grep -q 'input  wire clk_clk_hbm_' $TOPF && echo "" || echo "+define+KV_DFI_CORE")
cat > $O/vl.f <<EOF
$DFI
-Wno-fatal
-Wno-lint
-Wno-style
-Wno-MULTIDRIVEN
-Wno-TIMESCALEMOD
-Wno-PINMISSING
-Wno-MODDUP
--timescale 1ns/1ps
--top-module tb_kvslice
$H/kvs_link_phy_models.sv
$H/qkd_pll_analog_model_bench.sv
$H/qkd_hbm3e_phy_pc4_bench.sv
$H/kvs_compute_end.sv
$R/rtl/qwen_split/qfd_kvn_static_transport.sv
$R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv
$R/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv
+incdir+$IMGD
+incdir+$H
$H/tb_kvslice.sv
EOF
cat $O/hostside.f $O/files.f $O/incdirs.f >> $O/vl.f
[ "${HIER:-1}" = 1 ] && echo "$O/hier.vlt" >> $O/vl.f
fi
cd $O
if [ "$MODE" = lint ]; then
  /usr/bin/time -v $VL --lint-only --timing -f vl.f > lint.log 2>&1; rc=$?
  echo "LINT rc=$rc errors $(grep -c '^%Error' lint.log) $(grep 'Maximum resident' lint.log)"; exit $rc
fi
J=${J:-48}
/usr/bin/time -v $VL --binary --timing $([ "${HIER:-1}" = 1 ] && echo --hierarchical) -O1 --x-assign ${XASSIGN:-fast} --x-initial ${XINIT:-fast} --output-split 20000 --output-groups 256 \
  -j $J --build-jobs $J -CFLAGS ${COPT:--O1} -Mdir obj -f vl.f > build.log 2>&1; rc=$?
echo "BUILD rc=$rc errors $(grep -c '^%Error' build.log) $(grep -E 'Maximum resident|Elapsed' build.log | tr -s ' ' | tr '\n' ' ')"
exit $rc
