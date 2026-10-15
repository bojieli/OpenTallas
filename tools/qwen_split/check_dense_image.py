#!/usr/bin/env python3
"""Dense-image format/control-store fixture; native timing remains uncalibrated."""
from pathlib import Path
import sys,hashlib,subprocess,json
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from qwen_static_schedule.dense_image import build,native_capability
from qwen_static_schedule.calendar import ScheduleError

def fixture(program_bytes):
 stage=37;command=(64<<49)|(8192<<25)|(8192<<1)|1
 events=[dict(stage=stage,pc=7,kind='owner_end',owner=1,time_fs=600),dict(stage=stage,pc=7,kind='owner_end',owner=2,time_fs=610)]
 events += [dict(stage=stage,kind='copy_issue',target_pc=pc,time_fs=t,cp56_hex=f'{command:014x}',rtl_instance='format_fixture.copy',rtl_module='qfd_su_static_copy',requires=['actual_source_image'],produces=['actual_masked_writes'])for pc,t in [(4,60),(5,200),(6,340)]]
 issues=[dict(stage=stage,pc=pc,unit=2,time_fs=t)for pc,t in [(0,5),(1,10),(2,20)]]+[dict(stage=stage,pc=pc,unit=1,time_fs=t)for pc,t in [(3,40),(4,180),(5,320),(6,460)]]+[dict(stage=stage,pc=7,unit=0,time_fs=600)]
 cal=dict(issues=issues,events=events,program_sha256={stage:hashlib.sha256(program_bytes).hexdigest()})
 pf=(1<<71)|(8<<53)|(9<<49)|(1<<37)|(8<<25)|(8192<<1)|1
 rows=[]
 for unit,pc,issue,arm,first in [(2,2,20,34,50),(3,4,60,64,80),(3,5,200,204,220),(3,6,340,344,360)]:
  value=(first<<156)|(issue<<124)|(arm<<92)|(stage<<86)|(unit<<84)|(pc<<72)|pf
  rows.append(dict(cfg_data_hex=f'{value:047x}'))
 return build(program_bytes,[0]*8,cal,stage,dict(period_fs=1,phase_fs=0,stop_cycle=600),dict(period_fs=1,phase_fs=0,stop_cycle=610),rows,605,dict(period_fs=1,phase_fs=0,stage_start_cycle=0,relay_edges=0,stop_cycle=600,command_pin_edges=1),format_only=True)

def check():
 program=subprocess.check_output(['git','show','origin/main:results/arch/qwen_tp8_native_dispatch_1014/token_source_plan/head_program_rank7.hex'],cwd=ROOT)
 image=fixture(program);assert len(image['writes'])==1032 and not image['fused_native59_capability']
 footer=int(image['footer_hex'],16);assert footer>>32==0x58504631 and footer&3==2 and (footer>>6)&63==37 and (footer>>2)&15==4
 native_program=subprocess.check_output(['git','show','origin/main:results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex'],cwd=ROOT)
 words=[int(w,16)for w in native_program.split()];assert native_capability(words,1)
 words[11]^=1<<152
 try:native_capability(words,1)
 except ScheduleError:pass
 else:raise AssertionError('noncanonical native instruction installed a fused capability')
 out=ROOT/'results/rtl/qwen_q_export_1014/dense_controller_join/dense_image_format.json';out.write_text(json.dumps(dict(scope='actual source ISA image format/control-store fixture; not native microevent calibration',head_source_SHA256=hashlib.sha256(program).hexdigest(),footer=image['footer_hex'],authorized_digest=image['authorized_digest_hex'],PW=1024,DW=8,native_capability='actual PC11 PASS; modified native instruction rejected'),indent=2)+'\n')
 print('PASS dense1024PW+8DW footer, actual-source nativecap derivation and capability mutant rejection')
if __name__=='__main__':check()
