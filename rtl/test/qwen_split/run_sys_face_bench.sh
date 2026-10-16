#!/bin/bash
# Q-NETLIST 2026-10-16: compute-die system face bench (tb_qfd_sys_face.sv).  usage: run_sys_face_bench.sh OUTDIR [MUT ...]
# Builds the config-ROM image from sys_face_bench_events.json (+ the compute end's D2D calendars of the dies_token
# sequencer's compiled starts), the expected-event include, then runs MUT 0 (must PASS) and every listed mutant (default 1 2 3, must FAIL).
set -eu
OUT=$(mkdir -p "$1" && readlink -f "$1"); shift
MUTS=${*:-1 2 3 4}
R=$(cd "$(dirname "$0")/../../.." && pwd)
# production token timeline: the D2D sequencer's compiled starts (d2d_cal_image.svh) + the bench layer / row events
python3 - $R $OUT <<'PY'
import json, re, sys
R, OUT = sys.argv[1], sys.argv[2]
b = json.load(open(f'{R}/rtl/test/qwen_split/sys_face_bench_events.json'))
v = int(re.search(r"D2D_CAL_START = 720'h([0-9a-f]+)", open(f'{R}/rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh').read()).group(1), 16)
st = [(v >> (20 * l)) & ((1 << 20) - 1) for l in range(36)]
C0, L0, EMB, TOK = b['go_ofs'], b['l0_start'], b['emb_stage'], b['token_cycles']
T = [(C0, 5, 128), (C0 + EMB, 0, 0), (C0 + L0, 0, 1 | 64), (C0 + L0 + 2, 1, 3)]
T += [(C0 + st[l], 0, (l + 1) | 64) for l in range(1, 36)]
T += [(C0 + TOK, 0, 37 | 256), (C0 + TOK + 30, 1, 4)]
ev = dict(first_token=b['first_token'], T=T, L=b['L'], E=b['E'], go_ofs=C0, cal=[(C0, 1)] + [(C0 + st[l], 0) for l in range(1, 36)])
json.dump(ev, open(f'{OUT}/events.json', 'w'))
PY
python3 $R/tools/qwen_split/sys_face_image.py --events $OUT/events.json --bench-program --out $OUT/img > $OUT/img.json
python3 - $OUT/events.json $OUT/tb_qfd_sys_face_events.svh <<'PY'
import json, sys
ev = json.load(open(sys.argv[1]))
out, lev, timeline = [], [0, 0], []
for c, k, a in sorted(ev['T']):
    if k in (0, 5):
        if k == 0: timeline.append((c, 0, a & 63))
        if a & 256: timeline.append((c, 9, 0))
        if a & 64: timeline += [(c + cl, kl, al) for cl, kl, al in ev['L']]
        if a & 128: timeline += [(c + ce, ke, ae) for ce, ke, ae in ev['E']]
    else:
        timeline.append((c, 1, a))
timeline += [(c, 10, seg) for c, seg in ev['cal']]
for c, k, a in sorted(timeline):
    if k == 1:
        new = [a & 1, (a >> 1) & 1]
        if new != lev: out.append((c, 1, new[0] | new[1] << 1))
        lev = new
    else:
        out.append((c, k, a))
end_c = max(c for c, k, a in ev['T'] if k == 1 and a & 4)
hdr = f'localparam integer GO_OFS = {ev["go_ofs"]}, TOKEN_PERIOD = {end_c};'
open(sys.argv[2], 'w').write('\n'.join([hdr, 'initial begin'] + [f'    add({c}, {k}, {a});' for c, k, a in out] + ['end', '']))
PY
# Icarus 11 has no typed string parameters: the bench compiles a copy of the ROM model with untyped ones
sed 's/parameter string /parameter /g' $R/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v > $OUT/ot_rom_4096x72_m8.v
F="$R/rtl/qwen_split/qfd_sys_face.sv $R/rtl/qwen_split/qfd_embedding_word_provider.sv
   $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv
   $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq.sv $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq_dies.sv
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
    iverilog -g2012 -s tb_qfd_sys_face -I $OUT -I $R/rtl/qwen_sys/d2d_static_20261015 -Ptb_qfd_sys_face.MUT=$M -Ptb_qfd_sys_face.IMG=\"$OUT/img\" -o $OUT/sim_$M $F
    (cd $OUT && vvp -n sim_$M > run_$M.log 2>&1) || true
    L=$(grep -E "SYS_FACE_(PASS|FAIL)" $OUT/run_$M.log | tail -1); echo "$L"
    if [ $M = 0 ]; then case "$L" in SYS_FACE_PASS*) ;; *) rc=1;; esac
    else case "$L" in SYS_FACE_FAIL*) ;; *) rc=1;; esac; fi
done
exit $rc
