#!/bin/bash
# KV-CTL3 10-20: lockstep of qkd_static_kv_layer_programme_s32 (native-census restructure: sliced held registers with
# per-slice kept literals, fault copy family, cfg data copies) against qkd_static_kv_layer_programme_mu MU 1 (the
# reference of tb_kv_lprg_mu5_lockstep: every output, every edge, modes A / C / B incl. faults).  Verilator 5.050.
#   usage: run_kv_ctl_s32_c.sh ROOT OUT CASE
#   PASS cases: c1 (CTLSRAM 1, RCOPIES 32 = the tile), c2 (CTLSRAM 2), lint (s32 alone, -Wall lint)
#   mutants (must FAIL, regex 'FAIL KV_LPRG_MU5_LOCKSTEP mismatches[1-9]'):
#     m_land  row landing slice 7 latches the slice-8 source bits (p_run low half <- p_run high half)
#     m_cnt   counter slices: a waiting context reloads ng instead of decrementing (cs_w arm swapped)
#     m_om    output metadata slice 1: fire one-hot 1 reads context 2's metadata
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
S32=rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_layer_programme_s32.sv
TB=tb_kv_lprg_mu5_lockstep; TF=rtl/test/mu_qwen_1018/tb_kv_lprg_mu5_lockstep.sv; LST=tb_kv_lprg_s32
PA='qkd_static_kv_layer_programme_mus #(.MUT(0),.MU(1)) dut'
pb(){ PB="qkd_static_kv_layer_programme_s32 #(.MUT(0),.MU(1),.CTLSRAM($1),.RCOPIES(32)) dut"; }
MF=""; FROM=""; TO=""
case "$CASE" in
 c1) pb 1;; c2) pb 2;;
 lint) pb 1;;
 m_land) pb 1; MF=$S32; FROM=".a(lsrc[LO+:W])"; TO=".a((gs==7)?lsrc[LO+16+:W]:lsrc[LO+:W])";;
 m_cnt) pb 1; MF=$S32; FROM=".a(cn1[LO+:16]),.b(ng_f[32*gk+LO+:16])"; TO=".a(ng_f[32*gk+LO+:16]),.b(cn1[LO+:16])";;
 m_om) pb 1; MF=$S32; FROM=".a(meta_f[68*1+LO+:W])"; TO=".a((gs==1)?meta_f[68*2+LO+:W]:meta_f[68*1+LO+:W])";;
 *) echo "S32C $CASE: unknown case"; exit 2;;
esac
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done < "$L/$LST.f"
sub(){ python3 - "$W/$1" "$2" "$3" <<'PY' || { echo "S32C $CASE: substitution did not apply"; exit 2; }
import sys
p, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
assert s.count(a) == 1, (a, s.count(a))
open(p, "w").write(s.replace(a, b))
PY
}
sub "$TF" "$PA" "$PB" || exit 2
[ -n "$MF" ] && { sub "$MF" "$FROM" "$TO" || exit 2; }
cd "$W"
"$V" --version > "$OUT/verilator_version.txt"
if [ "$CASE" = lint ]; then
  "$V" --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM --top-module qkd_static_kv_layer_programme_s32 \
    -GCTLSRAM=1 -GRCOPIES=32 $S32 rtl/lib/ot_s32_cells.sv physical/asap7_memory_macros_v2/ctl_sram_1r1w_64x64_p192/ctl_sram_1r1w_64x64_p192.v \
    physical/asap7_memory_macros_v2/ctl_sram_1r1w_64x128_p192/ctl_sram_1r1w_64x128_p192.v \
    physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$OUT/lint.log" 2>&1
  rc=$?; cat "$OUT/lint.log" | head -60; echo "S32C lint rc $rc"; exit $rc
fi
"$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH \
  --top-module "$TB" -Mdir obj -j 4 -o sim $(cat "$L/$LST.f") > "$OUT/$CASE.build" 2>&1 \
  || { echo "S32C $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
./obj/sim +verilator+seed+$((0x5eed)) > "$OUT/$CASE.log" 2>&1; rc=$?
cat "$OUT/$CASE.log"
rm -rf "$W/obj"
