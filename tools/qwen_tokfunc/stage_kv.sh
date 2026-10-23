#!/bin/bash
# TOK-FUNC-QW stage "kv" (10-21): KV-die attention (release vehicle tb_kvattn_rel, 1 user and 4 users) on the RTL-only
# SOURCE ASSEMBLY (RUNROOT/src), Verilator 5.050 hierarchical.  = KV-MU7 job4/job4b (claude/kv-mu6-kvattn-1020 0e597ed1c)
# rebuilt from scratch on RUNROOT/src instead of reusing job3's hier libraries.
#
#   stage_kv.sh RUNROOT [--die-netlist DIR]
#
# Bench files (not on the assembly; tb + CPU-golden driver only) come from 0e597ed1c and are staged at RUNROOT/kv/fx:
#   tools/qwen_layerbench/kvattn_rel/{build,run}.sh collect.py kvattn_rel.vlt sources.txt,
#   rtl/test/qwen_kv_die/kvattn_rel_1019/{tb_kvattn_rel,kvattn_rel_dp}.sv, + the 3 SRAM macro models sources.txt names
#   outside the staged physical/ (physical/qkd_astk_strip/macros/*, asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2).
# Every RTL file in sources.txt is taken from RUNROOT/src (overlay RUNROOT/kv/tree = symlinks to src + fx).
# Source check 10-21 (job4b src_0e597ed1c vs c0f8097f3, 57 files the build read): 53 identical, 3 bench-only (absent on
# the assembly), 1 differs: rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv (assembly adds RX_FREE/TX_FREE,
# default 0 = as built; the KV-side instantiator qkd_kvs_attn_r16 is identical and leaves them 0) -> functionally same.
# Runs (run.sh): u1/u4 at T 1024/4096/8192, u1 T4096 peaky, u1 T8191, T32768 bound (expected REFUSED), 7 mutants at T1024
# (k_shift v_swap q_swap k_late gmut1 gmut2 gmut4: each must FAIL); golden = tools/qwen_tp8_attention_native.py vectors.
# MEMORY: the hierarchical build peaks ~590 GB (job4 died at 586 GB under --mem 600) -> launch with --mem 700.
#
# --die-netlist DIR (closure hook): DIR/sources.txt = the GEN die carve of the KV attention tile (netlist .v files, paths
#   absolute or relative to DIR) replaces the RTL list; the tb / golden / runs are unchanged; grade = die-netlist.
set -euo pipefail
RUNROOT=$(readlink -f "$1"); shift
NET=""; EXPL=""
# --explicit-r17 OBJDIR (TOKc-QW2 10-22, coordinator decision (a)): the CURRENT r17 attention vehicle (qkd_kvs_attn_r17 /
#   qkd_kvs_attn_fl_r17 of the assembly, RETIRE_STATIC 1 STATUS_DELAY 213 = tb defaults) built on the assembly tree with the
#   ROOT-approved explicit genuine-archive binding (b0cc8cdca, kv_explicit_r17/): top-only frontend (~1 s / ~100 MB instead
#   of the ~590 GB implicit hierarchical top) + the 35 child archives of OBJDIR, admitted only when their sha256 and their
#   whole child source readset match the approved table / the assembly bytes (kv_explicit_build.py).  Memory ~16 GB.
# --plan-frame (KV-P2-RTL 10-23, needs --explicit-r17): the data path in the KV die plan v3 frame
#   (kv_planframe/kvattn_rel_dp.sv, PV_LAND 0: pvst / pvfst unlanded = D(pvp) 0 -> F_DLY law 2); run.sh calibrates FD.
# --dqk N (with --plan-frame): kvs_ctl D_QK cfg of every run (kv_planframe/tb_kvattn_rel.sv +DQK; default 0).  The plan
#   frame keeps the QK words' landing edge, so its QK path is one edge longer than its PV path: D_QK 1.
PF=0; DQK=0
while [ $# -gt 0 ]; do case "$1" in --die-netlist) NET=$(readlink -f "$2"); shift 2;;
  --explicit-r17) EXPL=$(readlink -f "$2"); shift 2;; --plan-frame) PF=1; shift;; --dqk) DQK=$2; shift 2;; *) echo "bad arg $1"; exit 2;; esac; done
[ $PF = 0 ] || [ -n "$EXPL" ] || { echo "--plan-frame needs --explicit-r17"; exit 2; }
SRC=$RUNROOT/src; S=$RUNROOT/kv; FX=$S/fx; T=$S/tree; O=$S/out; HERE=$(dirname "$(readlink -f "$0")")
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | grep -q '5.050'
[ -f "$FX/tools/qwen_layerbench/kvattn_rel/build.sh" ] || { echo "missing fixtures $FX"; exit 2; }
rm -rf "$T" "$O"; mkdir -p "$T/physical" "$O"
for d in rtl tools configs; do cp -as "$SRC/$d" "$T/"; done
cp -as "$SRC/physical/." "$T/physical/"
cp -a "$FX/tools/qwen_layerbench/kvattn_rel" "$T/tools/qwen_layerbench/"
mkdir -p "$T/rtl/test/qwen_kv_die"; cp -a "$FX/rtl/test/qwen_kv_die/kvattn_rel_1019" "$T/rtl/test/qwen_kv_die/"
cp -as "$FX/physical/." "$T/physical/"
GRADE="RTL-functional (source assembly)"
if [ -n "$NET" ]; then
  GRADE="die-netlist"
  ( cd "$NET" && while read -r f; do [ -n "$f" ] && readlink -f "$f"; done < sources.txt ) > "$O/net_sources.txt"
  grep -E '^rtl/test/' "$T/tools/qwen_layerbench/kvattn_rel/sources.txt" >> "$O/net_sources.txt"
  cp "$O/net_sources.txt" "$T/tools/qwen_layerbench/kvattn_rel/sources.txt"
fi
echo "$(cat $SRC/ASM_COMMIT) assembly + bench 0e597ed1c (tb sha $(sha256sum $T/rtl/test/qwen_kv_die/kvattn_rel_1019/tb_kvattn_rel.sv | cut -c1-16))" > "$O/SOURCE_COMMIT.txt"
if [ -n "$EXPL" ]; then
  [ -z "$NET" ] || { echo "--explicit-r17 and --die-netlist are exclusive"; exit 2; }
  E=$HERE/kv_explicit_r17; BD=$T/rtl/test/qwen_kv_die/kvattn_rel_1019; SL=$T/tools/qwen_layerbench/kvattn_rel/sources.txt
  rm -f "$BD/kvattn_rel_dp.sv"; cp "$E/kvattn_rel_dp.sv" "$E/kvattn_rel_pv_bound.sv" "$BD/"
  OVL=(); if [ $PF = 1 ]; then cp "$HERE/kv_planframe/kvattn_rel_dp.sv" "$BD/kvattn_rel_dp.sv"; OVL=(--overlay-dp "$HERE/kv_planframe/kvattn_rel_dp.sv"); GRADE="$GRADE, plan frame PV_LAND 0 D_QK $DQK"
    cp "$HERE/kv_planframe/tb_kvattn_rel.sv" "$BD/tb_kvattn_rel.sv"
    sed -i 's#"\$B" "\$@" >#"$B" "$@" +DQK='"$DQK"' >#' "$T/tools/qwen_layerbench/kvattn_rel/run.sh"
    grep -q "+DQK=$DQK" "$T/tools/qwen_layerbench/kvattn_rel/run.sh" || { echo "run.sh DQK patch failed"; exit 2; }; fi
  sed -i 's#qkd_kvs_attn_r16\.sv#qkd_kvs_attn_r17.sv#; s#qkd_kvs_attn_fl_r16\.sv#qkd_kvs_attn_fl_r17.sv#' "$SL"
  echo rtl/test/qwen_kv_die/kvattn_rel_1019/kvattn_rel_pv_bound.sv >> "$SL"
  echo "$(cat $SRC/ASM_COMMIT) assembly: current r17 KV attention (qkd_kvs_attn_r17/fl_r17) + bench 0e597ed1c + explicit genuine-archive binding b0cc8cdca (tb sha $(sha256sum $BD/tb_kvattn_rel.sv | cut -c1-16))" > "$O/SOURCE_COMMIT.txt"
  python3 "$HERE/kv_explicit_build.py" --tree "$T" --out "$O" --archives "$EXPL" "${OVL[@]}" > "$O/build.out" 2>&1 || { echo BUILD_FAIL; tail -30 "$O/build.out"; exit 1; }
else
VJOBS=${VJOBS:-2} JOBS=${JOBS:-6} bash "$T/tools/qwen_layerbench/kvattn_rel/build.sh" "$T" "$O" > "$O/build.out" 2>&1 || { echo BUILD_FAIL; tail -30 "$O/build.log"; exit 1; }
fi
bash "$T/tools/qwen_layerbench/kvattn_rel/run.sh" "$T" "$O" > "$O/run.out" 2>&1 || true
python3 "$T/tools/qwen_layerbench/kvattn_rel/collect.py" "$O" "$O/record.json" > "$O/collect.out" 2>&1 || true
python3 "$HERE/stage_kv.collect.py" "$RUNROOT" --out "$O" --grade "$GRADE"
