#!/usr/bin/env python3
"""Bind finite DRAM-provider events to the retained scheduler before RTL."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCHED_REV='4535be1001d69bc43669e0fdf0401896be4034a6'
SCHED_PATH='rtl/hdc/kv/ot_hdc_hbm_model.sv'
def compose():
    source=subprocess.check_output(['git','show',SCHED_REV+':'+SCHED_PATH],cwd=ROOT)
    for token in [b'function automatic longint schedule',b'if (h_tcol[p] <= now)',b'mem[q_addr[p][slot] % MEM_WORDS]',b'tcol + CWL_PS + BURST_PS + WR_PS']:
        assert token in source
    # Backing DRAM data is off-chip, but outstanding write-data/timestamps and
    # event holds are finite on-controller state, separately charged.
    bits=256+34+16+5+5+64+64+64+4
    assert bits==512
    registers=4*4*bits
    mux=4*32*3*114*2+4*3*256
    compare=4*4*32*5*2+4*4*64
    control=4*4*128
    area=(registers*.2916+(mux+compare+control)*.2)/.5/1e6
    return dict(schema='opentallas.common-hbm-real-provider-binding.v1',
        status='SOURCE_BOUND_PROVIDER_PORT_CANDIDATE_MODEL_ADMISSION_PENDING',
        engine_RTL_build_ready=False,physical_build_ready=False,adoption=False,full_token=False,
        source_pin={'revision':SCHED_REV,'path':SCHED_PATH,'sha256':hashlib.sha256(source).hexdigest()},
        source_scope='Reuse bank/refresh/FR-FCFS scheduling arithmetic as reference; pinned original remains untouched. No claim that original modulo/column-write model implements this provider.',
        geometry=dict(controllers=4,NPC=32,QD=512,RQD=512,AW_parameter={'Qwen':34,'DeepSeek':27},
            sector_bits=256,tag_bits=16,LENW=6,BEATW=5,read_max_sectors=32,
            read_write_shared_commands_per_stack_cycle=1,write_sectors_per_command=1,
            shared_byte_budget_per_stack_cycle=750,token_bucket_capacity_bytes=1024,
            pending_backend_write_slots_per_controller=4),
        exact_clock=dict(target_hz=1200000000,period_ps_numerator=2500,period_ps_denominator=3,
            timestamp_policy='ceil(cycle*2500/3)ps, conservative integer timestamp. Historical833psCLK is not relabeled exact1.2GHz.',
            event_timestamp='Scheduled DRAM column timestamp may fall between fabric edges. Emit at the first observing edge; preserve actual column timestamp, never retime it to acceptance or guess a future visibility event.'),
        event_contract=dict(WR_scheduled='Captured actual h_tcol<=now WRissue before queue pop, retaining sector/tag/beat/PC/tcol. Valid held until frontend accepts.',
            backing_commit='At actual scheduled burst end tcol+CWL+BURST, update exact full-address sector backing once and capture actual visible timestamp. Read/write turnarounds, bank conflict and refresh remain scheduler costs.',
            WR_visible='Emit only after actual backing update, retain visible event under ready stall; schedule event delivered first. Retain backend slot until both events delivered.',
            no_host_timer_completion=True,no_acceptance_completion=True,
            frontend_credit='Backend event delivery frees only backend event slot. Frontend write/ACK credit and sector lock remain held through actual finalconsumerdone/resultvisibility and reverseCDC.',
            read_visibility='All shared-client reads consult sector ownership/publication before issue; same-address reads cannot observe a partially merged/unpublished write.'),
        storage=dict(bits_per_pending_backend_slot=bits,total_register_bits=registers,
            fields={'data':256,'sector':34,'tag':16,'beat':5,'PC':5,'column_time':64,'burst_due_time':64,'actual_visible_time':64,'valid_scheduled_pending_visible_pending_backing_committed_flags':4},
            slots_reserved='Reserve backend pending slot before actual WRissue; never pop a write into an unavailable slot. Four frontend credits cap all write events including RMW.',
            fulladdress_backing='Finite capacity-checked DRAM address space; sparse simulation storage may omit untouched pages but never modulo alias. Initial unseen data policy must be explicit from checkpoint loader; no implicit populated checkpoint.'),
        additional_port_cost=dict(register_bits=registers,mux_bit_equivalents=mux,
            comparison_bit_equivalents=compare,control_gate_equivalents=control,
            additive_footprint_mm2=area,
            allocation='Additional to ec3 frontend32PC-to4slot event mux/compare and helperr4 ACK cost; backend4slot-to32PC schedule/visible fanout and pending storage are not free reuse',
            not_physical='First analytical gate equivalents only; exact implementation/placement/routing/SSFF remain unqualified'),
        remaining_admission=['Ram admits complete backend-event/queue/read-write-byte budget and CDC/consumer/publication composition',
            'Halley/Qwen bind finite stageconsumer landing/opcodefinish/stored-result-visible/finaldone providers; no fixed8cycle release',
            'Exact fulladdress loader/backing and36client ownership/tag map plus RMW lock consultation',
            'Legal fullsize32SM/L2/controller/RF floorplan before anyPnR'],
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
class BurstVisibilityModel:
    """Finite contract bench with supplied WR issues, not a DRAM scheduler."""
    def __init__(self,capacity_sectors=632812500):
        self.capacity=capacity_sectors;self.slots={};self.memory={};self.cycle=0;self.tags=set()
    @property
    def now(self):return (self.cycle*2500+2)//3
    def address(self,sector):
        if not isinstance(sector,int) or not 0<=sector<self.capacity:raise ValueError('finite fulladdress capacity')
    def preload(self,sector,data):
        self.address(sector)
        if len(data)!=32:raise ValueError('sector bytes')
        self.memory[sector]=bytes(data)
    def reserve(self,tag,sector,data):
        self.address(sector)
        if not 0<=tag<65536 or tag in self.tags:raise ValueError('tag reuse without proven drain')
        if len(data)!=32:raise ValueError('sector bytes')
        if len(self.slots)==4 or any(e['sector']==sector for e in self.slots.values()):return None
        self.tags.add(tag);self.slots[tag]=dict(sector=sector,data=bytes(data),reserved_ps=self.now,column=None,due=None,scheduled_pending=False,committed=False,visible=None)
        return tag
    def WR_issue(self,tag,sector,column_ps):
        e=self.slots.get(tag)
        if e is None or e['sector']!=sector or e['column'] is not None or not e['reserved_ps']<=column_ps<=self.now:raise ValueError('actual scheduled WR identity/time')
        e['column']=column_ps;e['due']=column_ps+7274;e['scheduled_pending']=True
    def tick(self,cycles=1):
        if not isinstance(cycles,int) or cycles<1:raise ValueError('positive cycles')
        for _ in range(cycles):
            self.cycle+=1
            for e in self.slots.values():
                if e['due'] is not None and not e['committed'] and e['due']<=self.now:
                    self.memory[e['sector']]=e['data'];e['committed']=True;e['visible']=self.now
    def take_scheduled(self,tag):
        e=self.slots.get(tag)
        if e is None or not e['scheduled_pending']:raise ValueError('unknown/duplicate schedule event')
        e['scheduled_pending']=False
        return dict(tag=tag,sector=e['sector'],column_ps=e['column'])
    def peek_visible(self,tag):
        e=self.slots.get(tag)
        if e is None or not e['committed'] or e['scheduled_pending']:return None
        return dict(tag=tag,sector=e['sector'],visible_ps=e['visible'])
    def take_visible(self,tag):
        event=self.peek_visible(tag)
        if event is None:raise ValueError('visible event requires delivered schedule and actual backing commit')
        del self.slots[tag]
        return event
    def read(self,sector,publication_permission):
        self.address(sector)
        if not publication_permission:raise ValueError('external ownership/publication not granted')
        if sector not in self.memory:raise ValueError('no loaded or written checkpoint backing')
        return self.memory[sector]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();x=compose()
    with a.out.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
    print(json.dumps(x['additional_port_cost'],indent=2))
