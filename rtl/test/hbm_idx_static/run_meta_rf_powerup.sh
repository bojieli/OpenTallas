#!/usr/bin/env bash
set -eu
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=${1:?output directory required}
mkdir -p "$out"
for m in 0 1 2; do
  source=rtl/hdc/ot_hdc_delay_rf.sv
  if [ "$m" = 2 ]; then
    # Break invalid-state recovery without changing any data/latency path.
    python3 - "$source" "$out/wrap_mutant.sv" <<'PY'
import pathlib,sys
s=pathlib.Path(sys.argv[1]).read_text()
assert s.count('wptr >= LAST') == 1
pathlib.Path(sys.argv[2]).write_text(s.replace('wptr >= LAST','wptr == LAST'))
PY
    source="$out/wrap_mutant.sv"
  fi
  iverilog -g2012 -s tb_idx_meta_rf_powerup -Ptb_idx_meta_rf_powerup.MUT=$m -o "$out/m$m.vvp" "$source" rtl/test/hbm_idx_static/tb_idx_meta_rf_powerup.sv > "$out/build$m.log" 2>&1
  set +e
  vvp "$out/m$m.vvp" > "$out/run$m.log" 2>&1
  rc=$?
  set -e
  cat "$out/run$m.log"
  if [ "$m" = 0 ]; then [ "$rc" = 0 ]; else [ "$rc" != 0 ]; fi
done
sha256sum rtl/hdc/ot_hdc_delay_rf.sv rtl/test/hbm_idx_static/tb_idx_meta_rf_powerup.sv > "$out/sources.sha256"
echo 'IDX_META_RF_POWERUP GATE PASS'
