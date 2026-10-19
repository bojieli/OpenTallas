#!/bin/bash
# MU-KV-CTX benches (2026-10-19; FLEET only, Verilator 5.050 = the closure daemon's): KV host plane -> d2d kind-12 MU
# context slot -> compute qfd_mu_ctx_rx -> qfd_tt_ctlm_dv OPSEG boot-context loader (mu_kvctx_bench.py, tb_mu_kvctx.sv).
#   usage: run_mu_kvctx.sh WORK [part ...]      parts (default pass mut): pass mut model kboot
#   pass  kmut 0 rmut 0: MU_KVCTX_PASS
#   mut   kmut 1 (wrong user field) / kmut 2 (wrong slot: pair order swapped) / kmut 3 (producer off) / rmut 1 (leaf loads
#         the wrong user): each MU_KVCTX_FAIL; the fail lines are the committed witnesses (results/rtl/mu_qwen_1018/kvctx/runs)
#   MU-DQ-SYSFACE 10-19: pass / mut run in CAL mode (default of mu_kvctx_bench.py: the pair slots come from both dies'
#   real D2D sequencers with the MU image + the real calendar playback); mut adds c1 (--cmut 1: the face sequencer
#   carries the MU 0 C RX image) -> MU_KVCTX_FAIL.  Part `model`: the original bench-edge pair (--model-link) pass + mutants.
set -u
D=$(cd "$(dirname "$0")" && pwd); W=${1:?WORK}; shift; mkdir -p "$W"; W=$(cd "$W" && pwd)
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
export PATH=$(dirname "$VL"):$PATH VERILATOR=$VL
verilator --version
P=${*:-pass mut}; rc=0
# the committed MU image must be the compiler's (D2D_MU=1 production compile on the current die stages / token path)
R=$(cd "$D/../../.." && pwd)
(cd "$R" && D2D_MU=1 bash tools/qwen_split/d2d_cal_image_production.sh "$W/img_mu" > "$W/img_mu.log" 2>&1) &&
  cmp "$W/img_mu/d2d_cal_image.svh" "$R/rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu.svh" &&
  echo "OK   mu_image: committed d2d_cal_image_mu.svh == compiler (D2D_MU=1)" || { echo "BAD  mu_image differs from the compiler"; rc=1; }
want() { case " $P " in *" $1 "*) return 0;; esac; return 1; }
chk() { local ok=0; case "$3" in *$2*) ok=1;; esac
    [ $ok = 1 ] && echo "OK   $1: $3" || { echo "BAD  $1 (want $2): $3"; rc=1; }; }
if want pass; then
    python3 -I "$D/mu_kvctx_bench.py" --work "$W/kvctx" --verilator "$VL" --jobs 8 > "$W/kvctx_pass.out" 2>&1
    chk kvctx_pass MU_KVCTX_PASS "$(grep -m1 '^MU_KVCTX_' "$W/kvctx_pass.out")"
fi
if want mut; then
    for mc in "k1 --kmut 1" "k2 --kmut 2" "k3 --kmut 3" "r1 --rmut 1" "c1 --cmut 1"; do
        set -- $mc; t=$1; shift
        python3 -I "$D/mu_kvctx_bench.py" --work "$W/kvctx" "$@" --verilator "$VL" --jobs 8 > "$W/kvctx_$t.out" 2>&1
        chk kvctx_$t MU_KVCTX_FAIL "$(grep -m1 '^MU_KVCTX_' "$W/kvctx_$t.out")"
    done
fi
if want model; then
    python3 -I "$D/mu_kvctx_bench.py" --work "$W/kvctx" --model-link --verilator "$VL" --jobs 8 > "$W/kvctx_model_pass.out" 2>&1
    chk kvctx_model_pass MU_KVCTX_PASS "$(grep -m1 '^MU_KVCTX_' "$W/kvctx_model_pass.out")"
fi
# KV-LINKCFG-MU 10-19 part `kboot`: the KV TX calendar boot-loaded from target 11 as on the KV die (--kboot; the KV
# sequencer's cfg_* are load-less there).  target11_mu.hex = kv_static_programme.link_cfg_words under OT_KV_MU=1 (branch
# claude/kv-linkcfg-mu-1019); it must equal the bound d2d_cal_image_mu.svh K words.  Mutant: target11_prefix.hex = the
# pre-fix compile (seam 2,2,2,2,2,2/11,11,9,9,9,11,11, no --mu): no MU context slot -> MU_KVCTX_FAIL.
KB=$R/results/rtl/mu_qwen_1018/kvctx/kboot
if want kboot; then
    python3 -I - "$KB/target11_mu.hex" "$R/rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu.svh" <<'PY' && echo "OK   kboot_image: target11_mu.hex == d2d_cal_image_mu.svh K TX/RX + SEG2" || { echo "BAD  kboot_image: target11_mu.hex != the bound MU image"; rc=1; }
import re, sys
w = [int(x, 16) for x in open(sys.argv[1]).read().split()]
t = open(sys.argv[2]).read()
v = lambda n: int(re.search(n + r" = \d+'h([0-9a-fA-F]+);", t).group(1), 16)
tx, rx = v('D2D_CAL_K_TX_IMG'), v('D2D_CAL_K_RX_IMG')
want = [x for i in range(32) for x in ((tx >> 32 * i) & 0xffffffff, (rx >> 32 * i) & 0xffffffff)] + [v('D2D_CAL_K_TX_SEG2'), v('D2D_CAL_K_RX_SEG2')]
sys.exit(0 if w == want else 1)
PY
    python3 -I "$D/mu_kvctx_bench.py" --work "$W/kvctx" --kboot "$KB/target11_mu.hex" --verilator "$VL" --jobs 8 > "$W/kvctx_kboot_mu.out" 2>&1
    chk kvctx_kboot_mu MU_KVCTX_PASS "$(grep -m1 '^MU_KVCTX_' "$W/kvctx_kboot_mu.out")"
    python3 -I "$D/mu_kvctx_bench.py" --work "$W/kvctx" --kboot "$KB/target11_prefix.hex" --verilator "$VL" --jobs 8 > "$W/kvctx_kboot_prefix.out" 2>&1
    chk kvctx_kboot_prefix MU_KVCTX_FAIL "$(grep -m1 '^MU_KVCTX_' "$W/kvctx_kboot_prefix.out")"
fi
[ $rc = 0 ] && echo "MU_KVCTX BENCHES: PASS" || echo "MU_KVCTX BENCHES: FAIL"
exit $rc
