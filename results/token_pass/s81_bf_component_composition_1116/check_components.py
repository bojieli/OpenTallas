from pathlib import Path
import os,json,sys
r=Path('/srv/opentallas-scratch2/claude/tok-verify-2/recovery1116/ds_current_compile1116')
code=r/'code_bf_components_2240';source=r/'source_bf_components_2240'
a=json.loads((source/'physical/die_plan/s81/bind/frame_asbuilt.json').read_text())
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OT_S81_SELECTED_SOURCE_ROOT=str(source),OT_S81_SELECTED_ASBUILT_MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json',OT_S81_SELECTED_DEFINES=','.join(a['defines']),OT_S81_FRAME_SOURCE_ROOT=str(source),OT_S81_FRAME_ASBUILT_MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json',OT_S81_FRAME_PLAN='/srv/opentallas-scratch2/claude/s81-b3-clk/ev/B6gF2s4tapfix1.json',OT_XS_ASB_SCHEDULE_DIR=str(r/'profiles'))
sys.path[:0]=[str(code/'tools/s81_dv/layer_prog'),str(code/'tools/s81_dv'),str(code/'tools')]
import xs_bf as XB
records=json.loads((r/'bf_components_2240/records.json').read_text());out=[]
for scoped,rec in sorted(records.items()):
 frame,key=scoped.split('::');shape=key.split('|')[0];master,variant=shape.split('_asb_');fv='asb_'+variant
 selected,how=XB.meas_for(records,master,2,fv,op='attn.wo_a',frame_instance=frame)
 assert how=='component_composition_bf_idle_q'
 pairs=sorted(int(v) for v in rec['fits']);values=[[0x3f800000+17*i] for i in range(6)]
 plan=XB.bf_plan(master,pairs,values,0,4,dict(selected,calendar=how),[0]*3,frame=fv,frame_instance=frame)
 assert plan['faults']==0,(frame,plan['faults'])
 assert plan['ret_words']==6,(frame,plan['ret_words'])
 assert sorted(w[2] for w in plan['ret'])==sorted(x[0] for x in values),(frame,'payload')
 out.append(dict(frame=frame,scope=how,returns=plan['ret_words'],faults=plan['faults'],first=plan['ret'][0][0],last=plan['ret'][-1][0],input_shifts=rec['asbuilt_source_qualification']['component_composition']['input_shifts']))
(r/'bf_components_2240/component_composition_result.json').write_text(json.dumps(dict(status='COMPONENT_COMPOSITION_PASS',scope='unchanged BF kernel native replay plus exact source-traced input shifts/current return topology; six finite synthetic partials per frame; no new RTL runtime or physical qualification',frames=out),indent=1)+'\n')
print('BF_COMPONENT_COMPOSITION_PASS',len(out),'frames',len(out)*6,'exact_return_words')
