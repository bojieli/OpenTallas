"""Offline descriptor guards. No execution, source mutation or deadline credit."""
import re


def _integer(packet, key, width):
    value = packet[key]
    if type(value) is not int or not 0 <= value < 2**width:
        raise ValueError(f'{key}: invalid unsigned field')
    return value


def validate_descriptor(sample, event):
    """Require a pre-NBA sample and same-edge lifecycle acceptance identity.

    Core ME issue and packed descriptor acceptance are distinct source events.
    This schema is a future observation requirement, not fields retrofitted to
    the retained journal. Exact geometry is the frozen L0 QK fixture only.
    """
    widths = dict(time_ps=64, phase=1, rn=1, life_state=3, last_gen=16,
                  desc_v=1, kvd_v=1, retain_l0=1, hbm_attention=1,
                  start_ready=1, service_busy=1, service_fault=1, stage_v=1,
                  beat_v=1, beat_ready=1, wrap_drained=1, user=10, pos=21,
                  tiles=21, k=21, nout=21, wbase=30, ts=30, ks=30, js=30,
                  hg=2, mmode=1, window_region_ok=1)
    if set(sample) != set(widths):
        raise ValueError('same-phase source fields missing or extra')
    if set(event) != {'time_ps', 'phase', 'generation', 'rows', 'user', 'pos'}:
        raise ValueError('descriptor identity fields missing or extra')
    s = {key: _integer(sample, key, width) for key, width in widths.items()}
    e = {key: _integer(event, key, width) for key, width in
         dict(time_ps=64, phase=1, generation=16, rows=11, user=10, pos=21).items()}
    if s['phase'] != 0 or (e['time_ps'], e['phase']) != (s['time_ps'], s['phase']):
        raise ValueError('stale or non-pre-NBA source sample')
    desc_v = s['kvd_v'] and (not s['retain_l0'] or not s['hbm_attention'] or
                             s['start_ready'] or s['service_busy'])
    if not s['rn'] or s['life_state'] != 0 or not desc_v or s['desc_v'] != desc_v:
        raise ValueError('source descriptor admission guard false')
    if s['service_fault'] or s['stage_v'] or (s['beat_v'] and s['beat_ready']):
        raise ValueError('source lifecycle fault has precedence')
    if s['last_gen'] == 65535 and not s['wrap_drained']:
        raise ValueError('generation wrap not drained')
    generation = 1 if s['last_gen'] == 65535 else s['last_gen'] + 1
    rows = s['nout'] if s['ks'] == 1 else s['k']
    if not s['mmode'] or rows != 128 or s['pos'] < 127:
        raise ValueError('source L0 descriptor shape invalid')
    if (e['generation'], e['rows'], e['user'], e['pos']) != (generation, rows, s['user'], s['pos']):
        raise ValueError('same-phase generation/descriptor identity mismatch')
    if not s['window_region_ok'] or not s['hbm_attention']:
        raise ValueError('selected WINDOW provider start unqualified')
    return dict(status='PASS_MODEL_DESCRIPTOR_ACCEPTANCE_ONLY', core_ME_admission='NOT_IMPLIED',
                service_bound='BOUND_MISSING', fulltoken=False)


def legacy_descriptor_status(text):
    """Reject stale/all-false trace gates without manufacturing absent fields."""
    gates = {}
    found = 0
    for line in text.splitlines():
        if not line.startswith(('D1_REAL_GATE ', 'D1_REAL_DESCRIPTOR ')):
            continue
        fields = {key: int(value) for key, value in re.findall(r'(\w+)=(\d+)', line)}
        if line.startswith('D1_REAL_GATE '):
            gates[fields['time']] = fields
        else:
            found += 1
            gate = gates.get(fields['time'])
            if gate is None or gate.get('kvd_v') != 1:
                raise ValueError('descriptor requires same-edge asserted kvd_v, not any prior gate')
    if found != 1:
        raise ValueError('expected one retained descriptor')
    return dict(status='UNBOUND_DESCRIPTOR_CAUSAL_PROVENANCE',
                missing=['rn/pre-NBA phase', 'life_state/last_gen', 'service_start_ready/busy',
                         'lifecycle fault/shape priority', 'descriptor user/position identity'],
                core_ME_admission='NOT_OBSERVED', service_bound='BOUND_MISSING', fulltoken=False)

if __name__ == '__main__':
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal', type=Path)
    args = parser.parse_args()
    print(json.dumps(legacy_descriptor_status(args.journal.read_text()), indent=2))


def verify_causal_first_return(text, exit_code, sample, event, read_owner):
    """Future strict entrypoint; retained trace cannot supply read_owner fields.

    A caller must obtain these fields from a same-edge source observation,
    not infer them from tag, PC, or the later final snapshot.
    """
    from tools.w17_D1_reset_qualified_runtime_verify import verify
    validate_descriptor(sample, event)
    widths = dict(time_ps=64, generation=16, user=10, pos=21,
                  address=30, tag=16, write=1, phase=1)
    if set(read_owner) != set(widths):
        raise ValueError('same-edge read owner association missing')
    r = {key: _integer(read_owner, key, width) for key, width in widths.items()}
    if r['phase'] != 0 or r['write'] != 0 or r['time_ps'] <= event['time_ps']:
        raise ValueError('read phase/order invalid')
    if tuple(r[k] for k in ('generation','user','pos')) != tuple(event[k] for k in ('generation','user','pos')):
        raise ValueError('read belongs to different descriptor generation/identity')
    descriptors = re.findall(r'^D1_REAL_DESCRIPTOR time=(\d+) generation=(\d+) rows=(\d+)$', text, re.M)
    accepts = re.findall(r'^D1_REAL_ACCEPT time=(\d+) address=(\d+) tag=(\d+) write=(\d+)$', text, re.M)
    if descriptors != [tuple(str(event[k]) for k in ('time_ps','generation','rows'))]:
        raise ValueError('descriptor packet/journal mismatch')
    if accepts != [tuple(str(r[k]) for k in ('time_ps','address','tag','write'))]:
        raise ValueError('read owner packet/journal mismatch')
    legacy_descriptor_status(text)  # No stale or all-false gate accepted.
    result = verify(text, exit_code)
    result['descriptor_provenance'] = 'MODEL_SCHEMA_CHECKED_SOURCE_PACKET_REQUIRED'
    result['core_ME_admission'] = 'NOT_IMPLIED'
    return result
