#!/bin/bash
# usage: boot_d_gate.sh KV42_BUILD KV42_TREE OUT
# TOK-QK/D 2026-10-24: kv3_pc_part (pc_EN_0: 4 HOST slices + 4 kvpc PC paths) flat sub-bench of the HBM cold boot with the
# kvpc reset on the delivered HBM reset (+KVPC_RST_HBM = fix A) and fix B, for fix D in both design forms:
#   DFI   : kv42 + B, apply_D dfi-core (owner decision 14: the PHY DFI clock is the core clock; the partition's clk_clk_hbm
#           and the PHY model both run on clk, +DFI_CORE)                          -> every slice done & ok, 0 faults
#   HBM   : kv42 + B + apply_D --mode hbm-lanes (controller on the HBM clock, every HBM<->HBM lane register on clk_clk_hbm),
#           REAL HBM clock, swept over HBM/core phase and rate                       -> every slice done & ok, 0 faults
#   MUT   : kv42 + B (lanes on the partition default clock = the finding), real HBM clock, same sweep -> must FAIL somewhere
# Fleet only (Verilator; ~5 GB per build, ~1-2 GB per run).
set -uo pipefail
K=${1:?kv42 build dir}; T=${2:?kv42 staged tree}; O=${3:?out}; H=$(cd $(dirname $0) && pwd); R=$(cd $H/../../../.. && pwd)
mkdir -p $O; O=$(cd $O && pwd); K=$(cd $K && pwd); T=$(cd $T && pwd)
grep -q "$T/" $K/obj/Vkv3_pc_part__hierMkArgs.f || { echo "FAIL $K was not built from $T"; exit 1; }
for v in MUT HBM; do rm -rf $O/tree_$v; cp -a $T $O/tree_$v; $R/tools/qwen_layerbench/kv_dieslice/kv43/apply_B.sh $O/tree_$v > $O/apply_B_$v.log || exit 1; done
$R/tools/qwen_layerbench/kv_dieslice/kv43/apply_D.sh $O/tree_HBM --mode hbm-lanes > $O/apply_D_HBM.log 2>&1 || { cat $O/apply_D_HBM.log; exit 1; }
$R/tools/qwen_layerbench/kv_dieslice/kv43/apply_D.sh $O/tree_HBM --mode hbm-lanes > $O/apply_D_HBM_again.log 2>&1 || exit 1
grep -q "no WRONG_CLOCK lane" $O/apply_D_HBM_again.log || { echo "FAIL apply_D hbm-lanes not idempotent"; cat $O/apply_D_HBM_again.log; exit 1; }
PCS=$(grep -o "$K/top_s/kv3_pc_part.sv" $K/obj/Vkv3_pc_part__hierMkArgs.f | head -1)
for v in MUT HBM; do
  M="$T/=$O/tree_$v/"; [[ -n $PCS ]] && M="$M;$PCS=$O/tree_$v/src/bind__rtl/kv3_pc_part.sv"
  $H/build.sh $K $O/pcb_$v "$M" > $O/build_$v.out 2>&1 &
done
wait
for v in MUT HBM; do [[ -x $O/pcb_$v/obj/Vtb_pcpart ]] || { cat $O/build_$v.out; tail -30 $O/pcb_$v/build.log; echo "FAIL build $v"; exit 1; }; done
grep -q "TOK-QK/D" $O/pcb_HBM/srcs.f || grep -l "TOK-QK/D" $(grep 'kv3_pc_part.sv$' $O/pcb_HBM/srcs.f) >/dev/null || { echo "FAIL HBM build did not take the D partition"; exit 1; }
# sweep: (half period ps, first-edge phase ps): rate 0.977 GHz at 8 phases, + 0.9 / 1.05 GHz, + equal rate at 4 phases
SW="512:0 512:64 512:128 512:256 512:384 512:512 512:640 512:896 556:0 556:300 476:0 476:200 417:0 417:100 417:208 417:300"
run(){ # variant tag args...
  local v=$1 t=$2; shift 2; (cd $O/pcb_$v && ./obj/Vtb_pcpart +KVPC_RST_HBM +MAXCYC=25000 "$@" > $O/$v.$t.log 2>&1); }
N=0
run HBM DFI +DFI_CORE &   # dfi-core: the D partition with clk_clk_hbm == clk is exactly the dfi-core vehicle's pc partition
run MUT DFI +DFI_CORE &
for s in $SW; do h=${s%%:*}; p=${s##*:}
  run HBM h${h}p$p +HCK_HALF_PS=$h +HCK_PHASE_PS=$p &
  run MUT h${h}p$p +HCK_HALF_PS=$h +HCK_PHASE_PS=$p &
  N=$((N+2)); [[ $((N % 16)) == 0 ]] && wait
done
wait
end(){ grep -oE 'PCB END cyc [0-9]+ sdo [01]+ soo [01]+ sfo [01]+' $1; }
fo(){ grep -cE '^PCB PC[0-3] c_v .* fo 1' $1; }
rvx(){ grep -E '^PCB PC[0-3] phy_pi_valid' $1 | awk '$4!=$6' | wc -l; }   # PCs whose controller saw != PHY returns
ok=1; nmf=0
for f in $O/*.log; do case $f in *apply*) continue;; esac
  b=$(basename $f .log); echo "== $b: $(end $f) | controllers_faulted $(fo $f) | pi!=rv PCs $(rvx $f)"; done
for f in $O/HBM.*.log; do
  end $f | grep -q 'sdo 1111 soo 1111 sfo 0000' && [[ $(fo $f) == 0 && $(rvx $f) == 0 ]] || { echo "D FAIL $(basename $f)"; ok=0; }; done
for f in $O/MUT.h*.log; do end $f | grep -q 'sdo 1111 soo 1111 sfo 0000' && [[ $(fo $f) == 0 ]] || nmf=$((nmf+1)); done
end $O/MUT.DFI.log | grep -q 'sdo 1111 soo 1111 sfo 0000' && [[ $(fo $O/MUT.DFI.log) == 0 ]] || { echo "dfi-core (MUT tree, single clock) not all ok"; ok=0; }
echo "MUTANT (lanes on partition default clock, real HBM clock): $nmf of $(ls $O/MUT.h*.log | wc -l) sweep points FAIL"
[[ $nmf -gt 0 ]] || { echo "mutant not observed"; ok=0; }
rm -rf $O/pcb_*/obj
[[ $ok == 1 ]] && echo PASS KV_BOOT_D_PCPART_ALL_SLICES_OK_SWEEP_MUTANT_OBSERVED || { echo FAIL KV_BOOT_D_PCPART; exit 1; }
