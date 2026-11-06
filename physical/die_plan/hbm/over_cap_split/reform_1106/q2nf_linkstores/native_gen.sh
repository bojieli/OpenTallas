#!/bin/bash
set -euo pipefail
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
run_yosys() {
 sudo -n docker run --rm --memory 8g --cpus 2 -v "$PWD:/work" -w /work openroad/orfs:latest "$Y" -Q -T -p "$1"
}
run_yosys 'read_json grouped3.json; submod ot_q2nf_rest; write_json split3_raw.json' > split3_raw.log 2>&1
python3 q2nf_linkstore_extract.py trim split3_raw.json split3.json > port_trim.log
run_yosys 'read_json split3.json; rename ot_q2nf_rest_g_linkstore0 ot_q2nf_linkstore0; rename ot_q2nf_rest_g_linkstore1 ot_q2nf_linkstore1; rename ot_q2nf_rest_rest_control ot_q2nf_control; chtype -set ot_q2nf_linkstore0 t:ot_q2nf_rest_g_linkstore0; chtype -set ot_q2nf_linkstore1 t:ot_q2nf_rest_g_linkstore1; chtype -set ot_q2nf_control t:ot_q2nf_rest_rest_control; rename ot_q2nf_rest ot_q2nf_linkstore_parent; hierarchy -check -top ot_q2nf_linkstore_parent; design -save final; flatten ot_q2nf_linkstore_parent; write_json final_reflat.json; design -load final; select ot_q2nf_linkstore_parent ot_q2nf_linkstore0 ot_q2nf_linkstore1 ot_q2nf_control; write_verilog -selected -noattr ot_q2nf_linkstores.sv; write_json native3.json' > native3.log 2>&1
python3 q2nf_linkstore_extract.py compare original.json final_reflat.json --other-top ot_q2nf_linkstore_parent > exact_graph3.log
python3 - <<'PY'
import json
from pathlib import Path
p=json.loads(Path('grouped3.json').read_text());p['modules']={n:t for n,t in p['modules'].items()if n.startswith('ot_sram_')};Path('actual_sram_bbs.json').write_text(json.dumps(p))
PY
run_yosys 'read_json actual_sram_bbs.json; read_verilog -sv ot_q2nf_linkstores.sv; hierarchy -check -top ot_q2nf_linkstore_parent; stat' > emitted_source_hierarchy.log 2>&1
