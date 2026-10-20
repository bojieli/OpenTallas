#!/bin/bash
# KV-CTL3 10-20: REAL-RTL FIRST USE of qkd_kvs_ctl_s32 (native-census members): the MU-KV-BOOT bench (tb_mu_kv_boot:
# the compiler's 471-word MU image through the real boot path, targets 2 / 3, then 4 users run per the GAP table; every
# programme pulse checked against the compiler's event list, user 0 lockstep with the single-user programme, every token
# completes 36 stages) with the DUT = qkd_kvs_ctl_s32.  Verilator 5.050.
#   usage: run_kv_ctl_s32_kb.sh ROOT OUT CASE
#   PASS: kb (CTLSRAM 1), kb_ctl2 (CTLSRAM 2), kb_first / kb_first2 (--x-initial unique + +verilator+rand+reset+2: every
#         flop, kept copy and SRAM word starts random -> the copies must converge from reset alone; por_n follows rst_n so
#         the POR domain is reset too), kb_first_orig (the same first-use run on the original qkd_kvs_ctl: baseline)
#   FAIL (fail regex):  kb_sealwrong 'layer programme not configured .*lprg fault 04'   kb_gapnot 'layer programme not configured .*lprg fault 01'
#                       kb_u0gap 'user 0 differs from MU 0'   kb_collide 'layer programme / dispatcher fault .*lprg fault 10'
#                       m_tl / m_cnt (S32 structure: row-landing slice / counter arms) '^FAIL MU_KV_BOOT'
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
K=results/rtl/mu_qwen_1018/kvboot
DATA="$K/target1.hex $K/target3.hex $K/bench_starts.txt $K/bench_events.txt $K/mut_u0gap.hex $K/mut_collide.hex $K/mut_sealwrong.hex results/arch/qwen_kv_static_programme_1017/die/target2.hex"
TOPF=rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_ctl_s32.sv
LP=rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_layer_programme_s32.sv
TBF=rtl/test/mu_qwen_1018/tb_mu_kv_boot.sv
TB=tb_mu_kv_boot; LST=tb_kv_ctl_s32_kb; IMG=$K/target1.hex; NW=471; MF=""; FROM=""; TO=""; PX=""; XI=""; RR=""; SEED=$((0x5eed))
DUT='qkd_kvs_ctl_s32 dut('; POR=0
case "$CASE" in
 kb) ;;
 kb_ctl2) DUT='qkd_kvs_ctl_s32 #(.CTLSRAM(2)) dut(';;
 kb_first) XI="--x-initial unique"; RR="+verilator+rand+reset+2"; POR=1;;
 kb_first2) XI="--x-initial unique"; RR="+verilator+rand+reset+2"; SEED=4242; POR=1;;
 kb_first_orig) XI="--x-initial unique"; RR="+verilator+rand+reset+2"; POR=1; DUT='qkd_kvs_ctl dut(';;
 kb_sealwrong) IMG=$K/mut_sealwrong.hex; NW=327;;
 kb_gapnot) MF=$TOPF; FROM='.MU(1), .WMUT(0)'; TO='.MU(1), .WMUT(1)';;
 kb_u0gap) IMG=$K/mut_u0gap.hex;;
 kb_collide) IMG=$K/mut_collide.hex; PX=+NOLIST;;
 m_tl) MF=$LP; FROM=".a(lsrc[LO+:W])"; TO=".a((gs==7)?lsrc[LO+16+:W]:lsrc[LO+:W])";;
 m_cnt) MF=$LP; FROM=".a(cn1[LO+:16]),.b(ng_f[32*gk+LO+:16])"; TO=".a(ng_f[32*gk+LO+:16]),.b(cn1[LO+:16])";;
 m_priority) MF=$LP; FROM="assign p={e[3]&&!(|e[2:0]),e[2]&&!(|e[1:0]),e[1]&&!e[0],e[0]};"; TO="assign p=4'b0;";;
 *) echo "S32KB $CASE: unknown case"; exit 2;;
esac
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
for f in $(cat "$L/$LST.f") $DATA; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done
sub(){ python3 - "$W/$1" "$2" "$3" <<'PY' || { echo "S32KB $CASE: substitution did not apply"; exit 2; }
import sys
p, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
assert s.count(a) == 1, (a, s.count(a))
open(p, "w").write(s.replace(a, b))
PY
}
sub "$TBF" 'qkd_kvs_ctl dut(' "$DUT" || exit 2
[ -n "$MF" ] && { sub "$MF" "$FROM" "$TO" || exit 2; }
# first use: the bench ties por_n high; from a random power-up state the POR domain (u_dcfg) must see a POR pulse too
# and the inputs the bench leaves open (0 in a zero-initialised run) are tied to 0 explicitly (else they power up random)
[ "$POR" = 1 ] && { sub "$TBF" '.por_n(1'"'"'b1)' '.por_n(rst_n),.embgw__bw(293'"'"'d0),.d2d__skw(12'"'"'d0),.d2d__srx(522'"'"'d0),.d2d__kvn_word_identity(59'"'"'d0),.d2d__kvn_word_generation(2'"'"'d0),.oobs__host_launch_quiet(1'"'"'b0),.oobs__host_upstream_quiet(6'"'"'d0),.i_hroot_WS(144'"'"'d0),.i_hroot_WN(144'"'"'d0),.i_hroot_ES(144'"'"'d0),.i_hroot_EN(144'"'"'d0)' || exit 2; }
cd "$W"
"$V" --version > "$OUT/verilator_version.txt"
"$V" --binary --timing -O2 $XI -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH -Wno-PINMISSING \
  --top-module "$TB" -Mdir obj -j 8 -o sim $(cat "$L/$LST.f") > "$OUT/$CASE.build" 2>&1 \
  || { echo "S32KB $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
./obj/sim +verilator+seed+$SEED $RR +IMG=$IMG +NW=$NW +IMG2=results/arch/qwen_kv_static_programme_1017/die/target2.hex +IMG3=$K/target3.hex \
  +STARTS=$K/bench_starts.txt +EVENTS=$K/bench_events.txt $PX > "$OUT/$CASE.log" 2>&1; rc=$?
r=$(grep -E '^(PASS|FAIL)|^%Error|Fatal|fatal' "$OUT/$CASE.log" | head -1)
echo "S32KB $CASE rc=$rc: $r"
rm -rf "$W/obj"
[ $rc = 0 ] && grep -q '^PASS' "$OUT/$CASE.log"
