#!/bin/bash
# usage: boot_b_gate.sh KV42_BUILD KV42_TREE OUT
# KV-TOK B 2026-10-24: kv3_pc_part (pc_EN_0: 4 HOST slices + 4 kvpc PC paths) flat sub-bench of the HBM cold-boot check with
# the kvpc reset on the delivered HBM reset (+KVPC_RST_HBM = fix A) for five source variants of the staged vehicle tree:
#   B     : kv42 + apply_B.sh (controller boot window)                -> every slice done & ok, no controller fault
#   ORIG  : kv42 as staged (original controller)                      -> MUTANT: must time out (no boot column ever issues)
#   WOFF  : B with the window disabled (boot_win reset value 0)       -> MUTANT: must time out
#   NOOBS : B without the write-observer expectation of boot columns  -> MUTANT: controller fault (observer)
#   NORAW : B without the boot read's nominal raw slot                -> MUTANT: controller fault (f_raw)
# Each runs with the real HBM clock and with +HCK_IS_CLK (the partition's PHY po/pi boundary lanes are bound on the core
# clock: with the real 0.977 GHz HBM clock one return can reach a controller twice -- a bind clock-domain finding, not B;
# HCK_IS_CLK isolates it).  B is judged on HCK_IS_CLK (all 4 PCs) and on the real clock for the PCs whose returns arrive
# exactly once.  Fleet only (Verilator); ~5 GB per build.
set -uo pipefail
K=${1:?kv42 build dir}; T=${2:?kv42 staged tree}; O=${3:?out}; H=$(cd $(dirname $0) && pwd); R=$(cd $H/../../../.. && pwd)
mkdir -p $O; O=$(cd $O && pwd)
for v in B WOFF NOOBS NORAW; do rm -rf $O/tree_$v; cp -a $T $O/tree_$v; $R/tools/qwen_layerbench/kv_dieslice/kv43/apply_B.sh $O/tree_$v > $O/apply_$v.log || exit 1; done
ed(){ # variant old new
  local n=0; for c in $(find $O/tree_$1/src -path '*static_kv_20261014*' -name qkd_ctrl_pc_nc.sv); do
    python3 - "$c" "$2" "$3" <<'PY' || exit 1
import sys
p,o,n=sys.argv[1:];t=open(p).read();assert t.count(o)==1,o;open(p,'w').write(t.replace(o,n))
PY
    n=$((n+1)); done; [[ $n -gt 0 ]] || exit 1; }
ed WOFF "if (!h_rn) boot_win <= 1'b1;" "if (!h_rn) boot_win <= 1'b0;"
ed NOOBS "expected_sr_q<=expected_sr_pipe[2]|col_boot;" "expected_sr_q<=expected_sr_pipe[2];"
ed NORAW "wire raw_nom = rawslot_q | boot_raw[BRAW-1];" "wire raw_nom = rawslot_q;"
T=$(cd $T && pwd); grep -q "$T/" $K/obj/Vkv3_pc_part__hierMkArgs.f || { echo "FAIL $K was not built from $T"; exit 1; }
$H/build.sh $K $O/pcb_ORIG "" +define+PCB_ORIG > $O/build_ORIG.out 2>&1 &
for v in B WOFF NOOBS NORAW; do $H/build.sh $K $O/pcb_$v $T/=$O/tree_$v/ > $O/build_$v.out 2>&1 & done
wait
for v in B ORIG WOFF NOOBS NORAW; do [[ -x $O/pcb_$v/obj/Vtb_pcpart ]] || { cat $O/build_$v.out; echo "FAIL build $v"; exit 1; }
  (cd $O/pcb_$v && ./obj/Vtb_pcpart +KVPC_RST_HBM +MAXCYC=25000 > $O/$v.hbm.log 2>&1) &
  (cd $O/pcb_$v && ./obj/Vtb_pcpart +KVPC_RST_HBM +HCK_IS_CLK +MAXCYC=25000 > $O/$v.hbmeq.log 2>&1) & done
wait
ok=1
end(){ grep -oE 'PCB END cyc [0-9]+ sdo [01]+ soo [01]+ sfo [01]+' $1; }
fo(){ grep -cE '^PCB PC[0-3] c_v .* fo 1' $1; }
for f in $O/*.log; do echo "== $(basename $f .log): $(end $f) | controllers_faulted $(fo $f) | $(grep HBM_PHY $f)"; done
end $O/B.hbmeq.log | grep -q 'sdo 1111 soo 1111 sfo 0000' && [[ $(fo $O/B.hbmeq.log) == 0 ]] || { echo "B (HCK_IS_CLK) not all done&ok / faulted"; ok=0; }
end $O/B.hbm.log | grep -qE 'soo [01]1[01]1 ' || { echo "B (real HBM clock) PC0/PC2 not ok"; ok=0; }
for v in ORIG WOFF; do end $O/$v.hbmeq.log | grep -q 'soo 0000 sfo 1111' || { echo "mutant $v not observed"; ok=0; }; done
for v in NOOBS NORAW; do [[ $(fo $O/$v.hbmeq.log) == 4 ]] || { echo "mutant $v not observed"; ok=0; }; done
rm -rf $O/pcb_*/obj $O/tree_*
[[ $ok == 1 ]] && echo PASS KV_BOOT_B_PCPART_ALL_SLICES_OK_MUTANTS_OBSERVED || { echo FAIL KV_BOOT_B_PCPART; exit 1; }
