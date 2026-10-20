#!/bin/bash
# KV-CTL3 S32-A 10-20: lockstep benches of the S32 writer programme / writer role (Verilator 5.050).
#   usage: run_kv_ctl_s32_a.sh ROOT OUT CASE
#   PASS cases:
#     lock   tb_kv_ctl_s32_a: qkd_kv_native_programme (SRAM 1 CTLSRAM 1 RCOPIES 16) -> qkd_kv_static_writer_native_mu
#            (MU 1 RST_COPIES 10) == qkd_kv_native_programme_s32 -> qkd_kv_static_writer_native_mu_s32 (NC 4, copy ports),
#            every output every edge + copy outputs == main outputs        PASS regex 'PASS KV_S32_A_LOCKSTEP mismatches0'
#     wprg1  tb_kv_wprg_mu5_lockstep with dut = qkd_kv_native_programme_s32 SRAM 1 CTLSRAM 1 RCOPIES 16 (ref = flop table)
#     wprg0  tb_kv_wprg_mu5_lockstep with dut = qkd_kv_native_programme_s32 SRAM 0                    PASS 'PASS KV_WPRG_MU5_LOCKSTEP'
#   mutants (must FAIL, regex 'FAIL KV_S32_A_LOCKSTEP mismatches[1-9]'):
#     m_sl   writer: es high-half slice 3 never loads (its hs copy ignored)
#     m_lo   writer: half_data slice 5 never loads (its ls copy ignored)
#     m_ld   wprg:   root-row slice 0 (t0[13:0]) never loads (its ld copy ignored)
#     m_cy   wprg:   cycle slice 0 never increments (its active copy ignored)
#     m_cp   wprg:   exported word-slot copy 0 stuck 0 (writer select family group 0 dead)
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
S=rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_s32_writer.sv
TW=rtl/test/mu_qwen_1018/tb_kv_wprg_mu5_lockstep.sv
WD='qkd_kv_native_programme #(.MUT(0),.VMAP(1),.RCOPIES(3),.SRAM(1)) dut'
TB=tb_kv_ctl_s32_a; LF=tb_kv_ctl_s32_a; PF=""; PA=""; PB=""; MF=""; FROM=""; TO=""
case "$CASE" in
 lock) ;;
 wprg1) TB=tb_kv_wprg_mu5_lockstep; PF=$TW; PA="$WD"; PB="qkd_kv_native_programme_s32 #(.MUT(0),.VMAP(1),.RCOPIES(16),.SRAM(1),.CTLSRAM(1)) dut";;
 wprg0) TB=tb_kv_wprg_mu5_lockstep; PF=$TW; PA="$WD"; PB="qkd_kv_native_programme_s32 #(.MUT(0),.VMAP(1),.SRAM(0)) dut";;
 m_sl) MF=$S; FROM="else if (hs_hi[k]) es_data[128 + LO +: W]"; TO="else if (hs_hi[k] && k != 3) es_data[128 + LO +: W]";;
 m_lo) MF=$S; FROM="else if (ls_h[k]) half_data"; TO="else if (ls_h[k] && k != 5) half_data";;
 m_ld) MF=$S; FROM="else if(ldc[k])tv[LO+:W]<=rt_all[LO+:W];"; TO="else if(ldc[k]&&k!=0)tv[LO+:W]<=rt_all[LO+:W];";;
 m_cy) MF=$S; FROM=".s(actc[k]&&!spy[k])"; TO=".s(actc[k]&&!spy[k]&&k!=0)";;
 m_cp) MF=$S; FROM="wsc<={NC{actc[NCY]&&next_slot}};"; TO="wsc<={NC{actc[NCY]&&next_slot}}&{{(NC-1){1'b1}},1'b0};";;
 m_l0) MF=$S; FROM=".s(lsg[gi] && good)"; TO=".s(lsg[gi] && good && gi != 1)";;
 *) echo "S32A $CASE: unknown case"; exit 2;;
esac
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done < "$L/$LF.f"
mkdir -p "$W/$(dirname "$TW")"; cp "$ROOT/$TW" "$W/$TW"
sub(){ python3 - "$W/$1" "$2" "$3" <<'PY' || { echo "S32A $CASE: substitution did not apply"; exit 2; }
import sys
p, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
assert s.count(a) == 1, (a, s.count(a))
open(p, "w").write(s.replace(a, b))
PY
}
[ -n "$PF" ] && { sub "$PF" "$PA" "$PB" || exit 2; }
[ -n "$MF" ] && { sub "$MF" "$FROM" "$TO" || exit 2; }
cd "$W"
FILES="$(cat "$L/$LF.f")"; [ "$TB" != "$LF" ] && FILES="$FILES $TW"
"$V" --version > "$OUT/verilator_version.txt"
"$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH \
  --top-module "$TB" -Mdir obj -j 4 -o sim $FILES > "$OUT/$CASE.build" 2>&1 \
  || { echo "S32A $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
./obj/sim +verilator+seed+$((0x5eed)) > "$OUT/$CASE.log" 2>&1; rc=$?
cat "$OUT/$CASE.log"
rm -rf "$W/obj"
exit $rc
