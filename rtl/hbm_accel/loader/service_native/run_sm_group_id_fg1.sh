#!/usr/bin/env bash
# ELEM-GAPS/HBMB 2026-10-18: ot_hbm_svc_sm_group_id at the d4g die binding #(.LBANKS(4),.FIXED_GO(1)) -- one stack's
# eight groups + 32 controller leaves + DRAM fixture, hardware-issued, go on compiler slots (tb_hbm_svc_sm_group_id_fg1).
#   run_sm_group_id_fg1.sh <out> [stack] [rows] [epochs]
# PASS = strap positive passes (data, counts, go slot every GOGAP edges, 8 groups cycle-aligned) AND its report equals
# the parameterised ot_hbm_svc_sm_group #(FIXED_GO=1) line for line; every mutant FAILS with its own message:
#   msm1/msm4 (id_sm xor 1/4) and mst (id_stack xor 1) -> 'SM_STACK (actualPC mapping|DUT fault|timeout|counts)';
#   skew (group 3 go slot +1) -> 'SM_STACK go skew';  earlygo (go slot 20, blocks not resident) -> 'SM_STACK DUT fault'.
# GOGAP: the first of 100 160 240 320 at which the parameterised master passes (compiler slot spacing), recorded.
set -euo pipefail
ulimit -c 0
root=$(cd "$(dirname "$0")/../../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?out}"); stack=${2:-0}; rows=${3:-64}; epochs=${4:-8}
mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
# images: IMAGES=<dir> (made by tools/hbm_die_v15/idx_key_images_2210.py --stack S --rows R) or generated here
images=${IMAGES:-}
if [ -z "$images" ]; then python3 tools/hbm_die_v15/idx_key_images_2210.py --stack "$stack" --rows "$rows" --out "$out/images" > "$out/images.json"; images=$out/images; fi
images=$(realpath "$images"); (cd "$images" && sha256sum sm*/records.hex sm*/backing.hex) > "$out/images.sha256"
d=rtl/hbm_accel/loader/service_native
common=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_rst_relay.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_sm8_landing_bank.sv" "$d/ot_hbm_svc_static_sm_packed136.sv" "$d/ot_hbm_svc_sm_issuer.sv" rtl/hbm_accel/sm/static/ot_smh_static_feed.sv rtl/hbm_accel/sm/static/ot_smh_calendar_static.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv "$d/ot_hbm_svc_pc_ctrl_leaf.sv" "$d/ot_hbm_svc_pc_ctrl_leaf_cfg.sv" rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap.sv "$d/ot_hbm_svc_native_sector_pipeline_leaves.sv" "$d/tb_hbm_svc_command_dram_pipeline_fixture.sv")
par=("$d/ot_hbm_svc_prefetch_mapped4_owner.sv" "$d/ot_hbm_svc_prefetch_overlap_owner.sv" "$d/ot_hbm_svc_sm4pc_cdc.sv" "$d/ot_hbm_svc_sm_feed_programmed.sv" "$d/ot_hbm_svc_sm_group.sv")
gid=("$d/ot_hbm_svc_fault_cdc_rs.sv" "$d/ot_hbm_svc_prefetch_overlap_owner_id.sv" "$d/ot_hbm_svc_sm4pc_cdc_id.sv" "$d/ot_hbm_svc_sm_feed_programmed_id.sv" "$d/ot_hbm_svc_sm_group_id.sv")
tb=$d/tb_hbm_svc_sm_group_id_fg1.sv
sha256sum "${common[@]}" "${par[@]}" "${gid[@]}" "$tb" "$0" > "$out/sources.sha256"
build(){ local n=$1 kind=$2; shift 2; local s=("${common[@]}" "${gid[@]}" "$tb"); [ "$kind" = par ] && s=("${common[@]}" "${par[@]}" "$tb")
 "$vl" --binary --timing -j 4 -Wno-fatal "$@" --top-module tb_hbm_svc_sm_group_id_fg1 -GSTACK="$stack" -GROWS="$rows" -GEPOCHS="$epochs" \
  --Mdir "$out/$n" -o sim "${s[@]}" > "$out/$n.build.log" 2>&1 || { tail -20 "$out/$n.build.log"; echo "SVG_FG1 BUILD_FAIL $n"; exit 2; }; }
# ONLY=<msm1|msm4|mst|skew|earlygo>: one mutant alone (closure-loop expect-fail bench, GOGAP=${GOGAP:-100}); prints
# 'SVG_FG1_MUT <m> FAIL: <message>' and exits 1 when the mutant is rejected with its own message, else exits 0.
if [ -n "${ONLY:-}" ]; then
 g=${GOGAP:-100}; extra=(); re='SM_STACK (actualPC mapping|DUT fault|timeout|counts)'
 case "$ONLY" in msm1) def=-DOT_SVG_ID_MUT_SM=1;; msm4) def=-DOT_SVG_ID_MUT_SM=4;; mst) def=-DOT_SVG_ID_MUT_STACK=1;;
  skew) def=-DOT_SVG_FG_MUT_SKEW=1; re='SM_STACK go skew';; earlygo) def=; extra=(+EARLYGO); re='SM_STACK DUT fault';;
  *) echo "SVG_FG1 unknown ONLY=$ONLY"; exit 2;; esac
 build obj_$ONLY id $def
 "$out/obj_$ONLY/sim" +IMAGES="$images" +GOGAP=$g "${extra[@]}" > "$out/mut_$ONLY.log" 2>&1 || true
 rm -rf "$out/obj_$ONLY"/*.o "$out/obj_$ONLY"/*.cpp
 if grep -q '^SM_GROUPS_ISSUED PASS' "$out/mut_$ONLY.log"; then echo "SVG_FG1_MUT $ONLY PASS (survived)"; exit 0; fi
 if grep -Eq "$re" "$out/mut_$ONLY.log"; then echo "SVG_FG1_MUT $ONLY FAIL: $(grep -Eo -m1 "$re[^\"]*" "$out/mut_$ONLY.log")"; exit 1; fi
 echo "SVG_FG1_MUT $ONLY NO_WITNESS"; tail -3 "$out/mut_$ONLY.log"; exit 0
fi
build obj_par par -DOT_SVG_PAR &
build obj_id id &
build obj_msm1 id -DOT_SVG_ID_MUT_SM=1 &
build obj_msm4 id -DOT_SVG_ID_MUT_SM=4 &
build obj_mst id -DOT_SVG_ID_MUT_STACK=1 &
build obj_skew id -DOT_SVG_FG_MUT_SKEW=1 &
wait
for b in par id msm1 msm4 mst skew; do [ -x "$out/obj_$b/sim" ] || { echo "SVG_FG1 BUILD_FAIL $b"; exit 2; }; done
fail=0; gap=
for g in 100 160 240 320; do
 "$out/obj_par/sim" +IMAGES="$images" +GOGAP=$g > "$out/par_g$g.log" 2>&1 || true
 if grep -q '^SM_GROUPS_ISSUED PASS' "$out/par_g$g.log"; then gap=$g; break; fi
 echo "SVG_FG1 gogap=$g parameterised: $(grep -m1 -o 'SM_STACK[^"]*' "$out/par_g$g.log" || tail -1 "$out/par_g$g.log")"
done
[ -n "$gap" ] || { echo "SVG_FG1_GATE FAIL no go slot spacing passes"; exit 1; }
echo "SVG_FG1 GOGAP=$gap"
cp "$out/par_g$gap.log" "$out/par.log"
"$out/obj_id/sim" +IMAGES="$images" +GOGAP=$gap > "$out/id.log" 2>&1 || true
grep -q '^SM_GROUPS_ISSUED PASS' "$out/id.log" || { echo "SVG_FG1 strap positive FAILED"; tail -3 "$out/id.log"; fail=1; }
grep '^SM_GROUPS_ISSUED' "$out/par.log" > "$out/par.report"; grep '^SM_GROUPS_ISSUED' "$out/id.log" > "$out/id.report" || true
if cmp -s "$out/par.report" "$out/id.report"; then echo "SVG_FG1 REPORT_IDENTICAL lines=$(wc -l < "$out/id.report")"; else echo "SVG_FG1 REPORT_DIFFERS"; diff "$out/par.report" "$out/id.report" | head; fail=1; fi
head -1 "$out/id.report" || true
mut(){ local m=$1 re=$2; shift 2
 if "$out/obj_$m/sim" +IMAGES="$images" +GOGAP=$gap "$@" > "$out/mut_$m.log" 2>&1 && grep -q '^SM_GROUPS_ISSUED PASS' "$out/mut_$m.log"; then echo "SVG_FG1 MUTANT_SURVIVED $m"; fail=1
 elif grep -Eq "$re" "$out/mut_$m.log"; then echo "SVG_FG1 MUTANT_REJECTED $m: $(grep -Eo -m1 "$re[^\"]*" "$out/mut_$m.log")"
 else echo "SVG_FG1 MUTANT_NO_WITNESS $m"; tail -3 "$out/mut_$m.log"; fail=1; fi; }
mut msm1 'SM_STACK (actualPC mapping|DUT fault|timeout|counts)'
mut msm4 'SM_STACK (actualPC mapping|DUT fault|timeout|counts)'
mut mst 'SM_STACK (actualPC mapping|DUT fault|timeout|counts)'
mut skew 'SM_STACK go skew'
mkdir -p "$out/obj_earlygo"; ln -sf "$out/obj_id/sim" "$out/obj_earlygo/sim"
mut earlygo 'SM_STACK DUT fault' +EARLYGO
rm -rf "$out"/obj_*/*.o "$out"/obj_*/*.cpp
[ $fail = 0 ] && echo "SVG_FG1_GATE PASS stack=$stack gogap=$gap" || { echo "SVG_FG1_GATE FAIL stack=$stack"; exit 1; }
