#!/bin/bash
# KV-CTL10 10-20: benches for the exact native-census successor of the die ctl tile (OT_KV_CTL_C32).  Verilator 5.050.
#   usage: run_kv_ctl_c32.sh ROOT OUT CASE
# PASS cases
#   dcfg        tb_kv_dcfg_a_c32: qkd_kv_die_cfg_a vs qkd_kv_die_cfg_a_c32, 400 POR / image / error episodes
#   tile_a/b    tb_kv_ctl_c32_tile: reference ctl (boot-ages tile + declared deltas u_own PIPE1/SAFE1, u_boot SRQ2) vs the
#               generated _c32 / _c32b tile, every output every edge (random inputs, resets, POR)
#   first_a     tile_a from a random power-up state (--x-initial unique + rand reset)
#   kb_a/kb_b   tb_mu_kv_boot (compiler 471-word MU image through the real boot path, 4 users per the GAP table, every
#               programme pulse vs the compiler event list) with DUT = the generated c32 / c32b qkd_kvs_ctl
#   kb_first    kb_a from a random power-up state
# FAIL cases (mutants; fail regex '^FAIL')
#   m_dc6 dcfg with c32 MUT 6 (age words one off)   m_dc7 dcfg with c32 MUT 7 (ages not seal-gated)
#   m_tl  tile_a with the layer programme row-landing slice 7 taking the slice-8 bits (random inputs never load a valid
#         programme: NOT caught by tile_a -> use kb_m_tl)
#   kb_m_tl kb_a with the same layer programme mutant (fail regex '^C32 kb_m_tl rc=.*FAIL MU_KV_BOOT')
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
D=rtl/qwen_sys/static_kv_die_20261017; M=rtl/qwen_sys/mu_qwen_20261018; S=rtl/qwen_sys/static_kv_20261014; T=rtl/test/kv_ctl10_1020
BA=$D/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv
LP=$M/qkd_static_kv_layer_programme_s32.sv
K=results/rtl/mu_qwen_1018/kvboot
KBDATA="$K/target1.hex $K/target3.hex $K/bench_starts.txt $K/bench_events.txt results/arch/qwen_kv_static_programme_1017/die/target2.hex"
COMMON="$S/qkd_static_kv_ownership.sv $S/qkd_static_kv_layer_programme.sv $S/qkd_static_kv_boot_cdc.sv $S/qkd_static_kv_boot_dispatch.sv
 rtl/physical/ot_qkd_kv_static_writer_native.sv $S/qkd_kv_static_writer.sv rtl/lib/ot_rst_relay.sv $S/qkd_kv_ownership_obs.sv
 $S/qkd_kv_native_programme.sv $D/qkd_kv_ctl_half_root_b.sv $S/qkd_kv_die_cfg.sv $S/qkd_kv_cfault_tree.sv $M/qkd_kv_mu_rowoff.sv
 $M/qkd_kv_static_writer_native_mu.sv $M/qkd_static_kv_layer_programme_mu.sv $M/qkd_static_kv_boot_dispatch_mu.sv
 $M/qkd_static_kv_ownership_calendar_mu.sv rtl/qwen_sys/kv_bootage_20261019/qkd_kv_die_cfg_a.sv
 physical/asap7_memory_macros_v2/ctl_sram_1r1w_64x64_p192/ctl_sram_1r1w_64x64_p192.v
 physical/asap7_memory_macros_v2/ctl_sram_1r1w_64x128_p192/ctl_sram_1r1w_64x128_p192.v
 rtl/lib/ot_s32_cells.sv $LP $D/qkd_kv_ctl_s32_writer.sv $D/qkd_kv_ctl_c32_misc.sv $D/qkd_kv_ctl_c32_boot.sv
 $D/qkd_kv_ctl_c32_dcfg.sv $D/qkd_kv_ctl_c32_obs.sv"
XI=""; RR=""; SEED=$((0x5eed)); MF=""; FROM=""; TO=""; DEF=""; KIND=tile; C32=$D/qkd_kvs_tiles_hroot_ff_k_mu_ba_c32.sv
case "$CASE" in
 dcfg) KIND=dcfg;;
 m_dc6) KIND=dcfg; DEF="+define+CMUT=6";;
 m_dc7) KIND=dcfg; DEF="+define+CMUT=7";;
 tile_a) ;;
 tile_i) C32=$D/qkd_kvs_tiles_hroot_ff_k_mu_ba_c32i.sv;;
 kb_i) KIND=kb; C32=$D/qkd_kvs_tiles_hroot_ff_k_mu_ba_c32i.sv;;
 kb_i_m_tl) KIND=kb; C32=$D/qkd_kvs_tiles_hroot_ff_k_mu_ba_c32i.sv; MF=$LP; FROM=".a(lsrc[LO+:W])"; TO=".a((gs==7)?lsrc[LO+16+:W]:lsrc[LO+:W])";;
 tile_b) C32=$D/qkd_kvs_tiles_hroot_ff_k_mu_ba_c32b.sv;;
 first_a) XI="--x-initial unique"; RR="+verilator+rand+reset+2";;
 m_tl) MF=$LP; FROM=".a(lsrc[LO+:W])"; TO=".a((gs==7)?lsrc[LO+16+:W]:lsrc[LO+:W])";;
 kb_a) KIND=kb;;
 kb_b) KIND=kb; C32=$D/qkd_kvs_tiles_hroot_ff_k_mu_ba_c32b.sv;;
 kb_first) KIND=kb; XI="--x-initial unique"; RR="+verilator+rand+reset+2";;
 kb_m_tl) KIND=kb; MF=$LP; FROM=".a(lsrc[LO+:W])"; TO=".a((gs==7)?lsrc[LO+16+:W]:lsrc[LO+:W])";;
 *) echo "C32 $CASE: unknown case"; exit 2;;
esac
case "$CASE" in tile_i|kb_i|kb_i_m_tl) export C32_DSTG=1;; esac
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
cpf(){ mkdir -p "$W/$(dirname "$1")"; cp "$ROOT/$1" "$W/$1"; }
EXTRA=""
if [ $KIND = kb ]; then
  KBL="rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_pcport.sv
   rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv
   physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/test/mu_qwen_1018/tb_mu_kv_boot.sv"
  for f in $COMMON $KBL $KBDATA; do cpf $f; done
  TB=tb_mu_kv_boot
elif [ $KIND = dcfg ]; then
  for f in $D/qkd_kv_ctl_c32_misc.sv rtl/qwen_sys/kv_bootage_20261019/qkd_kv_die_cfg_a.sv $D/qkd_kv_ctl_c32_dcfg.sv $T/tb_kv_dcfg_a_c32.sv; do cpf $f; done
  COMMON="$D/qkd_kv_ctl_c32_misc.sv rtl/qwen_sys/kv_bootage_20261019/qkd_kv_die_cfg_a.sv $D/qkd_kv_ctl_c32_dcfg.sv"
  EXTRA="$T/tb_kv_dcfg_a_c32.sv"; TB=tb_kv_dcfg_a_c32
else
  for f in $COMMON $T/tb_kv_ctl_c32_tile.sv; do cpf $f; done
  # reference: the KV-CTL3 copies of the four shared files carrying PIPE / SAFE / SRQ (bench-only, replace the originals)
  for r in qkd_static_kv_ownership.sv qkd_static_kv_boot_dispatch.sv; do cp "$ROOT/$T/ref/$r" "$W/$S/$r"; done
  for r in qkd_static_kv_ownership_calendar_mu.sv qkd_static_kv_boot_dispatch_mu.sv; do cp "$ROOT/$T/ref/$r" "$W/$M/$r"; done
  EXTRA="$T/tb_kv_ctl_c32_tile.sv ref_ctl.sv"; TB=tb_kv_ctl_c32_tile
  python3 - "$ROOT/$BA" "$W/ref_ctl.sv" <<'PY' || exit 2
import re, sys
s = open(sys.argv[1]).read(); m = re.search(r'^module qkd_kvs_ctl \(.*?^endmodule\n', s, re.S | re.M); b = m.group(0)
for a, c in (('module qkd_kvs_ctl (', 'module qkd_kvs_ctl_ref ('),
             ('qkd_static_kv_ownership_calendar_mu #(.MUT(0), .MU(1)) u_own', 'qkd_static_kv_ownership_calendar_mu #(.MUT(0), .MU(1), .PIPE(1), .SAFE(1)) u_own'),
             ('.MU(1), .WMUT(0)) u_boot', '.MU(1), .WMUT(0), .SRQ(2)) u_boot')):
    assert b.count(a) == 1, a
    b = b.replace(a, c)
import os
if os.environ.get('C32_DSTG') == '1': b=b.replace('.SRQ(2)) u_boot', '.SRQ(2), .DSTG(1)) u_boot')
open(sys.argv[2], 'w').write('`timescale 1ns/1ps\n' + b)
PY
fi
if [ $KIND != dcfg ]; then   # the generated c32 qkd_kvs_ctl only (the tile file's other tiles need die children)
  python3 - "$ROOT/$C32" "$W/c32_ctl.sv" <<'PY' || exit 2
import re, sys
s = open(sys.argv[1]).read(); m = re.search(r'^(//[^\n]*\n)*module qkd_kvs_ctl \(.*?^endmodule\n', s, re.S | re.M)
open(sys.argv[2], 'w').write('`timescale 1ns/1ps\n' + m.group(0))
PY
  EXTRA="$EXTRA c32_ctl.sv"
fi
if [ "$CASE" = kb_first ]; then   # first use: the POR domain sees a POR pulse (por_n follows rst_n), open inputs tied 0
  python3 - "$W/rtl/test/mu_qwen_1018/tb_mu_kv_boot.sv" <<'PY' || { echo "C32 $CASE: por substitution did not apply"; exit 2; }
import sys
p = sys.argv[1]; s = open(p).read(); a = ".por_n(1'b1)"
assert s.count(a) == 1, s.count(a)
s = s.replace(a, ".por_n(rst_n),.embgw__bw(293'd0),.d2d__skw(12'd0),.d2d__srx(522'd0),.d2d__kvn_word_identity(59'd0),"
              ".d2d__kvn_word_generation(2'd0),.oobs__host_launch_quiet(1'b0),.oobs__host_upstream_quiet(6'd0),"
              ".i_hroot_WS(144'd0),.i_hroot_WN(144'd0),.i_hroot_ES(144'd0),.i_hroot_EN(144'd0)")
open(p, "w").write(s)
PY
fi
if [ -n "$MF" ]; then python3 - "$W/$MF" "$FROM" "$TO" <<'PY' || { echo "C32 $CASE: substitution did not apply"; exit 2; }
import sys
p, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read(); assert s.count(a) == 1, (a, s.count(a)); open(p, "w").write(s.replace(a, b))
PY
fi
cd "$W"
"$V" --version > "$OUT/verilator_version.txt"
"$V" --binary --timing -O2 $XI $DEF -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH -Wno-PINMISSING \
  --top-module "$TB" -Mdir obj -j 8 -o sim $COMMON $([ $KIND = kb ] && echo $KBL) $EXTRA > "$OUT/$CASE.build" 2>&1 \
  || { echo "C32 $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
if [ $KIND = kb ]; then
  ./obj/sim +verilator+seed+$SEED $RR +IMG=$K/target1.hex +NW=471 +IMG2=results/arch/qwen_kv_static_programme_1017/die/target2.hex \
    +IMG3=$K/target3.hex +STARTS=$K/bench_starts.txt +EVENTS=$K/bench_events.txt > "$OUT/$CASE.log" 2>&1; rc=$?
else
  ./obj/sim +verilator+seed+$SEED $RR > "$OUT/$CASE.log" 2>&1; rc=$?
fi
r=$(grep -E '^(PASS|FAIL)|^%Error|Fatal|fatal' "$OUT/$CASE.log" | head -1)
echo "C32 $CASE rc=$rc: $r"
rm -rf "$W/obj"
[ $rc = 0 ] && grep -q '^PASS' "$OUT/$CASE.log"
