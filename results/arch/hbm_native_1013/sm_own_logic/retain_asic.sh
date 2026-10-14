#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
docker run --rm -v "$PWD:/work" -w /work openroad/orfs:asap7lock yosys -Q -p 'read_liberty -lib SEQ.lib; read_json eg_retention_asic_input.json; hierarchy -check -top ot_smh_own_eg; techmap; dfflibmap -liberty SEQ.lib; abc -liberty AO.lib -liberty OA.lib -liberty SIMPLE.lib -liberty INVBUF.lib -liberty SEQ.lib -D 833.333; clean; stat -liberty AO.lib -liberty OA.lib -liberty SIMPLE.lib -liberty INVBUF.lib -liberty SEQ.lib; write_json eg_retention_asap7.json; write_verilog eg_retention_asap7.sv' > eg_retention_asap7.log
