#!/usr/bin/env python3
"""Replay actual PC0 publication and size a finite endpoint owner controller.

Provider ticks and virtual-rank backing addresses never become hardware timing
or physical die identities. No arithmetic, engine RTL, or ideal refill is used.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import zlib

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/h4_hbm_production_owner_20261002'
INPUT_SHA = 'ead636fcc8e10a947f1e71516e1bc752492d9f85c96d84a16c36752bc016f2f1'
RAW_SHA = '6b4f32a19ab71908e90d51d9e6d292d73932c8d8d28d974fefc92f5b859940de'
PROJECTION_SHA = '647abb96910b945464e5953c839b33d6946e0cf96f652f16ea63513c1f1edbbb'
RF_SM = 262144

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':')).encode()

def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()

def inputs():
    raw = (BASE/'inputs_manifest.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != INPUT_SHA:
        raise ValueError('input manifest pin')
    out = {}
    for r in json.loads(raw)['inputs']:
        p = (BASE/r['archive']).resolve()
        if not p.is_relative_to(BASE.resolve()):
            raise ValueError('input archive origin')
        b = p.read_bytes()
        if len(b) != r['bytes'] or hashlib.sha256(b).hexdigest() != r['sha256']:
            raise ValueError('exact input hash')
        out[p.name] = b
    return out

def rf_coordinate(sector):
    """Exact r30 provider ABI. Rank-to-die is intentionally a separate input."""
    if type(sector) is not int or not 0 <= sector < 32*2*RF_SM//32:
        raise ValueError('RF extent')
    address = sector*32
    sm_copy, local = divmod(address, RF_SM)
    sm, mirror = divmod(sm_copy, 2)
    slot, within = divmod(local, 512)
    page, row = divmod(slot, 128)
    word, lane = divmod(within, 32)
    return dict(SM=sm, mirror=mirror, slot=slot, bank=word, page=page, row=row,
                word=word, local_byte_address=local, source_sector=sector,
                source_byte_address=address, sector_word_lane=lane)

class OwnerController:
    """Constructive finite FSM: one credit per SM and one per shared L2 bank.

    Events represent explicit endpoint handshakes, NOT generic 'done' packets.
    A write visibility fence holds both credits through two mirror ACKs,
    downstream consumption, and reverse retirement. It never times out into
    success. The caller must bind the physical die and full-generation owner.
    """
    def __init__(self, physical_dies=(0,)):
        if (not isinstance(physical_dies,tuple) or not 1<=len(physical_dies)<=96
                or len(set(physical_dies))!=len(physical_dies)
                or any(type(d) is not int or d<0 for d in physical_dies)):
            raise ValueError('finite explicit physical die inventory')
        self.physical_dies=physical_dies
        self.sms = {}; self.banks = {}; self.watermarks = {}

    def acquire(self, owner, *, die, sm, bank, address, size, lease, reference,
                write, mirror_required=True):
        if (type(owner) is not tuple or len(owner) != 5 or
            any(type(x) is not int for x in owner)):
            raise ValueError('full owner tuple')
        gen, pc, seq, rank, osm = owner
        if not (0 < gen < 2**64 and 0 <= pc < 2213 and 0 < seq < 2**40
                and 0 <= rank < 96 and osm == sm and 0 <= sm < 32):
            raise ValueError('owner fields')
        if type(die) is not int or die not in self.physical_dies or type(bank) is not int or not 0 <= bank < 8:
            raise ValueError('actual physical die/bank binding')
        if (type(address) is not int or type(size) is not int or size not in (4,32,64,128)
                or address < 0 or address % size or address+size > 262144):
            raise ValueError('finite bank range')
        if (type(lease) is not int or not 0 < lease < 2**64 or
                type(reference) is not int or not 0 <= reference < 2**32 or
                type(write) is not bool or type(mirror_required) is not bool):
            raise ValueError('lease/reference/write')
        sk = (die, sm); bk = (die, sm//8, bank)
        if sk in self.sms or bk in self.banks:
            raise ValueError('finite SM/bank credit held')
        if (gen,seq) <= self.watermarks.get((die,sm),(0,0)):
            raise ValueError('stale generation/sequence')
        self.sms[sk] = dict(owner=owner, bank=bk, phase='DRAIN', write=write,
                            mask=0, required=3 if write and mirror_required else 0,
                            lease=lease, reference=reference, address=address, size=size,
                            captured_words=0,word_pending=False,words=max(1,size//32))
        self.banks[bk] = sk
        self.watermarks[die,sm] = (gen,seq)

    def event(self, owner, *, die, lease, reference, event, mirror=None, ordinal=None):
        sk = (die,owner[-1]); x = self.sms.get(sk)
        if x is None or x['owner'] != owner or x['lease'] != lease or x['reference'] != reference:
            raise ValueError('stale owner/lease/reference')
        p = x['phase']
        if event == 'all_prior_H1_sinks_drained' and p == 'DRAIN': x['phase']='ISSUE'
        elif event == 'bank_request_accepted' and p == 'ISSUE': x['phase']='CAPTURE'
        elif event == 'bank_word_request_accepted' and p == 'CAPTURE':
            if x['word_pending'] or ordinal != x['captured_words']:
                raise ValueError('one in-flight exact bank word ordinal')
            x['word_pending']=True
        elif event == 'bank_word_capture_accepted' and p == 'CAPTURE':
            if not x['word_pending'] or ordinal != x['captured_words']:
                raise ValueError('source bank word capture identity')
            x['word_pending']=False;x['captured_words']+=1
            if x['captured_words']==x['words']:
                x['phase']='MIRRORS' if x['required'] else 'VISIBLE'
        elif event == 'RF_mirror_ACK_accepted' and p == 'MIRRORS':
            if mirror not in (0,1) or x['mask'] & (1 << mirror):
                raise ValueError('distinct actual mirror ACK required')
            x['mask'] |= 1 << mirror
            if x['mask'] == x['required']: x['phase']='VISIBLE'
        elif event == 'visibility_fence_accepted' and p == 'VISIBLE': x['phase']='CONSUMER'
        elif event == 'consumer_completion_accepted' and p == 'CONSUMER': x['phase']='REVERSE'
        elif event == 'reverse_lease_grant_accepted' and p == 'REVERSE':
            del self.banks[x['bank']]; del self.sms[sk]
        else: raise ValueError('out-of-order endpoint handshake')

    def h1_combined_ACK(self, owner, *, die, lease, reference,
                        copy0_write_edge,copy1_write_edge,host_ack_valid,host_ack_ready):
        # H1 rf_service drives both mirror w_ce from the SAME write_go. There
        # is one registered host_ack_valid, not two independently timed pins.
        # Require the two actual write-edge observations AND that ACK handshake.
        if any(x is not True for x in (copy0_write_edge,copy1_write_edge,host_ack_valid,host_ack_ready)):
            raise ValueError('both copy write edges and actual combined H1 ACK')
        x=self.sms.get((die,owner[-1]))
        if (x is None or x['owner']!=owner or x['lease']!=lease or x['reference']!=reference
                or x['phase']!='MIRRORS' or x['mask']!=0):
            raise ValueError('combined ACK requires fresh matching two-copy fence')
        for copy in (0,1):
            self.event(owner,die=die,lease=lease,reference=reference,
                       event='RF_mirror_ACK_accepted',mirror=copy)

def finite_bounds(*, contenders, words, drain, word_service, mirror_ACK,
                  visibility, consumer, reverse, provenance):
    """Bound a rotating finite arbiter from bounded downstream service.

    Entries are (edges, evidence_kind, source_sha256). Source-model bounds remain
    provisional; no software event tick or default 1 edge is admissible here.
    """
    if type(contenders) is not int or not 1 <= contenders <= 256 or words not in (1,2,4):
        raise ValueError('explicit source contender inventory/word count')
    terms=dict(drain=drain,word_service=word_service,mirror_ACK=mirror_ACK,
               visibility=visibility,consumer=consumer,reverse=reverse)
    missing=[k for k,v in terms.items() if v is None]
    if missing:return dict(status='FAIL_FINITE_WAIT_BINDING',missing=missing,upper_edges=None)
    for k,v in terms.items():
        if (type(v) is not tuple or len(v)!=3 or type(v[0]) is not int or v[0]<=0
                or v[1] not in ('source_model','measured_context_SS_FF')
                or not isinstance(v[2],str) or len(v[2])!=64
                or any(c not in '0123456789abcdef' for c in v[2])):
            raise ValueError('source-pinned positive endpoint edges: '+k)
    if not isinstance(provenance,str) or not provenance:raise ValueError('source contender inventory pin')
    # Whole credit hold includes consumption/reverse; a bank cannot rotate while
    # the previous source owner still owns its line. One edge to rotate/select.
    hold=drain[0]+words*word_service[0]+mirror_ACK[0]+visibility[0]+consumer[0]+reverse[0]
    return dict(status='CONDITIONAL_FINITE_SOURCE_BOUND',contenders=contenders,
                source_contender_inventory=provenance,credit_hold_upper_edges=hold,
                arbitration_wait_upper_edges=(contenders-1)*(hold+1),
                completion_upper_edges=(contenders-1)*(hold+1)+hold,
                all_endpoint_terms_measured=all(v[1]=='measured_context_SS_FF' for v in terms.values()),
                hardware_qualified=False,
                source_terms={k:list(v) for k,v in terms.items()},
                whole_operator_coverage=False,whole_token_latency_ns=None)

def publication_directory(db, homes):
    """PC0 output identities come from real receipts, never from slot guessing."""
    directory = {}; records = []; expected = {}
    for seq,b in db.execute('select seq,value from event where journal=3 order by seq'):
        e = json.loads(zlib.decompress(b)); r=e['record']
        if 'publication' not in r: continue
        identity=r['identity']; rank=identity['rank']; version=identity['version']
        if identity['PC'] != 0 or identity['generation'] != 1 or not r['exact']:
            raise ValueError('actual PC0 publication scope')
        if r['expected_sha256'] != r['observed_sha256'] or r['publication']['pending_obligations']:
            raise ValueError('exact publication/drain')
        records.append(dict(identity=identity,payload_sha256=r['observed_sha256'],
                            terminal_events=r['publication']['events']))
        count=0
        for index in identity['home_indices']:
            h=homes[index]
            if h['version'] != version or rank not in h['rank_group'] or h['home']['class'] != 'RF':
                raise ValueError('source home identity')
            sector_first=h['home']['slot_first']*16
            n=(h['word_count']*4+31)//32
            for mirror in range(2):
                base=(h['SM']*2+mirror)*RF_SM//32+sector_first
                for k in range(n):
                    key=(rank,base+k)
                    if key in directory: raise ValueError('PC0 output home aliases')
                    directory[key]=(version,index,k,mirror)
            count += n
        expected[rank,version]=count
    if len(records) != 384 or {x['identity']['rank'] for x in records} != set(range(96)):
        raise ValueError('all96 actual four-output receipts')
    return directory,records,expected

def capture(path, source):
    if file_sha(path) != RAW_SHA: raise ValueError('actual production journal SHA')
    receipt=json.loads(source['receipt.json'])
    homes=json.loads(gzip.decompress(source['homes.json.gz']))['homes']
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro&immutable=1', uri=True)
    try:
        directory,publications,expected=publication_directory(db,homes)
        rows=[]; counts=Counter(); paired=Counter(); transactions=0
        for row in receipt['RF_journals']:
            rank=row['rank']; j=row['journal']['journal_id']; h=hashlib.sha256()
            current=None; previous_tick=0; flow=Counter(); tick_deltas=Counter(); phases=Counter()
            last_generation=0; sequence_count=0; coords={}
            for seq,blob in db.execute('select seq,value from event where journal=? order by seq',(j,)):
                if seq != sequence_count: raise ValueError('journal sequence hole')
                sequence_count+=1; raw=zlib.decompress(blob);h.update(len(raw).to_bytes(8,'little')+raw)
                e=json.loads(raw); name=e['event']; counts[name]+=1
                if e['tick'] < previous_tick or e['hardware'] is not False:
                    raise ValueError('software provenance/ordered ticks')
                previous_tick=e['tick']; identity=e['identity']
                if identity['pc'] != 0 or identity['rank'] != rank or identity['epoch'] != 1:
                    raise ValueError('PC0 exact owner')
                if name == 'request_accept':
                    if current is not None or e['generation'] <= last_generation:
                        raise ValueError('one live tag/fresh generation')
                    last_generation=e['generation']; current=dict(identity=identity,
                        generation=e['generation'],tag=e['tag'],start=e['tick'],events=[],seq=seq)
                if current is None or any(e[k] != current[k] for k in ('identity','generation','tag')):
                    raise ValueError('transaction identity held through reverse')
                current['events'].append(name)
                if name == 'software_service_phases_reserved':
                    phases.update({str(k)+':'+str(v):1 for k,v in e['phase_costs'].items()})
                if name in ('software_backing_visible','software_read_capture'):
                    current['capture']=e['tick'];current['write']=name=='software_backing_visible'
                if name == 'validated_reverse_grant':
                    write=current['write']
                    required=['request_accept']+(['write_residence_reserved'] if write else [])+[
                        'software_owned_issue','software_service_phases_reserved',
                        'software_backing_visible' if write else 'software_read_capture',
                        'consumer_accept','reverse_credit_accept','validated_reverse_grant']
                    if current['events'] != required: raise ValueError('actual full lifecycle')
                    sector=identity['sector']; version,index,offset,mirror=directory[rank,sector]
                    coordinate=rf_coordinate(sector)
                    if coordinate['SM'] != homes[index]['SM'] or coordinate['mirror'] != mirror:
                        raise ValueError('provider/home translation')
                    key=(version,index,coordinate['SM'],mirror,'write' if write else 'read')
                    flow[key]+=1;coords[key]=coordinate
                    if write: paired[rank,version,index,offset,mirror]+=1
                    tick_deltas['write' if write else 'read',e['tick']-current['start']]+=1
                    transactions+=1;current=None
            if current is not None or h.hexdigest() != row['journal']['framed_event_SHA256']:
                raise ValueError('journal framed origin/unfinished tag')
            rows.append(dict(rank=rank,journal=j,events=sequence_count,
                framed_SHA256=h.hexdigest(),peak_live_tags=1,final_live_tags=0,
                software_final_tick=previous_tick,
                provider_phase_cost_occurrences=dict(sorted(phases.items())),
                software_transaction_ticks=[dict(kind=k[0],ticks=k[1],count=v) for k,v in sorted(tick_deltas.items())],
                flows=[dict(version=k[0],home_index=k[1],SM=k[2],mirror=k[3],kind=k[4],
                            sectors32=v,last_coordinate=coords[k]) for k,v in sorted(flow.items())]))
        pairs=0
        for (rank,version,index,offset,mirror),v in paired.items():
            if v != 1 or paired[rank,version,index,offset,1-mirror] != 1:
                raise ValueError('both actual mirror write lifecycle receipts')
            if mirror==0:pairs+=1
        if pairs != sum(expected.values()) or transactions != 738816:
            raise ValueError('all actual PC0 source/home sectors')
        return dict(schema='HBM_PC0_EXACT_PUBLICATION_PROJECTION_V1',raw_journal_SHA256=RAW_SHA,
            raw_journal_bytes=Path(path).stat().st_size,transactions=transactions,
            event_counts=dict(counts),paired_mirror_write_sectors=pairs,
            copies_written=2,copies_readback=1,hardware_ACK_evidence=False,
            physical_die_translation_qualified=False,primitive_scratch_transport_qualified=False,
            rows=rows,publications=publications)
    finally: db.close()

def group_span_binding(source):
    """Join each real directed receipt to CURRENT production home references.

    The control uses a software state-fragment namespace and synthetic output
    homes. Compute the actual expected RF endpoints, report differences; never
    silently rewrite a control receipt into a production physical translation.
    """
    g=json.loads(gzip.decompress(source['group_execution.json.gz']))
    overlay=json.loads(gzip.decompress(source['group_overlay.json.gz']))
    homes=json.loads(gzip.decompress(source['homes.json.gz']))['homes']
    plan=next(p for p in overlay if p['PC']==g['PC'])
    control_source=source['group_control_fixture.py'].decode()
    if "home=dict(class_='RF',slot_first=32,vectors=2)" not in control_source:
        raise ValueError('retained control output home ABI')
    if g['actual_publication']['identity']['home_indices']!=list(range(32)):
        raise ValueError('retained directed home directory identity')
    receipts=g['actual_source_receipts'];outputs=g['output_span_receipts']
    if len(receipts)!=512 or len(outputs)!=64 or len(plan['tiles'])!=64:
        raise ValueError('complete exact64tile directed span receipts')
    rows=[];differences=0;dest_differences=0
    for ti,t in enumerate(plan['tiles']):
        output=outputs[ti]
        if output['first'] != t['output_flat_word_first'] or output['bytes']!=512 or output['pending_obligations']:
            raise ValueError('exact tile output receipt')
        expected_output=[(i,homes[i]) for i in plan['source_writes'][0]['home_indices']
                         if g['rank'] in homes[i]['rank_group'] and homes[i]['SM']==t['SM']]
        if len(expected_output)!=1:raise ValueError('unique real output home')
        di,dh=expected_output[0]
        if di!=t['SM'] or dh['home']['slot_first']!=32:dest_differences+=1
        for j,span in enumerate(t['source_spans']):
            r=receipts[ti*8+j];proof=r['source_operand_proof'];ref=proof['source_reference']
            if (r['rank']!=span['source_rank'] or r['version']!=span['source_version'] or
                    r['source_words']!=span['words'] or ref['logical_byte_offset']!=span['LOAD_flat_word_first']*4
                    or proof['payload_bytes']!=span['bytes'] or not r['software_reverse_drained']):
                raise ValueError('exact contributor source LOAD span/lease')
            source_sm=span['local_word_first']//256%32
            candidate=[(i,homes[i]) for i in plan['source_reads'][0]['home_indices']
                       if r['rank'] in homes[i]['rank_group'] and homes[i]['SM']==source_sm]
            if len(candidate)!=1:raise ValueError('unique real input home')
            si,sh=candidate[0]
            local=span['local_word_first']%256
            if local+128>sh['word_count']:raise ValueError('source span crosses RF home')
            byte_address=2*source_sm*RF_SM+sh['home']['slot_first']*512+local*4
            matches=proof['physical_byte_address']==byte_address and proof['owner']['SM']==source_sm
            if not matches:differences+=1
            rows.append(dict(tile=ti,source_rank=r['rank'],source_version=r['version'],
                source_home_index=si,source_SM=source_sm,source_slot=sh['home']['slot_first'],
                source_expected_RF_byte_address=byte_address,bytes=span['bytes'],
                source_reference=ref,lease=proof['owner']['lease'],
                observed_software_backing_address=proof['physical_byte_address'],
                observed_software_owner_SM=proof['owner']['SM'],
                physical_RF_match=matches,translation_scope=proof['translation_scope'],
                consumer_SM=t['SM'],destination_home_index=di,
                destination_RF_slot=dh['home']['slot_first'],
                destination_output_word_first=t['output_flat_word_first'],
                endpoint_route_bound=False,hardware_ACKs_bound=False))
    return dict(source_spans=rows,exact_source_span_receipts=512,tiles=64,
        source_current_RF_translation_differences=differences,
        output_current_home_index_differences_tiles=dest_differences,
        production_physical_translation_closed=False,
        source_generation=g['generation'],source_version_retired=g['source_version_retired'],
        scope='directed control source/lease evidence joined to required current homes; mismatches are implementation dependencies')

def controller_model(projection, source):
    if projection['raw_journal_SHA256'] != RAW_SHA or projection['transactions'] != 738816:
        raise ValueError('actual publication projection scope')
    constructor=json.loads(gzip.decompress(source['constructor.json.gz']))
    group=json.loads(gzip.decompress(source['group_execution.json.gz']))
    spans=group_span_binding(source)
    fields=dict(constructor['request_fields'])
    fields.update(mirror_ACK_mask=2,state=4,word_ordinal=2,full_word_pending=1,
                  completion_sink_mask=4,captured_word_count=3,
                  last_generation=64,last_endpoint_sequence=40)
    bits=sum(fields.values())
    # Existing model's RVT DFF and gate assumptions, stated rather than measured.
    gate_equivalents=2*(128+64+32)+2*18+8*3+64
    footprint=2*(bits*.2916+gate_equivalents*.3)
    source_scope=[]
    for name,m in constructor['models'].items():
        source_scope.append(dict(model=name,SMs=m['SMs'],source_geometry_fit=m['source_geometry_fit'],
            source_reserved_die_mm2=m['full_reserved_die_mm2'],
            new_RF_shared_MACs_per_cycle=0,RF_read_bytes_per_command=1024,
            RF_write_bytes_per_mirror=512,shared_bytes_per_command=64,
            L2_word_bytes_per_bank=32,L2_line_words=4,L2_banks_per_slice=8,
            RF_port_contract='existing finite2R1W; third operand serialized',
            owner_single_entry_footprint_um2=footprint,
            owner_local_reservation_um2=constructor['additive_source_wrapper']['existing_connector_reservation_um2_per_SM'],
            owner_subset_fits_local_reservation=footprint<=constructor['additive_source_wrapper']['existing_connector_reservation_um2_per_SM'],
            owner_entries_local_per_die=32,owner_entries_bank_per_die=4*8,
            bank_entry_metadata_reservation_bits=constructor['selected_request_metadata_bits']+constructor['selected_reverse_metadata_bits'],
            bank_entry_register_subset_fits=bits<=constructor['selected_request_metadata_bits']+constructor['selected_reverse_metadata_bits'],
            L2_source_controller_footprints_um2=[r['footprint_um2'] for r in m['L2_controller_slots']],
            L2_source_cut_capacities_tracks=[r['cut']['signal_capacity_tracks'] for r in m['L2_controller_slots']],
            existing_reservation_recharged=False,source_route_clock_PG_reservation_changed=False))
    return dict(schema='HBM_MATRIX_L2_OWNER_CONSTRUCTIVE_G0_V1',enabled_default=False,
        actual_PC0=dict(transactions=projection['transactions'],ranks=96,
            paired_mirror_write_sectors=projection['paired_mirror_write_sectors'],
            software_publications=len(projection['publications']),
            software_mirror_lifecycles_closed=True,hardware_mirror_ACKs_bound=False,
            source_coordinate_binding='r30 address=(2*SM+mirror)*262144+slot*512+word*32',
            rank_to_physical_die_mapping=None,all96_same_die_not_assumed=True),
        corrected_group=dict(PC=group['PC'],rank=group['rank'],tiles=group['tiles_executed'],
            source_native_sha256=group['source_native_sha256'],source_dispatch_sha256=group['source_dispatch_sha256'],
            shared_capacity_bytes=group['shared_capacity_per_SM'],
            staging_bound_bytes=group['total_operand_and_staging_bound_bytes'],
            peak_RF_vectors=group['peak_RF_vectors'],
            source_view_released=group['source_global_view_released'],
            actual_mirrored_publication=group['actual_RF_mirror_journal'],
            PC0_is_not_PC10_production_evidence=True,
            production_payload_provenance=group['production_payload_provenance']),
        corrected_group_current_source_home_join=spans,
        controller=dict(fields_bits=fields,entry_bits=bits,states=['DRAIN','ISSUE','CAPTURE','MIRRORS','VISIBLE','CONSUMER','REVERSE'],
            credits='one SM request and one bank request; hold both through reverse',
            producer_arbitration='C0/GU/KV/DS frame share same bank owner; rotating finite accepted-source grant; no bypass',
            no_unbounded_FIFO=True,no_timeout_success=True,range_policy='exclusive whole bank while range captured; reject alias even if nonoverlapping',
            mirror_policy='distinct copy0 and copy1 actual ACK acceptance before publication',
            actual_H1_ACK_adapter='one host_ack_valid&&host_ack_ready plus both copy w_ce accepted from same write_go; no invented independent ACK pins',
            bank_word_contract='one32byte word outstanding; exact ordinal accepted then captured;4word line cannot publish on first word',
            generation_policy='full64bit generation and last40bit endpoint sequence retained; dispatch sequence globally monotone per physical SM across ranks; no epoch reuse until all sinks and leases drain',
            die_inventory='explicit finite tuple up to96 dies; no implicit additional context allocated',
            mux='metadata arbitration only; existing RF payload ports,32byte bank word buffer; no new wide RF crossbar',
            area_DFF_um2_per_bit=.2916,area_gate_um2_ASSUMED=.3,placement_utilization_ASSUMED=.5,
            metadata_gate_equivalents=gate_equivalents,entry_footprint_um2=footprint),
        source_context=source_scope,
        finite_wait_contract=dict(drain_edges=None,bank_arbitration_edges=None,backend_edges=None,
            RF_mirror_ACK_edges=[None,None],consumer_edges=None,reverse_edges=None,
            stage_expression='C_drain+C_arb+C_bank_words+C_mirror_ACKs+C_visibility+C_consumer+C_reverse',
            source_leaf_edges=dict(RF_read_pair=3,RF_write_mirrors=2,shared64_read=3,shared64_write=2,L2_read128=12,L2_write128=8),
            source_leaf_excludes='arbitration, external backend stalls, consumer stalls, reverse stalls, route stages',
            software_ticks_are_hardware_edges=False,provisional_1_1_1_admitted=False,
            progress_requires='source-bound positive per-port contracts; finite queue contender count and maximum credit-hold time',
            fairness_is_not_a_latency_bound=True),
        finite_arbiter_equation=dict(contenders=None,
            hold='drain+words*word_service+mirrored_ACK+visibility+consumer+reverse',
            arbitration_wait='(actual_contenders-1)*(hold+1)',
            completion='arbitration_wait+hold',
            local_GU_source_fan_in=16,
            physical_bank_contender_inventory=None,
            external_backend_wait_satisfied_by_PC0_ticks=False),
        hardware_admitted=False,engine_build_allowed=False,whole_token_latency_ns=None,
        new_RF_I64_RMW_C0_provider_costs=0,
        missing_connections=['actual rank-to-die mapping, globally unique per-SM dispatch sequence, and simultaneous live-version conflicts',
            'matrix frame/GU row to L2 bank physical translation and provider references',
            'actual combined H1 host ACK joined to both copy write-enable acceptances and visibility fence',
            'positive endpoint hold/consumer/reverse bounds for whole operator calendar'],
        next_gate='bind exact physical owners and per-port finite waits, replay actual transactions; then contextual source implementation')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--journal',type=Path)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--verify',action='store_true')
    args=parser.parse_args();s=inputs();args.out.mkdir(parents=True,exist_ok=True)
    p=args.out/'PC0_projection.json.gz'
    if args.journal:
        projection=capture(args.journal,s)
        raw=gzip.compress(canonical(projection),mtime=0)
        if args.verify:
            if p.read_bytes()!=raw:raise ValueError('raw production journal replay differs')
        else:
            if p.exists():raise ValueError('fresh projection required')
            p.write_bytes(raw)
    else:
        b=p.read_bytes()
        if hashlib.sha256(b).hexdigest()!=PROJECTION_SHA:raise ValueError('actual projection pin')
        projection=json.loads(gzip.decompress(b))
    raw=canonical(controller_model(projection,s))+b'\n';p=args.out/'model.json'
    if args.verify:
        if p.read_bytes()!=raw:raise ValueError('model replay differs')
    else:
        if p.exists():raise ValueError('fresh model required')
        p.write_bytes(raw)
    print('PASS_ACTUAL_PC0_OWNER_MODEL_REPLAY; physical admission remains FAIL')

if __name__=='__main__': main()
