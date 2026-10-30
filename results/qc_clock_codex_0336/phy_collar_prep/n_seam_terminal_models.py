import json,gzip,re,sys,math
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan');import die_clock_128 as D
p=json.load(open('/tmp/qcclock0336/n_seam_repeaters_prep.json'));q=json.load(open('/tmp/qcclock0336/n_seam_coupler_prep.json'));byname={b['bus']+'['+str(b['bit'])+']':b for b in q['bits']};cells={c['id']:c for c in p['cells']}
# Independent R0 placement underMX: translate eachreservedR0slot to realnegativeR0row, never mirror cellorientation/halfrow.
south={}
for n,c in cells.items():
 x,y=c['origin_um'];sy=-y-.54;kind=c.get('kind','BUF24');south[n]={'id':n,'origin_um':[x,sy],'A_um':[x+(.058 if kind=='BUF8' else .048),sy+.135],'Y_um':[x+(.416 if kind=='BUF8' else .956),sy+.234]}
mxrows=[]
for r in p['bits']:
 b=byname[r['bus']+'['+str(r['bit'])+']'];length=b['wire_native_to_existing_face_pin_um'];steps=math.ceil(length/60);fr=[j/steps for j in range(1,steps)]
 rev=r['flow_direction']=='existingFF_to_native'
 if rev and (not fr or (1-fr[-1])*length>20):fr.append(max(0,1-20/length))
 fr=sorted(set(fr));yy=-b['track_height_um'];nativex=b['polyline_um'][0][0];outerx=b['polyline_um'][-1][0];cur=[outerx,0] if rev else[nativex,.096];pr=2 if rev else 0;tot=0;mm=0
 def region(t):
  d=t*length;return 0 if d<=-yy+.096 else 2 if d>=-yy+.096+abs(nativex-outerx) else 1
 order=list(enumerate(r['repeaters']));order=order[::-1] if rev else order
 for i,n in order:
  c=south[n];reg=region(fr[i]);dest=c['A_um'];ll=abs(cur[0]-dest[0])+abs(cur[1]-dest[1]) if pr==reg and reg in[0,2] else abs(cur[1]-yy)+abs(cur[0]-dest[0])+abs(yy-dest[1]);tot+=ll;mm=max(mm,ll);cur=c['Y_um'];pr=reg
 dest=[nativex,.096] if rev else[outerx,0];reg=0 if rev else 2;ll=abs(cur[0]-dest[0])+abs(cur[1]-dest[1]) if pr==reg else abs(cur[1]-yy)+abs(cur[0]-dest[0])+abs(yy-dest[1]);tot+=ll;mm=max(mm,ll);mxrows.append({'bus':r['bus'],'bit':r['bit'],'total_with_existingFF30_um':tot+30,'max_section_um':mm})
models={}
for co in ['TT','FF']:
 txt=gzip.open(f'/home/ubuntu/.cache/opentallas/asap7_nldm/asap7sc7p5t_INVBUF_RVT_{co}_nldm_220122.lib.gz','rt').read();models[co]={}
 for pin,master,driver,target,yh,load in [('clk','BUFx24_ASAP7_75t_R',p['summary']['nativeclk_BUF_body'],[753.288,-.096],2.208,50.0),('rst_n','BUFx8_ASAP7_75t_R',p['summary']['native_reset_BUF_body'],[753.336,-.096],2.400,1.2399)]:
  native=(Path('/home/ubuntu/OpenTallas/physical/qwen_missing_phy/nface_tall_1017/ot_qfd_serdes_112g_x12_phy_s597')/f'ot_qfd_serdes_112g_x12_phy_s597_{co.lower()}.lib').read_text();nativepin=native.split('pin ('+pin+')')[1];load=float(re.search(r'capacitance\s*:\s*([\d.]+)',nativepin)[1]);i=txt.index('cell ('+master+')');j=txt.find('cell (',i+10);b=txt[i:j];out=driver['Y_um'];h=abs(out[0]-target[0]);v5=abs(yh-target[1]);v7=abs(out[1]-yh);cw=1.7*(h*.187426+v5*.164264+v7*.162979);rw=h*.0118796+v5*.0189935+v7*.0125096;el=rw*(cw/2+load)+.0752*(cw+load);tabcap=load+cw;dd=max(D._bilin(D._table(b,k),80,tabcap) for k in['cell_rise','cell_fall']);ss=max(D._bilin(D._table(b,k),80,tabcap) for k in['rise_transition','fall_transition']);models[co][pin]={'master':master,'model_input_slew_ps':80,'native_pin_load_ff':load,'actual_M5_target_um':target,'M6_H_track_um':yh,'wire_um':h+v5+v7,'wireC_with1p7_ff':cw,'total_driver_load_ff':tabcap,'delay_model_ps':dd+el,'native_pin_transition_model_ps':math.hypot(ss,2.2*el),'scope':'LumpedconservativewireElmore + actualviaR; terminalM5stubunshielded1p7guard. Physicalsource/clocknativeinternalframeandresetwavearrivalnotknown.'}
summary={'status':'N/S terminal construction MODEL PREP only; nativeportshapespreserved','N':p['summary'],'S_MX_R0':{'dataFF_added':0,'cells':len(south),'x_off54nm':sum(abs(c['origin_um'][0]/.054-round(c['origin_um'][0]/.054))>1e-6 for c in south.values()),'y_offR0_540nm':sum(abs(c['origin_um'][1]/.54-round(c['origin_um'][1]/.54))>1e-6 for c in south.values()),'max_segment_um':max(r['max_section_um'] for r in mxrows),'max_total_with_FF30_um':max(r['total_with_existingFF30_um'] for r in mxrows),'paths_over405':sum(r['total_with_existingFF30_um']>405 for r in mxrows),'placement_rule':'BodyoriginS=-originN-.54 onactualR0rows; no mirroredcellorientation orhalfrow.'},'native_terminal_electrical':models,'clock_reset_track_separation':'M6clock2.208/reset2.400,192nmseparation leavesroomforclockshieldtracks; actualnativeM5clock/resetadjacent48nm preserved, final~2.3umM5stubhasnoclaim ofdouble-sidedshield.','native_missionreset':'Dataunreset/epochs remainexistingwrappersemantics; onlytransparentcombresetdriverproposed. NoextraSTART/controlFFassumedinsidebarePHY. Actualreset/STARTcountsalignmentmustberebound.','no_cycles_added':True}
Path('/tmp/qcclock0336/n_s_terminal_models.json').write_text(json.dumps({'summary':summary,'S_cells':south,'S_bits':mxrows},indent=1)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='N'},indent=2))
