#!/usr/bin/env python3
"""Lower actual Qwen source bytes through the selected dense TT/SU consumers.

No profile template carries production timings. Missing measured path contracts
produce a structured refusal and no installable writes.
"""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qwen_static_schedule.segments import program_segments,physical_profile,MissingPhysicalProfile
from qwen_static_schedule.dense_image import build
from qwen_static_schedule.calendar import ScheduleError

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--program',type=Path,required=True);p.add_argument('--descriptors',type=Path,required=True)
 p.add_argument('--stage',type=int,required=True);p.add_argument('--plan',type=Path)
 p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 raw=a.program.read_bytes();d=[int(v,16)for v in a.descriptors.read_text().split()]
 if len(d)>8:raise ScheduleError('actual descriptor store has eight words')
 d += [0]*(8-len(d));plan={}if a.plan is None else json.loads(a.plan.read_text())
 report=dict(schema='opentallas.qwen-production-stage-lowering.v1',stage=a.stage,
  source_program_sha256=hashlib.sha256(raw).hexdigest(),source_descriptor_sha256=hashlib.sha256(a.descriptors.read_bytes()).hexdigest(),
  segments=program_segments(raw,d))
 try:
  physical_profile(plan.get('segment_profile',{}),raw)
  report['image']=build(raw,d,plan['calendar'],a.stage,plan['me_clock'],plan['su_clock'],
    plan['xpf_rows'],plan['xpf_stop'],plan['collective_clock'],plan['segment_profile'])
  report['status']='LOWERED_RECEIVER_WITNESSES_REQUIRED';code=0
 except MissingPhysicalProfile as e:
  report.update(status='REFUSED_MISSING_PHYSICAL_PROFILE',missing_fields=e.missing_fields);code=2
 except (ScheduleError,KeyError)as e:
  report.update(status='REFUSED_INVALID_PRODUCTION_CONTRACT',error=str(e));code=2
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n')
 print(report['status']);return code
if __name__=='__main__':sys.exit(main())
