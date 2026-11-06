#!/bin/bash
set -eu
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /work
python3 - <<'INNER'
import glob
from pathlib import Path
ls=sorted(p for p in glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*') if 'FAKE' not in p)
la=' '.join('-liberty '+p for p in ls)
s='read_verilog -sv sram_bb.sv new.sv ot_hbm_accel_cdc_fifo.sv ot_reset_sync.sv area_top.sv\nhierarchy -top area_top\nsynth -top area_top -flatten -noabc\ndfflibmap -liberty '+next(p for p in ls if '_SEQ_' in p)+'\nabc -script /OpenROAD-flow-scripts/flow/scripts/abc_speed.script '+la+' -dont_use *x1p*_ASAP7* -dont_use *xp*_ASAP7* -dont_use SDF* -dont_use ICG* -D 833\nstat '+la+'\nwrite_json area.json\n'
Path('area.ys').write_text(s)
INNER
yosys -s area.ys > area.log 2>&1
tail -24 area.log
