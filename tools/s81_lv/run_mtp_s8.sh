#!/bin/bash
# run_mtp_s8.sh <src root> <out dir> <die-layer stim dir> <ds_head export dir> : S81 layer vehicle seam S8 (s81lv).
# Builds tb_s81lv_mtp_s8 (real hrow_src x3 + hrow_tc + cap/coll/vm MTP endpoints + dsfd_mtp_seq_rtt) for base and
# the two seam mutants, stimulus tools/s81_lv/mtp_stim.py (640 golden H_STORE rows of the 1M token + the exporter's
# head RESULT).  Verdict: MTP_S8_GATE PASS iff base prints S8_RESULT PASS and both mutants S8_RESULT FAIL.
# Env: VL (verilator 5.050), J (16), ADMIT ("" or "/srv/opentallas-scratch/admit.sh <GB> --").  Fleet hosts only.
set -u
SRC=$1; OUT=$2; STIM=$3; HEAD=$4
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; J=${J:-16}; ADMIT=${ADMIT:-}
M=$SRC/rtl/dsrom_sys/mtp
mkdir -p $OUT/vec
python3 $SRC/tools/s81_lv/mtp_stim.py --stim $STIM --head $HEAD --out $OUT/vec > $OUT/stim.log 2>&1 || { echo "MTP_S8_GATE FAIL stim"; exit 1; }
FILES="$M/dsfd_mtp_partner_ep.sv $M/dsfd_coll_mtp_ep.sv $M/dsfd_mtp_seq_rtt.sv $M/ot_dsrom_mtp_seq.sv $M/ot_dsrom_mtp_hrow.sv
 $M/ot_dsrom_mtp_hrow_bank.sv $M/ot_dsrom_mtp_hrow_tiles.sv $M/ot_dsrom_mtp_link_rtt.sv $M/ot_dsrom_mtp_link_pair.sv
 $M/ot_dsrom_mtp_skid.sv $M/rtt/ot_dsrom_mtp_rstsync.sv $SRC/rtl/dsrom_sys/s81_lv/mtp/ot_s81lv_mtp_s8.sv
 $SRC/rtl/dsrom_sys/s81_lv/mtp/tb_s81lv_mtp_s8.sv"
sha256sum $FILES $SRC/tools/s81_lv/mtp_stim.py > $OUT/sources.sha256
for m in base mut_drop mut_early; do
  case $m in base) X="";; mut_drop) X="+define+OT_S81LV_MTP_MUT_DROP";; mut_early) X="+define+OT_S81LV_MTP_MUT_EARLY";; esac
  ( $ADMIT $VL --binary --timing -j $J -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT \
      -Wno-TIMESCALEMOD -Wno-PINMISSING --top-module tb_s81lv_mtp_s8 $X --Mdir $OUT/obj_$m -o sim $FILES \
      > $OUT/build_$m.log 2>&1 && cd $OUT/vec && $OUT/obj_$m/sim > $OUT/run_$m.log 2>&1 ) &
done
wait
for m in base mut_drop mut_early; do
  exp=FAIL; [ $m = base ] && exp=PASS
  v=$(grep -h "S8_RESULT" $OUT/run_$m.log 2>/dev/null | tail -1); [ -z "$v" ] && v="NO_RESULT $(grep -m1 '%Error' $OUT/build_$m.log)"
  echo "$m expect $exp: $v | $(grep -h '^S8 ' $OUT/run_$m.log 2>/dev/null | tail -1 | cut -c1-400)"
done | tee $OUT/verdicts.log
if grep -q "base expect PASS: S8_RESULT PASS" $OUT/verdicts.log && [ $(grep -c "expect FAIL: S8_RESULT FAIL" $OUT/verdicts.log) -eq 2 ]; then
  echo "MTP_S8_GATE PASS" | tee -a $OUT/verdicts.log
else echo "MTP_S8_GATE FAIL" | tee -a $OUT/verdicts.log; exit 1; fi
