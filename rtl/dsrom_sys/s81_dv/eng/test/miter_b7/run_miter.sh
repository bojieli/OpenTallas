#!/bin/bash
# S81-ENGRR-B7 11-07 latency-aligned lock-step miter of core E: NEW = this worktree + DEFS_NEW; REF = same sources at REF_SHA
# with the new forms off and every module renamed *_ref. f_ks/cfg_en reach REF one edge later (PIN CYCLES +1, F6 entry stage);
# hx_w is compared with REF one edge earlier (OT_S81ENG_HXW_POS). $1 = H|I (vH defines | vI defines), $2 = pass|mut, $3 seeds, $4 cycles
set -uo pipefail
T=$1; M=$2; SEEDS=$3; CYC=$4
REF_SHA=${REF_SHA:-08d577e1d87}
B=$(cd "$(dirname "$0")" && pwd); G=${MITER_ROOT:-$(git -C "$B" rev-parse --show-toplevel)}; S=$B/../miter_ohsel
# REF_DIR: exported tree of REF_SHA, for hosts without git access to the hub
refshow() { if [ -n "${REF_DIR:-}" ]; then cat "$REF_DIR/$1"; else git -C "$G" show "$REF_SHA:$1"; fi; }
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
W=${MITER_WORK:-/tmp/b7_miter_$$}/build_${T}_${M}; rm -rf "$W"; mkdir -p "$W/ref" "$W/new" "$W/sh"
SPEC=$G/physical/die_plan/s81/cores/legacy/specs/dsdv_eng_rr_e/spec.json
SRC=$(python3 -I -c "import json,sys;print(' '.join(json.load(open(sys.argv[1]))['sources']))" "$SPEC")
for p in $SRC rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_hash_n32_layer_pr.sv; do case "$p" in *pkg*) cp "$G/$p" "$W/sh/";; physical/*) cp "$G/${p%_bb.v}.v" "$W/sh/" 2>/dev/null || cp "$G/$p" "$W/sh/";; *) refshow "$p" > "$W/ref/$(basename $p)"; cp "$G/$p" "$W/new/$(basename $p)";; esac; done
sed -i -E 's/\bOT_S81ENG_(MACRO_F6|RST_TIMED|TMAP_CPRE|HXW_POS|SYNC_RST)\b/OT_REF_OFF_\1/g' "$W"/ref/*.sv
mods=$(grep -h -o -E '^\s*(\(\*[^*]*\*\)\s*)?module\s+[A-Za-z0-9_]+' "$W"/ref/*.sv | sed -E 's/.*module\s+//' | sort -u | paste -sd'|')
perl -pi -e "s/\\b($mods)\\b/\$1_ref/g" "$W"/ref/*.sv
DEFS="+define+SYNTHESIS +define+OT_ENGRAM_CRCMAT +define+OT_S81ENG_RR_N32 +define+OT_S81ENG_RR_MUL_N32 +define+OT_S81ENG_HXL +define+OT_S81ENG_XQ_OHSEL +define+OT_S81ENG_BF_PREDEC +define+OT_S81ENG_TMAP_CPRE +define+OT_S81ENG_MACRO_F6 +define+OT_S81ENG_RST_TIMED +define+OT_S81ENG_HXW_POS"
[ "$T" = I ] && DEFS="$DEFS +define+OT_S81ENG_SYNC_RST"
[ "$M" = mut ] && DEFS="$DEFS +define+OT_S81ENG_MUT_F6_RA"
[ "$M" = mut2 ] && DEFS="$DEFS +define+B7_NO_ALIGN"
echo "B7_MITER build $T $M ref=$REF_SHA ref_dir=${REF_DIR:-} defs: $DEFS"
$V --binary -O3 --top-module tb -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC --x-assign 0 --x-initial 0 -j ${J:-16} -I"$W/sh" --Mdir "$W/obj" $DEFS \
   "$W"/sh/*pkg*.sv $(ls "$W"/sh/*.sv "$W"/sh/*.v 2>/dev/null | grep -v pkg) "$W"/new/*.sv "$W"/ref/*.sv "$B/tb_core.sv" > "$W/build.log" 2>&1 || { tail -30 "$W/build.log"; echo "B7_MITER BUILD_FAIL $T $M"; exit 2; }
rc=0
for s in $SEEDS; do
  out=$("$W/obj/Vtb" +seed=$s +cycles=$CYC 2>&1 | grep -E "MITER|MISMATCH|INTERNAL|Error|error" | tail -8); echo "$out"
  line=$(echo "$out" | grep "_MITER ")
  if [ "$M" = pass ]; then echo "$line" | grep -q " PASS " || rc=1; else echo "$line" | grep -q -E "mismatches=[1-9]" || rc=1; fi
done
echo "B7_MITER DONE $T $M rc=$rc"
exit $rc
