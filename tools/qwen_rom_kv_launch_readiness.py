#!/usr/bin/env python3
"""Source-state startup readiness and exact tile acceptance receipt checker.

Additive software join only. No physical readiness/CDC or RTL admission.
Actual state export is mandatory; the conditional Euclid fixture is not one.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EUCLID = 'b6adee5098803bcf6d4d1ff7c910322e440a393a'
FIELDS = [('nout',18),('tiles',18),('k',18),('wsrc',1),('wbase',24),
          ('ts',24),('ks',24),('js',24),('xbase',24),('xks',24),('xjs',24),
          ('xcs',24),('jsh',3),('split',4),('wcs',24),('round',1),
          ('obase',24),('ots',24),('ojs',24),('mmode',1),('oen',1),
          ('amax',1),('rmax',1),('mbase',24)]
assert sum(w for _,w in FIELDS) == 379


def binary(value, width):
    if not isinstance(value,str) or len(value)!=width or set(value)-{'0','1'}:
        raise ValueError('exact binary width required; X/Z are not accepted')
    return value


def instruction(fields):
    """All actual DYN-adjusted ME fields, in source MSB-first concatenation."""
    if set(fields)!=dict(FIELDS).keys():
        raise ValueError('all24 source fields required, no default or omitted bit')
    result=''
    for name,width in FIELDS:
        v=fields[name]
        if type(v) is not int or not 0<=v<1<<width:
            raise ValueError('source field aperture: '+name)
        result+=format(v,'0%db'%width)
    return result


def zero(values):
    if any(type(v) is not int or v<0 for v in values):
        raise ValueError('nonnegative actual occupancy required')
    return not any(values)


def fifo_released_empty(s):
    """Both local release and crossed on/Gray pointers, not rv==0 alone."""
    one=('wrsync','rrsync','won','ron','ronw2','wonr2')
    if any(type(s[k]) is not int for k in one):
        raise ValueError('binary FIFO release state required')
    if s['wrsync']!=3 or s['rrsync']!=3 or any(s[k]!=1 for k in one[2:]):
        return False
    for k in ('wb','rb','wg','rg','rgw2','wgr2'):
        if type(s[k]) is not int or not 0<=s[k]<4:
            raise ValueError('actual Gray/pointer state aperture')
    return (s['wb']==s['rb'] and s['wg']==s['rg']==s['rgw2']==s['wgr2']
            and s['wg']==((s['wb']>>1)^s['wb']))


def startup_ready(snapshot, causal, resources):
    """One reset/epoch startup join; never require global drain for each ME op.

    Source exports must be coherent local snapshots crossed by an acknowledged
    handshake. Software does not synchronize multibit CDC state. Four enabled
    stack copies and bridge inventory are still candidate, not connected proof.
    """
    for domain in ('stream','serial','service'):
        d=snapshot['domains'][domain]
        if type(d['released']) is not bool or type(d['acknowledged']) is not bool:
            raise ValueError('known domain control required')
        if (d['epoch']!=snapshot['epoch'] or not d['released'] or not d['acknowledged']):
            return False
    stacks=snapshot['stacks']
    if len(stacks)!=4 or {s['stack'] for s in stacks}!=set(range(4)):
        raise ValueError('all four candidate stack instances required')
    for s in stacks:
        if type(s['enabled']) is not int or type(s['fault']) is not int:
            raise ValueError('known provider control required')
        if s['enabled']!=1 or s['fault']!=0:
            return False
        if len(s['qcount'])!=32 or len(s['rcount'])!=32:
            raise ValueError('all32 source PC occupancies required')
        if not zero(s['qcount']+s['rcount']+[s[k] for k in
                    ('ingress','wr_live','wr_backed','wr_mapped','grant_valid',
                     'live_tags','owner_state','owner_held','route_held')]):
            return False
    if not snapshot['bridges'] or not all(fifo_released_empty(f) for f in snapshot['bridges']):
        return False
    serial=snapshot['serial']
    if not zero([serial[k] for k in ('active','inflight','fault')]):
        return False
    kv=snapshot['kv']
    if not zero([kv[k] for k in ('used','fl_v','boot_busy','boot_any_v','desc_pending','kvd_v','fault')]):
        return False
    if kv['adapter_idle']!=1 or kv['tail_state_bound']!=1:
        return False
    # Source live_tags can retire before reverse ACK/grant/drain: also require
    # the causal ledger and finite assembly to be empty. Never trust live_tags alone.
    debts=causal.debts()
    if not zero([debts[k] for k in ('pending_producer_rows','live_allocations',
                                  'pending_read_sectors','planned_write_sectors')]):
        return False
    if resources.tags or resources.assembly or resources.windows or resources.owner_busy:
        return False
    return True


def kv_admission(s):
    """Literal current system predicate; descriptor/data/cadence join is separate."""
    names=('kvs_ok','kv_write_drained','boot_any_v','boot_busy','desc_pending','kvd_v')
    if any(type(s[k]) is not int or s[k] not in (0,1) for k in names):
        raise ValueError('known KV admission control required')
    return bool(s['kvs_ok'] and s['kv_write_drained'] and
                not any(s[k] for k in names[2:]))


class StartupBarrier:
    """Price a registered stream join: a new sample cannot enable this edge.

    Call reset after an explicit epoch abort/quarantine receipt. This class
    cannot generate local releases or a CDC acknowledgment from a clock ratio.
    """
    def __init__(self):
        self.epoch=None
        self.ready=False
        self.last_edge=-1

    def sample(self, stream_edge, snapshot, causal, resources):
        if type(stream_edge) is not int or stream_edge!=self.last_edge+1:
            raise ValueError('consecutive stream samples required')
        if self.epoch is not None and self.epoch!=snapshot['epoch']:
            raise ValueError('epoch change needs explicit reset/abort/quarantine')
        self.epoch=snapshot['epoch']
        old=self.ready
        self.ready=startup_ready(snapshot,causal,resources)
        self.last_edge=stream_edge
        return dict(parent_domains_ready_preedge=old,
                    registered_ready_afteredge=self.ready,epoch=self.epoch)


class AcceptedInstruction:
    """Local IREG=1 pre-edge trace: request hold through the next ME edge.

    Array go&&ready is delayed BD-IREG, then tile go_q/ib_q one edge. This
    checks the local boundary; global BD distribution/ready induction is open.
    """
    def __init__(self):
        self.request=None
        self.previous=None
        self.last_edge=-1
        self.accepted=0

    def offer(self, owner, pc, fields, xl):
        if self.request is not None:
            raise ValueError('one held boundary request; drain before reuse')
        self.request=dict(owner=owner,pc=pc,ib=instruction(fields),xl=binary(xl,128),launch=None)

    def edge(self, e):
        n=e['edge']
        if type(n) is not int or n!=self.last_edge+1:
            raise ValueError('every consecutive local stream edge required')
        for k in ('rst_n','request_go','ib_go','parent_domains_ready','go_q','active','pend'):
            if type(e[k]) is not int or e[k] not in (0,1):
                raise ValueError('known binary control: '+k)
        binary(e['ib'],379);binary(e['ib_q'],379)
        binary(e['xl'],128);binary(e['xl_q'],128)
        launch=e['rst_n'] & e['request_go'] & e['parent_domains_ready']
        if e['ib_go']!=launch:
            raise ValueError('actual tile ib_go must equal source provider launch_enable')
        if not e['rst_n']:
            if self.request and self.request['launch'] is not None:
                raise ValueError('reset interrupted accepted ownership; explicit abort/quarantine required')
            self.previous=None
        elif self.previous is not None:
            if (e['go_q']!=self.previous['launch'] or
                e['ib_q']!=self.previous['ib'] or e['xl_q']!=self.previous['xl']):
                raise ValueError('actual IREG go/379bit instruction/128bit x differs from captured boundary')
        if self.request:
            r=self.request
            if e['ib']!=r['ib'] or e['xl']!=r['xl']:
                raise ValueError('owner must retain exact instruction and x through IREG acceptance')
            if launch:
                if r['launch'] is not None:
                    raise ValueError('duplicate held-request launch')
                r['launch']=n
            if e['go_q']:
                if r['launch']!=n-1 or not e['rst_n'] or not e['parent_domains_ready']:
                    raise ValueError('queued go lacks same-epoch retained readiness')
                if e['active'] or e['pend']:
                    raise ValueError('tile issuer cannot accept; ready=!active&&!pend')
                if (e['ib_q']!=r['ib'] or e['xl_q']!=r['xl'] or
                    e['owner']!=r['owner'] or e['pc']!=r['pc']):
                    raise ValueError('accepted PC/owner/full payload mismatch')
                self.accepted+=1
                self.request=None
        elif launch or e['go_q']:
            raise ValueError('launch/go lacks actual held owner')
        self.previous=dict(launch=launch,ib=e['ib'],xl=e['xl'])
        self.last_edge=n


def contract(parent_ref):
    parent=subprocess.check_output(['git','rev-parse',parent_ref],cwd=ROOT,text=True).strip()
    paths=['rtl/physical/ot_qwen_rom_reset_parent_provider.sv',
           'rtl/hdc/ot_qwen_rom_tile_context_candidate_r3_retained.sv',
           'rtl/hdc/ot_qwen_w12_matvec.sv','rtl/hdc/ot_qwen_me_array_w12.sv',
           'rtl/hdc/ot_hdc_core_vector_weight.sv','rtl/hdc/kv/ot_hdc_qwen_kv_system.sv',
           'rtl/hdc/kv/ot_hdc_qwen_kv_vector_bridge.sv',
           'rtl/model_ready_hbm_r14/ot_hbm_causal_command_provider.sv',
           'rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv',
           'rtl/model_ready_hbm_r14/ot_hbm_r14_clock_bridge.sv',
           'rtl/model_ready_hbm_r14/ot_hbm_r14_fifo2.sv',
           'rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12.sv']
    sources={p:subprocess.check_output(['git','show',parent+':'+p],cwd=ROOT,text=True) for p in paths}
    anchors={paths[0]:'parent_domains_ready',paths[1]:'else go_q <= ib_go;',
             paths[2]:'assign ready = !active && !pend;',
             paths[3]:'.d(go && ready)',paths[4]:'(kv_ok && !kvd_v)',
             paths[5]:'assign kv_ok=kvs_ok && kv_write_drained',
             paths[6]:'assign drained = used == 0 && adapter_idle && !fl_v;',
             paths[7]:'wire [6:0] qcount[0:31]',paths[8]:'live[tag_saved]<=0',
             paths[9]:'.EDGES(38)',paths[10]:'assign wr=wrsync[1]&&ronw2&&!full;',
             paths[11]:".kv_write_drained(1'b1)"}
    locations={}
    for p,a in anchors.items():
        locations[p]=[i for i,l in enumerate(sources[p].splitlines(),1) if a in l]
        if not locations[p]:raise ValueError('source changed: '+a)
    fields=', '.join('i_'+n for n,_ in FIELDS)
    actual=' '.join(sources[paths[3]].split())
    if fields not in actual:raise ValueError('379bit source concatenation changed')
    gatepath='results/uarch/qwen_rom_owned_binary_source_20261002/contract_and_remaining.json'
    raw=subprocess.check_output(['git','show',EUCLID+':'+gatepath],cwd=ROOT)
    return dict(schema='opentallas.qrom-source-owned-launch-readiness.v1',
        status='BLOCKED_ACTUAL_READY_PRODUCER_AND_CONTEXTUAL_ACCEPTANCE',parent=parent,
        source_sha256={p:hashlib.sha256(s.encode()).hexdigest() for p,s in sources.items()},
        source_anchor_lines=locations,euclid_commit=EUCLID,euclid_receipt_sha256=hashlib.sha256(raw).hexdigest(),
        euclid_conditional_gate=json.loads(raw)['literal_source_gate'],
        instruction=dict(width=379,fields_MSB_first=FIELDS,IREG=1,
            hold='Parent owner/PC, all379 instruction bits and tile128bit x held from request through local IREG consumer acceptance.',
            acceptance='Boundary launch at edgeN captures ib_q/xl_q/go_q. Source FAST issuer consumes preedge go_q atN+1 only when active=0 and pend=0.',
            go_wires='request_go is provider ib_go; receipt ib_go is actual tile input and must equal provider launch_enable. Tile itself does not gate go_q with readiness.',
            upstream='Array delays go&&ready and all379 fields byBD-IREG. No tile ready output; global safe broadcast and BD consistency need actual source induction.'),
        readiness=dict(kind='Software predicate/journal checker, not physical producer RTL',
            producer_API='StartupBarrier.sample(stream_edge, acknowledged_source_snapshot, CausalJoin, FinitePrefetchReplay); AcceptedInstruction.offer(owner,issued_pc,all24fields,x128); edge(actual_preedge_tile_snapshot)',
            startup='Register stream-domain join of acknowledged same-epoch stream/serial/service release, source FIFOs/route and prior-owner debt drain, actual tail-state binding.',
            per_instruction='Do not repeat global startup drain. KV ME issue also requires actual descriptor-bound kv_ok&&!kvd_v and current writes drained; safe visible stream window/cadence must join actual demanded state.',
            constant_is_not_receipt=True,actual_connected_producer=None,
            exact_source_kv_ok='kvs_ok && kv_write_drained && !boot_any_v && !boot_busy && !desc_pending && !kvd_v',
            bridge='Each FIFO local two-edge release plus crossed won/ron and coherent Gray-pointer acknowledgments. Shared rst_n source does not prove separate domain release or empty route.'),
        dependencies=dict(
            Euclid=['Actual accepted owner/issued-PC and complete379bit DYN-adjusted instruction, ib/ib_q/go_q plus active/pend for all1536tiles or proven source induction;128bit tile x qualification.',
                    'Retain85controls and90physical metadata endpoints;237cycle fixture is conditional only.'],
            Ampere=['Source-local service/serial/stream release and acknowledged snapshot CDC inventory, local clock phase and reset min/max/pulse/recovery/removal at exact endpoints.',
                    'Two streaming provider FFs cannot release service or serial. Price all readiness register/synchronizer/drivers and their slot/CTS/PG/cut tracks, SS60ps/FF25ps.',
                    'Retain existing service384 and tail128 macro clocks/rank once; include owner/control/assembly readiness sinks.'],
            Kepler=['Export all32PC qcount/rcount perstack plus ingress/wr_live/backed/mapped/grant, ownerstate/held/live_tags and actual bridge/route snapshots; disabled service zero counts cannot qualify.',
                    'Actual allocation/owned404bit reverseACK/grant/readerdrain receipts feed CausalJoin; no inferred producer payload.'],
            Russell=['Join actual producer/tail state, CausalJoin and finite resource journals to readiness epoch and exact demand window; no synthetic final qualification.']),
        service_slot_model='results/uarch/qwen_rom_kv_rate_risk_20261002/model_r3.json',
        readiness_logic_area=None,readiness_CDC_latency=None,complete_slot_fit=None,
        added_startup_latency='Streaming provider2edges once plus actual source local-domain release/snapshot acknowledgment and registered join latency, currently unbound. Never per-layer, never doublechargeKV reads.',
        actual_production_calendar=False,source_owned_launch_PASS=False,hardware_admitted=False,
        new_decode=False,new_PnR=False,peer_delivery='Committed for parent relay; no peer message transport exposed')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parent-ref',required=True);p.add_argument('--result',type=Path,required=True)
    a=p.parse_args();record=contract(a.parent_ref)
    with a.result.open('x') as f:json.dump(record,f,indent=2);f.write('\n')
