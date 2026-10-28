#!/bin/bash
# TOK-ALL-17 GB slice composition: fresh extraction on the tok17 manifest (h10 + h9 hard params restored), six-frame
# vectors, merged image dir, one build of tb_dense_gb_slice (+ die return cone), runs: landed / bypass / input mutant /
# swapped-image control.   tok17_gb.sh SRC OUT
set -euo pipefail
SRC=$(realpath "$1"); O=$(realpath -m "$2"); mkdir -p "$O"; cd "$SRC"
export GB_MANIFEST=physical/die_plan/s81/bind/asbuilt_b178_gb_image_candidate_tok17.json
TREE=/srv/opentallas-scratch2/claude/tok-ds-12-1027/veh/tree_b178
FX=/srv/opentallas-scratch2/claude/tok15-gb/fixtures/L0
LP=$TREE/results/arch/s81_dv_1016/landing/p4l/land_plan.json
mkdir -p "$O/asb_sched/work"
if [ ! -f "$O/asb_sched/.done" ]; then
for mv in col_h10:x col_h10:nx col_h9:x col_h9:nx; do m=${mv%%:*}; v=${mv##*:}
  python3 tools/s81_dv/frame_schedule_asb.py --master $m --var $v --manifest "$GB_MANIFEST" \
     --out "$O/ex_${m}_$v" --work "$O/ex_${m}_$v/work" > "$O/ex_${m}_$v.log" 2>&1 &
done; wait
for mv in col_h10:x col_h10:nx col_h9:x col_h9:nx; do m=${mv%%:*}; v=${mv##*:}
  head -1 "$O/ex_${m}_$v.log"; cp "$O/ex_${m}_$v"/*.json "$O/asb_sched/"; cp "$O/ex_${m}_$v/work/${m}_l4_lp_asb_$v.ys" "$O/asb_sched/work/"; done
touch "$O/asb_sched/.done"; fi
export OT_XS_ASB_SCHEDULE_DIR=$O/asb_sched OT_S81_SELECTED_ASBUILT_MANIFEST=$GB_MANIFEST OT_S81_SELECTED_SOURCE_ROOT=$SRC
export OT_S81_SELECTED_CHILD_FILES=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv,rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv
export OT_XS_GB_PROVIDER_UNDER_TEST=1 OT_XS_Q_CPR=1
(cd tools/s81_dv/layer_prog && python3 aproj_native_pair_map.py --tree "$TREE" --fixtures "$FX" --out "$O/capture-map.json")
export OT_XS_APROJ_TOPO=1 OT_XS_APROJ_ALIGN4=1 OT_XS_APROJ_RANK_TAGS=1 OT_XS_DENSE_SPLIT2=B OT_XS_APROJ_CAP_PLAN=1
declare -A MS=([0L01]=col_h10_l4_lp_asb_x [0L02]=col_h9_l4_lp_asb_x [0L03]=col_h9_l4_lp_asb_nx [0R01]=col_h10_l4_lp_asb_x [0R02]=col_h9_l4_lp_asb_x [0R03]=col_h9_l4_lp_asb_nx)
for F in 0L01 0L02 0L03 0R01 0R02 0R03; do (
  rm -rf "$O/vec/u_f_$F"
  python3 tools/s81_dv/layer_prog/lower_xs.py gen --die-src "$TREE" --fixtures "$FX" --slice u_s_0S --frame u_f_$F \
     --out "$O/vec/u_f_$F" --cycles 4000 > "$O/vec_$F.log" 2>&1
  python3 tools/s81_dv/tokfunc/dense_xs_program.py --vectors "$O/vec/u_f_$F" --capture-map "$O/capture-map.json" \
     --die-master ${MS[$F]} --q-calendar native_advance1 >> "$O/vec_$F.log" 2>&1 ) &
done; wait
for F in 0L01 0L02 0L03 0R01 0R02 0R03; do head -1 "$O/vec_$F.log"; done
# merged image dir: frame-independent files must be identical across the six; instance-named images are unioned
python3 - "$O" <<'PY'
import sys, shutil, filecmp, json
from pathlib import Path
o = Path(sys.argv[1]); F = ['0L01','0L02','0L03','0R01','0R02','0R03']; m = o/'vec_slice'; s = o/'vec_swap'
for d in (m, s): shutil.rmtree(d, ignore_errors=True); d.mkdir()
PER = {'ARGS', '_field', 'meta.json', 'dense_program.json', 'frame_schedule.json', 'return_plan.json'}
common = sorted(p.name for p in (o/'vec/u_f_0L01').iterdir() if p.is_file() and not p.name.startswith(('u_f_', 'f_')) and p.name not in PER)
assert {'pq_phase0.viamap.hex', 'pq_stream0.viamap.hex', 'dense_stim.txt', 'capture.hex'} <= set(common), common
for c in common:
    for f in F[1:]:
        assert filecmp.cmp(o/'vec/u_f_0L01'/c, o/f'vec/u_f_{f}'/c, shallow=False), (c, f)
    shutil.copy(o/'vec/u_f_0L01'/c, m/c); shutil.copy(o/'vec/u_f_0L01'/c, s/c)
n = 0
for f in F:
    for p in (o/f'vec/u_f_{f}').glob(f'u_f_{f}_*'):
        shutil.copy(p, m/p.name); n += 1
        # swapped-image control: u_f_0L02 <-> u_f_0R02 images exchanged (same master col_h9_l4_lp_asb_x)
        q = p.name.replace('u_f_0L02', 'TMPX').replace('u_f_0R02', 'u_f_0L02').replace('TMPX', 'u_f_0R02') if f in ('0L02', '0R02') else p.name
        shutil.copy(p, s/q)
print('merged images', n, 'common', common)
PY
# sources: the three masters' exact extracted file sets + XS/CAP/landing set of run_dense_xs_cap_gb.sh + return cone
python3 tools/s81_dv/tokfunc/die_ret_cone.py physical/die_plan/s81/bind/inputs/die_b178.v "$O/ret_cone.sv" 0L01,0L02,0L03,0R01,0R02,0R03 "$LP" > "$O/ret_cone.json"
python3 - "$O/sources.f" "$O/asb_sched/work" "$O/ret_cone.sv" <<'PY'
from pathlib import Path
import re, sys
src = Path('tools/s81_dv/frame_bench.f').read_text().splitlines()
root = str(Path('.').resolve()) + '/'
for y in sorted(Path(sys.argv[2]).glob('*_asb_*.ys')):
    if 'h10_l4_lp_asb_nx' in y.name: continue
    src += [f.replace(root, '').replace('/srv/opentallas-scratch2/claude/wt/claude-tok15-gb-1027/', '') for f in re.findall(r'(\S+\.s?v)\b', y.read_text()) if not f.endswith('.endpoints.sv')]
src += '''rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb.sv
rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv
rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv
rtl/dsrom_sys/s81_dv/land/dsfd_dvland.sv
rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dvh.sv
rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv
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
tools/s81_dv/tokfunc/tb_dense_gb_slice.sv'''.splitlines()
src.append(sys.argv[3])
Path(sys.argv[1]).write_text('\n'.join(dict.fromkeys(s for s in src if s.strip() and not s.startswith('#')))+'\n')
PY
grep -c . "$O/sources.f"
python3 - "$O/sources.f" "$O/sources.json" <<'PY'
import hashlib,json,sys
from pathlib import Path
paths=[Path(s) for s in Path(sys.argv[1]).read_text().splitlines() if not s.startswith('+')]
d={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}
Path(sys.argv[2]).write_text(json.dumps(d,sort_keys=True,indent=2)+'\n')
PY
DEFS=$(python3 -c "import json,sys;print(' '.join('-D'+d for d in json.load(open(sys.argv[1]))['defines']))" "$GB_MANIFEST")
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
if [ ! -x "$O/obj/Vtb_dense_gb_slice" ]; then
/usr/bin/time -v -o "$O/build.time" "$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
   $DEFS --top-module tb_dense_gb_slice -Mdir "$O/obj" -f "$O/sources.f" --build-jobs "${J:-24}" \
   -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > "$O/build.log" 2>&1
fi
T=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["cycles"])' "$O/vec/u_f_0L01/dense_program.json")
B=$O/obj/Vtb_dense_gb_slice
$B +OT_ROM_DIR=$O/vec_slice +T=$T +mut=0 +byp=0 > $O/run_landed.log 2>&1 &
$B +OT_ROM_DIR=$O/vec_slice +T=$T +mut=0 +byp=1 > $O/run_bypass.log 2>&1 &
$B +OT_ROM_DIR=$O/vec_slice +T=$T +mut=1 +byp=0 > $O/run_mut_input.log 2>&1 &
$B +OT_ROM_DIR=$O/vec_swap  +T=$T +mut=0 +byp=0 > $O/run_swapimg.log 2>&1 &
wait
python3 tools/s81_dv/tokfunc/check_gb_slice.py --vec-root $O/vec --run $O || true
