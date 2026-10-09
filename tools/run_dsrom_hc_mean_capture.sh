#!/bin/bash
set -euo pipefail
out=$1
mkdir -p "$out"
if [[ -e "$out/terminal.json" || -e "$out/positive.log" ]]; then
    echo 'immutable gate already exists' >&2;exit 73
fi
python3 tools/dsrom_hc_mean_capture_vectors.py --out "$out/synthetic"
sources=(rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_mean_capture.sv
 rtl/test/dsrom_hc_capture_20261009/tb_hc_mean_capture.sv)
iverilog -g2012 -s tb_hc_mean_capture -o "$out/base.vvp" "${sources[@]}" >"$out/elaborate.log" 2>&1
vvp "$out/base.vvp" +vectors="$out/synthetic" >"$out/positive.log" 2>&1
for bad in 1 2 3 4 5; do
    vvp "$out/base.vvp" +vectors="$out/synthetic" +bad="$bad" >"$out/negative_$bad.log" 2>&1
done
for injection in CE UE; do
    iverilog -g2012 -s tb_hc_mean_capture -DHC_INJECT_$injection -o "$out/$injection.vvp" "${sources[@]}" >"$out/$injection.elaborate.log" 2>&1
    vvp "$out/$injection.vvp" +vectors="$out/synthetic" >"$out/$injection.log" 2>&1
done
for mutation in TREE ALIAS; do
    iverilog -g2012 -s tb_hc_mean_capture -DHC_MUT_$mutation -o "$out/$mutation.vvp" "${sources[@]}" >"$out/$mutation.elaborate.log" 2>&1
    if vvp "$out/$mutation.vvp" +vectors="$out/synthetic" >"$out/$mutation.log" 2>&1; then
        echo "mutation $mutation escaped" >&2;exit 1
    fi
    grep -q 'mean/identity/order mismatch' "$out/$mutation.log"
done
if [[ -n ${HC_RELEASED_ROOT:-} ]]; then
    for rank in 0 1 2 3; do
        python3 tools/dsrom_hc_mean_capture_vectors.py --out "$out/released_rank$rank" --rank "$rank" --released-root "$HC_RELEASED_ROOT"
        vvp "$out/base.vvp" +vectors="$out/released_rank$rank" >"$out/released_rank$rank.log" 2>&1
    done
fi
python3 - "$out" <<'PY'
import json, pathlib, sys
p=pathlib.Path(sys.argv[1]);logs=sorted(p.glob('*.log'))
record={'verdict':'PASS','source_commit':pathlib.Path('SOURCE_COMMIT').read_text().strip(),
 'scope':'actual HC4 eight-lane engine, three full1280-dimension TP4-rank captures, real3 SRAM macros',
 'logs':{x.name:x.read_text()[-1200:] for x in logs if 'elaborate' not in x.name},
 'integration_qualified':False,'physical_qualified':False}
(p/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
PY
