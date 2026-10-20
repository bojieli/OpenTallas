#!/usr/bin/env python3
"""Default-off whole-frontier join: source interfaces + actual receiver/origin receipts. Emits no K."""
import argparse, hashlib, json, re
from pathlib import Path
from shared_epoch_origin_guard import evaluate

def digest(x):return isinstance(x,str) and len(x)==64 and all(c in '0123456789abcdef'for c in x)
def endpoint(x):return isinstance(x,str) and bool(re.fullmatch(r'[\w.\[\]/]+/[\w.\[\]]+',x)) and not any(t in x.upper()for t in ['TODO','UNKNOWN','UNBOUND','PLACEHOLDER'])

def audit(packet,bindings,top,packet_ref,packet_sha):
    errors=[];reports=[]
    if not packet_ref or not digest(packet_sha):errors.append('SOURCE_PACKET_IDENTITY_MISSING')
    found=[x for x in packet.get('interfaces',[])if x.get('top')==top]
    if len(found)!=1:return dict(status='BLOCKED',qualified=False,K_emit=None,errors=['TOP_MISSING_OR_AMBIGUOUS'])
    interface=found[0];ports=[p for p in interface['ports']if p['direction']=='input'and p['kind']=='data']
    if not digest(interface.get('sha256')):errors.append('INVALID_SOURCE_RTL_HASH')
    expected={p['port']for p in ports}
    seen_native_eps=set()
    if set(bindings)!=expected:errors.append('INCOMPLETE_OR_EXTRA_WHOLE_FRONTIER_ACK')
    hashes=['upstream_origin_receipt_sha256','receiver_origin_receipt_sha256','native_receipt_sha256',
            'actual_receiver_map_sha256','placement_receipt_sha256','phase_receipt_sha256','schedule_receipt_sha256']
    for p in ports:
        name=p['port'];bad=[];b=bindings.get(name)
        if not isinstance(b,dict):reports.append(dict(port=name,errors=['MISSING_RECEIVER_ORIGIN_ACK']));continue
        identities=dict(source_packet_ref=packet_ref,source_packet_sha256=packet_sha,source_commit=packet['source_commit'],
                        top=top,source_sha256=interface['sha256'],port=name,width=p['width'],msb=p['msb'],lsb=p['lsb'],direction='input')
        for k,v in identities.items():
            if b.get(k)!=v:bad.append('SOURCE_IDENTITY:'+k)
        for k in hashes:
            if not digest(b.get(k)):bad.append('MISSING_OR_INVALID:'+k)
        for k in ['receiver_endpoint','receiver_clock_pin','receiver_reset_pin','producer_endpoint']:
            if not endpoint(b.get(k)):bad.append('MISSING_ACTUAL_ENDPOINT:'+k)
        if type(b.get('first_valid_global_edge'))is not int:bad.append('FIRST_VALID_NULL_OR_NONINTEGER')
        if type(b.get('compiled_age_edges'))is not int:bad.append('COMPILED_AGE_NULL_OR_NONINTEGER')
        slices=b.get('slices');nextbit=p['lsb'];ages=set();valids=set();origins=set()
        if not isinstance(slices,list)or not slices:bad.append('ACTUAL_RX_SLICE_MAP_MISSING');slices=[]
        for s in slices:
            nums=['payload_lsb','payload_msb','native_lsb','native_msb','native_width','age_edges','first_valid_global_edge']
            if not isinstance(s,dict)or any(type(s.get(k))is not int for k in nums):bad.append('INCOMPLETE_SLICE_MAP');continue
            if s['payload_lsb']!=nextbit or s['payload_msb']<s['payload_lsb']:bad.append('SPLIT_REORDER_OVERLAP_OR_GAP')
            width=s['payload_msb']-s['payload_lsb']+1
            if s['native_lsb']!=0 or s['native_msb']!=width-1 or s['native_width']!=width or s.get('order')!='lsb_to_msb':
                bad.append('BIT_ORDER_PADDING_OR_TRUNCATION')
            if not endpoint(s.get('receiver_endpoint'))or not digest(s.get('native_receipt_sha256'))or not digest(s.get('actual_receiver_map_sha256')):
                bad.append('SLICE_NATIVE_RECEIVER_UNBOUND')
            ep=s.get('receiver_endpoint')
            if ep in seen_native_eps:bad.append('DUPLICATE_PHYSICAL_RECEIVER')
            seen_native_eps.add(ep)
            nextbit=s['payload_msb']+1;ages.add(s['age_edges']);valids.add(s['first_valid_global_edge']);origins.add(s.get('upstream_origin_receipt_sha256'))
        if nextbit!=p['msb']+1 or p['msb']-p['lsb']+1!=p['width']:bad.append('WHOLE_WORD_COVERAGE_MISMATCH')
        if ages!={b.get('compiled_age_edges')}or valids!={b.get('first_valid_global_edge')}or origins!={b.get('upstream_origin_receipt_sha256')}:
            bad.append('COHERENT_FRONTIER_SPLIT_AGE_VALID_OR_ORIGIN')
        oc=b.get('origin_contract')
        if not isinstance(oc,dict):bad.append('ORIGIN_CONTRACT_MISSING');model=None
        else:
            model=evaluate(oc)
            if model['status']=='BLOCKED':bad.append('ORIGIN_MODEL_BLOCKED')
            if model.get('first_consumer_global_edge')!=b.get('first_valid_global_edge')or oc.get('global_source_to_consumer_edges')!=b.get('compiled_age_edges'):
                bad.append('FIRST_VALID_OR_AGE_JOIN_MISMATCH')
        reports.append(dict(port=name,width=p['width'],errors=sorted(set(bad)),origin_model=model))
    blocked=bool(errors)or any(r['errors']for r in reports)
    return dict(schema='opentallas.qwen.slice-whole-frontier-origin-join.v1',status='BLOCKED'if blocked else'MODEL_JOIN_COMPLETE_NOT_NATIVE_SIGNOFF',
                qualified=False,enabled=False,K_emit=None,top=top,source_packet_ref=packet_ref,source_packet_sha256=packet_sha,
                source_commit=packet['source_commit'],errors=errors,ports=reports)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['packet','bindings','out']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--packet-ref',required=True);p.add_argument('--top',required=True);a=p.parse_args()
    r=audit(json.loads(a.packet.read_text()),json.loads(a.bindings.read_text()),a.top,a.packet_ref,hashlib.sha256(a.packet.read_bytes()).hexdigest())
    a.out.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(dict(status=r['status'],errors=r['errors'],blocked_ports=sum(bool(x['errors'])for x in r.get('ports',[])))));return int(r['status']=='BLOCKED')
if __name__=='__main__':raise SystemExit(main())
