#!/usr/bin/env python3
"""Finite local parity-read calendar join; no allocator or second owner ledger.

Consumes the single mirrored-padding option's source addresses/initialization
receipts. Existing owner lease identifiers are references, not new wire serials.
All timings require positive supplied profiles; no default/local-free costs.
"""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import dsrom_finite_resources as F
ROOT=Path(__file__).resolve().parents[1]
CANDIDATE='DS4096-TP4-S58-PAR2-NP2048'


def mirror_fence(fence,manifest,stage,rank,generation):
    identity={'candidate':CANDIDATE,'stage':stage,'rank':rank,'shard':1,'generation':generation,'mirror_manifest_sha256':manifest['sha256'],'source_image_revision':manifest['source_image_revision']}
    if fence.get('identity')!=identity:raise ValueError('mirror initialization owner/source generation')
    if fence.get('initialized_protected_words')!=manifest['protected_words'] or manifest['protected_words']<=0:raise ValueError('partial mirror initialization')
    if fence.get('pending_accepted_writes')!=0:raise ValueError('mirror accepted write debt')
    if not all(fence.get(k) is True for k in ('source_provenance','matching_copy_bytes','causal_backing_visibility','delivery_closed')):raise ValueError('mirror visibility/provenance fence; no timer/ACK substitute')
    return identity


def read_identity(request):
    i=request['identity']
    for key,limit in [('stage',58),('rank',4),('shard',2),('phase',1024)]:
        if type(i.get(key)) is not int or not 0<=i[key]<limit:raise ValueError('owner identity '+key)
    if i['shard']!=1:raise ValueError('this option is mirrored local shard1 parity')
    for key in ('generation','operation_sequence'):
        if type(i.get(key)) is not int or i[key]<0:raise ValueError('existing operation identity '+key)
    for key in ('owner_lease','request_nonce'):
        if not isinstance(i.get(key),str) or not i[key]:raise ValueError('external ledger reference '+key)
    if i.get('candidate')!=CANDIDATE:raise ValueError('candidate identity')
    if not request.get('source_coordinate_receipt'):raise ValueError('Nash exact option coordinate receipt required')
    digest=request.get('mirror_manifest_sha256','')
    if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError('exact mirror source manifest digest')
    for name in ('raw_address','mirrored_parity_address'):
        a=request[name]
        if (a.get('stage'),a.get('shard'))!=(i['stage'],1):raise ValueError('local provider/address owner')
        for key,limit in [('local_site',2048),('mb',2),('parity',2),('physical_row',4096)]:
            if type(a.get(key)) is not int or not 0<=a[key]<limit:raise ValueError('physical coordinate '+key)
    off=request.get('parity_data_bit')
    if type(off) is not int or off<0 or off%8 or off+8>256:raise ValueError('8 parity bits in protected256bit sidecar payload')
    return i


def groups(requests,coalesce):
    seen=set();result=[]
    for r in requests:
        i=read_identity(r);key=(i['owner_lease'],i['generation'],i['operation_sequence'],i['request_nonce'])
        if key in seen:raise ValueError('duplicate accepted child request identity')
        seen.add(key)
        # Only consecutive consumers under the same live lease can share capture.
        # No address/order compiler and no global sorting by parity word.
        match={k:i[k] for k in ('candidate','stage','rank','shard','phase','generation','operation_sequence','owner_lease')}
        signature=(json.dumps(match,sort_keys=True),json.dumps(r['mirrored_parity_address'],sort_keys=True))
        if coalesce and result and result[-1]['signature']==signature and len(result[-1]['requests'])<32:result[-1]['requests'].append(r)
        else:result.append({'signature':signature,'requests':[r]})
    return result


def price_local(requests,profile,initialization,manifest,*,coalesce=False):
    fields=['raw_read_cycles','parity_read_cycles','sidecar_SECDED_cycles','raw_ECC_cycles','deliver_consume_cycles','raw_port_bits_per_cycle','parity_port_bits_per_cycle','capture_groups','decoder_II_cycles']
    if any(type(profile.get(k)) is not int or profile[k]<=0 for k in fields):raise ValueError('positive actual/provisional port and timing profile required')
    if profile.get('evidence_kind') not in ('source_model','provisional','measured') or not profile.get('source_receipts'):raise ValueError('explicit source-bound cost evidence')
    batches=groups(requests,coalesce);specs={};resources={};totals={'raw_macro_reads':0,'protected_parity_macro_reads':0,'raw_ECC_decodes':0,'sidecar_SECDED256_plus10_decodes':0};rank_orders={};accepted_identities=[]
    for index,b in enumerate(batches):
        rs=b['requests'];i=rs[0]['identity'];rank=i['rank'];stage=i['stage'];n=len(rs)
        if any(r['mirror_manifest_sha256']!=manifest['sha256'] for r in rs):raise ValueError('read before matching initialized mirror generation')
        mirror_fence(initialization[(stage,rank,i['generation'])],manifest,stage,rank,i['generation'])
        order=rank_orders.get(rank,0);rank_orders[rank]=order+1
        portprefix=f'S{stage}.SH1';raw=portprefix+'.raw';parity=portprefix+'.mirror';decoder=portprefix+'.decode';slot=portprefix+f'.capture{order%profile["capture_groups"]}'
        for rid,kind,bandwidth in [(raw,'raw_ROM_port',profile['raw_port_bits_per_cycle']),(parity,'protected_sidecar_ROM_port',profile['parity_port_bits_per_cycle']),(decoder,'ECC_decode',None),(slot,'held_return_capture',None)]:
            if rid not in resources:
                resources[rid]={'kind':kind,'scope':'rank','domain':'streaming','ownership':portprefix,'source_receipts':profile['source_receipts'],'minimum_issue_cycles':1,'issue_interval_cycles':profile['decoder_II_cycles'] if rid==decoder else 1}
                if bandwidth is not None:resources[rid]['capacity_bits_per_cycle']=bandwidth
        # Conservative serialized paired capture/decoder/consume option. No ideal
        # parallel macro latency or decoder overlap, no inherited27cycle credit.
        portcycles=(274*n+profile['raw_port_bits_per_cycle']-1)//profile['raw_port_bits_per_cycle']+(274+profile['parity_port_bits_per_cycle']-1)//profile['parity_port_bits_per_cycle']
        complete=max(profile['decoder_II_cycles'],portcycles+n*profile['raw_read_cycles']+profile['parity_read_cycles']+profile['sidecar_SECDED_cycles']+n*(profile['raw_ECC_cycles']+profile['deliver_consume_cycles']))
        claims=[{'resource':rid,'order':order,'release':'complete','demand_bits':bits} for rid,bits in [(raw,274*n),(parity,274),(decoder,0),(slot,0)]]
        name=f'ECCgroup{index}.R{rank}'
        binding={'provider':portprefix,'calendar':{'accept_cycles':1,'complete_cycles':complete,'issue_interval_cycles':1,'completion_dependencies':[],'acceptance_dependencies':[]},'resource_coverage_receipts':profile['source_receipts'],'resource_claims':claims}
        specs[name]={'binding':binding,'period':Fraction(5,6),'previous':None,'dependencies':[],'unit':3,'collective_input_bits':0}
        totals['raw_macro_reads']+=n;totals['protected_parity_macro_reads']+=1;totals['raw_ECC_decodes']+=n;totals['sidecar_SECDED256_plus10_decodes']+=1
        accepted_identities.extend(r['identity'] for r in rs)
    completed,reservations=F.price(specs,resources,{})
    return {'schema':'opentallas.dsrom.par2.local-ECC-calendar.v1','candidate':CANDIDATE,'option':'103 exact protected sidecar pair mirrors in existing shard1 Q_ONLY padding; addresses supplied externally','coalesce_consecutive_same_lease_word':coalesce,'groups':len(batches),'counts':totals,'paired_capture_payload_upper_bits':profile['capture_groups']*((32 if coalesce else 1)*274+274),'capture_payload_scope':'per selected stage/rank option; excludes existing owner ledger, decoder FF and tags; not area or slot qualification','completed_ns':{k:[str(v) for v in times] for k,times in completed.items()},'resource_reservations':reservations,'identities':accepted_identities,'profile':profile,'macro_instances_added':0,'decoder_capture_router_cost_priced_in_area':False,'same_source_compute_order':True,'new_owner_ledger_or_wire_serial':False,'actual_provider_implemented':False,'physical_or_no_token_loss_qualified':False}


def terminal_join(request,terminal):
    """Authenticate externally retained debt, never allocate/pop a second ledger."""
    identity=read_identity(request)
    if terminal.get('identity')!=identity:raise ValueError('stale/wrong accepted provider terminal; debt remains in existing ledger')
    if terminal.get('raw_address')!=request['raw_address'] or terminal.get('mirrored_parity_address')!=request['mirrored_parity_address']:raise ValueError('paired raw/parity source identity')
    if terminal.get('mirror_manifest_sha256')!=request.get('mirror_manifest_sha256'):raise ValueError('mirror source generation changed')
    statuses=[terminal.get('sidecar_SECDED_status'),terminal.get('raw_ECC_status')]
    if any(s not in ('good','corrected','poison') for s in statuses):raise ValueError('both protected-sidecar and raw-codeword decoder terminals required')
    expected='poison' if 'poison' in statuses else 'corrected' if 'corrected' in statuses else 'good'
    if terminal.get('status')!=expected:raise ValueError('decoder poison cannot become arithmetic good')
    if terminal.get('paired_capture_consumed') is not True:raise ValueError('accepted raw/parity returns still owned')
    return {'existing_ledger_terminal_identity':identity,'arithmetic_authorized':terminal['status'] in ('good','corrected'),'poison_keeps_sticky_fault':terminal['status']=='poison','whole_owner_restart_authorized':False}
