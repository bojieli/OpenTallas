#!/bin/bash
# Invoke ONLY through measured remote admission guard, never local fallback.
set -eu
SRC=${SRC:?}; OUT=${OUT:?}; mkdir -p "$OUT"
cd "$SRC"
python3 - "$OUT" <<'PY'
from pathlib import Path
import sys
out=Path(sys.argv[1])
p=Path('rtl/dsrom_sys/s81_ingest/ot_s81_native_pc_mux_plain.sv').read_text()
assert p.count('next_owner=chosen[1:0]')==1
(out/'wrong_source.sv').write_text(p.replace('next_owner=chosen[1:0]','next_owner=0'))
p=Path('rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence_plain.sv').read_text()
assert p.count('(!is_done||landed>=head[31:0])')==1
(out/'early_fence.sv').write_text(p.replace('(!is_done||landed>=head[31:0])',"1'b1"))
PY
for kind in pc fence; do
 if [[ $kind == pc ]]; then
  TOP=tb_s81_native_pc_mux; DUT=rtl/dsrom_sys/s81_ingest/ot_s81_native_pc_mux_plain.sv
  TB=rtl/test/s81_native_ingest/tb_s81_native_pc_mux_plain.sv; MUT=$OUT/wrong_source.sv
 else
  TOP=tb_s81_ingest_visibility; DUT=rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence_plain.sv
  TB=rtl/test/s81_native_ingest/tb_s81_ingest_visibility_plain.sv; MUT=$OUT/early_fence.sv
 fi
 iverilog -g2012 -s "$TOP" -o "$OUT/${kind}_base" "$DUT" "$TB" >"$OUT/${kind}_base.build.log" 2>&1
 vvp "$OUT/${kind}_base" >"$OUT/${kind}_base.log" 2>&1
 iverilog -g2012 -s "$TOP" -o "$OUT/${kind}_mut" "$MUT" "$TB" >"$OUT/${kind}_mut.build.log" 2>&1
 set +e
 vvp "$OUT/${kind}_mut" >"$OUT/${kind}_mut.log" 2>&1
 rc=$?
 set -e
 echo "$rc" >"$OUT/${kind}_mut.rc"
 if [[ $rc == 0 ]]; then echo "MUTANT ESCAPED $kind"; exit 1;fi
 done
 echo 'NATIVE_PLAIN_COMPONENTS PASS baseline and source/fence mutants detected'
