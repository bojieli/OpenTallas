"""Finite programme/store and operation-range audit; no RTL adoption."""
import argparse,hashlib,json,re
from pathlib import Path
from collections import defaultdict

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def model(metadata,composition,calendar,certificate,source_paths):
    words=metadata['programme']['words'];pw=words*16
    by=defaultdict(list)
    for index,event in enumerate(composition['events']):
        label=event['label'];family=label.split(':')[0] if ':' in label else label.split()[0]
        if family=='SEG':family='SEG_'+label.split()[-1]
        by[family].append((index,event))
    ranges=[]
    for family,events in by.items():
        indices=[i for i,_ in events];first,last=min(indices),max(indices)
        actual_first=calendar['ranges']['decode']['first']+first
        runs=[]
        for i,_ in events:
            if not runs or i!=runs[-1][-1]+1:runs.append([i])
            else:runs[-1].append(i)
        ranges.append(dict(id=family,events=len(events),first=actual_first,count=last-first+1,
          source_indices=indices,first_w5=events[0][1]['edge_w5'],last_w5=events[-1][1]['edge_w5'],
          interleaved_other_commands=(last-first+1)-len(events),
          contiguous_runs=[dict(first=calendar['ranges']['decode']['first']+r[0],count=len(r)) for r in runs],
          source_range_first_aligned=actual_first%4==0,
          producer_source_id=digest(source_paths['composition']),user_stage_bindings=[
            dict(user=u,stage=s,source_family=family,first=actual_first,count=last-first+1,
              first_w5=events[0][1]['edge_w5'],last_w5=events[-1][1]['edge_w5'],
              production_start=None,production_phase=None) for s in range(1,37) for u in range(4)]))
    starts={x['pcs'][0]:x['start'] for x in composition['composition']['stages'] if x['pcs']}
    # Use actual operation identity, not the combined norm/QKV first PC alias.
    target={1:next(x['start'] for x in composition['composition']['stages'] if x['pcs']==[1]),
            11:next(x['start'] for x in composition['composition']['stages'] if x['pcs']==[11]),
            12:next(x['start'] for x in composition['composition']['stages'] if x['pcs']==[12,13]),
            16:next(x['start'] for x in composition['composition']['stages'] if x['pcs']==[16]),
            20:next(x['start'] for x in composition['composition']['stages'] if x['pcs']==[20,21])}
    aligned_count=0;aligned_ranges=[];previous_edge=0
    for family,events in by.items():
        pad=(-aligned_count)%4
        aligned_ranges.append(dict(id=family,first=calendar['ranges']['decode']['first']+aligned_count+pad,
          count=len(events),pad_entries=pad,
          first_delta_after_padding=events[0][1]['edge_w5']-previous_edge-pad,
          first_w5=events[0][1]['edge_w5'],last_w5=events[-1][1]['edge_w5']))
        aligned_count+=pad+len(events);previous_edge=events[-1][1]['edge_w5']
    # Repack only counts to quantify capacity; no phase/production image emitted.
    n=calendar['ranges']['decode']['first']+aligned_count
    for key in ('head','boot','init'):
        n=(n+3)&~3;n+=calendar['ranges'][key]['count']
    new_init=(calendar['ranges']['decode']['first']+aligned_count+3)&~3
    new_init+=calendar['ranges']['head']['count'];new_init=(new_init+3)&~3
    new_init+=calendar['ranges']['boot']['count'];new_init=(new_init+3)&~3
    for _ in range(36):n=(n+3)&~3;n+=1
    mismatch=[]
    for r in metadata['me_rows']:
        pc=r['pc']
        if pc in target:
            original=r['cycle']+metadata['constants']['HEAD0']
            mismatch.append(dict(pc=pc,original_metadata_edge=original,
              dv_composed_target=target[pc],difference=target[pc]-original))
    producers=defaultdict(set)
    for case in certificate['cases']:
        for p in case['producers']:producers[(case['user'],case['epoch'])].add(p['instruction'])
    compact=[dict(user=u,epoch=e,actual_compact_producer_ids=sorted(ids)) for (u,e),ids in producers.items()]
    root=Path(__file__).resolve().parents[2]
    macro_geometry={}
    for label,rel,count in (
      ('existing_programme_SRAM','physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.lef',2),
      ('immutable_template_ROM','physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.lef',4)):
        p=root/rel;raw=p.read_bytes();width,height=map(float,re.search(rb'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',raw).groups())
        macro_geometry[label]=dict(count=count,size_um=[width,height],raw_area_um2=count*width*height,source_sha256=hashlib.sha256(raw).hexdigest(),physical_fit=False)
    return dict(schema='opentallas.qwen.programme-integration-options.v1',production_bound=False,
      sources={k:dict(path=str(v),sha256=digest(v)) for k,v in source_paths.items()},
      macro_geometry=macro_geometry,
      current_store=dict(instruction_bits=1024,programme_words=words,metadata_pw=pw,
        data_pw_ceiling=976,physical_pw=1024,physical_instruction_rows=64,
        fixed_me_rows=8,fixed_xpf_records=4,read_ports=1,write_bits_per_edge=64,
        current_user_snapshots='hu2 at LOCAL SEG; exposed native_pos[17:16]',
        existing_rom_relocator='code/scale bases only; no user Xbase modification',
        fixed_issue_arm='q_h_start && q_prog_base==0',
        xpf_arm='monitor_start[48] && monitor_start[11:0]==0',
        xpf_lifetime='one active stage until stop_cycle; overlapping start faults'),
      options=[
        dict(id='four-existing-PW-templates',programme_words=4*words,
          required_metadata_pw=4*pw,available_data_pw=976,deficit_pw=4*pw-976,
          fit=False,blockers=['all four templates cannot fit','nonzero base does not arm fixed ME/XPF schedules']),
        dict(id='immutable-four-template-store',logical_instruction_rows=4*words,
          logical_instruction_bits=4*words*1024,native_roms_4096x266=4,
          physical_rom_bits=4*4096*266,read_bits_per_edge=1064,
          proposed_read_age_edges=2,read_age_qualified=False,
          required_user_selection='held user or source-certified programme base',
          blockers=['actual per-user selector/home unbound','nonzero base and single-active ME/XPF semantics remain']),
        dict(id='canonical-template-plus-held-user',canonical_programme_words=words,
          canonical_metadata_pw=pw,changed_ME_words=4,changed_XPF_records=4,
          user_stride=65536,canonical_bases=dict(qkv=4096,o=16384,gu=4096,down=32768,head=8192),
          address_function='canonical_base | (user2<<16), only after exact canonical base qualification',
          arithmetic_adder_required=False,candidate_extra_user_state_bits=4,
          existing_user_context='hu already held at head starts; XPF capture/lifetime not yet proven',
          external_wide_API_required=False,RTL_implemented=False,
          blockers=['snapshot publication/retirement must cover all ME/XPF uses',
                    'actual phase/path/fanout native evidence absent','single-active schedule must be recut per group'])
      ],
      address_certificate=dict(cases=certificate['case_count'],arithmetic_bits_changed=False,
        source_manifest_sha256=certificate['source']['table_manifest_sha256']),
      operation_ranges=ranges,compact_producer_ids=compact,ME_timing_mismatches=mismatch,
      aligned_operation_candidate=dict(decode_entries=aligned_count,ranges=aligned_ranges,
        full_capsule_entries=n,spare_entries=1023-n,INIT_FIRST=new_init,
        production_emitted=False,production_bound=False,
        min_first_delta=min(r['first_delta_after_padding'] for r in aligned_ranges)),
      clone24_model={k:v for k,v in certificate['clone24_model'].items() if k!='proofs'},
      XPF_compact_identity_collision=dict(qkv_producer=3,gu_producer=3,producer_unit=2,
        good_checker_rejects_duplicate=True,runtime_each_matchingPC_checked=True,
        candidate_clone=24,candidate_head_local_reservation=[12,23],adopted=False),
      producer_observation=dict(filler_users_observed=False,
        source='qfd_tt_ctlm_dv_lpf_parts.sv su_obs requires c_su&&c_u0',
        actual_qkv_and_gu_events_per_group=12,events_are_slice_targeted=True,
        XPF_any_matching_PC_at_other_cycle_faults=True,
        clone24_resolves_only_record_identity=True,production_witness_bound=False),
      axis=dict(source_events='lowerer W5 pins',raw_calendar_vehicle='same offsets played at cal output',
        conversion='must rederive declared cal-start plus command landing ages; no production conversion assumed',
        source_R_CMD=metadata['relay']['R_CMD'],source_CAL_S=metadata['constants']['CAL_S'],
        first_source_W5_event=composition['events'][0]['edge_w5'],
        nominal_first_cal_T=composition['events'][0]['edge_w5']-metadata['relay']['R_CMD']-metadata['constants']['CAL_S'],
        calendar_ROM_worst_filler_min_first_T=8,
        nominal_old_axis_qualifies=composition['events'][0]['edge_w5']-metadata['relay']['R_CMD']-metadata['constants']['CAL_S']>=8),
      F16_compatibility=dict(qualified=False,public_period=8053632,INIT=calendar['ranges']['init'],
        public_fixture_FIRST=52,actual_capsule_FIRST=calendar['ranges']['init']['first'],
        reasons=['actual family command ranges are not public cap0 op ranges',
          'ME/XPF source timing differs from composed406 timeline','global producerPCs need compact per-user IDs',
          'shared resource lifetimes and source/consumer phases unbound','public actual L/head/provider images absent']))
def main():
    ap=argparse.ArgumentParser()
    for n in ('metadata','composition','calendar','certificate','out'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args();paths={k:getattr(a,k) for k in ('metadata','composition','calendar','certificate')}
    d={k:json.loads(v.read_text()) for k,v in paths.items()}
    out=model(**d,source_paths=paths);a.out.write_text(json.dumps(out,indent=2)+'\n')
    print('PROGRAMME_FINITE_MODEL',len(out['operation_ranges']),'families',sum(r['events'] for r in out['operation_ranges']),'events')
if __name__=='__main__':main()
