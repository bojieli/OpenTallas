#!/bin/bash
# m4 (2026-10-06 20:00): IO at the MEASURED glue_m3 insertion (SS 218-244 mid 231, FF 120-134 mid 127): in max 481 / min 77, out max 19 / min -177 (m3: SS +53.3, FF -1.4 at the assumed 175 ps FF insertion).
# m3 (2026-10-06 18:20): m2 reached GRT with NO setup violations but died GRT-0232 (overflow 58) after 10,731 hold buffers repaired to +40 ps (flow hold margin 40, accept is FF>=+15): m3 hold margin 20, util 30. m2 (2026-10-06 14:20): glue_m1 died in GRT (overflow 25,302 after 17,755 hold buffers): its IO min delays assumed 150 ps insertion,
# measured is WC 281-291 / BC 171-183 ps, so every input bit carried ~260 ps of WC hold. m2 uses the owner hold model (FF insertion,
# 50 ps hold IO uncertainty: in min = 175-50 = 125, out min = -(175+50) = -225), hold repaired at the FF/BC sign-off corner only, util 35.
# Head-bundle glue MARGIN route (owner margin-first rule 2026-10-06): MARGIN=1 (registered faces, split argmax,
# result group +3), MIN_DEPTH=2 retained min-delay cells; routed at 770 ps with the die IO budget (same numbers as
# signoff_833_m4.sdc), signed off at 833.333 ps by tools/w18/corner_sta.py --post-sdc. Accept SS >= +40 / FF >= +15, DRC 0.
# Usage: route.sh <source root (clean checkout)> <out dir>
set -o pipefail
S=${1:?src}; O=${2:?out}; mkdir -p $O
cd $S
export OT_ORFS_NUM_CORES=16 NUM_CORES=16 OPENTALLAS_ORFS_IMAGE=${OPENTALLAS_ORFS_IMAGE:-sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29}
H=physical/s81_die_views/hbglue/margin
I=0.15
args=(--view asap7 --top ot_dsrom_head_bundle_glue
  --source rtl/s81/ot_dsrom_head_bundle_glue.sv --source rtl/s81/ot_s81_head_min_delay.sv --source rtl/hdc/ot_hdc_delay.sv
  --param USE_MIN_DELAY_CELLS=1 --param MARGIN=1 --param MIN_DEPTH=2
  --clock-period-ns 0.770 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025
  --orfs-corner WC --hold-corners BC --stages pnr
  --false-path-from rst_n --core-input-delay-min-ns 0.077 --core-input-delay-max-ns 0.481
  --output-delay-min-ns -0.177 --output-delay-max-ns 0.019
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited
  --core-utilization 30 --place-density .55 --routing-layers M2 M6 --orfs-var ADDER_MAP_FILE=
  --max-transition-ns .25 --slew-margin-percent 20 --hold-margin-ns 0.020 --orfs-var NUM_CORES=16 --orfs-var PLACE_DENSITY_LB_ADDON=
  --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl
  --keep-workdir $O/work --output $O/physical.json --nickname-tag hbglue_m4 --keep-heavy-artifacts)
for hook in POST_PDN POST_CTS POST_GLOBAL_ROUTE; do args+=(--step-tcl $hook=$H/keep.tcl); done
echo "$(date -Is) START $(hostname)" >> $O/MANIFEST
python3 tools/run_abi3_physical.py "${args[@]}" > $O/route.log 2>&1; echo $? > $O/route.exit
python3 tools/w18/corner_sta.py --orfs-dir $O/work/orfs --post-sdc $H/signoff_833_m4.sdc --output $O/corner_sta.json > $O/sta.log 2>&1
echo $? > $O/sta.exit
echo "$(date -Is) END route=$(cat $O/route.exit) sta=$(cat $O/sta.exit)" >> $O/MANIFEST
touch $O/DONE
