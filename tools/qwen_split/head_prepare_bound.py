#!/usr/bin/env python3
"""Price HEAD_PREP from a bound die, preserving actual landed field identities.

Exports a component age only. It neither selects a programme nor inherits a GEN
calendar. Unqualified/missing members cannot fall back to nominal bus depths.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

PREP = {'head_prepare_v': ('tt_ctlm.emb_start', 1),
        'head_prepare_token': ('tt_ctlm.emb_token', 18),
        'head_prepare_position': ('tt_ctlm.emb_position', 18),
        'head_prepare_user': ('tt_ctlm.emb_user', 2)}
DESC = {'head_descriptor_v': ('native59.head_descriptor_v', 1),
        'head_descriptor_tag': ('native59.head_descriptor_tag', 59),
        'head_descriptor_generation': ('native59.head_descriptor_generation', 2)}

HOST = {'host_epoch_valid': ('sys_face.host_epoch_valid', 1),
        'host_fused_capability': ('sys_face.host_fused_capability', 1),
        'host_epoch': ('sys_face.host_epoch', 16),
        'host_tag': ('sys_face.host_tag', 59),
        'host_generation': ('sys_face.host_generation', 2)}


def tuple_age(groups, sink, fields):
    found = {}
    for group in groups['landing']:
        if group['sink'] != sink:
            continue
        for row in group['members']:
            port = row['sink_port']
            if port not in fields:
                continue
            source, width = fields[port]
            if (port in found or row['source'] != source or
                    row['sink_bits'] != [[0, width-1]] or row['source_bits'] != [[0, width-1]]):
                raise ValueError('missing/duplicate/wrong HEAD_PREP tuple identity: ' + port)
            age = row.get('landed_stages')
            if type(age) is not int or age < 0:
                raise ValueError('actual landed age required: ' + port)
            found[port] = age
    if set(found) != set(fields) or len(set(found.values())) != 1:
        raise ValueError('incomplete or unequal landed HEAD_PREP tuple: ' + sink)
    return next(iter(found.values())), found


def selected(bound, filename, instance):
    text = (bound/'rtl'/filename).read_text()
    names = re.findall(r'\b(qfd_\w+)\s+' + re.escape(instance) + r'\s*\(', text)
    if len(names) != 1:
        raise ValueError('unique actual selected child required: ' + instance)
    return names[0]


def source_match(root, inventory, master, expected_path):
    expected = root/expected_path
    paths = set(inventory['full'] + inventory['lib'])
    defining = [Path(p) for p in paths if Path(p).is_file() and
                re.search(r'\bmodule\s+' + re.escape(master) + r'\b', Path(p).read_text())]
    if len(defining) != 1 or defining[0].read_bytes() != expected.read_bytes():
        raise ValueError('actual elaboration source differs or is ambiguous: ' + master)
    return hashlib.sha256(expected.read_bytes()).hexdigest()


def wrapper_boundary(root):
    # Only the exact boundary source/capture witness applies here. The historic
    # inner hierarchy/ROM programme is deliberately not qualified by this age.
    from sysface_lctx_source import WRAPPER_BINDING, WRAPPER_MASTER, WRAPPER_SHA256
    binding = json.loads((root/WRAPPER_BINDING).read_text())
    path = root/binding['source_path']
    proof = json.loads((root/'results/arch/codex_sysface_l_2000/wrapper_capture_receipt.json').read_text())
    cases = {x['case']: x['returncode'] for x in proof['results']}
    if (binding['master'] != WRAPPER_MASTER or binding['input_capture_edges'] != 1 or
            binding['output_capture_edges'] != 1 or hashlib.sha256(path.read_bytes()).hexdigest() != WRAPPER_SHA256 or
            proof['wrapper_sha256'] != WRAPPER_SHA256 or cases.get('selected') != 0 or
            any(cases.get(x) not in (1, 2) for x in ('wrong_source_mutant', 'extra_capture_edge_mutant'))):
        raise ValueError('actual wrapper boundary capture source/witness differs')
    return dict(source=binding['source_path'], input_capture_edges=1, output_capture_edges=1,
                scope='exact boundary capture only; inner hierarchy/ROM programme not inherited')


def host_join(prepare_capture_edge, token, position, host, filler_output_edges=()):
    """Compile the actual user0 pending/HOST join at core-published p_* pins.

    No HOST path age is invented here. All dates are already at those pins;
    board-to-core transport and programme identity remain caller obligations.
    """
    keys = ('first_core_edge', 'last_core_edge', 'tag', 'epoch', 'generation', 'fused_capability', 'interval_basis')
    if host is None or any(k not in host for k in keys):
        raise ValueError('actual core-published HOST cohort interval/identity required')
    if (type(prepare_capture_edge) is not int or prepare_capture_edge < 0 or
            type(token) is not int or not 0 <= token < 151936 or
            type(position) is not int or not 0 <= position < 8192):
        raise ValueError('invalid static prepare date/token/position')
    first, last, tag, epoch, generation = (host[k] for k in keys[:5])
    if (any(type(x) is not int for x in (first,last,tag,epoch,generation)) or
            first < 0 or last < first or not 0 <= tag < 1 << 59 or
            not 0 <= epoch < 1 << 16 or not 0 <= generation < 4 or
            host['fused_capability'] is not True):
        raise ValueError('invalid explicit HOST core interval/identity')
    if (tag >> 43 != epoch or (tag >> 19) & ((1 << 18)-1) != token or
            (tag >> 6) & 8191 != position or (tag >> 37) & 63 or tag & 63):
        raise ValueError('HOST tuple does not match actual pending prepare')
    if any(type(c) is not int or c < 0 for c in filler_output_edges):
        raise ValueError('actual static filler output dates required')
    basis=host['interval_basis']
    if basis not in ('pre_edge_sampling', 'post_edge_publication'):
        raise ValueError('explicit HOST publication/sampling interval basis required')
    sample_shift=1 if basis=='post_edge_publication' else 0
    date = max(prepare_capture_edge + 3, first + sample_shift)
    busy = set(filler_output_edges)
    while date in busy:
        date += 1
    if date > last + sample_shift:
        raise ValueError('HOST valid interval ends before legal pending/cohort publication')
    return dict(descriptor_core_edge=date, descriptor_tag=tag,
                descriptor_generation=generation, status='CORE_PIN_COMPONENT_JOIN_ONLY',
                runtime_waiting=False)


def host_core_interval(host_at_sysface, bound_component):
    """Shift an explicit source-published interval; never invent its origin."""
    if host_at_sysface is None or host_at_sysface.get('endpoint') != 'sys_face.host_tuple':
        raise ValueError('actual sysface HOST publication interval required')
    row = dict(host_at_sysface)
    if row.get('interval_basis') != 'post_edge_publication':
        raise ValueError('actual sysface post-edge publication basis required')
    for key in ('first_core_edge', 'last_core_edge'):
        if type(row.get(key)) is not int or row[key] < 0:
            raise ValueError('explicit sysface HOST interval endpoint required')
    if row['last_core_edge'] < row['first_core_edge']:
        raise ValueError('reversed sysface HOST interval')
    ages = bound_component['landed_fields']['host']
    if set(ages) != set(HOST) or len(set(ages.values())) != 1:
        raise ValueError('all five coherent bound HOST fields required')
    delay = bound_component['edges']['host_to_native'] + bound_component['edges']['native_host_capture']
    if (set(ages.values()) != {bound_component['edges']['host_to_native']} or
            bound_component['edges']['native_host_capture'] != 1):
        raise ValueError('actual RECV_INPUTS0 HOST capture profile required')
    row['first_core_edge'] += delay
    row['last_core_edge'] += delay
    row['endpoint'] = 'native59.u_svc.p_HOST'
    row['transport_capture_edges'] = delay
    row['interval_basis'] = 'post_edge_publication'
    return row


def measure(bound, root, receipt):
    bound, root = Path(bound), Path(root).resolve()
    sys.path.insert(0, str(root/'tools/qwen_split'))
    from tt_source_local import source_local_edges
    tt = selected(bound, 'qfd_qc_tt_ctlm_part.sv', 'u_core')
    native = selected(bound, 'qfd_qc_native59_part.sv', 'u_core')
    face = selected(bound, 'qfd_qc_glue_part.sv', 'u_sys_face')
    if native != 'qfd_native59_dv_headprep_obs1' or face != 'qfd_sys_face_lctx3_wrapped':
        raise ValueError('unqualified native/held-face intrinsic implementation')
    local, witness = source_local_edges(root, tt, receipt)
    wrapper = wrapper_boundary(root)
    inventory = json.loads((bound/'asbuilt_sources.json').read_text())
    row = json.loads(Path(receipt).read_text())
    source_match(root, inventory, tt, row['rtl'])
    source_match(root, inventory, face, wrapper['source'])
    source_match(root, inventory, native, 'rtl/qwen_split/qfd_native59_dv_headprep_obs1.sv')
    native_files=[Path(p) for p in inventory['lib'] if Path(p).name=='qfd_native59_dv_headprep_obs1.sv']
    service=root/'rtl/qwen_split/qfd_native59_svc_obs1.sv'
    if len(native_files)!=1 or native_files[0].with_name(service.name).read_bytes()!=service.read_bytes():
        raise ValueError('actual native prepare/cohort child source differs')
    groups = json.loads((bound/'bus_groups.json').read_text())
    prep, prep_fields = tuple_age(groups, 'native59', PREP)
    desc, desc_fields = tuple_age(groups, 'sys_face', DESC)
    host, host_fields = tuple_age(groups, 'native59', HOST)
    native_text=(root/'rtl/qwen_split/qfd_native59_dv_headprep_obs1.sv').read_text()
    if 'SVC_RECV=0' not in native_text or '.RECV_INPUTS(SVC_RECV)' not in native_text:
        raise ValueError('actual native default RECV_INPUTS0 capture path required')
    total = local + prep + 3 + desc + wrapper['input_capture_edges'] + 1
    from head_record_timing import emitted
    protocol_paths = emitted(bound, paths_only=True)
    return dict(schema='opentallas.qwen.bound_head_prepare_age.v1',
                status='BOUND_COMPONENT_AGE_NOT_PROGRAMME_QUALIFIED',
                selected_masters=dict(tt=tt, native=native, face=face),
                tt_source=witness, landed_fields=dict(prepare=prep_fields, descriptor=desc_fields, host=host_fields),
                internal_protocol_edges=protocol_paths,
                edges=dict(tt_local=local, tt_to_native=prep, native_prepare_descriptor=3,
                           native_to_face=desc, host_to_native=host, native_host_capture=1, face_input=wrapper['input_capture_edges'], face_held_bank=1),
                filler_head_prepare_edges=total, user0_prepare_only_min_edges=total+1,
                head_prepare_edges=None, calendar_installable=False,
                programme_blockers=['actual core-published HOST cohort interval/identity',
                                    'shared programme-record producer capture age and callback alignment',
                                    'selected current programme and producer reservation'],
                scope='Calendar sample to held bank only; HOST cohort availability, selected programme and outgoing face capture remain separate')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bound', required=True);p.add_argument('--source-root', required=True)
    p.add_argument('--tt-source-receipt', required=True);p.add_argument('--out', required=True)
    a = p.parse_args()
    try:
        result = measure(a.bound, a.source_root, a.tt_source_receipt)
    except (ValueError, OSError, KeyError) as e:
        result = dict(status='BLOCKED', reason=str(e))
    Path(a.out).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result));return 2 if result['status']=='BLOCKED' else 0

if __name__ == '__main__':
    raise SystemExit(main())
