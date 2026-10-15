#!/usr/bin/env bash
set -euo pipefail
mkdir -p evidence
if [ ! -f baseline_staging.sv ]; then
 cp results/arch/hbm_system_geometry_1015/grouped_staging_gate/baseline_staging.sv baseline_staging.sv
fi
iverilog -g2012 -s tb_grouped -Ptb_grouped.MUT=0 -o evidence/base.vvp \
 baseline_staging.sv rtl/hdc/v41x/static/ot_hbm_attn_staging_grouped.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 rtl/test/hbm_staging_geometry/tb_grouped.sv >evidence/base.compile.log 2>&1
vvp evidence/base.vvp >evidence/base.log 2>&1
iverilog -g2012 -s tb_grouped -Ptb_grouped.MUT=1 -o evidence/mut.vvp \
 baseline_staging.sv rtl/hdc/v41x/static/ot_hbm_attn_staging_grouped.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 rtl/test/hbm_staging_geometry/tb_grouped.sv >evidence/mut.compile.log 2>&1
set +e
vvp evidence/mut.vvp >evidence/mut.log 2>&1
mut_rc=$?
set -e
if [ "$mut_rc" -eq 0 ]; then echo 'ERROR mutant passed';exit 1;fi
python3 - <<'PY'
import hashlib,json,pathlib
files=['baseline_staging.sv','rtl/hdc/v41x/static/ot_hbm_attn_staging_grouped.sv','rtl/test/hbm_staging_geometry/tb_grouped.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v']
r=dict(scope='actual34mappedSRAM grouped packing vs original actual34SRAM and independent flat bench scoreboard; not physical or whole native qualification',baseline_pass='PASS' in pathlib.Path('evidence/base.log').read_text(),mutant_rejected='grouped scoreboard mismatch' in pathlib.Path('evidence/mut.log').read_text(),source_sha256={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in files})
assert r['baseline_pass'] and r['mutant_rejected'];pathlib.Path('evidence/receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
