#!/usr/bin/env python3
"""Emit an opt-in source family with the actual POR request history, never a tie.

This is source integration only. It does not install a die, qualify a CDC path,
or implement the still-unbound continuous-health host-retirement callback.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = Path('rtl/qwen_sys')
DEST = SRC / 'retire_source_20261019'
FILES = [SRC / 'host_integrated_20261014' / (n + '.sv') for n in (
    'qkd_host_ctrl_token_service_packet_collected',
    'qkd_host_packet_bundle_admission', 'qkd_host_control_packet_admission')]
FILES += [SRC / 'split_20261014/qkd_host_root_admission.sv',
          SRC / 'mu_qwen_20261018/qkd_host_ctrl_token_service_packet_collected_mu.sv']
MODULES = ['qkd_host_ctrl_token_service_packet_collected_mu',
           'qkd_host_ctrl_token_service_packet_collected',
           'qkd_host_packet_bundle_admission', 'qkd_host_control_packet_admission',
           'qkd_host_rank_services_admission', 'qkd_host_root_admission']


def once(s, old, new, count=1):
    if s.count(old) != count:
        raise ValueError(f'expected {count} occurrence(s): {old!r}, got {s.count(old)}')
    return s.replace(old, new)


def transform(name, text):
    s = text
    if name == 'qkd_host_ctrl_token_service_packet_collected.sv':
        s = once(s, 'input wire terminal_accepted\n);',
                 'input wire terminal_accepted,output wire retained_context\n);')
        s = once(s, ' reg[2:0]did_q,die_capture;',
                 ' // Zero-edge export of existing POR state; never warm-reset state.\n'
                 ' assign retained_context=retained_request;\n reg[2:0]did_q,die_capture;')
    elif name == 'qkd_host_ctrl_token_service_packet_collected_mu.sv':
        s = once(s, 'input wire terminal_accepted\n);',
                 'input wire terminal_accepted,output wire retained_context\n);')
        s = once(s, '.terminal_accepted(terminal_accepted));',
                 '.terminal_accepted(terminal_accepted),.retained_context(retained_context));')
        s = once(s, ' wire retained_request=|rr;',
                 ' wire retained_request=|rr;\n assign retained_context=retained_request;')
    elif name in ('qkd_host_packet_bundle_admission.sv', 'qkd_host_control_packet_admission.sv'):
        s = once(s, 'input wire terminal_accepted',
                 'output wire retained_context,input wire terminal_accepted')
        s = once(s, '.terminal_accepted(terminal_accepted),',
                 '.terminal_accepted(terminal_accepted),.retained_context(retained_context),')
    elif name == 'qkd_host_root_admission.sv':
        s = once(s, ' wire[142:0]pr,raw_pr;',
                 ' wire retained_context;\n wire[142:0]pr,raw_pr;')
        s = once(s, '.terminal_accepted(token_cancel_accepted),',
                 '.terminal_accepted(token_cancel_accepted),.retained_context(retained_context),')
        s = once(s, 'qkd_host_service_guard u_guard(',
                 'qkd_host_service_guard_wh u_guard(.por_n(por_n&&pll_locked),'
                 '.retained_ctx(retained_context),.recovery_certified(native_recovery_clear),')
    else:
        raise ValueError(name)
    # Word-boundary substitution also renames comments; no source body changes.
    s = re.sub(r'\b(' + '|'.join(MODULES) + r')\b', lambda m: m[0] + '_rh', s)
    return '// SOURCE ONLY: explicit *_rh family, unselected by default.\n' + s


def emit(root=ROOT):
    out = root / DEST
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for rel in FILES:
        b = (root / rel).read_bytes()
        result = transform(rel.name, b.decode()).encode()
        target = out / (rel.stem + '_rh.sv')
        target.write_bytes(result)
        records.append(dict(source=str(rel), source_sha256=hashlib.sha256(b).hexdigest(),
                            output=str(target.relative_to(root)),
                            output_sha256=hashlib.sha256(result).hexdigest()))
    manifest = dict(schema='opentallas.kv_retained_export.v1',
                    production_selected=False, added_export_FF=0,
                    added_export_edges=0, native_CDC_qualified=False,
                    complete_health_retirement_qualified=False, files=records)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    print(json.dumps(emit(), indent=2))
