#!/usr/bin/env python3
"""Constructive32SM expanded HBM service reservation before RTL.

Retained actual ODB bodies keep all macros, cells, OBS and PDN exclusions.
New bank routes use explicit rectangles and finite technology track positions.
Unplaced original FFs and unbound cone routes remain failed admission gates.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path
import h4_v1_g0_model as V
import h4_v1_physical_join as P
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'results/uarch/h4_v1_expanded_service_20261002/inputs'
BASE='results/uarch/full_sm_actual_parent_route_20261002/'
PIN='8ba2400b7d910b79fe2d5eec32d293cff4cb5dc3'
OUTLINE_PIN='6ce60f8ea4a8eb7ce809d90840415bddc5cd0cd8'
BANK_W=450.;BANK_H=508.;COL_GAP=226.8;ROW_GAP=576.;CONTROL_H=112.;BODY_GAP=32.;WIRE_UPPER=.81


def overlap(a,b):return max(a[0],b[0])<min(a[2],b[2])-1e-6 and max(a[1],b[1])<min(a[3],b[3])-1e-6

def rect(x,y,w,h):return [x,y,x+w,y+h]

def contained(a,b):return a[0]>=b[0]-1e-6 and a[1]>=b[1]-1e-6 and a[2]<=b[2]+1e-6 and a[3]<=b[3]+1e-6

def positions(start,end,origin,pitch):
    lo=max(0,math.ceil((start-origin)/pitch));hi=math.floor((end-origin)/pitch)
    return max(0,hi-lo+1)


def track_capacity(grid,axis,low,high,layers):
    """Extend source process lattices into new explicit geometry, keep50% seats.

    Existing finite parent track vectors are never credited outside their body;
    candidate extensions require future PDN/clock/via binding, not new layers.
    """
    result={}
    for g in grid['grids']:
        if g['layer'] in layers:
            # Deduplicate repeated database patterns by offset and pitch.
            patterns={(origin,pitch) for origin,count,pitch in g[axis]}
            if len(patterns)!=1:raise ValueError('single upper process lattice required')
            o,p=next(iter(patterns));n=positions(round(low*1000),round(high*1000),o,p)
            result[g['layer']]=dict(raw_tracks=n,signal_tracks=n//2,PG_clock_via_reserved_tracks=n-n//2,pitch_DBU=p,origin_DBU=o)
    if set(result)!=set(layers):raise ValueError('source track layer gate')
    return result


def cut(grid,axis,low,high,layers,demand,owner,coordinate):
    cap=track_capacity(grid,axis,low,high,layers);total=sum(c['signal_tracks'] for c in cap.values())
    return dict(owner=owner,axis=axis,coordinate_um=coordinate,span_um=[low,high],layers=cap,demand_tracks=demand,signal_capacity_tracks=total,margin_tracks=total-demand,screen_pass=total>=demand,
        demand_scope='dedicated source-interface reservation upper; not a routed-net measurement',actual_new_PDN_bound=False)


def provider_location(vector,lane,copy):
    """Exact original H1 RF address decomposition into proposed physical banks.

    C0 resolves the actual source home/vector first. This does not allocate a
    version, decode HBM addresses or synthesize a checkpoint/mutable KV home.
    """
    if any(type(v)is not int for v in (vector,lane,copy)) or not 0<=vector<512 or not 0<=lane<128 or copy not in (0,1):raise ValueError('source9bit RF vector,7bit lane,physical mirror required')
    bank=lane>>3;page=vector>>7
    return dict(macro=f'RF.b{bank}.p{page}.copy{copy}',row=vector&127,word=lane&7,bank=bank,page=page,copy=copy,bit_offset=32*(lane&7))


def latency_delta(read_pairs,writes,*,outward_hops,return_hops,hop_ticks=1):
    vals=[read_pairs,writes,outward_hops,return_hops]
    if any(type(x)is not int or x<0 for x in vals) or type(hop_ticks)is not int or hop_ticks<=0:raise ValueError('finite transaction counts and positive provisional transport cost')
    return dict(read_pairs=read_pairs,write_vectors=writes,added_ticks=(read_pairs+writes)*(outward_hops+return_hops)*hop_ticks,
        RF_baseline_II=[3,2],RF_baseline_recharged=False,C0_front_recharged=False,I64_RMW_recharged=False,
        scope='incremental request/return distance only; existing Dewey intervals retained once',measured=False)


def bank_service(h1,v1,grid,c0,name,rf_provider_grid=None):
    body=0;macros=[];logic=[];cuts=[]
    # Entire C0 scoreboard/control lives once in the central strip. H1 SIMD128
    # and V1 lanes32 split into16 banks, respectively8 and2 lanes per bank.
    upper_logic=h1['logic_area_estimate_um2']+v1['area']['logic_um2_range'][1]+153.6
    pipe_hops=math.ceil((4*BANK_W+4*BANK_H+CONTROL_H)*WIRE_UPPER/(1000/1.2-60))
    bank_pipeline_bits=(pipe_hops-1)*(512+128+64)*2
    per_bank_footprint=2*upper_logic/16+2*bank_pipeline_bits*.2916
    provider=grid if rf_provider_grid is None else rf_provider_grid
    master=provider['macro_master_OBS']['ot_sram_1r1w_128x256_m1_r2c2']
    if master['size']!=[94824,41040] or {o['layer'] for o in master['OBS']}!={'M1','M2','M3','M4'}:raise ValueError('source shallow RF macro/OBS gate')
    master_name=next(n for n,m in grid['macro_master_OBS'].items() if '1024x256' in n)
    scratch=grid['macro_master_OBS'][master_name]['size'];sw,sh=[a/1000 for a in scratch]
    for bank in range(16):
        bx=(bank%4)*BANK_W;by=(bank//4)*BANK_H
        for page in range(4):
            for copy in range(2):
                x=bx+copy*102.824;y=by+page*49.04
                macros.append(dict(name=f'RF.b{bank}.p{page}.copy{copy}',master='ot_sram_1r1w_128x256_m1_r2c2',halo_bbox_um=rect(x,y,102.824,49.04),body_bbox_um=rect(x+4,y+4,94.824,41.04),OBS_layers=['M1','M2','M3','M4'],physical_read_ports=1,physical_write_ports=1))
        box=rect(bx+216,by,232,300)
        if 232*300<per_bank_footprint:raise ValueError('bank composed logic slot fails upper bound')
        logic.append(dict(bank=bank,bbox_um=box,required_footprint_um2=per_bank_footprint,capacity_footprint_um2=232*300,H1_SIMD_lanes=8,V1_lanes=2,lane_mapping='lane=8*bank+local_lane; V1 two local lanes folded over four groups; per-lane source arithmetic unchanged'))
        # Conservative parallel page buses, host+SIMD transports, full C0
        # local command/metadata/control reservation, and V1 local incidences.
        demand=2048+256+int(c0['routing']['new_control_tracks_local'])+math.ceil(v1['routing']['local_tracks_upper']/16)+128
        # All macro-edge cuts plus the macro/logic split use upper metal only.
        xs=sorted({bx,bx+102.824,bx+205.648,bx+216,bx+448,bx+BANK_W})
        ys=sorted({by+49.04*p for p in range(5)}|{by+300,by+BANK_H})
        for x in xs:cuts.append(cut(grid,'Y',by,by+BANK_H,['M6','M8'],demand,f'bank{bank}/Xcut',x))
        for y in ys:cuts.append(cut(grid,'X',bx,bx+BANK_W,['M7','M9'],demand,f'bank{bank}/Ycut',y))
    control_y=4*BANK_H
    for i in range(2):macros.append(dict(name=f'scratch{i}',master=master_name,halo_bbox_um=rect(i*(sw+8),control_y,sw+8,sh+8),body_bbox_um=rect(i*(sw+8)+4,control_y+4,sw,sh),OBS_layers=sorted({o['layer']for o in grid['macro_master_OBS'][master_name]['OBS']})))
    c0box=rect(400,control_y,1400,CONTROL_H)
    if 1400*CONTROL_H<2*c0['area']['logic_um2_per_SM']:raise ValueError('central C0 slot upper bound')
    c0cuts=[cut(grid,'X',0,4*BANK_W,['M7','M9'],c0['routing']['new_control_tracks_local']+576,'C0/bank fanout',control_y)]
    boxes=[(m['name'],m['halo_bbox_um'])for m in macros]+[(f'logic{b["bank"]}',b['bbox_um'])for b in logic]+[('C0',c0box)]
    conflicts=[(a,c)for i,(a,b)in enumerate(boxes)for c,d in boxes[i+1:]if overlap(b,d)]
    if conflicts:raise ValueError('service exclusion conflict '+str(conflicts[:2]))
    return dict(width_um=4*BANK_W,height_um=4*BANK_H+CONTROL_H,RF_macros=128,scratch_macros=2,macro_placements=macros,logic_slots=logic,C0_logic_bbox_um=c0box,C0_required_footprint_um2=2*c0['area']['logic_um2_per_SM'],all_service_macro_logic_conflicts=conflicts,bank_cuts=cuts,C0_cuts=c0cuts,
        service_cut_screens_pass=all(c['screen_pass']for c in cuts+c0cuts),same_process_layers_only=True,
        macro_OBS_crossed=False,bank_routes_scope='Constructive upper-metal bank reservation; no retained TC body or FF coordinates borrowed',
        current_H1_netlist_implements_bank_local_join=False,RF_atomic_owner_credit=1,bank_response_accept='all16 bank returns captured for same C0 ticket; no partial vector publication',
        transport_pipeline_hops=pipe_hops,bank_pipeline_bits_each=bank_pipeline_bits,
        extra_register_bits_proposed=16*(512+128+64)*2*pipe_hops,extra_register_area_um2=16*(512+128+64)*2*pipe_hops*.2916,
        central_endpoint_register_area_um2=16*(512+128+64)*2*.2916,
        transport_state_scope='two direction buffers per bank, positive finite credit; additional footprint must be reconciled before admission')


class ProviderAtomicFence:
    """Finite16-bank fence model using the Sagan C0 owner tuple ABI.

    Models acceptance/visibility only, never executes source arithmetic or a
    host oracle. Addresses must be the actual RF homes resolved by C0. This
    exports the contract required of the future connected provider gateway.
    """
    def __init__(self,**owner_context):
        self.owner=P.SerializedOwner(**owner_context);self.kind=None;self.mask=0

    def accept(self,ticket,source_RF_addresses,destination_RF_addresses):
        self.owner.accept(ticket,source_RF_addresses,destination_RF_addresses)

    def read(self,ticket):
        result=self.owner.read(ticket);self.kind='read';self.mask=0;return result

    def bank_return(self,ticket,bank,*,stalls=0):
        self.owner._own(ticket)
        if self.kind!='read' or type(bank)is not int or not 0<=bank<16 or self.mask&(1<<bank):raise ValueError('owned unique bank read return required')
        self.owner._stalls(stalls)
        if self.mask and stalls!=self.stalls:raise ValueError('aggregate vector stall count must agree')
        self.stalls=stalls;self.mask|=1<<bank
        if self.mask==65535:self.owner.return_read(ticket,stalls=stalls);self.kind=None

    def complete(self,ticket,*,native_ticks):self.owner.complete(ticket,native_ticks=native_ticks)

    def write(self,ticket):
        result=self.owner.write(ticket);self.kind='write';self.mask=0;return result

    def bank_ACK(self,ticket,bank,mirror,*,stalls=0):
        self.owner._own(ticket)
        if self.kind!='write' or type(bank)is not int or not 0<=bank<16 or type(mirror)is not int or mirror not in (0,1):raise ValueError('owned bank/mirror ACK required')
        bit=1<<(2*bank+mirror)
        if self.mask&bit:raise ValueError('duplicate physical mirror ACK')
        self.owner._stalls(stalls)
        if self.mask and stalls!=self.stalls:raise ValueError('aggregate vector stall count must agree')
        self.stalls=stalls;self.mask|=bit
        if self.mask==2**32-1:
            self.owner.ack(ticket,0,stalls=stalls);self.owner.ack(ticket,1,stalls=stalls);self.kind=None

    def consumer(self,ticket):self.owner.consumer(ticket)
    def retire(self,ticket,*,reverse_grant):self.owner.retire(ticket,reverse_grant=reverse_grant)
    def unrelated_request_ready(self):return self.owner.unrelated_request_ready()


def build():
    joined=P.build();blobs=P.facts();h1=json.loads(blobs['H1']);v1=json.loads(blobs['V1']);c0=json.loads(blobs['C0']);capacity=V.load(PIN,BASE+'actual_geometry_capacity.json');parent=V.load(PIN,BASE+'model.json')
    if '0.72-0.81 ps/um' not in blobs['unified'].decode():raise ValueError('source loaded-wire uncertainty range gate')
    private_source=V.pinned(V.C0,'tools/qwen_hbm_shoreline_remedy_r10.py').decode()
    if '1698/v_tracks' not in private_source or '1698/h_tracks' not in private_source:raise ValueError('private provider source wire-count gate')
    models={};inputpins={}
    for name,key in [('Qwen','Qwen'),('DeepSeek','DS')]:
        gp=INPUT/(key+'_geometry.json.gz');gr=INPUT/(key+'_grid.json');gb=gp.read_bytes();rb=gr.read_bytes()
        if hashlib.sha256(gb).hexdigest()!=capacity['models'][key]['export_sha256'] or hashlib.sha256(rb).hexdigest()!=capacity['models'][key]['grid_sha256']:raise ValueError('actual geometry/grid source mismatch')
        inputpins[str(gp.relative_to(ROOT))]=hashlib.sha256(gb).hexdigest();inputpins[str(gr.relative_to(ROOT))]=hashlib.sha256(rb).hexdigest()
        g=json.loads(gzip.decompress(gb));grid=json.loads(rb);old=json.loads(blobs[key+'_geometry']);pa=parent['models'][key];ca=capacity['models'][key]
        if g['ODB_sha256']!=ca['ODB_sha256'] or g['ODB_mutations'] or g['physical_flow_commands_run']:raise ValueError('read-only actual ODB gate')
        rfgrid=json.loads((INPUT/'DS_grid.json').read_bytes())
        service=bank_service(h1['models'][key],v1,grid,c0['programs'][name],name,rf_provider_grid=rfgrid)
        service['RF_abstract_provider']='source-pinned DS_grid shallow1R1W SRAM; Qwen timing/physical qualification not transferred'
        # Price the additional transport state explicitly in the central strip;
        # keep original C0/V1 command/state reservations charged exactly once.
        buffer_footprint=2*service['extra_register_area_um2']; central_buffer_footprint=2*service['central_endpoint_register_area_um2']; spare=1400*CONTROL_H-service['C0_required_footprint_um2']
        if central_buffer_footprint>spare:raise ValueError('finite transport buffers exceed central-strip residual')
        W,H=[a/1000 for a in g['die'][2:]];tw=max(W,service['width_um']);th=H+BODY_GAP+service['height_um']
        hubw=old.get('dedicated_hub',{}).get('w',0)
        aw=8*tw+7*COL_GAP if key=='Qwen' else 8*tw+6*COL_GAP+hubw+2*COL_GAP
        ah=4*th+3*ROW_GAP;dw,dh=old['die_um'];ox=(dw-aw)/2;oy=(dh-ah)/2
        obstacles=[]
        for r in old['regions']:
            if r['kind'] not in ('die','sm') and r['name']!='dedicated_hub':obstacles.append(dict(name=r['name'],bbox_um=rect(r['x'],r['y'],r['w'],r['h'])))
        if key=='DS':
            hub=old['dedicated_hub'];hx=ox+4*tw+3*COL_GAP+COL_GAP
            obstacles.append(dict(name='dedicated_hub',bbox_um=rect(hx,hub['y'],hub['w'],hub['h'])))
        private_routes=[]
        if key=='Qwen':
            route_w=69.552;route_h=120.96
            for idx,label in enumerate(['s0','s1','n0','n1']):
                side=idx%2;is_north=idx>=2;outer=ox-route_w if side==0 else ox+aw
                l2=next(o for o in obstacles if o['name']=='l2_'+label)
                cx=(l2['bbox_um'][0]+l2['bbox_um'][2])/2
                escape_y=23059.92 if is_north else 2451.84
                row=2 if is_north else 0;branch_y=oy+(row+1)*th+row*ROW_GAP
                left=min(outer,cx);width=abs(cx-outer)+route_w
                private_routes.extend([dict(name='private_'+label+'_vertical',signal_layers=['M5','M7','M9'],bbox_um=rect(outer,min(escape_y,branch_y),route_w,abs(branch_y-escape_y)+route_h)),dict(name='private_'+label+'_L2_escape',signal_layers=['M6','M8'],bbox_um=rect(left,escape_y,width,route_h)),dict(name='private_'+label+'_horizontal',signal_layers=['M6','M8'],bbox_um=rect(left,branch_y,width,route_h))])
            obstacles.extend(private_routes)
        tiles=[]
        for sm in range(32):
            row,col=divmod(sm,8);x=ox+col*(tw+COL_GAP)
            if key=='DS' and col>=4:x=ox+4*tw+3*COL_GAP+COL_GAP+hubw+COL_GAP+(col-4)*(tw+COL_GAP)
            y=oy+row*(th+ROW_GAP);tiles.append(dict(SM=sm,bbox_um=rect(x,y,tw,th),retained_actual_body_bbox_um=rect(x,y,W,H),service_origin_um=[x,y+H+BODY_GAP],stack=(0 if row<2 else 2)+(0 if col<4 else 1)))
        conflicts=[(t['SM'],o['name'])for t in tiles for o in obstacles if overlap(t['bbox_um'],o['bbox_um'])]
        outside=[t['SM']for t in tiles if not contained(t['bbox_um'],[20,20,dw-20,dh-20])]
        pairconf=[(a['SM'],b['SM'])for i,a in enumerate(tiles)for b in tiles[i+1:]if overlap(a['bbox_um'],b['bbox_um'])]
        # Source-derived complete interface reservation across each *new*
        # dedicated corridor, not generic channel multiplicities.
        trunk_demand=1024+2048+pa['actual_params']['NC']*32+c0['programs'][name]['routing']['new_control_tracks_local']+576+128
        corridors=[]
        row_spans=[(ox,ox+aw)] if key=='Qwen' else [(tiles[0]['bbox_um'][0],tiles[3]['bbox_um'][2]),(tiles[4]['bbox_um'][0],tiles[7]['bbox_um'][2])]
        for row in range(3):
            y=oy+(row+1)*th+row*ROW_GAP
            for side,(left,right) in enumerate(row_spans):
                reserved_private=120.96 if key=='Qwen' and row in (0,2) else 0
                route=cut(grid,'Y',y+reserved_private,y+ROW_GAP,['M6','M8'],trunk_demand,f'row{row}/side{side}',left)
                route['private_provider_reserved_height_um']=reserved_private
                route['bbox_um']=rect(left,y+reserved_private,right-left,ROW_GAP-reserved_private);corridors.append(route)
        col_spans=[]
        for i in range(7):
            left=tiles[i]['bbox_um'][2];right=tiles[i+1]['bbox_um'][0]
            if key=='DS' and i==3:col_spans.extend([(left,left+COL_GAP),(right-COL_GAP,right)])
            else:col_spans.append((left,right))
        for i,(left,right) in enumerate(col_spans):
            route=cut(grid,'X',left,right,['M5','M7','M9'],trunk_demand,'column'+str(i),oy)
            route['bbox_um']=rect(left,oy,right-left,ah);corridors.append(route)
        orthogonal_crossings=[dict(corridor=r['owner'],private_owner=o['name'],corridor_layers=list(r['layers']),private_layers=o['signal_layers'],actual_via_binding=False)for r in corridors for o in private_routes if overlap(r['bbox_um'],o['bbox_um']) and not(set(r['layers'])&set(o['signal_layers']))]
        route_conflicts=[(r['owner'],o['name'])for r in corridors for o in obstacles if overlap(r['bbox_um'],o['bbox_um']) and (not o.get('signal_layers') or set(r['layers'])&set(o['signal_layers']))]
        global_service_cuts=[]
        for tile in tiles:
            sx,sy=tile['service_origin_um']
            for template in service['bank_cuts']+service['C0_cuts']:
                offset=sy if template['axis']=='Y' else sx
                coordoff=sx if template['axis']=='Y' else sy
                translated=cut(grid,template['axis'],template['span_um'][0]+offset,template['span_um'][1]+offset,list(template['layers']),template['demand_tracks'],template['owner'],template['coordinate_um']+coordoff)
                translated['SM']=tile['SM'];global_service_cuts.append(translated)
        native=[]
        for layer in ca['native_cut_capacity']:
            screens={r['cut_DBU']:r for r in pa['native_parent_route_cut_screens'][layer['layer']]}
            for r in layer['cut_records']:
                assert r['free_tracks']+r['all_OBS_halo_PDN_via_blocked_tracks']==layer['unique_track_count']
                s=screens[r['cut_DBU']]
                native.append(dict(layer=layer['layer'],direction=layer['direction'],**r,macro_to_macro_unique_net_lower_demand=s['macro_to_macro_unique_net_lower_demand'],original_parent_root_unique_net_demand=s['parent_band_root_unique_net_demand'],scope='exact retained ODB sampled cuts; original FF/cone routes not proven by macro-only lower demand'))
        maxlocal=service['width_um']+service['height_um'];wire=old.get('source_loaded_wire_ps_per_um',.76)
        if wire!=.76:raise ValueError('source loaded wire provisional coefficient')
        hops=math.ceil(maxlocal*WIRE_UPPER/(1000/1.2-60))
        assert hops==service['transport_pipeline_hops']
        trunk_pipeline=[]
        for route in corridors:
            length=route['bbox_um'][2]-route['bbox_um'][0] if route['owner'].startswith('row') else ah
            stages=math.ceil(length*WIRE_UPPER/(1000/1.2-60))
            bits=stages*route['demand_tracks']
            trunk_pipeline.append(dict(corridor=route['owner'],max_length_um=length,provisional_stages=stages,register_bits=bits,footprint_um2=2*bits*.2916,command_credit=1,aligned_tag_data=True))
        private_cuts=[];private_pipeline=[]
        for pr in private_routes:
            vertical=pr['name'].endswith('vertical');b=pr['bbox_um'];axis='X' if vertical else 'Y'
            low,high=(b[0],b[2])if vertical else (b[1],b[3])
            private_cuts.append(cut(grid,axis,low,high,pr['signal_layers'],1698,pr['name'],b[1]if vertical else b[0]))
            length=(b[3]-b[1])if vertical else (b[2]-b[0]);stages=math.ceil(length*WIRE_UPPER/(1000/1.2-60));bits=1698*stages
            private_pipeline.append(dict(owner=pr['name'],max_length_um=length,provisional_stages=stages,register_bits=bits,footprint_um2=2*bits*.2916,old_charged_route_ticks=None,reconcile_owner='Goodall/Dewey original provider interval; no cost removed without source receipt'))
        profiles={op:latency_delta(v['upper']['RF_read_pair_transactions'],v['upper']['RF_write_vectors'],outward_hops=hops,return_hops=hops)for op,v in v1['typed_cost_bounds'].items()}
        pc=[]
        for r in v1['models'][name]['PC_costs']:
            added=sum(n*profiles[k]['added_ticks']for k,n in r['source_count'].items())
            pc.append(dict(pc=r['pc'],dependencies=r['dependencies'],V1_ticks_upper=r['V1_ticks_upper']+added,added_service_distance_ticks_upper=added))
        # DS source_count sums ranks while original costs use max rank. This is
        # a conservative no-overlap upper; never advertise achieved SM overlap.
        placed=sum(f['bbox']is not None for f in g['FF_instances'])
        retained_bounds=g['die']
        physical_escaped=sum(not contained(cell['bbox'],retained_bounds)for cell in g['placed_physical_cells'])
        macro_escaped=sum(not contained(m['bbox'],retained_bounds)for m in g['macro_instances'])
        if physical_escaped or macro_escaped:raise ValueError('actual retained source exclusions escape reserved body')
        models[name]=dict(SMs_per_die=32,ranks=joined['models'][name]['replicas']//32,SM_tile_um=[tw,th],array_bbox_um=rect(ox,oy,aw,ah),complete_die_um=old['die_um'],SM_placements=tiles,retained_nonSM_reservations=obstacles,retained_hub_repositioned=key=='DS',Qwen_private_provider_routes=private_routes,Qwen_private_provider_cuts=private_cuts,Qwen_private_provider_pipeline=private_pipeline,private_route_relocation_source='r11 twelve rectangles retained as source-sized vertical/horizontal bands; location/length repriced for expanded array',full_die_obstacle_conflicts=conflicts,SM_pair_conflicts=pairconf,outside_die=outside,full_die_geometry_screen_pass=not(conflicts or pairconf or outside),service=service,
            area=dict(expanded_SM_array_mm2=32*tw*th/1e6,service_mm2_per_SM=service['width_um']*service['height_um']/1e6,service_mm2_per_die=32*service['width_um']*service['height_um']/1e6,interSM_corridors_array_overhead_mm2=(aw*ah-32*tw*th-hubw*ah)/1e6,die_mm2=dw*dh/1e6,retained_PHY_mm2=4*12000.096*833.49/1e6,complete_reserved_occupancy_mm2=(32*tw*th+sum((o['bbox_um'][2]-o['bbox_um'][0])*(o['bbox_um'][3]-o['bbox_um'][1])for o in obstacles)+4*12000.096*833.49)/1e6,original_standalone_slot_deficit_retained=True,transport_state_incremental_footprint_um2=buffer_footprint,central_endpoint_footprint_um2=central_buffer_footprint,interSM_trunk_register_footprint_um2=sum(p['footprint_um2']for p in trunk_pipeline),Qwen_private_pipeline_footprint_um2=sum(p['footprint_um2']for p in private_pipeline),C0_strip_spare_before_transport_um2=spare),
            corridor_cuts=corridors,corridor_obstacle_conflicts=route_conflicts,orthogonal_private_crossings=orthogonal_crossings,global_service_cuts=global_service_cuts,global_service_cut_screens_pass=all(c['screen_pass']for c in global_service_cuts),trunk_pipeline_reservations=trunk_pipeline,corridor_screens_pass=all(c['screen_pass']for c in corridors),retained_native_cuts=native,
            actual_source_geometry=dict(ODB_sha256=g['ODB_sha256'],macros=len(g['macro_instances']),retained_placed_physical_cells=len(g['placed_physical_cells']),actual_FFs=len(g['FF_instances']),actual_FFs_placed=placed,retained_physical_cells_outside_body=physical_escaped,retained_macros_outside_body=macro_escaped,retained_PDN_shapes=sum(len(p['shapes'])for p in g['power_special_shapes']),unknown_layer_vias_blocked_on_all_planes=ca['unknown_layer_PDN_via_count_conservatively_blocked_all_planes'],retained_macro_body_all_OBS_FF_PG_excluded_from_service=True),
            latency=dict(provisional_loaded_wire_ps_per_um=wire,source_loaded_wire_range_ps_per_um=[.72,.81],sizing_loaded_wire_upper_ps_per_um=WIRE_UPPER,nominal_request_hops=math.ceil(maxlocal*wire/(1000/1.2-60)),streaming_target_GHz=1.2,setup_uncertainty_ps=60,hold_uncertainty_ps=25,SSFF_qualified=False,bank_max_L1_um=maxlocal,request_hops=hops,return_hops=hops,proposed_shared_fetch_round_trip_ticks=2*max(p['provisional_stages']for p in trunk_pipeline),trunk_cost_scope='source-distance upper transport stage proposal; no existing route cost subtracted until Dewey interval receipt supplies it',typed_extra_costs=profiles,PC_distance_costs=pc,isolated_V1_with_distance_path=V.critical(pc),rank_provider_C0_fetch='one finite64B request seat per shared trunk;32 distinct SM commands require32 grants, not free512bit broadcast',Dewey_cost_reconcile='replace distance component only after provider interval join; RF/I64/RMW/C0 charged once',whole_token_ns=None),
            G0_status='CONSTRUCTIVE_SERVICE_AND_DIE_SCREENS_ONLY_PARENT_AND_PDN_BINDING_BLOCKED',hardware_admitted=False,
            blockers=['all original parent FFs unplaced; actual FF/cone endpoint ownership incomplete','new bank-local H1+C0+V1 source endpoint absent; Sagan atomic gateway must own all16bank tags/ACKs; Qwen shallowRF abstract remains unqualified','new PDN/clock/via geometry and pin escapes not source-bound;50% reservation is a proposal','full retained-parent detailed cuts and all unrelated provider occupancy required before routing sufficiency','Dewey actual typed ordered distance and shared-fetch interval reconciliation','full-context SS/FF closure'])
        del g
    return dict(schema='opentallas.H4.V1.expanded-service.v1',provider_atomic_contract=dict(entrypoint='ProviderAtomicFence',C0_ticket_fields=['generation','PC','sequence','rank','SM'],RF_home_resolver='Sagan C0 source_home / original rank-SM9bit RF base; no new virtual storage',read_publication_requires=16,write_visibility_requires=32,read_mask_bits=16,write_mask_bits=32,one_command_credit_per_SM=True,partial_bank_publication=False,actual_H1_gateway_present=False,bank_mask_state_owner='existing V1 control reservation plus staged transport metadata; no numeric engine callback'),models=models,input_pins=inputpins,source_pins=joined['source_pins']+[dict(commit=V.C0,path='tools/qwen_hbm_shoreline_remedy_r10.py',sha256=hashlib.sha256(V.pinned(V.C0,'tools/qwen_hbm_shoreline_remedy_r10.py')).hexdigest())]+[dict(commit=PIN,path=BASE+p,sha256=hashlib.sha256(V.pinned(PIN,BASE+p)).hexdigest())for p in ['actual_geometry_capacity.json','model.json']],RF_address_mapping=dict(entrypoint='provider_location',logical_vector_bits=4096,physical_word_bits=32,vector_count=512,lanes_per_vector=128,bank_count=16,pages=4,read_copies=2,logical_RF_bytes=262144,physical_RF_bytes=524288,I64_policy='actual codec supplies both source RF vectors; no invented adjacent highword or duplicate RMW cost',source_home_owner='Sagan C0 resolves actual native version_homes; mutableKV/checkpoint remain separate providers'),source_geometry_complete_for_retained_body=True,all_original_failures_preserved=True,no_new_layers=True,no_RTL_or_PnR=True,hardware_admitted=False)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--verify',action='store_true');a=ap.parse_args();p=Path(a.out)
    b=(json.dumps(build(),sort_keys=True,indent=2)+'\n').encode();pins={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()for s in ['tools/h4_v1_expanded_service.py','tests/test_h4_v1_expanded_service.py']}
    if a.verify:
        if (p/'model.json').read_bytes()!=b or json.loads((p/'source_pins.json').read_text())!=pins:raise ValueError('expanded evidence/source mismatch')
        print('PASS_EXACT_EXPANDED_SERVICE_REPLAY');return
    p.mkdir(parents=True,exist_ok=False);(p/'model.json').write_bytes(b);(p/'source_pins.json').write_text(json.dumps(pins,indent=2,sort_keys=True)+'\n');print('EXPANDED_SERVICE_RECORDED_NO_HARDWARE_ADMISSION')
if __name__=='__main__':main()
