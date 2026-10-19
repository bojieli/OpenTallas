#!/bin/bash
# GEN16 item 6 (10-19): PHYSICAL die clock of a Qwen compute die chain run BEFORE GRT, on the chain's own PDN floorplan
# (landed-regions standard: regional entries at the sink medians fed by ONE buffered DME spine, item 1; one buffer per
# trunk, item 5).  usage: chain_dieclk.sh RUN SRC   (RUN = <tag>/chain with case_r22k/floorplan_pdn.odb + libs/)
# Writes RUN/dieclk (prep, spec_spine.json, spine/{tt/clock.odb,tt/manifest.json,tt/arrivals_tt.tsv,ff/arrivals_ff.tsv,
# die_clock_check.txt,spine_neighbour.json,landed_pairs.json}) and RUN/dieclk/dieclk_lat_{tt,ff}.tcl for the STA.
# Exit != 0 = no complete physical die clock (the chain stops: DIE CLOCK PHYS FAIL).
set -u
R=$1; S=$2; C=$R/case_r22k; D=$R/dieclk; V=${OT_DIE_CLOCK_VARIANT:-spine}
mkdir -p $D/tools/hbm_die_v15; chmod a+rwx $D
cp -r $S/tools/die_clock $S/tools/die_clock_check.py $S/tools/die_clock_geom_dump.py $D/tools/
cp $S/tools/hbm_die_v15/die_clock_tree.py $D/tools/hbm_die_v15/
[ -s $C/floorplan_pdn.odb ] || { echo "no $C/floorplan_pdn.odb"; exit 1; }
DC_FLOORPLAN=floorplan_pdn.odb bash $D/tools/die_clock/qwen_compute_dieclk.sh prep $D $C $R/libs || exit 1
grep -q 'QCLK_CLKRX .* missing 0 ' $D/clkrx_ports.log || { echo "clk_rx LEF lacks die.v pll ports (GEN bug, STA-0201): $(grep -h QCLK_CLKRX $D/clkrx_ports.log | head -1 | cut -c1-300)"; exit 1; }
bash $D/tools/die_clock/qwen_compute_dieclk.sh spine $D $V || exit 1
[ -s $D/$V/tt/clock.odb ] && [ -s $D/$V/tt/manifest.json ] || { echo "no clock.odb / manifest"; exit 1; }
AF=$(ls $D/$V/ff/arrivals_ff.tsv 2>/dev/null) || { echo "no FF arrivals"; exit 1; }
python3 $D/tools/die_clock/dieclk_sta_lat.py --clocks $R/libs/clocks_tt.tcl --arrivals $D/$V/tt/arrivals_tt.tsv --col late \
  --out $D/dieclk_lat_tt.tcl | tee -a $D/STATUS.log || exit 1
python3 $D/tools/die_clock/dieclk_sta_lat.py --clocks $R/libs/clocks_ff.tcl --arrivals $AF --col early \
  --out $D/dieclk_lat_ff.tcl | tee -a $D/STATUS.log || exit 1
exit 0
