#!/bin/bash
# HEAD-SERDES-SECONDARY overlay. Usage: apply.sh SRC_TREE   (e.g. .../kw45/src_head_rp21z_pgcap1d724b73)
# Run on each gen host. Replaces by copy+mv (src files are hardlinked across trees). Idempotent.
set -euo pipefail
S=$1; H=$(cd "$(dirname "$0")" && pwd); T=$S/tools/die_plan
for f in secondary_clock.py secondary_clock_taps.tcl; do cp "$H/tools/die_plan/$f" "$T/$f.new.$$"; mv -f "$T/$f.new.$$" "$T/$f"; done
if ! grep -q OT_GEN_SECONDARY_CLOCK "$T/gen_phys.py"; then
  cp "$T/gen_phys.py" "$T/gen_phys.py.new.$$"; patch -s "$T/gen_phys.py.new.$$" < "$H/gen_phys_secondary.patch"
  python3 -I -m py_compile "$T/gen_phys.py.new.$$"; mv -f "$T/gen_phys.py.new.$$" "$T/gen_phys.py"
fi
grep -c OT_GEN_SECONDARY_CLOCK "$T/gen_phys.py"
