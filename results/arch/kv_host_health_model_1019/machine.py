#!/usr/bin/env python3
"""SOURCE MODEL ONLY: explicit fixture ages; no RTL or physical qualification."""
import hashlib
import json
from pathlib import Path

CLASS_SERVICE, CLASS_PHYSICAL, CLASS_TRANSPORT, CLASS_PROTOCOL = 1, 2, 4, 8

def code(cause, missing=False):
    return 5 if missing else 4 if cause & 8 else 2 if cause & 2 else 3 if cause & 4 else 1 if cause else 0

class Machine:
    def __init__(self, capture=1, bridge=2, status=12, retire=16, mutant=None):
        assert capture >= 1 and bridge >= 1 and retire > status
        self.capture, self.bridge = capture, bridge
        self.status_edge, self.retire_edge = status, retire
        self.mutant = mutant
        self.source = self.observed = 0
        self.queue = []
        self.contexts = {}
        self.records = []
        self.recovery_open = True

    def start(self, identity, edge, deadline):
        if self.observed and self.mutant != 'admission':
            return False
        assert self.recovery_open and identity not in self.contexts
        assert edge <= deadline
        self.contexts[identity] = {'deadline': deadline, 'reported': False, 'missing': False}
        return True

    def edge(self, edge, event=0, report=None):
        # event is captured in its source domain here. A pulse never crosses raw.
        if event:
            self.source |= event
            self.queue.append((edge + self.capture + self.bridge, self.source))
        for due, value in self.queue:
            if due == edge and self.mutant != 'drop_health':
                self.observed |= value
        if report in self.contexts:
            self.contexts[report]['reported'] = True
        for identity, context in self.contexts.items():
            if edge == context['deadline'] and not context['reported']:
                context['missing'] = True
            if edge in (self.status_edge, self.retire_edge):
                cause = self.observed
                if edge == self.retire_edge and self.mutant == 'status_snapshot':
                    cause = context['status_cause']
                missing = context['missing']
                record = dict(edge=edge, identity=identity, cause=cause,
                              bad=bool(cause or missing), code=code(cause, missing))
                # No change to active dataflow or terminal time on a fault.
                self.records.append(record)
                if edge == self.status_edge:
                    context['status_cause'] = cause

    def recover(self, *, producer_clear, bridge_drained, identity_drained, fixed_guard_expired):
        # A fixture gate, NOT proof of an actual fixed recovery schedule.
        if not all((producer_clear, bridge_drained, identity_drained, fixed_guard_expired)):
            return False
        self.source = self.observed = 0
        self.queue.clear()
        self.contexts.clear()
        self.records.clear()
        return True


def scenario(event_edge=None, event=0, report_edge=5, mutant=None):
    m = Machine(mutant=mutant)
    assert m.start(('client7', 'slot0', 'gen2', 'pos31'), 0, 8)
    for edge in range(21):
        m.edge(edge, event=event if edge == event_edge else 0,
               report=('client7', 'slot0', 'gen2', 'pos31') if edge == report_edge else None)
    return m


def test(mutant=None):
    checks = 0
    for event in (1, 2, 4, 8):
        for when in (0, 5, 8, 9):
            m = scenario(when, event, mutant=mutant)
            assert len(m.records) == 2
            assert all(r['bad'] and r['cause'] & event and r['code'] == code(event) for r in m.records), 'health did not veto aligned STATUS/terminal'
            assert [r['edge'] for r in m.records] == [12, 16]
            assert not m.start(('next',), 20, 21), 'sticky health did not veto admission'
            checks += 3
    m = scenario(10, 2, mutant=mutant)
    assert not m.records[0]['bad'] and m.records[1]['bad'], 'late health must veto retirement after healthy STATUS'
    checks += 1
    m = scenario(17, 4, mutant=mutant)
    assert not m.records[-1]['bad'], 'past terminal cannot be retroactively changed'
    assert not m.start(('next',), 21, 22), 'late health must veto future admission'
    checks += 2
    for report in (None, 9):
        m = scenario(report_edge=report, mutant=mutant)
        assert all(r['bad'] and r['code'] == 5 for r in m.records), 'missing/late operation report escaped fixed deadline'
        checks += 1
    m = scenario(event_edge=0, event=15, mutant=mutant)
    assert m.records[-1]['cause'] == 15 and m.records[-1]['code'] == 4
    for premise in range(4):
        vals = [True] * 4
        vals[premise] = False
        assert not m.recover(**dict(zip(('producer_clear','bridge_drained','identity_drained','fixed_guard_expired'), vals)))
        assert m.observed == 15
        checks += 2
    assert m.recover(producer_clear=True, bridge_drained=True, identity_drained=True, fixed_guard_expired=True)
    assert m.start(('new_epoch',), 0, 8)
    checks += 2
    print(json.dumps({'source_model_only': True, 'checks': checks, 'mutant': mutant, 'PASS': True}))

if __name__ == '__main__':
    import sys
    print('machine_sha256=' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    test(sys.argv[1] if len(sys.argv) > 1 else None)
