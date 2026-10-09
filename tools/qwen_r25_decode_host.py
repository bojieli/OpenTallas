"""Executable finite TOKEN18/TP4 host shell over actual command-processor pins.

No arithmetic or simulated kernel completion occurs here. Driver owns8 actual
RTL CP halves, snapshots before each shared edge, drives inputs, then ticks.
An incomplete production entry map must be refused by program.link first.
"""
from qwen_r25_cmdproc_program import doorbell,loader_pair,completion,VOCAB

class DecodeHost:
    def __init__(self,pins,batches,*,token,position,job,generation):
        # Host ABI validation before any write/doorbell.
        doorbell(token,position,job,generation)
        if position>=8192:raise ValueError('Qwen KV context extent')
        if not batches or any(not 1<=len(b['words'])<=256 for b in batches):raise ValueError('linked command batches required')
        if any(type(w)!=int or not 0<=w<1<<64 for b in batches for w in b['words']):raise ValueError('command width')
        if any(b['words'][-1]!=(2<<60) for b in batches):raise ValueError('END required')
        if job+len(batches)>1<<32:raise ValueError('per-batch transaction job extent')
        self.pins,self.batches=pins,batches
        self.token,self.position,self.job,self.generation=token,position,job,generation
        self.state='CONFIG';self.batch=0;self.address=0;self.sent=set();self.retired={}
        self.result=None;self.failure=None;self.cycles=0

    def step(self):
        if self.failure:raise RuntimeError('terminal host failure: '+self.failure)
        if self.state=='DONE':return self.state
        snap=self.pins.snapshot()
        if len(snap)!=4 or any(len(d)!=2 for d in snap):raise ValueError('actual TP4 north/south processor census')
        expected_job=self.job+self.batch
        ports=[[dict(cmd_we=0,cmd_addr=0,cmd_wdata=0,db_v=0,db_token=self.token,db_pos=self.position,db_job=expected_job,db_generation=self.generation,cpl_rdy=0) for _ in range(2)] for _ in range(4)]
        b=self.batches[self.batch]
        try:
            if self.state=='CONFIG':
                if not hasattr(self.pins,'stage_batch'):raise RuntimeError('actual descriptor installation hook missing')
                if self.pins.stage_batch(b):self.state='LOAD'
            elif self.state=='LOAD':
                if any(not c['db_rdy'] or c['cpl_v'] for d in snap for c in d):raise RuntimeError('command memory not exclusively retired')
                for d in ports:
                    for p in d:p.update(cmd_we=1,cmd_addr=self.address,cmd_wdata=b['words'][self.address])
                self.address+=1
                if self.address==len(b['words']):self.state='DB';self.sent=set();self.retired={}
            elif self.state=='DB':
                for die in range(4):
                    for band in range(2):
                        key=(die,band)
                        if key not in self.sent:
                            ports[die][band]['db_v']=1
                            if snap[die][band]['db_rdy']:self.sent.add(key)
                if len(self.sent)==8:self.state='WAIT'
            elif self.state=='WAIT':
                for die in range(4):
                    for band in range(2):
                        key=(die,band);c=snap[die][band]
                        if key in self.retired:continue
                        if c['cpl_v']:
                            if (c['cpl_job'],c['cpl_generation'],c['cpl_position'])!=(expected_job,self.generation,self.position):raise RuntimeError('stale completion identity')
                            expected=0 if b['result'] else 2
                            if c['cpl_status']!=expected:raise RuntimeError('actual processor completion status')
                            self.retired[key]=completion(c['cpl_token'],0) if b['result'] else None
                            ports[die][band]['cpl_rdy']=1
                if len(self.retired)==8:
                    if b['result']:
                        ids=list(self.retired.values())
                        if len(set(ids))!=1:raise RuntimeError('TP4 global token mismatch')
                        self.result=ids[0]
                    self.batch+=1
                    if self.batch==len(self.batches):self.state='DONE'
                    else:self.state='CONFIG';self.address=0
            # Actual pin driver, no synthetic completion or calculation.
            for die in range(4):
                self.pins.drive_die(die,ports[die])
            self.pins.tick();self.cycles+=1
        except (RuntimeError,ValueError) as exc:
            self.failure=str(exc);raise
        return self.state


def loader_payload(ports):
    """Physical343-bit loader input; ready/completion remain separate bindings."""
    if len(ports)!=2:raise ValueError('north/south tuple pair')
    def pack(p):return doorbell(p['db_token'],p['db_pos'],p['db_job'],p['db_generation'],valid=p['db_v'],cmd_we=p['cmd_we'],cmd_addr=p['cmd_addr'],cmd_wdata=p['cmd_wdata'])
    return loader_pair(pack(ports[1]),pack(ports[0]))
