#!/usr/bin/env bash
# HEAD tail publisher (option A) gate: lockstep bench (raw rc14 vs rc16 TAILPUB 0/1 + 5 mutants) over genuine and
# synthetic HEAD contexts, then the yosys FF census.  Run inside the packet made by prepare_head_tailpub_gate.sh.
set -euo pipefail
cd "$(dirname "$0")"
export OBJCACHE=${OBJCACHE-}   # no ccache in the bench container
sha256sum -c SHA256SUMS > hash_guard.log
MODE=${1:-all}
JOBS=${JOBS:-8}
TIME=(); if [[ -x /usr/bin/time ]]; then TIME=(/usr/bin/time -v); fi
if [[ $MODE == all || $MODE == bench ]]; then
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version | tee compiler_version.log
"${TIME[@]}" "$VL" --binary --timing -O0 -finline --output-groups 16 -j "$JOBS" --build-jobs "$JOBS" -CFLAGS '-O0 -w -fno-var-tracking' \
 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_head_tailpub_lockstep \
 -f source.f ref_part.sv native_head_rom_return_cut.sv tb_head_tailpub_lockstep.sv --Mdir obj > build.log 2>&1
: > results.tsv
caught=0
run(){ # dir scen tile gold expect_raw expect_pub [op1_raw op1_pub]
 local d=$1 s=$2 t=$3 g=$4 er=$5 ep=$6 log
 log=$PWD/contexts/$d/scen${s}_tile${t}.log
 (cd "contexts/$d" && "$OLDPWD/obj/Vtb_head_tailpub_lockstep" +SCEN=$s +TILE=$t +GOLD=$g > "$log" 2>&1)
 grep -q "PASS_TAILPUB_LOCKSTEP scen=$s tile=$t .* raw=$er published=$ep " "$log"
 if [[ $# -gt 6 ]]; then grep -q "op1=$8/$7 " "$log"; fi
 local m; m=$(sed -n 's/.*mutants_caught=\([01]*\).*/\1/p' "$log"); caught=$((caught | 2#$m))
 local rb; rb=$(sed -n 's/.*raw_publisher_contract_mismatches=\([0-9]*\).*/\1/p' "$log")
 printf '%s\t%s\t%s\traw=%s\tpub=%s\tmutants=%s\traw_publisher_mismatch=%s\n' "$d" "$s" "$t" "$er" "$ep" "$m" "$rb" | tee -a results.tsv
}
run tile639 1 639 1 64 24          # q4 block148 genuine: 3 per K
run tile639 1 512 0 64 24          # q4 first tile
run tile639 1 700 0 64 0           # q5 (block149 absent): none
run tile639 1 767 0 64 0           # q5 last tile
run tile639 1 0   0 64 64          # q0 last chunk: all rows < 560
run tile639 1 384 0 64 64          # q3: rows 384..511 < 560
run tile639 4 639 0 64 64          # outside the HEAD lease: raw
run tile639 4 700 0 64 64          # outside the HEAD lease, q5: raw
run tile639 3 639 0 512 512        # full chunk nout 6144, 8 rounds
run tile639 5 639 0 576 536 64 24  # early GO: full chunk then the last chunk on first ready
run tile639 5 700 0 576 512 64 0   # early GO, q5
run tile0   2 0   1 64 64          # genuine q0 block0 context
run tile0   3 0   0 512 512
printf 'MUTANTS_CAUGHT_UNION=%s (m5..m1 bits, 31 = all)\n' "$caught" | tee -a results.tsv
test "$caught" -eq 31
grep -q $'tile639\t1\t639\t.*raw_publisher_mismatch=40' results.tsv
grep -q $'tile639\t1\t700\t.*raw_publisher_mismatch=64' results.tsv
echo PASS_HEAD_TAILPUB_BENCH | tee -a results.tsv
fi
if [[ $MODE == all || $MODE == ff ]]; then
Y=${YOSYS:-$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys}
for v in rc14:src_rc14_part1.sv: rc16tp0:src/015_ot_qwen_w12_matvec_land32_tailpub.sv:-DFF_TP=0 rc16tp1:src/015_ot_qwen_w12_matvec_land32_tailpub.sv:-DFF_TP=1; do
 IFS=: read -r name part def <<< "$v"
 sed -e "s#@PART1@#$part#" -e "s#@DEF@#$def#" -e "s#@OUT@#stat_$name.txt#" head_tailpub_ffcount.ys > ff_$name.ys
 "${TIME[@]}" "$Y" -q -l yosys_$name.log ff_$name.ys > /dev/null 2> time_$name.log
done
echo PASS_HEAD_TAILPUB_FF
fi
