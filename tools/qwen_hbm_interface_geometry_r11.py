#!/usr/bin/env python3
"""Source-pinned address/1GHz PHY composition and separate full resident layouts.
Opt-in analytical overlay; no implementation or physical qualification.
"""
import argparse, hashlib, json, math, re
from pathlib import Path
from fractions import Fraction as F
from qwen_hbm_shoreline_remedy_r10 import get, reserves, geometry, rectangles_overlap, snap_up, PIN
from qwen_hbm_downstream_contract_r8 import fixture
from qwen_hbm_controller_calendar_r2 import bankmap, BASE, PROGRAM, weight_ranges
from qwen_hbm_controller_events_r1 import ROOT, pinned, REV, SOURCE, source_timing

OUT='results/uarch/qwen_hbm_interface_geometry_20261002'
CAPACITY=22500000000
SECTORS=CAPACITY//32

def inverse(pc,bank,row,column):
    if not (0<=pc<32 and 0<=bank<32 and 0<=row<1<<19 and 0<=column<32):
        raise ValueError('bank tuple bounds')
    s=(row<<15)|(column<<7)|((((bank>>2)^(row>>2))&7)<<12)|((bank^row)&3)
    return s|((pc^column^((s>>12)&31))<<2)

def system_address(die,stack,local):
    if not (0<=die<2 and 0<=stack<4 and 0<=local<1<<31):raise ValueError('system namespace')
    return (die<<33)|((local>>2)<<4)|(stack<<2)|(local&3)

def decode_system(s):
    if not 0<=s<1<<34:raise ValueError('AW34')
    return s>>33,(s>>2)&3,(((s&((1<<33)-1))>>4)<<2)|(s&3)

def checked_local(s,n):
    if not (0<=s<1<<34 and 1<=n<=32 and s+n<=SECTORS):
        raise ValueError('held full-owner address/length fault BEFORE narrowing or head pop')
    assert s<1<<31
    return s

class TagOwners:
    """Finite map: accepted generations immutable; all actual beat captures needed.
    Terminal consumer ownership is separate from PHY tag residence.
    """
    def __init__(self):self.live={};self.pc=[0]*32
    def accept(self,s,n,caller,producer,transport):
        checked_local(s,n)
        pcs={bankmap(s+b)['pc'] for b in range(n)}
        if any(self.pc[p]>=128 for p in pcs) or len(self.live)>=4096:return None
        tag=next(i for i in range(4096) if i not in self.live)
        self.live[tag]=dict(owner=(s,n,caller,producer,transport),pcs=pcs,seen=set(),held=None)
        for p in pcs:self.pc[p]+=1
        return tag
    def capture(self,tag,pc,beat,data):
        x=self.live[tag];s,n,*_=x['owner']
        if not (0<=beat<n and bankmap(s+beat)['pc']==pc) or beat in x['seen']:
            raise ValueError('return address/PC/beat or duplicate')
        x['seen'].add(beat)
        return (s+beat,*x['owner'][2:],data)
    def reclaim(self,tag):
        x=self.live[tag]
        if len(x['seen'])!=x['owner'][1]:raise ValueError('quarantine until all actual returns captured')
        for p in x['pcs']:self.pc[p]-=1
        del self.live[tag]

def map_cost():
    # Native one descriptor/core edge, up to32 touched PCs. Independent CAM
    # lookup plus immutable1R1W metadata RAM perPC; mutable bitmap stays in FF.
    macro='ot_sram_1r1w_128x256_m1_r2c2'
    spec=json.loads(get(f'physical/asap7_memory_macros/{macro}/{macro}.json'))
    ff=dict(CAM_tag_valid=32*128*13,seen_masks=32*128*32,
      lookup_pipeline=32*12*(278+128),root_expected_done=4096*64,
      tag_allocator=4096+32*127*8,reverse_credit_router=32*32*22*5)
    bits=sum(ff.values());logic=32*128*12+32*127*12+32*32*22*5
    ramarea=32*spec['area']['macro_area_um2']/1e6
    cellarea=bits*.2916/.5/1e6+logic*.2/.5/1e6
    levels=0;v=bits;bufs=0
    while v>1:v=math.ceil(v/16);bufs+=v;levels+=1
    cts=bufs*.4374/.5/1e6
    return dict(macro=macro,macros_per_stack=32,immutable_owner_bits=227,macro_width=256,
      FF_bits=ff,total_FF_bits=bits,gate_bit_equivalents=logic,macro_area_mm2=ramarea,
      logic_area_mm2=cellarea,additional_clock_mm2=cts,area_mm2=ramarea+cellarea+cts,
      global_tags=4096,per_PC_contexts=128,source_queue_bound_per_PC=64+32+4+3+2,
      PHY_tag_wire_bits=16,allocated_tag_bits=12,original_caller_tag_preserved_bits=16,
      lookup_CORE_edges=12,lookup_initiation_interval_CORE_edges=1,
      allocator_banks=32,allocator_tree_edges=7,bank_freeze=True,
      memory_ports='PerPC immutable context1write+1read/core edge; mutable masks separate FF; tag allocation freezes selected bank, rotating32 banks hides7edge tree. Backpressure if a PC context or tag unavailable.',
      timing_scope='Pipelined capacity proposal; macro SS clkq and logic SS/FF remain admission checks; area proxies from inherited model, no measured closure')

def qwen_geometry():
    r=reserves();c=map_cost()
    # Retain every r10 budget incl widened-interface allowance: zero replacement
    # credit. This over-reserves the preferred minimal native interface.
    r['non_PDN_need_mm2']+=c['area_mm2']
    r['minimum_slot_mm2_per_stack']=r['non_PDN_need_mm2']/(1-r['PDN_charged_site_fraction'])
    r['minimum_band_depth_um']=r['minimum_slot_mm2_per_stack']*1e6/15880
    g=geometry(r);macro=c['macro'];a=json.loads(get(f'physical/asap7_memory_macros/{macro}/{macro}.json'))['area']
    for band in (x for x in g['regions'] if x['kind']=='service'):
        for stack in range(2):
            for i in range(32):
                g['macro_placements'].append(dict(name=f"r11_{band['name']}_{stack}_owner{i}",macro=macro,
                  x=band['x']+stack*15880+2200+(i%8)*(a['macro_width_um']+8.64),
                  y=band['y']+2.16+(i//8)*(a['macro_height_um']+4.32),
                  w=a['macro_width_um'],h=a['macro_height_um'],orient='R0',status='added_owner_context'))
    ps=g['macro_placements'];conf=[(a['name'],b['name']) for i,a in enumerate(ps) for b in ps[i+1:] if rectangles_overlap(a,b)]
    assert not conf and len(ps)==676
    g.update(owner_context_macros_per_stack=32,total_macros_per_die=676,macro_pair_conflicts=conf,
      model_scope='Qwen cost composed with finite PHY-owner map; retained r10 CTS/via/adapter allowances, no PHY credit',reserves=r)
    return g

def ds_geometry(depth):
    p='results/floorplan/hbm_gpu/v41_hbm_die.json';fp=json.loads(get(p));delta=depth-630.72
    regions=[]
    for x in fp['regions']:
        x=dict(x)
        if x['name']=='svc_south':x['h']=depth
        if x['name']=='svc_north':x['y']-=delta;x['h']=depth
        if x['kind']=='l2':x['y']+=delta if x['name'].startswith('l2_s') else -delta
        regions.append(x)
    blocks=[x for x in regions if x['kind']!='die']
    conf=[(a['name'],b['name']) for i,a in enumerate(blocks) for b in blocks[i+1:] if rectangles_overlap(a,b)]
    raw=get('results/floorplan/hbm_gpu/v41_hbm_die_macros.def');assert hashlib.sha256(raw).hexdigest()==fp['def_sha256']
    ps=[]
    for name,macro,x,y,orient in re.findall(r'- (\w+) (\w+) \+ FIXED \( (\d+) (\d+) \) (\w+) ;',raw.decode()):
        y=int(y)/1000
        if name.startswith('l2_s'):y+=delta
        if name.startswith('l2_n'):y-=delta
        ps.append(dict(name=name,macro=macro,x=int(x)/1000,y=y,orient=orient))
    assert len(ps)==292 and not conf
    return dict(design='DeepSeek_GPU_HBM',source_commit=PIN,source_sha256=hashlib.sha256(get(p)).hexdigest(),
      source_DEF_sha256=fp['def_sha256'],die_um=fp['die_um'],regions=regions,macro_placements=ps,
      macro_counts=fp['macro_counts'],dedicated_hub=fp['dedicated_hub'],service_depth_um=depth,
      service_capacity_mm2_per_stack=15880*depth/1e6,geometry_conflicts=conf,geometry_envelope_fit=True,
      DS_provider_area_fit=False,required_DS_service_area='NOT_DERIVED_FROM_QWEN',
      actual_blocker='DS source-resident hub/SM/PHY/L2 layout preserved; DS-specific owned writer/reader counts, endpoint residence and mixed-service admission must be supplied by its source model owner. No Qwen272/288 or11.33234 cost transfer.',
      source_historical_clock_hz=fp['clock_hz'],clock_transfer=False,physical_admission=False)

def composed():
    f=fixture();g=json.loads(pinned(ROOT,BASE,PROGRAM));wr=weight_ranges(g)
    rows=f['sector_rows']+f['KV_prefix_read_rows'];maximum=max(x['sector'] for x in rows)
    for x in rows:
        s=x['sector'];checked_local(s,1);m=bankmap(s);assert inverse(m['pc'],m['bank'],m['row'],(s>>7)&31)==s
    max_weight=0
    for w in wr:
        for r in w['ranges']:
            for s in r['stacks']:
                if s['line_count']:
                    end=s['first_local_sector']+(s['line_count']-1)*4+3
                    checked_local(end,1);max_weight=max(max_weight,end)
    q=qwen_geometry();ds=ds_geometry(q['selected_depth_um'])
    paths=['tools/uarch_model.py','tools/mem_compiler/hbm_phy_gen.py',
      'physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy_bb.v',
      'physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy_ss.lib','configs/hardware/technology.json']
    pins={p:dict(commit=PIN,sha256=hashlib.sha256(get(p)).hexdigest()) for p in paths}
    pins[SOURCE]=dict(commit=REV,sha256=hashlib.sha256(pinned(ROOT,REV,SOURCE)).hexdigest())
    return dict(schema='HBM_native_address_frequency_geometry_r11',source_pins=pins,Qwen=q,DeepSeek=ds,
      exact_metadata=dict(instructions=len(g['instructions']),writers=272,RMW=256,readers=288,weight_instructions=len(wr),max_KV_local_sector=maximum,max_weight_local_sector=max_weight,no_payload=True),
      address=dict(units='32B stack-local sector; die and stack are separate actual metadata selectors',
        system_namespace='Optional flattened AW34: die=bit33, stack=bits3:2, local=((system_low33>>4)<<2)|(system&3). This is NOT existing local req_addr.',
        bank_inverse='row=s>>15; column=(s>>7)&31; bankhigh=((s>>12)^(row>>2))&7; banklow=(s^row)&3; pc=((s>>2)^(s>>7)^(s>>12))&31; inverse() is exact',
        capacity_bytes=CAPACITY,legal_sectors=SECTORS,needed_local_bits=(SECTORS-1).bit_length(),PHY_AW=31,
        row_bits_PHY=16,column_bits=5,PCs=32,banks_per_PC=32,sector_bytes=32,
        fault='Keep fullAW34 owner; validate entire burst against physical capacity before narrowing/reservation/pop. 2^32 is held-address fault, never masked to0.',alias_failure_preserved=True),
      PHY=dict(existing_AW_LEN_BEAT=[31,5,4],proposed_AW_LEN_BEAT=[31,6,5],max_count=32,
        proposed_total_pins=9370,pin_span_um=9370*.192,edge_capacity_50percent=31250,
        width_delta_pins=33,held_visible_slot_valid_ready_pins=128,zero_PHY_replacement_credit=True,
        unchanged_chunk16_request_ceiling_Bps=512e9,unchanged_literal31_request_ceiling_Bps=992e9,
        beat4_alias_witness=dict(base=8176,beats=[0,16],sectors=[8176,8192],PCs=[bankmap(8176)['pc'],bankmap(8192)['pc']],wire_beats=[0,0]),
        descriptor_port_ceiling_Bps=1024e9,parallel_response_port_ceiling_Bps=1024e9,
        clock_ps=dict(controller='2500/3',consumer='10000/9',PHY_core=1000,DRAM_internal_tCK=512),
        PHY_SS_abstract_min_period_ps=1000,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
        clock_admission=False,frequency_scope='Retain1GHz hardmacro core, native32beat descriptor; price explicit CDC. DRAM512ps is internal timing quantum, not a512ps command-core closure claim.',
        proposed_hooks='Native full-beat return and held perPC WRvisible slot/valid/ready; conventional command accept journal at core boundary. Existing abstraction does not expose these hooks; new opt-in implementation/abstract required.'),
      capacity=map_cost(),
      dependency=dict(bridge_forward_CORE_edges=3,bridge_return_FAST_edges=3,lookup_CORE_edges=12,
        held_WRvisible='max(actual WR column+CWL6250+burst1024, destination ownership slot availability); ACK capture immutable until ready, not WRdone pulse',
        RMW_read_result='max(actual CL+burst and return arbitration, held return availability)+3FAST CDC+12CORE map lookup+NoC route+consumer CDC; then actual27SER RMW/result-retire inputs',
        critical_path='Writer visibility=max(causal bank/currentREF/serialized18..35 scan+headprefetch, actual RMW result+owned retire, reserved WR column+CWL+burst, heldACK/CDC). Sector store+retire+reversecredit independently free4 owners. Whole writerIRS waits272 sectors; reader publication also waits fenceIRS/prior-generation. Reader lease waits actual288 result+retire+reversecredit and SCORES/EXP/PV IRS; no timing-bound callbacks.',
        new_route_FAST_edges=q['new_oneway_route_FAST_edges'],service_bandwidth_credit=False),
      terminal=dict(geometry_model_fit=True,DS_service_admission=False,provider_implementation=False,
        source_retirement_events=0,arithmetic_admission=False,physical_admission=False,
        blockers=['Actual source has no addressed held WR-visible/sector-retire/reader-lease endpoint; proposed finite protocol must be implemented after review.',
          'LEN6/BEAT5 native PHY abstract and1GHz domain CDC need SS/FF setup/hold/skew/macro checks; no existing timing transfer.',
          'DS-specific service ownership inventory absent from supplied geometry; emitted layout is resident-preserving capacity envelope.',
          'Shared BF16 underflow arithmetic failure b33395215 remains; 4933 and952 observations unchanged.'],
        no_compile_PR_or_VM=True))

def emit(out):
    out.mkdir(exist_ok=False);x=composed()
    (out/'model_r11.json').write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
    for name,g in [('qwen',x['Qwen']),('deepseek',x['DeepSeek'])]:
        (out/(name+'_floorplan_r11.json')).write_text(json.dumps(g,sort_keys=True,indent=2)+'\n')
        ps=g['macro_placements'];lines=['VERSION 5.8 ;','DIVIDERCHAR "/" ;','BUSBITCHARS "[]" ;',f'DESIGN {name}_service_candidate_r11 ;','UNITS DISTANCE MICRONS 1000 ;',f"DIEAREA ( 0 0 ) ( {round(g['die_um'][0]*1000)} {round(g['die_um'][1]*1000)} ) ;",f'COMPONENTS {len(ps)} ;']
        for p in ps:lines.append(f"- {p['name']} {p['macro']} + PLACED ( {round(p['x']*1000)} {round(p['y']*1000)} ) {p['orient']} ;")
        (out/(name+'_floorplan_r11.def')).write_text('\n'.join(lines+['END COMPONENTS','END DESIGN'])+'\n')
    return x

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--output-dir',type=Path,required=True)
    emit(a.parse_args().output_dir)
