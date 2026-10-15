#!/usr/bin/env bash
set -euo pipefail
mkdir -p evidence
for mut in 0 1 2 3;do
  iverilog -g2012 -s tb_mode_local -Ptb_mode_local.MUT="$mut" -o "evidence/m${mut}.vvp" \
   baseline_staging.sv rtl/hdc/v41x/static/ot_hbm_attn_staging_mode_local.sv \
   physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
   rtl/test/hbm_staging_geometry/tb_mode_local.sv >"evidence/m${mut}.compile.log" 2>&1
  set +e
  vvp "evidence/m${mut}.vvp" >"evidence/m${mut}.log" 2>&1
  rc=$?
  set -e
  if [ "$mut" = 0 ];then test "$rc" = 0;else test "$rc" != 0;fi
  cat "evidence/m${mut}.log"
done
python3 - <<'PY'
import json,hashlib,pathlib
files=['baseline_staging.sv','rtl/hdc/v41x/static/ot_hbm_attn_staging_mode_local.sv','rtl/test/hbm_staging_geometry/tb_mode_local.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v']
r=dict(physical_qualified=False,scope='actual34SRAM mode-specific raw8480 bijection, full320rows*2lanes*4jobs, maskedwrites, sameaddress olddata, realPVlocal decoding and3realguards; not complete compiler/controller join',source_sha256={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in files},baseline_pass='PASS mode actual34SRAM' in pathlib.Path('evidence/m0.log').read_text(),mutants_rejected={str(k):'scoreboard mismatch' in pathlib.Path(f'evidence/m{k}.log').read_text() for k in [1,2,3]})
assert r['baseline_pass'] and all(r['mutants_rejected'].values());pathlib.Path('evidence/receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
