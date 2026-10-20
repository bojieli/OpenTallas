#!/usr/bin/env python3
"""Regression for mandatory FUSED I7 admission and opt-in GQ s3 launch cost.

Run on the fleet. Existing P3 images must be refused, not relabelled as healthy.
The before-checker is a frozen copy from the programme parent, supplied explicitly.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import image_check as IC
import fused_phase_check as FC
import plane_compiler as PC
import hnx_coll_gq_train as GQ


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--before', type=Path, required=True)
    ap.add_argument('--gq-before', type=Path, required=True)
    ap.add_argument('--images', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    before = load(args.before, 'image_check_before')
    gq_before = load(args.gq_before, 'gq_train_before')
    ok, cases = FC.selftest()
    assert ok
    result = dict(fused_synthetic=cases, images={}, native_execution=False)
    for directory in sorted(args.images.iterdir()):
        if not directory.is_dir():
            continue
        meta, img, recs, violations, loops = IC.run_dir(directory)
        old, old_loops = before.check_image(recs, meta['token']['segments'], meta,
                                            meta['mode'], meta['N'], meta['P'])
        assert [v for v in violations if v['check'] != 'I7'] == old
        assert old_loops == loops
        expected = sum(len(FC.check_fused(r, rx)) for _, r, rx, _ in recs)
        actual = [v for v in violations if v['check'] == 'I7']
        assert len(actual) == expected and expected > 0
        mutants = IC.mutants(recs, meta)
        assert all(v['fails'] in (True, None) for v in mutants.values())
        result['images'][directory.name] = dict(sha256=hashlib.sha256(img).hexdigest(),
            records=len(recs), before_violations=len(old), i7_violations=len(actual),
            admitted=False, first_i7=actual[0], mutants=mutants)
    assert len(result['images']) == 6
    # Existing fire-relative bank calendars retain exact offsets; only their
    # absolute launch epoch moves. No duplicated charge per row is permitted.
    assert GQ.FIRE_FROM_LAUNCH == gq_before.FIRE_FROM_LAUNCH + 1 == 4
    compared = 0
    for q in range(4):
        for f, rings in ((1, 1), (35, 2), (145, 2)):
            current = GQ.schedule(q, f, rings, False, True, 64, 0, 160)
            assert current == gq_before.schedule(q, f, rings, False, True, 64, 0, 160)
            compared += sum(len(events) for events in current)
    records = [SimpleNamespace(orig_op='COLL.ROW_GATHER', c1=100., ii=8., base_cost=140.),
               SimpleNamespace(orig_op='COLL.ROW_GATHER', base_cost=100.),
               SimpleNamespace(orig_op='COLL.TOPK_MERGE', base_cost=50.)]
    unchanged = copy.deepcopy(records)
    assert PC.apply_frames(records, PC.Knobs()) == {} and records == unchanged
    notes = PC.apply_frames(records, PC.Knobs(meas=('gq_s3',)))
    assert notes == {'COLL.ROW_GATHER': 2.}
    assert records[0].c1 == 101. and records[0].ii == 8. and records[0].base_cost == 141.
    assert records[1].base_cost == 101. and records[2].base_cost == 50.
    result['gq_s3'] = dict(fire_from_launch=4, delta_per_descriptor=1,
        calendar_events_compared=compared, row_ii_unchanged=True, default_unchanged=True,
        coverage='COLL.ROW_GATHER only; other native COLL lowering remains unbound')
    result['PASS'] = True
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print('CMTP_SUCCESSOR_CHECK PASS; six original images remain REFUSED by I7')


if __name__ == '__main__':
    main()
