#!/bin/bash
set -euo pipefail
out=$1
extra_defines=()
if [[ ${HC_ECC_PIPE:-0} == 1 ]];then extra_defines=(-DHC_ECC_PIPE);fi
mkdir -p "$out"
if [[ -e "$out/terminal.json" || -e "$out/positive.log" ]];then exit 73;fi
python3 tools/dsrom_hc_mean_capture_vectors.py --out "$out/vectors"
sources=(rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_secded_pipe.sv
 rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_seed_join.sv
 rtl/test/dsrom_hc_capture_20261009/tb_hc_seed_join.sv)
iverilog -g2012 "${extra_defines[@]}" -s tb_hc_seed_join -o "$out/base.vvp" "${sources[@]}" >"$out/elaborate.log" 2>&1
vvp "$out/base.vvp" +vectors="$out/vectors" >"$out/positive.log" 2>&1
vvp "$out/base.vvp" +vectors="$out/vectors" +reset=1 >"$out/reset.log" 2>&1
for bad in 1 2 3 4 5 6 7;do
 vvp "$out/base.vvp" +vectors="$out/vectors" +bad="$bad" >"$out/negative_$bad.log" 2>&1
done
for injection in CE UE;do
 iverilog -g2012 "${extra_defines[@]}" -s tb_hc_seed_join -DHC_INJECT_$injection -o "$out/$injection.vvp" "${sources[@]}" >"$out/$injection.elaborate.log" 2>&1
 vvp "$out/$injection.vvp" +vectors="$out/vectors" >"$out/$injection.log" 2>&1
done
python3 - "$out" <<'PY'
import json,pathlib,sys
p=pathlib.Path(sys.argv[1]);r={'verdict':'PASS','source_commit':pathlib.Path('SOURCE_COMMIT').read_text().strip(),
 'scope':'actual three-SRAM protected headjoin120full512bframes; independent capture2/0/1, identity/frame/last/duplicate/bounds negatives, partial reset, CE/UE',
 'logs':{x.name:x.read_text()[-1000:] for x in p.glob('*.log') if 'elaborate' not in x.name},
 'registered_link_qualified':False,'physical_qualified':False,'integration_qualified':False}
(p/'terminal.json').write_text(json.dumps(r,indent=2)+'\n')
PY
