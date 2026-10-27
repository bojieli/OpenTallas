#!/usr/bin/env bash
# TOK-ALL-15 (10-27): GB successor of run_dense_xs_cap.sh. Fleet-only, bounded real selected
# XS4 -> as-built GB frame (col_h10_l4_lp_asb_x, image-bound candidate manifest) -> capc5r_e6 mechanism.
#   run_dense_xs_cap_gb.sh OUT VEC_POS VEC_OLDQ VEC_WRONGIMG [BINARY]
# Runs: positive (native Q advance1 calendar), input-corruption mutant (+mut=1), old-Q-calendar control (VEC_OLDQ),
# wrong-loaded-image control (VEC_WRONGIMG). Checks via check_dense_xs_cap.py --gb.
set -euo pipefail
O=$(realpath -m "$1"); VP=$(realpath "$2"); VQ=$(realpath "$3"); VW=$(realpath "$4")
BINARY=$(realpath -m "${5:-$O/obj/Vtb_dense_xs_cap_gb}")
FRAME=${GB_FRAME:-u_f_0L01}
SCHED=${OT_XS_ASB_SCHEDULE_DIR:?extracted as-built schedule dir required}
mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 - "$O/sources.f" "$SCHED/work/col_h10_l4_lp_asb_x.ys" <<'PY'
from pathlib import Path
import re, sys
src = Path('tools/s81_dv/frame_bench.f').read_text().splitlines()
# exact as-built frame file set the fresh extraction elaborated (endpoint black-box stubs excluded)
ys = Path(sys.argv[2]).read_text()
root = str(Path('.').resolve()) + '/'
src += [f.replace(root, '') for f in re.findall(r'(\S+\.s?v)\b', ys) if not f.endswith('.endpoints.sv')]
src += '''rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb.sv
rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv
rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv
rtl/common/landed_parent/ot_pl_land_n32.sv
rtl/common/landed_parent/ot_pl_land_rst_copy.sv
rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_tr.sv
rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_rt.sv
rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ed.sv
rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ld.sv
rtl/dsrom_sys/s81_dv/slice/cap_end/ot_s81sl_cap_trn.sv
rtl/dsrom_sys/s81_dv/slice/cap_end/ot_s81_retn_fwd.sv
rtl/dsrom_sys/s81_dv/slice/lp/ot_s81sl_capc5r_e6.sv
rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv
rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_stream_rom4_sel.sv
rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs4.sv
physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v
physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
tools/s81_dv/tokfunc/tb_dense_xs_cap_gb.sv'''.splitlines()
Path(sys.argv[1]).write_text('\n'.join(dict.fromkeys(s for s in src if s.strip() and not s.startswith('#')))+'\n')
PY
python3 - "$O/sources.f" "$O/sources.current.json" <<'PY'
import hashlib,json,sys
from pathlib import Path
paths=[Path(s) for s in Path(sys.argv[1]).read_text().splitlines() if not s.startswith('+')]
paths += list(Path('physical/asap7_memory_macros_v2/ot_rom_4096x72_m8').glob('*.vh'))
d={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}
Path(sys.argv[2]).write_text(json.dumps(d,sort_keys=True,indent=2)+'\n')
PY
# exactly the selected (candidate) manifest's defines, as the fresh schedule extraction elaborated
DEFS=$(python3 -c "import json;print(' '.join('-D'+d for d in json.load(open('physical/die_plan/s81/bind/asbuilt_b178_gb_image_candidate_1450.json'))['defines']))")
if [ ! -x "$BINARY" ]; then
    [ "$BINARY" = "$O/obj/Vtb_dense_xs_cap_gb" ] || { echo 'External binary missing' >&2; exit 3; }
    /usr/bin/time -v -o "$O/build.time" "$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
        -Wno-lint -Wno-style -Wno-MULTIDRIVEN $DEFS "-DGB_FRAME=\"$FRAME\"" \
        --top-module tb_dense_xs_cap_gb -Mdir "$O/obj" -f "$O/sources.f" --build-jobs "${J:-8}" \
        -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > "$O/build.log" 2>&1
    cp "$O/sources.current.json" "$O/sources.compiled.json"
fi
python3 - "$BINARY" "$O" "$VP" "$VQ" "$VW" <<'PY'
import hashlib,json,sys
from pathlib import Path
binary,o=map(Path,sys.argv[1:3])
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
d=dict(binary=str(binary),binary_sha256=sha(binary),compiled_source_identity=json.loads((o/'sources.compiled.json').read_text()),
       vectors={Path(v).name:{p.name:sha(p) for p in sorted(Path(v).glob('*')) if p.is_file()} for v in sys.argv[3:]},
       driving_tools={s:sha(Path('tools/s81_dv/tokfunc')/s) for s in ('run_dense_xs_cap_gb.sh','dense_xs_program.py','check_dense_xs_cap.py','tb_dense_xs_cap_gb.sv')},
       uniform_clock_phase=True,full_stage=False,full_token=False)
(o/'run_identity.json').write_text(json.dumps(d,indent=2)+'\n')
PY
T=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["cycles"])' "$VP/dense_program.json")
"$BINARY" +OT_ROM_DIR="$VP" +T="$T" +mut=0 > "$O/run_mut0.log" 2>&1 || true
"$BINARY" +OT_ROM_DIR="$VP" +T="$T" +mut=1 > "$O/run_mut1.log" 2>&1 || true
"$BINARY" +OT_ROM_DIR="$VQ" +T="$T" +mut=0 > "$O/run_oldq.log" 2>&1 || true
"$BINARY" +OT_ROM_DIR="$VW" +T="$T" +mut=0 > "$O/run_wrongimg.log" 2>&1 || true
python3 tools/s81_dv/tokfunc/check_dense_xs_cap.py --vectors "$VP" --run "$O" --gb --oldq-vectors "$VQ" --wrongimg-vectors "$VW"
