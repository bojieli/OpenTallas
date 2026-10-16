#!/usr/bin/env bash
# H-DIE 2026-10-15: hardware-issued service groups (tb_hbm_svc_sm_groups_issued) + mutants.
#   run_sm_groups_issued.sh <out> <images> [stack] [rows] [epochs]
set -euo pipefail
ulimit -c 0
out=${1:?out}; images=${2:?images}; stack=${3:-0}; rows=${4:-64}; epochs=${5:-8}
mkdir -p "$out"
# $readmemh is only a warning in Verilator. Reject missing/truncated external
# records and backing images before any build; never compare zero-filled DUT
# memory with a zero-filled expected array after a file-load failure.
python3 - "$images" "$stack" "$rows" <<'PYIMAGE'
import hashlib,json,re,sys
from pathlib import Path
root=Path(sys.argv[1]);stack=int(sys.argv[2]);rows=int(sys.argv[3]);recorded={}
for sm in range(8*stack,8*stack+8):
 d=root/f'sm{sm:02d}'
 records=d/'records.hex';backing=d/'backing.hex'
 assert records.is_file() and backing.is_file(),f'required image unavailable: {d}'
 rr=records.read_text().splitlines();bb=backing.read_text().splitlines()
 assert len(rr)==rows and all(re.fullmatch(r'[0-9a-fA-F]{272}',t) for t in rr),f'incomplete records image: {records}'
 sectors=(rows*136+31)//32
 assert len(bb)==2*sectors and all(re.fullmatch(r'@[0-9a-fA-F]+',bb[i]) and re.fullmatch(r'[0-9a-fA-F]{64}',bb[i+1]) for i in range(0,len(bb),2)),f'incomplete backing image: {backing}'
 assert len({int(bb[i][1:],16) for i in range(0,len(bb),2)})==sectors,f'duplicate backing sector address: {backing}'
 for p in (records,backing):recorded[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
print('SM_GROUPS_IMAGES_VALID '+json.dumps(recorded,sort_keys=True))
PYIMAGE
d=rtl/hbm_accel/loader/service_native
src=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_rst_relay.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/ot_hbm_svc_prefetch_mapped4_owner.sv" "$d/ot_hbm_svc_prefetch_overlap_owner.sv" "$d/ot_hbm_svc_sm8_landing_bank.sv" "$d/ot_hbm_svc_sm4pc_cdc.sv" "$d/ot_hbm_svc_static_sm_packed136.sv" "$d/ot_hbm_svc_sm_feed_programmed.sv" "$d/ot_hbm_svc_sm_issuer.sv" "$d/ot_hbm_svc_sm_group.sv" rtl/hbm_accel/sm/static/ot_smh_static_feed.sv rtl/hbm_accel/sm/static/ot_smh_calendar_static.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv "$d/ot_hbm_svc_pc_ctrl_leaf.sv" "$d/ot_hbm_svc_pc_ctrl_leaf_cfg.sv" rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap.sv "$d/ot_hbm_svc_native_sector_pipeline_leaves.sv" "$d/tb_hbm_svc_command_dram_pipeline_fixture.sv" "$d/tb_hbm_svc_sm_groups_issued.sv")
build(){ verilator --binary --timing -j 4 -Wno-fatal $1 --top-module tb_hbm_svc_sm_groups_issued -GSTACK="$stack" -GROWS="$rows" -GEPOCHS="$epochs" --Mdir "$out/$2" -o sim "${src[@]}" > "$out/$2.build.log" 2>&1; }
build "" obj
"$out/obj/sim" +IMAGES="$images" > "$out/positive.log"
grep -q 'SM_GROUPS_ISSUED PASS' "$out/positive.log"
if "$out/obj/sim" +IMAGES="$out/missing_images" > "$out/missing_image_negative.log" 2>&1;then echo 'missing-image negative survived';exit 1;fi
grep -q 'required image unavailable' "$out/missing_image_negative.log"
if "$out/obj/sim" +IMAGES="$images" +EARLY > "$out/early_mutant.log" 2>&1;then echo 'early programme mutant survived';exit 1;fi
grep -q 'SM_STACK DUT fault' "$out/early_mutant.log"
build "-DOT_ISSUER_MUT_NORESIDENT" obj_mut
if "$out/obj_mut/sim" +IMAGES="$images" > "$out/noresident_mutant.log" 2>&1;then echo 'copy-before-resident issuer mutant survived';exit 1;fi
grep -q 'SM_STACK' "$out/noresident_mutant.log"
grep -v '^- ' "$out/positive.log"
echo 'SM_GROUPS_EARLY_PROGRAMME_MUTANT rejected'
echo "SM_GROUPS_NORESIDENT_ISSUER_MUTANT rejected: $(grep -m1 -o 'SM_STACK[^"]*' "$out/noresident_mutant.log")"

for bad in PC PHASE; do
 build "-DOT_PC_CFG_MUT_$bad" "obj_cfg_$bad"
 if "$out/obj_cfg_$bad/sim" +IMAGES="$images" > "$out/cfg_${bad}_mutant.log" 2>&1;then echo "wrong config $bad survived";exit 1;fi
 grep -Eq 'SM_STACK (DUT fault|PHY aperture)' "$out/cfg_${bad}_mutant.log"
 echo "SM_GROUPS_CFG_${bad}_MUTANT rejected"
done
