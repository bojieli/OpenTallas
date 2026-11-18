from pathlib import Path
import json,os,sys,shutil,hashlib
r=Path('/tmp/token_ds_followthrough1116');source=r/'source';out=r/'current_schedules';out.mkdir(exist_ok=False)
refs=[('u_f_0L02','fsa_h9_p2'),('u_f_0R02','fsa_h9_p5r2'),('u_f_0L03','fsa_h9_nx'),('u_f_0L01','fsa_h10_x')]
for frame,run in refs:
 d=out/'frames'/frame;d.mkdir(parents=True)
 for p in (r/run).glob('*_schedule.json'):shutil.copy2(p,d/p.name)
 for p in (r/run).glob('*_check.json'):shutil.copy2(p,d/p.name)
shutil.copy2(r/'gb_component/qualification/gb_provider_qualification.json',out/'gb_provider_qualification.json')
os.environ.update(OT_XS_ASB_SCHEDULE_DIR=str(out),OT_S81_FRAME_SOURCE_ROOT=str(r/'f2s4_source'),OT_S81_FRAME_ASBUILT_MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json',OT_S81_FRAME_PLAN=str(r/'f2s4_source/selected_plan.json'))
sys.path[:0]=[str(source/'tools'),str(source/'tools/s81_dv'),str(source/'tools/s81_dv/layer_prog')]
import lower_xs as X
rows=[]
for frame,run in refs:
 p=next((r/run).glob('*_schedule.json'));master=p.name.removesuffix('_schedule.json')
 got=X.source_frame_schedule(master,frame);rows.append(dict(frame=frame,master=master,path=str(got),sha256=hashlib.sha256(got.read_bytes()).hexdigest(),status='PASS_SOURCE_AND_PROVIDER_JOIN'))
wrong=r/'foreign_scope_control';(wrong/'frames/u_f_0R02').mkdir(parents=True)
for p in (out/'frames/u_f_0L02').iterdir():shutil.copy2(p,wrong/'frames/u_f_0R02'/p.name)
shutil.copy2(out/'gb_provider_qualification.json',wrong/'gb_provider_qualification.json')
os.environ['OT_XS_ASB_SCHEDULE_DIR']=str(wrong)
try:X.source_frame_schedule('col_h9_l4_lp_asb_x','u_f_0R02')
except ValueError as e:
 assert 'another actual instance' in str(e);control={'status':'CAUGHT','reason':str(e)}
else:raise AssertionError('foreign frame scope was admitted')
(r/'frame_profile_join.json').write_text(json.dumps({'schema':'opentallas.s81.actual-frame-profile-join.v1','status':'PASS_COMPONENT_SOURCE_JOIN','rows':rows,'foreign_frame_control':control,'GB_QUAL_USED':X.GB_QUAL_USED,'production_enabled':False,'full_layer_compiled':False},indent=2)+'\n')
print('ACTUAL_FRAME_PROFILE_JOIN_PASS',len(rows),'FOREIGN_FRAME_CAUGHT')
