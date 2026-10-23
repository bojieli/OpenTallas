#!/bin/bash
# QDIE5-TLD: the golden per-slice table images (the "right slice constants") for tb_qdie5_tld_chain, rebuilt from the
# committed QW-TLOAD2 fixture inputs (closure record qfd_dv_slice_tload_ns4-ns4-b8e6c6f86 bench_f16_tload_capture):
# compact table manifest (sha256 c63242ab...) + programme_store.py + table_rom_native_fixture.py at b8e6c6f86.
# usage (repository with b8e6c6f86 available): mk_fixture.sh OUTDIR   -> OUTDIR/images/table_s<k>_m<l>.viamap.hex,
#   OUTDIR/fixture/s<k>/expected.hex (k = 0..11)
set -euo pipefail
OUT=$(mkdir -p "$1" && cd "$1" && pwd); R=${REPO:-$(git rev-parse --show-toplevel)}; C=b8e6c6f86
T=$OUT/tools; mkdir -p "$T"
git -C "$R" show $C:results/arch/qwen_programme_store_1019/table_manifest.json.gz | zcat > "$OUT/table_manifest.json"
echo "c63242abc11b880c741bd7556138529dab331b21579231b7ba9b53c7435cee92  $OUT/table_manifest.json" | sha256sum -c --quiet
git -C "$R" show $C:tools/qwen_layerbench/programme_store.py > "$T/programme_store.py"
git -C "$R" show $C:tools/qwen_layerbench/table_rom_native_fixture.py > "$T/table_rom_native_fixture.py"
( cd "$T" && python3 -I programme_store.py --manifest "$OUT/table_manifest.json" --out "$OUT/images" \
  && python3 table_rom_native_fixture.py --manifest "$OUT/table_manifest.json" --images "$OUT/images" --out "$OUT/fixture" )
ls "$OUT/fixture" | wc -l; sha256sum "$OUT"/fixture/s*/expected.hex | cut -c1-16
