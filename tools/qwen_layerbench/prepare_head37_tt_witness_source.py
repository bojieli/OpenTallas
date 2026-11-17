#!/usr/bin/env python3
"""Select a source-linked HEAD37 witness leaf in the reconstructed TT parent.

This prepares source only. A production receipt is required; the closed BASE
leaf and its default instance hierarchy remain intact. No profile is invented.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rewrite_parent(text, master):
    if not re.fullmatch(r'qfd_tt_ctlm_dv_wtn_head37_prod_[0-9a-f]{16}_e[0-9]+', master):
        raise ValueError('distinct baked production witness master required')
    if len(re.findall(r'parameter\s+integer\s+HEAD_STAGE37\s*=\s*0\b', text)) != 1:
        raise ValueError('actual default-off HEAD_STAGE37 TT parent required')
    begin = '    generate if (F16WTN != 0) begin : g_wtn\n'
    end = '    end else begin : g_no_wtn\n'
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ValueError('actual unique frozen TT witness generate boundary required')
    i = text.index(begin)
    j = text.index(end, i)
    body = text[i + len(begin):j]
    if body.count('qfd_tt_ctlm_dv_wtn u_wtn (') != 1:
        raise ValueError('actual closed BASE witness instance differs')
    if body.count('assign w_fault = f16_st[16];') != 1:
        raise ValueError('actual witness fault return differs')
    selected = body.replace('qfd_tt_ctlm_dv_wtn u_wtn (', master + ' u_wtn (', 1)
    new = ('    generate if (F16WTN != 0 && HEAD_STAGE37 == 0) begin : g_wtn\n'
           + body + '    end else if (F16WTN != 0) begin : g_wtn_head37\n' + selected)
    return text[:i] + new + text[j:]


def trace_parent(text):
    """Passive bootstrap capture, independent of a not-yet-known witness image."""
    needle = "    wire [15:0] u_tokid = l_start ? tok_b[l_user][15:0] : s_tok[15:0];"
    if text.count(needle) != 1 or 'u_head37_witness_trace' in text:
        raise ValueError('actual unique TT accepted-start/token identity face required')
    end = text.index('\n', text.index(needle)) + 1
    probe = '''`ifdef OT_HEAD37_WITNESS_TRACE
    // Passive receiver-face capture: no WTN enable/profile needed to bootstrap.
    qfd_head37_witness_trace u_head37_witness_trace (
        .ck(ck), .rst_n(rst_n),
        .start({u_start, 2'(u_user), u_stage, u_tokid}), .obs(f16_obs));
`endif
'''
    return text[:end] + probe + text[end:]


def prepare(parts, receipt_path, profile_path, leaf, controller, output):
    if output.exists():
        raise ValueError('existing source preparation/evidence is never overwritten')
    r = json.loads(receipt_path.read_bytes())
    p = json.loads(profile_path.read_bytes())
    if (r.get('status') != 'PRODUCTION_PROFILE_SOURCE_READY_NOT_PHYSICAL'
            or r.get('component_only') is not False
            or r.get('selection_default') is not False
            or r.get('physical_adoption') is not False):
        raise ValueError('actual production witness receipt required; TEST/unresolved refused')
    if (p.get('status') != 'EXECUTABLE_SOURCE_LINKED_HEAD37_WITNESS'
            or p.get('unresolved') != [] or p.get('primary_pidx') != 16
            or p.get('duplicate_programme_words') != 0
            or len(p.get('kernel_join', [])) != 48
            or p.get('profiles', {}).get('head37', {}).get('records') != 15):
        raise ValueError('actual source-linked 48-event/fifteen-record primary16 profile required')
    for path, key in [(profile_path, 'profile_sha256'), (leaf, 'source_sha256'),
                      (controller, 'controller_sha256')]:
        if sha(path) != r.get(key):
            raise ValueError('selected witness dependency hash differs: ' + key)
    if r.get('digest') != p.get('digest') or r.get('epoch') != p.get('epoch'):
        raise ValueError('selected witness profile identity differs')
    identity = json.dumps({'base': p.get('base_records'),
                           'head_fixture': p.get('head_groups'),
                           'kernel_join': p.get('kernel_join')}, sort_keys=True).encode()
    digest = hashlib.sha256(identity).digest()[:8].hex()
    if digest != p.get('digest') or digest in ('0000000000000000', '198f7708b478a667'):
        raise ValueError('selected witness digest does not identify its actual records')
    if ({(v.get('slice'), v.get('user')) for v in p['kernel_join']}
            != {(s, u) for s in range(12) for u in range(4)}):
        raise ValueError('selected witness must join all48 unique actual kernel identities')
    if (len(p.get('base_records', [])) != 13 or len(p.get('head_groups', [])) != 2
            or any(g.get('pc') != 16 for g in p['head_groups'])
            or sorted(e[1] for g in p['head_groups'] for e in g['events']) != list(range(12))):
        raise ValueError('selected witness must retain BASE13 and two disjoint primary16 groups')
    if r.get('records') != 15 or r.get('template_bits') != 2010 or r.get('output_core_edges') != 2:
        raise ValueError('selected witness changes required storage/output contract')
    master = r['master']
    body = leaf.read_text()
    if len(re.findall(r'^module\s+' + re.escape(master) + r'\s*#', body, re.M)) != 1:
        raise ValueError('baked selected master absent')
    compact = re.sub(r'\s+', '', body)
    for token in ['.HEAD_STAGE37(1)', '.SAFE_PHYS(1)',
                  ".HEAD_PROFILE_DIGEST(64'h" + p['digest'] + ')',
                  ".HEAD_PROFILE_EPOCH(16'd" + str(p['epoch']) + ')']:
        if token not in compact:
            raise ValueError('baked selected leaf does not bind its authenticated controller')
    result = trace_parent(rewrite_parent(parts.read_text(), master))
    output.mkdir(parents=True)
    target = output / parts.name
    target.write_text(result)
    record = dict(schema='opentallas.qc.head37-tt-witness-source.v1',
                  status='SOURCE_READY_NOT_BOUND_OR_PHYSICAL',
                  source=str(target), source_sha256=sha(target),
                  original_parts_sha256=sha(parts),
                  witness_master=master, witness_source_sha256=sha(leaf),
                  witness_controller_sha256=sha(controller),
                  witness_profile_sha256=sha(profile_path),
                  witness_receipt_sha256=sha(receipt_path),
                  HEAD_STAGE37_default=0, F16WTN_default_changed=False,
                  base_instance='g_wtn.u_wtn', selected_instance='g_wtn_head37.u_wtn',
                  default_base_body_identical=True, ports_added=0,
                  added_output_cycles=0, physical_adoption=False,
                  trace_define='OT_HEAD37_WITNESS_TRACE',
                  requires_frontend_receipt_regeneration=True,
                  next=['native construct must retain the exact new leaf and dependency',
                        'all48 current loader/command/lease windows',
                        'unified model/slot fit and physical qualification'])
    (output / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for arg in ['parts', 'out']:
        ap.add_argument('--' + arg.replace('_', '-'), type=Path, required=True)
    for arg in ['leaf_receipt', 'leaf_profile', 'leaf', 'controller']:
        ap.add_argument('--' + arg.replace('_', '-'), type=Path)
    ap.add_argument('--trace-only', action='store_true',
                    help='passive actual face capture only; no new leaf/profile selection')
    a = ap.parse_args()
    if a.trace_only:
        if a.out.exists():
            raise ValueError('existing source preparation/evidence is never overwritten')
        result = trace_parent(a.parts.read_text())
        a.out.mkdir(parents=True)
        (a.out / a.parts.name).write_text(result)
        print('PASSIVE_TRACE_SOURCE_READY_NO_WITNESS_PROFILE_SELECTED')
        return
    if any(getattr(a, arg) is None for arg in ['leaf_receipt', 'leaf_profile', 'leaf', 'controller']):
        ap.error('authenticated production leaf/profile dependencies are required without --trace-only')
    r = prepare(a.parts, a.leaf_receipt, a.leaf_profile, a.leaf, a.controller, a.out)
    print(r['status'], r['witness_master'])


if __name__ == '__main__':
    main()
