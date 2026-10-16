#!/bin/bash
# Q-NETLIST 2026-10-16: compute-die system face bench (tb_qfd_sys_face.sv).  usage: run_sys_face_bench.sh OUTDIR [MUT ...]
# Builds the config-ROM image from sys_face_bench_events.json (+ the compute end's D2D calendars of the dies_token
# profile), the expected-event include, then runs MUT 0 (must PASS) and every listed mutant (default 1 2 3, must FAIL).
set -eu
OUT=$(mkdir -p "$1" && readlink -f "$1"); shift
MUTS=${*:-1 2 3}
R=$(cd "$(dirname "$0")/../../.." && pwd)
python3 $R/tools/qwen_split/d2d_link_calendar.py --out $OUT/d2d --txl 6 --profile dies_token > $OUT/d2d.json
python3 $R/tools/qwen_split/sys_face_image.py --events $R/rtl/test/qwen_split/sys_face_bench_events.json --bench-program \
    --d2d-dir $OUT/d2d --out $OUT/img > $OUT/img.json
python3 - $R/rtl/test/qwen_split/sys_face_bench_events.json $OUT/tb_qfd_sys_face_events.svh <<'PY'
import json, sys
ev = json.load(open(sys.argv[1]))
out, lev = [], [0, 0]
T = sorted(ev['T']); L = sorted(ev['L']); E = sorted(ev['E'])
timeline = []
for c, k, a in T:
    if k == 0:
        timeline.append((c, 0, a & 0xff))
        if a & 256: timeline.append((c, 9, 0))
        if a & 64: timeline += [(c + cl, kl, al) for cl, kl, al in L]
        if a & 128: timeline += [(c + ce, ke, ae) for ce, ke, ae in E]
    else:
        timeline.append((c, 1, a))
for c, k, a in sorted(timeline):
    if k == 1:
        new = [a & 1, (a >> 1) & 1]
        if new != lev: out.append((c, 1, new[0] | new[1] << 1))
        lev = new
    else:
        out.append((c, k, a))
open(sys.argv[2], 'w').write('initial begin\n' + ''.join(f'    add({c}, {k}, {a});\n' for c, k, a in out) + 'end\n')
PY
# Icarus 11 has no typed string parameters: the bench compiles a copy of the ROM model with untyped ones
sed 's/parameter string /parameter /g' $R/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v > $OUT/ot_rom_4096x72_m8.v
F="$R/rtl/qwen_split/qfd_sys_face.sv $R/rtl/qwen_split/qfd_embedding_word_provider.sv
   $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv
   $R/rtl/qwen_sys/context_transport_20261014/qfd_program_record_port.sv
   $R/rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv
   $R/rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv
   $R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_preload_face.sv
   $R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_core_store.sv
   $OUT/ot_rom_4096x72_m8.v
   $R/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
   $R/rtl/test/qwen_split/tb_qfd_sys_face.sv"
rc=0
for M in 0 $MUTS; do
    iverilog -g2012 -s tb_qfd_sys_face -I $OUT -Ptb_qfd_sys_face.MUT=$M -Ptb_qfd_sys_face.IMG=\"$OUT/img\" -o $OUT/sim_$M $F
    (cd $OUT && vvp -n sim_$M > run_$M.log 2>&1) || true
    L=$(grep -E "SYS_FACE_(PASS|FAIL)" $OUT/run_$M.log | tail -1); echo "$L"
    if [ $M = 0 ]; then case "$L" in SYS_FACE_PASS*) ;; *) rc=1;; esac
    else case "$L" in SYS_FACE_FAIL*) ;; *) rc=1;; esac; fi
done
exit $rc
