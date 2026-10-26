"""Compile published HEAD8 offsets into a symbolic boot/mission contract.

A missing die START producer remains an explicit blocker. This does not assign
bootstrap roles, install missing providers, or claim a head token pass.
"""
import argparse
import hashlib
import json
from pathlib import Path


def compile_contract(plan, offsets):
    if plan.get('reset',{}).get('start')!='broadcast' or offsets.get('start',{}).get('mode')!='broadcast':
        raise ValueError('explicit broadcast plan and matching published offsets required')
    types=plan['partition_types']; rows={}
    instances={p['name']:p for p in plan['partitions']}
    if set(offsets['parts']) != set(instances):
        raise ValueError('published offsets must cover the exact selected partition set')
    for name, part in offsets['parts'].items():
        # Published wavefront output includes hard partitions which have no START input.
        tn=part.get('type')
        if tn is None:
            inst=instances[name]
            tn=inst['type']
        if tn != instances[name]['type']:
            raise ValueError(f'{name}: published type differs from selected plan')
        role=types[tn].get('reset',{}).get('start_role','mission')
        release=part['release']
        hard=bool(types[tn].get('hard'))
        rows[name]=dict(type=tn,role='raw_hard_reset' if hard else role,reset_release=release,
            mission_release=f'max({release}, S+{release})' if not hard else None,
            control_release=release if hard or role=='bootstrap' else f'max({release}, S+{release})',
            start_offset=None if hard else release)
    return dict(kind='HEAD8_SYMBOLIC_SOURCE_CONTRACT',parts=rows,die_START_edge=None,
        die_START_edge_status='UNRESOLVED: actual selected controller/host boot completion must drive S',
        required_BOOT_roles='No role inferred from a type name; bootstrap needs a real mission-admission input',
        element_GO=dict(pin_capture_after_delivered_reset=3,command_accept_after_delivered_reset=4,
            activation_word_a_after_GO_pin='6+a',relationship_to_die_START='separate command; no alias'),
        adoption='BLOCKED pending actual provider/source composition, boot S/roles, geometry/clock gates',
        steady_state_cycles_added_by_contract=0)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('plan',type=Path); ap.add_argument('offsets',type=Path); ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args(); result=compile_contract(json.loads(a.plan.read_text()),json.loads(a.offsets.read_text()))
    result['inputs']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (a.plan,a.offsets)}
    a.out.write_text(json.dumps(result,indent=2)+'\n'); print(a.out)
if __name__=='__main__':main()
