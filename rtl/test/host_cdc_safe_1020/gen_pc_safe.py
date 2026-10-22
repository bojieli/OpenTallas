#!/usr/bin/env python3
"""Opt-in derivative of canonical generated PC wrapper; preserve all ports/glue bytes.
No legacy generated file changes. Four channel macros per tile, effective capacities unchanged.
"""
from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parents[3]
src=r/'rtl/qwen_sys/host_cluster_20261017/qkd_hr_cdc_pc.v'
s=src.read_text();assert s.count('module qkd_hr_cdc_pc(')==1
assert s.count('ot_qwen_die_cdc_ch #(.W(546), .PIPE(2))')==2
s=s.replace('module qkd_hr_cdc_pc(', 'module qkd_hr_cdc_pc_sram(').replace('ot_qwen_die_cdc_ch #(.W(546), .PIPE(2))','ot_host_die_cdc_sram #(.W(546), .PIPE(2))')
out=r/'rtl/qwen_sys/host_cluster_20261017/qkd_hr_cdc_pc_sram.v';out.write_text(s)
print(json.dumps({'input':str(src.relative_to(r)),'input_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'output':str(out.relative_to(r)),'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'replaced_instances':2,'other_glue_changed':False},indent=2))
