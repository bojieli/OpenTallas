"""Validate real root, registered writer, destination visibility and drain events.

This consumes the sole source observer journal, not predictions or VCD offers.
It complements the acceptance extractor; it never compiles or runs HDL.
"""
import argparse
import hashlib
import json
from pathlib import Path


def validate(events,provenance):
    if provenance.get('basis')!='ACTUAL_RUNTIME_SOURCE_OBSERVER':
        raise ValueError('actual source observer receipt required')
    if not provenance.get('source_commit') or not provenance.get('binary_sha256'):
        raise ValueError('source and executable identity required')
    initial={};roots={};writes={};visible={};idle=None;drain=None;accept=None
    last=-1
    for e in events:
        edge=e['edge'];kind=e['kind']
        if edge<last:raise ValueError('journal edge order')
        last=edge
        if kind.startswith('FAIL'):raise ValueError('source fault')
        if kind=='VM_destination_initial':
            address=e['a']
            if accept is not None or address in initial or not 32768<=address<33344 or e['c']==0:
                raise ValueError('nonvacuous initial destination required before op')
            initial[address]=e['c']
        elif kind=='op_accept':
            if accept is not None or e['a']!=10 or len(initial)!=576:
                raise ValueError('exact phase and initialized full destination required')
            accept=edge
        elif kind=='root_row_accept':
            row=e['b']
            if accept is None or row in roots or not 0<=row<576 or not 0<=e['a']<128:
                raise ValueError('root identity/conservation')
            roots[row]=(edge,e['a'],e['c'])
        elif kind=='VM_write_accept':
            row=e['b']-32768
            if row not in roots or row in writes:
                raise ValueError('writer without unique root')
            re,port,data=roots[row]
            if edge!=re+1 or e['a']!=port or e['c']!=data:
                raise ValueError('native registered writer dependency')
            writes[row]=(edge,e['c'])
        elif kind=='VM_write_visible':
            row=e['a']-32768
            if row not in writes or row in visible or e.get('sampling')!='postNBA':
                raise ValueError('actual postNBA sink visibility required')
            we,data=writes[row]
            if edge!=we or e['c']!=data or e['c']==initial[e['a']]:
                raise ValueError('destination did not perform matching accepted write')
            visible[row]=edge
        elif kind=='spine_idle':idle=edge
        elif kind=='all_source_root_writer_drained':
            if len(visible)!=576 or len(writes)!=576 or len(roots)!=576 or idle is None:
                raise ValueError('drain before full destination visibility')
            if edge<=max(visible.values()) or e['a']!=102400 or e['b']!=576 or e['c']!=576:
                raise ValueError('drain counts or visibility fence')
            drain=edge
    if drain is None:raise ValueError('missing actual root/destination/drain receipt')
    return dict(phase=10,rows=576,op_accept=accept,last_root=max(x[0] for x in roots.values()),
                last_destination_visible=max(visible.values()),idle=idle,drain=drain,
                acceptance_to_destination_edges=max(visible.values())-accept,
                no_ECC_pool_or_new_ACK=True,physical_clock_qualified=False,fulltoken_qualified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--journal',type=Path,required=True)
    p.add_argument('--provenance',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('immutable evidence')
    raw=a.journal.read_bytes();h=hashlib.sha256(raw).hexdigest();pins=json.loads(a.provenance.read_text())
    if pins.get('actual_journal_sha256')!=h:raise ValueError('journal identity')
    result=validate([json.loads(x) for x in raw.splitlines()],pins)
    if a.journal.read_bytes()!=raw:raise ValueError('live journal changed during validation')
    result.update(source_commit=pins['source_commit'],binary_sha256=pins['binary_sha256'],journal_sha256=h)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
