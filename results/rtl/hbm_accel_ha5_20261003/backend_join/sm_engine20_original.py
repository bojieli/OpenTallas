"""Default-off real CP20 kernel callback for the connected DS SM simulator.

Pins supplies snapshot(), drive_die(index, **ports), tick() from actual RTL.
This driver does not execute arithmetic or substitute ready/completion signals.
Caller owns IMEM loading and immutable source-selected kernel entries. ABI3
request program.bin must be lowered separately; it is not SM instruction RAM.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Completion:
    job: int
    generation: int
    position: int
    token: int
    status: int
    cycles_by_die: tuple
    elapsed_edges: int


class SMEngine20:
    def __init__(self, pins, *, enable=False, ndie=2, nsm=2, imw=14):
        if not enable:
            raise ValueError('explicit enable required')
        if not 1 <= ndie or not 1 <= nsm <= 16 or not 1 <= imw <= 32:
            raise ValueError('actual CP mask/IMEM topology')
        self.pins, self.ndie, self.nsm, self.imw = pins, ndie, nsm, imw
        self.state = 'IDLE'
        self.failure = None
        self.completed = {}
        self.sent = set()
        self.edges = 0
        self.receipt = None

    @staticmethod
    def _field(value, bits, name):
        if type(value) is not int or not 0 <= value < 1 << bits:
            raise ValueError(name+' would narrow')
        return value

    def launch(self, *, entry_pc, token, position, job, generation, expected_status=2):
        if self.failure:
            raise RuntimeError(self.failure)
        if self.state != 'IDLE':
            raise RuntimeError('existing kernel has not completed')
        self.entry = self._field(entry_pc, self.imw, 'source entry')
        self.token = self._field(token, 17, 'token')
        self.position = self._field(position, 20, 'DS1M position')
        self.job = self._field(job, 32, 'job')
        self.generation = self._field(generation, 4, 'generation')
        self.expected_status = self._field(expected_status, 4, 'status')
        self.words = ((1 << 60) | (((1 << self.nsm)-1) << 44) | self.entry, 2 << 60)
        self.completed, self.sent, self.edges, self.receipt = {}, set(), 0, None
        self.state = 'LOAD0'

    def poll(self):
        """Advance one actual shared edge; return only accepted RTL completion."""
        if self.failure:
            raise RuntimeError(self.failure)
        if self.state == 'IDLE':
            return self.receipt
        snap = self.pins.snapshot()
        dies = snap['dies']
        if len(dies) != self.ndie:
            raise ValueError('actual die census differs from connected topology')
        ports = [dict(cmd_we=0, cmd_addr=0, cmd_wdata=0, db_v=0,
                      db_token=self.token, db_pos=self.position, db_job=self.job,
                      db_generation=self.generation, cpl_rdy=0) for _ in dies]
        failure = None
        if self.state in ('LOAD0', 'LOAD1'):
            # Wait on real readiness, without mutating a busy command memory.
            if all(d['db_rdy'] and not d['cpl_v'] for d in dies):
                address = int(self.state == 'LOAD1')
                for p in ports:
                    p.update(cmd_we=1, cmd_addr=address, cmd_wdata=self.words[address])
                self.state = 'DB' if address else 'LOAD1'
        elif self.state == 'DB':
            for i, d in enumerate(dies):
                if i not in self.sent:
                    ports[i]['db_v'] = 1
                    if d['db_rdy']:
                        self.sent.add(i)
            if len(self.sent) == self.ndie:
                self.state = 'WAIT'
        elif self.state == 'WAIT':
            for i, d in enumerate(dies):
                if i in self.completed:
                    continue
                ports[i]['cpl_rdy'] = 1
                if d['cpl_v']:
                    raw = self._field(d['cpl_data'], 109, 'actual CPL109')
                    token = raw & ((1 << 17)-1)
                    position = (raw >> 17) & ((1 << 20)-1)
                    status = (raw >> 37) & 15
                    cycles = (raw >> 41) & ((1 << 32)-1)
                    generation = (raw >> 73) & 15
                    job = raw >> 77
                    self.completed[i] = (token, status, cycles)
                    if (position, job, generation, status) != (self.position, self.job, self.generation, self.expected_status):
                        failure = 'actual CPL109 identity/status mismatch'
            if not failure and len(self.completed) == self.ndie:
                tokens = [v[0] for v in self.completed.values()]
                if len(set(tokens)) != 1:
                    failure = 'actual cross-die RESULT mismatch'
                else:
                    self.state = 'IDLE'
                    self.receipt = Completion(self.job, self.generation, self.position,
                        tokens[0], self.expected_status,
                        tuple(self.completed[i][2] for i in range(self.ndie)), self.edges+1)
        for i, p in enumerate(ports):
            self.pins.drive_die(i, **p)
        self.pins.tick()
        self.edges += 1
        if failure or self.receipt is not None:
            # The accepting edge has occurred. Do not leave ACK/doorbell
            # inputs asserted when the caller stops polling this kernel.
            for i, p in enumerate(ports):
                self.pins.drive_die(i, **dict(p, cmd_we=0, db_v=0, cpl_rdy=0))
        if failure:
            self.failure = failure
            raise RuntimeError(failure)
        return self.receipt
