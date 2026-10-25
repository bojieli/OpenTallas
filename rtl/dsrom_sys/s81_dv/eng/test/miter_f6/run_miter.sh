#!/bin/bash
# PATH-S81/ENG3 miter runner (from ENG2 miter_ohsel) (run from anywhere inside the worktree):
#   $1 = unit|core|xq, $2 = pass|mut, $3 = seeds ("1 2 3"), $4 = cycles
# REF = ot_s81eng_rr_n32.sv + dsdv_eng_rr_split.sv at REF_SHA (default d2d23d2ebb, the unchanged source), modules renamed
# *_ref; NEW = the same files at HEAD of this worktree (built with -DOT_S81ENG_XQ_OHSEL -DOT_S81ENG_BF_PREDEC; ref = neither); every other source is shared,
# read from REF_SHA (unchanged by this fix).  Exit 0 only if every seed PASSes (pass) or every seed has mismatches (mut).
set -uo pipefail
T=$1; M=$2; SEEDS=$3; CYC=$4
REF_SHA=${REF_SHA:-88ec67b9f3}
B=$(cd "$(dirname "$0")" && pwd); S=$B/../miter_ohsel; G=$(git -C "$B" rev-parse --show-toplevel)
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
W=${MITER_WORK:-/tmp/eng3_miter_$$}/build_${T}_${M}; rm -rf "$W"; mkdir -p "$W/ref" "$W/new" "$W/sh"
E=rtl/dsrom_sys/s81_dv/eng
CHG="$E/ot_s81eng_rr_n32.sv $E/dsdv_eng_rr_split.sv rtl/dsrom_sys/engram/static_lookup_1015/dsfd_engram_lkp_ra640_hx.sv"
SHARED=$(sed -n 's/^SRC //p' "$S/sources.txt")
for p in $SHARED; do case " $CHG " in *" $p "*) continue;; esac; if [ "$(basename "$p")" = ot_s81eng_reset3n32.sv ]; then cp "$G/$p" "$W/sh/$(basename $p)"; else git -C "$G" show "$REF_SHA:$p" > "$W/sh/$(basename $p)" || exit 3; fi; done
for p in $CHG; do git -C "$G" show "$REF_SHA:$p" > "$W/ref/$(basename $p)"; cp "$G/$p" "$W/new/$(basename $p)"; done
mods=$(grep -h -o -E '^\s*(\(\*[^*]*\*\)\s*)?module\s+[A-Za-z0-9_]+' "$W"/ref/*.sv | sed -E 's/.*module\s+//' | sort -u | paste -sd'|')
perl -pi -e "s/\\b($mods)\\b/\$1_ref/g" "$W"/ref/*.sv
DEFS="+define+SYNTHESIS +define+OT_ENGRAM_CRCMAT +define+OT_S81ENG_RR_N32 +define+OT_S81ENG_RR_MUL_N32 +define+OT_S81ENG_TMAP_CPRE +define+OT_S81ENG_XQ_OHSEL +define+OT_S81ENG_BF_PREDEC +define+OT_S81ENG_MACRO_F6 +define+OT_S81ENG_RST_TIMED"
[ "$M" = mut ] && DEFS="$DEFS +define+OT_S81ENG_MUT_F6_RA"
echo "ENG3_MITER build $T $M ref=$REF_SHA new=$(git -C "$G" rev-parse --short HEAD) dirty=$(git -C "$G" status --porcelain -- $CHG | wc -l) defs: $DEFS"
sha256sum "$W"/ref/*.sv "$W"/new/*.sv "$B"/tb_$T.sv
$V --binary -O3 --top-module tb -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC --x-assign 0 --x-initial 0 \
   -j 16 -I"$W/sh" --Mdir "$W/obj" $DEFS "$W"/sh/*pkg*.sv $(ls "$W"/sh/*.sv "$W"/sh/*.v | grep -v pkg) "$W"/new/*.sv "$W"/ref/*.sv "$B/tb_$T.sv" \
   > "$W/build.log" 2>&1 || { tail -40 "$W/build.log"; echo "ENG3_MITER BUILD_FAIL $T $M"; exit 2; }
rc=0
for s in $SEEDS; do
  out=$("$W/obj/Vtb" +seed=$s +cycles=$CYC 2>&1 | grep -E "MITER|MISMATCH|INTERNAL|Error|error" | tail -9); echo "$out"
  line=$(echo "$out" | grep "_MITER ")
  if [ "$M" = pass ]; then echo "$line" | grep -q " PASS " || rc=1
  else echo "$line" | grep -q -E "mismatches=[1-9]" || rc=1; fi
done
echo "ENG3_MITER DONE $T $M rc=$rc ($([ $M = pass ] && echo 'all seeds PASS' || echo 'mutant CAUGHT on every seed') iff rc=0)"
# keep progressing/compiled objects for followup
exit $rc
