#!/usr/bin/env python3
"""Connected, finite PC completion/ACK owner design; model before RTL.

This opt-in design changes the installed count-only retirement connection.
It never attributes its executable state machine to installed hardware.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]/'results/uarch/h4_hbm_pc_completion_owner_20261003'
PIN='a5dda94f212cd12ecd9e557f702f21851ec5b705e96ead6eb44f7451d7877d62'
TERMS=('reserve','completion_match','completion_capture','dispatch','local_ACK','visibility','consumer','reverse_match','credit_release')

def require(value,why):
    if not value:raise ValueError(why)
def canonical(value):return (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
def inputs():
    raw=(BASE/'input_manifest.json').read_bytes();require(hashlib.sha256(raw).hexdigest()==PIN,'hard manifest pin');out={}
    for row in json.loads(raw)['inputs']:
        p=(BASE/row['archive']).resolve();require(p.is_relative_to((BASE/'inputs').resolve()),'archive containment')
        data=p.read_bytes();require(len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],'exact input')
        out[p.name]=data
    return out

class LocalACKOwners:
    """One shared32SM RF/shared lease directory for all128PCs."""
    def __init__(self):self.live={}

class CompletionOwner:
    """One PC,96 reserved contexts; source-sized no-ready capture and held ACK.

    Physical client tag is generation25:slot7; outer client3 remains intact.
    Reset/reuse requires external quiescence; this design never wraps tags.
    A request is exposed to backend only after its context reservation edge.
    """
    def __init__(self,pc,*,local_owners):
        require(type(pc)is int and 0<=pc<128,'actual PC');self.pc=pc
        require(isinstance(local_owners,LocalACKOwners),'shared physical SM ACK owner directory required')
        self.rows={};self.generations=[0]*96;self.local=local_owners.live;self.fault=False
    def reserve(self,client,original_tag,identity,*,write):
        require(type(client)is int and 0<=client<6,'source client')
        require(type(original_tag)is int and 0<=original_tag<2**32,'original client tag')
        widths={'generation':64,'sequence':40,'rank':7,'SM':5,'lease':64,'provider_reference':32,'sector':29,'address':32,'local_address':10}
        require(set(identity)==set(widths)|{'source_command_sha256','provider_sha256'},'complete bounded provenance')
        for k,w in widths.items():require(type(identity[k])is int and 0<=identity[k]<2**w,'bounded '+k)
        require(identity['generation']>0 and identity['lease']>0,'live generation/lease')
        require(identity['address']&127==self.pc,'installed exact address-to-PC low7 selection')
        for k in ('source_command_sha256','provider_sha256'):
            require(isinstance(identity[k],str) and len(identity[k])==64 and all(c in '0123456789abcdef' for c in identity[k]),'exact '+k)
        require(type(write)is bool,'direction')
        slot=next((s for s in range(client*16,(client+1)*16) if s not in self.rows and self.generations[s]<2**25-1),None)
        require(slot is not None,'finite client credit or generation exhausted; no wrap')
        self.generations[slot]+=1;tag=(self.generations[slot]<<7)|slot
        self.rows[slot]=dict(client=client,tag=tag,original_tag=original_tag,identity=dict(identity),write=write,phase='BACKEND',data=None)
        return (client<<32)|tag
    def resolve(self,physical_tag):
        require(type(physical_tag)is int and 0<=physical_tag<2**35,'physical tag width')
        slot=physical_tag&127;row=self.rows.get(slot)
        if row is None or physical_tag>>32!=row['client'] or physical_tag&0xffffffff!=row['tag']:
            self.fault=True;raise ValueError('unmatched slot/client/generation; no credit retired')
        return slot,row
    def capture(self,physical_tag,*,write,data=None):
        slot,row=self.resolve(physical_tag)
        if row['phase']!='BACKEND' or type(write)is not bool or row['write']!=write:
            self.fault=True;raise ValueError('duplicate or wrong-direction completion')
        require((write and data is None) or (not write and type(data)is bytes and len(data)==32),'read capture32B/write done has no payload')
        row['data']=data;row['phase']='CAPTURED'
        return row['original_tag']
    def local_issue(self,physical_tag,kind,*,sink_ready=True):
        slot,row=self.resolve(physical_tag);require(kind in ('RF','shared'),'actual local sink')
        require(kind!='RF' or row['identity']['local_address']<512,'source RF512 vector bound')
        require(type(sink_ready)is bool,'actual downstream ready')
        sm=row['identity']['SM'];key=(sm,kind)
        require(row['phase']=='CAPTURED' and key not in self.local,'held local owner/reserved capture')
        # Installed RF/shared admit one local operation while ACK/done held.
        if not sink_ready:return False
        self.local[key]=(self.pc,physical_tag);row['phase']='LOCAL_ACK';return True
    def local_ack(self,sm,kind,*,valid,ready,physical_tag):
        require(type(valid)is bool and type(ready)is bool,'actual handshake booleans')
        slot,row=self.resolve(physical_tag);key=(sm,kind)
        require(self.local.get(key)==(self.pc,physical_tag) and row['phase']=='LOCAL_ACK','ACK belongs to held request owner')
        if not(valid and ready):return False
        row['phase']='VISIBILITY';row['common_copy_mask']=3 if kind=='RF' else 1;del self.local[key];return True
    def advance(self,physical_tag,event,*,identity):
        slot,row=self.resolve(physical_tag);require(identity==row['identity'],'exact provenance/lease match')
        transitions={'visibility':('VISIBILITY','CONSUMER'),'consumer':('CONSUMER','REVERSE'),'reverse':('REVERSE','RELEASE')}
        require(event in transitions and row['phase']==transitions[event][0],'causal local ACK/fence/consumer/reverse order')
        row['phase']=transitions[event][1]
    def release(self,physical_tag,*,reverse_valid,reverse_ready):
        slot,row=self.resolve(physical_tag)
        require(row['phase']=='RELEASE','backend completion never returns causal credit')
        require(type(reverse_valid)is bool and type(reverse_ready)is bool,'reverse CDC acceptance handshake')
        if not(reverse_valid and reverse_ready):return False
        del self.rows[slot];return True


def storage_row(payload_bits):
    """Conservative protected FF implementation; no unpriced SRAM substitution.

    64bit SECDED codewords,8 checkbits; padded finalword. Encoding/decoding
    upper circuit budget768 two-input gate equivalents/word, ASSUMED.
    """
    words=math.ceil(payload_bits/64)
    return dict(payload_bits=payload_bits,words=words,protected_bits=words*72,
                ECC_gate_equivalents_ASSUMED=words*768)

def model():
    src=inputs();pc=src['PC.sv'].decode();rf=src['RF.sv'].decode();system=src['system.sv'].decode()
    require("CW'(p_wr_done_v && wr_id==c)" in pc and 'p_wr_done_rdy' not in pc,'installed unmatched no-ready source')
    require('else if(ack_valid && ack_ready) ack_valid<=0' in rf,'installed held common RF ACK')
    require('NC=6' in system and 'MAX_OUT=16' in system and 'NPC!=128' in system,'source geometry')
    require('n_sm = 32' in src['uarch_model.py'].decode(),'unified32SM context')
    fields={'generation':64,'PC':7,'sequence':40,'rank':7,'SM':5,'lease':64,'provider_reference':32,
            'client':3,'original_client_tag':32,'sector':29,'address':32,'local_address':10,'write':1,'phase':3,'SRAM_bank_mask':32}
    # Fixed full provenance prevents an unbounded dictionary hiding behind32bit handles.
    storage={'owner_metadata':storage_row(sum(fields.values())),
             'provenance':storage_row(512), 'slot_generation':storage_row(25),
             'read_payload':storage_row(256), 'read_capture_flag':storage_row(1),
             'write_capture_flag':storage_row(1),'causal_state':storage_row(8)}
    per_entry=sum(r['protected_bits'] for r in storage.values());entries=128*96
    # One RF and one shared held owner perSM; no ready pulse is detached from its request.
    shadow_identity_bits=35+7+64+64+5+1+3+2+512+10
    shadows=storage_row(shadow_identity_bits)
    local_staging_RF=storage_row(4096+16*35+16+5)
    local_staging_shared=storage_row(512+2*35+2+2)
    queues=storage_row(sum(fields.values())+512+35+256+8) # ACK/fence/reverse request held, one of each perPC
    arb=storage_row(2+6*5+3+1)
    bits=entries*per_entry+64*shadows['protected_bits']+128*4*queues['protected_bits']+128*arb['protected_bits']+32*(local_staging_RF['protected_bits']+local_staging_shared['protected_bits'])
    ecc=entries*sum(r['ECC_gate_equivalents_ASSUMED'] for r in storage.values())+64*shadows['ECC_gate_equivalents_ASSUMED']+128*4*queues['ECC_gate_equivalents_ASSUMED']+128*arb['ECC_gate_equivalents_ASSUMED']+32*(local_staging_RF['ECC_gate_equivalents_ASSUMED']+local_staging_shared['ECC_gate_equivalents_ASSUMED'])
    # Metadata3readmuxes, provenance1dispatchmux, data1dispatchmux/PC.
    mux=128*(96-1)*(3*storage['owner_metadata']['protected_bits']+storage['provenance']['protected_bits']+storage['read_payload']['protected_bits'])
    compare=128*2*(35*2+7*2)+128*6*16*25*2
    area=(bits*.2916+(ecc+mux+compare)*.3)/.5/1e6
    context=json.loads(gzip.decompress(src['context_geometry.json.gz']))
    context_join={name:dict(retained_SMs=v['SMs'],retained_reserved_die_mm2=v['full_reserved_die_mm2'],
        retained_clock_contacts=v['clock_single_contacts'],retained_cut_count=v['existing_cut_count'],
        unallocated_candidate_area_mm2_ASSUMED=area,retained_plus_unallocated_screen_mm2=v['full_reserved_die_mm2']+area,
        extra_clock_sinks=bits,new_clock_PG_current_upper=None,existing_contacts_do_not_cover_new_FFs=True,
        retained_cuts_do_not_admit_new_endpoint_buses=True,fit=False) for name,v in context['models'].items()}
    return dict(schema='HBM_CONNECTED_PC_COMPLETION_ACK_OWNER_G0_R1',source_sha256={k:hashlib.sha256(v).hexdigest() for k,v in src.items()},
        status='CONNECTED_DESIGN_SIZED_CALENDAR_PHYSICAL_ALLOCATION_BLOCKED',design_opt_in=True,
        scope='both HBM models;128PC envelope source-bound to Qwen installed services; DS adapter/geometry must be separately matched',
        unified_model_join=dict(source='tools/uarch_model.py',source_sha256=hashlib.sha256(src['uarch_model.py']).hexdigest(),SMs=32,
            model_keys=['qwen','v41'],component_key='PC_completion_ACK_causal_owner',automatic_latency_delta=False),
        source_change=dict(request='reserve context before p_req_v; physical tag client3:gen25:slot7; retain original32bit client tag',
            completion='match exact tag and direction; indexed reserved sink always captures valid write done, duplicate/unmatched faults without retire',
            held_client_completion='new c_wr_done_ready accepts held restored original tag; backend p_wr_done still no-ready and captured independently; read capture held through c_rsp_ready',
            ACK='RF common two-copy ACK/shared done matched to held local accepted-request owner; valid/ready required',
            retire='replace installed rsp/write counter decrement with exact post-consumer reverse grant',
            generation='no modulo wrap; exhaustion refuses new request; reset requires externally proven quiescence'),
        context=dict(PCs=128,clients_per_PC=6,credit_per_client=16,entries=entries,entry_fields=fields,storage_rows=storage,
            protected_bits_per_entry=per_entry,held_local_owners=64,held_local_row=shadows,RF_parent_assembly_row=local_staging_RF,shared_parent_assembly_row=local_staging_shared,
            source_parent_grouping_bound='one4096bit RF vector holds16sectors; one512bit shared beat holds2sectors; actual child->parent source journal required',
            assembly_dataflow_installed=False,
            held_control_queues_per_PC=4,held_control_queue_row=queues,arbiter_row=arb),
        storage_bits_per_die=bits,protected_FF_cell_area_um2_ASSUMED=bits*.2916,
        ECC_gate_equivalents_ASSUMED=ecc,mux_gate_equivalents_ASSUMED=mux,compare_gate_equivalents_ASSUMED=compare,
        footprint_mm2_per_die_ASSUMED=area,area_screen_only=True,existing_R2_envelope_replaced_not_added_twice=True,
        ports=dict(metadata_reads_per_PC=3,metadata_writes_per_PC=1,
            read_completion_capture_ports_per_PC=1,write_completion_capture_ports_per_PC=1,
            capture_flag_write_ports_per_plane=2,metadata_dispatch_shares_control_read_port=True,
            request_valid_ready_bits=2,read_valid_ready_bits=2,write_done_valid_bits=1,
            reverse_valid_ready_bits=2,common_ACK_valid_ready_bits=2,
            physical_read_port_bits=291,physical_write_done_port_bits=35,request_port_bits=324,
            proposed_client_write_done_payload_bits=32,proposed_client_write_done_valid_ready_bits=2,
            per_PC_capture_max_bytes_per_edge=32,local_RF_payload_bits=4096,local_RF_pair_response_bits=8192,shared_payload_bits=512,
            held_control_message_bits=sum(fields.values())+512+35+256+8,proposed_reverse_port_bits=35,
            ECC_implementation='protected FF banks, separate completion planes; ECC decode/update are budgeted, not measured'),
        finite_arbitration=dict(proposed=True,installed=False,control_classes=['reserve','dispatch','local_ACK_fence_consumer','reverse'],
            acceptance='one metadata update/PC/edge with cyclic4class arbitration; each held queue oneentry; completion planes independent',
            contention='other accepted control updates<=3; downstream grant gap still requires source-bound interval',
            client_request='existing eligible6client round robin; no admit without reserved free context',
            ACK_resource='at most one owner per SM and RF/shared sink; shared across PCs, must not instantiate64 shadows perPC'),
        latency=dict(source_local_RF_write_ACK_min_edges=1,source_local_RF_read_ACK_min_edges=2,
            proposed_pipeline_edges={'reserve':2,'completion_match':2,'completion_capture':1,'dispatch':2,'local_ACK':2,
                'visibility':1,'consumer':1,'reverse_match':2,'credit_release':1},
            proposals_are_not_measured_SS_FF=True,domain='streaming1.2GHz; exact CDC and serial0.9GHz dependency crossings separately required',
            event_keys=list(TERMS),per_operator_composed_ns=None,whole_token_ns=None,
            required_lease_intervals=['reservation->backend capture','capture->local dispatch','local issue->common ACK accepted',
                'ACK->visibility','visibility->consumer','consumer->matching reverse acceptance','slot reuse after credit release']),
        physical=dict(source_bound_retained_context=context_join,complete32SM_slot_allocation=None,clock_PG_via_cut_allocation=None,tracks_capacity=None,
            endpoint_cuts_bits={'PC_backend_read':291,'PC_backend_write_done':35,'PC_request':324,'SM_common_ACK_owner':35,'reverse':35},
            SRAM_macro_reuse_credited=False,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25),
        prerequisites=['emitted contender and lease intervals matched to exact source event IDs','protected storage/logic full-context slot, clock/PG and cut allocation',
            'bounded ECC and owner mux stage timing at target; simultaneous completion and control ports verified'],
        installed_source=False,hardware_admitted=False,engine_build_ready=False)


def compose_intervals(rows):
    """Each cost occurrence charged once; unknown/missing IDs never zero-fill.

    Input is a proposed physical calendar, not a claim generated from software
    ticks. Independent occurrences must have distinct IDs; critical paths must
    be emitted by the calendar, not reconstructed by serializing all events.
    """
    seen={};source_sha=model()['source_sha256']['PC.sv']
    for row in rows:
        require(set(row)=={'id','event','operator','PC','lease','start_ns','end_ns','source_sha256'},'exact interval ABI')
        require(row['event'] in TERMS and isinstance(row['id'],str) and bool(row['id']),'source event ID')
        require(type(row['PC'])is int and 0<=row['PC']<128 and row['lease'] and row['operator'],'real owner lease')
        require(type(row['start_ns'])in (int,float) and type(row['end_ns'])in (int,float) and math.isfinite(row['start_ns']) and math.isfinite(row['end_ns']) and 0<=row['start_ns']<row['end_ns'],'positive finite interval')
        require(row['source_sha256']==source_sha,'installed source binding')
        require(row['id'] not in seen or row==seen[row['id']],'one occurrence cannot change cost')
        seen[row['id']]=row
    groups={}
    for row in seen.values():groups.setdefault((row['operator'],row['PC'],row['lease']),[]).append(row)
    require(bool(groups),'no empty calendar admitted')
    for key,events in groups.items():
        require(len(events)==len(TERMS) and set(e['event'] for e in events)==set(TERMS),'complete connected owner cost terms')
        ordered=sorted(events,key=lambda r:TERMS.index(r['event']))
        require(all(a['end_ns']<=b['start_ns'] for a,b in zip(ordered,ordered[1:])),'causal emitted owner intervals')
    return dict(unique_occurrences=len(seen),groups=len(groups),proposed_occupied_ns=sum(r['end_ns']-r['start_ns'] for r in seen.values()),
                composed_critical_path_ns=None,hardware_admitted=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--verify',action='store_true');a=p.parse_args();raw=canonical(model())
    if a.verify:require((BASE/'model.json').read_bytes()==raw,'byte-exact model replay');print('PASS connected completion-owner model replay')
    else:require(a.output is not None,'explicit output');a.output.mkdir(parents=True,exist_ok=True);(a.output/'model.json').write_bytes(raw)
if __name__=='__main__':main()
