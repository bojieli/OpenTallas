"""Default-off DSpark controller -> existing RTL command processor pin driver.

No SM execution, result computation, ready/fence substitution or clock domain
crossing occurs here. `pins` owns the connected simulator, samples pre-edge
outputs through snapshot(), drives die/ctl inputs, then ticks ONE shared edge.
The two die completions are joined before publishing a controller result.
Fullshape tokens need a wider cmdproc successor: this binding refuses narrowing.
"""
from tools.gpu_sys import v41_dspark_connected as C

OPS = ('VLAYER', 'VHEAD', 'SEED', 'DSTAGE', 'DHEAD', 'MARKOV')


def lower(command, entries, *, noise, nsm=2, imw=14):
    """Actual linked entry PCs and existing kernel order, with field validation."""
    C.validate_command(command, noise=noise)
    if not 1 <= nsm <= 16 or not 1 <= imw <= 32:
        raise ValueError('cmdproc mask/PC geometry')
    if set(entries) != set(C.D.KINDS):
        raise ValueError('all eleven linked kernel entries required')
    if any(type(pc) is not int or not 0 <= pc < 1 << imw for pc in entries.values()):
        raise ValueError('linked program does not fit actual IMEM')
    if command['op'] in ('DSTAGE', 'DHEAD') and command['pos']+1+C.D.B > C.D.CTX:
        raise ValueError('draft source position storage extent')
    # NOISE is an original module variable. Do not mutate live/global source
    # state: replace only the actual draft embedding's immutable noise token.
    if command['op'] == 'DSTAGE' and command['idx'] == 0:
        # This source expansion is otherwise byte-for-byte D.expand's stage0.
        q, y = command['pos'], command['tok1']
        launches = []
        for i in range(C.D.B):
            launches += [('swapin', C.D.PMAX+i, 40),
                         ('demb', y if i == 0 else noise, 0),
                         ('dsa', i, q+1+i), ('swapout', C.D.PMAX+i, 0)]
        for i in range(C.D.B):
            launches += [('swapin', C.D.PMAX+i, 40),
                         ('dsb', i, q+1+i), ('swapout', C.D.PMAX+i, 0)]
    else:
        launches = C.D.expand(command)
    out = []
    for kind, token, pos in launches:
        if type(token) is not int or type(pos) is not int or not 0 <= token < 65536 or not 0 <= pos < 65536:
            raise ValueError('launch token/position narrowing forbidden')
        out.append(dict(kind=kind, token=token, pos=pos,
                        words=((1 << 60) | (((1 << nsm)-1) << 44) | entries[kind], 2 << 60),
                        expected_status=0 if kind in ('head', 'markov') else 2))
    return out


class CmdprocBridge:
    """One finite ordered command in flight; actual ready and completion only.

    snapshot: {ctl:{cmd_v,cmd_op,cmd_idx,cmd_ncol,cmd_pos,cmd_tok1,
                    cmd_toks:[integer tokens]}, dies:[{db_rdy,cpl_v,
                    cpl_status,cpl_token}, ...]}.
    drive_die(index, **ports), drive_ctl(**ports), tick() must access RTL.
    Instantiate on the SM/cmdproc clock. Existing host CDC remains external.
    """
    def __init__(self, pins, entries, *, noise, enable=False, ndie=2, nsm=2, imw=14):
        if not enable:
            raise ValueError('explicit enable required')
        if ndie != C.D.TP or nsm != C.D.NSM:
            raise ValueError('source-selected reduced checkpoint topology')
        # Validate even before the first controller command.
        lower(dict(op='SEED',idx=0,ncol=1,pos=0,tok1=0,toks=[]),
              entries,noise=noise,nsm=nsm,imw=imw)
        self.pins, self.entries, self.noise = pins, dict(entries), noise
        self.ndie, self.nsm, self.imw = ndie, nsm, imw
        self.state, self.queue, self.cursor = 'IDLE', (), 0
        self.sent, self.completed, self.failed = set(), {}, None
        self.launches = self.commands = self.cycles = 0

    def step(self):
        if self.failed:
            raise RuntimeError('bridge terminal failure: '+self.failed)
        snap = self.pins.snapshot()
        if len(snap['dies']) != self.ndie:
            raise ValueError('actual die census mismatch')
        ctl = dict(cmd_ready=int(self.state == 'IDLE'), eng_done=0, am_v=0, am_idx=0)
        ports = [dict(cmd_we=0,cmd_addr=0,cmd_wdata=0,db_v=0,
                      db_token=0,db_pos=0,cpl_rdy=0) for _ in range(self.ndie)]
        failure = None
        if self.state == 'IDLE' and snap['ctl']['cmd_v']:
            c = snap['ctl']
            try:
                if type(c['cmd_op']) is not int or not 0 <= c['cmd_op'] < len(OPS):
                    raise ValueError('unsupported controller opcode')
                self.queue = lower(dict(op=OPS[c['cmd_op']],idx=c['cmd_idx'],
                    ncol=c['cmd_ncol'],pos=c['cmd_pos'],tok1=c['cmd_tok1'],
                    toks=list(c['cmd_toks'])[:c['cmd_ncol']]),self.entries,
                    noise=self.noise,nsm=self.nsm,imw=self.imw)
                self.cursor=0; self.state='LOAD0'; self.commands+=1
            except ValueError as exc:
                failure=str(exc); ctl['cmd_ready']=0
        elif self.state in ('LOAD0','LOAD1'):
            if not all(d['db_rdy'] and not d['cpl_v'] for d in snap['dies']):
                failure='command memory not exclusively idle'
            else:
                address=int(self.state == 'LOAD1')
                for p in ports:
                    p.update(cmd_we=1,cmd_addr=address,cmd_wdata=self.queue[self.cursor]['words'][address])
                self.state='DB' if address else 'LOAD1'
                self.sent=set(); self.completed={}
        elif self.state == 'DB':
            launch=self.queue[self.cursor]
            for i,d in enumerate(snap['dies']):
                if i not in self.sent:
                    ports[i].update(db_v=1,db_token=launch['token'],db_pos=launch['pos'])
                    if d['db_rdy']:
                        self.sent.add(i)
            if len(self.sent) == self.ndie:
                self.state='WAIT'; self.launches+=1
        elif self.state == 'WAIT':
            launch=self.queue[self.cursor]
            for i,d in enumerate(snap['dies']):
                if i not in self.completed:
                    ports[i]['cpl_rdy']=1
                    if d['cpl_v']:
                        self.completed[i]=(d['cpl_status'],d['cpl_token'])
                        if d['cpl_status'] != launch['expected_status']:
                            failure='actual '+launch['kind']+' completion status '+str(d['cpl_status'])
            if not failure and len(self.completed) == self.ndie:
                if launch['expected_status'] == 0:
                    tokens=[v[1] for v in self.completed.values()]
                    if len(set(tokens)) != 1 or not 0 <= tokens[0] < 65536:
                        failure='cross-die RESULT identity mismatch'
                    else:
                        ctl.update(am_v=1,am_idx=tokens[0])
                if not failure:
                    self.cursor+=1
                    if self.cursor == len(self.queue):
                        ctl['eng_done']=1; self.state='IDLE'
                    else:
                        self.state='LOAD0'
        for i,p in enumerate(ports):
            self.pins.drive_die(i,**p)
        self.pins.drive_ctl(**ctl)
        self.pins.tick()
        self.cycles+=1
        if failure:
            self.failed=failure
            raise RuntimeError(failure)
        return ctl
