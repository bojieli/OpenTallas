#!/bin/bash
# DIE-QC-93 11-08: NK form vR8a = vR7 (same proved mapped netlist 1_2_yosys.v / 1_synth, same pins, same RTL)
# with ONLY macro sites moved (core-internal, no interface change; pins/RTL/netlist unchanged): a continuous WEST N-S channel
# (top 42.3 um beside the node, was 21.6; bottom 44.7 um, was 5) and romleaf col0 MY->R0 so its 5x530 pins face that west
# channel instead of the central spine (bottom central 44.8 um now serves col1 only). rawE + clock entry (228.97,578.88) unchanged.
# x shifts are multiples of 1.728 um (site 0.054 x M4/M6 0.192 lcm).
set -euo pipefail
S=/srv/opentallas-scratch2/claude/dq92/qfd_tile_nk_a0c_vR7
K=/srv/opentallas-scratch2/claude/dq93/qfd_tile_nk_a0c_vR8a
[ ! -e $K ] || { echo "exists"; exit 3; }
mkdir -p $K
rsync -a --exclude run --exclude 'run_resume_*.log' --exclude signoff --exclude signoff.log $S/ $K/
B=run/results/asap7/kq_qfd_tile_nk_a0c_vR7/base
mkdir -p $K/$B $K/run/logs/asap7/kq_qfd_tile_nk_a0c_vR7/base $K/run/reports/asap7/kq_qfd_tile_nk_a0c_vR7/base
for f in 1_1_yosys_canonicalize.rtlil 1_2_yosys.sdc 1_2_yosys.v 1_synth.odb 1_synth.sdc 1_synth.v clock_period.txt mem.json ot_face_flops.txt ot_rst_copies.tsv ot_rst_copies.ys ot_rst_copies_prep.ys ot_unreg_pins.txt; do cp -p $S/$B/$f $K/$B/; done
cp -p $S/run/logs/asap7/kq_qfd_tile_nk_a0c_vR7/base/1_* $K/run/logs/asap7/kq_qfd_tile_nk_a0c_vR7/base/ 2>/dev/null || true
cp $K/macro_place.tcl $K/macro_place.pre_vR8a.tcl
python3 -I - $K/macro_place.tcl <<'PY'
import re,sys
p=sys.argv[1]; t=open(p).read()
# (name regex, old x, dx)
moves=[(r"g_ndh\.u_node",25.92,20.736),
       (r"g_sl\[(1|3|5|6)\]\.g_hd\.u_lh\.u_native_rawleaf",86.4,20.736),
       (r"g_sl\[(0|2|4|7)\]\.g_hd\.u_lh\.u_native_rawleaf",299.856,0.0),
       (r"g_col\[0\]\.u_leaf",9.288,39.744),
       (r"g_col\[1\]\.u_leaf",261.408,5.184)]
blocks=t.split("set hit {}")
n=0
for i,b in enumerate(blocks):
    for rx,x0,dx in moves:
        m=re.search(r'puts "hard child (\S+) ->',b)
        if m and re.search(rx,m.group(1)):
            x1=round(x0+dx,3)
            if dx==0.0: n+=1; continue
            if "g_col[0]" in m.group(1):
                assert b.count("$i setOrient MY")==1; b=b.replace("$i setOrient MY","$i setOrient R0").replace(" MY at "," R0 at ")
            old=f"round({x0} * $dbu)"
            assert b.count(old)==1,(m.group(1),old)
            b=b.replace(old,f"round({x1} * $dbu)").replace(f" at {x0} "," at %s "%x1)
            blocks[i]=b; n+=1
assert n==19,n
open(p,"w").write("set hit {}".join(blocks)+"")
print("moved",n)
PY
echo "$(date) DIE-QC-93 vR8a: macro x-sites only (see mk_vr8a.sh); from vR7 dq92 kit; mapped netlist sha $(sha256sum $K/$B/1_2_yosys.v | cut -c1-16)" >> $K/vR8a_FORM.txt
grep "^puts \"hard child" $K/macro_place.tcl | sed -E 's/.*logic\.([^ ]*) -> .* ([A-Z0-9]+) at ([0-9.]+) ([0-9.]+).*/\1 \2 \3 \4/'
