"""Native scalar indexed gathers: descriptor pins and actual RG0/WG0 timing.

The runtime index always comes from VM. Fixture-resolved A addresses are never
encoded into commands. A candidate is not a connected layer until its selected
engine, real bank-port ownership, source clocks and producer leases are bound.
"""
from __future__ import annotations
import math
from copy import deepcopy
import json
from pathlib import Path

ENGINE = 'ot_hbm_su_indexed_scalar'
BANKED_ENGINE = 'ot_hbm_su_indexed_scalar_banked'
SOURCE = 'rtl/hbm_accel/generic/adapters/static_su/gather/ot_hbm_su_indexed_scalar.sv'
BANKED_SOURCE = 'rtl/hbm_accel/generic/adapters/static_su/gather/ot_hbm_su_indexed_scalar_banked.sv'
SOURCE_REF = '865ad748e'
APERTURE = 1 << 18


def load_binding(path):
    record=json.loads(Path(path).read_text())
    if record.get('schema')!='opentallas.hbm.gather_calendar.v1':return record
    binding=deepcopy(record['source_binding'])
    if record.get('status')!='SOURCE_PROGRAMME':
        binding['status']='PARTIAL'
        binding['missing_producer_calendar_authorities']=record.get('missing',[])
    return binding


def integer(value, name, lo=0, hi=APERTURE-1):
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(f'{name}: finite integer outside selected source bounds')
    return value


def phases(read_sample, write_commit):
    r=integer(read_sample,'READ_SAMPLE',7,32760)
    w=integer(write_commit,'WRITE_COMMIT',4,65535)
    end=2*r+4+w
    if end>65535: raise ValueError('engine phase counter would overflow')
    # Phase p is evaluated one edge after the sampled start plus p. Requests
    # are registered outputs and the bank samples those pins the next edge.
    # The source programme checks old busy/done at release-1; ownership
    # therefore ends two edges after the engine publishes done.
    return dict(index_request_pin=1,index_sample=r+1,score_request_pin=r+3,
                score_sample=2*r+3,write_request_pin=2*r+5,done=end+1,
                source_phase_end=end,read_sample=r,write_commit=w)


def lower(raw, *, tag, source_window=None, binding=None, record_start=0, placement=None):
    from su_program_inventory import decode
    _,unit,sut,d=decode(raw)
    a,ix,o=(d.get(k) for k in ('A','I','O'))
    base=dict(status='candidate_requires_binding',sut=sut,reasons=[],
              lowering=dict(supported=False,owner='HBM-SU-GATHER-2000'),
              qualifies_native_layer=False,qualifies_native_chain=False)
    if (unit!=2 or a is None or ix is None or o is None or not a.indexed or
        any(x.space!='VM' for x in (a,ix,o)) or a.n!=1 or a.m!=1 or
        ix.n!=1 or ix.m!=1 or o.n!=1 or o.m!=1 or a.dyn_mul!=1 or ix.indexed or o.indexed):
        base.update(status='unsupported_lowering',reasons=['selected source requires scalar VM A[I] -> O, multiplier1'])
        return base
    # The dedicated gather engine copies a word; it must not replace arithmetic.
    if any(v for k,v in sut.items() if k not in ('a_ind','dst')) or sut['dst']!=1:
        base.update(status='unsupported_lowering',reasons=['indexed engine does not implement arithmetic/SFU/reduction'])
        return base
    descriptor=dict(index_word=integer(ix.base,'index_word'),score_base=integer(a.base,'score_base'),
                    dest_word=integer(o.base,'dest_word'),dyn_mul=1)
    base['native_gather']=dict(engine=ENGINE,source=SOURCE,source_ref=SOURCE_REF,
        descriptor=descriptor,tag=tag,address_expression='score_base + U32(live VM[index_word])',
        input_index_resolved_on_host=False,output_injected=False)
    if source_window is None:
        base['reasons']=['actual full score producer window and source receipt required']
        return base
    lo=integer(source_window['base'],'producer window base')
    hi=integer(source_window['limit'],'producer window limit',lo+1,APERTURE)
    if lo!=a.base or not source_window.get('producer') or not source_window.get('source_receipt'):
        raise ValueError('window must be the actual unresolved A producer, not fixture-resolved A')
    descriptor['score_limit']=hi
    base['native_gather']['logical_descriptor']=dict(descriptor)
    base['native_gather']['address_space']='logical HGI; actual producer placement not yet bound'
    if not binding or binding.get('status')!='PASS':
        base['reasons']=['existing indexed-scalar engine needs selected VM RG0/WG0 binding, clock, return ages and producer leases']
        return base
    if placement is None:
        base['reasons']=['actual producer logical-to-physical VM placement required; no identity mapping assumed']
        return base
    segmented=binding.get('parameters',{}).get('SEGMENTED96',0)==1
    segments=source_window.get('segment_bases') if segmented else None
    needed=[ix.base//8]
    if not segmented: needed+=list(range(lo//8,(hi-1)//8+1))
    missing=[sector for sector in needed if sector not in placement.map]
    if missing:
        base['reasons']=['actual source/index producer VM sectors not placed: '+str(missing)]
        return base
    if segmented:
        if hi-lo!=384 or not segments or len(segments)!=4:
            base['reasons']=['selected segmented96 source requires the real four GSC producer runs']
            return base
        for address in segments:integer(address,'actual GSC segment base',0,APERTURE-96)
        mapped=None
    else:
        mapped=[placement.map[sector] for sector in range(lo//8,(hi-1)//8+1)]
        if mapped!=list(range(mapped[0],mapped[0]+len(mapped))):
            base['reasons']=['runtime score window needs a contiguous producer allocation; existing VM placement is scattered']
            return base
    if binding.get('engine') not in (ENGINE,BANKED_ENGINE) or binding.get('status')!='PASS' or binding.get('clock')!='stream':
        raise ValueError('actual selected stream-clock indexed engine binding PASS required')
    if segmented and (binding['engine']!=BANKED_ENGINE or binding['parameters'].get('NATIVE_BANKED')!=1):
        raise ValueError('SEGMENTED96 requires actual banked implementation and NATIVE_BANKED=1')
    base['native_gather'].update(engine=binding['engine'],
        source=BANKED_SOURCE if binding['engine']==BANKED_ENGINE else SOURCE,
        source_ref=binding.get('source_ref'),source_sha256=binding.get('source_sha256'))
    if binding.get('read_client')!=0 or binding.get('write_client')!=0:
        raise ValueError('selected engine requires actual RG0/WG0 ownership')
    if not binding.get('source_sha256') or not binding.get('die_sha256'):
        raise ValueError('actual engine and die source identities required')
    profile=phases(binding['parameters']['READ_SAMPLE'],binding['parameters']['WRITE_COMMIT'])
    job=binding['jobs'][tag]
    ready=max(integer(job['index_ready'],'index producer ready',0,2**31-1),
              integer(job['score_ready'],'score producer ready',0,2**31-1))
    start=max(math.ceil(record_start),ready+1,integer(job['port_free'],'port available',0,2**31-1))
    done=start+profile['done']
    for name in ('index_release','score_release'):
        integer(job[name],name,done,2**31-1)
    integer(job['output_release'],'output consumer release',done+2,2**31-1)
    if binding.get('control_transport')!='ot_static_program_target':
        raise ValueError('selected source binding requires actual static-programme producer')
    # Input addresses come from actual producer placements. The output is a
    # real finite VM allocation shared with downstream records, not a guessed
    # logical=physical address or an injected result.
    physical_base=segments[0] if segmented else 8*mapped[0]+lo%8
    descriptor.update(index_word=8*placement.map[ix.base//8]+ix.base%8,
                      score_base=physical_base,score_limit=max(segments)+96 if segmented else physical_base+(hi-lo),
                      dest_word=8*(placement.map[o.base//8] if o.base//8 in placement.map else
                                   placement.get(o.base//8,0,tag+':indexed_O'))+o.base%8)
    if segmented:
        descriptor['segment_bases']=list(segments)
        base['native_gather']['address_expression']='segment_bases[U32(live VM[index_word]) // 96] + U32(live VM[index_word]) % 96'
    if job.get('descriptor')!=descriptor:
        raise ValueError('compiler placement differs from the actual native producer receipt descriptor')
    for name in ('index_word','score_base','dest_word'):
        integer(descriptor[name],name)
    integer(descriptor['score_limit'],'physical score limit',descriptor['score_base']+1,APERTURE)
    base['native_gather']['address_space']='actual producer VM placement'
    base['native_gather']['outer_slice_state_updated']=False
    base.update(status='native_gather_emitted',reasons=[])
    base['lowering'].update(supported=True,execution_qualified=False)
    base['native_gather'].update(start=start,done=done,phases=profile,
        port_reservations=[dict(client=client,banks=list(range(32)),first=start,last_exclusive=done+2) for client in ('RG0','WG0')],
        producer_leases=job,source_binding=binding)
    return base


def encode_programme_row(descriptor, *, start, release, row_identity):
    """Actual opt-in HBM binding ABI implemented by the gather source owner.

    Lower120 bits are the existing engine's five24-bit input pins. Two dated
    16-bit fields select ownership; the standard target tag and row identity
    occupy the upper32 bits. No runtime index value enters this record.
    """
    value=0
    for k,name in enumerate(('index_word','score_base','score_limit','dest_word','dyn_mul')):
        value |= integer(descriptor[name],name,0,(1<<24)-1) << (24*k)
    if descriptor['score_limit']>APERTURE or not 0<=descriptor['score_base']<descriptor['score_limit']:
        raise ValueError('score producer window is outside native VM')
    for name in ('index_word','dest_word'):
        integer(descriptor[name],name)
    if descriptor['dyn_mul']!=1:raise ValueError('selected source scalar multiplier must be1')
    value |= integer(start,'programme start',2,65535)<<120
    value |= integer(release,'programme release',start+1,65535)<<136
    if descriptor.get('segment_bases') is not None:
        segments=descriptor['segment_bases']
        if len(segments)!=4 or segments[0]!=descriptor['score_base']:
            raise ValueError('actual four-run segmented96 source bases required')
        for index,address in enumerate(segments):
            integer(address,'segment base',0,APERTURE-96)
            if address+96>descriptor['score_limit']:raise ValueError('segment exceeds native score limit')
            if index:value |= address << (152+24*(index-1))
    value |= integer(row_identity,'programme row identity',0,65535)<<224
    return value | (0xc7a1<<240)


def programme_replay(plans, binding):
    """Install six actual descriptor rows through the released host-CP caller.

    Binding supplies the measured launch-to-calendar phase. Producer readiness
    and programme epoch are actual selected-source dates, never model zeros.
    """
    from hbm_layer_vehicle.layer_images import cp_frames
    if binding.get('control_transport')!='ot_static_program_target':
        raise ValueError('actual static programme target binding required')
    if len(plans)!=6 or any(p.get('status')!='native_gather_emitted' for p in plans):
        raise ValueError('all six source-bound route gathers must be present')
    epoch=integer(binding['calendar_epoch'],'actual calendar epoch',0,2**31-1)
    selector_tail=integer(binding['ownership_release_tail'],'actual selector ownership release tail',0,65535)
    if integer(binding['port_free'],'actual bank ownership availability',0,2**31-1)>epoch:
        raise ValueError('programme epoch precedes actual native bank port release')
    profile=phases(binding['parameters']['READ_SAMPLE'],binding['parameters']['WRITE_COMMIT'])
    rows=[];previous_release=0
    for ix,plan in enumerate(plans):
        rec=plan['native_gather'];start=rec['start']-epoch
        if rec['done']!=rec['start']+profile['done']:
            raise ValueError('gather done differs from actual selected source phase profile')
        release=rec['done']+2-epoch
        if start<previous_release:raise ValueError('indexed gather programme port reservations overlap')
        if rec['descriptor'].get('segment_bases') is not None and binding['parameters'].get('SEGMENTED96')!=1:
            raise ValueError('segmented descriptor requires the actual enabled source parameter')
        rows.append(encode_programme_row(rec['descriptor'],start=start,release=release,row_identity=ix))
        previous_release=release
    from hbm_layer_vehicle.sm_images import cal_word,prog_row
    expected_launch=epoch-integer(binding['launch_to_calendar_zero'],'actual target launch phase',1,65535)
    if expected_launch<0:raise ValueError('actual calendar epoch precedes host launch')
    native=binding.get('bank_calendars',{})
    if set(native)!=set(('SW','SE','NW','NE')):raise ValueError('four actual native bank calendars required')
    end=epoch+previous_release+selector_tail
    events=[];calendar_plans=[]
    free=integer(binding['configuration_start'],'actual CP configuration start',0,2**31-1)
    first_owner=epoch;last_owner=end;targets={binding['target_id']}
    for quarter in ('SW','SE','NW','NE'):
        cal=native[quarter];target=integer(cal['target_id'],'actual native calendar target',0,255)
        if target in targets or not cal.get('source_sha256'):raise ValueError('unique source-bound native calendar target required')
        targets.add(target)
        ages=cal['launch_to_bank_owner_edges']
        if len(ages)!=8:raise ValueError('actual owner publication age required for all eight native banks')
        owner_edges=[expected_launch+integer(age,'actual launch to native owner pin',1,65535) for age in ages]
        if max(owner_edges)>min(p['native_gather']['start'] for p in plans):
            raise ValueError('gather starts before native bank calendar ownership is published')
        first=min(owner_edges)
        if binding['port_free']>first:raise ValueError('native calendar preempts a live previous bank owner')
        span=max(1,end-first);nrows=(span+65534)//65535
        if nrows>1024:raise ValueError('native owner calendar exceeds source PCW10 capacity')
        loops=(span+nrows-1)//nrows
        words=[prog_row(i,cal_word(rslot_v=255,wslot_v=255),187) for i in range(nrows)]
        cp,_,free=cp_frames(target,words,free,loops=loops,launch=False);events+=cp
        final=max(owner_edges)+nrows*loops
        first_owner=min(first_owner,first);last_owner=max(last_owner,final)
        calendar_plans.append(dict(quarter=quarter,target=target,owner=0,rows=nrows,loops=loops,
            first_owner_edges=owner_edges,last_owner_exclusive=final,
            programme_rows=[f'{word:064x}' for word in words],source_profile=cal))
    cp,launch,free=cp_frames(integer(binding['target_id'],'actual target ID',0,255),rows,free)
    events+=cp
    if launch+integer(binding['launch_to_calendar_zero'],'actual target launch phase',1,65535)!=epoch:
        raise ValueError('host CP launch and actual selected programme epoch differ')
    return dict(schema='opentallas.hbm_slice_replay.v1',scope='component_probe',
        qualifies_native_layer=False,qualifies_native_chain=False,events=events,
        programme_rows=[f'{v:064x}'for v in rows],configuration_next_free=free,
        calendar_epoch=epoch,source_binding=binding,native_owner_calendars=calendar_plans,
        port_reservations=[dict(client=client,banks=list(range(32)),first=first_owner,
                                last_exclusive=last_owner) for client in ('RG0','WG0')],
        assumptions=['actual runtime producers retain I and complete score window; no resolved index encoded'])
