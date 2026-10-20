#!/bin/bash
# QW-DIEFIX-NFAR: tb_qfd_dv_heads cases (Verilator 5.050): fixed heads + die-sidx model (PASS), MUT 8 / 9, old (pre-retag)
# heads + new model (FAIL), fixed heads + old model (FAIL: the old tb model no longer matches)
set -u
H=/srv/opentallas-scratch/claude/qw-diefix-heads; cd $H
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$VERILATOR --version > verilator.version
rm -rf src_old src_oldmodel; cp -a src src_old; cp -a src src_oldmodel
sed -i 's/retag = {t\[7\], b, t\[3\], a};/retag = t;/' src_old/rtl/qwen_dv/qfd_dv_heads.sv
grep -q 'retag = t;' src_old/rtl/qwen_dv/qfd_dv_heads.sv || { echo ANCHOR_MISSING; exit 3; }
cp tb_qfd_dv_heads_oldmodel.sv src_oldmodel/rtl/test/qwen_dv/tb_qfd_dv_heads.sv
run() { name=$1; d=$2; shift 2; (cd $d && JOBS=8 bash rtl/test/qwen_dv/run_heads.sh $H/out_$name "$@" > $H/res_$name.txt 2>&1; echo "rc=$?" >> $H/res_$name.txt) ; }
run fixed src & run mut8 src -GMUT=8 & run mut9 src -GMUT=9 & run oldheads src_old & run oldmodel src_oldmodel &
wait
for n in fixed mut8 mut9 oldheads oldmodel; do echo "== $n: $(tr '\n' ' ' < res_$n.txt)"; done
