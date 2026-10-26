#!/bin/bash
# PATH-QC-N59-5 fix (3) lockstep + mutants on the FULL native59 part (qfd_qc_native59_part, kit defines), Verilator 5.032.
# Models: old = RTL before fix (3) (d3b38e9245^ svc), new = fix (3), mutW = new with the decode taken from the UNREGISTERED
# bnd_native_cmd (one cycle early: must be caught), mutB = new with the token bound 151936 -> 151937 (must be caught).
# Usage: run_lockstep.sh REPO_WT OUT_DIR [CYCLES]
set -euo pipefail
WT=$1; O=$2; N=${3:-40000}
P=$WT/results/qc_n59_2145; mkdir -p $O; cd $O
for m in old new mutW mutB; do rm -rf rtl_$m; cp -r $P/inputs/rtl rtl_$m; cp $WT/physical/asap7_memory_macros/ot_sram_1r1w_32x512_m1/ot_sram_1r1w_32x512_m1.v rtl_$m/; done
git -C $WT show d3b38e9245^:results/qc_n59_2145/inputs/rtl/qfd_native59_svc_obs1.sv > rtl_old/qfd_native59_svc_obs1.sv
S=rtl_mutW/qfd_native59_svc_obs1.sv
grep -q 'wire emb_go=p_emb_go;' $S; sed -i 's/wire emb_go=p_emb_go;/wire emb_go=bnd_emb_go;/; s/wire cmd_bad=p_cmd_bad;/wire cmd_bad=bnd_cmd_bad;/' $S; grep -q 'wire cmd_bad=bnd_cmd_bad;' $S
S=rtl_mutB/qfd_native59_svc_obs1.sv
grep -q "bnd_native_cmd\[375:358\]>=18'd151936" $S; sed -i "s/bnd_native_cmd\[375:358\]>=18'd151936/bnd_native_cmd[375:358]>=18'd151937/" $S; grep -q "18'd151937" $S
cp $P/n59_5/lockstep/gen_harness.py $O/
sha256sum rtl_*/qfd_native59_svc_obs1.sv > svc_sha256.txt
FILES=$(sed 's#^results/qc_n59_2145/inputs/rtl/##' $P/inputs/files.f | tr '\n' ' ')
docker run --rm --memory=48g -v $O:/o -w /o --entrypoint bash verilator/verilator:v5.032 -c "
set -e
for m in old new mutW mutB; do
  (cd rtl_\$m && verilator --cc -O3 --x-assign fast --x-initial fast -Wno-fatal -Wno-lint -Wno-style -DSYNTHESIS -DOT_N59_WIF -DOT_N59_STN \
     --top-module qfd_qc_native59_part --prefix V\$m -Mdir /o/obj_\$m $FILES ot_sram_1r1w_32x512_m1.v > /o/verilate_\$m.log 2>&1) &
done; wait
for m in old new mutW mutB; do (make -s -C obj_\$m -f V\$m.mk libV\$m.a OPT_FAST=-O1 > build_\$m.log 2>&1) & done; wait
python3 /o/gen_harness.py obj_old/Vold.h old new mutW mutB > tb.cpp
make -s -C obj_old -f Vold.mk libverilated.a > build_rt.log 2>&1
VR=/usr/local/share/verilator/include; [ -d \$VR ] || VR=\$(dirname \$(find / -name verilated.h -path '*include*' 2>/dev/null | head -1))
g++ -O1 -std=c++17 -I\$VR -I\$VR/vltstd -Iobj_old -Iobj_new -Iobj_mutW -Iobj_mutB tb.cpp obj_old/libVold.a obj_new/libVnew.a obj_mutW/libVmutW.a obj_mutB/libVmutB.a obj_old/libverilated.a -lpthread -latomic -o tb
./tb $N 0 | tee lockstep.txt; ./tb $N 1 | tee -a lockstep.txt
"
