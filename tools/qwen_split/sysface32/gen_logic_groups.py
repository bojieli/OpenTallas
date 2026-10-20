"""Generate an opt-in SYSFACE combinational mapping experiment.

Every sequential helper and its hierarchy is preserved. Only combinational
helper boundaries may flatten, so ABC can map Boolean cones together. Actual
native fanout, depth, retained state and protocol still require measurement.
"""
import hashlib
import json
import re
from pathlib import Path

COMB = ('and', 'or', 'xor', 'not', 'mux')


def generate(repo, record_only=False):
    repo = Path(repo)
    rtl = repo / 'rtl/qwen_split'
    inputs = [rtl / p for p in ('qfd_sys_face_n32_bounded.sv',
                               'qfd_sysface32_helpers.sv', 'qfd_sys_face_record_port_n32.sv')]
    top, helpers, record = [p.read_text() for p in inputs]
    comb_helpers = []
    for name in COMB:
        pattern = rf'\(\* keep_hierarchy="yes" \*\) module qfd_bmath_{name}\b.*?endmodule'
        matches = re.findall(pattern, helpers, re.S)
        assert len(matches) == 1, name
        comb_helpers.append(matches[0].replace('(* keep_hierarchy="yes" *) ', '', 1)
                            .replace('qfd_bmath_', 'qfd_syslogic_'))
        pattern = rf'\(\* keep=1, keep_hierarchy="yes" \*\) qfd_bmath_{name}\b'
        if not record_only:
            top = re.sub(pattern, f'(* keep=1 *) qfd_syslogic_{name}', top)
    top = top.replace('module qfd_sys_face_n32_bounded(', 'module qfd_sys_face_n32_opt(', 1)
    top = top.replace('qfd_sys_face_record_port_n32 ', 'qfd_sys_face_record_port_n32_opt ')
    record = record.replace('qfd_sys_face_record_port_n32(', 'qfd_sys_face_record_port_n32_opt(', 1)
    if record_only:
        record = record.replace('module qfd_sys_face_record_port_n32_opt(',
                                '(* keep_hierarchy="yes" *) module qfd_sys_face_record_port_n32_opt(', 1)
    record = record.replace('qfd_record32_', 'qfd_recordlogic_')
    for name in COMB:
        record = record.replace(f'(* keep_hierarchy="yes" *) module qfd_recordlogic_{name} ',
                                f'module qfd_recordlogic_{name} ')
        record = record.replace(f'(* keep=1, keep_hierarchy="yes" *) qfd_recordlogic_{name} ',
                                f'(* keep=1 *) qfd_recordlogic_{name} ')
    # Sequential instance lines must be identical except for the explicitly
    # private helper-family spelling. No register, reset or clock edits.
    seq = lambda text: [line for line in text.splitlines() if 'module ' not in line and re.search(r'\b(?:qfd_bmath_|qfd_record(?:32|logic)_)(?:s?dff)', line)]
    assert seq(inputs[0].read_text()) == seq(top)
    old_record_seq = [line.replace('qfd_record32_', 'qfd_recordlogic_') for line in seq(inputs[2].read_text())]
    assert old_record_seq == seq(record)
    outputs = {rtl / 'qfd_sys_face_n32_opt.sv': top,
               rtl / 'qfd_sysface_logic_helpers.sv': '\n'.join(comb_helpers) + '\n',
               rtl / 'qfd_sys_face_record_port_n32_opt.sv': record}
    for path, text in outputs.items():
        path.write_text(text)
    receipt = {'schema': 'opentallas.sysface_logic_groups.v1',
               'scope': 'Source-only opt-in file-list twin; no default source or kit changes.',
               'record_only': record_only,
               'extra_data_edges': 0, 'extra_boot_edges_relative_to_n32o': 0,
               'sequential_instances_preserved': {'parent': len(seq(top)), 'record': len(seq(record))},
               'inputs': {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
               'outputs': {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs},
               'physical_qualification': False,
               'next': 'Full actual native synthesis/census/depth and real first-epoch wrapper protocol with causal clock negative.'}
    out = repo / 'results/arch/qw_sysface5_0720'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'source_model.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt['sequential_instances_preserved']))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--record-only', action='store_true')
    args = parser.parse_args()
    generate(args.repo, args.record_only)
