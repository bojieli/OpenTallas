#!/bin/bash
set -euo pipefail
out=$1
mkdir -p "$out"
if [[ -e "$out/terminal.json" || -e "$out/reader.log" ]]; then exit 73;fi
sources=(rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
 rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_mean_capture.sv
 rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_input_reader.sv
 rtl/test/dsrom_hc_capture_20261009/tb_hc_mean_capture.sv)
iverilog -g2012 -s tb_hc_mean_capture -DHC_VM_READER -o "$out/reader.vvp" "${sources[@]}" >"$out/elaborate.log" 2>&1
python3 tools/dsrom_hc_mean_capture_vectors.py --out "$out/synthetic"
vvp "$out/reader.vvp" +vectors="$out/synthetic" >"$out/reader.log" 2>&1
for bad in 6 7 8;do
 if vvp "$out/reader.vvp" +vectors="$out/synthetic" +bad="$bad" >"$out/negative_$bad.log" 2>&1;then
  echo "bad native H read $bad escaped" >&2;exit 1
 fi
 grep -q 'native H reader fault' "$out/negative_$bad.log"
done
for rank in 0 1 2 3;do
 python3 tools/dsrom_hc_mean_capture_vectors.py --out "$out/released_rank$rank" --rank "$rank" --released-root "$HC_RELEASED_ROOT"
 vvp "$out/reader.vvp" +vectors="$out/released_rank$rank" +rank="$rank" >"$out/rank$rank.log" 2>&1
done
python3 - "$out" <<'PY'
import json,pathlib,sys
p=pathlib.Path(sys.argv[1]);r={'verdict':'PASS','source_commit':pathlib.Path('SOURCE_COMMIT').read_text().strip(),
 'scope':'actual H4x5120 resident per rank, copy320row stride, rank80row offset; single outstanding variable-rvalid facade plus full1280d HC mean captures',
 'logs':{x.name:x.read_text()[-1000:] for x in p.glob('*.log') if x.name!='elaborate.log'},
 'native_port_arbiter_qualified':False,'integration_qualified':False,'physical_qualified':False}
(p/'terminal.json').write_text(json.dumps(r,indent=2)+'\n')
PY
