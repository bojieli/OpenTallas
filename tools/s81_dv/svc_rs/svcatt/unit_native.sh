#!/bin/bash
# usage: run.sh SRCROOT OUT TOP DEFINES...
set -e
S=$1; O=$2; T=$3; shift 3; DEF="$*"
LIB=/srv/opentallas-scratch/claude/elemsvc-g4-1021/out_norst/map/lib
mkdir -p $O
cat > $O/map.ys <<YS
read_liberty -lib /tmp/lib/SIMPLE.lib
read_liberty -lib /tmp/lib/AO.lib
read_liberty -lib /tmp/lib/OA.lib
read_liberty -lib /tmp/lib/INVBUF.lib
read_liberty -lib /tmp/lib/SEQ.lib
read_verilog -defer -sv -DSYNTHESIS $DEF /src/rtl/hdc/ot_hdc_fp32_f12.sv /src/rtl/hdc/ot_hdc_fastfp.sv /src/rtl/hdc/ot_hdc_prefix.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv /src/rtl/hdc/v41x/ot_hdc_v41x_kreg.sv /exp/wrap.sv $EXTRA
hierarchy -check -top $T
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top $T -flatten -noshare
dfflibmap -liberty /tmp/lib/SEQ.lib
abc -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
opt_clean
setattr -mod -unset keep_hierarchy
flatten
opt_clean
tee -o /out/stat.txt stat -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
write_verilog -noattr /out/flat.v
write_json /out/flat.json
YS
docker run --rm -v "$S:/src:ro" -v "$(dirname $0):/exp:ro" -v "$O:/out" -v "$LIB:/tmp/lib:ro" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -l /out/synth.log -s /out/map.ys' > $O/build.log 2>&1
args=(); for f in $LIB/*.lib; do args+=(--liberty $f); done
python3 /srv/opentallas-scratch/claude/svcatt-1021/tools/ref_tile/native_census.py --netlist $O/flat.v --top $T --out $O/census.json "${args[@]}" > $O/census.log 2>&1 || true
python3 /srv/opentallas-scratch/claude/svcatt-1021/attrib.py $O/flat.v $O/census.json $O/attrib.json > $O/attrib.log 2>&1 || true
python3 -c "import json;r=json.load(open('$O/census.json'));print('$T',r['status'],r['max_dynamic_loads'],r['violations'] if isinstance(r['violations'],int) else len(r['violations']))"
