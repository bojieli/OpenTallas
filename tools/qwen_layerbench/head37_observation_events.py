#!/usr/bin/env python3
"""Extract HEAD37 witness-face dates from the passive selected-TT trace.

The selected execution receipt states the scope; a component trace remains a
component trace. This tool never supplies missing dates from memory latencies.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(trace, receipt_path, output):
    if output.exists():
        raise ValueError('existing event evidence is never overwritten')
    r = json.loads(receipt_path.read_bytes())
    if r.get('schema') != 'opentallas.qwen.head37-witness-execution.v1':
        raise ValueError('actual selected execution receipt required')
    if r.get('trace_sha256') != sha(trace):
        raise ValueError('actual receiver trace differs from execution receipt')
    component = r.get('component_only')
    if type(component) is not bool:
        raise ValueError('execution scope must state component_only explicitly')
    if r.get('status') != 'PASS_SOURCE_SELECTED_COMMAND_TRANSPORT_REPLAY':
        raise ValueError('actual source-selected command/transport replay required')
    if type(r.get('rank')) is not int or not 0 <= r['rank'] < 8:
        raise ValueError('actual rank required')
    sources = r.get('selected_source_files', {})
    if not sources or not {'calendar', 'tt_parent', 'observer_transport'}.issubset(sources):
        raise ValueError('actual calendar, TT parent, observer transport sources required')
    identities = {}
    for label, entry in sources.items():
        source = Path(entry['path'])
        if not source.is_absolute():
            source = receipt_path.parent / source
        actual = sha(source)
        if actual != entry.get('sha256'):
            raise ValueError('selected execution source differs: ' + label)
        identities[label] = actual
    authorities = {}
    for key in ('command_edge_authority', 'context_start_authority'):
        if not isinstance(r.get(key), str) or not r[key].strip():
            raise ValueError('actual source authority required: ' + key)
        authorities[key] = r[key]
    lines = trace.read_text().splitlines()
    if not lines or lines.pop(0) != 'HEAD37_TRACE_V1 RECEIVER_FACE_PRE_NBA':
        raise ValueError('actual receiver-face trace format required')
    starts = {}
    observations = {}
    last = -1
    for line in lines:
        tokens = line.split()
        if not tokens:
            continue
        if tokens[0] == 'HEAD37_START' and len(tokens) == 5:
            edge, user, stage, epoch = map(int, tokens[1:])
            if user in starts or not 0 <= user < 4 or stage != 37:
                raise ValueError('one actual HEAD37 context start per user required')
            starts[user] = (edge, epoch)
        elif tokens[0] == 'HEAD37_OBS' and len(tokens) == 7:
            edge, user, sl, pc, stage, epoch = map(int, tokens[1:])
            if (user not in starts or not 0 <= sl < 12 or stage != 37
                    or pc != 16 + 128 * user or epoch != starts[user][1]
                    or (sl, user) in observations):
                raise ValueError('actual unique primary16 HEAD witness/context identity differs')
            observations[sl, user] = dict(slice=sl, user=user, stage=stage, pidx=pc,
                                         epoch=epoch, observation_receiver_edge=edge,
                                         context_start_receiver_edge=starts[user][0])
        else:
            raise ValueError('malformed/unrecognized actual witness trace row')
        if edge < 0 or edge < last:
            raise ValueError('actual receiver edges must be nonnegative and ordered')
        last = edge
    if set(observations) != {(s, u) for s in range(12) for u in range(4)}:
        raise ValueError('actual complete48 HEAD observations required')
    result = dict(schema='opentallas.qwen.head37-observation-events.v1',
                  status=('COMPONENT_SOURCE_SELECTED_EXECUTION_DATES' if component
                          else 'SOURCE_SELECTED_EXECUTION_DATES'),
                  unresolved=[] if not component else ['component scope is not final source programme'],
                  component_only=component, rank=r['rank'],
                  edge_origin='actual selected TT witness receiver face, pre-NBA core edge',
                  **authorities, source_sha256={**identities, 'receiver_trace': sha(trace),
                                               'selected_execution_receipt': sha(receipt_path)},
                  events=[observations[k] for k in sorted(observations)])
    output.write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for arg in ('trace', 'execution_receipt', 'out'):
        ap.add_argument('--' + arg.replace('_', '-'), type=Path, required=True)
    a = ap.parse_args()
    r = extract(a.trace, a.execution_receipt, a.out)
    print(r['status'], len(r['events']))


if __name__ == '__main__':
    main()
