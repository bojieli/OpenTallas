#!/bin/bash
set -euo pipefail
mkdir -p ../out
python3 tools/s81_dv/svc_rs/gen_service72.py > ../out/generate.log 2>&1
python3 - <<'PY' > ../out/chain_audit.log
from pathlib import Path
import hashlib
D=Path('rtl/dsrom_sys/s81_dv/svc_rs')
g=(D/'group72/dsdv_svc_group72.sv').read_text();c=(D/'group72/dsdv_svc_rs_c_group72.sv').read_text()
assert g.count('.PV_IDENTITY(PV_IDENTITY)')==16
assert '.PV_IDENTITY(PV_IDENTITY)' in c
assert '.NTP(NTP)' not in c and 'parameter integer NTP' not in c
for name in ['attw/dsdv_svc_attw_n1_f.sv','attw/lp/dsdv_svc_attw_n1_f_lp.sv']:
 s=(D/name).read_text();assert 'parameter integer PV_IDENTITY = 0' in s and '.PV_IDENTITY(PV_IDENTITY)' in s
s=(D/'dsdv_svc_rs_glue.sv').read_text().split('module dsdv_svc_rs_attw1 #')[1].split('endmodule')[0]
assert 'dsdv_svc_att #' in s and 'dsdv_svc_att_nt1 #' not in s and '.PV_IDENTITY(PV_IDENTITY)' in s
s=(D/'dsdv_svc_att.sv').read_text();assert '.PV_IDENTITY(PV_IDENTITY)' in s and '.launch_ok(job_open && !job_active && !run && !dr_arm && !dr_on)' in s
print('CHAIN_AUDIT_PASS group16 -> controller -> LP -> attw1 -> currentABI thinwrapper -> SRAMcore -> original launchguard identity')
for p in [D/'dsdv_svc_att.sv',D/'dsdv_svc_rs_glue.sv',D/'attw/lp/dsdv_svc_attw_n1_f_lp.sv',D/'group72/dsdv_svc_group72.sv',D/'group72/dsdv_svc_rs_c_group72.sv']:
 print(hashlib.sha256(p.read_bytes()).hexdigest(),p)
PY
bash tools/s81_dv/pv_so_assembly_1021/identity.sh ../out/identity > ../out/identity.execution.log 2>&1
source tools/s81_dv/svc_rs/rs_files.sh
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --lint-only --top-module dsdv_svc_group72 -GPV_IDENTITY=1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
 -I"$D" -DOT_SVC_GROUP72 -DOT_SVC_LAND_SRAM -DOT_SVC_ATT_SRAM -DOT_ATTN_HGRP_HARD -DOT_ATTN_HGRP8 -DOT_HGRP8_MOD=ot_s81svc8_hgrp_s81_bounded "${RS_DEF[@]}" "${RS_SRC[@]}" "${RS_LIB[@]}" \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 rtl/lib/ot_reset_sync.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_n32.sv rtl/common/landed_parent/ot_pl_land_field_copies.sv rtl/common/landed_parent/ot_pl_land_reset_forest.sv \
 "$D/dsdv_svc_rs_glue.sv" "$D/attw/lp/dsdv_svc_attw_n1_f_lp.sv" tools/s81_dv/svc_rs/attn1/ot_s81svc8_hgrp_s81_bounded_bb.v \
 "$D/group72/dsdv_svc_face72.sv" "$D/group72/dsdv_svc_rs_c_group72.sv" "$D/group72/dsdv_svc_group72.sv" > ../out/group_hierarchy.log 2>&1
printf '%s\n' 'PRODUCTION_GROUP16_HIERARCHY_PASS NTP1 PV_IDENTITY1 SRAM1 PMEMmaskFFFF TEXT1 realLP, hard arithmetic group interfaces only; no simulation/layout/token claim'
