#!/usr/bin/env bash
# HANDOFF 0az parent proof: actual controller (ELASTIC) + elastic block front +
# fixed return ring under variable in-order PHY latency. Sources are copied
# from the given commit (default HEAD) so the receipt is source-pinned.
set -euo pipefail
ulimit -c 0
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh output directory};rev=${2:-HEAD};mkdir -p "$out/source";src="$out/source"
# Extract once (git host); a copied output dir with source.rev runs anywhere.
if [ ! -f "$out/source.rev" ];then
for p in rtl/qwen_sys/static_kv_20261014/{ot_qkd_static_emb_cdc,qkd_static_kv_write_observer,qkd_ctrl_pc_host_static,ot_qkd_static_ctrl_pc_emb,ot_qkd_static_kv_timing,qkd_static_kv_return_calendar,qkd_static_kv_return_slots_mc,qkd_kv_hbm_elastic_front_mc}.sv \
  rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_pcport.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv \
  rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv rtl/lib/{ot_async_fifo,ot_reset_sync}.sv \
  rtl/test/qwen_static_kv/tb_kv_hbm_elastic_boundary_mc.sv;do
 mkdir -p "$src/$(dirname "$p")"
 # a closure-loop staged snapshot is not a git tree: copy the staged file (its sha256 is recorded below)
 if git -C "$root" rev-parse --verify -q "$rev" >/dev/null 2>&1;then git -C "$root" show "$rev:$p" > "$src/$p";else cp "$root/$p" "$src/$p";fi
done
git -C "$root" rev-parse "$rev" > "$out/source.rev" 2>/dev/null || echo "staged-snapshot $root" > "$out/source.rev"
fi
[ "${PREP_ONLY:-0}" = 1 ] && exit 0
mapfile -d '' sources < <(find "$src" -name '*.sv' -print0)
# NBLK / RDEPTH (env): production front blocks and return-ring depth under test (r1 defaults 4 / 8; r2 kits 10 / 64)
TBP=(-GNBLK="${NBLK:-4}" -GRDEPTH="${RDEPTH:-8}")
b(){ local tag=$1;shift;verilator --binary --timing -Wno-fatal -j "${JOBS:-4}" --top-module tb_kv_hbm_elastic_boundary_mc "${TBP[@]}" "$@" --Mdir "$out/obj_$tag" "${sources[@]}" > "$out/build_$tag.log" 2>&1; }
if [ "${BUILD_SERIAL:-0}" = 1 ]; then
 b prod; b fm1 -GFRONT_MUT=1; b fm2 -GFRONT_MUT=2; b fm3 -GFRONT_MUT=3; b ce0 -GCTRL_ELASTIC=0
else
 b prod & b fm1 -GFRONT_MUT=1 & b fm2 -GFRONT_MUT=2 & b fm3 -GFRONT_MUT=3 & b ce0 -GCTRL_ELASTIC=0 & wait
fi
run(){ local tag=$1 name=$2;shift 2;if "$out/obj_$tag/Vtb_kv_hbm_elastic_boundary_mc" "$@" > "$out/$name.log" 2>&1;then echo 0;else echo $?;fi > "$out/$name.exit"; }
fails=0
for ph in 137 637;do for jit in 0 8 16;do for seed in 1 2 3;do
 run prod "prod_p${ph}_j${jit}_s${seed}" +phase=$ph +jit=$jit +seed=$seed +verilator+seed+$seed
 grep -q '^PASS 0az' "$out/prod_p${ph}_j${jit}_s${seed}.log" && test "$(cat "$out/prod_p${ph}_j${jit}_s${seed}.exit")" = 0 || { echo "PROD FAIL p$ph j$jit s$seed";fails=1; }
done;done;done
must_fail(){ local name=$1 pat=$2;test "$(cat "$out/$name.exit")" != 0 && grep -q "$pat" "$out/$name.log" || { echo "MUTANT ESCAPED $name";fails=1; }; }
# late block = sector 303, the LAST sector of block 37 (reads count the HOST static read first)
run prod m2_late +jit=16 +faultmode=2 +late=304;must_fail m2_late OBSERVED_HOLD
run prod m3_historical +jit=16 +faultmode=3;must_fail m3_historical OBSERVED_FAIL
run prod m5_early +jit=0 +faultmode=5 +late=1;must_fail m5_early OBSERVED_FAIL
run prod m6_silent +jit=16 +faultmode=6;must_fail m6_silent OBSERVED_FAIL
run fm1 fm1 +jit=16 +seed=2;must_fail fm1 OBSERVED_FAIL
for t in fm2 fm3;do run $t "$t" +jit=16 +faultmode=2 +late=304;must_fail "$t" OBSERVED_FAIL;done
run ce0 ce0 +jit=16 +seed=2;must_fail ce0 OBSERVED_FAIL
find "$src" -name '*.sv' -print0 | sort -z | xargs -0 sha256sum > "$out/source.sha256"
grep -h '^MEASURE' "$out"/*.log > "$out/measure.txt" || true
test $fails = 0 && echo "PASS 0az elastic boundary: 18 production runs, 8 failing cases observed (1 hold + 7 fail)"
