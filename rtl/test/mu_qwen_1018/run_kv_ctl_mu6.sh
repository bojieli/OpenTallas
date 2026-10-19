#!/bin/bash
# KV-SRAM-CTL 10-19: lockstep benches of the mu6 / mu6b control-tile storage and copy changes (Verilator 5.050).
#   usage: run_kv_ctl_mu6.sh ROOT OUT CASE
#   PASS cases:
#     lprg1 / lprg2  qkd_static_kv_layer_programme_mus CTLSRAM 1 (10 x 64x64 p192 banks) / 2 (64x128) + RCOPIES 32
#                    == qkd_static_kv_layer_programme_mu MU 1, every output, every edge (tb_kv_lprg_mu5_lockstep)
#     wprg1 / wprg2  qkd_kv_native_programme SRAM 1 CTLSRAM 1 / 2 + RCOPIES 16 == SRAM 0 (tb_kv_wprg_mu5_lockstep)
#     fanr           qkd_kv_es_fan_root2_b PH1C 1 + RCOPIES 28 == PH1C 0 / RCOPIES 1 (tb_kv_fanr_mu6_lockstep)
#   mutants (must FAIL, regex 'FAIL KV_(LPRG|WPRG)_MU5_LOCKSTEP mismatches[1-9]' / 'FAIL KV_FANR_MU6_LOCKSTEP mismatches[1-9]'):
#     m_lb1  CTLSRAM 1: rowb bank 2 (gap ==0 / ==1 flags) reads row + 1
#     m_lb2  CTLSRAM 2: rowa bank 1 (P_issue..P_quiet) reads row + 1
#     m_wr1  CTLSRAM 1: wprg bank 1 (roots 2, 3) reads row + 1
#     m_wr2  CTLSRAM 2: wprg bank 1 (stop root) written at row + 1
#     m_ph   PH1C 1: DB slices take the ph1 = 0 lane pair when ph1 = 1 (mux arms swapped)
#     m_pc   PH1C 1: QA pc field arms swapped
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
LP=rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_layer_programme_mus.sv
WP=rtl/qwen_sys/static_kv_20261014/qkd_kv_native_programme.sv
FR=rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_half_root_b.sv
TL=rtl/test/mu_qwen_1018/tb_kv_lprg_mu5_lockstep.sv; TW=rtl/test/mu_qwen_1018/tb_kv_wprg_mu5_lockstep.sv
LD='qkd_static_kv_layer_programme_mus #(.MUT(0),.MU(1)) dut'
WD='qkd_kv_native_programme #(.MUT(0),.VMAP(1),.RCOPIES(3),.SRAM(1)) dut'
l1(){ TB=tb_kv_lprg_mu5_lockstep; PF=$TL; PA="$LD"; PB="qkd_static_kv_layer_programme_mus #(.MUT(0),.MU(1),.CTLSRAM($1),.RCOPIES(32)) dut"; }
w1(){ TB=tb_kv_wprg_mu5_lockstep; PF=$TW; PA="$WD"; PB="qkd_kv_native_programme #(.MUT(0),.VMAP(1),.RCOPIES(16),.SRAM(1),.CTLSRAM($1)) dut"; }
TB=""; PF=""; PA=""; PB=""; MF=""; FROM=""; TO=""
case "$CASE" in
 lprg1) l1 1;; lprg2) l1 2;; wprg1) w1 1;; wprg2) w1 2;;
 fanr) TB=tb_kv_fanr_mu6_lockstep;;
 m_lb1) l1 1; MF=$LP; FROM=".r_addr_in(rd_idx),.rd_out(rowb[128+:64])"; TO=".r_addr_in(rd_idx+6'd1),.rd_out(rowb[128+:64])";;
 m_lb2) l1 2; MF=$LP; FROM=".r_addr_in(rd_idx),.rd_out(rowa[128+:128])"; TO=".r_addr_in(rd_idx+6'd1),.rd_out(rowa[128+:128])";;
 m_wr1) w1 1; MF=$WP; FROM=".r_addr_in(r_row),.rd_out(rd[64+:64])"; TO=".r_addr_in(r_row+6'd1),.rd_out(rd[64+:64])";;
 m_wr2) w1 2; MF=$WP; FROM=".w_addr_in(wq_row),.wd_in(w_d[128+:128])"; TO=".w_addr_in(wq_row+6'd1),.wd_in(w_d[128+:128])";;
 m_ph) TB=tb_kv_fanr_mu6_lockstep; MF=$FR; FROM="es_p[865 + 32*gs +: 32] : es_p[289 + 32*gs +: 32]"; TO="es_p[289 + 32*gs +: 32] : es_p[865 + 32*gs +: 32]";;
 m_pc) TB=tb_kv_fanr_mu6_lockstep; MF=$FR; FROM="assign qa_s = ph1 ? epc_p[10 +: 5] : epc_p[0 +: 5];"; TO="assign qa_s = ph1 ? epc_p[0 +: 5] : epc_p[10 +: 5];";;
 *) echo "MU6 $CASE: unknown case"; exit 2;;
esac
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done < "$L/$TB.f"
sub(){ python3 - "$W/$1" "$2" "$3" <<'PY' || { echo "MU6 $CASE: substitution did not apply"; exit 2; }
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
"$V" --version > "$OUT/verilator_version.txt"
"$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH \
  --top-module "$TB" -Mdir obj -j 4 -o sim $(cat "$L/$TB.f") > "$OUT/$CASE.build" 2>&1 \
  || { echo "MU6 $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
./obj/sim +verilator+seed+$((0x5eed)) > "$OUT/$CASE.log" 2>&1; rc=$?
cat "$OUT/$CASE.log"
rm -rf "$W/obj"
[ $rc = 0 ] && grep -q '^PASS' "$OUT/$CASE.log"
