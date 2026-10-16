#!/usr/bin/env python3
"""Reversible top-down MIX4-E/VM-W candidate; never edits a contract or recipe."""
import argparse
import copy
import hashlib
import json
import math
import re
from pathlib import Path

WIDTHS = dict(rq_v=20, rq_row=280, rs_v=20, rs_d=10240,
              wq_v=4, wq_row=56, wq_mask=64, wq_d=2048)


def validate(logic, mix, vm, offset):
    seen = set()
    for g in logic['groups']:
        for name in g['ordered_logical_ports']:
            port, bit = re.fullmatch(r'(\w+)\[(\d+)\]', name).groups()
            bit = int(bit)
            if name in seen or port not in WIDTHS or not 0 <= bit < WIDTHS[port]:
                raise ValueError('duplicate or unexpected logical pin: ' + name)
            seen.add(name)
            left = mix['ports'][port]['per_bit'][bit]
            right = vm['ports'][logic['VM_parent_port_aliases'][port]]['per_bit'][bit]
            if left[:2] != ['E', 'M4'] or right[:2] != ['W', 'M4']:
                raise ValueError('not an opposing E/W M4 pair: ' + name)
            if abs(left[2] - right[2] + offset) > 1e-6:
                raise ValueError('peer bit coordinate mismatch: ' + name)
            if abs((left[2] - .012) / .048 - round((left[2] - .012) / .048)) > 1e-6:
                raise ValueError('off track: ' + name)
    expected = {f'{p}[{i}]' for p, w in WIDTHS.items() for i in range(w)}
    if seen != expected:
        raise ValueError('incomplete 12732-bit interface')
    return len(seen)


def create(logic, base_vm, hub):
    if len(logic['groups']) != 4 or logic['bits'] != sum(WIDTHS.values()):
        raise ValueError('incorrect full-shape logical interface')
    mx, vv = hub['mix4_slot'], hub['blocks']['sp_vm']
    offset = mx[1] - vv[1]
    vm = copy.deepcopy(base_vm)
    vm.update(case='candidate_mix4_vm_joint_1016', adopted=False,
              status='CANDIDATE_ONLY_NOT_NATIVE_OR_ROUTED',
              parent_integration='All existing capture pins retained; new W interface requires actual source/clock/registered child proof.')
    mix = dict(schema='opentallas.s81.assigned_pins.v1', master='dsfd_engram_mix4_c',
               case='candidate_mix4_vm_joint_1016', outline_um=[mx[2] - .024, mx[3] - .024],
               adopted=False, status='CANDIDATE_ONLY_NOT_NATIVE_OR_ROUTED',
               unassigned='Clock/reset/status/command pins require separate actual source-bound assignment.', ports={})
    for port, width in WIDTHS.items():
        alias = logic['VM_parent_port_aliases'][port]
        mix['ports'][port] = dict(bits=width, uniform=False, per_bit=[None] * width)
        vm['ports'][alias] = dict(bits=width, uniform=False, per_bit=[None] * width)
    bands = []
    for q, group in enumerate(logic['groups']):
        names = group['ordered_logical_ports']
        if group['physical_VM_group'] != q or len(names) != 3183 or group['bits'] != 3183:
            raise ValueError('incorrect physical VM group')
        digest = hashlib.sha256(('\n'.join(names) + '\n').encode()).hexdigest()
        expected = {f'{p}[{i}]' for p, w in WIDTHS.items()
                    for i in range(q * (w // 4), (q + 1) * (w // 4))}
        if digest != group['logical_order_sha256'] or set(names) != expected:
            raise ValueError('source logical order/group mismatch')
        # Snap each quarter independently onto the real 48-nm lattice. Five
        # tracks/bit leaves explicit face margin; it does not prove routing cuts.
        quarter = math.floor(q * mx[3] / 4 / .048 + .5) * .048
        start = round(quarter + 74.736 + .012, 3)
        for k, name in enumerate(names):
            port, bit = re.fullmatch(r'(\w+)\[(\d+)\]', name).groups()
            bit = int(bit)
            y = round(start + k * .240, 3)
            alias = logic['VM_parent_port_aliases'][port]
            if mix['ports'][port]['per_bit'][bit] is not None:
                raise ValueError('duplicate bit: ' + name)
            mix['ports'][port]['per_bit'][bit] = ['E', 'M4', y, .192]
            vm['ports'][alias]['per_bit'][bit] = ['W', 'M4', round(y + offset, 3), .192]
        bands.append(dict(physical_VM_group=q, bits=3183, first_local_y_um=start,
                          last_local_y_um=round(start + 3182 * .240, 3),
                          logical_order_sha256=group['logical_order_sha256']))
    validate(logic, mix, vm, offset)
    unchanged = {p for p in base_vm['ports'] if p not in logic['VM_parent_port_aliases'].values()}
    assert all(vm['ports'][p] == base_vm['ports'][p] for p in unchanged)
    report = dict(schema='opentallas.s81.mix4_vm_joint_pin_candidate.v1',
        source_commit=logic['source_commit'], status='CANDIDATE_ONLY_NOT_ADOPTED',
        source_geometry='17b13fb0637869d53580a1084bdd250d18828d9b vmc_26b',
        logical_bits=12732, exact_peer_jog_um=0, pitch_um=.240, layer='M4',
        nominal_seam_um=round(vv[0] - mx[0] - mx[2], 3),
        post_shave_candidate_seam_um=round(vv[0] - mx[0] - mix['outline_um'][0], 3),
        same_layer_face_pin_fraction=round(12732 * .048 / mix['outline_um'][1], 6),
        bands=bands, preserved_existing_VM_ports=sorted(unchanged),
        dependency_rules=logic['dependency_rules'],
        missing=['Source-current full native interleaf graph including H transpose, V broadcast and write transpose',
                 'Actual pin-registered launch/capture, clock/reset/status/command allocation and all incident stages',
                 'Real internal/channel cut occupancy with LEF obstructions and PG, no over-hardmacro layer assumption',
                 'VM XIO/WFC/payload/header hardening and any consequent outline change',
                 'All TT setup/FF hold/DRC0 and exact static-calendar/full native workload qualification'],
        warnings=['Face pin fraction is geometry only, NOT a measured route cut.',
                  'Four groups are physical VM lanes, NEVER four independent compute copies.',
                  'Current c26b/26n snapshots and daily contract/recipes are unchanged.',
                  'MIX4 record covers data interface only; importing it does not bind all master ports.'])
    return mix, vm, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--logical', type=Path, required=True)
    p.add_argument('--vm-base', type=Path, required=True)
    p.add_argument('--hub', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    logic = json.loads(a.logical.read_text())
    mix, vm, report = create(logic, json.loads(a.vm_base.read_text()), json.loads(a.hub.read_text()))
    report['input_sha256'] = {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.logical, a.vm_base, a.hub)}
    a.out.mkdir(parents=True, exist_ok=True)
    for name, record in [('dsfd_engram_mix4_c.json', mix), ('dsfd_sp_vm.json', vm), ('candidate_receipt.json', report)]:
        (a.out / name).write_text(json.dumps(record, indent=1) + '\n')
    # A deliberately shifted physical VM bit must fail even though all counts,
    # widths and logical names remain correct.
    mutant = copy.deepcopy(vm)
    mutant['ports']['t_mx_rs']['per_bit'][0][2] += .048
    hub = json.loads(a.hub.read_text())
    offset = hub['mix4_slot'][1] - hub['blocks']['sp_vm'][1]
    try:
        validate(logic, mix, mutant, offset)
    except ValueError as error:
        assert 'coordinate mismatch' in str(error)
    else:
        raise AssertionError('shifted peer mutant survived')
    print('PASS 12732 exact paired coordinates; existing VM pins unchanged; shifted-bit mutant FAIL')


if __name__ == '__main__':
    main()
