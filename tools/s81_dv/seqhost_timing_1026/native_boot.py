#!/usr/bin/env python3
"""Encode explicit current atomic seqhost MU boot and validate KS pin dates.

This supplies only CSR0x15/0x16 words. Calendar, template, descriptor and
physical reset/transport bookings remain the caller's responsibilities.
"""
import argparse
import hashlib
import json
from pathlib import Path


def uint(value, bits, name):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError(name+': explicit unsigned '+str(bits)+'-bit integer required')
    return value


def compile_boot(config, receipt, *, allow_unbooked_launch=False):
    if config['schema'] != 'opentallas.s81.seqhost_native_boot.v1':
        raise ValueError('unsupported explicit boot configuration schema')
    if receipt['schema'] != 'opentallas.s81.bound_control_local.v1' or receipt['verdict'] != 'PASS':
        raise ValueError('current local timing PASS receipt required')
    master = receipt['masters']['dsdv_hostb_seqhost_mux']
    if master['params'] != dict(HOSTB_ENABLE=0, STATIC_KS6=0):
        raise ValueError('boot encoder qualified only for selected direct native mux')
    gaps = [uint(x, 24, 'slot gap') for x in config['slot_gaps']]
    # One gap selects all47 slots in the RTL; two or more selects actual length.
    if not 1 <= len(gaps) <= 47:
        raise ValueError('actual tracker requires1..47 gap words')
    slots = 47 if len(gaps) == 1 else len(gaps)
    rl = uint(config['return_latency'], 24, 'return latency')
    if min(gaps) <= slots+1 or rl <= slots:
        raise ValueError('slot gap/RL violates actual hslot/hwin arming conditions')
    slot_gaps = gaps * slots if len(gaps) == 1 else gaps
    period = sum(slot_gaps)
    slot_offsets = [sum(slot_gaps[:i]) for i in range(slots)]
    if rl > period:
        raise ValueError('slot table wraps before an outstanding start retires')
    kit = uint(config['kit_issue'], 24, 'KIT issue')
    offset = master['edges']['f_ks_pin_event_plus_kit_issue_to_t_kd']
    # hslot's RL is measured from KS sampling, one edge after the pin event.
    if rl != kit+offset-1:
        raise ValueError('return latency differs from measured selected KIT return')
    words = []
    def word(op, payload):
        words.append(((op | (payload << 32)) << 1) | 1)
    for gap in gaps:
        word(0x15, (1 << 25) | gap)
    word(0x15, (1 << 25) | (1 << 24) | rl)
    events = config['events']
    if len(events) != 8:
        raise ValueError('actual mux requires all8 explicit HWIN event rows')
    output_dates = set()
    for index, event in enumerate(events):
        kind = uint(event['kind'], 1, 'event kind')
        endpoint = uint(event['endpoint'], 2, 'event endpoint')
        delay = uint(event['delay'], 21, 'event delay')
        attrs = event['attributes']
        if not slots+2 <= delay <= rl-2 or len(attrs) != slots:
            raise ValueError('event delay/slot attributes violate actual HWIN bounds')
        word(0x16, (1 << 25) | index | (kind << 8) | (endpoint << 9))
        word(0x16, (1 << 25) | (1 << 21) | delay)
        for slot, attr in enumerate(attrs):
            ab = uint(attr['ab'], 1, 'event copy')
            land = uint(attr['land'], 1, 'event replay enable')
            if kind == 0 or land:
                key = (kind, endpoint, (slot_offsets[slot]+delay) % period)
                if key in output_dates:
                    raise ValueError('two events drive one actual endpoint on the same edge')
                output_dates.add(key)
            word(0x16, (1 << 25) | (2 << 21) | slot | (ab << 10) | (land << 11))
    launch = config.get('launch')
    if launch is None:
        if not allow_unbooked_launch:
            raise ValueError('actual launch booking required unless local encoding is explicitly unbooked')
        if 'seqhost_input_clock' not in receipt:
            raise ValueError('unbooked local encoding still requires actual reset/KS phase contract')
    else:
        reset_edge = uint(launch['reset_release_pin_edge'], 48, 'reset release pin edge')
        ks = [uint(x, 48, 'KS pin edge') for x in launch['ks_pin_edges']]
        phase = receipt['seqhost_input_clock']['accepted_ks_pin_event_offset_from_reset_release_pin_event_mod4']
        if not ks or any(x <= reset_edge or (x-reset_edge) % 4 != phase for x in ks):
            raise ValueError('KS pin date violates selected issuer phase relative to reset release')
        for index, (a, b) in enumerate(zip(ks, ks[1:])):
            if b-a != gaps[index % len(gaps)]:
                raise ValueError('KS pin dates differ from explicit slot gap calendar')
    return words, dict(schema='opentallas.s81.seqhost_native_boot_emission.v1',
        status='ENCODED', words=len(words), slots=slots, kit_issue=kit,
        return_latency=rl, launch=launch, launch_booked=launch is not None,
        pin_event_convention=receipt['edge_convention'],
        required_relative_KS_phase=receipt['seqhost_input_clock']['accepted_ks_pin_event_offset_from_reset_release_pin_event_mod4'],
        source_sha256=receipt['source_sha256'], params=master['params'], defines=master['defines'],
        obligations=['boot all words while actual tracker unarmed and no outstanding starts',
                     'caller books actual host-word transport and reset release pin event',
                     'caller supplies actual8window events and matching incoming descriptors'],
        full_token=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config', type=Path, required=True)
    ap.add_argument('--local-receipt', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    words, emission = compile_boot(json.loads(a.config.read_text()), json.loads(a.local_receipt.read_text()))
    a.out.mkdir(parents=True, exist_ok=False)
    payload = ''.join(f'{x:0129x}\n' for x in words)
    (a.out/'mux_boot.memh').write_text(payload)
    emission['payload_sha256'] = hashlib.sha256(payload.encode()).hexdigest()
    emission['config_sha256'] = hashlib.sha256(a.config.read_bytes()).hexdigest()
    emission['local_receipt_sha256'] = hashlib.sha256(a.local_receipt.read_bytes()).hexdigest()
    (a.out/'manifest.json').write_text(json.dumps(emission, indent=1)+'\n')
    print('NATIVE_MUX_BOOT ENCODED', len(words), 'words')


if __name__ == '__main__':
    main()
