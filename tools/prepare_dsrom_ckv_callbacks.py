#!/usr/bin/env python3
"""Prospective full512 callback ABI and independent finite trace assertions.

No HDL or hardware callback exists merely because this file defines its ABI.
Input words are immutable synthetic stimuli; expected hashes only feed assertions.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/rtl/dsrom_ckv_callback_prepare_20261003'
K=512


def digest(value,width):return hashlib.sha256(value.to_bytes(width,'little')).hexdigest()


def images():
    gids=list(range(511))+[4095]
    rows=[]
    for rank,gid in enumerate(gids):
        codes=sum(((i+rank)%16)<<(4*i) for i in range(512))
        raw=codes+sum(0x38<<(2048+8*g) for g in range(32))
        packed=sum(((1<<264)+((raw>>(128*g))&((1<<128)-1))+(((raw>>(2048+16*g))&65535)<<128))<<(265*g) for g in range(16))
        rows.append(dict(rank=rank,gid=gid,owner=(gid>>4)&3,row_hex=f'{raw:0576x}',row_sha=digest(raw,288),packed_sha=digest(packed,530)))
    window=[]
    for r in range(128):
        raw=sum(((i+r)%120)<<(8*i) for i in range(512))+sum(127<<(4096+8*g) for g in range(16))
        packed=sum((((raw>>(256*g))&((1<<256)-1))+(((raw>>(4096+8*g))&255)<<256))<<(265*g) for g in range(16))
        window.append(dict(row=r,row_hex=f'{raw:01056x}',packed_sha=digest(packed,530)))
    bf=[0,0x3f00,0x3f80,0x3fc0,0x4000,0x4040,0x4080,0x40c0]
    own_codes=[(i+511)%16 for i in range(512)]
    nw=[bf[c&7]|(0x8000 if c&8 else 0) for c in own_codes]
    beats=[sum(nw[32*b+i]<<(32*i+16) for i in range(32)) for b in range(16)]
    return dict(scope='IMMUTABLE_SYNTHETIC_INPUT_WORDS_ONLY_EXPECTED_HASHES_ASSERTIONS_ONLY',K=512,TROWS=640,group_id=0x1000000000000001,
                rows=rows,window=window,own_gid=4095,own_owner=3,own_capture_BF16_in_FP32_hex=[f'{x:0256x}' for x in beats],
                own_row_contract='all16-element blocks contain magnitude6, scale1=E4M3 0x38; exact representable E2M1 values including signed zero; encoder output assertion uses row511 raw words')


def uint(x,width):
    if type(x)!=int or not 0<=x<2**width:raise ValueError('malformed integer/width')


def validate(events,im):
    """Independent assertion consumer. No expected values are returned to DUT."""
    states=[dict(rows={},stages={'QK':0,'PV':0},retired=[],epoch=None,table=False,out=set(),desc={}) for _ in range(4)]
    pending=set();sent=set();stored={};emitted={};acks=set();writes={};visible=set();reset=False;ended=False;last=-1
    group=im['group_id'];rejections=0;callbacks=0
    for e in events:
        if ended:raise ValueError('callback after terminal/duplicate terminal')
        if type(e)!=dict:raise ValueError('malformed callback')
        uint(e.get('edge'),64);uint(e.get('group'),64)
        if e['edge']<last or e['group']!=group:raise ValueError('edge/group identity mismatch')
        last=e['edge'];kind=e.get('kind');callbacks+=1
        if kind=='reset_barrier':
            if reset or any(s['epoch'] is not None for s in states) or e.get('all4_endpoints_drained') is not True:
                raise ValueError('reset barrier absent/duplicate/late')
            reset=True;continue
        if kind=='end':
            if not reset or pending or visible!=set(range(9)) or len(sent)!=511*3 or len(acks)!=511*3:
                raise ValueError('peer/publication/coverage not drained')
            if any(len(s['rows'])!=512 or s['retired']!=['QK','PV'] for s in states):raise ValueError('both full passes not retired')
            ended=True;continue
        uint(e.get('die'),2);die=e['die'];s=states[die]
        if kind=='selection_accept':
            uint(e.get('epoch'),16)
            if not reset or s['epoch'] is not None or e.get('valid') is not True or e.get('ready') is not True or e.get('old_lease_drained') is not True or e.get('count_after')!=0:
                raise ValueError('selection/atomic clear admission')
            if any(t['epoch'] is not None and t['epoch']!=e['epoch'] for t in states):raise ValueError('group selection epochs disagree')
            uint(e.get('count_after'),10)
            s['epoch']=e['epoch'];s['select_edge']=e['edge'];continue
        if s['epoch'] is None or e.get('epoch')!=s['epoch']:raise ValueError('active selection generation mismatch')
        if kind=='table_publish':
            uint(e.get('count'),10)
            if s['table'] or e.get('count')!=512:raise ValueError('full ID table required')
            s['table']=True
        elif kind=='broadcast_accept':
            r=e.get('rank');uint(r,10)
            if r>=511 or not s['table'] or im['rows'][r]['owner']!=die or e.get('valid') is not True or e.get('ready') is not True:raise ValueError('broadcast admission')
            for dst in range(4):
                if dst!=die:
                    token=(die,dst,r)
                    if token in sent:raise ValueError('duplicate broadcast')
                    sent.add(token);pending.add(token)
        elif kind=='storage_accept':
            r=e.get('rank');uint(r,10);uint(e.get('gid'),21)
            if r>=512:raise ValueError('rank outside512')
            expected=im['rows'][r]
            uint(e.get('offered_epoch'),16)
            if e['offered_epoch']!=s['epoch']:raise ValueError('RX carried generation mismatch')
            uint(e.get('count_before'),10);uint(e.get('count_after'),10)
            if (not s['table'] or e['edge']==s['select_edge'] or r in s['rows'] or e['gid']!=expected['gid'] or
                    e.get('valid') is not True or e.get('ready') is not True or e.get('write_strobe') is not True or
                    e.get('row_sha')!=expected['row_sha'] or e.get('count_before')!=len(s['rows']) or e.get('count_after')!=len(s['rows'])+1):
                raise ValueError('invalid storage write/count')
            source=e.get('source');uint(source,2)
            if r==511:
                if source!=die or e.get('origin')!='own_encoder':raise ValueError('own row origin')
            elif source!=expected['owner']:raise ValueError('wrong source owner')
            elif source!=die:
                token=(source,die,r)
                if token not in pending:raise ValueError('remote row without owned broadcast')
                stored[token]=e['edge']
            s['rows'][r]=e['row_sha']
        elif kind=='rx_reject':
            r=e.get('rank');uint(r,10)
            old=s['rows'].get(r)
            uint(e.get('count_before'),10);uint(e.get('count_after'),10)
            if (e.get('valid') is not True or e.get('ready') is not False or e.get('write_strobe') is not False or
                    e.get('count_before')!=len(s['rows']) or e.get('count_after')!=len(s['rows']) or
                    e.get('row_before')!=old or e.get('row_after')!=old or e.get('fault') is not True or
                    e.get('reason') not in ['stale','duplicate','wrong_gid','wrong_owner','range','malformed']):
                raise ValueError('rejected RX mutated or unbound')
            offered=e.get('offered_epoch');uint(offered,16);uint(e.get('gid'),21);uint(e.get('source'),2)
            reason=e['reason']
            bound=(reason=='stale' and offered!=s['epoch']) or (reason=='duplicate' and r in s['rows']) or (reason=='range' and r>=512) or (reason=='wrong_gid' and r<512 and e['gid']!=im['rows'][r]['gid']) or (reason=='wrong_owner' and r<512 and e['source']!=im['rows'][r]['owner']) or (reason=='malformed' and e.get('format_valid') is False)
            if not bound:raise ValueError('rejection reason lacks actual offending field')
            rejections+=1
        elif kind=='stored_ACK_emit':
            uint(e.get('echo_epoch'),16)
            if e['echo_epoch']!=s['epoch']:raise ValueError('ACK carried generation mismatch')
            uint(e.get('source'),2);uint(e.get('rank'),10);token=(e['source'],die,e['rank'])
            if token not in stored or token in emitted or e['edge']<=stored[token] or e.get('valid') is not True or e.get('ready') is not True:
                raise ValueError('ACK emit before actual store/duplicate/unowned')
            emitted[token]=e['edge']
        elif kind=='stored_ACK_return':
            uint(e.get('echo_epoch'),16)
            if e['echo_epoch']!=s['epoch']:raise ValueError('ACK carried generation mismatch')
            uint(e.get('destination'),2);uint(e.get('rank'),10);token=(die,e['destination'],e['rank'])
            if token not in emitted or token in acks or e['edge']<=emitted[token] or e.get('valid') is not True or e.get('ready') is not True or e.get('pending_before') is not True or e.get('pending_after') is not False:
                raise ValueError('ACK return before registered emit/duplicate/unowned/pending clear')
            acks.add(token);pending.remove(token)
        elif kind=='stage_write':
            phase=e.get('phase')
            if phase not in ['QK','PV'] or (phase=='PV' and s['retired']!=['QK']):raise ValueError('phase lease')
            uint(e.get('descriptor_generation'),16)
            gen=e['descriptor_generation']
            if phase in s['desc'] and s['desc'][phase]!=gen:raise ValueError('mutable descriptor generation')
            if phase=='PV' and gen==s['desc'].get('QK'):raise ValueError('descriptor generation reused across passes')
            s['desc'][phase]=gen
            ptr=s['stages'][phase]
            uint(e.get('row_base'),10);uint(e.get('stage_addr'),8);uint(e.get('mask'),4)
            if ptr>=640 or e.get('row_base')!=ptr or e.get('stage_addr')!=ptr//4 or e.get('mask')!=15 or e.get('valid') is not True or e.get('ready') is not True or e.get('write_strobe') is not True:
                raise ValueError('actual staging acceptance/address/mask')
            expected=[]
            for r in range(ptr,ptr+4):
                if r<128:expected.append(im['window'][r]['packed_sha'])
                else:
                    if r-128 not in s['rows']:raise ValueError('stage before row storage')
                    expected.append(im['rows'][r-128]['packed_sha'])
            if e.get('packed_hashes')!=expected:raise ValueError('packed words mismatch')
            s['stages'][phase]+=4
        elif kind=='output_write':
            phase=e.get('phase')
            if phase not in ['QK','PV'] or phase in s['retired'] or s['stages'][phase]!=640 or e.get('descriptor_generation')!=s['desc'].get(phase) or e.get('actual_write') is not True:raise ValueError('actual output write missing')
            s['out'].add(phase)
        elif kind=='descriptor_retire':
            phase=e.get('phase')
            if e.get('descriptor_generation')!=s['desc'].get(phase):raise ValueError('retire descriptor generation mismatch')
            expected='QK' if not s['retired'] else 'PV'
            if (len(s['retired'])>=2 or phase!=expected or s['stages'].get(phase)!=640 or phase not in s['out'] or
                    e.get('actual_desc_done') is not True or e.get('actual_engine_idle') is not True or e.get('output_write_mask')!=0):
                raise ValueError('actual attention/output retirement missing')
            s['retired'].append(phase)
        elif kind in ['owner_write_accept','owner_write_visible']:
            n=e.get('sector');uint(n,4)
            if n>=9 or die!=im['own_owner'] or e.get('gid')!=im['own_gid'] or e.get('stack')!=((im['own_gid']>>6)&3):raise ValueError('write ownership')
            loc=((im['own_gid']>>8)<<4)|(im['own_gid']&15)
            if e.get('address')!=(1<<22)+9*loc+n:raise ValueError('write address')
            raw=int(im['rows'][511]['row_hex'],16);word=(raw>>(256*n))&((1<<256)-1)
            if e.get('word_sha')!=digest(word,32):raise ValueError('publication word mismatch')
            if kind=='owner_write_accept':
                if writes.keys()!=visible or n in writes or e.get('valid') is not True or e.get('ready') is not True:raise ValueError('write outstanding/accept')
                writes[n]=e['edge']
            else:
                if n not in writes or n in visible or e['edge']<=writes[n] or e.get('actual_wr_done') is not True or e.get('backing_write_observed') is not True:raise ValueError('write visibility not completion')
                visible.add(n)
        else:raise ValueError('unknown callback')
    if not ended:raise ValueError('missing terminal')
    return dict(status='PASS_FINITE_SYNTHETIC_CALLBACK_CONTRACT_ONLY_NO_DUT',selected_rows_stored=2048,selected_rows_staged=4096,stage_rows=5120,stored_ACK_emits=1533,stored_ACKs=1533,owner_visible_sectors=9,rejected_offers=rejections,callbacks=callbacks,actual_RTL_measured=False)


def fixture(im,epoch=1):
    out=[];edge=0;g=im['group_id']
    def add(kind,die=None,**kw):
        e=dict(kind=kind,edge=edge,group=g,**kw)
        if die is not None:e.update(die=die,epoch=epoch)
        out.append(e)
    add('reset_barrier',all4_endpoints_drained=True);edge+=1
    for d in range(4):add('selection_accept',d,valid=True,ready=True,old_lease_drained=True,count_after=0)
    edge+=1
    for d in range(4):add('table_publish',d,count=512)
    counts=[0]*4
    for r,row in enumerate(im['rows']):
        edge+=1;source=row['owner']
        if r<511:add('broadcast_accept',source,rank=r,valid=True,ready=True)
        for d in range(4):
            add('storage_accept',d,offered_epoch=epoch,rank=r,gid=row['gid'],source=d if r==511 else source,origin='own_encoder' if r==511 else 'fetched',valid=True,ready=True,write_strobe=True,row_sha=row['row_sha'],count_before=counts[d],count_after=counts[d]+1);counts[d]+=1
        edge+=1
        if r<511:
            for d in range(4):
                if d!=source:add('stored_ACK_emit',d,echo_epoch=epoch,source=source,rank=r,valid=True,ready=True)
            edge+=1
            for d in range(4):
                if d!=source:add('stored_ACK_return',source,echo_epoch=epoch,destination=d,rank=r,valid=True,ready=True,pending_before=True,pending_after=False)
    for n in range(9):
        edge+=1;raw=int(im['rows'][511]['row_hex'],16);word=(raw>>(256*n))&((1<<256)-1);gid=im['own_gid'];loc=((gid>>8)<<4)|(gid&15)
        fields=dict(gid=gid,stack=(gid>>6)&3,sector=n,address=(1<<22)+9*loc+n,word_sha=digest(word,32))
        add('owner_write_accept',3,valid=True,ready=True,**fields);edge+=2;add('owner_write_visible',3,actual_wr_done=True,backing_write_observed=True,**fields)
    for phase in ['QK','PV']:
        for ptr in range(0,640,4):
            edge+=1;hashes=[im['window'][r]['packed_sha'] if r<128 else im['rows'][r-128]['packed_sha'] for r in range(ptr,ptr+4)]
            for d in range(4):add('stage_write',d,phase=phase,descriptor_generation=1 if phase=='QK' else 2,row_base=ptr,stage_addr=ptr//4,mask=15,valid=True,ready=True,write_strobe=True,packed_hashes=hashes)
        edge+=1
        for d in range(4):add('output_write',d,phase=phase,descriptor_generation=1 if phase=='QK' else 2,actual_write=True)
        edge+=2
        for d in range(4):add('descriptor_retire',d,phase=phase,descriptor_generation=1 if phase=='QK' else 2,actual_desc_done=True,actual_engine_idle=True,output_write_mask=0)
    edge+=1;add('end');return out


def prepare(out):
    if out.exists():raise ValueError('fresh output directory required')
    out.mkdir(parents=True)
    pins=json.loads((BASE/'input_pins.json').read_text())
    for pin in pins:
        if hashlib.sha256((BASE/pin['archive']).read_bytes()).hexdigest()!=pin['sha256']:raise ValueError('source pin mismatch')
    model=json.loads((BASE/'inputs/lease_model.json').read_text())
    im=images();ev=fixture(im);result=validate(ev,im)
    (out/'input_words.json').write_text(json.dumps(im,indent=2)+'\n')
    (out/'finite_fixture.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in ev))
    (out/'fixture_receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    abi=dict(version='CKV_CALLBACK_V1',status='PROSPECTIVE_EXACT_INTERFACE_NOT_INSTALLED',model_commit='eae838a3ad98bde6505694aa8d4d74385856e63f',full_geometry=dict(K=512,TROWS=640,D=512,NL=4,TP=4,NSLOT=64),capacity=dict(CKV_bytes_per_rank=147456,staging_bytes_per_rank=339200),callbacks=sorted({e['kind'] for e in ev}|{'rx_reject'}),sampling='after actual rising-edge eval/NBA settle; report actual strobes and before/after storage, never inferred from offers',identity=dict(group_ref='uint64 software directory handle preserving native owner mapping; not a physical tag or truncated/hash native identity',selection_epoch='uint16 separate from descriptor generation',rank='10 bits validated<512',gid='21 bits, immutable selected ID table'),hardware_increment=model['incremental'],observer_extra_hardware_bits=0,resource_scope='Python preparation only; no compiler/HDL or new compute lease. Generated header is declarations only; future complete source package needs reviewed measured resource admission and fresh GO.',numerical_scope='transport/reformat/retirement contract; output_write proves ownership event only, not full QK/PV arithmetic golden',program_failure_scope='illegal RX/reset/duplicate fixtures are negative interface controls; unbounded stalls are not admitted-program failure',source_hooks=dict(selection_accept='successor actual sel_v&&sel_ready; original core su_go lacks service readiness',storage_accept='successor qualified buf_row/present write + npresent snapshots; original accepts bad in-range rows',stored_ACK_emit='successor destination registered ACK valid and accepted on reverse link, after actual storage',stored_ACK_return='successor source pending-bit clear on matching destination/rank/epoch ACK, never TX/dequeue',stage_write='runtime adapter kv_stream_v&&kv_ready -> engine u_stage wr_en/wptr/4',descriptor_retire='actual att_packed_desc_done && att_packed_idle, e_idle includes no o_we',owner_write_visible='candidate mux recorded owner c_wr_done + idx_hbm actual masked backing write; original mux blocks this path'),build_GO=False,physical_credit=False,fulltoken_credit=False)
    (out/'callback_abi.json').write_text(json.dumps(abi,indent=2)+'\n')
    (out/'ckv_callback_v1.hpp').write_text('''#pragma once
// Prospective observer ABI only. No installed callback or hardware proof.
#include <cstdint>
#include <array>
#include <vector>
namespace ot_ckv_callback_v1 {
enum class Phase : std::uint8_t { QK, PV };
struct Identity { std::uint64_t group_ref, edge; std::uint16_t selection_epoch; std::uint8_t die; };
struct Row { std::uint16_t rank; std::uint32_t gid; std::uint8_t source; std::array<std::uint32_t,72> words; };
struct Snapshot { std::uint16_t count_before,count_after; bool valid,ready,actual_write; };
struct Selection { Identity id; bool valid,ready,old_lease_drained; std::uint16_t count_after; };
struct ResetBarrier { std::uint64_t group_ref,edge; bool all4_endpoints_drained; };
struct TablePublish { Identity id; std::uint16_t count; };
struct Broadcast { Identity id; std::uint16_t rank; bool valid,ready; };
enum class RejectReason : std::uint8_t { Stale, Duplicate, WrongGid, WrongOwner, Range, Malformed };
struct RejectedRx { Identity id; Row offered; std::uint16_t offered_epoch; Snapshot probe; std::array<std::uint32_t,72> before,after; bool row_present,fault,format_valid; RejectReason reason; };
struct OutputWrite { Identity id; Phase phase; std::uint16_t descriptor_generation; bool actual_write; /* Per-port actual o_we/o_addr/o_mask/o_data, width bound in generated source adapter. */ std::vector<std::uint32_t> enables,addresses,masks,data; };
struct Storage { Identity id; std::uint16_t offered_epoch; Row row; Snapshot probe; };
struct StoredAck { Identity id; std::uint8_t peer; std::uint16_t rank,echo_epoch; bool valid,ready,pending_before,pending_after; };
struct Stage { Identity id; Phase phase; std::uint16_t descriptor_generation,row_base,write_addr; std::uint8_t mask; bool valid,ready,actual_write; std::array<std::uint32_t,530> words; };
struct Retire { Identity id; Phase phase; std::uint16_t descriptor_generation; bool descriptor_done,engine_idle; std::uint32_t output_write_mask; };
struct OwnerWrite { Identity id; std::uint32_t gid,address; std::uint8_t stack,sector; std::array<std::uint32_t,8> words; bool valid,ready,actual_wr_done,actual_backing_write; };
struct Sink { virtual ~Sink()=default; virtual void reset_barrier(const ResetBarrier&)=0; virtual void table_publish(const TablePublish&)=0; virtual void broadcast_accept(const Broadcast&)=0; virtual void rx_reject(const RejectedRx&)=0; virtual void output_write(const OutputWrite&)=0; virtual void end(std::uint64_t group_ref,std::uint64_t edge)=0; virtual void selection(const Selection&)=0; virtual void storage(const Storage&)=0; virtual void stored_ack_emit(const StoredAck&)=0; virtual void stored_ack_return(const StoredAck&)=0; virtual void staging(const Stage&)=0; virtual void retire(const Retire&)=0; virtual void owner_write(const OwnerWrite&)=0; };
}
''')
    source_base=ROOT/'results/uarch/dsrom_ckv_receive_lease_g0_20261003'
    origins=json.loads((source_base/'source_manifest.json').read_text())['origins']
    for origin in origins:
        if hashlib.sha256((source_base/origin['archive']).read_bytes()).hexdigest()!=origin['sha256']:
            raise ValueError('full-parent source/library pin mismatch')
    targets={
        'selection_accept':('rtl/w17_runtime/hdc/v41x/fastpp_pc21/l20/ot_hdc_core_v41x.sv','assign ckv_sel_v'),
        'storage_accept':('rtl/chip/ot_chip_v41x_ckv_die_service.sv','buf_row[wrank'),
        'table_publish':('rtl/chip/ot_chip_v41x_ckv_die_service.sv','wire id_done'),
        'stage_write':('rtl/hdc/v41x/ot_hdc_v41x_attn.sv','.wr_en({NL{kv_go}}'),
        'descriptor_retire':('rtl/chip/ckvsel/ot_chip_v41x_die.sv','.retain_complete(att_packed_desc_done'),
        'output_write':('rtl/w17_runtime/hdc/v41x/ot_hdc_v41x_att_adapt.sv','idle <= (st == A_IDLE)'),
        'owner_write_visible':('rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv',"wr_done[p] <= 1'b1"),
        'owner_write_accept':('rtl/chip/ot_chip_v41x_ckv_die_service.sv','if (wr_act && c_rdy[wr_stack])')}
    bindings={}
    for callback,(path,text) in targets.items():
        origin=next(x for x in origins if x['path']==path)
        lines=(source_base/origin['archive']).read_text().splitlines()
        matches=[dict(line=i+1,source=line) for i,line in enumerate(lines) if text in line]
        if not matches:raise ValueError('source hook equation missing')
        bindings[callback]=dict(origin=origin,equation=matches,installed_successor=False)
    for callback in ['reset_barrier','broadcast_accept','rx_reject','stored_ACK_emit','stored_ACK_return','end']:
        bindings[callback]=dict(installed_successor=False,prospective_requirement=callback+' must bind successor actual state/strobes; no installed equivalent is assumed')
    (out/'source_hook_bindings.json').write_text(json.dumps(dict(source_pins_verified=len(origins),bindings=bindings),indent=2)+'\n')
    component=dict(status='SOURCE_SIZED_PROSPECTIVE_CALLBACK_COMPONENT_NO_HDL',parent_model_commit=abi['model_commit'],
        source_commit=model['source_commit'],full_L20_sources=125,Hubble_observer_commit=pins[0]['commit'],
        source_model_unchanged=True,geometry=abi['full_geometry'],capacity=abi['capacity'],incremental=model['incremental'],
        interfaces=dict(selection='four ready/valid accepts + shared epoch16 grant; clear dominates storage',
            forward='12 directed routes, 2304 payload + rank10 + gid21 + epoch16 + ready; source/GID ownership immutable',
            reverse='12 directed routes, registered valid + epoch16 + rank10 + ready; emission after store, return clears own pending bit',
            staging='4 ranks; 4 rows/beat, 16960 data bits + mask4; 160 accepted beats/pass, 640 rows, QK and PV distinct descriptor generations',
            publication='one owner, nine 256bit sectors, actual request acceptance then returned wr_done and backing write; no request-only visibility'),
        component_gate=dict(cases=['full512 valid and exact raw/reformatted words','stale/duplicate/wrongID/wrongowner/range/malformed refusals preserve storage','atomic selection clear and ready stall','ACK emission/return ownership and generation','both full640 QK/PV staging and actual output idle retirement','nine owner writes and returned completion','reset/wrap only all routes/storage/publication/consumers drained'],
            numerical_obligations_open='full QK/PV arithmetic oracle is separate; this interface only observes words and ownership',
            actual_source_adapters_open=True,default_parameter='CKV_RX_LEASE=0',compile_GO=False,
            resource_plan='complete source adapter/model and fresh measured host CPU/memory/disk lease before compile; unlimited file size, no arbitrary build wall/AS caps; no PVE2/PVE3'),
        frozen_H4_connector=model['frozen_H4_connector'],clock_domain_contract=model['CDC'],ports_and_boundary_price=model['boundaries'],latency_assumptions=model['prospective_bounds'],
        hardware_admission='prospective source-ready functional component; no installed full-die or physical/CDC/slot admission',physical_credit=False,fulltoken_credit=False)
    (out/'component_model.json').write_text(json.dumps(component,indent=2)+'\n')
    fields={}
    for event in ev:
        fields.setdefault(event['kind'],{key:type(value).__name__ for key,value in event.items()})
    fields['rx_reject']={key:typ for key,typ in dict(kind='str',edge='int',group='int',die='int',epoch='int',offered_epoch='int',rank='int',gid='int',source='int',valid='bool',ready='bool',write_strobe='bool',count_before='int',count_after='int',row_before='str_or_null',row_after='str_or_null',fault='bool',reason='str',format_valid='bool_required_for_malformed').items()}
    (out/'event_field_schema.json').write_text(json.dumps(dict(fields=fields,
        JSON_to_CXX=dict(epoch='id.selection_epoch is active epoch; offered_epoch and echo_epoch are independently sampled carried tags',source='ACK emit: source origin; ACK return: destination identifies actual emitting peer; C++ StoredAck.peer maps accordingly',
            hashes='serializer hashes actual sampled raw words; independent assertion consumer alone computes expected hashes',
            output_write='record actual o_we/o_addr/o_mask/o_data vectors at their source-bound widths; fixture only tests ownership event, not numerical output correctness'),
        reject_semantics='ready false for invalid RX; storage and npresent unchanged, error flags asserted from source predicates; valid backpressure is not an invalid RX fault',
        unobserved_edges='trace gaps imply no acceptance measurement; never infer ready, idle, deadline or latency from gaps',
        reset_scope='this fixture admits one epoch after a drained reset barrier; mid-lease reset/wrap and second-generation reuse need actual full source gate, not claimed here'),indent=2)+'\n')
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()}
    (out/'artifact_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();mode=p.add_mutually_exclusive_group(required=True);mode.add_argument('--out',type=Path);mode.add_argument('--trace',type=Path);p.add_argument('--images',type=Path);p.add_argument('--receipt',type=Path);a=p.parse_args()
    if a.out:prepare(a.out)
    else:
        if not a.images or not a.receipt:p.error('--trace requires --images and fresh --receipt')
        if a.receipt.exists():raise ValueError('fresh receipt required; preserve previous result')
        im=json.loads(a.images.read_text())
        if im!=images():raise ValueError('immutable input image changed')
        try:
            result=validate([json.loads(line) for line in a.trace.read_text().splitlines()],im)
        except (ValueError,TypeError,KeyError) as err:
            result=dict(status='FAIL_CALLBACK_CONTRACT',diagnosis=str(err),actual_RTL_measured=False)
            a.receipt.write_text(json.dumps(result,indent=2)+'\n');raise
        a.receipt.write_text(json.dumps(result,indent=2)+'\n')
