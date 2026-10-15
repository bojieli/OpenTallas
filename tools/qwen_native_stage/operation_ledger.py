#!/usr/bin/env python3
"""Account for every emitted operation without upgrading component evidence.

Decoded flags describe semantic dependencies; production scheduling must be a
separate compiler calendar. A candidate RTL path never proves a completed join.
"""
import argparse,hashlib,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--isa-root',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--program',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.isa_root/'tools'));import hdc_qwen_fullshape_isa_w12 as I
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=a.program.read_bytes();rows=[]
for pc,word in enumerate(raw.split()):
 d=I.decode_instruction(int(word,16));u=d['unit'];sources=['rtl/qwen_sys/static_schedule_20261014/ot_qwen_rom_core_ctrl_su_static.sv']
 if u==2:
  sources+=['rtl/qwen_split/qfd_sp_su64_sfu.sv','rtl/qwen_sys/static_schedule_20261014/ot_qfd_sp_su64_static_entries.sv','rtl/qwen_sys/static_schedule_20261014/ot_hdc_vstream_static_entries.sv','rtl/hdc/ot_hdc_vstream_lane.sv','rtl/hdc/ot_hdc_fastfp.sv']
  if d.get('sfu'):sources+=['rtl/hdc/ot_hdc_sfu.sv']
  if d.get('red'):sources+=['rtl/physical/ot_hdc_vreduce_entries64.sv']
  operands={k:{f:d.get(k+'_'+f,0) for f in ['src','base','so','si','d']} for k in 'abc'}
  storage='mapped NOX VM via actual A/B/C ports; constant operands require actual CROM; KV destination requires actual formatter/remote writer'
  candidate='u_math.u_su; qfd_sp_su64_sfu actual64 lanes'
 elif u==1:
  sources+=['rtl/qwen_sys/static_schedule_20261014/ot_qwen_rom_core_ctrl_static.sv']
  operands={k:d[k] for k in d if k.startswith('me_') and d[k]}
  storage='actual weight ROM/scale and mapped VM operands/results; native attention for me_wsrc1'
  candidate='actual ME/attention producer path not instantiated by embedding-stage harness'
 else:
  operands={};storage=None;candidate='actual controller fixed owner END; full layer calendar not yet measured'
 pins={name:sha((a.source_root/name).read_bytes()) for name in sources if (a.source_root/name).is_file()}
 rows.append(dict(pc=pc,unit=u,instruction_sha256=sha(int(word,16).to_bytes(128,'little')),decoded={k:v for k,v in d.items() if v},candidate_arithmetic=candidate,operand_ports=operands,required_storage_join=storage,source_sha256=pins,runtime_native_join_verified=False,blocking_evidence='exact source operation -> actual producer/calendar -> arithmetic -> mapped storage runtime plus mutant and native profile still required',source_dependency_flags={k:d[k] for k in ['barrier','wait_me','wait_su','chase','chase_rows'] if d.get(k)}))
a.out.write_text(json.dumps(dict(scope='exhaustive source operation ledger for the supplied rank program; candidate paths only',program_sha256=sha(raw),operations=rows,count=len(rows),full_native_token=False,proven_native_operations=0,embedding_stage_note='Separate two-instruction token151935 arithmetic/mapped SRAM stage remains BUILD_PENDING until collected; not evidence for these layer PCs'),indent=2)+'\n')
print('ACCOUNTED_OPERATIONS',len(rows),'VERIFIED_FULL_LAYER_JOINS',0)
