#!/usr/bin/env python3
"""Source-bound reset quarantine model and additive opt-in controller copies."""
from pathlib import Path
import json,hashlib,argparse
import w2_nc6_mutable_protection_model as codec
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/w2_nc6_reset_quarantine_20261003'
RTL=ROOT/'rtl/experimental/w2_nc6_reset_quarantine_20261003'
PRIMARY=ROOT/'rtl/experimental/w2_nc6_primary_20261003/ot_w2_nc6_protected_completion.sv'
SECONDARY=ROOT/'rtl/experimental/w2_nc6_primary_20261003/ot_w2_nc6_coded_secondary_acyclic.sv'
class Refusal(Exception):pass
class ResetContract:
    """Independent owner debt and local quarantine; fences are authoritative inputs."""
    def __init__(self):self.quarantined=True;self.external=set();self.local=set();self.orphans=set()
    def accept(self,key):
        if self.quarantined:raise Refusal('reset-quarantine')
        if key in self.external:raise Refusal('duplicate')
        self.external.add(key);self.local.add(key)
    def reset(self):
        self.orphans|=self.local;self.local.clear();self.quarantined=True
    def consume(self,key):
        if self.quarantined or key not in self.local:raise Refusal('no-matching-live-local-debt')
        self.local.remove(key);self.external.remove(key)
    def provider_retire(self,key):
        if key not in self.orphans:raise Refusal('not-reset-orphan')
        self.orphans.remove(key);self.external.remove(key)
    def check(self):
        if self.local&self.orphans or self.external != self.local|self.orphans:raise Refusal('debt-conservation')
    def rearm(self,*,stop,provider,reverse,reset,quiet,clean=True):
        self.check()
        if not all([stop,provider,reverse,reset,quiet,clean]) or self.external or self.local or self.orphans:raise Refusal('fence-or-owned-debt')
        self.quarantined=False

def model():
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    reset_masks={str(pc):codec.seal(0,pc,132,4)^codec.seal(1,pc,132,4) for pc in range(128)}
    changed=sorted({bit for mask in reset_masks.values() for bit in range(72) if mask>>bit&1})
    price_path=ROOT/'results/uarch/w2_nc6_mutable_protection_20261003/inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json'
    facts=json.loads(price_path.read_text())['facts']
    body_um2=8*facts['NAND2x1_ASAP7_75t_R']['SS']['area_um2']+16*facts['INVx1_ASAP7_75t_R']['SS']['area_um2']
    reset_fact=facts['DFFASRHQNx1_ASAP7_75t_R']['SS']['pins']
    polarities={str(pc):dict(old_setn_bits=codec.seal(0,pc,132,4).bit_count(),new_setn_bits=codec.seal(1,pc,132,4).bit_count(),delta_reset_cap_fF=(codec.seal(1,pc,132,4).bit_count()-codec.seal(0,pc,132,4).bit_count())*(reset_fact['SETN']['cap_fF']-reset_fact['RESETN']['cap_fF'])) for pc in range(128)}
    assert changed==[0,1,2,71]
    return dict(schema='w2.reset-quarantine.v1',source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [PRIMARY,SECONDARY]},
        old_failure='r6 request1483 localreset1484 stale-backend-capture1485; externalreceipt1/localprojection0; invariant FAIL preserved',
        storage=dict(codewords=219,coded_bits=15768,added_bits=0,added_words=0,sticky_fault_global=132,secondary_local=36,payload_bits=1,reset_payload=1),
        reset=dict(opt_in='OPT_RESET_QUARANTINE=1; default0',faultword_new_reset='sealed payload1; reset clears local tables but cannot retire provider debt',changed_physical_bits=changed,reset_cell_effect='four of existing72 faultword bits invert SETN/RESETN use; no addedFF; sourcePC seal determines exact direction',
            holds='p_req_v,c_req_rdy,p_rsp_rdy,p_wr_done_ready,c_rsp_v,c_wr_done_v remain0 until fenced rearm; no normal accepted debt/publication during reset quarantine'),
        rearm=dict(required=['admission_stop','provider_fenced','reverse_fenced','reset_fenced','local_idle','CURRENT allcodewords clean','no p_rsp_v','no p_wr_done_v','no c_req_v'],causal='upstream owner supplies authoritative fences after external debits and reverse copies retire; localclean/idle is insufficient',edges=1,post_edge='next CURRENT fault0 permits first admission; normal coldrequestcalendar unchanged from this origin'),
        ports=dict(new_external_bits=0,new_internal_bits=0,quiet_ingress_inputs=8,fanout='six clientvalid+backendreadvalid+backendWRvalid feed rearm qualification only; existing fault fanout gates normal outputs'),
        control_price=dict(added_FF=0,cell_prices_sha256=sha(price_path),prospective_body_um2_perPC=body_um2,prospective_body_mm2_128PC=body_um2*128/1e6,reset_polarity_byPC=polarities,quiet_tree='eightinput OR tree7 OR2 + inverter; qualify existing idle by AND2',conservative_twoinput_mapping={'NAND2':8,'INV':16},max_added_gate_depth_bound=9,loaded_SS_FF='unmeasured, no oneedge frequency qualification; prospective rearmedge is logical protocol not loaded delay',area='22 quiet-tree cells +2 qualifier cells conservative NAND/INV mapping; exact mapped area/load and reset polarity context required'),
        conservation='external accepted receipts = local table/journal debts UNION identity-qualified reset-orphans, disjoint; only actual clientconsume or authoritative providerretirement removesreceipt',
        owner_storage='reset-orphan ledger is provider-side ownership/reference, not new W2storage; full integration must bind actual providerledger and allcopies fences, no inventedfree seat',
        positive='boot/syntheticcold positivefencedrearm before normal requests; runtime localreset outstanding receipts remainquarantined untilproviderfence',
        negative=['localclean alone cannotrearm','each missingfence blocks','held stale ingress blocks even allfencebits asserted','stale return cannotconsume orphan','drop orphan failsconservation','samekey ABA admission blocked beforeallcopies retirement'],
        latency=dict(healthy_request_II_same_client=19,healthy_different_client_prospective_II=10,repair_II=9,reset_rearm_edges=1,fence_wait='actual provider retirement bound external; no timer/run cap'),
        claims=dict(runtime=False,physical=False,system_reset_safe=False))

def sources():
    p=PRIMARY.read_text();s=SECONDARY.read_text()
    p=p.replace('module ot_w2_nc6_protected_completion #','module ot_w2_nc6_protected_completion_reset_quarantine #')
    p=p.replace('parameter integer OPT_EXACT=0, NC=6','parameter integer OPT_EXACT=0, OPT_RESET_QUARANTINE=0, NC=6')
    p=p.replace('ot_w2_nc6_coded_secondary_acyclic #(.OPT_PROTECTION(OPT_EXACT),.PC_ID(PC_ID))','ot_w2_nc6_coded_secondary_reset_quarantine #(.OPT_PROTECTION(OPT_EXACT),.OPT_RESET_QUARANTINE(OPT_RESET_QUARANTINE),.PC_ID(PC_ID))')
    p=p.replace('.local_other_idle(core_idle)', '.local_other_idle(core_idle&&(!OPT_RESET_QUARANTINE||(!(|c_req_v)&&!p_rsp_v&&!p_wr_done_v)))')
    s=s.replace('module ot_w2_nc6_coded_secondary_acyclic #','module ot_w2_nc6_coded_secondary_reset_quarantine #')
    s=s.replace('parameter integer OPT_PROTECTION=0,','parameter integer OPT_PROTECTION=0, OPT_RESET_QUARANTINE=0,')
    before="cw[w]<=encode_payload(0,10'(global_index(w)),3'(kind_of(w)));"
    assert before in s
    s=s.replace(before,"cw[w]<=encode_payload((OPT_RESET_QUARANTINE!=0&&global_index(w)==132)?44'd1:44'd0,10'(global_index(w)),3'(kind_of(w)));")
    return {'ot_w2_nc6_protected_completion_reset_quarantine.sv':p,'ot_w2_nc6_coded_secondary_reset_quarantine.sv':s}
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--emit',action='store_true');o=a.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    # Model written before RTL emission. Original generators/source remain untouched.
    (OUT/'model.json').write_text(json.dumps(model(),sort_keys=True,indent=2)+'\n')
    if o.emit:
        RTL.mkdir(parents=True,exist_ok=True)
        for name,source in sources().items():(RTL/name).write_text(source)
