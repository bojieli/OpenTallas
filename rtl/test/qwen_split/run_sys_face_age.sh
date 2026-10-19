#!/bin/bash
# Q-NETLIST 2026-10-16: compute-die system face bench (tb_qfd_sys_face.sv).  usage: run_sys_face_bench.sh OUTDIR [MUT ...]
# Builds the config-ROM image from sys_face_bench_events.json (+ the compute end's D2D calendars of the dies_token
# sequencer's compiled starts), the expected-event include, then runs MUT 0 (must PASS) and every listed mutant (default 1 2 3 4 5, must FAIL).
set -eu
OUT=$(mkdir -p "$1" && readlink -f "$1"); shift
MUTS=0
R=$(cd "$(dirname "$0")/../../.." && pwd)
# MU-DQ-SYSFACE 10-19: D2D_MU=1 = the MU release build (qfd_sys_face MU kit): the D2D sequencer source is
# ot_qwen_d2d_cal_seq_dies_mu.sv with the MU image d2d_cal_image_mu.svh (+ the token-run MU context slot), the face and the
# bench #(MU 1) (filler head contexts, check 7; mutants 6 / 7 must FAIL); default = MU 0.
DIMG=d2d_cal_image.svh; DSEQ=ot_qwen_d2d_cal_seq_dies.sv
if [ "${D2D_MU:-0}" = 1 ]; then DIMG=d2d_cal_image_mu.svh; DSEQ=ot_qwen_d2d_cal_seq_dies_mu.sv; fi
export DIMG
# production token timeline: the D2D sequencer's compiled starts (d2d_cal_image.svh) + the bench layer / row events
python3 - $R $OUT <<'PY'
import json, re, sys
R, OUT = sys.argv[1], sys.argv[2]
b = json.load(open(f'{R}/rtl/test/qwen_split/sys_face_bench_events.json'))
v = int(re.search(r"D2D_CAL_START = 720'h([0-9a-f]+)", open(f'{R}/rtl/qwen_sys/d2d_static_20261015/'+__import__('os').environ['DIMG']).read()).group(1), 16)
st = [(v >> (20 * l)) & ((1 << 20) - 1) for l in range(36)]
img = open(f'{R}/rtl/qwen_sys/d2d_static_20261015/'+__import__('os').environ['DIMG']).read()
iv = lambda n: int(re.search(rf'{n} = (\d+)', img).group(1))
PERIOD, FIRST = iv('D2D_TOKEN_PERIOD'), iv('D2D_FIRST_TOKEN')
C0, L0, EMB = b['go_ofs'], b['l0_start'], b['emb_stage']
TOK = PERIOD - 40 - C0                    # LM-head stage + RESULT capture 40 edges before the compiled END
T = [(C0, 5, 128), (C0 + EMB, 0, 0), (C0 + L0, 0, 1 | 64), (C0 + L0 + 2, 1, 3)]
T += [(C0 + st[l], 0, (l + 1) | 64) for l in range(1, 36)]
T += [(C0 + TOK, 0, 37 | 256), (PERIOD, 1, 4)]  # END at the compiled token period (D2D_TOKEN_PERIOD)
ev = dict(first_token=FIRST - C0,  # t_go edges after the strobe: the token cal_start lands at D2D_FIRST_TOKEN
          d2d_first_token=FIRST, d2d_adm_ofs=iv('D2D_ADM_OFS'), T=T, L=b['L'], E=b['E'], go_ofs=C0, cal=[(C0, 1)] + [(C0 + st[l], 0) for l in range(1, 36)])
json.dump(ev, open(f'{OUT}/events.json', 'w'))
PY
python3 $R/tools/qwen_split/sys_face_image.py --events $OUT/events.json --bench-program --d2d-image $R/rtl/qwen_sys/d2d_static_20261015/$DIMG --out $OUT/img > $OUT/img.json
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
hdr = (f'localparam integer GO_OFS = {ev["go_ofs"]}, TOKEN_PERIOD = {end_c}, '
       f'ADM_TO_TOKEN = {ev["d2d_first_token"] - ev["d2d_adm_ofs"]};')
open(sys.argv[2], 'w').write('\n'.join([hdr, 'initial begin'] + [f'    add({c}, {k}, {a});' for c, k, a in out] + ['end', '']))
PY
# Icarus 11 has no typed string parameters: the bench compiles a copy of the ROM model with untyped ones
sed 's/parameter string /parameter /g' $R/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v > $OUT/ot_rom_4096x72_m8.v

V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version > "$OUT/verilator.txt";grep -q 5.050 "$OUT/verilator.txt"
"$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -I"$OUT" -I"$R/rtl/qwen_sys/d2d_static_20261015" --top-module tb_qfd_sys_face_age -GMU=1 -GIMG=\"$OUT/img\" --Mdir "$OUT/obj" \
 "$R/rtl/qwen_split/qfd_sys_face.sv" "$R/rtl/qwen_split/qfd_embedding_word_provider.sv" \
 "$R/rtl/qwen_split/qfd_sys_face_accepted_mu_ctx.sv" \
 "$R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv" \
 "$R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq.sv" "$R/rtl/qwen_sys/d2d_static_20261015/$DSEQ" \
 "$R/rtl/qwen_split/qfd_sys_face_record_port.sv" \
 "$R/rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv" \
 "$R/rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv" \
 "$R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_preload_face.sv" \
 "$R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_core_store.sv" \
 "$R/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v" \
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" \
 "$R/rtl/test/qwen_split/tb_qfd_sys_face_age.sv" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_qfd_sys_face_age" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
grep -q SYS_FACE_PASS "$OUT/run.log"
