"""S81 source address -> W11 masked bank-row/port admission model.

Metadata only, no tensor/checkpoint payload, allocator replay, RTL or jobs.
The native 4-bank provider and W11 VM are separate physical layouts.
"""
from pathlib import Path
from collections import Counter,defaultdict
import gzip,hashlib,json,math,re
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_s81_native_vm_ports_20261004'
CANON='results/uarch/dsrom_s81_released_binding_20261004/canonical/matrix_map.jsonl.gz'
DEMAND='results/uarch/dsrom_native_weight_address_join_20261002/inputs/demand-r5.json.gz'
BINDINGS='results/uarch/dsrom_native_weight_address_join_20261002/r3/node_bindings.jsonl.gz'


def home(address):
    if type(address)!=int or not 0<=address<1<<19:raise ValueError('actual expanded AW19 bounds')
    w=address>>7
    return dict(group=address&127,bank=(w>>3)&1,row=w>>4,column=w&7)


def bank4_home(address):
    home(address);word=address>>4
    return dict(bank=word&3,row=(word>>2)&511,group=word>>11,column=address&15)


def root_for(row):
    if type(row)!=int or not 0<=row<1<<16:raise ValueError('source row16')
    return (row>>1)&127


def write_edge(obase,ops,returns,other_writes=()):
    """Returns: [{root,row,pos}], one NOREADY row per root; all raw values opaque.

    Other writes carry source-order id/address. Later source writer wins a
    same-address NBA. Different-address row merging never drops a transaction.
    This models physical demand, not grant/ready or original retirement.
    """
    occupied=set();requests=[]
    for x in returns:
        r,row,pos=x['root'],x['row'],x['pos']
        if not 0<=r<128 or r in occupied or root_for(row)!=r or not 0<=pos<=7:
            raise ValueError('original root/row/pos and one return/root/edge')
        occupied.add(r);address=obase+row+pos*ops;h=home(address)
        requests.append(dict(id=('field',r,row,pos),address=address,**h))
    for x in other_writes:
        h=home(x['address']);requests.append(dict(id=x['id'],address=x['address'],**h))
    winners={x['address']:x['id'] for x in requests}
    rows=defaultdict(list);superseded=[]
    for x in requests:
        if winners[x['address']]!=x['id']:superseded.append(x['id']);continue
        rows[x['group'],x['bank'],x['row']].append(x)
    banks=Counter((g,b) for g,b,_ in rows)
    bank4_rows=defaultdict(set)
    for x in requests:
        h=bank4_home(x['address']);bank4_rows[h['bank']].add((h['group'],h['row']))
    return dict(masked_rows=[dict(group=g,bank=b,row=r,mask=sum(1<<x['column'] for x in xs),identities=[x['id'] for x in xs]) for (g,b,r),xs in sorted(rows.items())],
      distinct_rows_per_bank=[dict(group=g,bank=b,rows=n) for (g,b),n in sorted(banks.items())],
      W11_immediate_ports_PASS=all(n<=1 for n in banks.values()),
      source_superseded=superseded,field_visibility_refused=any(x[0]=='field' for x in superseded),
      bank4_distinct_words_per_bank={str(b):len(s) for b,s in bank4_rows.items()},
      bank4_one_word_port_PASS=all(len(s)<=1 for s in bank4_rows.values()))


def extent_reservation(obase,rows):
    """Exact distinct physical bank-row keys of one contiguous P1 phase.

    Reserving these empty slots BEFORE GO is sufficient storage independent
    of return skew only if ingress handles all rows, by-row coalescing is real,
    no competitors occupy these banks, and same-epoch rows merge without loss.
    Service/visibility/CDC and acceptance still need their real contracts.
    """
    if rows<1:raise ValueError('nonempty source phase')
    home(obase);home(obase+rows-1)
    reservation=[]
    for g in range(128):
        low=max(0,(obase-g+127)//128);high=(obase+rows-1-g)//128
        for b in range(2):
            first=max(0,(low-8*b-7+15)//16);last=min(255,(high-8*b)//16)
            n=max(0,last-first+1)
            if n:reservation.append(dict(group=g,bank=b,first_row=first,last_row=last,seats=n))
    return dict(base=obase,rows=rows,bank_row_reservations=reservation,
      max_seats_per_bank=max(x['seats'] for x in reservation),
      total_reserved_rows=sum(x['seats'] for x in reservation),
      priced_W11_depth4_storage_PASS=all(x['seats']<=4 for x in reservation),
      accepted_service_proven=False,physical_admission=False)


def census(owner):
    """ONE canonical metadata pass and existing demand binding, no new allocator.

    Does not enumerate tensor words/compute capacity/revalidate full-model
    assignment. Phase ordinal follows Popper's exact same file ordering.
    """
    owner=Path(owner);d=json.load(gzip.open(owner/DEMAND,'rt'));nodes={n['id']:n for n in d['nodes']}
    bs=[json.loads(line) for line in gzip.open(owner/BINDINGS,'rt')]
    calls=[b for b in bs if b['classification']=='WEIGHT_PHASE']
    phases=defaultdict(list);ordinal=Counter();matrix_count=0;max_rows=0
    for line in gzip.open(owner/CANON,'rt'):
        m=json.loads(line);stage=m['stage'];phase=ordinal[stage];ordinal[stage]+=1;matrix_count+=1
        max_rows=max(max_rows,m['rows'])
        phases[m['layer'],m.get('original_alias',m['alias'])].append(dict(stage=stage,phase=phase,alias=m['alias'],rows=m['rows'],offset=m.get('row_offset',0),format=m['format']))
    geometries={};by_call=[];misses=[];choices=0;wait_counts=Counter()
    for b in calls:
        n=nodes[b['node']];f=n['instruction'];wait_counts[f.get('wait',0)]+=1
        if f.get('mx_m',0)!=0 or f.get('mx_ops',0)!=0 or f.get('qe_d_obase',0) or f.get('me_d_obase',0):
            raise ValueError('cannot silently replace actual dynamic/MTP field addresses')
        if b['selector_slot'] is not None:
            suffix=b['alias'].split('.',1)[1];aliases=[f'exp{e}.{suffix}' for e in range(384)]
        else:aliases=[b['alias']]
        # Source binding base is expanded FP32-element address (ME*16 already).
        base=b['consumer_output_base_elements'];call_choices=0;worst=0;bad=[]
        for alias in aliases:
            ms=phases.get((b['layer'],alias))
            if not ms:misses.append(dict(node=b['node'],alias=alias));continue
            for m in ms:
                geometry=(base+m['offset'],m['rows'])
                if geometry not in geometries:geometries[geometry]=extent_reservation(*geometry)
                g=geometries[geometry];worst=max(worst,g['max_seats_per_bank']);choices+=1;call_choices+=1
                if not g['priced_W11_depth4_storage_PASS']:
                    bad.append(dict(alias=alias,stage=m['stage'],phase=m['phase'],base=geometry[0],rows=geometry[1],required_seats=g['max_seats_per_bank']))
        by_call.append(dict(node=b['node'],kind=b['kind'],output_base=base,selector_slot=b['selector_slot'],actual_mx_m=0,actual_ops=0,phase_choices=call_choices,
          max_bank_seats=worst,depth4_storage_PASS=worst<=4,native_admission_failures=b.get('native_admission_failures',[]),failures=bad,
          wait_mask=f.get('wait',0),wait_proves_all_engine_drained=f.get('wait',0)==31))
    return dict(canonical_matrices=matrix_count,max_fragment_rows=max_rows,calls=len(calls),QE_calls=sum(b['kind']=='QE' for b in calls),ME_calls=sum(b['kind']=='ME' for b in calls),
      actual_runtime_eids_observed=False,all_384_choices_symbolic=True,symbolic_phase_choice_instances=choices,
      geometries=len(geometries),geometry_profiles=[g for _,g in sorted(geometries.items())],call_profiles=by_call,missing_bindings=misses,
      field_wait_masks={str(k):v for k,v in sorted(wait_counts.items())},
      depth4_storage_PASS=not misses and all(g['priced_W11_depth4_storage_PASS'] for g in geometries.values()),
      native_unbound_head_preserved=sum(b['classification']=='UNBOUND_DEDICATED_HEAD' for b in bs),
      native_calls_with_admission_failures=sum(bool(b.get('native_admission_failures')) for b in calls),
      source_order_fullidle_wait_not_bank_grant=True,
      selected_fragment_program_END_wait31=True,
      no_fullprogram_or_traffic_claim=True)


def price(w11):
    """One prospective W11 reuse proposal, no sweep/adoption or installed claim."""
    C=w11['options']['C_rotate'];dens=w11['basis']['density'];f=dens['flop_um2'];c=dens['comb_cell_um2']
    # Existing1024-lane E rotate: source row%256 ensures different roots cannot
    # alias a lane, P1 uses a common obase rotation. Carry full actual identity.
    width=136;stages=C['su_op_class_stages']['element_write']
    added_ff=(width-32)*1024*stages;added_mux=(width-32)*1024*10
    #4-row planned bank queues: field membership per8columns + fullcontext57.
    owner_bits=128*2*4*(8+57);ack_bits=128*2*(8+8+57+1)
    reservation_bits=128*2*(8+8+1) # retained first/last row + owned-valid per bank
    owner_ack_bits=owner_bits+ack_bits+reservation_bits
    added_cell=(added_ff+owner_ack_bits)*f+added_mux*c
    return dict(existing_W11_SRAM_macros=1536,existing_W11_SRAM_mm2=C['sram']['mm2'],existing_W11_hub_mm2=C['geometry']['block_mm2'],
      existing_E_rotate_reuse=True,existing_E_rotate_paid_mm2=C['networks'][-1]['footprint_mm2'],
      proposed_packet_fields=dict(valid=1,error=1,root=7,row=16,pos=3,identity=47,phase=10,address=19,raw_data=32),packet_bits=width,
      root_fast_boundary_bits=128*width,root_fast_boundary_bytes_payload=512,
      required_slow_boundary_bits_4over3=math.ceil(128*width*4/3),
      current_priced_payload_only_slow_bits=5461,
      metadata_rotate_additional_mux_bits=added_mux,metadata_rotate_additional_FF_bits=added_ff,
      shadow_field_owner_bits=owner_bits,macro_commit_receipt_bits=ack_bits,preGO_bank_reservation_bits=reservation_bits,
      positive_added_cell_mm2_floor=added_cell/1e6,positive_added_placement_mm2_floor_at50pct=2*added_cell/1e6,
      added_macro_count=0,extra_buffer_depth_selected=False,
      mutable_codec_clock_reset_route_decode_and_gearbox_area_not_in_floor=True,
      prospective_write_route_slow_edges=stages,fast_to_slow_slow_edges=4,
      queued_to_macro_commit_slow_edges_min=1,registered_positive_commit_ack_slow_edges=1,
      reverse_slow_to_fast_fast_edges=5,
      emptyqueue_tail_min_ns=(4+stages+1+1)/.9+5/1.2,
      full_depth4_tail_bound_without_other_writers_ns=(4+stages+4+1)/.9+5/1.2,
      existing_ret_scatter_price_slow_edges=7,
      extra_delta_vs_old_ret_scatter_not_zero=True,
      source_ratio_FIFO_not_4over3_gearbox=True,
      worst_field_groups_inputs_per_fast_edge=2,slow_gearbox_worst_per_group_bank_inputs=4,
      existing_group_phys_K_default=2,existing_group_phys_WQD_default=8,priced_spec_queue_depth=4,
      proposal_selected_K=4,proposal_selected_WQD=4,
      comment='Port/ownership proposal only. Preserve all replicas and source write-order/read-old image. No existing FIFO width parameter alone guarantees4/3 bandwidth. Actual pack/CDC/calendar+loaded timing missing.',
      CAP1_literal_visibleACK_return_each_fast_edge_PASS=False,
      downstream_reserved_seat_handoff_required=True,
      matched_macro_receipt_context57_plus_bank_row8_mask8=True,
      ingress_credit_not_macro_visibility=True,
      source_registered_ack_CAN_NOT_be_timer_or_idle=True,
      per_layer_or_token_added_ns=None,
      background_drain_extra_GO_wait_ns=None,
      conditional_added_tail_over_old_ret_scatter_ns=(4+stages+4+1)/.9+5/1.2-7/.9,
      clock_source='W11 priced0.9GHz VM route/group service +1.2GHz field. Enclosing selected physical domain is not inferred from behavioral common clk; owner must confirm.',
      clocks_or_uncertainty_relaxed=False,setup_SS_ps=60,hold_FF_ps=25,physical_admission=False)


def build(owner,out):
    owner=Path(owner);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    w11=json.loads((BASE/'inputs/w11_vm_options.json').read_text());summary=census(owner)
    # Actual emitted native source conversion. Decode with full_shape=True.
    import hdc_isa_v41 as I
    prog=owner/'results/rtl/dsrom_s81_source_binding_20261004/native_conversion/s0_r0/prog.hex'
    f=I.decode(int(prog.read_text().splitlines()[0],16),full_shape=True)
    witness=write_edge(f['qe_obase'],0,[dict(root=r,row=2*r,pos=0) for r in range(128)])
    # A real source call, worst legal independent root skew from its extent.
    # Choose two different physical rows of the same group/bank when available;
    # no cycle assigned, so this is a legal-geometry witness, NOT measured order.
    skew=None
    for cp in summary['call_profiles']:
        for g in summary['geometry_profiles']:
            if g['base']!=cp['output_base'] or g['rows']<256:continue
            candidates=defaultdict(list)
            for row in range(g['rows']):
                h=home(g['base']+row);candidates[h['group'],h['bank']].append((h['row'],root_for(row),row))
            for (group,bank),rs in candidates.items():
                found=None
                for a in rs:
                    found=next((b for b in rs if a[0]!=b[0] and a[1]!=b[1]),None)
                    if found is not None:
                        ret=[dict(root=x[1],row=x[2],pos=0) for x in (a,found)]
                        skew=dict(node=cp['node'],base=g['base'],phase_rows=g['rows'],group=group,bank=bank,returns=ret,edge=write_edge(g['base'],0,ret),actual_accepted_edge=None)
                        break
                if skew:break
            if skew:break
        if skew:break
    paths=[CANON,DEMAND,BINDINGS,'tools/dsrom_stage_program_join.py','tools/dsrom_s81_capture_profile.py',
      'rtl/w17_runtime/chip/ot_chip_v41x_tile.sv','rtl/w17_runtime/hdc/v41x/ckvsel/ot_hdc_core_v41x.sv',
      'rtl/chip/ot_chip_v41_ratio_fifo.sv','rtl/model_ready_ds_native_vm_r2_20261003/ot_v41_vm_bank4_macro_pipe_masked_visible_r2.sv',
      str(prog.relative_to(owner)),'tools/uarch_model.py']
    pins={p:hashlib.sha256((owner/p).read_bytes()).hexdigest() for p in paths}
    pins['model_generator']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result=dict(schema='dsrom.s81.native_VM.physical_ports.v1',source_pins=pins,W11_origins=json.loads((BASE/'inputs/origins.json').read_text()),
      census=summary,emitted_program_witness=dict(node='L0.I7',stage=0,phase=0,rank=0,rows=320,obase=f['qe_obase'],actual_cycle=None,first_even_rows_geometry=witness),
      independent_root_skew_geometry_witness=skew,price=price(w11),
      verdict='CURRENT_CAP1_BEHAVIORAL_ACK_NOT_PHYSICAL_QUALIFICATION',
      proposal='Reserve exact perbank rows beforeGO; steer root into row%1024 lane, reuse global obase rotate, merge columns byphysical bankrow, use existing W11 masked-row queues with explicitlypriced full owner; ingress release only toreserved hardwareowned downstream seat; macrocommit receipt and reversecapturedcredit fencecontextretirement.',
      required_ownership='All relevant W11 bank queues initiallyempty plus atomic bank-row reservations; other writer GO suppressed or separately scheduled from actualheld hardwareowner. Source waitmask is not a bank reservation.',
      precise_blockers=['No actual selected physicalVM/clock provider binding','No sourceowned4:3 gearbox/CDC capture calendar (FIFO one-entry/edge != widening)','No current accepted fullphase/root cadence journal','No atomic otherwriter bank reservations/finite arbitration','CAP1 positive-visible ACK cannot return everyedge through a multi-stage path without separatelyreserved downstream seats','No fullsource/SSFF loaded mutableowner/ACK protection/area closure'],
      helper_RTL_written=False,allocator_replayed=False,hardware_job_launched=False,fulltoken_or_rate_credit=False)
    (out/'model.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');return result

if __name__=='__main__':
    import argparse,sys
    sys.path.insert(0,str(ROOT/'tools'))
    p=argparse.ArgumentParser();p.add_argument('--owner',type=Path,default=ROOT);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();x=build(a.owner,a.out)
    print(json.dumps({k:x['census'][k] for k in ('canonical_matrices','max_fragment_rows','calls','geometries','depth4_storage_PASS','missing_bindings','field_wait_masks')},indent=2))
    print(json.dumps(x['price'],indent=2))
