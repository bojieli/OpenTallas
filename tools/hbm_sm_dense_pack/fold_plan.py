#!/usr/bin/env python3
"""Complete35 folded geometry and explicitnewstaticretime lowerbound."""
import pathlib,json,copy,math,hashlib
R=pathlib.Path('/home/ubuntu/wt/hbm-smcompact-1014');O=pathlib.Path('results/hbm_sm_dense_pack');p=R/'results/arch/hier_contract_1011/handoff/r25gq_sm_child_origins.json';old=json.load(open(p))['sm_component'];tw,th=693.44,609.92;pitchx,pitchy=tw+20,th+20
# Two independent4-columnarms foldaftertheir secondlogicalcolumn.
xy={3:(1,3),2:(0,3),1:(0,1),0:(1,1),4:(2,3),5:(3,3),6:(3,1),7:(2,1)}
children=[]
for c in old['children']:
 c=copy.deepcopy(c);n=c['name']
 if n.startswith('g_fd'):c['x']+=302;c['y']+=10
 elif '.u_be' in n:
  i=int(n.split('[')[1].split(']')[0]);col,top=xy[i];upper=int(i in [2,3,4,5]);c['x']=10+col*pitchx+upper*(319.68+20);c['y']=10
 else:
  i=int(n.split('[')[1].split(']')[0]);pidx=int(n.split('g_p[')[1].split(']')[0]);col,top=xy[i];row=top-(1-pidx)
  # p0 north ofp1; physicalcolumn1/0 lowerwestchain turns east, mirroredtemplate.
  c['x']=10+col*pitchx;c['y']=107.76+row*pitchy;c['outline_um']=[tw,th];c['status']='NEW_TILE_HARDENING_REQUIRED'
  if i in [0,1,6,7]:c['orient']='MY'
 children.append(c)
for i,a in enumerate(children):
 for b in children[:i]:
  aw,ah=a['outline_um'];bw,bh=b['outline_um'];g=max(a['x']-b['x']-bw,b['x']-a['x']-aw,a['y']-b['y']-bh,b['y']-a['y']-ah);assert g>=-1e-5,(a['name'],b['name'])
w=max(c['x']+c['outline_um'][0]for c in children)+10;h=max(c['y']+c['outline_um'][1]for c in children)+10
shift=2*pitchy;extra=math.ceil(shift/500)-1
out={'verdict':'COMPLETE35_FOLDED_GEOMETRY_PASS_RETIME_UNBUILT','children':children,'frame_outline_um':[w,h],'frame_area_mm2':w*h/1e6,'all32_frame_mm2':32*w*h/1e6,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'logical_arms':[[3,2,1,0],[4,5,6,7]],'folds':{'column_pairs':[[2,1],[5,6]],'bands_per_arm':2,'payload_bits_per_band':3705,'external_fold_vertical_um':shift,'added_registered_edges_minimum_per_stream':extra,'added_payload_FF':4*3705*extra,'upper_gather200bit_BE_retime_FF_lowerbound':4*200*extra,'payload256_master_outlines_minimum':4*math.ceil(3705/256)*extra,'payload256_outline_area_lowerbound_um2':4*math.ceil(3705/256)*extra*25.92*43.2,'candidate_outside_fold_corridor_each_arm_um':249.6,'frame_with_twooutsidecorridors_mm2':(w+2*249.6)*h/1e6},'cycles':{'base_tile_transit':4,'base_tile_landing':1,'additional_fold_payload_cycles':extra,'required_calendar_updates':['postfoldlogicalcolumns0/1/6/7 launch/use move+2fixedcycles','newgatherreturnretimes andBEcollector alignment must becomposed','front-to-tilepaths newgeometry must bechecked; lowerbound doesnotincludeallfrontretimes']},'limits':['All35sourcechildren retained; actuallegacyfrontdynamiccredit stillmustbereplaced.','FoldFFcount is notcompletephysicalarea: all120retimeleafoutlines/gaps/PG/clockroots stillneedplacement.','Empty20um fieldchannels cannotcontain25.92um wide retimehardleaves with20umhalos.','Simpleexternal250umcorridors perarm raisebbox~11.16mm2, largelyerasefoldbenefit.','Absorbretimecells insideunhardenedtileparent freearea orpartitioncompilercalendar roots beforeadoption; nooverlappinghardframes.','Allfront-to-tile andBEactualpinseams unqualified; nohiddenzero-stageroute assumption.']}
(O/'fold35.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['frame_outline_um','frame_area_mm2','all32_frame_mm2','folds']},indent=2))
