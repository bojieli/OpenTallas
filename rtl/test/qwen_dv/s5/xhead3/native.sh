#!/bin/bash
# Pre-gate native census of qfd_dv_s5_xhead3: ORFS-image yosys (the gate's synthesis + the kept-register hook
# physical/common_flow/ot_keep_regs.tcl), ASAP7 RVT TT mapping, then tools/ref_tile/native_census.py (the gate's
# mandatory <=32 census) and tools/textbook_lint.py (stage depth ps / levels, boundary levels).
#   bash rtl/test/qwen_dv/s5/xhead3/native.sh OUT [TOP]      (run from the source root, on a fleet host with docker)
set -euo pipefail
O=$1; TOP=${2:-qfd_dv_s5_xhead3}; mkdir -p "$O"
IMG=${OT_ORFS_IMG:-openroad/orfs:asap7lock}
SRCS="rtl/lib/ot_rst_relay.sv rtl/qwen_dv/s5/qfd_dv_s5_xhead3.sv"
[ "$TOP" = qfd_dv_s5_xhead ] && SRCS="rtl/lib/ot_rst_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv"
cat > "$O/synth.tcl" <<TCL
set NL /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
yosys read_liberty -lib /src/$O/cells.lib
yosys read_verilog -sv -DSYNTHESIS $SRCS
yosys hierarchy -check -top $TOP
set ::env(DESIGN_NAME) $TOP
source physical/common_flow/ot_keep_regs.tcl
yosys synth -top $TOP -flatten
yosys dfflibmap -liberty /src/$O/cells.lib
yosys abc -liberty /src/$O/cells.lib
yosys opt_clean
yosys autoname
yosys tee -o /src/$O/stat.txt stat -liberty /src/$O/cells.lib
yosys write_verilog -noattr /src/$O/mapped.v
TCL
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/src" -w /src "$IMG" bash -c "
  set -e
  export PATH=/OpenROAD-flow-scripts/tools/install/yosys/bin:\$PATH
  python3 rtl/test/qwen_dv/s5/xhead3/merge_lib.py /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM $O/cells.lib
  yosys -c $O/synth.tcl > $O/synth.log 2>&1
"
set +e
python3 tools/ref_tile/native_census.py --netlist "$O/mapped.v" --top "$TOP" --liberty "$O/cells.lib" --out "$O/native_census.json" > "$O/native_census.log" 2>&1
NRC=$?
python3 tools/textbook_lint.py check --netlist "$O/mapped.v" --top "$TOP" --out "$O/textbook.json" > "$O/textbook.log" 2>&1
set -e
python3 - "$O" "$NRC" <<'PY'
import json,sys
o=sys.argv[1]
n=json.load(open(o+'/native_census.json'))
t=json.load(open(o+'/textbook.json')); m=t.get('metrics',{})
viol=n.get('violations') or n.get('drivers_over_limit') or []
print('NATIVE_CENSUS', n.get('status'), 'rc', sys.argv[2], 'max_dynamic_loads', n.get('max_dynamic_loads'),
      'over32', len(viol) if isinstance(viol,list) else viol)
print('DEPTH_PS', m.get('depth_ps'), 'levels', m.get('depth_levels'), 'path', m.get('depth_path'),
      'in_reg', m.get('in_to_reg_levels'), 'reg_out', m.get('reg_to_out_levels'), 'in_out', m.get('in_to_out_bits'),
      'ff', t.get('flops'), 'cells', t.get('cells'), 'hf_top', m.get('high_fanout_top', [])[:3])
PY
grep -E "Chip area" "$O/stat.txt" | tail -1 || true
gzip -kf "$O/mapped.v"
