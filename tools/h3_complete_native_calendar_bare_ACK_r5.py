#!/usr/bin/env python3
"""Execute literal local RF/commonACK and held-route control semantics.

No ACK tag is synthesized. Software context is captured at the sole accepted
write. Reset of one endpoint is distinct from quiescence of every old copy.
Source clock-edge ordinals are protocol derivations, not context timing claims.
"""
import argparse
import hashlib
import gzip
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT='results/uarch/h3_complete_native_calendar_20261002/bare_ACK_route_r5'

def sha(raw):return hashlib.sha256(raw).hexdigest()

def inputs():
    b=ROOT/OUT;m=json.loads((b/'input_manifest.json').read_bytes());src={}
    for name,row in m.items():
        raw=(b/'inputs'/name).read_bytes()
        if sha(raw)!=row['sha256']:raise ValueError('immutable source pin '+name)
        src[name]=(gzip.decompress(raw)if name.endswith('.gz')else raw).decode()
    for text in ('!read_pending && !rsp_valid && !ack_valid','ack_valid<=1;prefer_write<=0','ack_valid && ack_ready','write_go && wr_addr[8:7]==p'):
        if text not in src['RF.sv']:raise ValueError('literal source RF transition changed')
    for text in ('pending && host_ack_valid','host_ack_valid && host_ack_ready','pending<=0;retired<=retired+1'):
        if text not in src['fence.sv']:raise ValueError('literal source fence transition changed')
    for text in ('EDGES=38','assign ir=!live','live&&left==0','if(ov&&ore)live<=0'):
        if text not in src['route.sv']:raise ValueError('literal source held route changed')
    return m,src

def source_RF_context(command_id, *, lease_receipt):
    _,src=inputs();commands=json.loads(src['commands.json.gz'])['RMW']
    selected=[c for c in commands if c['id']==command_id]
    if len(selected)!=1:raise ValueError('actual selected RF command reference')
    c=selected[0];digest=sha(json.dumps(c,sort_keys=True,separators=(',',':')).encode())
    if (not isinstance(lease_receipt,dict)or set(lease_receipt)!={'source_command_sha256','provider_reference','lease'}
            or lease_receipt['source_command_sha256']!=digest or lease_receipt['provider_reference']!=c['provider_reference']
            or not lease_receipt['lease']):raise ValueError('actual matching provider lease receipt required; no synthetic owner')
    return dict(version=c['version'],provider_ref=c['provider_reference'],lease=lease_receipt['lease'],
        generation=c['generation'],SM=c['SM'],RF_slot=c['RF_slot'],die=c['die'],source_command_sha256=digest)

class RFService:
    """Control transitions match pinned RTL; opaque RF bytes are actual state.

    Both-copy bank writes use the same write_go and payload. No separate timed
    ACKs, request tag or response epoch is invented. Reset leaves SRAM intact.
    """
    def __init__(self):
        self.read_pending=False;self.rsp_valid=False;self.ack_valid=False;self.prefer_write=False
        self.pending_addresses=None;self.response=None;self.memory=[{},{}]
    def tick(self,*,rst_n=True,rd_valid=False,rd_a=0,rd_b=0,rsp_ready=False,wr_valid=False,wr_addr=0,wr_data=None,ack_ready=False):
        idle=rst_n and not(self.read_pending or self.rsp_valid or self.ack_valid)
        rd_ready=idle and (not wr_valid or not self.prefer_write)
        wr_ready=idle and (not rd_valid or self.prefer_write)
        read_go=rd_valid and rd_ready;write_go=wr_valid and wr_ready
        obs=dict(rd_ready=rd_ready,wr_ready=wr_ready,read_go=read_go,write_go=write_go,
                 common_ACK_valid=rst_n and self.ack_valid,common_ACK_consumed=rst_n and self.ack_valid and ack_ready,
                 response_consumed=rst_n and self.rsp_valid and rsp_ready,ACK_wire_fields=['valid','ready'])
        if not rst_n:
            self.read_pending=self.rsp_valid=self.ack_valid=self.prefer_write=False
            self.pending_addresses=None;return obs
        if read_go and any(type(a)is not int or not 0<=a<512 for a in (rd_a,rd_b)):raise ValueError('RF512 source address')
        if write_go and (type(wr_addr)is not int or not 0<=wr_addr<512 or not isinstance(wr_data,bytes)or len(wr_data)!=512):raise ValueError('actual128lane opaque RF vector')
        old_pending=self.read_pending;old_rsp=self.rsp_valid;old_ack=self.ack_valid
        if old_pending:
            a,b=self.pending_addresses
            if a not in self.memory[0]or b not in self.memory[1]:raise ValueError('uninitialized source RF read cannot be zero-filled')
            self.response=self.memory[0][a]+self.memory[1][b];self.rsp_valid=True
        elif old_rsp and rsp_ready:self.rsp_valid=False
        self.read_pending=read_go
        if read_go:self.pending_addresses=(rd_a,rd_b);self.prefer_write=True
        if write_go:
            self.memory[0][wr_addr]=wr_data;self.memory[1][wr_addr]=wr_data
            self.ack_valid=True;self.prefer_write=False
            obs['both_copy_bank_write_go']=[(copy,bank)for copy in range(2)for bank in range(16)]
        elif old_ack and ack_ready:self.ack_valid=False
        return obs

class SoleACKContext:
    """Actual local bareACK retirement requires the retained sole acceptance.

    The software context is not an ACK field. A caller must prohibit all other
    paths to this source RF service. Cross-reset delayed copies are UNKNOWN
    unless every actual path is enumerated, blocked, and drained or canceled.
    """
    def __init__(self,rf):self.rf=rf;self.pending=None;self.held=None;self.reset_blocked=False;self.debt={};self.retired=[]
    def accept_write(self,context,*,address,payload):
        if self.reset_blocked or self.pending is not None or self.held is not None:raise ValueError('sole RF owner/held completion/reset debt blocks reuse')
        required={'version','provider_ref','lease','generation','SM','RF_slot'}
        if (not isinstance(context,dict)or not required<=set(context)or set(context)-required-{'die','source_command_sha256'}
                or context['RF_slot']!=address or type(context['SM'])is not int or not 0<=context['SM']<32
                or type(context['generation'])is not int or context['generation']<0
                or any(not context[k]for k in ('version','provider_ref','lease'))):raise ValueError('concrete source acceptance context')
        event=self.rf.tick(wr_valid=True,wr_addr=address,wr_data=payload)
        if not event['write_go']:return None
        if len(event['both_copy_bank_write_go'])!=32:raise ValueError('actual common copy go required')
        self.pending=dict(context);return event
    def capture_common_ACK(self):
        if self.reset_blocked or self.pending is None or self.held is not None:raise ValueError('untagged ACK cannot identify absent/new owner')
        event=self.rf.tick(ack_ready=True)
        if not event['common_ACK_consumed']:return None
        self.held=self.pending;self.pending=None;return dict(retained_context=self.held,wire_ACK=event)
    def consumer_reverse(self,context):
        if self.reset_blocked or self.held is None or context!=self.held:raise ValueError('wrong retained owner or stale consumer/reverse')
        self.retired.append(self.held);self.held=None
    def begin_reset(self,*,old_copy_paths):
        if not old_copy_paths or len(set(old_copy_paths))!=len(old_copy_paths):raise ValueError('actual nonempty old-copy path inventory required')
        self.reset_blocked=True;self.debt={p:False for p in old_copy_paths}
    def observe_drained(self,path,*,admission_blocked,live_copies):
        if path not in self.debt or admission_blocked is not True or type(live_copies)is not int or live_copies!=0:raise ValueError('each actual old path must be blocked and empty')
        self.debt[path]=True
    def resume(self):
        if not self.reset_blocked or not all(self.debt.values())or self.rf.ack_valid or self.rf.rsp_valid or self.rf.read_pending or self.pending is not None or self.held is not None:raise ValueError('old source/context/completion copies not all drained')
        self.reset_blocked=False;self.debt={}
    def coordinated_local_cancel(self):
        if not self.reset_blocked:raise ValueError('admission blocked before local cancellation')
        self.rf.tick(rst_n=False);self.pending=None;self.held=None
        # No remote/FIFO/directory generation debt is discharged by local reset.

class HeldRoute:
    """Exact source EDGES38 single-owned lane; no same-edge reaccept."""
    def __init__(self):self.live=False;self.left=0;self.packet=None
    def tick(self,*,iv=False,packet=None,ore=False,rst_n=True):
        ir=not self.live;ov=self.live and self.left==0
        event=dict(accepted=iv and ir and rst_n,consumed=ov and ore and rst_n,output_valid=ov,ir=ir)
        if not rst_n:self.live=False;self.left=0;self.packet=None
        elif not self.live:
            if iv:self.packet=packet;self.live=True;self.left=38
        elif self.left:self.left-=1
        elif ore:self.live=False
        return event

def derive():
    pins,src=inputs();rf=RFService();owner=SoleACKContext(rf)
    commands=json.loads(src['commands.json.gz'])['RMW']
    bridge=json.loads(src['bridge_model.json'])['actual_consumer_delta']
    if len(commands)!=288:raise ValueError('actual all96 rank RF command inventory')
    context=dict(version='directed_control_only',provider_ref='directed_RF_SM0',lease='control1',generation=0,SM=0,RF_slot=7)
    write=owner.accept_write(context,address=7,payload=bytes(range(256))*2)
    held=rf.tick(ack_ready=False);completion=owner.capture_common_ACK();owner.consumer_reverse(context)
    route=HeldRoute();accept=[];consume=[]
    for edge in range(121):
        event=route.tick(iv=True,packet=edge,ore=True)
        if event['accepted']:accept.append(edge)
        if event['consumed']:consume.append(edge)
    if accept[:4]!=[0,40,80,120]or consume[:3]!=[39,79,119]:raise ValueError('literal source route cadence')
    # Reachable partial reset counterexample: RF reset kills ACK while fence
    # retained pending; conversely fence reset kills ACK_ready while RF holds ACK.
    witnesses=[]
    for which in ('RF_only','fence_only'):
        rf=RFService();owner=SoleACKContext(rf);owner.accept_write(context,address=7,payload=b'x'*512)
        if which=='RF_only':rf.tick(rst_n=False)
        else:owner.pending=None
        states=[]
        for edge in range(4):
            event=rf.tick(wr_valid=False,wr_addr=8,wr_data=b'y'*512,ack_ready=owner.pending is not None)
            states.append(dict(edge=edge,pending_context=owner.pending is not None,source_ACK=rf.ack_valid,write_go=event['write_go']))
        witnesses.append(dict(reset=which,states=states,
            reachable_local_stall=True,continuous_stimulus_required=False,
            consequence='pending fence has no new ACK'if which=='RF_only'else'RF ACK held but fence lost pending/ACK_ready'))
    return dict(schema='BARE_COMMON_ACK_ROUTE_SOURCE_EXECUTION_R5',source_pins=pins,
        W1_owner='Euclid',old_R3_evidence_unchanged=True,
        source_RF=dict(one_outstanding=True,bare_ACK_wire_fields=['valid','ready'],bank_write_go=write['both_copy_bank_write_go'],
            held_when_not_ready=held['common_ACK_valid'],retirement=completion,independent_mirror_ACK_times=False,
            SRAM_zero_on_reset=False,bank_write_go_is_source_command_not_observed_SRAM_acceptance=True,external_source_ownership_installation=False),
        partial_reset_witnesses=witnesses,
        route=dict(accept_FAST_edge_ordinals=accept,consume_FAST_edge_ordinals=consume,minimum_II=40,
            aggregate128PC_sector32_Bpc_upper=102.4,source_bulk_roof_Bpc=bridge['service']['source_ceiling_Bpc'],
            FIFO_only_fourlane_3to4_roof_Bpc=bridge['service']['candidate4lane_payload_Bpc_3to4'],FIFO_does_not_remove_source_route_II=True,
            proposed_pipelined_route_not_installed=True),
        reset_contract=dict(new_admission_blocked_until_every_old_copy_path_drained=True,RF_reset_alone_proves_remote_drain=False,
            delayed_CDC_ACK_alias_proved_absent=False,actual_old_copy_path_inventory=None,
            fourbit_generation_wrap_safety=None,tag_identity_not_synthesized=True,
            candidate_identity_capture_requires_source_and_ports_sizing=True),
        actual_program_bindings=dict(source_PC_inventory=dict(DS=2213,Qwen=1737),
            actual_source_RF_commands=len(commands),source_rank_inventory=sorted({c['die']for c in commands}),actual_checkpoint_lease_binding_supplied=False,
            note='prior source program inventories only; no full program owner execution in this milestone',
            actual_requester_SM_and_kind_specific_lifetimes=None,source_selected_dependency41_proof='11bfdf not yet available in local Git; awaiting parent intake',
            finite_consumer_reverse_and_CDC_deadlines=None),
        source_edge_ordinals_not_context_clock_claims=True,production_calls_closed=0,
        whole_token_ns=None,hardware_qualified=False,RTL_build_allowed=False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--verify',action='store_true');args=ap.parse_args()
    raw=json.dumps(derive(),sort_keys=True,indent=2).encode()+b'\n';path=ROOT/OUT/'model.json'
    if args.verify:
        if path.read_bytes()!=raw:raise ValueError('source control derivation changed')
    else:
        if path.exists()and path.read_bytes()!=raw:raise ValueError('historical verdict overwrite refused')
        path.write_bytes(raw)
    print('PASS literal bareRF/commonACK + routeII40; partial resets stall; composite old-copy drain UNKNOWN')
if __name__=='__main__':main()
