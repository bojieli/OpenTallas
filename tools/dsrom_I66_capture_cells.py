#!/usr/bin/env python3
"""Allowed-cell constructive capture pricing; no placed timing/slot credit."""
import argparse,collections,fnmatch,hashlib,json,math,re
from pathlib import Path
import dsrom_I66_capture_banks as B
ROOT=B.ROOT; OUT=ROOT/'results/uarch/dsrom_I66_capture_cells_20261002'
HQ='DFFHQNx1_ASAP7_75t_R'; ASR='DFFASRHQNx1_ASAP7_75t_R'
NAND='NAND2x1_ASAP7_75t_R'; INV='INVx1_ASAP7_75t_R'; BUF='BUFx4_ASAP7_75t_R'
def group(t,name,value):
    m=re.search(r'\b'+name+r'\s*\(\s*'+re.escape(value)+r'\s*\)\s*\{',t)
    if not m: raise ValueError('missing source group '+name+' '+value)
    i=t.index('{',m.start());d=1;j=i+1
    while d: d+=(t[j]=='{')-(t[j]=='}');j+=1
    return t[i+1:j-1]
def facts():
    bodies=json.loads((OUT/'inputs/cell_bodies.json').read_text()); lefs=json.loads((OUT/'inputs/cell_LEF.json').read_text())
    config=(OUT/'inputs/config.mk.txt').read_text()
    patterns=[x for line in re.findall(r'^export DONT_USE_CELLS\s*(?:=|\+=)\s*([^\n]+)',config,re.M) for x in line.split()]
    result={}
    for name in (HQ,ASR,NAND,INV,BUF):
        if any(fnmatch.fnmatchcase(name,p) for p in patterns): raise ValueError('excluded master')
        result[name]={}
        for corner,cells in bodies.items():
            t=cells[name];pins={}
            for pin in re.findall(r'\bpin\s*\(\s*([^)]*)\)',t):
                p=group(t,'pin',pin); cap=re.search(r'(?m)^\s*capacitance\s*:\s*([\d.]+)',p)
                fun=re.search(r'\bfunction\s*:\s*"([^"]+)"',p)
                maximum=re.search(r'\bmax_capacitance\s*:\s*([\d.]+)',p)
                pins[pin]=dict(cap_fF=float(cap[1]) if cap else None,function=fun[1] if fun else None,max_cap_fF=float(maximum[1]) if maximum else None)
            size=list(map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lefs[name]).groups()))
            area=float(re.search(r'\barea\s*:\s*([\d.]+)',t)[1])
            if abs(area-size[0]*size[1])>1e-8: raise ValueError('Liberty/LEF area')
            result[name][corner]=dict(area_um2=area,size_um=size,pins=pins)
            if name in (HQ,ASR):
                ff=group(t,'ff','IQN,IQNN')
                if 'next_state : "!D"' not in ff or pins['QN']['function']!='IQN': raise ValueError('QN polarity')
                if name==ASR and ('preset : "!RESETN"' not in ff or 'clear : "!SETN"' not in ff): raise ValueError('reset polarity')
            elif pins['Y']['function']!={NAND:'(!A) + (!B)',INV:'!A',BUF:'A'}[name]: raise ValueError('gate function')
    return result,patterns

def tree(sinks,fanout=8):
    if sinks<1: return []
    levels=[]
    while sinks>1:
        sinks=math.ceil(sinks/fanout); levels.append(sinks)
    return levels

def mux(a,b,s):
    # INV(s) shared by a vector; three actual NAND2 gates per bit.
    n0=not(a and not s); n1=not(b and s); return not(n0 and n1)

def invariant(plans):
    for p in plans:
        for row,root in p['rows'].items():
            if root!=(row%256)//2: raise ValueError('fixed bank decoder not legal for phase')
    return True

def model():
    f,policy=facts(); plans,depths=B.allocation(); invariant(plans)
    # All 768 maps identical. Fixed expected row constants require no lookup
    # SRAM and no mutable row ownership table. No change to reduction order.
    d=depths[0]; record_bits=576*69; ctrl=1483 # prior1468 +bank-ID7 +stickyfault2 +causal-fence latches6
    sections={}
    def add(section,master,count): sections.setdefault(section,collections.Counter())[master]+=count
    add('record_storage',HQ,record_bits);add('record_storage',INV,record_bits)
    # Every storage bit has an explicit hold/write feedback mux.
    add('record_write_hold_mux',NAND,3*record_bits);add('record_write_hold_mux',INV,576)
    read_nodes=sum(n-1 for n in d)+127 # 448 local +127 inter-root
    add('scalar_read_mux',NAND,3*69*read_nodes);add('scalar_read_mux',INV,read_nodes)
    # Constant row membership: per-root shared input inversions then
    # 16 literals ANDed using15 NAND+INV. Includes high row bits, no AW alias.
    add('constant_row_decode',INV,128*16+576*15);add('constant_row_decode',NAND,576*15)
    add('control_storage',ASR,ctrl);add('control_storage',INV,ctrl)
    add('control_write_hold_mux',NAND,3*ctrl);add('control_write_hold_mux',INV,ctrl)
    # Explicit vector select buses: all record writes
    # and575 read nodes have69 loads. Positive buffered fanout forest.
    vector_select=576+read_nodes
    add('vector_select_fanout',BUF,vector_select*sum(tree(69)))
    add('clock_fanout',BUF,sum(tree(record_bits+ctrl)))
    add('reset_fanout',BUF,sum(tree(ctrl)))
    add('owner_active_fanout',BUF,sum(tree(128)))
    # 128 fill+read counters, three-bit ripple increment: 2 XOR(4 NAND)
    # and one AND(NAND+INV), before the charged feedback mux.
    add('counter_increment',NAND,256*9);add('counter_increment',INV,256*2)
    # Each row decoded request is admitted only active AND not-seen AND valid;
    # no field-ready or refusal. Legal source trace has no duplicates.
    # Illegal wire handling remains a poison/discard terminal contract, never
    # a claim that arbitrary extra records fit576 finite destinations.
    add('row_valid_owner_duplicate_guard',NAND,576*3);add('row_valid_owner_duplicate_guard',INV,576*4)
    # Explicit boolean AND/OR reductions for source terminal qualification.
    # 128 bank empty flags +576 seen flags -> 702 two-input operations.
    add('terminal_reductions',NAND,127+575);add('terminal_reductions',INV,127+575)
    # Concrete remaining local control construction, with no SRAM tables.
    # Six3-bit counters are not substituted for128 producer ports.
    add('bank_empty_compare',NAND,128*14);add('bank_empty_compare',INV,128*5)
    add('bank_full_decode',NAND,128*2);add('bank_full_decode',INV,128*5)
    add('local_read_position_decode',NAND,576*2);add('local_read_position_decode',INV,576*2+128*3)
    add('selected_bank_decode',NAND,128*6);add('selected_bank_decode',INV,128*6+7)
    add('bank_valid_read_write_qualification',NAND,128*8);add('bank_valid_read_write_qualification',INV,128*8)
    # Frozen context matches123bits of incoming provider command/header;
    # existing raw root has ZERO generation bits and cannot be re-labelled.
    add('incoming_context_compare',NAND,123*4+122);add('incoming_context_compare',INV,123+122)
    add('bank_ID_increment',NAND,29);add('bank_ID_increment',INV,6)
    # reserve:7-input AND; release:7-input AND; sticky fault:7-input OR.
    add('reserve_terminal_rearm_and_fault_logic',NAND,6+6+6)
    add('reserve_terminal_rearm_and_fault_logic',INV,6+6+12)
    # Selected scalar bank uses7bit bank ID plus three-bit position. Balanced
    # read tree, no physical spare SRAM seat and no new accepted producer ACK.
    total=collections.Counter()
    for counts in sections.values(): total.update(counts)
    # TIEHI source policy names actual master; one per ASR SETN avoids
    # unqualified tie fanout. LEF body is charged even without timing arc.
    tie='TIEHIx1_ASAP7_75t_R';lef=json.loads((OUT/'inputs/cell_LEF.json').read_text())[tie]
    tie_size=list(map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef).groups()))
    if tie not in (OUT/'inputs/config.mk.txt').read_text() and 'TIEHIx1_ASAP7_75t_$(PRIMARY_VT_TAG)' not in (OUT/'inputs/config.mk.txt').read_text(): raise ValueError('tie source policy')
    section_area={s:sum(f[n]['SS']['area_um2']*k for n,k in c.items()) for s,c in sections.items()}
    tie_area=ctrl*math.prod(tie_size); area=sum(section_area.values())+tie_area
    loads={}
    for corner in ('SS','FF'):
        fp={n:v[corner]['pins'] for n,v in f.items()}
        loads[corner]=dict(clock_pin_fF=record_bits*fp[HQ]['CLK']['cap_fF']+ctrl*fp[ASR]['CLK']['cap_fF'],
            reset_pin_fF=ctrl*fp[ASR]['RESETN']['cap_fF'],SETN_pin_fF=ctrl*fp[ASR]['SETN']['cap_fF'],
            vector_select_69_NAND_input_fF=69*max(fp[NAND]['A']['cap_fF'],fp[NAND]['B']['cap_fF']),
            bounded_BUF_leaf_clock_load_fF=8*max(fp[HQ]['CLK']['cap_fF'],fp[ASR]['CLK']['cap_fF'])+5.76,
            bounded_BUF_leaf_select_load_fF=8*max(fp[NAND]['A']['cap_fF'],fp[NAND]['B']['cap_fF'])+5.76,
            wire_cap_budget_fF=5.76,wire_budget_is_obligation_not_measured=True)
        if loads[corner]['bounded_BUF_leaf_select_load_fF']>fp[BUF]['Y']['max_cap_fF']: raise ValueError('driver maxcap')
    # Exact bit-cell body: FF+restoreINV+3 NAND feedback, standard0.27umrow.
    bit_width=sum(f[n]['SS']['size_um'][0]*count for n,count in [(HQ,1),(INV,1),(NAND,3)])
    raw_slots=[]
    for shard in (0,1):
        seats=sum(d[shard*64:(shard+1)*64]); width=69*bit_width; height=seats*0.54
        raw_slots.append(dict(shard=shard,root_count=64,seats=seats,width_um=width,height_um=height,
                              allocated_um2=width*height,body_utilization=0.5,
                              fixed_record_bit_row_height_um=0.27,empty_routing_row_height_um=0.27,
                              scalar_mux_control_clock_reset_not_inside_this_raw_slot=True,
                              orientation='R0 on separated source rows; actual PG rail phase UNBOUND',
                              physical_home_accepted_by_Maxwell=False))
    return dict(schema=1,verdict='ALLOWED_CELL_CONSTRUCTION_PRICED_NOT_FULL_IMPLEMENTATION',
        prerequisite_capture_commit='ef6da37de6f6c641936615f61825628c2db7b8d4',all768_identical_row_to_root=True,
        row_to_root='(row %256)//2',physical_variant='exact576 FF seats; no640padding selected',
        source_cell_facts=f,source_DONT_USE_patterns=policy,cell_counts_by_section=sections,
        total_cell_counts=dict(total),SETN_TIEHI_cells=ctrl,SETN_TIEHI_LEF_area_um2=tie_area,
        cell_body_area_by_section_um2=section_area,subtotal_body_area_um2=area,
        subtotal_core_reservation_at50pct_um2=2*area,
        subtotal_core_reservation_at50pct_mm2=2*area/1e6,
        control_boolean_obligations=dict(reserve='!active &source_drained &wire_drained &input_visible &VM_exclusive &metadata_valid &provider_fenced',release='source_idle &all_seen &all_banks_empty &delivery_fence &causal_visible &provenance &lease_valid',sticky_fault='old_fault |bad_owner |bad_row |duplicate |overflow |unexpected_return |fault_terminal'),
        reset=dict(record_reset=False,control_async_RESETN=True,control_SETN_tied_high=True,
                   HQ_QN_restored_with_INV=True,ASR_QN_restored_with_INV=True,
                   shared_old_source_and_wire_debt_fence_before_rearm=True),
        fanout_loads=loads,fanout8_tree=dict(clock=tree(record_bits+ctrl),reset=tree(ctrl),
                    owner_active=tree(128),per_vector_select=tree(69)),
        mux=dict(one_scalar_port=True,nodes=read_nodes,bits=69,maximum_mux_levels=10,
                 maximum_series_NAND_levels=20,one_edge_timing_qualified=False,
                 no_pipeline_selected=True,conditional_added_read_edges=None),
        raw_record_slot_templates=raw_slots,
        full_slot_completion=False,source_clock_reset_PG_ingress=None,
        control_bits=dict(prior_ef6=1468,selected_bank_ID=7,sticky_fault=2,causal_fence_latches=6,total=ctrl),
        remaining_provider_boundaries=['command/source/wire rearm causal fence provider','512bit VM bridge/formatter ownership and commit','128 raw writer and scalar drain route geometry'],
        local_control_cell_counts_are_construction_budget_not_HDL_equivalence=True,
        arithmetic_and_hardware_admitted=False,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
        frequency_GHz=1.2,additional_clock_skew_ps=25,
        slot_and_provider_deadline_from_Hubble=None,missing_deadline_is_not_zero=True,
        timeout1024_failure_preserved=True,timeout4096_selected=False,new_RTL_or_build=False)

def pinned():
    ps=[Path(__file__),ROOT/'tools/dsrom_I66_capture_banks.py',B.OUT/'model.json']+sorted((OUT/'inputs').glob('*'))
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ps}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args()
    m=model();m['source_pins']=pinned();raw=(json.dumps(m,indent=2,sort_keys=True)+'\n').encode()
    if a.verify:
        if a.out.read_bytes()!=raw: raise SystemExit('FAIL source/cell model mismatch')
        print('PASS byteexact allowed-cell model')
    else:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(raw)
