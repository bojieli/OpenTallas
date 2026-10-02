#!/usr/bin/env python3
"""Price one source-caused control repair; no source/constraint/P&R mutation."""
import argparse,gzip,hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/uarch/qwen_rom_control_closure_cause_20261002'

def area(cell,file):
    s=gzip.decompress((OUT/'inputs'/file).read_bytes()).decode()
    m=re.search(r'cell\s*\(\s*'+re.escape(cell)+r'\s*\)\s*\{.*?area\s*:\s*([\d.]+)',s,re.S)
    if not m:raise ValueError('cell absent')
    return float(m[1])

def blocks(text, kind):
    for m in re.finditer(r'\b'+kind+r'\s*\(([^)]*)\)\s*\{',text):
        depth=1;j=m.end()
        while depth and j<len(text):
            depth += (text[j]=='{')-(text[j]=='}');j+=1
        if depth:raise ValueError('unbalanced library')
        yield m[1].strip(),text[m.end():j-1]

def cell_pin(file,cell,pin):
    text=gzip.decompress((OUT/'inputs'/file).read_bytes()).decode()
    body=next(b for n,b in blocks(text,'cell') if n==cell)
    return next(b for n,b in blocks(body,'pin') if n==pin)

def capacitance(file,cell,pin):
    return float(re.search(r'\bcapacitance\s*:\s*([\d.]+)',cell_pin(file,cell,pin))[1])

def lookup(table,x,y):
    axes=[list(map(float,re.search(r'index_'+str(i)+r'\s*\("([^"]+)"',table)[1].split(','))) for i in (1,2)]
    vals=re.search(r'values\s*\((.*?)\);',table,re.S)[1]
    rows=[list(map(float,r.split(','))) for r in re.findall(r'"([^"]+)"',vals)]
    if len(rows)!=len(axes[0]) or any(len(r)!=len(axes[1]) for r in rows):raise ValueError('bad table')
    def bracket(a,v):
        if not a[0]<=v<=a[-1]:raise ValueError('no extrapolated library claims')
        k=next((k for k in range(len(a)-1) if v<=a[k+1]),len(a)-2)
        return k,(v-a[k])/(a[k+1]-a[k])
    i,fx=bracket(axes[0],x);j,fy=bracket(axes[1],y)
    return sum(rows[i+di][j+dj]*wx*wy for di,wx in enumerate((1-fx,fx)) for dj,wy in enumerate((1-fy,fy)))

def propagation(corner, reverse=False):
    inv='invbuf_'+corner+'.lib.gz';simple='simple_'+corner+'.lib.gz';seq='seq_'+corner+'.lib.gz';ao='ao_'+corner+'.lib.gz'
    B='BUFx4_ASAP7_75t_R';F='DFFASRHQNx1_ASAP7_75t_R';N='NOR2xp33_ASAP7_75t_R';A='AO21x1_ASAP7_75t_R'
    bc=capacitance(inv,B,'A');nc=capacitance(simple,N,'A');ac=capacitance(ao,A,'B');dc=capacitance(seq,F,'D')
    # Explicit wire-cap scenario, not extracted geometry. No extrapolation.
    stages=[(seq,F,'QN','CLK',3*bc+1,'rise'),(inv,B,'Y','A',6*nc+1,'rise'),
            (simple,N,'Y','A',2*bc+1,'fall'),(inv,B,'Y','A',8*ac+1,'fall'),
            (ao,A,'Y','B',dc+1,'fall')]
    if reverse:stages=[(f,c,p,r,l,'fall' if e=='rise' else 'rise') for f,c,p,r,l,e in stages]
    slew=20.;result=[]
    for file,c,p,related,load,edge in stages:
        pin=cell_pin(file,c,p)
        ts=[b for _,b in blocks(pin,'timing') if re.search(r'related_pin\s*:\s*"'+related+'"',b)]
        if c==F:ts=[b for b in ts if 'rising_edge' in b]
        t=ts[0];tables={k:list(blocks(t,k))[0][1] for k in ('cell_'+edge,edge+'_transition')}
        delay=lookup(tables['cell_'+edge],slew,load);out=lookup(tables[edge+'_transition'],slew,load)
        limit=float(re.search(r'max_capacitance\s*:\s*([\d.]+)',pin)[1])
        result.append(dict(cell=c,related_pin=related,edge=edge,input_slew_ps=slew,load_fF=load,
            delay_ps=delay,output_slew_ps=out,max_capacitance_fF=limit,within_cap=load<=limit,within_slew=out<=320))
        slew=out
    return dict(stages=result,cell_path_ps=sum(r['delay_ps'] for r in result),
        assumed_clock_slew_ps=20,wire_cap_scenario_fF_per_net=1,
        period_minus_uncertainty_minus_cells_ps=833.3333333333334-60-sum(r['delay_ps'] for r in result),
        characterization=False,actual_wire_and_clock_skew_unknown=True)

def build():
    m=json.loads((OUT/'inputs/loaded_failure.json').read_text());old=json.loads((OUT/'inputs/prior_control_model.json').read_text())
    if m['status']!='BLOCKED_MAPPED_TIMING_OR_LIMITS' or m['unique_local_selector_bits']!=80:raise ValueError('wrong source failure')
    ss=gzip.decompress((OUT/'inputs/ss_all.log.gz').read_bytes()).decode();ff=gzip.decompress((OUT/'inputs/ff_all.log.gz').read_bytes()).decode()
    if 'Startpoint: rst_n' not in ff or 'removal check' not in ff or 'Startpoint: wrom_addr[0]' not in ff:raise ValueError('input/reset failure identity')
    src=(OUT/'inputs/matvec_source.sv').read_text()
    if 'output reg               wrom_re' not in src or 'wrom_addr <= cur;' not in src:raise ValueError('actual provider registers')
    buf=area('BUFx4_ASAP7_75t_R','invbuf_ss.lib.gz');reset_ff=area('DFFASRHQNx1_ASAP7_75t_R','seq_ss.lib.gz')
    # One fixed source-compatible candidate. Replicas sample identical wrom_re
    # on same edge; each bank uses its local prior-cycle read strobe.
    counts=dict(bank_strobe_output_buffers=5*3,bank_hold_select_output_buffers=5*2,
        reset_root_mid_leaf_buffers=1+2+12,low_address_root_leaf_buffers=12*(1+2))
    extraFF=4;cells=extraFF*reset_ff+sum(counts.values())*buf
    # Positive clear-wire/PG and occupancy policy; no claims of track availability.
    corridor=.25*cells;slot=(cells+corridor)/.5
    timings={(r['corner'],r['scope']):r for r in m['timings']}
    return dict(schema='opentallas.qwen-rom.control-cause-closure.v1',
        failure_commit='f28f30496d5489a76b90c3bc45fc479e4fcc5881',failure_unchanged=True,
        input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((OUT/'inputs').iterdir()) if p.is_file()},
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        analytical_loaded_arcs={c+'_'+edge:propagation(c,edge=='reverse') for c in ('ss','ff') for edge in ('forward','reverse')},
        cause=dict(SS_full_slack_ps=timings['ss','all']['slack_ps'],FF_full_slack_ps=timings['ff','all']['slack_ps'],
            SS_path='code_rd_q DFF QN -> shared bank NOR2 ->16holdmux AO21 ->local selector DFF',
            root_fanout=85,SSroot_cap_fF=43.032887,SSroot_slew_ps=618.009888,sink_slew_limit_ps=320,
            bank_select_net_fanout=16,bank_select_net_SS_cap_fF=8.466255,
            FF_root_cap_fF_rounded=51.73,root_cap_limit_fF=46.08,
            FF_worst='rst_n externalzero arrival ->RESETN removal; not macro data hold',
            reset_min_arrival_plus_distribution_minus_capture_skew_required_ps=50.049297,
            low_ROM_address_min_arrival_plus_distribution_minus_capture_skew_required_ps=42.422199,
            zero_input_delay_in_failed_screen_not_actual_source_arrival=True),
        fixed_candidate=dict(id='QROM_HOLD_DIRECT_CAPTURE_BANK5_CONTROL',off_by_default=True,
            strobe_FFs_before=1,strobe_FFs_after=5,new_FFs=4,total_metadata_FFs_after=90,
            local_mask_FFs=80,ROM_macros=10,bank_strobe_sink_bound=17,
            strobe_driver_load_plan='Each localstrobe Q drives3BUFx4 inputs; each buffer drives <=6 of17 bank-local NOR inputs. Includes the bank term and16hold feedback controls.',
            bank_hold_term_plan='Each of5 existing16load NOR outputs drives2BUFx4 inputs; each drives <=8AO21 pins.',
            buffer_counts=counts,total_added_buffers=sum(counts.values()),
            reset_plan='One declared root/two middle/twelve leaf buffers to90 metadataRESETN pins, <=8leaf sinks; upstream reset assertion/release phase must be bound, no arbitrary arrival waiver.',
            address_plan='Each12lowaddr bit gets root+2leaf buffers driving10macro address pins plus measured-port allowance11; source registered matvec arrival must be included.',
            semantic_proof_required='Every bankstrobe samples samewrom_re on sameclk/reset as oldcode_rd_q. Prove all5 copies equivalent and unchanged80 masks/512sampled outputs before mappedsource repair.',
            clock_and_reset_pins_added=4,data_path_capture_FFs_unchanged=True,new_token_cycles=0,
            no_added_cycle_is_conditional_on_actual_SSFF_arrival_and_cause_closure=True,
            original_MEM_EXTRA1_charged_once=True,RTL_implemented=False),
        cost=dict(async_reset_FF_cell_um2=reset_ff,BUF_cell_um2=buf,
            new_control_cell_area_um2=cells,positive_clear_wire_PG_policy_um2=corridor,
            incremental_control_slot_um2=slot,incremental_die_slot_mm2=slot*1536/1e6,
            mapped_failed_logic_and_existing_endpoint_um2=m['mapped_logic_area_um2_including_existing_endpoint'],
            prior645_control_wire_clock_buffer_allowance_not_subtracted=True,
            new_reservation_is_overlay_not_doublecount_claim_or_measured_slot=True,
            root_clock_tree_load_and_skew_unmeasured=True),
        contextual_constraints=dict(SS_period_ps=833.3333333333334,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
            reset='A_reset_min + Dreset_FF_min - clock_skew >=50.049297; A_reset_max +Dreset_SS_max +recovery+60 <=T. Unknown async phase cannot be assumed clockedge0.',
            address='Aaddr_min+Daddr_FF_min-clock_skew >=42.422199; Aaddr_max+Daddr_SS_max+macro_setup+60 <=T.',
            internal_control='Source loaded SS root +local buffers+NOR+AO+wire+FFsetup+relativeCTSskew <=T-60. Source FF min also meets hold25; report every branch maxcap/slew.',
            actual_parent_provider='rtl/hdc/ot_qwen_w12_matvec.sv outputs registered wrom_re/wrom_addr; map their actual CLKQ/loads and parentclock to tile arrivals, not a substitute set_input_delay.',
            actual_reset_owner_and_release_phase_still_needed=True,actual_pin_OBS_PG_slot_still_needed=True),
        retained_separate_paths=dict(macro_SS_slack_ps=timings['ss','macro']['slack_ps'],merge_SS_slack_ps=timings['ss','merge']['slack_ps'],merge_FF_slack_ps=timings['ff','merge']['slack_ps'],
            macro_ideal_margin_is_not_wire_CTS_closure=True,macro_capture_added_stage_not_selected=True,
            if_macro_wire_skew_exceeds_margin='Reject currentcapture; explicitlyprice changed capture+all metadata/operandalignment in sameprogram before another sourcebuild. IntegerMEM_EXTRA2 alone doesnot add second capture.'),
        admission=dict(priced_cause_model_ready=True,
            source_repair_preparation='Euclid may prepare this one defaultoff bank5 candidate afterreview; exact sameedge proof plus source-cell loaded propagation bounds and provider arrival/reset receipts precede characterization.',
            new_characterization_requires_actual_provider_reset_and_sameedge_proof=True,
            mapped_or_contextual_SSFF_closed=False,tile_PR=False,hardware_adoption=False,new_job=False),
        sameprogram_reference=old['latency']['exact_same_program_55_reference'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('fresh record required')
    a.output.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
