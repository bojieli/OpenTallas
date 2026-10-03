"""CPU-only closure for the two existing qualified DSpark acceptance runs.

Refuse live/incomplete runs before reading traces. Reuse the pre-registered
aggregator; no model loading, GPU work, prompt generation or accepted-tau input.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import tempfile

import blend_qualified as B


class NotTerminal(RuntimeError):
    pass


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def key(item, mode):
    return item['workload'], item['prompt_id'], mode


def terminal_inputs(runs, manifests):
    if len(runs) != 2 or len(manifests) != 2:
        raise ValueError('exactly the two enrolled runs and prompt manifests required')
    inventory, rows = {}, []
    for run, manifest in zip(map(Path, runs), map(Path, manifests)):
        status = run / 'status'
        words = status.read_text().split() if status.exists() else []
        if any(w.endswith('FAIL') for w in words):
            raise ValueError(f'preserved failure in {status}')
        if not {'GENDONE', 'DRAFTDONE'} <= set(words):
            raise NotTerminal(f'awaiting existing generation/draft chain: {run}')
        # No trace or generated-payload reads occur until BOTH runs qualify.
    for run, manifest in zip(map(Path, runs), map(Path, manifests)):
        paths = [manifest, run / 'status', run / 'run.sh', run / 'gen.log',
                 run / 'gen_out.pt', run / 'drafts.json', run / 'draft.log']
        for path in paths:
            if not path.is_file():
                raise ValueError(f'missing terminal artifact: {path}')
            inventory[str(path.resolve())] = dict(bytes=path.stat().st_size, sha256=sha(path))
        items = json.loads(manifest.read_text())['items']
        expected = Counter(key(item, mode) for item in items for mode in ('greedy', 't1'))
        if any(n != 1 for n in expected.values()):
            raise ValueError('duplicate enrolled prompt identity')
        produced = json.loads((run / 'drafts.json').read_text())
        actual = Counter(key(tr['item'], tr['mode']) for tr in produced)
        if expected != actual:
            raise ValueError('missing, duplicate or unenrolled actual trace')
        originals = {(item['workload'], item['prompt_id']): item for item in items}
        for tr in produced:
            item = originals[(tr['item']['workload'], tr['item']['prompt_id'])]
            if tr['item'] != item or tr['L'] != item['n_prompt'] or tr['tokens'][:tr['L']] != item['ids']:
                raise ValueError('prompt/source identity changed')
            if not all(type(t) is int and t >= 0 for t in tr['tokens']):
                raise ValueError('invalid token identity')
            generated = len(tr['tokens']) - tr['L']
            if not 1 <= generated <= 161:
                raise ValueError('trace outside pre-registered 161-token deviation')
            expected_rows = {str(p) for p in range(tr['L'], len(tr['tokens']) - 1)}
            field = 'drafts' if tr['mode'] == 'greedy' else 'q_tok'
            if set(tr[field]) != expected_rows:
                raise ValueError('partial, extra or stale draft row set')
            for row in tr[field].values():
                if len(row) != B.G:
                    raise ValueError('wrong native block depth')
                if tr['mode'] == 'greedy':
                    if not all(type(t) is int and t >= 0 for t in row):
                        raise ValueError('invalid draft token')
                elif not all(math.isfinite(p) and 0 <= p <= 1 for p in row):
                    raise ValueError('invalid measured draft probability')
            if tr['mode'] == 't1':
                if len(tr['p_tok']) != generated or not all(math.isfinite(p) and 0 < p <= 1 for p in tr['p_tok']):
                    raise ValueError('invalid measured sampled-target probability')
        rows.extend(produced)
    if len({key(tr['item'], tr['mode']) for tr in rows}) != len(rows):
        raise ValueError('overlapping batch trace identities')
    return inventory, rows


def validate_summary(result, rows):
    expected = Counter((tr['item']['workload'], tr['mode']) for tr in rows)
    for name, workloads in B.OURS.items():
        for mode in ('greedy', 't1'):
            for gamma in range(1, B.G + 1):
                stats = result['classes'][name][mode].get(str(gamma))
                if not stats or stats['cycles'] <= 0 or stats['prompts'] <= 0:
                    raise ValueError('no actual usable class acceptance')
                if stats['prompts'] > sum(expected[w, mode] for w in workloads):
                    raise ValueError('fabricated class prompt count')
                for field in ('tau_median_of_prompts', 'tau_pooled'):
                    if not math.isfinite(stats[field]) or not 1 <= stats[field] <= gamma + 1:
                        raise ValueError('invalid accepted length')
    if result['published']['label'] != B.LMSYS_LABEL:
        raise ValueError('published verify-window/model scope changed')
    for name, (_, window) in B.PUBLISHED.items():
        published = result['published']['values'][name]
        if published != dict(set=B.PUBLISHED[name][0], tau_verify_window=window):
            raise ValueError('published window substituted as measured acceptance')
    for mode in ('greedy', 't1'):
        tau = result['envelope'][mode]['class_tau_gamma5']
        if set(tau) != set(B.CLASSES):
            raise ValueError('incomplete eight-class envelope')
        for name, weights in B.WEIGHTS.items():
            expected_tau = round(1 / sum(weight / tau[c] for c, weight in weights.items()), 3)
            if result['blends'][name][mode].get('tau_blend_harmonic') != expected_tau:
                raise ValueError('wrong harmonic blend or missing class')
        if result['blends']['equal (default)'][mode]['published_weight_share'] != .375:
            raise ValueError('published contribution hidden')


def close(runs, manifests, out):
    if any(Path(out).resolve().is_relative_to(Path(run).resolve()) for run in runs):
        raise ValueError('output must be outside preserved live run directories')
    # The enrolled chain appends ANALYSED after its existing CPU aggregation.
    # Wait for that closure as well, so its status file cannot change beneath
    # this independent postprocessor. No additional watcher or GPU phase.
    status = Path(runs[0]) / 'status'
    if not status.exists() or 'ANALYSED' not in status.read_text().split():
        raise NotTerminal('awaiting existing chain CPU-analysis closure')
    inventory, rows = terminal_inputs(runs, manifests)
    paths = [str(Path(run) / 'drafts.json') for run in runs]
    # Existing aggregation is CPU-only. Write outside the live run directories.
    with tempfile.TemporaryDirectory(prefix='qualified-dspark-cpu-') as scratch:
        blend = Path(scratch) / 'blend.json'
        B.main(str(blend), paths)
        result = json.loads(blend.read_text())
    validate_summary(result, rows)
    for path, pin in inventory.items():
        if Path(path).stat().st_size != pin['bytes'] or sha(path) != pin['sha256']:
            raise ValueError('terminal artifact changed during postprocessing')
    here = Path(__file__).resolve().parent
    sources = {name: sha(here / name) for name in
               ('qualified_terminal.py', 'blend_qualified.py', 'acc_qualified.py', 'analyze.py', 'v41gen.py', 'v41draft.py')}
    protocol = here.parents[1] / 'results/speculative/v41_mtp_acceptance_qualified_20261003'
    sources.update({name: sha(protocol / name) for name in ('PROTOCOL.md', 'PROTOCOL_ADDENDUM.md', 'DEVIATIONS.md')})
    receipt = dict(status='PASS_ACTUAL_TERMINAL_CPU_POSTPROCESSING', actual_trace_count=len(rows),
                   input_inventory=inventory, source_sha256=sources, result=result,
                   qualification=dict(generation='existing retained runs only',
                                      accepted_tau='actual greedy replay; T1 measured-probability coupling replay',
                                      published='V4-Flash exact LMSYS verify windows, not measured V4.1 accepted length',
                                      blends='eight-class equal mix has37.5% published window references; measured-only c-g reported separately',
                                      late_output='tokens after161 unmeasured',
                                      rates='protocol historical analytical sensitivities; ROM draft unvalidated; uniform wire repricing separate',
                                      gpu_generation_launched=False))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(receipt, indent=2, sort_keys=True) + '\n'
    if out.exists() and out.read_text() != data:
        raise ValueError('refuse to overwrite a different verdict')
    out.write_text(data)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='append', required=True)
    parser.add_argument('--prompts', action='append', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = close(args.run, args.prompts, args.out)
    except NotTerminal as exc:
        print(json.dumps(dict(status='WAITING_NO_ACTUAL_TAU_PUBLISHED', reason=str(exc))))
        return 2
    print(json.dumps(dict(status=receipt['status'], traces=receipt['actual_trace_count'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
