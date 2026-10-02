"""Offline experimental fixture-native trace validation; no launch or RTL fidelity transfer."""
import argparse
import json
import re
from pathlib import Path


def verify_priming(text):
    reset = re.findall(r'^D1_RESET_ACCEPT time_ps=(\d+) rn=(\d+)$', text, re.M)
    full = re.findall(r'^D1_ALL128_PRIMED time_ps=(\d+) accepted=(\d+) rn=(\d+)$', text, re.M)
    pattern = r'^D1_QUALIFIED_PRIME time_ps=(\d+) row=(\d+) rn=(\d+) valid=(\d+) active=(\d+) tag=(\d+) user=(\d+) blocks=([0-9a-f]+)$'
    matches = list(re.finditer(pattern, text, re.M))
    if reset != [('6000','1')] or full != [('134501','128','1')] or len(matches) != 128:
        raise ValueError('reset/all128 witness mismatch')
    for row, match in enumerate(matches):
        fields = match.groups()
        got = tuple(int(x, 16 if i == 7 else 10) for i,x in enumerate(fields))
        if got != (7501+row*1000,row,1,1,1,row,0,65535):
            raise ValueError('prime identity/commit mismatch')
    if text.index('D1_RESET_ACCEPT') > matches[0].start() or text.index('D1_ALL128_PRIMED') < matches[-1].start():
        raise ValueError('priming witness order')
    return {'status':'PASS_RESET_QUALIFIED_PRIMING_ONLY','rows':128,'first_commit_ps':7501,
            'last_commit_ps':134501,'endpoint_credit':False,'fulltoken':False,'RTL_fidelity':'UNPROVEN'}


def verify_bound_execution(text, exit_code, actual_argv, expected_argv):
    if type(actual_argv) is not list or actual_argv != expected_argv:
        raise ValueError('actual executable/program argv binding mismatch')
    if len(expected_argv) != 2 or not expected_argv[1].startswith('+DIR='):
        raise ValueError('expected program binding malformed')
    return verify(text, exit_code)


def verify(text, exit_code):
    # Fatal anywhere wins, including after an apparent endpoint.
    if exit_code != 0 or any(x in text for x in ('D1_SOURCE_OR_LEDGER_FAULT', 'D1_SOURCE_ADMISSION_MISMATCH',
                                               'D1_PRIME_ACCEPT_NOT_COMMITTED', 'D1_PRIME_SET_INCOMPLETE',
                                               'D1_NO_PENDING_EVENTS_NO_SERVICE_CREDIT', '%Error')):
        raise ValueError('actual failure/exit has precedence')
    if 'D1_PREFIX_CYCLE_CAP_NO_COMPLETION_CREDIT' in text:
        raise ValueError('cycle-cap stop is not completion')
    records = []
    for line in text.splitlines():
        if not line.startswith('D1_'): continue
        fields = {}
        for key, value in re.findall(r'(\w+)=(\w+)', line):
            if key in fields: raise ValueError('duplicate field')
            if not re.fullmatch('[0-9]+', value) and not (key == 'blocks' and value == 'ffff'):
                raise ValueError('non-integer trace field')
            fields[key] = int(value, 16 if key == 'blocks' else 10)
        records.append((line.split()[0], fields))
    reset = False; primes = []; all128 = False; gates = []; descriptors = []
    pending = None; counts = dict(reads=0, returns=0, writes=0, acks=0)
    endpoint = False; terminal = False; previous = -1
    shapes = {
      'D1_RESET_ACCEPT': {'time_ps','rn'},
      'D1_QUALIFIED_PRIME': {'time_ps','row','rn','valid','active','tag','user','blocks'},
      'D1_ALL128_PRIMED': {'time_ps','accepted','rn'},
      'D1_REAL_GATE': {'time','pc','me_ready','kv_ok','kvd_v','win_idle','waited','q_gate','m0_gate'},
      'D1_REAL_DESCRIPTOR': {'time','generation','rows'},
      'D1_REAL_ACCEPT': {'time','address','tag','write'},
      'D1_REAL_RESPONSE': {'time','tag','beat'},
      'D1_REAL_WRITER_ACK': {'time'},
      'D1_PREFIX_GATE_AND_FIRST_RETURN_ONLY': {'reads','returns','writes','acks'},
      'D1_TERMINAL_PREFIX_ONLY': {'evals','time_ps','cycles'},
      'D1_HEARTBEAT': {'evals','time_ps','cycles'},
      'D1_REAL_DROP_KV_OK_COUNTEREXAMPLE': {'source_issue','mutated_predicate'},
    }
    for kind, f in records:
        if kind not in shapes or set(f) != shapes[kind]: raise ValueError('unknown or malformed marker')
        if terminal: raise ValueError('event after terminal')
        if kind == 'D1_HEARTBEAT': continue
        if kind == 'D1_REAL_DROP_KV_OK_COUNTEREXAMPLE':
            # Existing marker mixes sampled target and post-NBA fields; no same-phase issue proof.
            if f != {'source_issue':0,'mutated_predicate':1}: raise ValueError('bad mutation marker')
            continue
        t = f.get('time_ps', f.get('time', previous))
        if t < previous: raise ValueError('event time reversal')
        previous = t
        if kind == 'D1_RESET_ACCEPT':
            if reset or f != {'time_ps':6000,'rn':1}: raise ValueError('reset acceptance mismatch')
            reset = True
        elif kind == 'D1_QUALIFIED_PRIME':
            row = len(primes)
            expected = {'time_ps':7501+row*1000,'row':row,'rn':1,'valid':1,'active':1,
                        'tag':row,'user':0,'blocks':65535}
            if not reset or all128 or row >= 128 or f != expected: raise ValueError('unqualified row commit')
            primes.append(f)
        elif kind == 'D1_ALL128_PRIMED':
            if all128 or len(primes) != 128 or f != {'time_ps':134501,'accepted':128,'rn':1}:
                raise ValueError('all128 commit mismatch')
            all128 = True
        elif kind == 'D1_REAL_GATE':
            if not all128: raise ValueError('gate before priming')
            for key in shapes[kind] - {'time','pc'}:
                if f[key] not in (0,1): raise ValueError('gate not boolean')
            if f['pc'] >= 16384: raise ValueError('PC width')
            gates.append(f)
        elif kind == 'D1_REAL_DESCRIPTOR':
            if not all128 or not gates or f['rows'] != 128 or f['generation'] >= 2**16:
                raise ValueError('descriptor provenance/geometry')
            descriptors.append(f)
        elif kind == 'D1_REAL_ACCEPT':
            if not descriptors or pending is not None or endpoint or f['write'] not in (0,1):
                raise ValueError('unowned or duplicate accept')
            if f['address'] >= 2**30 or f['tag'] >= 2**16: raise ValueError('packet width')
            pending = f
            counts['writes' if f['write'] else 'reads'] += 1
        elif kind == 'D1_REAL_RESPONSE':
            if pending is None or pending['write'] or f['tag'] != pending['tag'] or f['beat'] != 0:
                raise ValueError('unowned response')
            counts['returns'] += 1; pending = None
        elif kind == 'D1_REAL_WRITER_ACK':
            if pending is None or not pending['write']: raise ValueError('unowned writer ACK')
            counts['acks'] += 1; pending = None
        elif kind == 'D1_PREFIX_GATE_AND_FIRST_RETURN_ONLY':
            if endpoint or pending is not None or not gates or not descriptors or counts['returns'] < 1 or f != counts:
                raise ValueError('endpoint/count mismatch')
            endpoint = True
        elif kind == 'D1_TERMINAL_PREFIX_ONLY':
            if not endpoint: raise ValueError('terminal without causal endpoint')
            terminal = True
    if not all128 or not endpoint or not terminal: raise ValueError('missing healthy witness or endpoint')
    return {'status':'PASS_EXPERIMENTAL_FIXTURE_NATIVE_PREFIX_ONLY','reset_qualified_rows':128,
            'gate_samples':len(gates),'descriptors':descriptors,'counts':counts,
            'actual_endpoint':'GATE_SEEN_AND_FIRST_RETURN_NO_PENDING','service_bound':'BOUND_MISSING',
            'first_return_deadline':None,'fulltoken':False,'RTL_fidelity':'UNPROVEN',
            'original_PC24_cause':'UNOBSERVED','I66_program_origin':None,'coll_busy':None,
            'writer_identity':'NOT_EXPORTED_BY_ACK_MARKER','I66_calendar_used':False,
            'me_go_same_phase_value':'NOT_EXPORTED; source guard remains authoritative'}

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('log');p.add_argument('--exit-code',type=int,required=True)
    a=p.parse_args();print(json.dumps(verify(Path(a.log).read_text(),a.exit_code),indent=2))
