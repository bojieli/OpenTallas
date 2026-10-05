#!/usr/bin/env python3
"""Installed HBM handshake mechanics and separate causal ownership successor.

The PC model reproduces the existing count-only RTL, including its limitations.
The owner adapter is software validation, never installed hardware credit.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INPUT_MANIFEST_SHA256='99b550e26e68a71f981fcf8ee25170f37e7be3bab8aec5a9ab5d683db562d70f'
OUT='results/uarch/h3_complete_native_calendar_20261002/installed_services_r2'


def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def sha(x):return hashlib.sha256(x).hexdigest()


class InstalledQwenPC:
    """Source-accurate old-value credit eligibility and simultaneous returns.

    No idealization: writes have no ready; tags route but do not validate the
    outstanding request; sticky fault does not gate the combinational grant.
    """
    def __init__(self,nclients=6,max_out=16):
        if type(nclients)is not int or nclients<2 or type(max_out)is not int or max_out<1:
            raise ValueError('source finite PC geometry')
        self.nc=nclients;self.cap=max_out;self.head=0;self.counts=[0]*nclients;self.fault=False
        self.counter_bits=max_out.bit_length();self.edge=0

    def step(self,requests,*,backend_ready,read_return=None,read_ready=(),write_done=None):
        for client,request in requests.items():
            if type(client)is not int or not 0<=client<self.nc or set(request)!={'tag','write'}:
                raise ValueError('actual PC client/tag/direction')
            if type(request['tag'])is not int or not 0<=request['tag']<2**32 or type(request['write'])is not bool:
                raise ValueError('source client tag width')
        grant=next((c for i in range(self.nc) for c in [(self.head+i)%self.nc]
                    if c in requests and self.counts[c]<self.cap),None)
        taken=grant is not None and backend_ready is True
        for returned in (read_return,write_done):
            if returned is not None and (set(returned)!={'client','tag'} or type(returned['client'])is not int):
                raise ValueError('source physical return tag routing')
        rid=None if read_return is None else read_return['client']
        wid=None if write_done is None else write_done['client']
        read_take=rid is not None and 0<=rid<self.nc and rid in read_ready
        write_take=wid is not None and 0<=wid<self.nc # No write completion ready port!
        if (rid is not None and not 0<=rid<self.nc) or (wid is not None and not 0<=wid<self.nc):self.fault=True
        before=list(self.counts)
        if rid is not None and wid==rid and 0<=rid<self.nc and before[rid]<2:self.fault=True
        for c in range(self.nc):
            r=int(read_take and rid==c);w=int(write_take and wid==c);q=int(taken and grant==c)
            if (r or w) and before[c]==0:self.fault=True
            self.counts[c]=(before[c]+q-r-w)%(1<<self.counter_bits)
        if taken:self.head=(grant+1)%self.nc
        row=dict(edge=self.edge,grant=grant,request_accepted=taken,read_accepted=read_take,
                 write_completion_accepted=write_take,before=before,after=list(self.counts),fault=self.fault,
                 full_tag_generation_checked_by_installed_source=False)
        self.edge+=1
        return row

    def fairness(self,*,backend_acceptance_gap=None,credit_return_upper=None):
        for v in (backend_acceptance_gap,credit_return_upper):
            if v is not None and (type(v)is not int or v<=0):raise ValueError('positive source-bound service gap; unknown is None')
        return dict(eligible_request_other_accepted_grants_upper=self.nc-1,
            eligibility_excludes_credit_exhausted_clients=True,
            conditional_acceptance_edge_upper=None if backend_acceptance_gap is None or credit_return_upper is None else
                credit_return_upper+self.nc*backend_acceptance_gap,
            missing=[name for name,value in [('backend_acceptance_gap',backend_acceptance_gap),('credit_return_upper',credit_return_upper)] if value is None],
            bound_scope='eligible continuously asserted source request; downstream ready and credit return must be bounded',
            hardware_qualified=False)


class CausalTransportOwners:
    """Opt-in finite exact-owner adapter, not the installed count-only PC RTL.

    Hardware completion does not discharge local SRAM ACKs, visibility,
    consumer or reverse. Evidence crossing clocks must retain both ordinals.
    """
    def __init__(self,capacity):
        if type(capacity)is not int or capacity<1:raise ValueError('explicit finite owner capacity')
        self.capacity=capacity;self.live={};self.retired=set();self.events=Counter()

    def accept(self,key,identity):
        required={'generation','PC','sequence','rank','SM','lease','provider_reference','source_command_sha256','write'}
        if set(identity)!=required or not isinstance(key,tuple) or len(key)!=3:
            raise ValueError('complete source transport identity')
        if (any(type(identity[k])is not int or identity[k]<0 for k in ('generation','PC','sequence','rank','SM'))
                or identity['generation']<1 or identity['sequence']<1 or identity['SM']>=32
                or not identity['lease'] or not identity['provider_reference']
                or len(identity['source_command_sha256'])!=64 or type(identity['write'])is not bool):
            raise ValueError('finite source version/home/lease identity')
        if any(type(v)is not int or v<0 for v in key) or key[0]>=128 or key[1]>=6 or key[2]>=2**32:
            raise ValueError('installed128PC/6client/32bit tag geometry')
        if key in self.live or len(self.live)>=self.capacity:
            raise ValueError('transport owner capacity or live tag reuse')
        token=sha(canonical(dict(key=list(key),identity=identity)))
        if token in self.retired:raise ValueError('stale full generation owner reuse')
        self.live[key]=dict(identity=dict(identity),token=token,phase='BACKEND',SRAM_ACK_ref=None)
        self.events['accepted']+=1
        return token

    def event(self,key,token,name,*,SRAM_receipt=None,SRAM_ledger=None,CDC_receipt=None):
        row=self.live.get(key)
        if row is None or row['token']!=token:raise ValueError('matching exact generation/tag/reference owner required')
        phase=row['phase']
        if name=='backend_completion' and phase=='BACKEND':row['phase']='LOCAL_ACK'
        elif name=='local_SRAM_ACK' and phase=='LOCAL_ACK':
            if SRAM_ledger is None or not isinstance(SRAM_receipt,dict) or set(SRAM_receipt)!={'parent','child','binding_sha256'}:
                raise ValueError('resolved observed SRAM ledger receipt required')
            p=SRAM_ledger.bindings['parents'].get(SRAM_receipt['parent'])
            d=SRAM_ledger.bindings['children'].get(SRAM_receipt['child'])
            live=SRAM_ledger.live.get(SRAM_receipt['parent'])
            active=None if live is None else live['child']
            if (p is None or d is None or p['binding_sha256']!=SRAM_receipt['binding_sha256']
                    or d['parent']!=p['id'] or active is None or active['id']!=d['id'] or not active.get('ACK_accepted')
                    or d['source_command_sha256']!=row['identity']['source_command_sha256']
                    or d['provider_reference']!=row['identity']['provider_reference']
                    or p['lease']!=row['identity']['lease'] or d['write']!=row['identity']['write']):
                raise ValueError('source-resolved all-bank/common-ACK acceptance required')
            owner=p['owner']
            expected_owner=[row['identity'][k] for k in ('generation','PC','sequence','rank','SM')]
            if isinstance(owner,list) and owner!=expected_owner:raise ValueError('source full generation/PC/sequence/rank/SM owner mismatch')
            if isinstance(owner,dict) and any(owner[k]!=row['identity'][k] for k in ('generation','PC','rank','SM')):raise ValueError('source native parent owner mismatch')
            row['SRAM_ACK_ref']=dict(SRAM_receipt);row['SRAM_ledger']=SRAM_ledger;row['phase']='VISIBILITY'
        elif name=='visibility' and phase=='VISIBILITY':
            ref=row['SRAM_ACK_ref'];local=row['SRAM_ledger'].live.get(ref['parent'])
            if local is None or local['phase']!='CONSUMER':raise ValueError('actual source parent visibility fence not accepted')
            row['phase']='CONSUMER'
        elif name=='consumer' and phase=='CONSUMER':
            ref=row['SRAM_ACK_ref'];local=row['SRAM_ledger'].live.get(ref['parent'])
            if local is None or local['phase']!='REVERSE':raise ValueError('actual source parent consumer not accepted')
            row['phase']='REVERSE'
        elif name=='reverse' and phase=='REVERSE':
            if row['SRAM_ACK_ref']['parent'] not in row['SRAM_ledger'].retired:
                raise ValueError('actual source parent reverse still held')
            if (not isinstance(CDC_receipt,dict) or set(CDC_receipt)!={'sender_domain','sender_edge','receiver_domain','receiver_edge','token'}
                    or CDC_receipt['token']!=token or any(type(CDC_receipt[k])is not int or CDC_receipt[k]<0 for k in ('sender_edge','receiver_edge'))
                    or not CDC_receipt['sender_domain'] or not CDC_receipt['receiver_domain']):
                raise ValueError('explicit matching reverse sender/receiver CDC receipt required')
            self.retired.add(token);del self.live[key]
        else:raise ValueError('backend completion is not local visibility/consumer/reverse retirement')
        self.events[name]+=1


def inventory(source):
    if not all(x in source['system.sv'].decode() for x in ['NC=6','MAX_OUT=16','NPC!=128']):raise ValueError('actual outer128PC/6client geometry')
    pc=source['PC.sv'].decode();rf=source['RF.sv'].decode();shared=source['shared.sv'].decode()
    wrapper=source['wrapper.sv'].decode();r14=source['provider_r14.sv'].decode();tag=source['owner_r14.sv'].decode()
    checks={
        'PC_round_robin_accept':('if (req_take) rr_head' in pc and 'outstanding[candidate]<MAX_OUT' in pc),
        'PC_old_value_counter_retire':("CW'(p_wr_done_v && wr_id==c)" in pc),
        'RF_common_two_copy_ACK':('ack_valid<=1' in rf and 'u_operand_a' in rf and 'u_operand_b' in rf),
        'shared_held_done':('else if(done && done_ready) done<=0' in shared),
        'external_owner_grants_only':('rf_owner_grant[sm]' in wrapper and 'shared_owner_grant[sm]' in wrapper),
        'R14_write_commit_floor8':('cyc<wr_column[w]+8' in r14),
        'R14_tag_lookup12':('delay==11' in tag),
        'R14_input_alloc_priority':('assign ir=(state==0)&&!held&&!av' in tag),
        'R14_write_visibility_priority':('if(visible_hit)' in r14 and 'else if(return_hit)' in r14),
    }
    if not all(checks.values()):raise ValueError('installed source edge/policy mismatch')
    fields=dict(generation=64,PC=12,sequence=40,rank=7,SM=5,lease=64,provider_reference=32,
                client=3,client_tag=32,address_sector=29,phase=3,write=1,SRAM_bank_ACK_mask=32)
    entry=sum(fields.values());capacity=128*6*16
    return dict(schema='HBM_INSTALLED_SOURCE_ACK_RETIREMENT_DELTA_R2',source_checks=checks,
        source_sha256={k:sha(v) for k,v in source.items()},
        installed_Qwen_PC=dict(clients=6,PCs=128,per_client_credit=16,total_count_credit=capacity,
            source_present=True,production_enable_and_connection_unproven=True,
            per_PC_counter_and_RR_bits=6*5+3+1,request_and_return_bytes=32,
            writes_have_completion_ready=False,full_generation_or_exact_tag_match=False,
            backend_ready_upper=None,held_read_consumer_upper=None,logical_reverse_upper=None),
        installed_RF_shared=dict(SMs_per_die=32,RF_mirrors=2,RF_banks_per_copy=16,shared_banks=2,
            source_write_ACK_after_accept_offset=1,source_read_ACK_after_accept_offset=2,
            these_offsets_are_local_lower_bounds_not_backpressure_upper=True),
        R14=dict(write_commit_min_CORE_edges=8,tag_lookup_CORE_edges=12,
            producer_av_can_block_lookup=True,write_visibility_can_block_read_return=True,
            full_program_owner_gate_connected=False,clock_conversion_to_H1=None),
        minimal_source_owner_successor=dict(installed=False,entry_field_bits=fields,entry_bits=entry,
            conservative_no_sharing_context_upper=capacity,metadata_upper_bits=capacity*entry,
            provenance='full installed accepted-beat credit envelope; actual emitted DAG may narrow with source proof',
            existing_context_reuse_credited=False,
            dictionary_and_source_reference_storage_bits=None,
            lease_and_reference_fields_require_bounded_source_dictionary=True,area_and_routing_fit=None,context_SS_FF=None,
            conservative_FF_cell_area_um2_ASSUMED=capacity*entry*.2916,
            conservative_FF_footprint_mm2_ASSUMED=capacity*entry*.2916/.5/1e6,
            area_method='explicit provisional0.2916um2/FF and50percent utilization; full accepted-beat metadata envelope; not an adoption',
            required_logic=['full source owner to unique physical tag mapping before acceptance',
                'retain causal SRAM-common ACK and both-copy acceptances',
                'held write-completion capture or admitted always-captured source sink; no ready pin exists',
                'consumer then exact reverse CDC release with finite downstream terms',
                'actual C0/SIMD/matrix/KV/L2 contenders share installed owner gate']),
        physical_wait_upper=None,full_token_latency=None,installed_full_native_hardware_bridge=False,
        TP96_literal64B_rate_promoted=False,hardware_qualified=False)


def aggregate_r55(producer,continuation,checkpoint,metadata,*,available):
    """Both distinct fresh dictionaries/indexes, and one new atomic checkpoint."""
    values=[producer,continuation,checkpoint,metadata,available]
    if any(type(v)is not int or v<=0 for v in values):raise ValueError('source-priced positive phase/resource inputs required')
    required=producer+continuation+checkpoint+metadata
    return dict(required_new_bytes=required,available_bytes=available,headroom_bytes=available-required,
        storage_fits=required<=available,constructor_GO=False,production_numerical_GO=False,
        capacity_reservation_acquired=False,reason='capacity arithmetic only; R55 source/RAM/constructor proof remains required')


def main():
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');args=p.parse_args()
    base=ROOT/OUT;manifest_raw=(base/'inputs_manifest.json').read_bytes()
    if sha(manifest_raw)!=INPUT_MANIFEST_SHA256:raise ValueError('source manifest pin mismatch')
    manifest=json.loads(manifest_raw);source={}
    for name,row in manifest.items():
        raw=(base/'inputs'/name).read_bytes()
        if sha(raw)!=row['sha256'] or len(raw)!=row['bytes']:raise ValueError('source archive pin mismatch')
        source[name]=raw
    model=inventory(source);raw=json.dumps(model,sort_keys=True,indent=2).encode()+b'\n'
    if args.verify:
        if (base/'model.json').read_bytes()!=raw:raise ValueError('installed-source model replay changed')
    else:
        if (base/'model.json').exists():raise ValueError('fresh successor model required')
        (base/'model.json').write_bytes(raw)
    print('PASS installed-source ACK/credit/retirement model; full production service remains UNKNOWN')


if __name__=='__main__':main()
