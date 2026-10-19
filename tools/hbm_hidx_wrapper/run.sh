#!/bin/bash
set -euo pipefail
mkdir -p out
T=tools/hbm_hidx_wrapper
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
python3 "$T/augment.py"
cp canonical/all.lib out/all.lib
docker run --rm --network none -v "$PWD:/work" -w /work "$IMG" yosys -Q -T -p 'read_json out/netlist.json; write_verilog -noattr -norename out/netlist.v' >out/representation.log 2>&1
docker run --rm --network none -v "$PWD:/work" -w /work "$IMG" yosys -Q -T -p 'read_liberty -lib out/all.lib; read_verilog out/netlist.v; hierarchy -check -top hidx_coupon1; write_json out/roundtrip.json' >out/roundtrip.log 2>&1
python3 "$T/roundtrip.py"
docker run --rm --network none -v "$PWD:/work" -w /work "$IMG" yosys -Q -T -p 'read_liberty -ignore_miss_func -ignore_miss_dir out/all.lib; read_verilog out/netlist.v; rename hidx_coupon1 mapped; read_verilog -sv tools/hbm_hidx_coupon1/coupon.sv tools/hbm_hidx_wrapper/wrapper.sv tools/hbm_hidx_wrapper/formal.sv; hierarchy -check -top formal_wrapper; setattr -mod -unset keep_hierarchy; prep -top formal_wrapper -flatten; sat -seq 3 -prove-skip 2 -prove bad 0 -verify -show-ports' >out/formal.log 2>&1
grep -q 'SAT proof finished - no model found: SUCCESS!' out/formal.log
sha256sum "$T/wrapper.sv" "$T/tb.sv" "$T/formal.sv" >out/SOURCE_TRACE_SHA256SUMS
iverilog -g2012 -s tb -o out/pass.vvp tools/hbm_hidx_coupon1/coupon.sv "$T/wrapper.sv" "$T/tb.sv"
vvp out/pass.vvp >out/pass.log
for m in 1 2;do
 iverilog -g2012 -s tb -DMUT=$m -o out/mut$m.vvp tools/hbm_hidx_coupon1/coupon.sv "$T/wrapper.sv" "$T/tb.sv"
 if vvp out/mut$m.vvp >out/mut$m.log 2>&1;then echo "MUTANT SURVIVED $m";exit 1;fi
 grep -q 'S1_CAPTURE_AGE_FAIL' out/mut$m.log
done
python3 tools/hbm_hidx_coupon1/native.py >out/native.log
# Independent oracle, including all clock terminals by native role.
docker run --rm --network none -v "$PWD:/work" -w /work "$IMG" python3 tools/hbm_hidx_coupon1/strict.py >out/strict.log 2>&1
python3 tools/hbm_hidx_coupon1/direct_caps.py >out/direct_caps.log
python3 "$T/geometry.py"
python3 "$T/constraints.py"
# No OpenROAD executable is invoked; these are a source/kit model, not placement.
sha256sum tools/hbm_hidx_wrapper/* canonical/* out/*.json out/*.log out/*.v out/*.lib out/*.sdc out/*.tcl >out/SHA256SUMS
