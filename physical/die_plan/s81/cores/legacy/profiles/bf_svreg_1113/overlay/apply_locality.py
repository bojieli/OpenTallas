#!/usr/bin/env python3
"""Install reviewed PRIVATE GF5 physical guides into a fresh generated kit.
Default recipes and source RTL are never changed. A1 requires a separate plan.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

FORMS = {
    'f': ('dsdv_gunit_l1f_bf', [0., 0., 432., 172.8], 'f_read_cache.tcl'),
    'a0-sort2cmp': ('dsdv_gunit_l1f_ba0', [0., 0., 432., 151.2], 'a0_sort2cmp.tcl'),
}

def config_value(text, key):
    values = re.findall(r'^(?:override\s+)?export\s+' + re.escape(key) + r'\s*=\s*(.*?)\s*$', text, re.M)
    if not values:
        raise ValueError('missing config ' + key)
    return values[-1]

def validate(text, form):
    top, outline, filename = FORMS[form]
    actual = config_value(text, 'DESIGN_NAME')
    if actual != top:
        raise ValueError(f'{form} requires {top}, got {actual}; A1 S-face locality remains a separate unqualified gate')
    if list(map(float, config_value(text, 'DIE_AREA').split())) != outline:
        raise ValueError('unreviewed outline; this constructor is for the recorded fixed geometry only')
    core = [4.32, 4.32, 427.68, 168.48 if form == 'f' else 146.88]
    if list(map(float, config_value(text, 'CORE_AREA').split())) != core or float(config_value(text, 'PLACE_DENSITY')) != .4:
        raise ValueError('unreviewed core frame or density')
    defines = config_value(text, 'VERILOG_DEFINES').split()
    needed = ['OT_GUNIT_BF_SVREG'] + (['OT_GUNIT_BF_M1REG', 'OT_GUNIT_BF_C1REG'] if form == 'f' else [])
    if any('-D' + define not in defines for define in needed):
        raise ValueError('missing captured form defines: ' + ','.join(needed))
    hooks = [config_value(text, key) for key in ('PRE_GLOBAL_PLACE_TCL', 'PRE_DETAIL_PLACE_TCL')]
    if any(not re.fullmatch(r'/work/[A-Za-z0-9_.-]+', hook) for hook in hooks):
        raise ValueError('unsupported hook path; preserve the generated hook chain explicitly')
    expected = ['/work/face_flops.tcl' if form == 'f' else '/work/pre_place.tcl', '/work/face_flops_release.tcl']
    if hooks != expected:
        raise ValueError('unreviewed existing placement-guide chain; use a fresh generated kit')
    return top, filename, [Path(hook).name for hook in hooks]

def install(kit, form, here=None):
    kit = Path(kit).resolve(); here = Path(here).resolve() if here else Path(__file__).resolve().parent
    text = (kit / 'config.mk').read_text()
    top, filename, hooks = validate(text, form)
    if form == 'a0-sort2cmp':
        macro_path = config_value(text, 'MACRO_PLACEMENT_TCL')
        if macro_path != '/work/macro_place.tcl' or not re.search(r'ot_sram_1r1w_128x256_m1_r2c2\s+\{\{43[.]2\s+55[.]056\s+MY\}\}', (kit / 'macro_place.tcl').read_text()):
            raise ValueError('unreviewed A0 macro site or orientation')
        pins = json.loads((kit / 'pins.json').read_text())
        outputs = [pin for pin in pins if pin.get('bus') in ('qa', 'qb')]
        if len(outputs) != 656 or any(pin['face'] != 'N' or (pin['x'] < 216) != (pin['bit'] < 164) for pin in outputs):
            raise ValueError('unreviewed A0 N-face record-bank pin mapping')
    receipt = kit / 'gf5_locality_install.json'
    source = here / filename
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if receipt.exists():
        old = json.loads(receipt.read_text())
        if old['form'] != form or old['helper_sha256'] != digest:
            raise ValueError('existing installation differs; generate a separate private kit')
        if (kit / 'gf5_locality.tcl').read_bytes() != source.read_bytes():
            raise ValueError('installed helper changed after receipt')
        for name, expected in old['installed_hook_sha256'].items():
            if hashlib.sha256((kit / name).read_bytes()).hexdigest() != expected:
                raise ValueError('installed hook changed after receipt')
        if hashlib.sha256((kit / 'gf5_locality_release.tcl').read_bytes()).hexdigest() != old['release_sha256']:
            raise ValueError('release hook changed after receipt')
        return old
    originals = {}
    for name in hooks:
        content = (kit / name).read_text()
        if 'source /work/gf5_locality' in content:
            raise ValueError('existing private GF5 hook has no matching source receipt; preserve it and generate a fresh kit')
        originals[name] = content
    # Validate every input before mutating any hook.
    release = here / 'locality_release.tcl'
    if not release.is_file():
        raise ValueError('missing release helper')
    for name in hooks:
        shutil.copy2(kit / name, kit / (name + '.before_gf5_profile'))
    shutil.copyfile(source, kit / 'gf5_locality.tcl')
    shutil.copyfile(release, kit / 'gf5_locality_release.tcl')
    for name, suffix in zip(hooks, ['source /work/gf5_locality.tcl', 'source /work/gf5_locality_release.tcl']):
        (kit / name).write_text(originals[name] + '\n# PRIVATE GF5 profile: existing hook preserved\n' + suffix + '\n')
    result = {'private': True, 'form': form, 'module': top, 'helper_sha256': digest,
              'config_sha256': hashlib.sha256(text.encode()).hexdigest(), 'hooks': hooks,
              'installed_hook_sha256': {name: hashlib.sha256((kit / name).read_bytes()).hexdigest() for name in hooks},
              'release_sha256': hashlib.sha256(release.read_bytes()).hexdigest(),
              'source_profile': 'bf_svreg_1113', 'policy': 'early GPL full producer/cone guides; release before DPL; no RTL/clock/SDC/pin/cycle/default recipe change',
              'adoption': 'unqualified; all paired F/A0/A1 views require fresh signoff; A1 not supported by this constructor'}
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kit', type=Path)
    parser.add_argument('--form', required=True, choices=FORMS)
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.kit, args.form), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')
