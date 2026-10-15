#!/usr/bin/env bash
set -euo pipefail
out=/tmp/hcoll-native-allgather-1015
vec=/tmp/hcoll-allgather-native-src-1015/results/arch/hbm_p2p_1014/native_allgather_1015/program
make -C "$out/obj" -f Vtb_hfd_coll_static_allgather_hier.mk -j4 hier_build > "$out/resume320-build.log" 2>&1
for mut in 0 1 2 3;do
 "$out/obj/Vtb_hfd_coll_static_allgather" +DIR="$vec" +MUT="$mut" > "$out/m$mut.log" 2>&1
 cat "$out/m$mut.log"
 if [[ "$mut" == 0 ]];then grep -q '^ALLGATHER_NATIVE PASS ' "$out/m$mut.log";else grep -q '^ALLGATHER_MUTANT PASS ' "$out/m$mut.log";fi
 if grep -Eq '%Fatal|%Error' "$out/m$mut.log";then exit 1;fi
done
