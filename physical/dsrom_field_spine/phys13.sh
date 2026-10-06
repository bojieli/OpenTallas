#!/bin/bash
# DS-ROM field SPINE v13 MARGIN-FIRST screens (owner rule 2026-10-06, /tmp/claude-review-20261003/OWNER_RULE_MARGIN_FIRST
# _20261006.txt): routed OVER-CONSTRAINED at 770 ps (60 / 25 ps uncertainty), signed off at 833.333 ps by
# tools/w18/corner_sta.py with --post-sdc physical/dsrom_field_spine/signoff_r<R>.sdc; pass = SS >= +60 ps, FF >= +15 ps
# (terminal.py with OT_FS_MARGIN=1).  The IO is NOT false-pathed: every port carries the die-integration budget (neighbour
# clock arrival = the block's measured insertion +/- 150 ps, 100 ps wire allowance), the same numbers in the routing SDC
# and the sign-off SDC.  Ports are registered at the screen boundary (ot_v41_pqc_spine_screen).
# Usage: phys13.sh <scratch dir> <tag>...   tag = c<PQ>r<R>_<v>[k]; v = e/f/g/h/p/q/r as phys.sh with hold targets raised
#   (FF >= +15 ps over the 25 ps hold uncertainty): e 40 ps / slew 40%, f 45 / 40, g 42 / 45, h e + routability-off GPL,
#   p / q / r: e at place density 0.55 / 0.70 / 0.62.  All with the raised repair buffer budget (IO hold buffering).
# OT_FS_PERIOD (ns, default 0.770) overrides the routing clock; OT_FS_AQ (default ot_dsrom_aq12f) names the quantiser
# module (file rtl/hdc/v41x/<name>.sv), OT_FS_KM extra SYNTH_KEEP_MODULES.
E=${1:?scratch dir}; shift
O=$E/out; J=$E/jobs; mkdir -p $O $J
export OT_ORFS_NUM_CORES=16 NUM_CORES=16 OT_FLOW_TIMEOUT_SECONDS=unlimited OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FS_MARGIN=1
PER=${OT_FS_PERIOD:-0.770}; AQ=${OT_FS_AQ:-ot_dsrom_aq12f}
COMMON="--view asap7 --clock-period-ns $PER --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --corner TT --orfs-corner WC --hold-corners WC,BC --max-transition-ns --max-fanout 32 --orfs-var ADDER_MAP_FILE= --orfs-var NUM_CORES=16 --keep-heavy-artifacts --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --stages pnr"
SP="--top ot_v41_pqc_spine_screen --source physical/dsrom_field_spine/ot_v41_pqc_spine_screen.sv --source rtl/v41die/ot_v41_spine_pqc_w17w10.sv --source rtl/hdc/ot_hdc_delay.sv --source rtl/v41rom/ot_v41_kreg.sv --source rtl/common/ot_prefix.sv --source rtl/hdc/v41x/$AQ.sv --source rtl/hdc/ot_hdc_sfu.sv --source rtl/hdc/ot_hdc_fastfp_lat_f12.sv --source rtl/hdc/ot_hdc_fp32_f12.sv --source rtl/hdc/ot_hdc_fastfp.sv --source rtl/hdc/ot_hdc_fp32_mul_lat.sv --source rtl/hdc/ot_hdc_fp32_add_lat.sv --source rtl/hdc/ot_hdc_prefix.sv"
OV=(--orfs-var "VERILOG_DEFINES=-DSYNTHESIS -DOT_PQ_ROM_PORTS")
BC=(--step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl)
run() { # tag
  t=$1; c=${t%%_*}; v=${t##*_}; pq=${c:1:1}; r=${c#*r}
  KM="ot_hdc_fp32_mul_f12_l5 ${OT_FS_KM:-}"; DENS=(); vl=${v:0:1}
  case $v in *k) KM="$KM $AQ";; esac
  case ${vl} in e) H=0.040; S=40; X=();; f) H=0.045; S=40; X=();; g) H=0.042; S=45; X=();;
             h) H=0.040; S=40; X=(--orfs-var GPL_ROUTABILITY_DRIVEN=0);;
             p) H=0.040; S=40; X=(); DENS=(--place-density 0.55);;
             q) H=0.040; S=40; X=(); DENS=(--place-density 0.70);;
             r) H=0.040; S=40; X=(); DENS=(--place-density 0.62);;
             *) echo "phys13.sh: unknown variant '$v' (tag $t)" >&2; exit 2;; esac
  # IO budget (ns; rst_n false-pathed, the die reset is its own synchronised tree): measured insertion 0.65 (R16) / 0.85 (R128), +/- 150 ps neighbour arrival, 100 ps wire allowance
  if [ "$r" = 128 ]; then g=56; SH=(--die-area 0 0 480 480 --core-area 2.16 2.16 477.84 477.84); I=0.85
  else g=44; SH=(--core-utilization 35); I=0.65; fi
  IO=(--false-path-from rst_n --core-input-delay-min-ns $(python3 -c "print(round($I-0.15,3))") --core-input-delay-max-ns $(python3 -c "print(round($I+0.25,3))")
      --output-delay-min-ns $(python3 -c "print(round(-$I-0.15,3))") --output-delay-max-ns $(python3 -c "print(round(0.25-$I,3))"))
  mkdir -p $O/tmp_$t; export TMPDIR=$O/tmp_$t
  echo "$(date -Is) START $t $(hostname) period=$PER aq=$AQ" >> $J/MANIFEST
  /srv/opentallas-scratch/admit.sh $g -- python3 tools/run_abi3_physical.py $COMMON $SP "${OV[@]}" "${IO[@]}" --orfs-var "SYNTH_KEEP_MODULES=$KM" "${BC[@]}" "${X[@]}" "${DENS[@]}" --slew-margin-percent $S --hold-margin-ns $H --param PQ=$pq --param R=$r "${SH[@]}" --nickname-tag dsfs13_$t --keep-workdir $O/work_$t --output $O/$t.json --force > $J/$t.log 2>&1
  echo $? > $J/$t.exit
  python3 tools/w18/corner_sta.py --orfs-dir $O/work_$t/orfs --post-sdc physical/dsrom_field_spine/signoff_r$r.sdc --output $O/${t}_corner_sta.json > $J/${t}_sta.log 2>&1
  python3 physical/dsrom_field_spine/terminal.py $O $t > $J/${t}_terminal.log 2>&1
  echo "$(date -Is) END $t exit=$(cat $J/$t.exit) $(tail -1 $J/${t}_terminal.log)" >> $J/MANIFEST
}
for t in "$@"; do run $t & done
wait
