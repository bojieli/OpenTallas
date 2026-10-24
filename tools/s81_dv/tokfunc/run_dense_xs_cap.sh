#!/usr/bin/env bash
# Fleet-only, bounded real selected XS4/frame/CAP producer mechanism.
set -euo pipefail
O=$(realpath -m "$1")
VD=$(realpath "$2")
BINARY=$(realpath -m "${3:-$O/obj/Vtb_dense_xs_cap}")
PIN_DIR=$(dirname "$(dirname "$BINARY")")
mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=rtl/dsrom_sys/s81_dv/slice
python3 - "$O/sources.f" <<'PY'
from pathlib import Path
import sys
src=Path('tools/s81_dv/frame_bench.f').read_text().splitlines()
src += '''rtl/dsrom_sys/s81_dv/frame_lp/col_h9_l4_lp.sv
rtl/dsrom_sys/s81_dv/frame_lp/col_h9_l4_lp_b.sv
rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv
rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv
rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv
rtl/common/landed_parent/ot_pl_land.sv
rtl/common/landed_parent/ot_pl_land_n32.sv
rtl/common/landed_parent/ot_pl_land_rst_copy.sv
rtl/common/landed_parent/ot_pl_land_reset_forest.sv
rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_tr.sv
rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_rt.sv
rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ed.sv
rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ld.sv
rtl/dsrom_sys/s81_dv/slice/lp/ot_s81sl_capc5r.sv
rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv
rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_stream_rom4_sel.sv
rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs4.sv
physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v
physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
tools/s81_dv/tokfunc/tb_dense_xs_cap.sv'''.splitlines()
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
if [ -x "$BINARY" ]; then
    python3 - "$O/sources.current.json" "$PIN_DIR/sources.compiled.json" "$(dirname "$BINARY")/Vtb_dense_xs_cap__verFiles.dat" <<'PY'
import json,shlex,sys
from pathlib import Path
current=json.loads(Path(sys.argv[1]).read_text())
compiled=json.loads(Path(sys.argv[2]).read_text())
bad=[p for p,h in current.items() if compiled.get(p)!=h]
assert not bad, 'binary source identity differs: '+str(bad)
line=next(l for l in Path(sys.argv[3]).read_text().splitlines() if l.startswith('C '))
cmd=shlex.split(shlex.split(line)[1])
assert all(x in cmd for x in ('--timing','-DLK=2','-DDSFD_PQ_STATIC_X2','-DDSFD_PQ_HAS_BF_X2'))
assert {x for x in cmd if x.startswith(('-D','+define+'))} == {'-DLK=2','-DDSFD_PQ_STATIC_X2','-DDSFD_PQ_HAS_BF_X2'}
assert not any(x.startswith('-G') for x in cmd), 'unexpected top parameter override'
assert cmd[cmd.index('--top-module')+1]=='tb_dense_xs_cap'
PY
fi
if [ ! -x "$BINARY" ]; then
    [ "$BINARY" = "$O/obj/Vtb_dense_xs_cap" ] || { echo 'External binary missing' >&2; exit 3; }
    /usr/bin/time -v -o "$O/build.time" "$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
        -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DDSFD_PQ_STATIC_X2 -DDSFD_PQ_HAS_BF_X2 -DLK=2 \
        --top-module tb_dense_xs_cap -Mdir "$O/obj" -f "$O/sources.f" --build-jobs "${J:-2}" \
        -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > "$O/build.log" 2>&1
    cp "$O/sources.current.json" "$O/sources.compiled.json"
fi
python3 - "$BINARY" "$VD" "$O" "$PIN_DIR/sources.compiled.json" <<'PY'
import hashlib,json,sys
from pathlib import Path
binary,v,o,pins=map(Path,sys.argv[1:])
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
d=dict(binary=str(binary),binary_sha256=sha(binary),compiled_source_identity=json.loads(pins.read_text()),
       vector_files={p.name:sha(p) for p in sorted(v.glob('*')) if p.is_file()},
       driving_tools={s:sha(Path('tools/s81_dv/tokfunc')/s) for s in ('run_dense_xs_cap.sh','dense_xs_program.py','check_dense_xs_cap.py')},
       full_stage=False,full_token=False)
(o/'run_identity.json').write_text(json.dumps(d,indent=2)+'\n')
PY
T=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["cycles"])' "$VD/dense_program.json")
for m in 0 1; do
    "$BINARY" +OT_ROM_DIR="$VD" +T="$T" +mut="$m" > "$O/run_mut$m.log" 2>&1
done
python3 tools/s81_dv/tokfunc/check_dense_xs_cap.py --vectors "$VD" --run "$O"
