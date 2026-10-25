#!/bin/bash
# TOK-QK 10-24: kv43 vehicle staged tree = staged kv42 (bound_kv42) + BO1 HOST boot-event candidate + COORD fix A
# (+ B / C1+C2 via kv43/apply_B.sh / apply_C.sh when present).  Then build with ../build.sh (fresh hierarchical build).
#   stage_kv43.sh KV42_STAGED BO1_DIR OUT [REPO]
set -eu
H=$(cd "$(dirname "$0")" && pwd); R=${4:-$(cd $H/../../../.. && pwd)}
K=$(readlink -f $1); BO=$(readlink -f $2); O=$3
[ -e $O ] && { echo "OUT $O exists (never stage into a live dir)"; exit 2; }
cp -a $K $O; O=$(readlink -f $O); RT=$O/src/bind__rtl
P0=$(head -1 $K/files.f | sed 's#/src/.*##')
for f in files.f incdirs.f hostside.f; do sed -i "s#$P0#$O#g" $O/$f; done
# BO1 (main a2757edd53 opt-in source; Codex bound candidate): HOST boot event waits for the accepted programme
cp $BO/kv3_hub_Wi_part.sv $RT/kv3_hub_Wi_part.sv
for n in qkd_host_root_admission_obsx_bo1.sv qkd_d2d_boot_event_bridge.sv; do cp $BO/$n $RT/$n; grep -qx "$RT/$n" $O/files.f || echo "$RT/$n" >> $O/files.f; done
# A: kvpc rst_n on the delivered HBM reset lane
python3 $R/physical/die_plan/qwen_kvsys/bind/kv_kvpc_hbm_reset.py $RT $O/fixA
for f in $O/fixA/kv3_pc*_part*.sv; do cp $f $RT/; done
for x in ${FIXES:-B C}; do if [ -f $H/apply_$x.sh ]; then echo "apply $x"; bash $H/apply_$x.sh $O; else echo "fix $x: apply_$x.sh not present (NOT APPLIED)"; fi; done
( cd $O && find src -type f \( -name '*.sv' -o -name '*.v' \) | sort | xargs sha256sum ) > $O/kv43_src.sha256
echo "kv43 staged $O"
