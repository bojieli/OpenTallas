#!/usr/bin/env python3
"""Finite opt-in capture contract; source unchanged, no physical admission."""
import argparse, collections, gzip, hashlib, json
from pathlib import Path
import dsrom_I66_stage_provider as M
ROOT=M.S.ROOT
OUT=ROOT/'results/uarch/dsrom_I66_capture_banks_20261002'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def records(p):
    with gzip.open(p,'rt') as f:
        yield from (json.loads(line) for line in f)
def mapping(m):
    if m['compiled_NP']!=4096 or m['K']!=5120 or m['rows']!=576 or m['segments']!=[[0,5120]]: raise ValueError('geometry/K grain')
    rows={}
    for seg,g,first,n,stride,start,w in m['plans']:
        if seg!=0 or not 0<=g<4096: raise ValueError('pair/segment')
        for j in range(n):
            for row in (2*(first+j*stride),2*(first+j*stride)+1):
                if row>=576: continue
                if row in rows: raise ValueError('duplicate row')
                rows[row]=g//32
    if set(rows)!=set(range(576)): raise ValueError('missing row')
    return rows

def allocation():
    phases={p['matrix_journal_ordinal']:p for p in records(M.D.OUT/'inputs/cfg_phase_directory.jsonl.gz')}
    receipt=json.loads((OUT/'inputs/extraction_receipt.json').read_text())
    subset=OUT/'inputs/selected_matrix_plans.jsonl.gz'
    if hashlib.sha256(gzip.decompress(subset.read_bytes())).hexdigest()!=receipt['raw_subset_sha256']: raise ValueError('subset extraction hash')
    plans=[]; depths={}; identities=set()
    for entry in records(OUT/'inputs/selected_matrix_plans.jsonl.gz'):
        m=entry['matrix']; p=phases[entry['matrix_journal_ordinal']]
        for a,b in [('stage','stage'),('alias','alias'),('tensor','source_tensor')]:
            if m[a]!=p[b]: raise ValueError('phase ownership')
        digest=hashlib.sha256(json.dumps(m['plans'],separators=(',',':')).encode()).hexdigest()
        if digest!=p['payload_plan_sha256'] or p['source_key_word']!=((1<<31)|m['key']): raise ValueError('phase key/plan')
        ident=(m['expert'],m['alias'].rsplit('.',1)[1]); identities.add(ident)
        rows=mapping(m); counts=collections.Counter(rows.values()); d=depths.setdefault(m['stage'],[0]*128)
        for bank,n in counts.items(): d[bank]=max(d[bank],n)
        plans.append(dict(stage=m['stage'],expert=m['expert'],alias=m['alias'],phase=p['phase'],rows=rows))
    if len(plans)!=768 or identities!={(e,w) for e in range(384) for w in ('w1','w3')}: raise ValueError('all384 W1/W3 coverage')
    for plan in plans:
        counts=collections.Counter(plan['rows'].values())
        if [counts[b] for b in range(128)]!=depths[plan['stage']]: raise ValueError('resident bank depth differs')
    return plans,depths

class Banks:
    """Candidate raw-record FIFO banks. Root wires have no generation field.
    A context switch therefore requires causal source/wire/home fences.
    """
    def __init__(self,rows,depths):
        self.rows=rows; self.depths=depths; self.queues=[[] for _ in range(128)]
        self.seen=set(); self.ports=set(); self.lease=None; self.last_read=None; self.last_capture=None
    def reserve(self,lease,edge,seats,input_visible,VM_exclusive,old_source_drained):
        if self.lease is not None or seats!=576 or not all((input_visible,VM_exclusive,old_source_drained)):
            raise ValueError('reservation/fences')
        self.queues=[[] for _ in range(128)]; self.seen=set(); self.ports=set(); self.last_read=None; self.last_capture=None
        self.lease=lease; self.reserved=edge
    def capture(self,row,root,edge,lease):
        if self.lease is None or lease!=self.lease or edge<=self.reserved: raise ValueError('lease/reserve before GO')
        if row in self.seen or self.rows.get(row)!=root: raise ValueError('duplicate/root/row')
        if (edge,root) in self.ports: raise ValueError('one/root/edge')
        if len(self.queues[root])>=self.depths[root]: raise ValueError('overflow')
        self.ports.add((edge,root)); self.seen.add(row); self.queues[root].append((row,edge)); self.last_capture=edge
    def drain(self,root,edge):
        if self.last_read is not None and edge<=self.last_read: raise ValueError('one scalar read/edge')
        if not self.queues[root] or edge<=self.queues[root][0][1]: raise ValueError('empty/NBA read')
        self.last_read=edge; return self.queues[root].pop(0)[0]
    def release(self,source_idle,delivery_fenced,causal_home_visible,provenance):
        if len(self.seen)!=576 or any(self.queues) or not all((source_idle,delivery_fenced,causal_home_visible,provenance)):
            raise ValueError('outstanding owner debt')
        self.lease=None

def local_trace(plans,depths):
    plan=next(p for p in plans if p['expert']==0 and p['alias']=='exp0.w1')
    bank=Banks(plan['rows'],depths[plan['stage']]); bank.reserve((0,0,0),59,576,True,True,True)
    writers=[]; idle=None
    for e in M.S.events('r2_PASS'):
        if e['kind']=='VM_write_accept':
            if not 398720<=e['b']<399296 or not 0<=e['b']<(1<<19): raise ValueError('AW alias/output aperture')
            bank.capture(e['b']-398720,e['a'],e['edge'],(0,0,0)); writers.append(e)
        elif e['kind']=='phase_retire': idle=e['edge']
    if len(writers)!=576 or idle!=422: raise ValueError('retained trace identity')
    peak=max(collections.Counter(e['edge'] for e in writers).values())
    # Conservative candidate starts after observed source terminal; no consumer
    # deadline is inferred from this local observer fixture.
    edge=idle+1; order=[]
    for root in range(128):
        while bank.queues[root]: order.append(bank.drain(root,edge)); edge+=1
    bank.release(True,True,True,True) # software completion oracle, NOT actual remote fence
    return dict(verdict='PASS_FINITE_LOCAL_CAPTURE_SCALAR_DRAIN',rows=len(order),peak_writers_per_edge=peak,
                first_writer=min(e['edge'] for e in writers),last_writer=max(e['edge'] for e in writers),
                source_idle=idle,reservation_model_edge=59,field_GO_source_edge=60,
                scalar_drain_first=423,scalar_drain_last=edge-1,scalar_reads_per_edge=1,
                drain_edges=576,drain_order_is_candidate=True,new_runtime=False,
                actual_remote_delivery_fence=False,actual_remote_home_visibility=False,
                full_program_consumer_deadline=None,deadline_verdict='UNBOUND',
                raw_journal_sha256=M.S.sha_raw(M.S.A/'r2_PASS/actual.jsonl.gz'))

def model():
    plans,depths=allocation(); c=M.source_contract(); trace=local_trace(plans,depths)
    stage={}
    for s,d in depths.items():
        rounded=[1<<(n-1).bit_length() for n in d]; exact=sum(d); padded=sum(rounded)
        # Raw records preserve FP32/BF16/pos/error/row; valid is included in69.
        # Control is an explicit candidate, not an existing implemented adapter.
        control=128*(3+3)+576+1+32+32+6+2+9+10+32
        stage[s]=dict(bank_depths=d,depth_histogram=dict(collections.Counter(d)),write_ports=128,
                      write_ports_per_shard=64,raw_write_bits_per_edge=128*69,
                      exact_FF_seats=exact,exact_FF_record_bits=exact*69,
                      legal_pow2_4_8_seats=padded,pow2_padding_seats=padded-exact,
                      legal_pow2_4_8_record_bits=padded*69,uniform8_seats=1024,
                      candidate_control_bits=control,
                      control_allocation=dict(fill_count=384,read_index=384,row_seen=576,
                          active=1,generation=32,user=32,stage=6,rank=2,eid=9,phase=10,xversion=32),
                      root_bank_write_address_selects=128,write_select_choice_sum=sum(d),
                      scalar_read_mux_2to1_bit_equivalents=69*(sum(n-1 for n in d)+127),
                      row_membership_compare_bits=sum(d)*16,
                      global_capture_bus=False,field_backpressure=False,
                      physical_memory_4_8_provider_available=False,
                      record_field_bits=dict(valid=1,row=16,pos=3,FP32=32,BF16=16,error=1),
                      write_context_fanout_destinations=128,write_context_fanout_per_shard=64,
                      row_seen_decode_destinations=576,
                      bank_local_write_select_2to1_bit_equivalents=69*sum(n-1 for n in d),
                      maximum_record_write_width_per_bank=69,
                      physical_cell_count_lower_bound_FF=exact*69+control,
                      FF_cell_area_mm2=None,mux_area_mm2=None,physical_slot_fit=None,
                      SS_setup_FF_hold_closed=False)
    return dict(schema=1,verdict='PASS_SYMBOLIC_BANKING_AND_LOCAL_FINITE_TRACE_ONLY',
                all384_experts_W1_W3=768,compiled_NP=4096,root_count=128,
                source_ports=c,stages=stage,local_trace=trace,
                raw_root_generation_bits=0,context_rearm='all source/wire/delivery/home visibility/provenance debts fenced; no timer substitutes',
                drain='one raw69 record per edge; source formatting preserved, planned bridge requires exclusive512bit VM read/modify/full-block ownership',
                whole_program_deadlines='X source L0.I52 and SU fence I53; actual accepted-visible producer origin and first consumer deadline unbound',
                timeout=dict(actual_default=1024,actual_default_verdict='FAIL_RETAINED_REQUESTED_TRANSPORT',
                             proposed_4096_selected=False,existing_counter_bits=32,incremental_bits_if4096=0),
                hardware_or_remote_or_token_credit=False,ECC_added=False)

def pins():
    paths=[Path(__file__),OUT/'inputs/selected_matrix_plans.jsonl.gz',OUT/'inputs/extraction_receipt.json',
           M.D.OUT/'inputs/cfg_phase_directory.jsonl.gz',M.D.OUT/'inputs/cfg_key_tables.jsonl.gz',
           ROOT/'tools/dsrom_I66_stage_provider.py', ROOT/'tools/dsrom_I66_stage_dispatch.py',
           M.S.A/'r2_PASS/actual.jsonl.gz',
           ROOT/'tools/dsrom_I66_standalone_calibration.py',
           M.D.OUT/'inputs/stage_link_tx.sv.txt',
           M.OUT/'inputs/stage_link_rx.sv.txt', M.OUT/'inputs/stage_link_endpoint.sv.txt',
           M.P.OUT/'inputs/core.sv.txt', M.P.OUT/'inputs/tile.sv.txt']
    return {str(p.relative_to(ROOT)):sha(p) for p in paths}
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--verify',action='store_true'); a=ap.parse_args()
    result=model(); result['source_pins']=pins()
    if a.verify:
        if a.out.read_bytes()!= (json.dumps(result,indent=2,sort_keys=True)+'\n').encode(): raise SystemExit('FAIL: model or source pins differ')
        print('PASS: byte-equivalent parsed model and source pins'); raise SystemExit(0)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
