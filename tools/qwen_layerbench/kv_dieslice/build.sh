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
TB="$H/tb_kvslice.sv"
[ "${NATIVE_BOOT:-0}" = 0 ] || TB="$H/tb_kvslice_native.sv"
printf "%s\n" "${NATIVE_BOOT:-0}" > "$O/native_boot.profile"
python3 $H/bind_tb_clocks.py "$TOPF" "$TB" "$O/tb_kvslice.sv" || exit 2
R=$(cd $H/../../.. && pwd)
JOIN_SRC=
[ "${NATIVE_BOOT:-0}" = 0 ] || JOIN_SRC="$R/rtl/physical/ot_fdi_join2.sv"
IMGD=${D2D_IMG:-$R/physical/die_plan/qwen_kvsys/boot_v36/image_kv41}   # the pair image the KV boot image carries
# TOK-KV-1 10-28: every bench include that names bound-top nets is GENERATED here from the bound top (never a hand-kept
# copy of an older bind): the hub_Wi partition record (partrec/gen_partrec.py) and the kvpc reset diag force list.
mkdir -p $O/gen
python3 -I $H/partrec/gen_partrec.py $TOPF $RD/kv3_hub_Wi_part.sv hub_Wi $O/gen > $O/gen/partrec.log || exit 2
mv $O/gen/rec_hub_Wi.svh $O/gen/partrec_hub_Wi.svh
python3 -I $H/gen_kvpc_rst_diag.py $TOPF $O/gen/kvpc_rst_diag.svh > $O/gen/kvpc_rst_diag.log || exit 2
# bench-side sources (off-die peers + PHY models); the UCIe macro model is the hard macro's own simulation model
UCIE_MODEL=$R/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv
BENCH="$H/kvs_link_phy_models.sv $UCIE_MODEL $H/qkd_pll_analog_model_bench.sv $H/qkd_hbm3e_phy_pc4_bench.sv $H/kvs_compute_end.sv $JOIN_SRC $R/rtl/qwen_split/qfd_kvn_static_transport.sv $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv $R/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv"
# close the lists over leaf modules / packages with the BINDER's own closure (bind manifest of provenance_bind.json)
for f in provenance_bind.json bind_report.json bind.f; do cp $V/$f $O/ || exit 2; done
python3 -I $H/vehicle_closure.py $O $R --bench $BENCH $O/tb_kvslice.sv > $O/vehicle_closure.log 2>&1 || { cat $O/vehicle_closure.log; exit 2; }
tail -1 $O/vehicle_closure.log
cat > $O/vl.f <<EOF
-Wno-fatal
-Wno-lint
-Wno-style
-Wno-MULTIDRIVEN
-Wno-TIMESCALEMOD
-Wno-PINMISSING
-Wno-MODDUP
--timescale 1ns/1ps
--top-module tb_kvslice
$(printf "%s\n" $BENCH)
+incdir+$O/gen
+incdir+$IMGD
+incdir+$H
$O/tb_kvslice.sv
EOF
cat $O/hostside.f $O/files.f $O/incdirs.f >> $O/vl.f
[ "${HIER:-1}" = 1 ] && echo "$O/hier.vlt" >> $O/vl.f
fi
cd $O
# TOK-QK-4/5 10-27: one source per module. -Wno-MODDUP (above) makes Verilator keep the FIRST of two definitions silently
# (B48: the old vehicle4 qkd_ctrl_pc_nc.sv beside the boot-window copy), so the list is checked before any build or lint;
# a duplicate fails the build. Identical-text later copies are dropped (same elaborated RTL). MODDUP_ALLOW="m1 m2"
# exempts COORD-ruled names only (record the ruling at the caller).
python3 -I $H/check_moddup.py --drop-redundant $O/vl.f --json $O/moddup.json ${MODDUP_ALLOW:+--allow $MODDUP_ALLOW} > $O/moddup.log; mrc=$?
tail -1 $O/moddup.log
if [ $mrc != 0 ]; then grep -e "^MODDUP " $O/moddup.log; echo "BUILD rc=4 duplicate module definitions in vl.f (see $O/moddup.log)"; exit 4; fi
if [ "$MODE" = lint ]; then
  /usr/bin/time -v $VL --lint-only --timing -f vl.f > lint.log 2>&1; rc=$?
  echo "LINT rc=$rc errors $(grep -c '^%Error' lint.log) $(grep 'Maximum resident' lint.log)"; exit $rc
fi
J=${J:-48}
/usr/bin/time -v $VL --binary --timing $([ "${HIER:-1}" = 1 ] && echo --hierarchical) -O1 --x-assign fast --x-initial fast --output-split 20000 --output-groups 256 \
  -j $J --build-jobs $J -CFLAGS ${COPT:--O1} -Mdir obj -f vl.f > build.log 2>&1; rc=$?
echo "BUILD rc=$rc errors $(grep -c '^%Error' build.log) $(grep -E 'Maximum resident|Elapsed' build.log | tr -s ' ' | tr '\n' ' ')"
exit $rc
