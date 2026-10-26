"""Resolve the selected slice's actual source components for native lowering.

This follows existing wrapper instances. It does not change any master or
qualify a physical binding. OT_S81_SELECTED_ASBUILT_MANIFEST selects the exact
binder file/preference map. OT_S81_SELECTED_CHILD_FILES may explicitly name
implementation children omitted by blackbox elaboration (comma-separated,
repo-relative); they cannot replace any manifest module. Materialized kit inventories remain authoritative
for a run; source-only programmes retain their explicit adoption hold.
"""
import hashlib
import json
from functools import lru_cache
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path('rtl/dsrom_sys/s81_dv/slice')


def bind_defines():
    """the die bind's +define set (port_bind.json defines), e.g. cap14 OT_S81SL_KV_TRANSPORT selects xrt1/xrt3:
    OT_S81_SELECTED_DEFINES=A,B,... (TOKc-S81 10-22); unset = none"""
    return {d for d in os.environ.get('OT_S81_SELECTED_DEFINES', '').split(',') if d}


def preprocess(text, defines=None):
    """resolve `ifdef / `ifndef / `elsif / `else / `endif with the bind defines (no macro expansion)"""
    defines = bind_defines() if defines is None else defines
    out, stack = [], []          # stack of (parent_active, this_branch_taken, active)
    for line in text.split('\n'):
        m = re.match(r'\s*`(ifdef|ifndef|elsif|else|endif)\b\s*(\w*)', line)
        active = all(a for _, _, a in stack)
        if not m:
            if active:
                out.append(line)
            continue
        kw, name = m.groups()
        if kw in ('ifdef', 'ifndef'):
            c = (name in defines) == (kw == 'ifdef')
            stack.append((active, c, c))
        elif kw == 'elsif':
            pa, taken, _ = stack.pop(); c = (not taken) and name in defines
            stack.append((pa, taken or c, c))
        elif kw == 'else':
            pa, taken, _ = stack.pop(); stack.append((pa, True, not taken))
        else:
            stack.pop()
    return '\n'.join(out)


@lru_cache(maxsize=8)
def _manifest_index(root, signature, prefer, files):
    # Signature includes source mtimes/sizes: a changed source never reuses a
    # stale module-definition inventory within a compiler process.
    sys_path = str(Path(__file__).resolve().parents[2] / 'die_plan')
    import sys
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    import bind_elab
    return bind_elab.module_index([], list(files), root)


def manifest_selection(source_root, name):
    """Use the binder's exact file/preference precedence, without default RTL fallback."""
    source_root = source_root.resolve()
    path = Path(name)
    path = path if path.is_absolute() else source_root / path
    path = path.resolve()
    if not path.is_relative_to(source_root):
        raise ValueError('selected source manifest is outside source root')
    ab = json.loads(path.read_text())
    if (path.parent / ab.get('base', '.')).resolve() != source_root:
        raise ValueError('selected source manifest base differs from source root')
    def checked(value):
        item = Path(value)
        if item.is_absolute() or '..' in item.parts:
            raise ValueError('selected source manifest paths must be repo-relative: ' + value)
        item = source_root / item
        if not item.exists() or not item.resolve().is_relative_to(source_root):
            raise ValueError('selected source manifest input absent/outside root: ' + value)
        return str(item)
    files = tuple(dict.fromkeys(checked(f) for f in ab.get('files', [])))
    if not files:
        raise ValueError('selected source manifest has no explicit files')
    # Blackboxed hard leaves need their implementation children for compiler
    # timing. The caller must name those files explicitly; never search a
    # default RTL tree or let an extension replace a manifest-selected module.
    extra_names = [f for f in os.environ.get('OT_S81_SELECTED_CHILD_FILES', '').split(',') if f]
    extras = tuple(checked(f) for f in extra_names)
    prefer = tuple(checked(f) for f in ab.get('prefer', []))
    if ab.get('rtl_roots'):
        raise ValueError('selected source manifest requires explicit files, not search roots')
    actual = bind_defines()
    if actual and actual != set(ab.get('defines', [])):
        raise ValueError('selected source defines differ from as-built manifest')
    signature = tuple((f, Path(f).stat().st_size, Path(f).stat().st_mtime_ns) for f in files)
    idx = _manifest_index(str(source_root), signature, prefer, files)
    if extras:
        extra_signature = tuple((f, Path(f).stat().st_size, Path(f).stat().st_mtime_ns) for f in extras)
        extra_index = _manifest_index(str(source_root), extra_signature, (), extras)
        overlap = {m for m, paths in extra_index.items() if m in idx and set(paths) - set(idx[m])}
        if overlap:
            raise ValueError('selected child files override manifest modules: ' + ', '.join(sorted(overlap)))
        idx = {**extra_index, **idx}
    return path, ab, idx, prefer


def resolve(die, slice_inst, source_root=None):
    explicit = source_root is not None or bool(os.environ.get('OT_S81_SELECTED_SOURCE_ROOT'))
    source_root = Path(source_root or os.environ.get('OT_S81_SELECTED_SOURCE_ROOT') or ROOT)
    sources = {}
    chain = []
    resolved_paths = {}
    manifest = os.environ.get('OT_S81_SELECTED_ASBUILT_MANIFEST')
    selection = manifest_selection(source_root, manifest) if manifest else None
    selected_defines = set(selection[1].get('defines', [])) if selection else None
    if selection:
        sources[str(selection[0].relative_to(source_root))] = hashlib.sha256(selection[0].read_bytes()).hexdigest()

    def body(master):
        if selection:
            import bind_elab
            picked, ambiguous = bind_elab.pick(selection[2], master, selection[3])
            if not picked or ambiguous:
                raise ValueError('selected as-built master missing/ambiguous: ' + master)
            paths = [Path(picked)]
        else:
            paths = list((source_root / BASE).rglob(master + '.sv'))
        if not paths and not selection:
            # Selected wrappers such as xr1/xrt1 can be real module definitions
            # in their family's source file. Resolve the definition, never a
            # similarly named candidate or a presumed compatible alias.
            definition = re.compile(r'\bmodule\s+' + re.escape(master) + r'\b')
            paths = [p for p in (source_root / 'rtl/dsrom_sys/s81_dv').rglob('*.sv')
                     if definition.search(re.sub(r'/\*.*?\*/|//[^\n]*', '', p.read_text(), flags=re.S))]
        if len(paths) != 1:
            raise ValueError('selected slice master needs one explicit source definition: ' + master)
        path = paths[0]
        raw = path.read_text()
        resolved_paths[master] = str(path.relative_to(source_root))
        sources[str(path.relative_to(source_root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        clean = preprocess(re.sub(r'/\*.*?\*/|//[^\n]*', '', raw, flags=re.S), selected_defines)
        match = re.search(r'\bmodule\s+' + re.escape(master) + r'\b(.*?)\bendmodule\b', clean, re.S)
        if not match:
            raise ValueError('selected source does not define master ' + master)
        return match[1]

    def child(text, name):
        match = re.search(r'(?m)^\s*(ot_[A-Za-z0-9_]+)\s*(?:#\s*\([^;]*?\)\s*)?' + re.escape(name) + r'\s*\(', text, re.S)
        return match[1] if match else None

    master = die.inst[slice_inst]['master']
    hb = re.search(r'\.HB\(\s*(\d+)\s*\)', die.inst[slice_inst].get('params', ''))
    hb = int(hb.group(1)) if hb else None
    seen = set()
    while True:
        if master in seen:
            raise ValueError('recursive slice wrapper ' + master)
        seen.add(master)
        text = body(master)
        default_hb = re.search(r'parameter\s+integer\s+HB\s*=\s*(\d+)', text)
        if hb is None and default_hb:
            hb = int(default_hb.group(1))
        chain.append(master)
        xg = child(text, 'u_xg')
        if xg:
            break
        # instance names: u_<x> or the bare wrapper core `u` (ot_s81sl_slice_lepw: `ot_s81sl_slice_lep #(...) u (...)`)
        nested = re.findall(r'(?m)^\s*(ot_s81sl_slice[A-Za-z0-9_]*)\s*(?:#\s*\([^;]*?\)\s*)?(u(?:_[A-Za-z0-9_]+)?)\s*\(', text, re.S)
        # generate branches may instantiate the same child master more than once (lep: u_sl in both HOST_EN arms)
        masters = sorted({m for m, _ in nested})
        if len(masters) != 1:
            raise ValueError('selected slice wrapper child is ambiguous: ' + master)
        master = masters[0]
    cap = child(text, 'u_cap')
    if cap is None:
        raise ValueError('selected source CAP instance is unresolved')
    xr = child(text, 'u_xr')
    xr_options = set(re.findall(r'\b(ot_s81sl_xr[0-9t]*)\s+u_xr\s*\(', text))
    if len(xr_options) > 1:
        if xr_options not in ({'ot_s81sl_xr1', 'ot_s81sl_xr3'}, {'ot_s81sl_xrt1', 'ot_s81sl_xrt3'}) or hb is None:
            raise ValueError('selected XR generate branch requires explicit HB binding')
        xr = next(x for x in xr_options if x.endswith('3' if hb != 0 else '1'))
    if xr is None:
        raise ValueError('selected source XR instance is unresolved')
    before = set(sources)
    body(xr)
    xr_paths = set(sources) - before
    if len(xr_paths) != 1:
        raise ValueError('selected XR source file is unresolved')
    xr_path = xr_paths.pop()
    xg_text = body(xg)
    streamer = child(xg_text, 'u_s')
    ring = child(xg_text, 'u_r')
    if streamer not in ('ot_s81sl_xs', 'ot_s81sl_xs4') or ring is None:
        raise ValueError('selected source streamer/ring pair is unresolved: ' + xg)
    body(streamer)
    body(ring)
    body(cap)
    added = 0
    if streamer == 'ot_s81sl_xs4':
        # capture-stage receipts: XS4 sources whose streamer capture adds exactly ONE edge.
        #   974ec6f3 = the native xs4 (xg5 lineage ab6b3f7b4), capture stage measured.
        #   50485a59 = the G9 GEN-selected physical xs4 (bind rtl_extra 8a495768, S81-FIX2/XG 5feb5dc07 + ELEM-XFV):
        #     974ec6f3 plus kept same-D/same-enable/same-edge register copies only (act_g, hb_q1 -> hbk_o, wps0,
        #     keep_hierarchy bdec predecode = combinational) for native fanout <= 32; no register stage added on any
        #     path (diff-reviewed TOKc-S81 10-22: every new reg is loaded on the same edge/enable as the reg it copies).
        known = {'974ec6f3e0ca8deb84d6690c03f10035213b6a3bc94ff178edeb9549f29b9ca9',
                 '50485a59b26517eb34e2ae4c0918f8480ae0c5e0c96f6246b93c30c6b7970808'}
        if sources[resolved_paths[streamer]] not in known:
            raise ValueError('changed XS4 source has no matching capture-stage receipt')
        added = 1
    return dict(schema='opentallas.s81.selected_slice_source.v1', slice=slice_inst,
                die_master=die.inst[slice_inst]['master'], wrapper_chain=chain,
                xg=xg, ring=ring, streamer=streamer, capture=cap,
                xr=xr, xr_source_path=xr_path,
                selected_hb=hb,
                streamer_added_capture_edges=added, source_sha256=sources,
                source_root=str(source_root), explicit_source_root=explicit, physical_binding_qualified=False,
                selected_asbuilt_manifest=(str(selection[0].relative_to(source_root)) if selection else None),
                resolved_module_sources=resolved_paths,
                qualification='SOURCE RESOLUTION ONLY; exact kit/netlist inventory and runtime clocks remain required')
