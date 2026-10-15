#!/usr/bin/env python3
"""Typed CP image-format mechanism fixture; not a native timing calibration."""
from pathlib import Path
import sys,copy,json
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from qwen_static_schedule.issue_rom import pw_image
from qwen_static_schedule.calendar import ScheduleError

def check():
 command=(64<<49)|(8192<<25)|(8192<<1)|1
 events=[dict(stage=37,pc=7,kind='owner_end',owner=1,time_fs=600),dict(stage=37,pc=7,kind='owner_end',owner=2,time_fs=610)]
 events += [dict(stage=37,kind='copy_issue',target_pc=pc,time_fs=t,cp56_hex=f'{command:014x}',rtl_instance='format_fixture.copy',rtl_module='qfd_su_static_copy',requires=['actual_source_image'],produces=['actual_masked_writes'])for pc,t in [(4,60),(5,200),(6,340)]]
 issues=[dict(stage=37,pc=pc,unit=2,time_fs=t)for pc,t in [(0,5),(1,10),(2,20)]]+[dict(stage=37,pc=pc,unit=1,time_fs=t)for pc,t in [(3,40),(4,180),(5,320),(6,460)]]+[dict(stage=37,pc=7,unit=0,time_fs=600)]
 fixture=dict(issues=issues,events=events)
 def image(f):return pw_image(f,37,dict(period_fs=1,phase_fs=0,stop_cycle=600),dict(period_fs=1,phase_fs=0,stop_cycle=610),8)
 output=image(fixture);by_addr={r['address']:int(r['data_hex'],16)for r in output}
 assert [by_addr[a] for a in (1019,1020,1021)]==[command]*3
 assert [((by_addr[a]>>44)&3,(by_addr[a]>>32)&4095,by_addr[a]&0xffffffff)for a in range(976,984)]==[(1,3,40),(3,4,60),(1,4,180),(3,5,200),(1,5,320),(3,6,340),(1,6,460),(0,7,600)]
 assert by_addr[1017]&63==8
 def reject(name,change):
  f=copy.deepcopy(fixture);change(f)
  try:image(f)
  except ScheduleError:return name
  raise AssertionError(name+' accepted')
 cases=[reject('before_previous_ME',lambda f:f['events'][3].update(time_fs=50)),reject('missing_source_attribution',lambda f:f['events'][2].pop('rtl_module')),reject('after_consumer',lambda f:f['events'][2].update(time_fs=181)),reject('conflicting_edge',lambda f:f['events'][2].update(time_fs=40))]
 out=ROOT/'results/rtl/qwen_q_export_1014/static_internal/cp_serializer.json';out.write_text(json.dumps(dict(scope='format fixture only; actual fullstage native microevent calendar remains required',positive='ME8 actual format fits4ME+3CP+END; separateSU END610',rejected=cases,PW=output),indent=2)+'\n')
 print('PASS CP56/PW typed image; malformed timing/source-attribution fixtures rejected')
if __name__=='__main__':check()
