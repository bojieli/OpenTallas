#!/usr/bin/env python3
"""Conventional GPU shoreline geometry/provider proposal, no hardware build.
All new sizing is an opt-in analytical overlay to pinned unified model.
Provider fixture inputs are explicit transactions, never timing-bound callbacks.
"""
import argparse,hashlib,json,math,re
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
from qwen_hbm_controller_events_r1 import ROOT,pinned,source_timing,Beat,MACRO
from qwen_hbm_controller_calendar_r2 import BankCalendar,bankmap,edge,audit_bank_events
from qwen_hbm_downstream_contract_r8 import fixture
from qwen_hbm_inventory_timers_r9 import compose as previous
PIN='a39eacc6bcfb75565313837d1303886b3395bf03'
FAST=F(2500,3);SERIAL=F(10000,9);PHY=F(512)
DIR='results/uarch/qwen_hbm_shoreline_remedy_20261002'

def get(p):return pinned(ROOT,PIN,p)
def snap_up(x,p=2.16):return math.ceil(x/p-1e-10)*p

def rectangles_overlap(a,b):
    return a['x']<b['x']+b['w']-1e-6 and b['x']<a['x']+a['w']-1e-6 and a['y']<b['y']+b['h']-1e-6 and b['y']<a['y']+a['h']-1e-6

def reserves():
    prev=previous()['resource_area'];base=prev['r9_retained_plus_additive_mm2_per_stack']
    tech=get('results/uarch/w10_connected_escape_prerequisite/image_reference_tech.lef').decode()
    vias=[]
    for name in ['VIA45','VIA56','VIA67','VIA78','VIA89']:
        block=tech.split('VIA '+name+' Default')[1].split('END '+name)[0]
        rects=[tuple(map(float,m)) for m in re.findall(r'RECT (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)',block)]
        # Conservative square keeps all enclosures and source max cut spacing.
        extent=max(max(abs(x) for x in r)*2 for r in rects)
        vias.append(dict(name=name,max_enclosure_extent_um=extent))
    pitch=snap_up(max(v['max_enclosure_extent_um'] for v in vias)+.097,.001)
    phy_new_pin_delta=36+(344+2)*32+128
    via_count=(60352+phy_new_pin_delta)*5
    via_area=via_count*pitch*pitch/1e6
    # All inherited standard-cell reservation could be DFFs. Independent
    # clock budget never subtracts an unspecified inherited CTS component.
    inherited_logic_um2=10*.5*1e6
    max_inherited_clock_sinks=math.ceil(inherited_logic_um2/.2916)
    additive_sinks=math.ceil((base-10)*.5*1e6/.2916)
    sinks=max_inherited_clock_sinks+additive_sinks
    level=sinks;bufs=0;levels=0
    while level>1:level=math.ceil(level/16);bufs+=level;levels+=1
    # BUF24 area source in local locked liberty; source area is corner invariant
    # proxy, NOT proof that fanout16 meets SS or controls clock skew.
    libname='lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib'
    lock=json.loads(get('configs/pdk/asap7_local_liberty_lock.json'));lib=(Path(lock['root'])/libname).read_bytes()
    assert hashlib.sha256(lib).hexdigest()==lock['files'][libname]['sha256']
    bufarea=float(re.search(r'cell \(BUFx24_ASAP7_75t_R\).*?area\s*:\s*([\d.]+)',lib.decode(),re.S).group(1))
    cts_area=(bufs+64)*bufarea/.5/1e6
    # Full64-bit timer ADD/decrement/zero/max/reload costs, no r9 narrowing.
    pc=32;timer_fields=32*3+17
    timer_logic_bits=pc*timer_fields*64*5
    timer_area=timer_logic_bits*.2/.5/1e6
    command_bits=3+5+5+19+34+16+5+256+1
    command_FIFO_bits=32*(2*command_bits+22+command_bits)
    response_FIFO_bits=32*(2*471+22+471)
    adapter_FF_bits=command_FIFO_bits+response_FIFO_bits+4*(404+338+4)+272+288
    timer_pipeline_FF_bits=pc*timer_fields*64
    timer_pipeline_area=timer_pipeline_FF_bits*.2916/.5/1e6
    adapter_FF_bits+=96+17*3+4*4+98 # includes independently priced prior directory snapshot # generation, opcode history flags, cancellation state
    adapter_area=adapter_FF_bits*.2916/.5/1e6
    sinks+=adapter_FF_bits+timer_pipeline_FF_bits
    level=sinks;bufs=0;levels=0
    while level>1:level=math.ceil(level/16);bufs+=level;levels+=1
    cts_area=(bufs+64)*bufarea/.5/1e6
    # Each stack has its own corridor; width uses existing50% signal escrow.
    v_tracks=.5*(1/.048+1/.064+1/.080);h_tracks=.5*(1/.064+1/.080)
    v_width=snap_up(1698/v_tracks,.432);h_height=snap_up(1698/h_tracks)
    horizontal_corridor_area=15880*h_height/1e6
    # Wide source PDN projection excluded from cell allocation; deliberately
    # conservative upper bound. Orthogonal stripe intersections counted once;
    # M1/M2 followpin projections added independently, not assumed aligned.
    vertical_fraction=2*.12/5.4+2*2/10.8
    horizontal_fraction=2*.288/5.4+2*2/10.8
    pdn_fraction=vertical_fraction+horizontal_fraction-vertical_fraction*horizontal_fraction+2*(2*.018/.54)
    # Layered PDN preserves50percent signal escrow on each upper layer.
    # Charge every proposed PG intersection site separately, with actual
    # default via enclosure+cut-spacing, even when projections overlap.
    pg_vias=[]
    for name in ['VIA12','VIA23','VIA34','VIA45','VIA56','VIA67','VIA78']:
        vb=tech.split('VIA '+name+' Default')[1].split('END '+name)[0]
        rects=[tuple(map(float,m)) for m in re.findall(r'RECT (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)',vb)]
        cut='V'+name[3]
        cb=tech.split('LAYER '+cut+'\n')[1].split('END '+cut)[0]
        cb=re.sub(r'#[^\n]*','',cb)
        scalar=re.search(r'^\s*SPACING ([\d.]+)',cb,re.M)
        prop=re.search(r'SPACINGTABLE\s+DEFAULT ([\d.]+)',cb)
        assert scalar or prop,'source cut spacing provider missing'
        spacing=float((scalar or prop).group(1))
        site=max(max(abs(x) for x in r)*2 for r in rects)+spacing
        pg_vias.append(dict(name=name,cut_spacing_um=spacing,site_pitch_um=site,site_area_um2=site*site))
    areas={v['name']:v['site_area_um2'] for v in pg_vias}
    densities=dict(M1_M2=4/.54**2,M2_M5=4/(.54*5.4),M5_M6=4/5.4**2,M6_M7=4/(5.4*10.8),M7_M8=4/10.8**2)
    pdn_site_fraction=densities['M1_M2']*areas['VIA12']+densities['M2_M5']*sum(areas[n] for n in ('VIA23','VIA34','VIA45'))+densities['M5_M6']*areas['VIA56']+densities['M6_M7']*areas['VIA67']+densities['M7_M8']*areas['VIA78']
    allocated_non_PDN=base+cts_area+timer_area+timer_pipeline_area+adapter_area+via_area+horizontal_corridor_area
    exclusive_required_slot=allocated_non_PDN/(1-pdn_fraction)
    required_slot=allocated_non_PDN/(1-pdn_site_fraction)
    return dict(base_r9_mm2_per_stack=base,clock=dict(max_clock_sinks=sinks,buffer_area_um2=bufarea,fanout_budget=16,buffers=bufs+64,levels=levels,area_mm2=cts_area,qualification='Area proxy only; SS/FF skew/setup/hold must close, no inherited CTS overlap credit'),timer_ADD_reload_zero_area_mm2=timer_area,timer_pipeline_FF_bits=timer_pipeline_FF_bits,timer_pipeline_area_mm2=timer_pipeline_area,clock_cell_source_sha256=hashlib.sha256(lib).hexdigest(),clock_cell_source='configs/pdk/asap7_local_liberty_lock.json:'+libname,timer_logic_bit_equivalents=timer_logic_bits,full_width_timers=True,adapter_FF_bits=adapter_FF_bits,adapter_area_mm2=adapter_area,command_bits=command_bits,command_FIFO_per_PC=2,response_FIFO_per_PC=2,via_stack=vias,via_keepout_pitch_um=pitch,PHY_added_signal_pins=phy_new_pin_delta,PHY_candidate_total_signal_pins=9209+phy_new_pin_delta,PHY_pin_span_um=(9209+phy_new_pin_delta)*.192,PHY_50percent_edge_pin_capacity=math.floor(12000*.5/.192),via_cuts=via_count,via_area_mm2=via_area,
      via_scope='Source reference tech geometry, conservative independent sites; must be re-bound to exact routed platform before build. No detailed DRC/EM proof.',vertical_corridor_width_um=v_width,horizontal_corridor_height_um=h_height,horizontal_corridor_area_mm2=horizontal_corridor_area,vertical_signal_tracks_per_um=v_tracks,horizontal_signal_tracks_per_um=h_tracks,signal_share=.5,PDN_exclusive_projection_fraction=pdn_fraction,PDN_via_geometry=pg_vias,PDN_intersection_density_per_um2=densities,PDN_charged_site_fraction=pdn_site_fraction,PDN_additive_site_area_mm2=required_slot-allocated_non_PDN,exclusive_projection_alternative_slot_mm2_per_stack=exclusive_required_slot,preferred_PDN_policy='Layered routing with unchanged50percent signal escrow; conservative PG intersection sites charged as exclusive keepouts. Entire upper-layer strap projections need not exclude cells underneath; full-projection alternative shown independently.',PDN_profile='configs/signoff/pdn_m7_m8_wide_upper_grid.tcl',PDN_projection_scope='Policy reservation upper bound, not a physical minimum. Conservative reserved area, not measured cell obstruction: upper vertical/horizontal union plus both followpin layers; no PDN relaxation or reuse credit',non_PDN_need_mm2=allocated_non_PDN,minimum_slot_mm2_per_stack=required_slot,minimum_band_depth_um=required_slot*1e6/15880)

def geometry(reserve_override=None):
    fp=json.loads(get('results/floorplan/hbm_gpu/qwen_hbm_die.json'));r=reserve_override or reserves()
    depth=snap_up(r['minimum_band_depth_um']);delta=depth-630.72
    proposed=[]
    for old in fp['regions']:
        x=dict(old)
        if x['name']=='svc_south':x['h']=depth
        if x['name']=='svc_north':x['y']-=delta;x['h']=depth
        if x['kind']=='l2':x['y']+=delta if x['name'].startswith('l2_s') else -delta
        proposed.append(x)
    blocks=[x for x in proposed if x['kind']!='die']
    collisions=[(a['name'],b['name']) for i,a in enumerate(blocks) for b in blocks[i+1:] if rectangles_overlap(a,b)]
    outside=[x['name'] for x in blocks if x['x']<0 or x['y']<0 or x['x']+x['w']>fp['die_um'][0] or x['y']+x['h']>fp['die_um'][1]]
    array=fp['array'];vw=r['vertical_corridor_width_um'];hh=r['horizontal_corridor_height_um']
    # Four independent south/north west/east paths, outside the SM array.
    routes=[]
    for side in ('s','n'):
        l2s=[x for x in proposed if x['kind']=='l2' and x['name'].startswith('l2_'+side)]
        for j,l2 in enumerate(l2s):
            x=array['x']-60-vw if j==0 else array['x']+array['w']+60
            if side=='s':y=l2['y']+l2['h']+60;end=array['y']-60-hh
            else:y=array['y']+array['h']+60+hh;end=l2['y']-60
            routes.append(dict(name=f'private_{side}{j}_vertical',kind='route',x=x,y=y,w=vw,h=end-y))
            y_h=array['y']-60-hh if side=='s' else array['y']+array['h']+60
            l2center=l2['x']+l2['w']/2
            y_escape=l2['y']+l2['h']+60 if side=='s' else l2['y']-60-hh
            routes.append(dict(name=f'private_{side}{j}_L2_escape',kind='route',x=min(x,l2center),y=y_escape,w=abs(x-l2center)+vw,h=hh))
            routes.append(dict(name=f'private_{side}{j}_horizontal',kind='route',x=min(x,l2center),y=y_h,w=abs(x-l2center)+vw,h=hh))
    route_collisions=[(a['name'],b['name']) for a in routes for b in blocks if rectangles_overlap(a,b)]
    # Route segments sharing their own elbow are intentional; independent
    # stack paths must not overlap one another.
    independent_overlap=[(a['name'],b['name']) for i,a in enumerate(routes) for b in routes[i+1:] if a['name'].split('_')[1]!=b['name'].split('_')[1] and rectangles_overlap(a,b)]
    rawdef=get('results/floorplan/hbm_gpu/qwen_hbm_die_macros.def').decode()
    assert hashlib.sha256(rawdef.encode()).hexdigest()==fp['def_sha256']
    dimensions={'ot_gpu_sm_q':tuple(fp['sm_tile']['abstract_um'])}
    for macro in ('ot_hbm3e_phy','ot_sram_1r1w_1024x256_m2_r2c2','ot_sram_1r1w_64x512_m1_r2c2'):
        text=get(f'physical/asap7_memory_macros/{macro}/{macro}.lef').decode()
        dimensions[macro]=tuple(map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',text).groups()))
    placements=[]
    for name,macro,x,y,orient in re.findall(r'- (\w+) (\w+) \+ FIXED \( (\d+) (\d+) \) (\w+) ;',rawdef):
        w,h=dimensions[macro];y=int(y)/1000
        if name.startswith('l2_s'):y+=delta
        if name.startswith('l2_n'):y-=delta
        placements.append(dict(name=name,macro=macro,x=int(x)/1000,y=y,w=w,h=h,orient=orient,status='retained' if not name.startswith('l2_') else 'moved_inward'))
    mw,mh=dimensions['ot_sram_1r1w_64x512_m1_r2c2']
    for side in ('south','north'):
        band=next(x for x in proposed if x['name']=='svc_'+side)
        for stack in range(2):
            for j in range(64):
                placements.append(dict(name=f'candidate_{side}_stack{stack}_queue{j}',macro='ot_sram_1r1w_64x512_m1_r2c2',x=band['x']+stack*15880+4.32+(j%10)*(mw+8.64),y=band['y']+2.16+(j//10)*(mh+4.32),w=mw,h=mh,orient='R0',status='added',PC=j%32,queue='request' if j<32 else 'return'))
    macro_conflicts=[(a['name'],b['name']) for i,a in enumerate(placements) for b in placements[i+1:] if rectangles_overlap(a,b)]
    assert not macro_conflicts
    assert len(placements)==548 and sum(p['status']=='added' for p in placements)==256
    per_stack=15880*depth/1e6
    wire_ps=float(re.search(r'WIRE_PS_PER_UM_LOADED = ([\d.]+)',get('tools/uarch_model.py').decode()).group(1))
    ss_reach=float(re.search(r'WIRE_REACH_SS_UM\s*=\s*([\d.]+)',get('tools/uarch_model.py').decode()).group(1))
    extra_fast_edges=math.ceil(2*delta/ss_reach)
    assert not collisions and not outside and not route_collisions and not independent_overlap
    assert all(x['h']>0 for x in routes)
    return dict(candidate='EXPAND_SERVICE_BANDS_MOVE_L2_INWARD_KEEP_OUTLINE_SMs_PHY_PCs',minimum_slot_mm2_per_stack=r['minimum_slot_mm2_per_stack'],selected_slot_mm2_per_stack=per_stack,selected_depth_um=depth,old_depth_um=630.72,delta_um=delta,die_um=fp['die_um'],outline_area_mm2=815,SMs_per_die=32,stacks_per_die=4,PCs_per_stack=32,L2_macros_per_die=256,queue_macros_per_stack=64,regions=proposed,macro_placements=placements,macro_pair_conflicts=macro_conflicts,source_DEF_sha256=fp['def_sha256'],private_routes=routes,private_route_reserved_area_mm2_per_die=sum(x['w']*x['h'] for x in routes)/1e6,geometry_conflicts=collisions+route_collisions+independent_overlap+macro_conflicts,outside=outside,geometry_fit=True,area_budget_margin_mm2_per_stack=per_stack-r['minimum_slot_mm2_per_stack'],new_service_area_mm2_per_die=4*per_stack,added_service_area_mm2_per_die=4*(per_stack-10.0158336),source_SS_wire_reach_um=ss_reach,source_historical_floorplan_clock_hz=fp['clock_hz'],source_clock_transfer_allowed=False,source_loaded_wire_ps_per_um=wire_ps,source_wire_qualification='Analytical loaded-wire model, not SS/FF closure at new geometry',occupancy_replacement_credit_mm2=0,conservative_added_oneway_FAST_edges=extra_fast_edges,new_oneway_route_FAST_edges=36+extra_fast_edges,
      comparison=dict(unchanged_band='FAIL11.33234>10.01583 before CTS/PDN reserves',unchanged_L2='FAIL band expansion overlaps source L2 placements; move all4 slices',outline_resize='NOT_REQUIRED_BY_THIS_GEOMETRY; no reticle/packaging change credited',existing_core_corridor='REJECTED: shared6792bits>2696tracks; private outside-array routes explicitly reserved'),minimum_scope='Minimum rounded band under the explicitly conservative PDN-site/clock/route reserve policy, not minimum manufacturable area',physical_fit_qualification=False)

class Provider:
    """Event-driven proposed finite controller+memory tracker+IRS/lease model.
    Only actual-input-style commits advance result/IRS/lease phases. Synthetic
    tests drive these inputs explicitly; no completion callback from a bound.
    """
    def __init__(self,rows):
        self.rows=rows;self.backing={};self.read_rows=fixture()['KV_prefix_read_rows'];self.pending_commands=[[] for _ in range(32)];self.generation=None;self.opcode_inputs={};self.RF_results=set();self.live={};self.completed=set();self.cancelled=set();self.opcodes={};self.readers={};self.reader_done=set();self.reader_cancelled=set();self.lease_cancelled=False;self.lease_released=False;self.lease=None;self.log=[];self.now=F(0);self.peak=Counter();self.pc_busy=[F(0)]*32;self.refresh_next=[F(source_timing()['REFI_PS'])+F(source_timing()['REFI_PS']*p,32) for p in range(32)];self.route_edges=geometry()['new_oneway_route_FAST_edges'];self.cal=BankCalendar(source_timing(),PHY)
    def record(self,kind,owner=None,**fields):self.log.append(dict(kind=kind,ps=str(self.now),owner=owner,**fields))
    def advance(self,now):
        now=F(now)
        if now<self.now:raise ValueError('causal time')
        self.now=now
        for p in range(32):self.pending_commands[p]=[x for x in self.pending_commands[p] if x>now]
        self.current_refresh()
        for i,x in self.live.items():
            if x['phase']=='WR_emitted' and now>=x['visible_due']:
                x['phase']='WR_visible';self.backing[x['sector']]=(i,x['producer'],x['transport']);self.record('backing_visible',i,sector=x['sector'])
    def current_refresh(self):
        t=source_timing()
        for p in range(32):
            if self.refresh_next[p]>self.now or self.pc_busy[p]>self.now:continue
            opened=[b for b in self.cal.b[p] if b.open]
            start=edge(max(self.now,self.cal.last_col[p]+t['BURST_PS']),PHY)
            if opened:
                pre=edge(max([start]+[b.preok for b in opened]),PHY)
                self.cal.log('PREall',pre,p);start=pre+t['RP_PS']
            ref=edge(start,PHY);self.cal.log('REF',ref,p)
            self.cal.last_ref[p]=ref
            for b in self.cal.b[p]:b.open=False;b.actok=max(b.actok,ref+t['RFC_PS'])
            self.pc_busy[p]=ref+t['RFC_PS']
            # Autonomous current REF, sticky due while busy; no retrospective
            # service. Debt serviced sequentially, not forgotten after stall.
            self.refresh_next[p]+=t['REFI_PS']
            self.cal.next_ref[p]=self.refresh_next[p]
            self.record('current_REFRESH',p,REF_ps=str(ref))
    def reserve(self,i,producer,transport):
        if self.lease is not None or len(self.live)>=4:return False
        if i in self.live or i in self.completed or i in self.cancelled:raise ValueError('duplicate sector owner')
        if self.generation is None:self.generation=(producer,transport)
        if self.generation!=(producer,transport):raise ValueError('accepted generation mismatch')
        self.live[i]=dict(sector=self.rows[i]['sector'],producer=producer,transport=transport,phase='RMW_wait' if self.rows[i]['partial'] else 'WR_ready',cancel=False,held=None)
        self.peak['sector_owners']=max(self.peak['sector_owners'],len(self.live));self.record('owner_accept',i);return True
    def owner(self,i,identity):
        x=self.live[i]
        if tuple(identity)!=(x['sector'],x['producer'],x['transport']):raise ValueError('full-address accepted identity')
        return x
    def RMW_read(self,i,identity):
        x=self.owner(i,identity)
        if x['phase']!='RMW_wait' or x['cancel']:raise ValueError('owned RMW read phase')
        p=bankmap(x['sector'])['pc']
        if len(self.pending_commands[p])>=3:return False
        start=edge(max(self.now+3*PHY,self.pc_busy[p])+37*FAST,PHY)
        b=Beat(x['sector'],i,x['producer'],x['transport'],accepted_ps=self.now)
        before=len(self.cal.events);col=self.cal.plan(b,start)
        assert all(e['ps']>=self.now for e in self.cal.events[before:])
        self.pc_busy[p]=col+FAST;self.pending_commands[p].append(col);self.peak['command_slots_per_PC']=max(self.peak['command_slots_per_PC'],len(self.pending_commands[p]));self.refresh_next[p]=self.cal.next_ref[p]
        arrived=edge(col+source_timing()['CL_PS']+source_timing()['BURST_PS']+source_timing()['RSP_PS'],FAST)
        x['RMW_ready']=edge(arrived+(6+self.route_edges)*FAST,SERIAL)+3*SERIAL+27*SERIAL
        x['phase']='RMW_result_wait';self.record('RMW_read_reserved',i,column_ps=str(col),minimum_RF_commit_ps=str(x['RMW_ready']))
        return x['RMW_ready']
    def RMW_result_commit(self,i,identity):
        x=self.owner(i,identity)
        if x['phase']!='RMW_result_wait' or x['cancel'] or self.now<x['RMW_ready']:raise ValueError('actual RMW result required before WR')
        x['phase']='RMW_retire_wait';self.record('RF_result_commit_INPUT',i)
    def RMW_owned_retire(self,i,identity):
        x=self.owner(i,identity)
        if x['phase']!='RMW_retire_wait' or x['cancel']:raise ValueError('actual RMW owned result retirement')
        x['phase']='WR_ready';self.record('RMW_owned_retire_INPUT',i)
    def WR_column(self,i,identity):
        x=self.owner(i,identity)
        if x['phase']!='WR_ready' or x['cancel']:raise ValueError('WR reserve/result-before-column')
        # Canonical source-bound finite command sequence; at most one active
        # scan per PC. Worst35edge scan + headprefetch1 charged before plan.
        p=bankmap(x['sector'])['pc']
        if len(self.pending_commands[p])>=3:return False
        ready=max(self.now+3*PHY,self.pc_busy[p])+37*FAST
        b=Beat(x['sector'],i,x['producer'],x['transport'],write=True,accepted_ps=self.now)
        before=len(self.cal.events);col=self.cal.plan(b,edge(ready,PHY));self.pc_busy[p]=col+FAST;self.pending_commands[p].append(col);self.peak['command_slots_per_PC']=max(self.peak['command_slots_per_PC'],len(self.pending_commands[p]))
        assert all(e['ps']>=self.now for e in self.cal.events[before:]),'no retrospective commands'
        self.refresh_next[p]=self.cal.next_ref[p]
        x['phase']='WR_emitted';x['column']=col
        x['visible_due']=edge(col+source_timing()['CWL_PS']+source_timing()['BURST_PS'],PHY)
        self.record('WR_reserved_before_column',i,column_ps=str(col),visible_due_ps=str(x['visible_due']))
        return x['visible_due']
    def RAW_read_ready(self,sector):
        return not any(x['sector']==sector and x['phase'] in ['RMW_wait','RMW_result_wait','RMW_retire_wait','WR_ready','WR_emitted'] for x in self.live.values())
    def ACK_capture(self,i,identity):
        x=self.owner(i,identity)
        if x['phase']!='WR_visible':raise ValueError('early ACK')
        x['phase']='ACK_CDC';x['ACK_landing']=edge(edge(self.now+(3+self.route_edges)*FAST,FAST),SERIAL)+3*SERIAL
        x['held']=(i,tuple(identity),bool(x['cancel']));self.record('held_ACK_capture',i)
    def sector_store(self,i,identity):
        x=self.owner(i,identity)
        if x['phase']!='ACK_CDC' or self.now<x['ACK_landing']:raise ValueError('forward CDC/held ACK not landed')
        x['phase']='store_pending';x['store_due']=edge(self.now,SERIAL)+SERIAL
        self.record('addressed_store_INPUT',i)
    def sector_retire(self,i,identity):
        x=self.owner(i,identity)
        if x['phase']!='store_pending' or self.now<x['store_due']+SERIAL:raise ValueError('visible bitstore then registered sector retirement')
        x['phase']='retire_held';x['reverse_due']=edge(self.now+(self.route_edges+3)*FAST,FAST);self.record('sector_retire',i)
    def reverse_credit(self,i,identity):
        x=self.owner(i,identity)
        if x['phase']!='retire_held' or self.now<x['reverse_due']:raise ValueError('retire then reverse CDC')
        (self.cancelled if x['cancel'] else self.completed).add(i);del self.live[i];self.record('reverse_credit',i)
    def opcode_issue(self,instruction,slot,serial,producer,transport):
        if (producer,transport)!=self.generation or instruction in self.opcode_inputs or not 0<=slot<32 or not 0<=serial<1<<32:raise ValueError('actual opcode accepted epoch/IRS aperture')
        active=[x for i,x in self.opcode_inputs.items() if i not in self.opcodes or self.opcodes[i]['retire'] is None]
        if len(active)>=4:return False
        if any(x[:2]==(slot,serial) for x in active):raise ValueError('IRS live slot/serial collision')
        self.opcode_inputs[instruction]=(slot,serial,producer,transport);self.record('opcode_issue_INPUT',instruction);return True
    def opcode_result_commit(self,instruction,producer,transport):
        if self.lease!=(producer,transport) or instruction not in (13,14,15) or instruction not in self.opcode_inputs:raise ValueError('actual owned leased RF result')
        deps={13:[12],14:[13],15:[12,14]}[instruction]
        if any(i not in self.opcodes or self.opcodes[i]['retire'] is None for i in deps):raise ValueError('actual consumer dependency')
        self.RF_results.add(instruction);self.record('opcode_result_commit_INPUT',instruction)
    def opcode_complete(self,instruction,slot,serial):
        if self.now%SERIAL:raise ValueError('opcode complete consumer clock edge')
        if instruction in self.opcodes:raise ValueError('duplicate opcode IRS')
        if self.opcode_inputs.get(instruction)!=(slot,serial,*self.generation):raise ValueError('actual opcode issue correlation')
        if instruction in (13,14,15) and instruction not in self.RF_results:raise ValueError('actual RF result not present')
        if instruction==11 and (10 not in self.opcodes or self.opcodes[10]['retire'] is None):raise ValueError('writer/fence dependency')
        if instruction in (10,11) and (len(self.completed)!=272 or self.live or self.cancelled):raise ValueError('whole writer after272 sector completions')
        if instruction==12 and len(self.reader_done)!=288:raise ValueError('KV_READ incomplete')
        self.opcodes[instruction]=dict(slot=slot,serial=serial,complete=self.now,retire=None);self.record('opcode_complete_INPUT',instruction)
    def IRS_retire(self,instruction,slot,serial):
        x=self.opcodes[instruction]
        if (slot,serial)!=(x['slot'],x['serial']) or self.now!=x['complete']+SERIAL or self.now%SERIAL or x['retire'] is not None:raise ValueError('actual registered matching IRS retirement')
        x['retire']=self.now;self.record('opcode_IRS_retire_INPUT',instruction)
    def acquire(self,producer,transport,prior_publication):
        prior_ok=isinstance(prior_publication,dict) and (prior_publication.get('position'),prior_publication.get('producer'),prior_publication.get('transport'),prior_publication.get('sector_retire_quorum'))==(0,producer,transport,272)
        if (producer,transport)!=self.generation or self.live or len(self.completed)!=272 or self.cancelled or not prior_ok or any(i not in self.opcodes or self.opcodes[i]['retire'] is None for i in (10,11)):raise ValueError('publication/quorum/actual IRS/prior generation')
        if self.lease is not None:raise ValueError('duplicate lease')
        self.lease=(producer,transport);self.record('lease_acquire_INPUT')
    def reader_accept(self,i,sector,producer,transport):
        if self.lease!=(producer,transport) or self.lease_cancelled:raise ValueError('actual lease identity/cancellation')
        if len(self.readers)>=4:return False
        f=self.read_rows
        if not 0<=i<288 or f[i]['sector']!=sector or i in self.readers or i in self.reader_done:raise ValueError('addressed reader identity')
        if not self.RAW_read_ready(sector):raise ValueError('RAW backing not visible')
        p=bankmap(sector)['pc']
        if len(self.pending_commands[p])>=3:return False
        b=Beat(sector,i,producer,transport,accepted_ps=self.now)
        before=len(self.cal.events);col=self.cal.plan(b,edge(max(self.now+3*PHY,self.pc_busy[p])+37*FAST,PHY))
        assert all(e['ps']>=self.now for e in self.cal.events[before:])
        self.pc_busy[p]=col+FAST;self.pending_commands[p].append(col);self.peak['command_slots_per_PC']=max(self.peak['command_slots_per_PC'],len(self.pending_commands[p]));self.refresh_next[p]=self.cal.next_ref[p]
        due=edge(col+source_timing()['CL_PS']+source_timing()['BURST_PS']+source_timing()['RSP_PS']+(6+self.route_edges)*FAST,SERIAL)+3*SERIAL
        self.readers[i]=dict(sector=sector,producer=producer,transport=transport,result=False,ready=due,retired=False);self.peak['reader_owners']=max(self.peak['reader_owners'],len(self.readers));return True
    def reader_result(self,i,identity):
        x=self.readers[i]
        if tuple(identity)!=(x['sector'],x['producer'],x['transport']) or x['result'] or self.now<x['ready']:raise ValueError('immutable held reader result or early physical return')
        x['result']=True
    def reader_retire(self,i,identity):
        x=self.readers[i]
        if tuple(identity)!=(x['sector'],x['producer'],x['transport']) or not x['result']:raise ValueError('actual addressed reader result retirement')
        if x['retired']:raise ValueError('duplicate addressed reader retirement')
        x['retired']=True;x['reverse_due']=edge(self.now+(self.route_edges+3)*FAST,FAST)
    def reader_reverse_credit(self,i,identity):
        x=self.readers[i]
        if tuple(identity)!=(x['sector'],x['producer'],x['transport']) or not x['retired'] or self.now<x['reverse_due']:raise ValueError('actual reader reverse CDC credit')
        (self.reader_cancelled if x.get('cancel') else self.reader_done).add(i);del self.readers[i]
    def release(self,producer,transport):
        if self.lease_cancelled or self.lease!=(producer,transport) or self.readers or len(self.reader_done)!=288 or any(i not in self.opcodes or self.opcodes[i]['retire'] is None for i in (12,13,14,15)):raise ValueError('KV_READ/SCORES/EXP/PV actual IRS/result and held lease release')
        self.lease=None;self.lease_released=True;self.record('lease_release_INPUT')
    def cancel(self,i,identity):
        x=self.owner(i,identity);x['cancel']=True
        if x['phase'] in ['RMW_result_wait','RMW_retire_wait']:
            x['phase']='cancel_read_wait'
        elif x['phase'] in ['RMW_wait','WR_ready']:
            x['phase']='retire_held';x['reverse_due']=edge(self.now+(self.route_edges+3)*FAST,FAST)
        # Emitted WR still commits backing/held cancellation; no early slot reuse.
        self.record('cancel_INPUT',i)

    def cancel_read_drain(self,i,identity):
        x=self.owner(i,identity)
        if x['phase']!='cancel_read_wait' or not x['cancel'] or self.now<x['RMW_ready']:raise ValueError('actual cancelled RMW return/discard still required')
        x['phase']='retire_held';x['reverse_due']=edge(self.now+(self.route_edges+3)*FAST,FAST);self.record('RMW_discard_INPUT',i)
    def lease_cancel(self,producer,transport):
        if self.lease!=(producer,transport):raise ValueError('cancel matching held lease')
        self.lease_cancelled=True;self.record('lease_cancel_INPUT')
    def reader_cancel_discard(self,i,identity):
        x=self.readers[i]
        if not self.lease_cancelled or tuple(identity)!=(x['sector'],x['producer'],x['transport']) or self.now<x['ready']:raise ValueError('actual cancelled reader return/discard')
        x['cancel']=True;x['retired']=True;x['reverse_due']=edge(self.now+(self.route_edges+3)*FAST,FAST)
    def lease_cancel_release(self,producer,transport,actual_consumer_discard_ACKs):
        expected={(i,*self.opcode_inputs[i]) for i in (13,15) if i in self.opcode_inputs}
        if len(expected)!=2 or not self.lease_cancelled or self.lease!=(producer,transport) or self.readers or set(actual_consumer_discard_ACKs)!=expected:raise ValueError('actual matching SCORES/PV slot/serial/epoch discard ACKs and drained cancelled readers required')
        self.lease=None;self.lease_released=True;self.record('lease_cancel_release_INPUT')

    def writer_context_release(self):
        if not self.lease_released or self.lease is not None or self.live or self.readers or any(x['retire'] is None for x in self.opcodes.values()):raise ValueError('held lease release/owned IRQ retirement before writer reuse')
        self.record('writer_context_release_INPUT')

def comparisons():
    parent_path='results/uarch/parent_qwen_hbm_service_enlargement_lower_bound_20261002/review.json'
    parent_raw=pinned(ROOT,'80ba82e57',parent_path);parent=json.loads(parent_raw)
    fp=json.loads(get('results/floorplan/hbm_gpu/qwen_hbm_die.json'));ds=json.loads(get('results/floorplan/hbm_gpu/v41_hbm_die.json'));r=reserves();g=geometry()
    assert parent['geometry_source']['sha256']==hashlib.sha256(get('results/floorplan/hbm_gpu/qwen_hbm_die.json')).hexdigest()
    assert abs(float(parent['required_mm2_per_stack'])-r['base_r9_mm2_per_stack'])<1e-12
    wider=2*r['minimum_slot_mm2_per_stack']*1e6/630.72
    new_height=fp['die_um'][1]+2*g['delta_um']
    return dict(scope='QWEN_HBM_ONLY; NO_DEEPSEEK_AREA_OR_QUALIFICATION_TRANSFER',parent_lower_bound=dict(commit='80ba82e57',path=parent_path,sha256=hashlib.sha256(parent_raw).hexdigest(),review=parent),Qwen=dict(stacks_system=8,stacks_per_die=4,SMs_per_die=32,L2_macros_per_die=256,required_base_mm2_per_stack=r['base_r9_mm2_per_stack'],base_system_shortfall_mm2=8*(r['base_r9_mm2_per_stack']-10.0158336),source_geometry_commit=PIN),DeepSeek=dict(source_commit=PIN,source_path='results/floorplan/hbm_gpu/v41_hbm_die.json',source_sha256=hashlib.sha256(get('results/floorplan/hbm_gpu/v41_hbm_die.json')).hexdigest(),SMs_per_source_die=ds['sm_count'],stacks_per_source_die=ds['macro_counts']['ot_hbm3e_phy'],L2_macros_per_source_die=ds['macro_counts']['ot_sram_1r1w_1024x256_m2_r2c2'],service_regions=[x for x in ds['regions'] if x['kind']=='service'],required_service_mm2_per_stack=None,remediation_fit=False,qualification_transfer=False),
      remedies=[dict(name='deeper bands and inward L2, retained outline',recommended=True,depth_um=g['selected_depth_um'],outline_mm2=815,added_reserved_service_mm2_per_die=g['added_service_area_mm2_per_die'],added_oneway_FAST_edges=g['conservative_added_oneway_FAST_edges'],geometry_fit=True,hardware_fit=False),dict(name='wider bands at existing630.72um depth',required_width_um=wider,available_width_um=31760,width_only_inside_outline=False,implied_die_width_um=wider+40,implied_outline_mm2=(wider+40)*fp['die_um'][1]/1e6,package_qualification=False),dict(name='deeper bands preserving every interior coordinate by enlarging die',required_die_height_um=new_height,outline_mm2=new_height*31800/1e6,added_outline_mm2=(new_height-fp['die_um'][1])*31800/1e6,reticle_source_limit_mm2=815,within_source_reticle=False,package_qualification=False),dict(name='exclusive projection PDN stress alternative',slot_mm2_per_stack=r['exclusive_projection_alternative_slot_mm2_per_stack'],band_depth_um=snap_up(r['exclusive_projection_alternative_slot_mm2_per_stack']*1e6/15880),reason='Deliberately reserves complete strap projections below every routing layer; not chosen physical minimum')],
      package='Retained candidate outline and source PHY locations/width; no new package electrical/bump-map/PDN qualification inferred',zero_PHY_replacement_credit=True)

def composed():


    r=reserves();g=geometry()
    uarch=get('tools/uarch_model.py')
    return dict(schema='Conventional_GPU_shoreline_geometry_provider_candidate_r10',status='QWEN_REVIEWABLE_SIZING_REMEDY_GEOMETRY_BUDGET_PASS_NO_HARDWARE_ADMISSION',scope='Qwen HBM only, eight system stacks; no DS requirement transfer',reserves=r,geometry=g,comparison=comparisons(),
      unified_model_overlay=dict(source='tools/uarch_model.py',commit=PIN,sha256=hashlib.sha256(uarch).hexdigest(),design='qwen_hbm_gpu',MACs_per_cycle_added=0,SMs_per_die=32,PCs_system=256,stacks_system=8,sector_bytes=32,request_bits=472,return_bits=471,retirement_bits=404,lease_bits=350,clock_domain_period_ps=dict(controller=str(FAST),consumer=str(SERIAL),PHY_command=str(PHY)),single_user_added_route_ps=str(2*g['conservative_added_oneway_FAST_edges']*FAST),critical_path='Per-sector max(actual RF result, bank/scan service, WR column+CWL+burst, held ACK resource/CDC, bitstore/sector-retire/reversecredit); publication=max272 credits plus real writer/fence IRS; reader=maxpublication/prior-generation/acquire; release=maxactual SCORES/PV results+IRS including EXP14, held release. Route increase applied to each causally exposed path, never272 serial sums.'),
      physical_interface=dict(existing=dict(AW=31,LEN=5,BEAT=4,min_period_ps=1000),required=dict(AW=34,LEN=6,BEAT=5,controller_period_ps=str(FAST),PHY_command_period_ps=str(PHY)),delta_request_response_pins=3+1+32,new_command_completion_pins=r['PHY_added_signal_pins']-36,total_candidate_signal_pins=r['PHY_candidate_total_signal_pins'],candidate_pin_span_um=r['PHY_pin_span_um'],edge_pin_capacity_with50percent_escrow=r['PHY_50percent_edge_pin_capacity'],action='NEW_OPT_IN_AW34_6_5_CONVENTIONAL_COMMAND_PHY_INTERFACE_ABSTRACT_AND_HARDENING_REQUIRED; existing source/ports retained byte-identical, no truncation/splitting credit',command_bits=r['command_bits'],async_PC_FIFO_depth=2,PHY_clock_change='512ps command domain is proposed from source tCK512/burst1024; source abstract1000ps does not qualify it. Controller833.333ps, consumer1111.111ps stay separate; no universal clock.',outer_request_ports=dict(clk=1,rst_n=1,req_v=1,req_rdy=1,req_we=1,req_addr=34,req_len=6,req_tag=16,req_wdata=256),outer_response_ports=dict(rsp_v=32,rsp_rdy=32,rsp_tag=512,rsp_beat=160,rsp_data=8192),parallel_return_ports=32,physical_peak_stack_Bps=32*32/(1024e-12),PCs_per_stack=32,clock_dynamic_power_frequency_multiplier=dict(controller_vs_source1ns=1.2,PHY_command_vs_source1ns=1.953125),clock_uncertainties_ps=dict(setup=60,hold=25),service_bandwidth_caveat='Outer32-PC response vectors and inherited GPU weight transport retained; finite KV ownership endpoints consume their own prepared stream. All PCs/HBM burst bandwidth preserved in proposed interface; frozen18..35edge scan still limits loaded controller throughput. No1TB/s effective controller or fullprogram rate claim.'),
      provider_inventory=dict(writer_sectors=272,partial_RMW_reads=256,reader_sectors=288,minimum_column_events=816,read_columns=544,WR_columns=272,HBM_payload_bytes=816*32,metadata_only_no_checkpoint_payload=True,sector_owners_per_die=4,sector_FIFO=4,opcode_IRS_slots=32,opcode_capture_FIFO=4,reader_owners_per_die=4,lease_FIFO=4,pending_WR_per_stack=4,request_queue_per_PC=64,read_return_queue_per_PC=32,reversecredit_FIFO=4,held_valid_ready=True,cancellation_tombstones=True,full_address_epoch_identity=True,actual_source_endpoints_implemented=False,model_endpoints=['owned_RF_commit_INPUT','WR_reserved_before_column','delayed_backing_visibility','held_ACK_capture','forward_CDC','addressed_bit_store','registered_sector_retire','reverse_CDC_credit','separate_opcode_IRS_capture','reader_acquire_result_retire','SCORES_EXP_PV_IRS','held_lease_release','cancel_drain_tombstone']),
      exact_arithmetic_admission=dict(status='FAIL_PARENT_BF16_MUL_FINITE_UNDERFLOW',parent_commit='b33395215',witness='0080*3b80 validFP32bits00008000; old0/fault',repair_owner='Epicurus',qualification_transfer=False),source_input_events=[],provider_PASS=False,RTL_admission=False,physical_admission=False,hardware_rate_credit=0,default_enabled=False,
      next_review_gate='Review this expanded-band geometry, reserve budgets, new PHY command/CDC interface and explicit-input protocol. Then require implementation inventory, exact numerical/ownership gates and SS/FF closure before admission; no build authorized by this record.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();a.output_dir.mkdir(exist_ok=False)
    x=composed()
    for name,value in [('model_r10.json',x),('floorplan_r10.json',x['geometry']),('comparison_r10.json',x['comparison'])]:
        (a.output_dir/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    g=x['geometry'];lines=['VERSION 5.8 ;','DIVIDERCHAR "/" ;','BUSBITCHARS "[]" ;','DESIGN qwen_hbm_shoreline_candidate_r10 ;','UNITS DISTANCE MICRONS 1000 ;',f"DIEAREA ( 0 0 ) ( {round(g['die_um'][0]*1000)} {round(g['die_um'][1]*1000)} ) ;",f"COMPONENTS {len(g['macro_placements'])} ;"]
    for m in g['macro_placements']:lines.append(f"- {m['name']} {m['macro']} + PLACED ( {round(m['x']*1000)} {round(m['y']*1000)} ) {m['orient']} ;")
    lines+=['END COMPONENTS','END DESIGN'];(a.output_dir/'floorplan_r10.def').write_text('\n'.join(lines)+'\n')

