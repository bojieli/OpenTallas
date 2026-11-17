"""Compose proved landing faces through exact, opaque signed hard children.

This is not a macro exemption: the child landing is re-proved from its captured
synthesis netlist, and the parent must connect each declared bit directly to
that child's corresponding input and its declared forwarded clock.
"""
import copy
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

# Proofs depend only on these exact captured bytes. Every call still verifies
# all files and the actual parent's selected views before consulting the memo.
_PROOFS = {}
CA_BASES = ('ot_dp_clk_landing_ca', 'ot_dp_clk_landing_cas')
# CLAND-MACRO-1 11-14: the plain forwarded-clock ring (ot_dp_clk_landing, fixed DEPTH 4 ot_meso_ring) as a hard child:
# no START port (t_rst_n), no strap; its land_slots declaration is d {D 4, hold_mux} only.
PLAIN_BASE = 'ot_dp_clk_landing'
PLAIN_DEPTH = 4
# KITPACK-CLOSE-1115 (COORD r221 F1): what gen does with a landing child view that is not closed (no landing_evidence/).
# 'warn' = log VIEW_NOT_CLOSED and fall back to following provenance.src (never blocks a launch);
# 'strict' = refuse.  Flip to strict (this one line) once backfill_views.py reports 0 open.  OT_VIEW_CLOSED_MODE overrides.
VIEW_CLOSED_MODE = 'warn'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def prove(directory):
    """Validate a staged, self-contained child receipt and re-prove its faces."""
    import face_guard as F
    import signoff_profile as SP
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
    # Older frozen signers retain LOCAL_PASS_NEEDS_PARENT for boundary hold.
    # Re-judge the immutable receipt using the same canonical profile as the
    # sign-off chain: a label alone never proves internal FF closure.
    qualification = SP.judge(s) if SP.is_minimal() else None
    signed = qualification['verdict'] == 'SIGNED' if qualification else s.get('verdict') == 'SIGNED'
    if not signed or old.get('verdict') != 'PASS':
        reason = '; '.join(qualification['reasons']) if qualification and not signed else ''
        raise ValueError('hard landing requires profile-qualified SIGNED child and PASS face evidence'
                         + (': ' + reason if reason else ''))
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
    plain = m.get('base') == PLAIN_BASE
    if land.get('d') != {'D': m['D'], 'form': 'hold_mux'}:
        raise ValueError('hard landing child depth/form mismatch')
    if plain:
        if set(land) != {'d'}:
            raise ValueError('plain hard landing child declares more than its d ring')
    elif land.get('t_rst_n') != {'form': 'ring_start', 'ring': 'd'}:
        raise ValueError('hard landing child START contract missing')
    key = digest(d / 'manifest.json')
    if key in _PROOFS:
        return m, _PROOFS[key]
    result = F.guard((d / 'netlist.v').read_text(), top=master,
                     clocks=['clk', 'fclk'], straps=[] if plain else ['strap_k'], land=land,
                     ring_reset=bool(re.search(r"\brst_xn\b", (d / 'netlist.v').read_text())))
    ring = result.get('ring_start', {}).get('t_rst_n', {})
    if (result['verdict'] != 'PASS' or result.get('land_mux_bits') != m['width']
            or (not plain and (ring.get('ring_clock') != ['fclk'] or not ring.get('writer_flops')))):
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
        base = wrap.get('base')
        if base not in CA_BASES and base != PLAIN_BASE:
            continue
        inst = c.get('physical_inst', c['inst'])
        match = re.fullmatch(r'(?:\w+\.)*u_cland_(\w+)', inst)
        if not match or match[1] not in out['buses']:
            continue
        bus = match[1]
        spec = out['buses'][bus]
        params = wrap['params']
        depth = PLAIN_DEPTH if base == PLAIN_BASE else params.get('DEPTH')
        # CLAND-MACRO-1 11-14: the writer edge (WFALL / WNEG) is the child's own signed timing, not a contract term:
        # HEAD rings are rising-edge WREG rings.  The count-aligned START contract still needs the registered writer.
        if spec != {'D': depth, 'form': 'hold_mux'} or (base != PLAIN_BASE and params.get('WREG') != 1):
            raise ValueError(f'{inst}: selected hard landing does not match declared ring')
        master = c.get('physical_master', c['module'])
        # QC-PLAN-R3 11-17: a raw plan row carries no view; kit_wave.prov_stage fills the signed provider lef/lib
        # before GEN.  Name the missing view instead of a bare KeyError (D2 st_a smoke ran GEN on the raw POR).
        missing = [k for k in ('lef', 'lib') if not c.get(k)]
        if missing:
            raise ValueError(f'{inst}: selected hard landing {master} has no {"/".join(missing)} view; resolve its '
                             'signed provider view (kit_wave prov_stage) before GEN')
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
            mode = os.environ.get('OT_VIEW_CLOSED_MODE') or VIEW_CLOSED_MODE
            if mode == 'strict':
                raise ValueError(f'VIEW_NOT_CLOSED {lef.parent}: no landing_evidence/ (run backfill_views.py or re-export with export_view.py)')
            print(f'VIEW_NOT_CLOSED (warn) {lef.parent}: no landing_evidence/; following provenance.src', file=sys.stderr)
            capture(lef, lib, master, depth, params['W'], dest, base=base)
        # These are already staged by gen_phys; also support the standalone
        # contract emission used to diagnose an immutable parent kit.
        for path in (lef, lib):
            selected = Path(kit) / 'macros' / path.name
            if not selected.exists():
                shutil.copyfile(path, selected)
        prove(dest)
        row = dict(form='hard_child', D=depth, instance=inst,
                   master=master, port='d', width=params['W'], clock_pin='fclk',
                   clock_port='fclk_in_' + bus,
                   evidence=str(dest.relative_to(kit)))
        out['buses'][bus] = row
        for name, v in list(out['buses'].items()):
            if isinstance(v, dict) and v.get('form') == 'ring_start' and v.get('ring') == bus:
                out['buses'][name] = dict(row, port='t_rst_n', width=1)
    return out


def capture(lef, lib, master, depth, width, dest, base='ot_dp_clk_landing_cas'):
    """Copy immutable inputs only; callers MUST prove before consuming them.

    The resulting directory can be retained as a view's landing_evidence, so a
    fresh parent kit does not depend on the original build host or run path.
    """
    lef, lib, dest = Path(lef), Path(lib), Path(dest)
    pv = lef.parent / 'provenance.json'
    provenance = read(pv)
    # FIX-CLASSIFY 11-14: a stub provenance (no 'src', empty 'export': a view written only so gen finds the file) carries
    # no landing evidence; say so instead of KeyError 'src' (classified as tool skew) -- the view must be built/exported
    if not provenance.get('src') or not provenance.get('export', {}).get('signoff'):
        raise ValueError(f'hard landing evidence unavailable: {pv} has no src/export.signoff (stub provenance, view not '
                         f'exported from a signed-off build); WAIT-DEP child view {master} needs a signed export')
    src = Path(provenance['src'])
    signoff = lef.parent / 'signoff.json'
    if not signoff.is_file():
        signoff = Path(provenance['export']['signoff'])
    if digest(signoff) != provenance['export']['signoff_sha256']:
        raise ValueError('hard landing captured signoff differs from the exported receipt')
    old = read(src / 'face_guard.json')
    net = Path(old['netlist'])
    if str(net).startswith('/work/'):
        net = src / str(net)[6:]
    dest.mkdir(parents=True, exist_ok=True)
    paths = {'provenance.json': pv, 'signoff.json': signoff,
             'face_guard.json': src / 'face_guard.json',
             'face_guard_source.py': src / 'face_guard.py',
             'land_slots.json': src / 'land_slots.json', 'netlist.v': net,
             lef.name: lef, lib.name: lib}
    for name, path in paths.items():
        shutil.copyfile(path, dest / name)
    manifest = dict(schema='hard_landing/1', master=master, D=depth, width=width,
                    **({'base': base} if base == PLAIN_BASE else {}),
                    lef=lef.name, lib=lib.name, netlist_source=str(net),
                    sha256={name: digest(dest / name) for name in paths})
    (dest / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    return manifest


def close_view(vd, kit, mod, signoff):
    """KITPACK-CLOSE-1115: make view dir `vd` CLOSED from its build dir `kit`: copy `signoff` into it as signoff.json and, for a
    hard landing child (kit has face_guard.json + land_slots.json with a d ring), the receipt into <vd>/landing_evidence/.
    Used by export_view (new views) and backfill_views (existing ones).  -> (closure {name: sha}, [problems])"""
    vd, kit = Path(vd), Path(kit)
    closure, problems = {'signoff.json': digest(signoff)}, []
    if Path(signoff).resolve() != (vd / 'signoff.json').resolve():
        shutil.copy2(signoff, vd / 'signoff.json')
    fg, ls = kit / 'face_guard.json', kit / 'land_slots.json'
    if not (fg.is_file() and ls.is_file()):
        return closure, problems
    try:
        land = read(ls).get('buses') or {}
        d = land.get('d')
        depth = d.get('D') if isinstance(d, dict) else d
        width = read(fg).get('land_mux_bits')
        if depth is None or width is None:
            return closure, problems
        base = PLAIN_BASE if set(land) == {'d'} else 'ot_dp_clk_landing_cas'
        ev = vd / 'landing_evidence'
        if ev.exists():
            shutil.rmtree(ev)
        man = capture(vd / f'{mod}.lef', vd / f'{mod}_tt.lib', mod, depth, width, ev, base=base)
        closure['landing_evidence'] = sorted(man['sha256'])
    except Exception as e:
        problems.append(f'VIEW_NOT_CLOSED {vd}: {type(e).__name__}: {e}')
    return closure, problems
