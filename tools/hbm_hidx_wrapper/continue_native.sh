#!/bin/bash
set -euo pipefail
T=tools/hbm_hidx_wrapper
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
python3 "$T/roundtrip.py"
docker run --rm --network none -v "$PWD:/work" -w /work "$IMG" yosys -Q -T -p 'read_liberty -ignore_miss_func -ignore_miss_dir out/all.lib; read_verilog out/netlist.v; rename hidx_coupon1 mapped; read_verilog -sv tools/hbm_hidx_coupon1/coupon.sv tools/hbm_hidx_wrapper/wrapper.sv tools/hbm_hidx_wrapper/formal.sv; hierarchy -check -top formal_wrapper; setattr -mod -unset keep_hierarchy; prep -top formal_wrapper -flatten; sat -seq 3 -prove-skip 2 -prove bad 0 -verify -show-ports' >out/formal.log 2>&1
grep -q 'SAT proof finished - no model found: SUCCESS!' out/formal.log
cp out_repr_bad/pass.log out_repr_bad/mut1.log out_repr_bad/mut2.log out/
python3 tools/hbm_hidx_coupon1/native.py >out/native.log
# Independent oracle, including all clock terminals by native role.
docker run --rm --network none -v "$PWD:/work" -w /work "$IMG" python3 tools/hbm_hidx_coupon1/strict.py >out/strict.log 2>&1
python3 tools/hbm_hidx_coupon1/direct_caps.py >out/direct_caps.log
python3 "$T/geometry.py"
python3 "$T/constraints.py"
python3 "$T/loaded_caps.py"
python3 "$T/pg_model.py"
for corner in TT FF;do
 docker run --rm --network none -e CORNER="$corner" -v "$PWD:/work" -w /work "$IMG" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit "$T/source_sta.tcl" >out/source_sta_$corner.log 2>&1
 if grep -Eq '\[ERROR|^Error:' out/source_sta_$corner.log;then exit 1;fi
done
sha256sum tools/hbm_hidx_wrapper/* canonical/* out/*.json out/*.log out/*.v out/*.lib out/*.sdc out/*.tcl >out/SHA256SUMS_FINAL
