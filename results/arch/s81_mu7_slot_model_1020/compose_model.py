from pathlib import Path
import json,math,copy,hashlib,collections
B=Path(__file__).parent;p=json.loads((B/'inputs/mu6_plan.json').read_text());blocks={x['name']:x for x in p['blocks']};sel=blocks['bk_sel'];host=blocks['seqhost'];rs=sorted([x for x in blocks.values() if x['kind']=='svc'],key=lambda b:b['name']);L=43.2
ceil=lambda v:math.ceil((v-1e-8)/L)*L
def overlap(a,b):return min(a['x']+a['w'],b['x']+b['w'])>max(a['x'],b['x'])+1e-6 and min(a['y']+a['h'],b['y']+b['h'])>max(a['y'],b['y'])+1e-6
oldq=(324,540);delta=4*(518.4*648-oldq[0]*oldq[1]);oldother=sel['w']*sel['h']-4*oldq[0]*oldq[1];gap=host['y']-(sel['y']+sel['h'])
parents=[]
for w,h,status in [(518.4,648,'HISTORICAL_FAIL13_SRAM_ORIGINS'),(648,648,'CORRECTED_GEOMETRY_ONLY_COLLECTOR19937f7db_NO_KIT_NO_GATE')]:
 area=oldother+4*w*h;pw=907.2;ph=max(ceil(area/pw),4*h+3*L+2*L+172.8+2*L);x=sel['x']+sel['w']/2-pw/2
 parents.append(dict(quarter_um=[w,h],quarter_status=status,quarter4_delta_mm2=(4*w*h-4*oldq[0]*oldq[1])/1e6,preserved_baseline_nonquarter_area_mm2=oldother/1e6,parent_box=dict(name='bk_sel',x=x,y=sel['y'],w=pw,h=ph),parent_reserved_delta_mm2=(pw*ph-sel['w']*sel['h'])/1e6,gap_to_seqhost_um=host['y']-(sel['y']+ph),column_side_channels_um=(1000-pw)/2,quarter_1x4_stack_height_um=4*h+3*L,quarter_gap_um=L,minimum_selector_seqhost_gap_um=100,selector_seqhost_gap_pass=host['y']-(sel['y']+ph)>=100,remaining_parent_height_um=ph-4*h,clock_pin_model='CURRENT_HISTORICAL_ONLY N ck bbox[201.960,647.962,201.978,648]; nofutureleafclockphase',data_control_edges='QUARTER+0 versusHQ3; correctedsource/parentloopageUNKNOWN',reset_boot_edges='QUARTER+0 versusHQ3; actualparentnoadditionalstageadmitted, existingstaticstrap31bits/core+2rungregions unchangedSOURCEONLY',status='REFUSED_PARENT_CLOCK_REACH_CREDIT_AND_PLACEMENT_UNPROVEN'))
# Grow16 sourceABI slots preserving exact mu6 per-column gaps and rowgap.
row0=rs[::2];xg=[row0[i+1]['x']-row0[i]['x']-row0[i]['w'] for i in range(7)];rowgap=rs[1]['y']-rs[0]['y']-rs[0]['h'];span=8*1728+sum(xg);center=(min(r['x'] for r in rs)+max(r['x']+r['w'] for r in rs))/2;x=center-span/2
new=[]
for c in range(8):
 for row in range(2):new.append(dict(name=f'rsv_{2*c+row:02d}',kind='svc',x=x,y=1724+row*(1641.6+rowgap),w=1728,h=1641.6))
 if c<7:x+=1728+xg[c]
def collisions(replacements,others):return [dict(new=a['name'],existing=b['name'],kind=b['kind']) for a in replacements for b in others if a['name']!=b['name'] and overlap(a,b)]
others=[x for x in blocks.values() if x['kind']!='svc'];cols=collisions(new,others)
# Reader insertion pushes the service start, without pretending missing reader source is adopted.
reader_y=1200+324+40;reader_h=1036.8;service_start=reader_y+reader_h+220
idxsvc=[dict(r,y=service_start+(r['y']-1724)) for r in new];idxcols=collisions(idxsvc,others)
readers=[dict(name=f'irg_{k:02d}',kind='idx',x=p['facts']['die_um'][0]/2-4250+k*1062.5+(1062.5-1036.8)/2,y=reader_y,w=1036.8,h=1036.8) for k in range(8)]
readers.append(dict(name='iqf',kind='idx',x=p['facts']['die_um'][0]/2-4250-40-259.2,y=reader_y,w=259.2,h=432))
# Explicit resource scenario: shift array864um, drop highestframe percolumn to retainreticle bound.
shift=864;shifted=[]
for a in others:
 a=copy.deepcopy(a)
 if a['kind'] not in ['phy','ctrl'] and a['group']!='south':a['y']+=shift
 shifted.append(a)
frames=[a for a in shifted if a['kind']=='frame'];top=[]
for prefix in sorted({a['name'][:4] for a in frames}):
 group=[a for a in frames if a['name'][:4]==prefix];top.append(max(group,key=lambda b:b['y']+b['h']))
# The exactnextmap is unresolved: list everycollidingframe requiringremoval ratherthan silently deletingcompute.
for c in collisions(idxsvc,[b for b in shifted if b['name'] not in {f['name'] for f in top}]):
 pass
futurecols=collisions(idxsvc,[b for b in shifted if b['name'] not in {f['name'] for f in top}]);rm={f['name'] for f in top}|{c['existing'] for c in futurecols if c['kind']=='frame'}
slots=lambda f:10 if f['h']>2800 else 9
removed=[a for a in frames if a['name'] in rm];remaining=[a for a in shifted if a['name'] not in rm];residual=collisions(idxsvc+readers,remaining)
# Wire-countlimits for a one-column quarter stack; allfourreturn+commandbundles cross theuppertrunk.
channel=(1000-907.2);m5=math.floor(channel/.048*.55);m7=math.floor(channel/.064*.55);trunk=4*(865+354+66+1)
out=dict(status='MODEL_ONLY_REFUSED_NOT_A_SELECTED_FULL_MAP',source_mu6='1b7b9d5d772008559e1b2467bc12de0fc067e2bd',baseline=dict(frames=p['facts']['n_frames'],rom_slots=p['facts']['rom_slots'],die_um=p['facts']['die_um'],frame_top_um=p['facts']['frame_top_um'],selector=sel,seqhost=host,selector_host_gap_um=gap),topk=dict(quarter_old_um=oldq,historical_hk1_area_delta_mm2=delta/1e6,fixed680_parent_height_growth_um=delta/680,fixed680_growth_hits_seqhost_um=max(0,delta/680-gap),options=parents,hard_credit_obligation='sourceparentquarter+u_c+u_g stronglyconnectedONEclockregion, SLAT4/creditdepth; extra landing requiresrescheduleproof, noautomaticrelaystages',parent_trunk=dict(bits_per_quarter=1286,four_quarter_trunk_bits=trunk,total_sidewidth_um=channel,M5_available55=m5,M7_available55=m7,two_layers_total=m5+m7,count_pass=trunk<=m5+m7,assumption='allfourreturn/commandbundles routedtosinglecontrolabove1x4stack, noPG/via allowance; countfailure evenbeforephysicalproof')),svc=dict(source='b2405769f exactcurrentABI',new_slot_um=[1728,1641.6],actual_mu6_old_slot_um=[rs[0]['w'],rs[0]['h']],area_delta_vs_actual_mu6_mm2=(16*1728*1641.6-sum(r['w']*r['h'] for r in rs))/1e6,width_growth_preserving_actual_gaps_um=span-(max(r['x']+r['w'] for r in rs)-min(r['x'] for r in rs)),x_gaps_um=xg,row_gap_um=rowgap,nonidx_collisions=cols,with_idx3_service_start_um=service_start,with_idx3_collisions=idxcols,new_boxes=idxsvc,reader_boxes=readers),resource_scenario=dict(array_shift_um=shift,dropped_frame_names=sorted(rm),dropped_rom_slots=sum(slots(f) for f in removed),remaining_frames=len(frames)-len(removed),remaining_ROM_slots=p['facts']['rom_slots']-sum(slots(f) for f in removed),density_multiplier_if_sameweights=p['facts']['rom_slots']/(p['facts']['rom_slots']-sum(slots(f) for f in removed)),residual_nonframe_collisions=residual,highest_remaining_body_um=max(b['y']+b['h'] for b in remaining),status='NOT_ADOPTED: idx3geometryonly/fullROMownermapnotyetcomposed; sourcechain/ages/reset/clock/pinplan/native/diecornersallowed'),missing_inputs=['collectorcorrectedALL32SRAMliteralgridquartersourceandnativepinperbitcontract/orientation','actualparentu_c+u_g geometry/perbitlanding/bootproducers source+nativeclockboth-edgeproof','feedbackloopSLAT4/sourcecredit reschedule ifanynewlanding; productionthroughput/causaltests','selectedidx3productionpairedreaderimmutablepass/ref andactualnewSRAMslotfit','joint16svc physicalpackingandexactcollisions/74oldrelayoverlapfix withalllanesrederived','selectedfullROM/cfgownermap andnewdiecount plusperlaneedges incompiler; no965/3kqualification'])
(B/'model.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:out[k] for k in ['baseline','topk','resource_scenario']},indent=2)[:5500])
