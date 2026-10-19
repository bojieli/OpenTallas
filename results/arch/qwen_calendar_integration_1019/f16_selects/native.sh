#!/bin/bash
set -euo pipefail
docker run --rm -v "$PWD:/work" -w /work openroad/orfs:asap7lock yosys -s generic.ys > generic.log 2>&1
python3 census.py generic.json generic_census > generic_census.stdout
docker run --rm -v "$PWD:/work" -w /work openroad/orfs:asap7lock yosys -p 'read_liberty -lib libsource/all.lib; read_json generic.json; dfflibmap -liberty libsource/seq.lib; abc -liberty libsource/comb.lib; clean; stat -liberty libsource/all.lib; write_verilog -noattr native.v; write_json native.json' > native.log 2>&1
python3 census.py native.json native_census > native_census.stdout
gzip -kf native_census.tsv generic_census.tsv
sha256sum src/rtl/qwen_dv/qfd_dv_typed_witness_control.sv generic.json native.json native.v libsource/*.lib > artifacts.sha256
cat native_census.stdout
echo F16_SELECT_NATIVE_CENSUS_DONE
