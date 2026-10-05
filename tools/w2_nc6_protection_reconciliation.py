#!/usr/bin/env python3
"""Executable row ownership reference and prospective NC6 protected calendar.

No engine RTL admission. Reference objects are model state, NOT added hardware.
All hardware records refer to the b846 189-word inventory.
"""
from dataclasses import dataclass
import hashlib,json,argparse
from pathlib import Path
import w2_nc6_mutable_protection_model as codec
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/w2_nc6_protection_reconciliation_20261003'
SOURCE=ROOT/'rtl/experimental/w2_nc6_completion_20261003/ot_hdc_qwen_pc_exact_completion.sv'
SHA='7230273667d61d7c87e67f93cff39523420a00913b40b76b03ae76e849ee3e94'
FREE,ISSUED,RD_HELD,WR_HELD=range(4)

class Refusal(Exception):pass

@dataclass
class Journal:
    row:int
    before:int
    after:int
    operation:str
    due:int

class Ledger:
    """Finite transactional reference. Helpers/sets are verification state only.

    Rows are actual sealed words. At most nine prepared journals exist. Lock
    acquisition must be a coded write before acceptance; this class exposes
    that boundary explicitly rather than treating a Python lock as zero-time.
    """
    def __init__(self,pc=0):
        codec.check(pc,7);self.pc=pc;self.edge=0;self.fault=False
        self.rows=[codec.seal(0,pc,i,0) for i in range(96)]
        self.journals=[];self.reserved=set();self.queries={};self.corrections={}
        self.owner_fenced=False

    @staticmethod
    def pack(state,tag=0,gen=0,direction=0,version=0,lock=0):
        return (codec.check(state,2)|(codec.check(tag,32)<<2)|
                (codec.check(gen,4)<<34)|(codec.check(direction,1)<<38)|
                (codec.check(version,4)<<39)|(codec.check(lock,1)<<43))

    def current(self,row):
        if not 0<=row<96:raise Refusal('rowbounds')
        p,s,_=codec.unseal(self.rows[row],self.pc,row,0)
        if s!='CLEAN':raise Refusal(s)
        return dict(state=p&3,tag=(p>>2)&((1<<32)-1),gen=(p>>34)&15,
                    direction=(p>>38)&1,version=(p>>39)&15,lock=(p>>43)&1)

    def payload(self,row):
        return self.pack(**self.current(row))

    def query(self,row):
        # Enrolled only after current-coded snapshot checks, not raw selection.
        self.current(row);self.queries[row]=self.queries.get(row,0)+1
        return self.rows[row]

    def drop_query(self,row):
        if self.queries.get(row,0)==0:raise Refusal('noquery')
        self.queries[row]-=1

    def reserve(self,client,tag,gen,direction):
        codec.check(client,3);codec.check(tag,32);codec.check(gen,4);codec.check(direction,1)
        if client>=6 or self.fault:raise Refusal('client/fault')
        bank=range(client*16,(client+1)*16)
        # Pending accepted journals participate in duplicate exclusion even
        # though they are not forwarded to the return-match CAM.
        for row in bank:
            p=self.current(row)
            if p['state']!=FREE and (p['tag'],p['gen'],p['direction'])==(tag,gen,direction):raise Refusal('duplicate')
            for j in self.journals:
                if j.row==row and j.operation=='issue':
                    q,_,_=codec.unseal(j.after,self.pc,row,0)
                    if ((q>>2)&((1<<32)-1),(q>>34)&15,(q>>38)&1)==(tag,gen,direction):raise Refusal('duplicate-pending')
        for row in bank:
            p=self.current(row)
            if p['state']==FREE and not p['lock'] and not self.queries.get(row,0):
                p['lock']=1
                # This operation models completion of a previously staged coded
                # reservation write. Caller may expose valid only afterwards.
                self.rows[row]=codec.seal(self.pack(**p),self.pc,row,0)
                self.reserved.add(row);return row
        raise Refusal('full')

    def cancel_unaccepted(self,row):
        if row not in self.reserved:raise Refusal('accepted-debt')
        p=self.current(row);p['lock']=0
        self.rows[row]=codec.seal(self.pack(**p),self.pc,row,0);self.reserved.remove(row)

    def prepare(self,row,target,operation):
        if self.fault:raise Refusal('fault')
        self.current(row)
        if len(self.journals)>=9:raise Refusal('journal-full')
        if any(j.row==row for j in self.journals):raise Refusal('same-row-writer')
        self.journals.append(Journal(row,self.rows[row],codec.seal(target,self.pc,row,0),operation,self.edge+4))

    def accept_request(self,row,tag,gen,direction):
        if row not in self.reserved:raise Refusal('not-reserved')
        p=self.current(row)
        self.prepare(row,self.pack(ISSUED,tag,gen,direction,p['version'],0),'issue')
        self.reserved.remove(row)

    def match_return(self,client,tag,gen,direction):
        if client>=6 or client<0 or self.fault:raise Refusal('client/fault')
        # Client-bank lock defers match; no optimistic journal forwarding.
        if any(j.row//16==client for j in self.journals):raise Refusal('bank-commit-stall')
        hits=[]
        for row in range(client*16,(client+1)*16):
            p=self.current(row)
            if p['state']==ISSUED and not p['lock'] and (p['tag'],p['gen'],p['direction'])==(tag,gen,direction):hits.append(row)
        if len(hits)!=1:raise Refusal('nonunique-return')
        row=hits[0];p=self.current(row)
        if self.queries.get(row,0):raise Refusal('query-live')
        p.update(state=WR_HELD if direction else RD_HELD)
        self.prepare(row,self.pack(**p),'held');return row

    def consume(self,row,direction):
        p=self.current(row)
        if p['state']!=(WR_HELD if direction else RD_HELD):raise Refusal('not-held')
        if self.queries.get(row,0) or row in self.corrections:raise Refusal('live-copy')
        if self.fault:raise Refusal('fault')
        # An actual consumer handshake creates the journal; it does NOT free
        # the old row. Version may wrap only after every local snapshot drains.
        p.update(state=FREE,lock=0,version=(p['version']+1)&15)
        self.prepare(row,self.pack(**p),'retire')

    def tick(self):
        self.edge+=1
        if self.fault:return
        ready=[j for j in self.journals if j.due<=self.edge]
        # Atomic fail-closed batch: a newly discovered fault cannot coexist
        # with another successful release/commit on this modeled edge.
        for j in ready:
            _,s,_=codec.unseal(self.rows[j.row],self.pc,j.row,0)
            _,t,_=codec.unseal(j.after,self.pc,j.row,0)
            if s!='CLEAN' or t!='CLEAN' or self.rows[j.row]!=j.before:
                self.fault=True;return
        for j in ready:self.rows[j.row]=j.after;self.journals.remove(j)

    def debts(self):
        # Count table OR accepted issue journal exactly once. Reserved holders
        # are not accepted debt. Retirement journals retain existing row debt.
        return {r for r in range(96) if self.current(r)['state']!=FREE} | {
            j.row for j in self.journals if j.operation=='issue'}

    def rearm(self,source_copies_drained,provider_fenced,reverse_cdc_fenced):
        if self.debts() or self.journals or self.reserved or any(self.queries.values()) or self.corrections:
            raise Refusal('local-debt')
        if not(source_copies_drained and provider_fenced and reverse_cdc_fenced):raise Refusal('external-copy')
        self.owner_fenced=True;return True


def model():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
    old=codec.model()
    return dict(schema='w2.nc6.protection-reconciliation.v1',source_sha256=SHA,
        antecedent_commit='b846a38ee3286f970be73288f13a0d37e0472d00',
        selected_geometry=old['geometry'],protected_words=189,protected_bits=13608,
        source_bindings=dict(table='state2+tag32+gen4+direction1=39;version4+lock1 fills44 payload',
            lookup='three selected-client banks of16; no96-row cross-client match',
            acceptance='req_take is p_req_v&&p_req_rdy, not source offer',
            release='rd_take or actual per-client c_wr_done_rdy; held completion preserves ownership',
            original_sameedge_return='rqbad/wqbad refuse return matching same-edge issue',
            original_outstanding='one alloc, one read retire, six WR retires; coded deferred journal replaces immediate update'),
        reconciled_contract=dict(
            reservation='coded lock committed before backend valid; unaccepted reservation may cancel, accepted journal may not',
            accepted_issue='debt retained in protected target journal until four-edge commit; duplicate lookup checks pending issue journals',
            return_match='bank commit stall; no journal-to-return forwarding CAM selected',
            snapshot='match row lock and version rechecked before journal prepare and actual commit',
            retirement='consumer accepts once; held output suppressed after acceptance; old row/count remain owned until coded commit',
            collision='same-row writer rejected, disjoint9writer journal batch permitted; any current-word error suppresses all batch commits',
            cache='count cache is checked derived state; never sole authorization; delta RMW required when allocation/read/write retire share client',
            scrub='snapshot identity recheck; dirty target locks write/retire; no CE-as-CLEAN or stale-syndrome consumer release',
            utility_repair='eight correction contexts retained; scheduling/all utility-coded controls still require constructive successor',
            reset='external all-copy cold fence; runtime rearm requires local journals/queries/correction/reservations empty plus source/provider/reverseCDC positive fence'),
        early_return_calendar=dict(request_accept_edge=0,coded_issue_commit_edge=4,
            earliest_legal_return_capture_edge=1,ordinary_current_check_edge=2,
            commit_visible_current_check_edge=5,extra_bank_stall_edges=3,
            antecedent_request_read_write_edges=[5,5,6],
            selected_capture_check_match_prepare_edges=[0,1,2,3],
            prepared_journal_commit_edge=7,first_qualified_consumer_edge=8,
            minimum_clean_request_edges=8,minimum_clean_read_edges=8,early_read_edges=11,
            minimum_clean_write_edges=9,early_write_edges=12,
            selected_request_read_write_delta_from_unprotected=[7,6,6],
            conservative_lookup_II_edges=8,bytes_per_service_edge_upper=4,
            reason='b846 one-edge journal stage did not compose four-edge coded commit; retain existing protected records for three extra edges',
            no_fit=True,held_or_contended_return='additional finite stalls; not bounded by these minimums'),
        price_delta=dict(new_forwarding_CAM=0,new_hardware_records=0,
            existing_query_records_hold_during_commit=True,
            selected_bank_busy_decode='OR of9 protected journal valid/address(client) matches plus row current lock; included arbitration budget, loaded path unqualified',
            net_F0_replacement_unknown=True,unchanged_gross_area_budget=old['cell_price']),
        readiness=dict(engine_RTL_admitted=False,physical_admitted=False,
            codec_characterization_source_allowed=True,
            outstanding_blockers=['protected count-cache same-client delta transaction atomicity',
                'utility-context single-bit repair scheduling without unprotected control',
                'exceptional held-valid quarantine interface enrollment',
                'loaded K64 clean/encoder and16-row equality SS/FF cuts including reset paths'],
            next_action='implement exact reusable K64 codec source cone for characterization; no NC6 engine build, no full caller/physical launch'))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path);a=ap.parse_args()
    t=json.dumps(model(),sort_keys=True,indent=2)+'\n'
    if a.output:a.output.write_text(t)
    else:print(t,end='')
