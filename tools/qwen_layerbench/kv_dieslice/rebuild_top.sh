#!/bin/bash
# KV-TOK 10-24: re-verilate and relink ONLY the bench top of an existing hierarchical kv_dieslice build (bench-side edits:
# tb_kvslice.sv, the PHY models, kvs_compute_end.sv).  The partition blocks do not change, but Verilator's hier makefile makes
# every block depend on every input file (the bench included), so a plain re-run re-verilates all 79 blocks (~30 min).
#   rebuild_top.sh BUILDDIR
# 1. the top's argument file gets the current bench file list (from the saved original + build.sh's extra bench files);
# 2. the block outputs are marked up to date (touch: wrappers / makefiles, then archives);
# 3. hier_launch_verilator on the top argument file, then make of the top only.
set -u
H=$(cd "$(dirname "$0")" && pwd); R=$(cd $H/../../.. && pwd)
O=$(readlink -f $1); A=$O/obj/Vtb_kvslice__hierMkArgs.f
IMGD=${D2D_IMG:-$R/physical/die_plan/qwen_kvsys/boot_v36/image_kv41}
[ -f $A.orig ] || cp $A $A.orig
python3 - $A.orig $A $H $R $IMGD <<'EOF'
import sys
src, dst, H, R, IMGD = sys.argv[1:]
extra = [f'{H}/kvs_compute_end.sv', f'{R}/rtl/qwen_split/qfd_kvn_static_transport.sv',
         f'{R}/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv', f'{R}/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv',
         f'+incdir+{IMGD}']
out = []
for l in open(src).read().splitlines():
    if l.endswith('/kv_dieslice/tb_kvslice.sv'):
        out += [e for e in extra if e not in out]
    if l not in extra:
        out.append(l)
open(dst, 'w').write('\n'.join(out) + '\n')
EOF
# THREADS=n: the top's scheduler runs n threads (the blocks are single-threaded protect-lib calls run in parallel)
[ -n "${THREADS:-}" ] && printf -- "--threads $THREADS\n--hierarchical-threads $THREADS\n" >> $A
# a running simulation keeps its binary: move it aside instead of relinking over it
[ -f $O/obj/Vtb_kvslice ] && mv $O/obj/Vtb_kvslice $O/obj/Vtb_kvslice.prev
cd $O/obj
touch V*/V*.mk V*/kv3_*.sv; sleep 1; touch V*/lib*.a
cd $O
/usr/bin/time -v make -f obj/Vtb_kvslice_hier.mk hier_launch_verilator VM_HIER_LAUNCH_VERILATOR_ARGSFILE=obj/Vtb_kvslice__hierMkArgs.f \
  > top_verilate.log 2>&1 || { echo "TOP_VERILATE FAIL"; grep '^%Error' top_verilate.log | head; exit 2; }
/usr/bin/time -v make -C obj -f Vtb_kvslice.mk -j ${J:-64} > top_make.log 2>&1 || { echo "TOP_MAKE FAIL"; grep -E 'error|undefined' top_make.log | head; exit 2; }
echo "TOP_REBUILD OK $(grep -E 'Elapsed|Maximum res' top_verilate.log top_make.log | tr -s ' ' | tr '\n' ' ')"
