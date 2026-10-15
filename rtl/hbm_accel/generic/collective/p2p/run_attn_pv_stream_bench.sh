#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=${HCOLL_ROOT:-$(git -C "$HERE" rev-parse --show-toplevel)}
OUT=$(realpath -m "${1:?output directory}")
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT"
cd "$ROOT"
P=rtl/hbm_accel/generic/collective/p2p
src=("$P/ot_hgi_attn_pv_pkg.sv" "$P/ot_hgi_attn_pv_stream_pkg.sv"
 "$HERE/tb_hgi_attn_pv_stream.sv" "$P/ot_hgi_attn_pv_stream.sv"
 "$P/ot_hgi_coll_pring_static.sv" "$P/ot_hgi_coll_reduce_static.sv"
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
sha256sum "${src[@]}" "$HERE/run_attn_pv_stream_bench.sh" tools/hbm_coll_static/attention_stream.py tools/hbm_coll_static/attention_calendar.py > "$OUT/source.sha256"
if git rev-parse HEAD > "$OUT/source.rev" 2>/dev/null;then :;else printf '%s\n' "${HCOLL_SOURCE_REV:?set pinned commit for an archived source tree}" > "$OUT/source.rev";fi
"$V" --version > "$OUT/verilator.version"
for case_name in production localfirst earlypub;do
 args=();[[ "$case_name" == production ]] || args+=(--mutant "$case_name")
 python3 tools/hbm_coll_static/attention_stream.py --out "$OUT/$case_name" "${args[@]}" > "$OUT/$case_name.compiler.log" 2>&1
 python3 - "$OUT/$case_name" "$ROOT" <<'PYVERIFY'
import hashlib,json,sys
from pathlib import Path
out,root=map(Path,sys.argv[1:]);m=json.loads((out/'manifest.json').read_text())
assert m['batches']==128 and m['output_words']==1024 and m['period']==82,m
for p,want in m['files'].items():
 assert hashlib.sha256((out/p).read_bytes()).hexdigest()==want,p
for p,want in m['source_binding'].items():
 assert hashlib.sha256((root/p).read_bytes()).hexdigest()==want,p
PYVERIFY
done
build() {
 local label=$1;shift
 "$V" --binary --timing -O2 -j "${JOBS:-4}" --output-split 10000 --output-split-cfuncs 500 \
  -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ --top-module tb_hgi_attn_pv_stream \
  --Mdir "$OUT/obj_$label" "$@" "${src[@]}" > "$OUT/$label.build.log" 2>&1 || {
   tail -40 "$OUT/$label.build.log";return 2;
  }
}
build production
binary="$OUT/obj_production/Vtb_hgi_attn_pv_stream"
"$binary" "+PROGRAM_DIR=$OUT/production" > "$OUT/production.run.log" 2>&1
cat "$OUT/production.run.log"
rg -q '^PV_STREAM_PASS checked1024 batches128 resets1 first163 last10577 period82 ' "$OUT/production.run.log"
# Same native binary; only externally supplied boundary node association changes.
if "$binary" "+PROGRAM_DIR=$OUT/localfirst" > "$OUT/localfirst.run.log" 2>&1;then
 cat "$OUT/localfirst.run.log";echo 'semantic localfirst mutant survived';exit 1
fi
cat "$OUT/localfirst.run.log"
rg -q 'PV_STREAM_DATA_MISMATCH faults_zero=1' "$OUT/localfirst.run.log"
"$binary" "+PROGRAM_DIR=$OUT/earlypub" +EXPECT_SCHEDULE_FAULT=1 > "$OUT/earlypub.run.log" 2>&1
cat "$OUT/earlypub.run.log"
rg -q '^PV_STREAM_EXPECTED_SCHEDULE_FAULT ' "$OUT/earlypub.run.log"
for mutation in carry bank;do
 args=();if [[ "$mutation" == carry ]];then args+=(-GMUT_CARRY=1);else args+=(-GMUT_BANK=1);fi
 build "$mutation" "${args[@]}"
 if "$OUT/obj_$mutation/Vtb_hgi_attn_pv_stream" "+PROGRAM_DIR=$OUT/production" > "$OUT/$mutation.run.log" 2>&1;then
  cat "$OUT/$mutation.run.log";echo "hardware $mutation mutant survived";exit 1
 fi
 cat "$OUT/$mutation.run.log"
 rg -q 'PV_STREAM_(DATA_MISMATCH|NATIVE_FAULT|VALID_MISMATCH|IDENTITY_MISMATCH)' "$OUT/$mutation.run.log"
done
printf '%s\n' 'PV_STREAM_SUITE_PASS production1024 semantic_localfirst_no_fault earlypub_fault MUT_CARRY MUT_BANK' | tee "$OUT/SUMMARY"
