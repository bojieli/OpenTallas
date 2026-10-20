#!/bin/bash
# QW-TLOAD2 bench: private CALR table-ROM loader + VM join qfd_dv_slice_tload (CAPTURE_STAGE=1, the gated/routed config) into
# the real qfd_dv_vm.  Fixture is rebuilt here from the committed compact table manifest (sha256 c63242...) with
# programme_store.py + table_rom_native_fixture.py; slice s0 drives the 4 real ROM macro models.
# usage: run_f16_tload_capture.sh OUTDIR MODE   (run from repo root; `verilator` on PATH = closure-daemon 5.050)
#   pass  : default CAPTURE_STAGE=0 first_age5 + CAPTURE_STAGE=1 all36 x all4 edge-exact/VM readbacks + collision reject
#           -> F16_TLOAD_CAPTURE_PASS
#   mut1..mut5 : loader/join mutants (MUT=1..5) on CAPTURE_STAGE=1  -> TLOAD_* fail lines
#   cmut1|cmut2: capture-specific causal mutants (CAPTURE_MUT=1/2)    -> TLOAD_(EDGE_MISMATCH|DONE_AGE|UNEXPECTED_FAULT)
set -uo pipefail
OUT=${1:?outdir}; MODE=${2:?mode}
R=$(pwd)
mkdir -p "$OUT/fx" "$OUT/logs"
OUT=$(cd "$OUT" && pwd)
verilator --version
MAN="$OUT/fx/table_manifest.json"
zcat "$R/results/arch/qwen_programme_store_1019/table_manifest.json.gz" > "$MAN" || { echo F16_TLOAD_FIXTURE_FAIL; exit 2; }
echo "c63242abc11b880c741bd7556138529dab331b21579231b7ba9b53c7435cee92  $MAN" | sha256sum -c --quiet || { echo F16_TLOAD_MANIFEST_SHA_FAIL; exit 2; }
( cd "$R/tools/qwen_layerbench" && python3 programme_store.py --manifest "$MAN" --out "$OUT/fx/images" \
  && python3 table_rom_native_fixture.py --manifest "$MAN" --images "$OUT/fx/images" --out "$OUT/fx/fixture" ) > "$OUT/logs/fixture.log" 2>&1 \
  || { tail -20 "$OUT/logs/fixture.log"; echo F16_TLOAD_FIXTURE_FAIL; exit 2; }
FX="$OUT/fx/fixture/s0"
M="$R/physical/asap7_memory_macros"
SRCS="$M/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v $M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 $M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 $R/rtl/qwen_dv/qfd_dv_vm.sv $R/rtl/qwen_dv/qfd_dv_table_rom_loader.sv $R/rtl/qwen_dv/qfd_dv_slice_tload.sv
 $R/rtl/test/qwen_dv/tb_qfd_dv_slice_tload.sv"
sha256sum $SRCS
B="--binary --timing -j 4 -Wno-fatal --top-module tb_qfd_dv_slice_tload"
build() { verilator $B "$@" $SRCS > "$OUT/logs/build_$1_$2.log" 2>&1 || { tail -30 "$OUT/logs/build_$1_$2.log"; echo F16_TLOAD_BUILD_FAIL; exit 3; }; }
run() { "$1/Vtb_qfd_dv_slice_tload" +OT_ROM_DIR="$FX" +EXPECTED="$FX/expected.hex" "${@:2}" 2>&1; }
case $MODE in
 pass)
  ok=1
  build -GCAPTURE_STAGE=0 -GMUT=0 -Mdir "$OUT/obj_d"
  run "$OUT/obj_d" > "$OUT/logs/default.log"
  grep -q 'TLOAD_JOIN_PASS.*first_age=5' "$OUT/logs/default.log" && echo "DEFAULT0 $(grep -o 'edge_checks=.*' "$OUT/logs/default.log")" || { echo DEFAULT0_FAIL; ok=0; }
  build -GCAPTURE_STAGE=1 -GMUT=0 -Mdir "$OUT/obj_c"
  run "$OUT/obj_c" > "$OUT/logs/capture.log"
  grep -q 'TLOAD_JOIN_PASS.*first_age=6' "$OUT/logs/capture.log" && echo "CAPTURE1 $(grep -o 'edge_checks=.*' "$OUT/logs/capture.log")" || { echo CAPTURE1_FAIL; tail -5 "$OUT/logs/capture.log"; ok=0; }
  run "$OUT/obj_c" +FAULT_CASE=1 > "$OUT/logs/collision.log"
  grep -q TLOAD_COLLISION_REJECT_PASS "$OUT/logs/collision.log" && echo COLLISION_REJECT_PASS || { echo COLLISION_FAIL; ok=0; }
  [ $ok = 1 ] && { echo F16_TLOAD_CAPTURE_PASS; exit 0; } || { echo F16_TLOAD_CAPTURE_FAIL; exit 1; } ;;
 mut[1-5])
  m=${MODE#mut}; fc=0; case $m in 1|3) fc=1;; esac
  build -GCAPTURE_STAGE=1 -GMUT=$m -Mdir "$OUT/obj_m$m"
  run "$OUT/obj_m$m" +FAULT_CASE=$fc; echo "MUT$m rc=$?"; exit 1 ;;
 cmut[12])
  c=${MODE#cmut}
  build -GCAPTURE_STAGE=1 -GMUT=0 -GCAPTURE_MUT=$c -Mdir "$OUT/obj_cm$c"
  run "$OUT/obj_cm$c"; echo "CMUT$c rc=$?"; exit 1 ;;
 *) echo "bad mode $MODE"; exit 2 ;;
esac
