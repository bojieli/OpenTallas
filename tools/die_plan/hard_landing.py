"""Compose proved landing faces through exact, opaque signed hard children.

This is not a macro exemption: the child landing is re-proved from its captured
synthesis netlist, and the parent must connect each declared bit directly to
that child's corresponding input and its declared forwarded clock.
"""
import copy
import hashlib
import json
import re
import shutil
from pathlib import Path

# Proofs depend only on these exact captured bytes. Every call still verifies
# all files and the actual parent's selected views before consulting the memo.
_PROOFS = {}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def prove(directory):
    """Validate a staged, self-contained child receipt and re-prove its faces."""
    import face_guard as F
    d = Path(directory)
    m = read(d / 'manifest.json')
    if m.get('schema') != 'hard_landing/1':
        raise ValueError('unknown hard landing evidence schema')
    for name, sha in m['sha256'].items():
        if Path(name).name != name or digest(d / name) != sha:
            raise ValueError(f'hard landing evidence hash mismatch: {name}')
    p, s, old = (read(d / x) for x in ('provenance.json', 'signoff.json', 'face_guard.json'))
    master = m['master']
    if p.get('kit', {}).get('module') != master or old.get('top') != master:
        raise ValueError('hard landing evidence master mismatch')
    if s.get('verdict') != 'SIGNED' or old.get('verdict') != 'PASS':
        raise ValueError('hard landing requires SIGNED child and PASS face evidence')
    if digest(d / 'signoff.json') != p['export']['signoff_sha256']:
        raise ValueError('hard landing signoff is not the exported view signoff')
    # Freeze *_sha256 fields identify tool scripts, not result JSON files.
    if digest(d / 'face_guard_source.py') != p['kit']['face_guard_sha256']:
        raise ValueError('hard landing face tool is not the frozen child tool')
    captured = s.get('face_guard', {})
    if (captured.get('verdict') != 'PASS' or captured.get('top') != master
            or captured.get('netlist') != m['netlist_source']):
        raise ValueError('hard landing netlist is not the signed face-proof input')
    for name in (m['lef'], m['lib']):
        if digest(d / name) != p['export']['files_sha256'][name]:
            raise ValueError('hard landing selected view is not the signed export')
        if digest(d.parents[1] / name) != digest(d / name):
            raise ValueError('parent macro view differs from the proved child view')
    land = F.kit_land(d / 'land_slots.json')
    if land.get('d') != {'D': m['D'], 'form': 'hold_mux'}:
        raise ValueError('hard landing child depth/form mismatch')
    if land.get('t_rst_n') != {'form': 'ring_start', 'ring': 'd'}:
        raise ValueError('hard landing child START contract missing')
    key = digest(d / 'manifest.json')
    if key in _PROOFS:
        return m, _PROOFS[key]
    result = F.guard((d / 'netlist.v').read_text(), top=master,
                     clocks=['clk', 'fclk'], straps=['strap_k'], land=land)
    ring = result.get('ring_start', {}).get('t_rst_n', {})
    if (result['verdict'] != 'PASS' or result.get('land_mux_bits') != m['width']
            or ring.get('ring_clock') != ['fclk'] or not ring.get('writer_flops')):
        raise ValueError(f'hard landing actual child proof failed: {result.get("fails")}')
    _PROOFS[key] = result
    return m, result


def emit(t, land, kit, root):
    """Replace only declared soft rings selected as actual hard children."""
    if not land:
        return land
    import cores
    out = copy.deepcopy(land)
    for c in t.get('hard_cores', []):
        wrap = c.get('param_wrap', {})
        if wrap.get('base') not in ('ot_dp_clk_landing_ca', 'ot_dp_clk_landing_cas'):
            continue
        inst = c.get('physical_inst', c['inst'])
        match = re.fullmatch(r'(?:\w+\.)*u_cland_(\w+)', inst)
        if not match or match[1] not in out['buses']:
            continue
        bus = match[1]
        spec = out['buses'][bus]
        params = wrap['params']
        if (spec != {'D': params['DEPTH'], 'form': 'hold_mux'}
                or params.get('WREG') != 1 or params.get('WFALL') != 1):
            raise ValueError(f'{inst}: selected hard landing does not match declared ring')
        master = c.get('physical_master', c['module'])
        lef, lib = (cores.resolve(c[k], root) for k in ('lef', 'lib'))
        dest = Path(kit) / 'macros' / 'landing' / master
        portable = lef.parent / 'landing_evidence'
        if portable.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            manifest = read(portable / 'manifest.json')
            for name in ['manifest.json', *manifest['sha256']]:
                if Path(name).name != name:
                    raise ValueError('invalid portable hard landing evidence path')
                shutil.copyfile(portable / name, dest / name)
        else:
            capture(lef, lib, master, params['DEPTH'], params['W'], dest)
        # These are already staged by gen_phys; also support the standalone
        # contract emission used to diagnose an immutable parent kit.
        for path in (lef, lib):
            selected = Path(kit) / 'macros' / path.name
            if not selected.exists():
                shutil.copyfile(path, selected)
        prove(dest)
        row = dict(form='hard_child', D=params['DEPTH'], instance=inst,
                   master=master, port='d', width=params['W'], clock_pin='fclk',
                   clock_port='fclk_in_' + bus,
                   evidence=str(dest.relative_to(kit)))
        out['buses'][bus] = row
        for name, v in list(out['buses'].items()):
            if isinstance(v, dict) and v.get('form') == 'ring_start' and v.get('ring') == bus:
                out['buses'][name] = dict(row, port='t_rst_n', width=1)
    return out


def capture(lef, lib, master, depth, width, dest):
    """Copy immutable inputs only; callers MUST prove before consuming them.

    The resulting directory can be retained as a view's landing_evidence, so a
    fresh parent kit does not depend on the original build host or run path.
    """
    lef, lib, dest = Path(lef), Path(lib), Path(dest)
    pv = lef.parent / 'provenance.json'
    src = Path(read(pv)['src'])
    old = read(src / 'face_guard.json')
    net = Path(old['netlist'])
    if str(net).startswith('/work/'):
        net = src / str(net)[6:]
    dest.mkdir(parents=True, exist_ok=True)
    paths = {'provenance.json': pv, 'signoff.json': lef.parent / 'signoff.json',
             'face_guard.json': src / 'face_guard.json',
             'face_guard_source.py': src / 'face_guard.py',
             'land_slots.json': src / 'land_slots.json', 'netlist.v': net,
             lef.name: lef, lib.name: lib}
    for name, path in paths.items():
        shutil.copyfile(path, dest / name)
    manifest = dict(schema='hard_landing/1', master=master, D=depth, width=width,
                    lef=lef.name, lib=lib.name, netlist_source=str(net),
                    sha256={name: digest(dest / name) for name in paths})
    (dest / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    return manifest
