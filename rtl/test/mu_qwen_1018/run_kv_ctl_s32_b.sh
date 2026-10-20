#!/bin/bash
# KV-CTL3 10-20 (fork S32-B): lockstep benches of the native32 S32 = 1 forms vs S32 = 0 (Verilator 5.050).
#   usage: run_kv_ctl_s32_b.sh ROOT OUT CASE
#   PASS cases:
#     fanr  qkd_kv_es_fan_root2_b S32 1 + PH1C 1 + RCOPIES 32 == PH1C 0 / RCOPIES 1 (tb_kv_fanr_mu6_lockstep, h + fault every edge)
#     fanr6 the same bench vs the mu6 form kept as reference: S32 1 / RCOPIES 32 == S32 0 / PH1C 1 / RCOPIES 28
#     dcfg  qkd_kv_die_cfg S32 1 == S32 0 (NRST 43 CAP 1 PCOPIES 8; tb_kv_dcfg_s32_lockstep, every output every edge)
#   mutants (must FAIL, regex 'FAIL KV_FANR_MU6_LOCKSTEP mismatches[1-9]' / 'FAIL KV_DCFG_S32_LOCKSTEP mismatches[1-9]'):
#     m_ub   S32 1: the early use_b copies ignore the ph1 term (ubd = ub_base)
#     m_p1   S32 1: DA slice copies take the hi lane pair when ph1 = 0 (mux arms swapped)
#     m_ev   S32 1: the ev_now copy groups drop the expected_valid copies (wvc only)
#     m_rc   dcfg S32 1: rst_dly row r decodes the low row bits of row r + 1 (fr from rlo[(q+1)%8])
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
FR=rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_s32_misc.sv
DC=rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_s32_misc.sv
TF=rtl/test/mu_qwen_1018/tb_kv_fanr_mu6_lockstep.sv
FD='qkd_kv_es_fan_root2_b #(.MUT(0),.RCOPIES(28),.PH1C(1)) dut'
FS='qkd_kv_es_fan_root2_b_s32 #(.MUT(0),.RCOPIES(32),.PH1C(1),.S32(1)) dut'
f1(){ TB=tb_kv_fanr_mu6_lockstep; PF=$TF; PA="$FD"; PB="$FS"; }
TB=""; PF=""; PA=""; PB=""; PF2=""; PA2=""; PB2=""; MF=""; FROM=""; TO=""
case "$CASE" in
 fanr) f1;;
 fanr6) f1; PF2=$TF; PA2='qkd_kv_es_fan_root2_b #(.MUT(0)) ref0'; PB2='qkd_kv_es_fan_root2_b #(.MUT(0),.RCOPIES(28),.PH1C(1)) ref0';;
 dcfg) TB=tb_kv_dcfg_s32_lockstep;;
 m_ub) f1; MF=$FR; FROM="(ub_base && !(evn[(k < 10) ? 1 : 2] && MUT != 2))"; TO="(ub_base)";;
 m_p1) f1; MF=$FR; FROM="p1c[16 + j] ? es_p[577 + 16*j +: 16] : es_p[  1 + 16*j +: 16]"; TO="p1c[16 + j] ? es_p[  1 + 16*j +: 16] : es_p[577 + 16*j +: 16]";;
 m_ev) f1; MF=$FR; FROM="assign evn[g] = (|evc[4*g +: 4]) | (|wvc[4*g +: 4]);"; TO="assign evn[g] = (|wvc[4*g +: 4]);";;
 m_rc) TB=tb_kv_dcfg_s32_lockstep; MF=$DC; FROM="assign fr[q] = rhi[q/8] && rlo[q%8];"; TO="assign fr[q] = rhi[q/8] && rlo[(q+1)%8];";;
 *) echo "S32B $CASE: unknown case"; exit 2;;
esac
LST=$TB; [ "$TB" = tb_kv_fanr_mu6_lockstep ] && LST=tb_kv_fanr_s32
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done < "$L/$LST.f"
sub(){ python3 - "$W/$1" "$2" "$3" <<'PY' || { echo "S32B $CASE: substitution did not apply"; exit 2; }
import sys
p, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
assert s.count(a) == 1, (a, s.count(a))
open(p, "w").write(s.replace(a, b))
PY
}
[ -n "$PF" ] && { sub "$PF" "$PA" "$PB" || exit 2; }
[ -n "$PF2" ] && { sub "$PF2" "$PA2" "$PB2" || exit 2; }
[ -n "$MF" ] && { sub "$MF" "$FROM" "$TO" || exit 2; }
cd "$W"
"$V" --version > "$OUT/verilator_version.txt"
"$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH \
  --top-module "$TB" -Mdir obj -j 4 -o sim $(cat "$L/$LST.f") > "$OUT/$CASE.build" 2>&1 \
  || { echo "S32B $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
./obj/sim +verilator+seed+$((0x5eed)) > "$OUT/$CASE.log" 2>&1; rc=$?
cat "$OUT/$CASE.log"
rm -rf "$W/obj"
exit $rc
