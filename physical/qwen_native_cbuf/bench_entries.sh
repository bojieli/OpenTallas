#!/usr/bin/env bash
set -eu
OUT=$1; CASE=$2; T=tb_qfd_su_crom5_entries_candidate; mkdir -p "$OUT"
PARAM="-GSW=64 -GVL=7 -GCRX=4 -GLT=1 -GLMIN=15 -GRD=2 -GLOFF=1 -GOPS=120 -GALIGN_ENTRIES=1 -GRED_ENTRIES=1"
case "$CASE" in
 exact) ;;
 payload_mut)PARAM="$PARAM -GCBUF_MUT=1";;
 group_mut)PARAM="$PARAM -GGROUP_MUT=1";;
 reset_mut)PARAM="$PARAM -GRESET_MUT=1 -GEPOCH_RESET=1";;
 old_identity_mut)PARAM="$PARAM -GSTAGE_MUT=2";;
 reset_exact)PARAM="$PARAM -GEPOCH_RESET=1";;
 stage_mut)PARAM="$PARAM -GSTAGE_MUT=1";;
 latency_mut)PARAM="$PARAM -GCRX=2";;
 *)exit 2;;
esac
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator};[ -x "$V" ]||V=verilator
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT -j 8 --top-module "$T" $PARAM --Mdir "$OUT/obj" $(cat physical/qwen_native_cbuf/entries_sources.txt) > "$OUT/build.log" 2>&1
 gzip -dc physical/qwen_native_cbuf/images/layer0/crom.hex.gz > "$OUT/crom.hex"
 "$OUT/obj/V$T" +CROM="$OUT/crom.hex" > "$OUT/run.log" 2>&1
 grep -E '^(CBUF_|SU_LAT|SU_COMPONENT|PASS|FAIL)' "$OUT/run.log"
 grep -q '^PASS qfd_su_vm_bv ' "$OUT/run.log"
