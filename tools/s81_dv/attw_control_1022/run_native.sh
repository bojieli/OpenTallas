#!/usr/bin/env bash
# Source-bound control-only synthesis; no graph rewriting and no parent closure claim.
set -euo pipefail
root=$PWD
out=$(mkdir -p "${1:?output}" && cd "$1" && pwd)
root_mode=${2:-0}
case "$root_mode" in 0|1) ;; *) exit 2;; esac
cat > "$out/native.ys" <<YS
read_verilog -lib /src/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2_bb.v
read_verilog -lib /src/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_bb.v
read_verilog -defer -sv -DSYNTHESIS -DOT_SVC_LAND_SRAM -DOT_SVC_ATT_SRAM -DOT_SVC_ATT_PINREG -DOT_S81_ATTW_RESET_R3 -DOT_S81_ATTW_ENABLE_R4 -I/src/rtl/dsrom_sys/s81_dv/svc_rs /src/rtl/dsrom_sys/s81_dv/svc_rs/ot_s81_attw_reset_fork.sv /src/rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_glue.sv /src/rtl/dsrom_sys/s81_dv/svc_rs/group72/dsdv_svc_att_nt1.sv /src/rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_qmem8.sv /src/rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv /src/rtl/hdc/v41x/ot_hdc_v41x_kreg.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn.sv /src/rtl/hdc/ot_hdc_fastfp.sv /src/rtl/hdc/ot_hdc_fp32_add_lat.sv /src/rtl/hdc/ot_hdc_prefix.sv /src/rtl/hdc/ot_hdc_fp32_f12.sv /src/rtl/hdc/v41x/ot_dsrom_su_add6.sv /src/rtl/hdc/ot_hdc_delay.sv /src/rtl/hdc/ot_hdc_fastfp_lat_f12.sv /src/rtl/hdc/ot_hdc_fp32_mul_lat.sv
read_liberty -lib /out/lib/INVBUF.lib
hierarchy -check -top dsdv_svc_rs_attw1 -chparam MUT 0 -chparam DIE_ID 0 -chparam ST 0 -chparam SRAM_MACRO 1 -chparam ROOT $root_mode -chparam PMEM 1 -chparam TEXT 1 -chparam TLX 6 -chparam TXD 0 -chparam NTP 1 -chparam ROLE_EXT 1
read_liberty -lib /out/lib/SIMPLE.lib
read_liberty -lib /out/lib/AO.lib
read_liberty -lib /out/lib/OA.lib
read_liberty -lib /out/lib/SEQ.lib
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top dsdv_svc_rs_attw1 -flatten -noshare
dfflibmap -liberty /out/lib/SEQ.lib
abc -liberty /out/lib/SIMPLE.lib -liberty /out/lib/AO.lib -liberty /out/lib/OA.lib -liberty /out/lib/INVBUF.lib -liberty /out/lib/SEQ.lib
opt_clean
setattr -mod -unset keep_hierarchy
flatten
opt_clean
tee -o /out/stat.txt stat -liberty /out/lib/SIMPLE.lib -liberty /out/lib/AO.lib -liberty /out/lib/OA.lib -liberty /out/lib/INVBUF.lib -liberty /out/lib/SEQ.lib
write_verilog -noattr /out/mapped.v
write_json /out/mapped.json
YS
sha256sum rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_glue.sv rtl/dsrom_sys/s81_dv/svc_rs/group72/dsdv_svc_att_nt1.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_roles*.svh physical/common_flow/ot_keep_regs.tcl > "$out/source.sha256"
docker run --rm -v "$root:/src:ro" -v "$out:/out" openroad/orfs:latest bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 mkdir -p /out/lib
 n=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
 for k in SIMPLE AO OA; do zcat "$n/asap7sc7p5t_${k}_RVT_TT_nldm_211120.lib.gz" > /out/lib/$k.lib; done
 zcat "$n/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz" > /out/lib/INVBUF.lib
 cp "$n/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" /out/lib/SEQ.lib
 cp /src/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/*_tt.lib /out/lib/MACRO256.lib
 cp /src/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/*_tt.lib /out/lib/MACRO32.lib
 yosys -V > /out/tool_identity.txt
 yosys -l /out/synth.log -s /out/native.ys > /out/synth.stdout 2>&1
' > "$out/docker.log" 2>&1 || { tail -n 25 "$out/synth.stdout" "$out/docker.log"; exit 1; }
args=();for f in "$out"/lib/*.lib;do args+=(--liberty "$f");done
python3 tools/ref_tile/native_census.py --netlist "$out/mapped.v" --top dsdv_svc_rs_attw1 --out "$out/native_census.json" "${args[@]}" > "$out/native_census.log" 2>&1 || true
python3 - "$out" "$root_mode" <<'PY_NATIVE'
import json,sys,collections,pathlib
out=pathlib.Path(sys.argv[1]);m=json.load(open(out/'mapped.json'))['modules']['dsdv_svc_rs_attw1'];c=collections.Counter(v['type'] for v in m['cells'].values());macros={k:v for k,v in c.items() if 'sram' in k.lower()};native=json.load(open(out/'native_census.json'))
r=dict(qualification='CONTROL_SYNTH_INVENTORY_ONLY',top='dsdv_svc_rs_attw1',ROOT=int(sys.argv[2]),params=dict(MUT=0,DIE_ID=0,ST=0,SRAM_MACRO=1,PMEM=1,TEXT=1,TLX=6,TXD=0,NTP=1,ROLE_EXT=1),macros=macros,cells=sum(c.values()),ports={k:dict(direction=v['direction'],width=len(v['bits'])) for k,v in m['ports'].items()},native_status=native.get('status'),max_dynamic_loads=native.get('max_dynamic_loads'),violation_count=len(native.get('violations',[])),parent_closed=False)
(out/'inventory.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY_NATIVE
