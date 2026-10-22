#!/bin/bash
set -eu
R=$PWD
O=$R/out_compat
mkdir -p "$O"
if [ ! -e "$O/obj_a" ]; then ln -s ../out/obj_a "$O/obj_a"; fi
sha256sum out/obj_a/Vtb_s81hd_tilecut runtime/ld-linux-x86-64.so.2 runtime/*.so.* > compat_identity.sha256
export HEAD_BINARY_RUNNER=$R/runtime/run.sh
J=16 /usr/bin/time -v -o compat.time bash tools/run_head_cut_runtime.sh "$R/src" "$R/bind" "$R/img" "$R/tiles.txt" "$R/ctx1048576_head.npz" "$O" a a_mut
