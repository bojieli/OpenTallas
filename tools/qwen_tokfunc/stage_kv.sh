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
NET=""
while [ $# -gt 0 ]; do case "$1" in --die-netlist) NET=$(readlink -f "$2"); shift 2;; *) echo "bad arg $1"; exit 2;; esac; done
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
VJOBS=${VJOBS:-2} JOBS=${JOBS:-6} bash "$T/tools/qwen_layerbench/kvattn_rel/build.sh" "$T" "$O" > "$O/build.out" 2>&1 || { echo BUILD_FAIL; tail -30 "$O/build.log"; exit 1; }
bash "$T/tools/qwen_layerbench/kvattn_rel/run.sh" "$T" "$O" > "$O/run.out" 2>&1 || true
python3 "$T/tools/qwen_layerbench/kvattn_rel/collect.py" "$O" "$O/record.json" > "$O/collect.out" 2>&1 || true
python3 "$HERE/stage_kv.collect.py" "$RUNROOT" --out "$O" --grade "$GRADE"
