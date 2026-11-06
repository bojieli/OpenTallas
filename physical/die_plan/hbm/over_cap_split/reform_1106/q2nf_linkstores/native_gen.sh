#!/bin/bash
set -euo pipefail
OR=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
sudo -n docker run --rm --memory 4g --cpus 2 -v "$PWD:/work" -w /work openroad/orfs:latest "$OR" -Q -T -p 'read_json grouped3.json; submod ot_q2nf_rest; write_json split3_raw.json' > split3_raw.log 2>&1
python3 q2nf_linkstore_extract.py trim split3_raw.json split3.json > port_trim.log
sudo -n docker run --rm --memory 4g --cpus 2 -v "$PWD:/work" -w /work openroad/orfs:latest "$OR" -Q -T -p 'read_json split3.json; design -save split; flatten ot_q2nf_rest; write_json reflat3.json; design -load split; rename ot_q2nf_rest_g_linkstore0 ot_q2nf_linkstore0; rename ot_q2nf_rest_g_linkstore1 ot_q2nf_linkstore1; rename ot_q2nf_rest_rest_control ot_q2nf_control; rename ot_q2nf_rest ot_q2nf_linkstore_parent; select ot_q2nf_linkstore_parent ot_q2nf_linkstore0 ot_q2nf_linkstore1 ot_q2nf_control; write_verilog -selected -noattr ot_q2nf_linkstores.sv; write_json native3.json' > native3.log 2>&1
python3 q2nf_linkstore_extract.py compare original.json reflat3.json > exact_graph3.log
