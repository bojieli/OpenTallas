#!/usr/bin/env python3
"""Extract the actual full-width decoder costs, retaining physical negatives."""
import collections,gzip,json,math,re
from pathlib import Path
from dsrom_secded_fullwidth_characterize import OUT,merged,input_pins,block,sha
def build():
    base=OUT/'terminal_r3';r=json.loads((base/'record.json').read_text());corners={c:merged(c)[1] for c in ('ss','ff')};rows=[]
    if r['status']!='CHARACTERIZED_COMBINATIONAL_ONLY':raise ValueError('failed or absent characterization')
    for k,replicas,allowance in [(256,412,.7996465152),(272,256,.5279219712)]:
        v=r['results'][str(k)];n=json.loads(gzip.decompress((base/f'K{k}/mapped.json.gz').read_bytes()))['modules']['ot_rom_secded_dec'];loads={};pins=collections.Counter();drivers={}
        for cellname,cell in n['cells'].items():
            ins=input_pins(corners['ss'][cell['type']])
            for pin,bits in cell['connections'].items():
                for bit in bits:
                    if pin not in ins:drivers[bit]=cellname+'/'+pin;continue
                    pins[bit]+=1
                    for c in ('ss','ff'):
                        body=corners[c][cell['type']];p=re.search(r'\bpin\s*\('+re.escape(pin)+r'\)',body)
                        cap=float(re.search(r'\bcapacitance\s*:\s*([\d.]+)',block(body,p.start()))[1]);loads.setdefault(c,collections.Counter())[bit]+=cap
        b,count=pins.most_common(1)[0];maxload={c:max(loads[c].values()) for c in loads}
        ss=max(x for x in v['ss']['data_arrival_ps'] if x>=0);ffmin=min(x for x in v['ff']['data_arrival_ps'] if x>=0)
        area=replicas*v['area_um2']/1e6
        rows.append(dict(K=k,N=k+10,R=9,replicas_per_die=replicas,mapped_cells_per_instance=sum(v['cell_counts'].values()),mapped_area_um2_per_instance=v['area_um2'],mapped_cell_area_mm2_all_replicas=area,existing_allowance_mm2=allowance,retained_budget_mm2=max(area,allowance),area_credit_claimed_mm2=0,source_state_bits=0,source_pipeline_cycles=0,
          SS_max_delay_ps=ss,FF_min_delay_ps=ffmin,SS_virtual_setup_slack_ps=min(v['ss']['virtual_slack_ps'][:3]),FF_virtual_min_hold_slack_ps=min(v['ff']['virtual_slack_ps'][3:]),
          corner_output_capture_D_load_fF={c:v[c]['output_load_fF'] for c in ('ss','ff')},max_internal_sink_pins=count,max_internal_pin_cap_fF=maxload,max_fanout_driver=drivers[b],
          SS_path_library_limit_exceeded='(VIOLATED)' in gzip.decompress((base/f'K{k}/ss.log.gz').read_bytes()).decode().split('max slew')[-1],
          provisional_two_cycle_decoder_budget_cycles=2,exceeds_two_times_setup_logic_window=ss>2*(833.333333-60),
          period_equivalent_only_diagnostic=math.ceil(ss/(833.333333-60)),diagnostic_is_not_certified_pipeline_minimum=True,
          required_next='source-defined syndrome/overall/fix/data+fault aligned pipeline cuts and local fanout buffer model; measured capture CQ/setup, actual enabled/header and PG/OBS/route/clock context before hardening',
          warnings_on_unused_cells_only=['FAx1_ASAP7_75t_R','HAxp5_ASAP7_75t_R']))
    # Prospective implementation options, not automatic adoption or new RTL.
    # Group16 bounds syndrome/overall correction fanout structurally; every
    # payload/header/fault edge is charged. Timing of each cut remains a gate.
    opt=[]
    for k,replicas in ((256,412),(272,256)):
        g=math.ceil(k/16);bits=4*k+11*g+4+3*58
        opt.append(dict(K=k,replicas=replicas,correction_groups=g,
          stage1='balanced source syndrome9 and overall, replicated10bits/group; retained payloadK and identity58',
          stage2='source fix[K] plus replicated overall/group and corrected/uncorrectable; delayed payloadK and identity58',
          stage3='source data[K] XOR gated fix plus same two flags; identity58 and terminal valid',
          state_bits_per_instance=bits,state_bits_all_replicas=bits*replicas,
          assigned_cycles_diagnostic=3,assigned_II_diagnostic=1,timing_bound=False,
          semantics='Boolean source functions and bit order unchanged; metadata accompanies every cut; fault suppresses arithmetic and read debt drains. Requires actual RTL exact proof before adoption.'))
    bits=sum(v['state_bits_all_replicas'] for v in opt)
    prior_decoder_reference_bits=412*2*(256+2+58)+256*2*(272+2+58)
    new_overlay_bits=999360-prior_decoder_reference_bits+bits
    options=dict(
      held_multicycle=dict(raw_cycles_diagnostic=4,main_cycles_diagnostic=3,raw_II_if_single_held_seat=4,main_II_if_single_held_seat=3,
        added_decoder_path_cycles_vs_provisional2plus2=3,
        required_contract='Hold exact accepted cw and identity until captured good/fault terminal; prohibit CE/address/slot overwrite, retain reverse credit and cancel debt. Main282 assembled only after matching main274 plus8side checks. No existing scheduler hold guarantee bound.',
        admission=False,reason='period equivalents use out-of-range unbuffered LUT delay and omit capture CQ/setup/wire/skew; not a certified multicycle timing exception'),
      registered_balanced=dict(entries=opt,total_added_reference_state_bits=bits,FF_cell_area_only_mm2=bits*.2916/1e6,
        conservative_FF50_proxy_mm2=bits*7.5816e-7,
        replacement_scope='Replace ONLY Maxwell two decoder-output stage reservations; keep all capture/gather/main-assembly reservations and all existing decoder logic floors.',
        Maxwell_prior_full_pipeline_overlay_bits=999360,prior_decoder_reference_bits=prior_decoder_reference_bits,
        new_full_pipeline_overlay_bits=new_overlay_bits,new_full_pipeline_overlay_FF50_mm2=new_overlay_bits*7.5816e-7,
        conservative_screen_with_replacement_overlay_mm2=732.9650770579258+new_overlay_bits*7.5816e-7,
        extra_decoder_path_cycles_vs_provisional2plus2=2,
        raw_credit_pipeline_min_if_II1_and3cycles=3,finite_seats_and_tags_need_source_owner_binding=True,
        admission=False,remaining='Source opt-in frozen implementation and Boolean/RTL exactness; per-cut SS/FF/load/buffer/clock/PG/OBS/wire; source finite producer acceptance and consumer deadlines. No assumed II1 guarantee or route-free slot.'))
    return dict(schema='opentallas.dsrom.secded.characterization-review.v1',candidate=r['model']['candidate'],source_decoder_sha256=r['model']['decoder_source_sha256'],mapping_source_commit='347beb640',timing_source_commit=r['source_commit'],Maxwell_admission_commit='28913b8882d9dc9f712d7fc1035e6c10d86dd6a6',terminal_record_sha256=sha(base/'record.json'),rows=rows,prospective_options=options,
      status='MEASUREMENT_COMPLETE_UNPIPELINED_SS_SCREEN_FAIL_PHYSICAL_OPEN',all_ports_dynamic_fullwidth=True,
      mapped_total_decoder_cell_area_mm2=sum(x['mapped_cell_area_mm2_all_replicas'] for x in rows),retained_decoder_allowance_mm2=sum(x['retained_budget_mm2'] for x in rows),
      area_scope='cell-area lower bound only; existing named floors retained, no PG/control/clock/wire or collector containment credit',
      timing_scope='20ps input transition, one actual corner D-pin on every output, ideal wires; library limit extrapolation is present. Virtual FF min is not registered/contextual hold.',
      numerical_scope='unchanged complete RTL mapped; no new arithmetic or executed RTL/golden-token qualification',SS_registered_capture_closed=False,FF_registered_hold_closed=False,PG_via_OBS_clock_bound=False,new_engine_RTL=False,PR_launched=False,fleet_jobs_owned=0,
      calendar_scope='positive two-cycle price is provisional and insufficient for these unbuffered paths; owner must price validated cuts/delivery. No full-token dependency was used as a characterization gate.',
      next_user_requested_characterization='Existing syndrome+overall parity detector only, separate from full correction selector. Full-cone measurements are not normal fast-check latency. No error-frequency assumption, no unvalidated irreversible consume.')
if __name__=='__main__':
    out=OUT/'review.json';data=(json.dumps(build(),indent=2,sort_keys=True)+'\n').encode()
    if out.exists() and out.read_bytes()!=data:raise ValueError('retain prior record; fresh successor required')
    out.write_bytes(data);print(data.decode())
