#!/usr/bin/env python3
"""One source-pinned analytical SC2 prototype; intentionally emits NO Liberty.

No defaults or legacy views are modified. Run on the fleet. The current timing
consumers cannot select the separate MAX/MIN libraries this master requires.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'results/rtl/s81_coll_wide_pitch_1019'
OLD = 'ot_sram_1r1w_512x128_m4_r2c2'
NEW = OLD + '_p192_sc2'
PLANNER_SHA = '2b4f2a2a23f5272393974655b89ad510947364e935b3771bfdc82136e5276394'
MODEL_SHA = '564c39512720a00c2924f267b87e36c487b5bba76817142b2c5b54d346fbb988'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def build(out):
    source = PACKET / 'sc2_prototype/source'
    assert sha((source / 'manifest.json').read_bytes()) == '2b654ea2647d31ecf7cea8222a1634cd4a7b704b8100c3fb5b529411c35ca9e4'
    manifest = json.loads((source / 'manifest.json').read_text())
    payload = {}
    for filename, record in manifest.items():
        b = (source / filename).read_bytes()
        assert sha(b) == record['sha256'], filename
        assert record['ref'] == 'eb8141cf8', filename
        payload[filename] = b
    model_bytes = (PACKET / 'access_model/model.json').read_bytes()
    assert sha(model_bytes) == MODEL_SHA
    data = json.loads((PACKET / 'access_model/input.json').read_text())
    model = json.loads(model_bytes)
    planner = ROOT / 'tools/mem_compiler/model_port_access_channels_1019.py'
    assert sha(planner.read_bytes()) == PLANNER_SHA
    from model_port_access_channels_1019 import plan
    assert plan(data) == model, 'planner/model mismatch'
    assert model['name'] == NEW
    assert model['proof']['geometry_error_count'] == 0
    assert model['proof']['path_count'] == 437
    assert model['proof']['via_count'] == 870
    assert len(model['pg_rectangles']) == 77
    assert sha(payload[OLD + '.lef']) == data['source_provenance']['old_lef_sha256']
    assert sha(payload[OLD + '.json']) == data['source_provenance']['old_json_sha256']
    out.mkdir(parents=True, exist_ok=True)
    assert not list(out.glob('*.lib')), 'never mix prior Liberty into geometry-only output'
    # Use original declarations and implementation, changing only the master name.
    for suffix in ('.v', '_bb.v'):
        b = payload[OLD + suffix]
        assert b.count(('module ' + OLD + ' (').encode()) == 1
        renamed = b.replace(('module ' + OLD + ' (').encode(), ('module ' + NEW + ' (').encode())
        assert renamed.replace(('module ' + NEW + ' (').encode(), ('module ' + OLD + ' (').encode()) == b
        (out / (NEW + suffix)).write_bytes(renamed)
    # Source LEF pin declarations retained verbatim except terminal rectangles.
    oldlef = payload[OLD + '.lef'].decode()
    header = oldlef[:oldlef.index('MACRO ' + OLD + '\n')]
    width, height = model['outline_nm']
    lines = [header.rstrip(), f'MACRO {NEW}', '  PROPERTY width 128 ;',
             '  PROPERTY depth 512 ;', '  PROPERTY banks 1 ;',
             f'  FOREIGN {NEW} 0 0 ;', '  SYMMETRY X Y ;',
             f'  SIZE {width/1000:.3f} BY {height/1000:.3f} ;', '  CLASS BLOCK ;']
    for p in model['paths']:
        name = p['pin']; x, y = p['terminal_nm']
        begin = oldlef.index('  PIN ' + name + '\n')
        end = oldlef.index('  END ' + name + '\n', begin) + len('  END ' + name + '\n')
        block = oldlef[begin:end]
        import re
        block, count = re.subn(r'RECT [^;]+;', f'RECT {(x-12)/1000:.3f} {(y-12)/1000:.3f} {(x+12)/1000:.3f} {(y+12)/1000:.3f} ;', block)
        assert count == 1, name
        lines.extend(block.rstrip().splitlines())
    for net, use in [('VDD', 'POWER'), ('VSS', 'GROUND')]:
        lines += [f'  PIN {net}', '    DIRECTION INOUT ;', f'    USE {use} ;', '    PORT', '      LAYER M4 ;']
        for p in model['pg_rectangles']:
            if p['net'] == net:
                lines.append('      RECT ' + ' '.join(f'{x/1000:.3f}' for x in p['rect_nm']) + ' ;')
        lines += ['    END', f'  END {net}']
    lines.append('  OBS')
    for o in model['proposed_obstruction_rectangles']:
        lines += [f"    LAYER {o['layer']} ;", '    RECT ' + ' '.join(f'{x/1000:.3f}' for x in o['rect_nm']) + ' ;']
    lines += ['  END', f'END {NEW}', 'END LIBRARY', '']
    (out / (NEW + '.lef')).write_text('\n'.join(lines))
    roles = {
        'status': 'BLOCKED_NO_LIBERTY_EMITTED',
        'tt_max_setup': {'corner': 'tt', 'cq': 'max_cq_ps_by_load_ff', 'setup': 'setup_required_upper_ps'},
        'ss_max_sensitivity': {'corner': 'ss', 'cq': 'max_cq_ps_by_load_ff', 'setup': 'setup_required_upper_ps'},
        'ff_min_hold': {'corner': 'ff', 'cq': 'min_cq_ps_lower_bound', 'added_minimum_lead_delay_ps': 0,
                        'hold': 'hold_required_upper_ps', 'policy': 'No MAX lead or positive slew/load delay added to minimum CQ'},
        'ff_max_characterization': {'corner': 'ff', 'cq': 'max_cq_ps_by_load_ff', 'setup': 'setup_required_upper_ps'},
        'per_pin_capacitance': 'timing[corner].clock_pin_cap_ff_by_pin and nonclock_pin_cap_ff_by_pin',
        'pulse_period': 'timing[corner].min_pulse_upper_ps and min_period_upper_ps',
        'energy': model['energy_policy'], 'leakage': model['leakage_policy'],
        'slew_domain_ps': model['characterized_slew_range_ps'],
        'load_domain_ff': model['characterized_load_range_ff'],
        'binding': None,
        'reason': 'Current single-library-per-corner writer/readers do not bind separate MIN and MAX CQ roles',
    }
    datasheet = dict(schema='opentallas.sc2.source-geometry-prototype.v1', master=NEW,
        status='SOURCE_GEOMETRY_ONLY_NO_TIMING_ADOPTION', old_master=OLD,
        source_manifest=manifest, access_model_sha256=sha(model_bytes), planner_sha256=PLANNER_SHA,
        outline_nm=model['outline_nm'], area_um2=model['macro_area_um2'],
        source_semantics_unchanged=model['source_semantics_unchanged'],
        cycle_change_proposed=0, access_paths=model['paths'], pg_rectangles=model['pg_rectangles'],
        obstruction_rectangles=model['proposed_obstruction_rectangles'], proof=model['proof'],
        timing=model['timing'], timing_roles=roles, native_qualification=None, parent_fit=None)
    dump(out / (NEW + '.json'), datasheet)
    dump(out / 'TIMING_ROLES.json', roles)
    (out / 'NO_LIBERTY.txt').write_text('STOP: source/geometry only. Separate FF MIN/MAX binding requires ROOT review.\n')
    hashes = {p.name: sha(p.read_bytes()) for p in sorted(out.iterdir()) if p.is_file() and p.name != 'hashes.json'}
    dump(out / 'hashes.json', hashes)
    print(f'SC2_SOURCE_GEOMETRY_PASS paths=437 vias=870 pg=77 area={model["macro_area_um2"]} liberty=NONE')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    build(a.out)
