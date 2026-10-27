#!/bin/bash
# lec_compose.sh WT OUT (HBM-CORES-RTL 2026-10-26): composition LEC of the NE-hub q2 NLINK 2 collective split
#   gold = ot_hfd_coll_q2_hard_v8g_s #(NLINK 2, TP 192, AR_ITER 1, ROWS 256, VM_RT 81) RTL (q2n2.files, read_verilog)
#   gate = split assembly (split_asm.py on the rest_extract parent view): ot_hfd_coll_q2n2_body_core + ot_hfd_coll_q2n2_vm_core
#          + coll_q2 ot_hfd_coll_q2_reduce_core / ot_hfd_coll_q2_ring_ag_core, elaborated + flattened with the same
#          proc / flatten / memory passes, piece-instance prefixes renamed to the parent's u_body.* scope (names only:
#          key points by name are then checked by the next-state proof, never assumed equal)
#   tools/die_plan/lec.py (key points + register correspondence + ABC proof); then the same on a MUTANT assembly
#   (vm core writer_rgx_vm inverted) which must be NOT EQUIVALENT.
set -u
WT=$(readlink -f $1); OUT=$(readlink -f $2); B=$WT/physical/die_plan/hbm/over_cap_split/bench/coll_q2n2_split
P=$WT/rtl/hbm_accel/cores_split; N=$P/ot_hfd_coll_q2n2_hard_v8g; Q2=$P/ot_hfd_coll_q2_hard_v8g
Y=$HOME/.local/opentallas-tools/bin/yosys; L=$OUT/lec; mkdir -p $L
python3 -I $WT/physical/die_plan/hbm/cores/harden/split_asm.py --parent $OUT/rest/coll_q2n2_body_rest.parent.v --top ot_hfd_coll_q2_hard_v8g_s \
  --rest $N/ot_hfd_coll_q2n2_body_core.sv:coll_q2n2_body_rest \
  --piece "$N/ot_hfd_coll_q2n2_vm_core.sv:\\u_body.u_vmasm=u_vmasm,\\u_body.u_writer=u_writer" \
  --piece "$Q2/ot_hfd_coll_q2_reduce_core.sv:\\u_body.u_reduce=u_reduce" \
  --piece "$Q2/ot_hfd_coll_q2_ring_ag_core.sv:\\u_body.u_ring=u_ring" --out $L/asm.v > $L/asm.log 2>&1 || exit 2
# the vm core feeds the writer's clk_rgx_ctrl AND clk_tkw from writer_clk_rgx_ctrl; split_asm keeps the last parent net
# (clk_tkw = clk_vmwrite[5]); the die wiring is clk_rgx_ctrl = clk_vmwrite[4] (LEC models one clock: proof unaffected)
sed -i 's/\.writer_clk_rgx_ctrl(clk_vmwrite\[5\])/.writer_clk_rgx_ctrl(clk_vmwrite[4])/' $L/asm.v
grep -q 'writer_clk_rgx_ctrl(clk_vmwrite\[4\])' $L/asm.v || exit 2
grep -c '\.writer_rgx_vm(\\u_body\.u_upipe\.SL\[6\]\.u\.d3\[8\] )' $L/asm.v | grep -qx 1 || exit 2
sed 's/\.writer_rgx_vm(\\u_body\.u_upipe\.SL\[6\]\.u\.d3\[8\] )/.writer_rgx_vm(~\\u_body.u_upipe.SL[6].u.d3[8] )/' $L/asm.v > $L/asm_mut.v
for side in gate mut; do
  K=$L/kit_$side; rm -rf $K; mkdir -p $K/rtl
  FL=""; GL=""
  for f in $(grep -v '^macro:' $B/q2n2.files); do mkdir -p $K/rtl/$(dirname $f); cp $WT/$f $K/rtl/$f; FL="$FL /work/rtl/$f"
    [ "$(basename $f)" = ot_hfd_coll_q2_hard_v8g_s.sv ] || GL="$GL $K/rtl/$f"; done
  MB=""; for m in $(grep '^macro:' $B/q2n2.files | cut -d: -f2); do f=physical/asap7_memory_macros_v2/$m/${m}_bb.v
    mkdir -p $K/rtl/$(dirname $f); cp $WT/$f $K/rtl/$f; FL="$FL /work/rtl/$f"; MB="$MB $K/rtl/$f"; done
  cat > $K/config.mk <<MK
export DESIGN_NAME = ot_hfd_coll_q2_hard_v8g_s
export VERILOG_FILES = $FL
export VERILOG_DEFINES = -DOT_COLL_ISSUER256_NATIVE32
export VERILOG_TOP_PARAMS = NLINK 2 TP 192 AR_ITER 1 ROWS 256 VM_RT 81
MK
  A=$L/asm.v; [ $side = mut ] && A=$L/asm_mut.v
  { for f in $MB; do echo "read_verilog -lib $f"; done
    for f in $GL $N/ot_hfd_coll_q2n2_body_core.sv $N/ot_hfd_coll_q2n2_vm_core.sv $Q2/ot_hfd_coll_q2_reduce_core.sv $Q2/ot_hfd_coll_q2_ring_ag_core.sv $A; do
      echo "read_verilog -defer -sv -DSYNTHESIS -DOT_COLL_ISSUER256_NATIVE32 $f"; done
    echo "hierarchy -check -top ot_hfd_coll_q2_hard_v8g_s"
    echo "proc"; echo "opt_clean"; echo "flatten -noscopeinfo"; echo "opt_clean"
    echo "memory -nomap -nordff"; echo "memory_map"; echo "opt_clean"
    echo "write_json $K/gate_pre.json"; } > $K/gate_prep.ys
  $Y -q -l $K/gate_prep.log -s $K/gate_prep.ys || exit 3
  python3 -I - $K/gate_pre.json $K/gate_ren.json <<'PY' || exit 3
import json, sys
j = json.load(open(sys.argv[1])); m = j["modules"]["ot_hfd_coll_q2_hard_v8g_s"]
MAP = [("u_ot_hfd_coll_q2n2_body_core.u_x.", ""), ("u_ot_hfd_coll_q2n2_vm_core.u_vmasm.", "u_body.u_vmasm."),
       ("u_ot_hfd_coll_q2n2_vm_core.u_writer.", "u_body.u_writer."), ("u_ot_hfd_coll_q2_reduce_core.u_reduce.", "u_body.u_reduce."),
       ("u_ot_hfd_coll_q2_ring_ag_core.u_ring.", "u_body.u_ring.")]
def ren(n):
    for a, b in MAP:
        if n.startswith(a):
            return b + n[len(a):], True
    if n.startswith("u_body."):            # assembly-level alias wires of the parent view: keep them out of the way
        return "lecasm_top." + n, False
    return n, False
for key in ("netnames", "cells"):
    old = m[key]; new = {}; nr = nd = 0
    rr = [(n, v) + ren(n) for n, v in old.items()]
    for n, v, k, r in rr:                  # names the rename leaves (top ports / parent view) first
        if not r:
            assert k not in new, (key, k); new[k] = v
    for n, v, k, r in rr:                  # piece scopes -> parent scope; a clash with a top name = wrapper port wire
        if r:
            if k in new:
                k = "lecasm_dup." + n; nd += 1
            assert k not in new, (key, k); new[k] = v; nr += 1
    m[key] = new; print(key, len(new), "renamed", nr, "clash", nd)
json.dump(j, open(sys.argv[2], "w"))
PY
  printf 'read_json %s\nwrite_verilog -noattr %s\n' $K/gate_ren.json $K/gate.v > $K/gate_write.ys
  $Y -q -l $K/gate_write.log -s $K/gate_write.ys || exit 3
  rm -f $K/gate_pre.json $K/gate_ren.json
  python3 -I $WT/tools/die_plan/lec.py $K --netlist $K/gate.v --out $L/lec_$side --gold-frontend verilog --jobs ${JOBS:-8} --mem ${MEMG:-120} > $L/lec_$side.log 2>&1
  echo "$side lec rc=$?"; python3 -c "import json;d=json.load(open('$L/lec_$side/lec.json'));print('$side', d.get('verdict'), {k:d.get(k) for k in ('reason','compare_points','proved','differ','undecided') if k in d})"
done
