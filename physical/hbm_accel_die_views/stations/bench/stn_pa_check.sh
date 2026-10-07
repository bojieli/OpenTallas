#!/bin/bash
# stn_pa_check.sh <view.lef> <master> <work dir>: die pin-access pre-check of an exported view LEF (coordinator ask
# 2026-10-06 after r8 DRT-0073): four instances at R0 / MX / MY / R180 on a 1.296 um lattice, every pin on its own net,
# then OpenROAD pin_access (M2-M9).  Prints OT_PA DONE|FAIL and the DRT-0073 count; rc 0 only when DONE with 0 DRT-0073.
set -o pipefail
L=$(readlink -f $1); m=$2; W=$(readlink -f -m $3); mkdir -p $W; cp $L $W/view.lef
python3 - $W/view.lef $m $W <<'P'
import re, sys
lef, m, w = sys.argv[1:4]
t = open(lef).read()
mt = re.search(r'MACRO\s+' + re.escape(m) + r'\s(.*?)\nEND\s+' + re.escape(m), t, re.S).group(1)
sx, sy = map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', mt).groups())
pins = [p for p in re.findall(r'^\s*PIN\s+(\S+)', mt, re.M)]
blk = dict(re.findall(r'^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$', mt, re.S | re.M))
sig = [p for p in pins if not re.search(r'USE\s+(POWER|GROUND)', blk.get(p, ''))]
g = 1.296
def up(v): return round(-(-v // g) * g, 3)
ox, oy = up(sx + 20), up(sy + 20)
esc = lambda p: '\\' + p + ' ' if '[' in p else p
bus = {}
for p in sig:
    mm = re.match(r'(.+)\[(\d+)\]$', p)
    b, i = (mm.group(1), int(mm.group(2))) if mm else (p, None)
    bus.setdefault(b, []).append(i)
v = ['module pa_top();']
pl = []
for k, (o, x, y) in enumerate([('R0', 10.368, 10.368), ('MX', 10.368 + ox, 10.368), ('MY', 10.368, 10.368 + oy), ('R180', 10.368 + ox, 10.368 + oy)]):
    con = []
    for j, (b, ix) in enumerate(sorted(bus.items())):
        if ix == [None]:
            v.append(f'  wire n{k}_{j};'); con.append(f'.{b}(n{k}_{j})')
        else:
            v.append(f'  wire [{max(ix)}:0] n{k}_{j};'); con.append(f'.{b}(n{k}_{j})')
    v.append(f'  {m} u{k} (' + ', '.join(con) + ');')
    pl.append(f'place_inst -name u{k} -location {{{x} {y}}} -orientation {o} -status FIRM')
v.append('endmodule')
open(f'{w}/pa.v', 'w').write('\n'.join(v) + '\n')
dx, dy = up(10.368 * 2 + 2 * ox), up(10.368 * 2 + 2 * oy)
open(f'{w}/pa.tcl', 'w').write(f'''read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/view.lef
read_verilog /work/pa.v
link_design pa_top
initialize_floorplan -die_area {{0 0 {dx} {dy}}} -core_area {{0 0 {dx} {dy}}} -site asap7sc7p5t
source /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
''' + '\n'.join(pl) + '''
set_routing_layers -signal M2-M9
if {[catch {pin_access -verbose 1} err]} { puts "OT_PA FAIL $err" } else { puts "OT_PA DONE" }
exit
''')
P
docker run --rm -u $(id -u):$(id -g) -v $W:/work openroad/orfs:asap7lock bash -c "cd /work && /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit pa.tcl" > $W/pa.log 2>&1
n=$(grep -c "DRT-0073" $W/pa.log); r=$(grep -o "OT_PA [A-Z]*" $W/pa.log | head -1)
echo "$m ${r:-OT_PA NONE} DRT0073=$n"
[ "$r" = "OT_PA DONE" ] && [ $n -eq 0 ]
