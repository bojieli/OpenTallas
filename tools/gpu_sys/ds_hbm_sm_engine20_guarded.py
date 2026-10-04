"""Opt-in CP20 callback that validates completions before acknowledging them.

The pinned original callback remains unchanged. This successor uses the same
actual pins and shared clock; foreign completions stay held by their producer.
It supplies no arithmetic, completion, memory or ownership substitutes.
"""
from tools.gpu_sys.ds_hbm_sm_engine20 import Completion, SMEngine20


class SMEngine20Guarded(SMEngine20):
    def poll(self):
        if self.failure:
            raise RuntimeError(self.failure)
        if self.state == 'IDLE':
            return self.receipt
        dies = self.pins.snapshot()['dies']
        if len(dies) != self.ndie:
            raise ValueError('actual die census differs from connected topology')
        ports = [dict(cmd_we=0, cmd_addr=0, cmd_wdata=0, db_v=0,
                      db_token=self.token, db_pos=self.position, db_job=self.job,
                      db_generation=self.generation, cpl_rdy=0) for _ in dies]
        incoming = {}
        if self.state == 'WAIT':
            try:
                for i, d in enumerate(dies):
                    if i in self.completed or not d['cpl_v']:
                        continue
                    raw = self._field(d['cpl_data'], 109, 'actual CPL109')
                    token = raw & ((1 << 17)-1)
                    position = (raw >> 17) & ((1 << 20)-1)
                    status = (raw >> 37) & 15
                    cycles = (raw >> 41) & ((1 << 32)-1)
                    generation = (raw >> 73) & 15
                    job = raw >> 77
                    if (position, job, generation, status) != (
                            self.position, self.job, self.generation, self.expected_status):
                        raise ValueError('actual CPL109 identity/status mismatch')
                    incoming[i] = (token, status, cycles)
                joined = {**self.completed, **incoming}
                if len({v[0] for v in joined.values()}) > 1:
                    raise ValueError('actual cross-die RESULT mismatch')
            except ValueError as error:
                # Clear any READY left from an earlier poll before yielding.
                # No accepting edge, receipt or local debt retirement occurs.
                for i, p in enumerate(ports):
                    self.pins.drive_die(i, **p)
                self.failure = str(error)
                raise RuntimeError(self.failure) from error
        if self.state in ('LOAD0', 'LOAD1'):
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
            for i in incoming:
                ports[i]['cpl_rdy'] = 1
        for i, p in enumerate(ports):
            self.pins.drive_die(i, **p)
        self.pins.tick()
        self.edges += 1
        self.completed.update(incoming)
        if len(self.completed) == self.ndie:
            self.state = 'IDLE'
            self.receipt = Completion(self.job, self.generation, self.position,
                self.completed[0][0], self.expected_status,
                tuple(self.completed[i][2] for i in range(self.ndie)), self.edges)
        # READY is a one-edge acceptance, never permission for the next record.
        for i, p in enumerate(ports):
            self.pins.drive_die(i, **dict(p, cmd_we=0, db_v=0, cpl_rdy=0))
        return self.receipt
