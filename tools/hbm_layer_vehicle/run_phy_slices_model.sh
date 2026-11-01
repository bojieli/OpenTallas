#!/bin/bash
set -euo pipefail
ulimit -c 0
R=$(realpath -m "${1:?new output directory}")
W=$(cd "$(dirname "$0")/../.." && pwd)/rtl/test/hbm_layer
if [[ -e "$R" ]]; then echo "Use a new output directory to preserve verdicts" >&2; exit 2; fi
mkdir -p "$R/images" "$R/missing"
python3 - "$R" <<'PY'
from pathlib import Path
import sys
r=Path(sys.argv[1]);lines=[]
for p in range(32):
 data=('1234%04x'%p)*8
 lines.append('%08x %s\n'%(4*p,data))
(r/'images/fixture.hex').write_text(''.join(lines))
(r/'missing/fixture.hex').write_text(''.join(lines[:-1]))
PY
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
# Run this lightweight model bench through ot-run, like every simulator build.
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_hbm_phy_slices_model -Mdir "$R/obj" "$W/ot_hbm3e_phy_rc_e8p5_dram_model.sv" "$W/ot_hbm3e_phy_slices_dram_model.sv" "$W/tb_hbm_phy_slices_model.sv" > "$R/build.log" 2>&1
BIN=$R/obj/Vtb_hbm_phy_slices_model
"$BIN" +HBM_IMG_DIR="$R/images" +RESET_PENDING=1 > "$R/positive.log" 2>&1
grep 'PHY_SLICE_MODEL PASS' "$R/positive.log"
if "$BIN" +HBM_IMG_DIR="$R/images" +MUT=1 > "$R/mut_write.log" 2>&1;then echo 'MUTANT ESCAPED';exit 2;fi
grep 'PHY_SLICE_MODEL FAIL payload' "$R/mut_write.log"
if "$BIN" +HBM_IMG_DIR="$R/missing" > "$R/mut_image.log" 2>&1;then echo 'MISSING IMAGE ESCAPED';exit 3;fi
grep 'uninitialized sector' "$R/mut_image.log"
echo 'HBM_PHY_SLICES_MODEL PASS positive+write-mutant+missing-image'
