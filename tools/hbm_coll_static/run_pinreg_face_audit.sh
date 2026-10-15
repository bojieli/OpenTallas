#!/usr/bin/env bash
set -euo pipefail
root=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
out=$(realpath -m "$1");mkdir -p "$out";cd "$root"
git show 4c66b6a95:rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv > "$out/crc.sv"
git show 4c66b6a95:rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv > "$out/native.sv"
python3 - "$out/macro.v" <<'PY'
import pathlib,sys,subprocess
s=subprocess.check_output(['git','show','4c66b6a95:physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v'],text=True)
s=s[s.index('module '):];s=s[:s.index(');')+2]
pathlib.Path(sys.argv[1]).write_text('(* blackbox *) '+s+'\nendmodule\n')
PY
p=rtl/hbm_accel/generic/collective/p2p
yosys=${YOSYS:-$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys}
"$yosys" -Q -T -p "read_verilog -lib -sv $out/macro.v; read_verilog -sv $out/crc.sv $out/native.sv $p/ot_hgi_coll_static_seq_ctl.sv $p/ot_hgi_coll_static_pinreg_ctl.sv $p/ot_hgi_coll_static_pinreg_store.sv $p/ot_hgi_coll_static_link_pinreg.sv; synth -top ot_hgi_coll_static_link_pinreg -flatten; write_json $out/mapped.json" > "$out/synth.log" 2>&1
python3 tools/hbm_coll_static/check_pinreg_faces.py "$out/mapped.json" "$out/face_audit.json"
python3 - "$out" <<'PY'
import pathlib,json,subprocess,sys
out=pathlib.Path(sys.argv[1]);j=json.loads((out/'mapped.json').read_text());m=j['modules']['ot_hgi_coll_static_link_pinreg']
macro=next(c for c in m['cells'].values() if c['type']=='ot_sram_1r1w_64x512_m1_r2c2')
macro['connections']['r_addr_in']=m['ports']['rd_seq']['bits'][:6]
(out/'raw_ra_mutant.json').write_text(json.dumps(j))
r=subprocess.run([sys.executable,'tools/hbm_coll_static/check_pinreg_faces.py',str(out/'raw_ra_mutant.json'),str(out/'should_not_exist.json')],capture_output=True,text=True)
assert r.returncode!=0,'raw macro address mutant passed'
(out/'raw_ra_mutant.log').write_text('RAW_MACRO_RA_MUTANT_REJECTED\n'+r.stderr)
print('RAW_MACRO_RA_MUTANT_REJECTED')
PY
