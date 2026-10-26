#!/usr/bin/env python3
"""el1011-qseam: fold the seam-bench verdicts (runs/<tag>/verdict.json from run.sh) into record.json.

Positive runs (no --mut) must PASS; every mutant run must FAIL.  Per seam class the record carries the seams that
passed / built, the transactions they carried and the relays they hold.

    collect.py --runs RUNS --src-commit SHA --out record.json [--note K=V ...]
"""
import argparse, glob, json, os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', required=True)
    ap.add_argument('--src-commit', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--note', action='append', default=[])
    a = ap.parse_args()
    pos, mut = {}, {}
    for f in sorted(glob.glob(os.path.join(a.runs, '*/verdict.json'))):
        tag = os.path.basename(os.path.dirname(f))
        V = json.load(open(f))
        m = V['meta']
        row = dict(verdict=V['verdict'], bench=m['bench'], deskew=m.get('deskew', False), mut=m.get('mut', []),
                   classes={k: dict(passed=v['passed'], seams=v['seams'], transactions=v['transactions'], relays=v['relays'],
                                    failures=v['failures'][:2]) for k, v in V['classes'].items()},
                   **{k: V[k] for k in ('nodes', 'roots', 'lanes', 'tile_errors', 'station_ready_at_vm') if k in V},
                   first_errors=V['first_errors'][:2])
        (mut if m.get('mut') else pos)[tag] = row
    meta = {}
    for f in sorted(glob.glob(os.path.join(a.runs, '*/expect.json'))):
        m = json.load(open(f))['meta']
        if not m.get('mut'):
            meta[os.path.basename(os.path.dirname(f))] = {k: v for k, v in m.items() if k not in ('mut',)}
    R = dict(schema='opentallas.qwen-die-seam-bench.v1', src_commit=a.src_commit, notes=dict(x.split('=', 1) for x in a.note),
             positive=pos, mutants=mut, bench_meta=meta,
             mutants_all_fail=all(r['verdict'] == 'FAIL' for r in mut.values()))
    json.dump(R, open(a.out, 'w'), indent=1)
    for t, r in list(pos.items()) + list(mut.items()):
        print(t, r['verdict'], {k: f"{v['passed']}/{v['seams']}" for k, v in r['classes'].items()}, r['first_errors'][:1])


if __name__ == '__main__':
    main()
