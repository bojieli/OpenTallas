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
MODELS=("$W/ot_hbm3e_phy_rc_e8p5_dram_model.sv" "$W/ot_hbm3e_phy_slices_dram_model.sv" "$W/tb_hbm_phy_slices_model.sv")
for period in 1024 833;do
 verilator --binary --timing -j 2 -Wno-fatal --top-module tb_hbm_phy_slices_model -GPHY_PERIOD_PS="$period" -Mdir "$R/obj$period" "${MODELS[@]}" > "$R/build$period.log" 2>&1
 BIN=$R/obj$period/Vtb_hbm_phy_slices_model
 "$BIN" +HBM_IMG_DIR="$R/images" +RESET_PENDING=1 > "$R/positive$period.log" 2>&1
 grep 'PHY_SLICE_MODEL PASS' "$R/positive$period.log"
done
BIN=$R/obj833/Vtb_hbm_phy_slices_model
if "$BIN" +HBM_IMG_DIR="$R/images" +MUT=1 > "$R/mut_write.log" 2>&1;then echo 'MUTANT ESCAPED';exit 2;fi
grep 'PHY_SLICE_MODEL FAIL payload' "$R/mut_write.log"
if "$BIN" +HBM_IMG_DIR="$R/missing" > "$R/mut_image.log" 2>&1;then echo 'MISSING IMAGE ESCAPED';exit 3;fi
grep 'uninitialized sector' "$R/mut_image.log"
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_hbm_phy_slices_model -GPHY_PERIOD_PS=833 -GADAPTER_READ_LATENCY=28 -Mdir "$R/obj833_early" "${MODELS[@]}" > "$R/build833_early.log" 2>&1
if "$R/obj833_early/Vtb_hbm_phy_slices_model" +HBM_IMG_DIR="$R/images" > "$R/mut_trl.log" 2>&1;then echo 'EARLY tRL ESCAPED';exit 4;fi
grep 'PHY_SLICE_MODEL FAIL valid' "$R/mut_trl.log"
echo 'HBM_PHY_SLICES_MODEL PASS 1024+833+reset+write-mutant+missing-image+tRL-mutant'
