#!/usr/bin/env python3
"""Extract actual native SU masters and frames; refuse variant drift, never alter parameters/cycles."""
import argparse,hashlib,importlib.util,json,pathlib,re
A=argparse.ArgumentParser();A.add_argument('partitions',type=pathlib.Path);A.add_argument('plan',type=pathlib.Path);A.add_argument('--cut-tool',type=pathlib.Path,required=True);A.add_argument('--out',type=pathlib.Path,required=True);a=A.parse_args()
s=importlib.util.spec_from_file_location('cut',a.cut_tool);M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
p=json.load(open(a.plan));out=a.out;out.mkdir(parents=True,exist_ok=True);master={};rows=[];types=[];frames=out/'frames';rtlout=out/'rtl';frames.mkdir(exist_ok=True);rtlout.mkdir(exist_ok=True)
for name,t in p['partition_types'].items():
 cores=[c for c in t.get('hard_cores',[]) if 'su_lane' in c['module']]
 if not cores:continue
 src=a.partitions/(name+'.sv');assert src.is_file(),src
 frame=src.read_text();before=frame;side=name[:3][-1]
 for c in sorted(cores,key=lambda x:int(re.search(r'\d+$',x['inst'])[0])):
  lane=int(re.search(r'\d+$',c['inst'])[0]);module=f'qfd_qc_su_lane_{side}_l{lane}'
  rtl,frame,r=M.cut(frame,lane,module)
  if module in master:assert master[module]==rtl,('current clock-type variants differ',module,name)
  master[module]=rtl;(rtlout/(module+'.sv')).write_text(rtl)
  rows.append(dict(partition_type=name,instance=c['inst'],module=module,old_module=c['module'],origin_um=c['origin_um'],outline_um=c['outline_um'],old_pins_file=c['pins_file'],input_bits=r['input_bits'],output_bits=r['output_bits'],memory_alignment=r['memory_alignment'],reset_source=r['reset_source'],source_partition_sha256=hashlib.sha256(before.encode()).hexdigest(),master_sha256=hashlib.sha256(rtl.encode()).hexdigest(),added_cycles=r['added_cycles']))
  contract=out/'cuts'/module;contract.mkdir(parents=True,exist_ok=True);(contract/'cut.json').write_text(json.dumps(r,indent=1)+'\n')
 assert before.split(');',1)[0]==frame.split(');',1)[0], ('parent ports changed',name)
 (frames/(name+'.sv')).write_text(frame);types.append(name)
rep=dict(status='SOURCE-PREP ONLY: no physical kit/plan adoption',source='fresh bind_profile3_final strict119; actual MEMORY_ALIGNMENT3/HEAD profile/witness8; no cached0 JSON',types=len(types),core_declarations=len(rows),physical_core_instances=sum(sum('su_lane' in c['module'] for c in p['partition_types'][q['type']].get('hard_cores',[])) for q in p['partitions']),native_masters=len(master),added_cycles=0,frame_ports_unchanged=True,parameter_changes=False,blockers=['Old P6 generic core pin files expose phantom ctl_o/stm_o/sc_o and truncate actual c_o. Exact master pins/clock/PG slice must replace these atomically.','Original-capture preservation plus meaningful mutant/current synthesis and native macro models required before any P&R.'],rows=rows)
(out/'source_packet.json').write_text(json.dumps(rep,indent=1)+'\n');print(json.dumps({k:v for k,v in rep.items() if k not in ['rows','blockers']}))
