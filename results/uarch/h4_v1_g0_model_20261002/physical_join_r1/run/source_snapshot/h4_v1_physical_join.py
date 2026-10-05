#!/usr/bin/env python3
"""Additive, default-off V1 physical capacity join and finite RF owner model.

This executable protocol model does not add a hardware endpoint or change any
source numerical operator. All geometry is source-specific analytical evidence.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import h4_v1_g0_model as V1

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'H1': ('6ce60f8ea4a8eb7ce809d90840415bddc5cd0cd8', 'results/uarch/full_sm_rf_service_20261002/model_final.json'),
    'Qwen_geometry': ('56506fb5bacb993107ff11f7df45f6f03363f667', 'results/uarch/qwen_hbm_interface_geometry_20261002/qwen_floorplan_r11.json'),
    'DS_geometry': ('56506fb5bacb993107ff11f7df45f6f03363f667', 'results/uarch/qwen_hbm_interface_geometry_20261002/deepseek_floorplan_r11.json'),
    'C0': (V1.C0, 'results/uarch/h4_c0_bridge_model_20261002/model.json'),
    'unified': (V1.C0, 'tools/uarch_model.py'),
    'RF': (V1.H1, 'rtl/gpu/ot_gpu_rf_service.sv'),
    'C0_owner': (V1.C0, 'tools/h4_c0_bridge.py'),
    'V1': ('f7fa8e290d419f6de3356385c0b55ded768c2090', 'results/uarch/h4_v1_g0_model_20261002/intake/run/model.json'),
}


def facts():
    blobs = {k: V1.pinned(*v) for k, v in SOURCES.items()}
    unified = blobs['unified'].decode()
    if 'Qwen HBM tier 3 (2 dies)' not in unified or 'V4.1 HBM tier 3 (96 dies)' not in unified:
        raise ValueError('unified die-count source gate')
    rf = blobs['RF'].decode()
    for token in ('!read_pending && !rsp_valid && !ack_valid', 'rd_a[8:7]', 'wr_addr[8:7]', 'if(write_go) begin ack_valid<=1'):
        if token not in rf: raise ValueError('H1 finite RF source contract changed')
    if 'ticket=(self.generation,self.pc,self.sequence,self.rank,self.SM)' not in blobs['C0_owner'].decode():
        raise ValueError('C0 owner ticket ABI changed')
    return blobs


def build():
    blobs = facts()
    h1 = json.loads(blobs['H1']); c0 = json.loads(blobs['C0']); v1 = json.loads(blobs['V1'])
    models = {}
    for name, key, count in [('Qwen', 'Qwen', 2), ('DeepSeek', 'DS', 96)]:
        geom = json.loads(blobs[key+'_geometry']); h = h1['models'][key]
        placements = [p for p in geom['macro_placements'] if p['name'].startswith('sm')]
        if {p['name'] for p in placements} != {'sm'+str(i) for i in range(32)}:
            raise ValueError('physical32SM floorplan identity gate')
        if v1['models'][name]['ranks'] != count or c0['programs'][name]['SMs_per_rank'] != 32:
            raise ValueError('compiler/C0/unified rank-SM join')
        mapping = [dict(rank=r, die=r, SM=s, instance='die%d/sm%d'%(r,s)) for r in range(count) for s in range(32)]
        # C0 includes the command latch reused by V1. H1/C0 existing SRAM and
        # provider intervals stay owned by their source models, charged once.
        logic = [h['logic_area_estimate_um2'] + c0['programs'][name]['area']['logic_um2_per_SM'] + a for a in v1['area']['logic_um2_range']]
        cap = h['existing_logic_slot_capacity_um2']; box = h['proposed_expanded_logic_rectangle_um']; outline = h['retained_element_outline_um']
        proposed = [[box[0], box[1], box[2], box[1]+math.ceil(2*a/(box[2]-box[0])/2.16)*2.16] for a in logic]
        local = v1['routing']['local_tracks_upper']; tracks = h['outline_channel_tracks']
        models[name] = dict(
            rank_to_die_SM=mapping, replicas=len(mapping), physical_floorplan_SM_instances=placements,
            mapping_scope='source32SM-per-die baseline; rank=die index; candidate floorplan identities, not installed hardened endpoints;48SM shoreline alternative excluded',
            slot=dict(existing_logic_cell_capacity_um2=cap, H1_logic_um2=h['logic_area_estimate_um2'],
                C0_incremental_logic_um2=c0['programs'][name]['area']['logic_um2_per_SM'],
                V1_incremental_logic_um2_range=v1['area']['logic_um2_range'], composed_logic_um2_range=logic,
                composed_footprint_mm2_range=[2*a/1e6 for a in logic], deficit_cell_um2_range=[a-cap for a in logic],
                existing_slot_fits_any_bound=any(a<=cap for a in logic), required_rectangle_um_range=proposed,
                rectangle_inside_retained_outline_range=[p[2]<=outline[0] and p[3]<=outline[1] for p in proposed],
                retained_service_outline_um=outline, rectangle_conflict_checked=False,
                geometry_context='H1 service outline only; die-floorplan macro shape not interchangeable',
                expanded_H1_rectangle_is_spare=False, occupancy_credit_um2=0,
                physical_slot_admitted=False),
            routing=dict(existing_outline_channel_tracks=tracks, V1_incremental_track_incidence_upper=local,
                H1_existing_track_incidence_upper=h['boundary_track_reservation_upper'],
                V1_channels_required=math.ceil(local/tracks),
                combined_channels_screen_lower_bound=math.ceil((local+h['boundary_track_reservation_upper'])/tracks),
                shared_channel_fits=False, C0_command512_already_in_V1=True,
                additional_C0_routes_unknown=True, actual_distributed_cut_allocation=None,
                basis='H1 existing M7-M9 50% track budget; incidences are screening bounds, not unique global nets; no extra layers or PG credit'),
            calendar=dict(**v1['models'][name]['critical_path'], RF_read_II=3, RF_write_II=2,
                typed_counts_owner='Dewey actual ordered C0 trace; use existing RF/highword/RMW intervals once',
                native_replacement_owner='Dewey native:OP; V1 native-only term replaces provisional entry, control remains C0'),
            opcode_hardware_coverage=[], opcode_source_semantics_count=22,
            G0_verdict='FAIL_EXISTING_COMPOSED_SLOT_AND_SHARED_CHANNEL')
    return dict(schema='opentallas.H4.V1.physical-join.v1', enabled_default=False, hardware_admitted=False,
        source_pins=[dict(name=k, commit=SOURCES[k][0], path=SOURCES[k][1], sha256=hashlib.sha256(b).hexdigest()) for k,b in blobs.items()],
        models=models, RF_contract=dict(command_credit=1, RF_transaction_credit=1,
            read_vectors_per_accept=2, write_vectors_per_accept=1, physical_write_mirrors=2,
            response_payload_B=1024, write_mirror_payload_B=1024, RF_vector_count=512,
            ticket_fields=['generation','PC','sequence','rank','SM'], generation_bits=64,
            owner_gate_state_bits=203, owner_gate_state_reserved_bits=448,
            owner_gate_state_layout=dict(ticket=128, mirror_mask=2, read_index=3, write_index=2, phase=4, stall_counter=64),
            owner_gate_state_area_recharged=False,
            owner_gate_state_basis='V1 existing256tag+128control+64state reservation; carve203bits, no duplicate latch',
            owner_held_until='all serialized reads, exact primitive completion, all write ACKs, consumer acceptance, reverse retirement',
            C0_order=['accepted','complete','mirrored_visible_ACK','consumer_accept','reverse_grant','retire'],
            missing_actual_gate='H1 arbitrates each transaction only; C0 owner gateway must mask unrelated host/matrix/SIMD throughout command',
            source_adapter='SerializedOwner below uses exact C0 ticket tuple; protocol-only model, no hardware binding',
            bounded_latency='3*read_pairs+2*write_vectors+native_ticks+C0_control+sum(response_stalls); each stall bound explicit, no timeout/drop'),
        blockers=['reserve composed H1+C0+V1 slot with actual macro/FF/OBS exclusions',
            'allocate distributed cuts including C0 routes without transferring candidate geometry contexts',
            'implement actual atomic owner gateway only after own G0 admission',
            'typed full-trace calendar join and source-exact connected V1 exception gates',
            'context SS60ps/FF25ps closure'], RTL_allowed=False)


class SerializedOwner:
    """Finite transaction/ACK model underneath the C0 command lifecycle.

    Bounded stalls are admission accounting, never a timeout freeing an owner.
    Source RF vectors are concrete9-bit homes; I64 supplies both actual vectors.
    Caller must obtain ticket and homes from C0, not invent version bindings.
    """
    def __init__(self, *, rank, SM, generation, response_stall_bound):
        if type(rank) is not int or not 0<=rank<96 or type(SM) is not int or not 0<=SM<32:
            raise ValueError('finite rank/SM')
        if type(generation) is not int or not 0<generation<2**64 or type(response_stall_bound) is not int or response_stall_bound<0:
            raise ValueError('generation and explicit finite stall bound')
        self.rank=rank; self.SM=SM; self.generation=generation; self.B=response_stall_bound
        self.owner=None; self.pending=None; self.time=0; self.last_sequence=0; self.phase='idle'
        self.events=[]; self.transactions=[]

    def _own(self,ticket):
        if ticket!=self.owner or self.owner is None: raise ValueError('stale or foreign owner')

    def accept(self,ticket,reads,writes):
        if self.owner is not None: raise ValueError('atomic owner credit busy')
        if not isinstance(ticket,tuple) or len(ticket)!=5 or any(type(t) is not int for t in ticket):raise ValueError('C0 tuple ABI')
        g,pc,seq,r,s=ticket
        if (g,r,s)!=(self.generation,self.rank,self.SM) or not 0<=pc<4096 or not self.last_sequence<seq<2**40:raise ValueError('source C0 owner identity')
        if len(reads)>5 or not 1<=len(writes)<=2 or any(type(a) is not int or not 0<=a<512 for a in list(reads)+list(writes)):raise ValueError('bounded concrete RF homes')
        self.owner=ticket; self.last_sequence=seq; self.reads=list(reads); self.writes=list(writes)
        self.read_index=0; self.write_index=0; self.phase='reading' if reads else 'compute'
        self.events.append(('accepted',ticket))

    def read(self,ticket):
        self._own(ticket)
        if self.phase!='reading' or self.pending is not None:raise ValueError('one read transaction credit')
        addresses=self.reads[self.read_index:self.read_index+2]
        self.pending=('read',self.time,tuple(addresses)); self.transactions.append(('read_accept',ticket,tuple(addresses),self.time)); return tuple(addresses)

    def return_read(self,ticket,*,stalls=0):
        self._own(ticket)
        if not self.pending or self.pending[0]!='read':raise ValueError('missing read credit')
        self._stalls(stalls); self.time+=3+stalls; self.transactions.append(('read_return',ticket,self.time)); self.read_index+=len(self.pending[2]);self.pending=None
        if self.read_index==len(self.reads):self.phase='compute'

    def _stalls(self,stalls):
        if type(stalls) is not int or not 0<=stalls<=self.B:raise ValueError('response stall bound exceeded; retain owner')

    def complete(self,ticket,*,native_ticks):
        self._own(ticket)
        if self.phase!='compute' or type(native_ticks) is not int or native_ticks<=0:raise ValueError('ordered exact primitive completion and positive cost')
        self.time+=native_ticks;self.phase='writing';self.events.append(('complete',ticket))

    def write(self,ticket):
        self._own(ticket)
        if self.phase!='writing' or self.pending is not None:raise ValueError('one write transaction credit')
        self.pending=('write',self.time,self.writes[self.write_index]);self.mask=0;self.transactions.append(('write_accept',ticket,self.pending[2],self.time));return self.pending[2]

    def ack(self,ticket,mirror,*,stalls=0):
        self._own(ticket)
        if not self.pending or self.pending[0]!='write' or type(mirror) is not int or mirror not in (0,1) or self.mask&(1<<mirror):raise ValueError('missing/duplicate mirror ACK')
        self._stalls(stalls)
        # One H1 ACK asserts both mirrors. Separate events permit checking an
        # upstream aggregator: retirement and next write wait for both proofs.
        if self.mask and stalls!=self.ack_stalls:raise ValueError('same aggregated ACK stall count required')
        self.ack_stalls=stalls;self.mask|=1<<mirror
        if self.mask==3:
            self.time+=2+stalls;self.transactions.append(('both_mirrors_ACK',ticket,self.pending[2],self.time));self.pending=None;self.write_index+=1
            if self.write_index==len(self.writes):self.phase='visible';self.events.append(('mirrored_visible_ACK',ticket))

    def consumer(self,ticket):
        self._own(ticket)
        if self.phase!='visible':raise ValueError('all mirrors and result halves not visible')
        self.phase='consumer';self.events.append(('consumer_accept',ticket))

    def retire(self,ticket,*,reverse_grant):
        self._own(ticket)
        if self.phase!='consumer' or reverse_grant is not True:raise ValueError('consumer and reverse grant required')
        self.events.extend([('reverse_grant',ticket),('retire',ticket)]);self.owner=None;self.phase='idle'

    def unrelated_request_ready(self):return self.owner is None


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--verify',action='store_true');a=ap.parse_args()
    out=Path(a.out); payload=(json.dumps(build(),sort_keys=True,indent=2)+'\n').encode()
    pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['tools/h4_v1_physical_join.py','tests/test_h4_v1_physical_join.py']}
    if a.verify:
        if (out/'model.json').read_bytes()!=payload or json.loads((out/'source_pins.json').read_bytes())!=pins:raise ValueError('physical join source/evidence mismatch')
        print('PASS_EXACT_V1_PHYSICAL_JOIN_REPLAY');return
    out.mkdir(parents=True,exist_ok=False);(out/'model.json').write_bytes(payload);(out/'source_pins.json').write_text(json.dumps(pins,sort_keys=True,indent=2)+'\n')
    (out/'Dewey_Sagan_handoff.json').write_text(json.dumps(dict(entrypoint='tools/h4_v1_physical_join.py',protocol='SerializedOwner',models={k:dict(replicas=v['replicas'],slot=v['slot'],routing=v['routing']) for k,v in build()['models'].items()},owner='C0 ticket / Dewey existing interval reconciliation',RTL_allowed=False),sort_keys=True,indent=2)+'\n')
    print('V1_PHYSICAL_JOIN_RECORDED_G0_FAIL')

if __name__=='__main__':main()
