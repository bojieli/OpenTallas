#!/usr/bin/env bash
set -euo pipefail
cd /work
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 - <<'INNER'
from pathlib import Path
import glob
r=Path('/work'); files=' '.join(str(p) for p in sorted((r/'rtl').glob('*.sv')))
head='read_liberty -lib /work/macros/ot_sram_1r1w2c_64x546_m1_tt.lib\nread_liberty -lib /work/macros/ot_sram_1r1w_32x546_m1_tt.lib\nread_verilog -D SYNTHESIS -I/work/rtl -sv '+files+'\n'
for cut in [0,1]:
 (r/'map'/('elab'+str(cut)+'.ys')).write_text(head+'hierarchy -check -top ot_pdie_serdes_rx_bm3_family -chparam CUT_BM '+str(cut)+'\nstat\nwrite_rtlil /work/map/elab'+str(cut)+'.il\n')
libs=sorted(p for p in glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*') if 'FAKE' not in p);la=' '.join('-liberty '+p for p in libs);seq=next(p for p in libs if '_SEQ_' in p)
for mode,top in [('bm','ot_pdie_serdes_rx_bm_native'),('rest','ot_pdie_serdes_rx_bm3_residual')]:
 script=head+'hierarchy -check -top '+top+'\nsynth -top '+top+' -flatten -noabc\ndfflibmap -liberty '+seq+'\nabc -script /OpenROAD-flow-scripts/flow/scripts/abc_speed.script '+la+' -dont_use *x1p*_ASAP7* -dont_use *xp*_ASAP7* -dont_use SDF* -dont_use ICG* -D 833\nstat '+la+'\nwrite_json /work/map/'+mode+'.json\n'
 (r/'map'/(mode+'.ys')).write_text(script)
INNER
for mode in elab0 elab1 bm rest;do
 /usr/bin/time -v yosys -s "map/$mode.ys" > "map/$mode.log" 2>&1
 printf '0\n' > "map/$mode.exit.rc"
done
printf 'ALL_MAP_ELAB_PASS\n' > map/result.txt
