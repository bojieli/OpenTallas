#!/bin/bash
# TOK-QK-KVL 10-27: B48 native tb_kvslice rebuilt with the per-layer far end (kvs_compute_end.sv +VECL); the 75 hier libs
# are the B48 ones (symlinked, read-only), only the top is re-verilated.
set -eu
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
K=/srv/opentallas-scratch2/claude/tok-qk-kvl; S=/srv/opentallas-scratch2/claude/codex-kv-boot-2005/build/obj
mkdir -p $K/build/obj; cd $K/build/obj
for d in $(find $S -maxdepth 1 -mindepth 1 \( -type d -o -type l \) ! -name Vtb_kvslice__hier.dir); do ln -sfn $(readlink -f $d) $(basename $d); done
cp -a $S/Vtb_kvslice__hier.dir .
for f in $(find $S -maxdepth 1 -type f ! -name 'Vtb_kvslice*'); do cp -a $f .; done
cp -a $S/Vtb_kvslice_hier.mk .
sed -e 's#^/srv/opentallas-scratch2/claude/wt/codex-kv-pv-image-0733/tools/qwen_layerbench/kv_dieslice/kvs_compute_end.sv$#'$K'/kvs_compute_end.sv#'     -e 's#"--build-jobs" "12"#"--build-jobs" "48"#' $S/Vtb_kvslice__hierMkArgs.f > Vtb_kvslice__hierMkArgs.f
grep -c "$K/kvs_compute_end.sv" Vtb_kvslice__hierMkArgs.f
cd $K/build
echo TOP_FRONTEND $(date -Is)
make -f obj/Vtb_kvslice_hier.mk hier_launch_verilator VM_HIER_LAUNCH_VERILATOR_ARGSFILE=obj/Vtb_kvslice__hierMkArgs.f > top_verilate.log 2>&1 || echo FRONTEND_RC $?
echo TOP_MAKE $(date -Is)
make -C obj -f Vtb_kvslice.mk -j48 > top_make.log 2>&1
echo BUILD_DONE $(date -Is); ls -la obj/Vtb_kvslice
