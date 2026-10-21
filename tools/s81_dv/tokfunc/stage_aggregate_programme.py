#!/usr/bin/env python3
"""Stage actual aggregate MAT/config/native CTL assets; never create a producer.

Run from a frozen compiler tree whose RTL matches the shipping inventory. The
checkpoint norm vector is used only by the return legaliser/scoreboard. It is
never written as gather/VM data, a replay input, or a runtime preload.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'tools/s81_dv'), str(ROOT/'tools/s81_dv/layer_prog')]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory', type=Path, required=True)
    p.add_argument('--tree', type=Path, required=True)
    p.add_argument('--fixtures', type=Path, required=True)
    p.add_argument('--frame-schedule', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    import dv_layer_compile as C
    import lower_xs as L
    from layer_prog.aproj_native import phase_material, programme
    from layer_prog.slice_source import resolve
    inventory = json.loads(a.inventory.read_text())
    for rel, receipt in inventory['sources'].items():
        assert digest(ROOT/rel) == receipt['sha256'], ('shipping source mismatch', rel)
    for schedule in a.frame_schedule.glob('*_schedule.json'):
        for rel, expected in json.loads(schedule.read_text())['source_sha256'].items():
            assert digest(ROOT/rel) == expected, ('LP source schedule mismatch', rel)
    os.environ.update(OT_XS_APROJ_TOPO='1', OT_XS_APROJ_RANK_TAGS='1', OT_XS_APROJ_ALIGN4='1',
                      OT_XS_DENSE_SPLIT2_ROWS=inventory['placement_environment']['OT_XS_DENSE_SPLIT2_ROWS'],
                      OT_XS_APROJ_CAP_PLAN='1', OT_XS_FRAME_SCHEDULE_DIR=str(a.frame_schedule.resolve()))
    die = C.Die(a.tree)
    assert die.die_sha == inventory['die_sha256']
    sl = inventory['selected_slice']
    selected = resolve(die, sl)
    fx = L.load_fixture(a.fixtures)
    assert digest(a.fixtures/'meta.json') == inventory['fixture_meta_sha256']
    a.out.mkdir(parents=True, exist_ok=False)
    for half in ('A', 'B'):
        os.environ['OT_XS_DENSE_SPLIT2'] = half
        out = a.out/half
        images = out/'rom'
        images.mkdir(parents=True)
        _, placement = L.placement(die, sl, fx)
        assert placement == inventory['selected_ownership'][half]
        capture = L.aproj_capture_contract(die, sl, fx, 1)
        frames, shared, expected_returns = [], None, {}
        for member in placement:
            assert member['rows'], ('unexpected idle selected member', member)
            mats, indices = L.frame_mats(fx, member['rows'])
            field, phase, plan, qa, q, bf = L.frame_programme(member['master'], member['lk'], mats,
                fx['x'], rank_rows=member['rows'], cap_cfg=capture['cfg'])
            assert plan['faults'] == 0
            material = phase_material(field)
            assert shared is None or shared == material, 'one real XS requires identical shared P/S words'
            shared = material
            L.field_images(field, qa, q, bf, member['frame'], images, rank_rows=member['rows'])
            mapped = L.rank_plan(plan, member['rows'])
            expected_returns[member['frame']] = mapped['ret']
            frames.append(dict(member, phase={k:v for k,v in phase.items() if k != 'matrices'},
                pairs=qa, out_index=indices, faults=plan['faults'], ret=mapped['ret'],
                emission=plan['emission'], source_schedule=str(L.source_frame_schedule(member['master']))))
        # Zero is an explicitly RELATIVE programme origin, never a global epoch
        # or fabricated HOST/KS descriptor. Parent must bind immutable dates.
        native = programme(die, dict(id='L0_'+half+'_aproj_'+sl, end=0),
                           dict(slice=sl, t_issue=0), shared, frames, capture)
        for name, content in native['files'].items():
            path = out/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        # Plans contain checkpoint-dependent values for comparison only. They
        # are deliberately outside all replay/ROM producer inputs.
        score = out/'SCOREBOARD_ONLY'
        score.mkdir()
        (score/'frame_return_plan.json').write_text(json.dumps(expected_returns, indent=1)+'\n')
        (out/'native_ctl_relative.json').write_text(json.dumps(dict(rows=native['rows'],
            templates=native['templates'], events=native['events'],
            epoch='RELATIVE_ONLY_NOT_HOST_ADOPTED', physical_phase_qualified=False), indent=1)+'\n')
    files = {str(f.relative_to(a.out)):digest(f) for f in sorted(a.out.rglob('*')) if f.is_file()}
    receipt = dict(schema='opentallas.s81.aggregate_source_assets.v1', status='STAGED_HELD_FOR_REAL_PRODUCER',
        selected_source=selected, selected_slice=sl, die_sha256=die.die_sha,
        inventory_sha256=digest(a.inventory), fixture_meta_sha256=digest(a.fixtures/'meta.json'),
        compiler_sha256={str(f.relative_to(ROOT)):digest(f) for f in [Path(__file__), Path(L.__file__)]},
        files=files, actual_gather_data_emitted=False, synthetic_frame_returns_emitted=False,
        simulation_launched=False, global_epoch_bound=False, aggregate_FIN_qualified=False,
        pending=['real 16-slice NORMR/XFIN VQ producer trace', 'exact grown clock/reset/return cone',
                 'all-frame aggregate CAP collision/FIN qualification', 'native HOST adoption'])
    (a.out/'assets.json').write_text(json.dumps(receipt, indent=1)+'\n')
    print(json.dumps(dict(status=receipt['status'], files=len(files), slice=sl)))


if __name__ == '__main__':
    main()
