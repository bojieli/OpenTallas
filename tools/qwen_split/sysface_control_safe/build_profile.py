#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--profile',choices=['cold','legacy'],required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
sources=['rtl/qwen_split/qfd_sys_face.sv','rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv','rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq.sv','rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq_dies_mu.sv','rtl/qwen_split/qfd_sys_face_record_port.sv','rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv','rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv','physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v','rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_ovl_seq.sv','rtl/qwen_sys/d2d_static_20261015/qfd_d2d_cal_seq_ovl.sv','rtl/qwen_split/qfd_sys_face_accepted_mu_ctx.sv','rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_sram.sv','physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1_bb.v']
params={'MU':1,'SRAM_CAL':1,'OVL':int(a.profile=='cold'),'CTX_ACCEPTED':int(a.profile=='cold'),'COLD_PREFIX':int(a.profile=='cold'),'COLD_START_OFS':2000 if a.profile=='cold' else 0,'OVL_FIRST_OFS':20000 if a.profile=='cold' else 1176,'OVL_AW':12 if a.profile=='cold' else 11}
manifest={'profile':a.profile,'parameters':params,'supported_parameters':dict(params),'production_origin_bound':False,'source_sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources}}
out=Path(a.out);out.mkdir(parents=True,exist_ok=True);(out/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
script='read_verilog -sv -Irtl/qwen_sys/d2d_static_20261015 '+' '.join(sources)+'; hierarchy -top qfd_sys_face '+' '.join('-chparam '+k+' '+str(v) for k,v in params.items())+'; setattr -mod -unset keep_hierarchy; flatten; synth -top qfd_sys_face -flatten -noabc; write_json '+str(out/'original.json')+'; stat\n'
(out/'synth.ys').write_text(script)
