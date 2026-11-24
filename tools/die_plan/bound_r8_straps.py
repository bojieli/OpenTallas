"""Project binder-declared, value-audited R8 pad-count inputs into physical metadata."""
import copy
import json
import hashlib
import re
import socket
from pathlib import Path

# FLOW-PROC-A 11-21 (COORD, FAM-QC-CB fp5/fp6): kit_rtl.json named an absolute bind_out that existed on one host only (epyc9);
# on epyc7 the R8 check then said "lack their bind manifest" with no path.  bind.py kit-rtl now copies the small bind
# sidecars a kit's GEN / strap checks read into <kit rtl dir>/bind_sidecars (sha256 recorded in kit_rtl.json), and every
# reader resolves a sidecar kit copy first, then bind_out; a miss names each path tried and the host.
KIT_BIND_DIR = "bind_sidecars"
KIT_BIND_SIDECARS = ("bind_parent_id_straps.json", "bind_r8pad_strap_audit.json", "bind_count_strap_audit.json",
                     "bind_report.json", "bind_tie_audit.json")


def stage_kit_sidecars(bind_out, kd, newer_than=None):
    """copy the KIT_BIND_SIDECARS present in bind_out into kd/bind_sidecars (copy + rename) -> {dir, files {name: sha256}}.
    newer_than (BIND-STREAM-LAUNCH, a kit of a still-running bind): a sidecar older than it belongs to an earlier bind of this OUT
    and is not staged."""
    dst = Path(kd) / KIT_BIND_DIR
    files = {}
    for name in KIT_BIND_SIDECARS:
        src = Path(bind_out) / name
        if not src.is_file():
            continue
        if newer_than is not None and src.stat().st_mtime < newer_than:
            continue
        data = src.read_bytes()
        dst.mkdir(parents=True, exist_ok=True)
        tmp = dst / f".{name}.tmp"
        tmp.write_bytes(data)
        tmp.replace(dst / name)
        files[name] = hashlib.sha256(data).hexdigest()
    return dict(dir=KIT_BIND_DIR, files=files)


ASBUILT_LEAF = "asbuilt_leaf.json"
ASBUILT_LEAF_KEYS = ("sub_core_leaf", "sub_core_leaf_variants", "hard_core_leaf")


def stage_asbuilt_leaf(asbuilt, kd, side):
    """FLOW-PROC-A 11-21 (FAM-QC-CB fp7: gen read asbuilt_manifest, an absolute as-built preview on epyc9 only): the three leaf
    tables gen / bound_macro_paths read from the as-built go into kd/bind_sidecars/asbuilt_leaf.json; sha added to side['files']"""
    if not asbuilt:
        return side
    doc = json.loads(Path(asbuilt).read_text())
    sub = {k: doc.get(k) or {} for k in ASBUILT_LEAF_KEYS} if isinstance(doc, dict) else {k: {} for k in ASBUILT_LEAF_KEYS}
    data = (json.dumps(sub, indent=1, sort_keys=True) + "\n").encode()
    dst = Path(kd) / (side.get("dir") or KIT_BIND_DIR)
    dst.mkdir(parents=True, exist_ok=True)
    tmp = dst / f".{ASBUILT_LEAF}.tmp"
    tmp.write_bytes(data)
    tmp.replace(dst / ASBUILT_LEAF)
    side.setdefault("files", {})[ASBUILT_LEAF] = hashlib.sha256(data).hexdigest()
    return side


def asbuilt_leaf(kit_rtl_json, kr):
    """-> {sub_core_leaf, sub_core_leaf_variants, hard_core_leaf}: the kit copy (sha checked) first, then the recorded
    asbuilt_manifest; {} when the kit names no as-built; FileNotFoundError naming every path tried + host otherwise"""
    kr = kr or {}
    side = kr.get("bind_sidecars") or {}
    if kit_rtl_json:
        p = Path(kit_rtl_json).parent / (side.get("dir") or KIT_BIND_DIR) / ASBUILT_LEAF
        if p.is_file():
            want = (side.get("files") or {}).get(ASBUILT_LEAF)
            if want and hashlib.sha256(p.read_bytes()).hexdigest() != want:
                raise ValueError(f"kit as-built sidecar {p}: sha256 differs from the kit_rtl.json bind_sidecars record")
            return json.loads(p.read_text())
    m = kr.get("asbuilt_manifest")
    if not m:
        return {}
    if Path(m).is_file():
        doc = json.loads(Path(m).read_text())
        return {k: doc.get(k) or {} for k in ASBUILT_LEAF_KEYS} if isinstance(doc, dict) else {}
    tried = ([str(Path(kit_rtl_json).parent / (side.get("dir") or KIT_BIND_DIR) / ASBUILT_LEAF)] if kit_rtl_json else []) + [str(m)]
    raise FileNotFoundError(f"as-built leaf tables not found on host {socket.gethostname().split('.')[0]}; tried {', '.join(tried)}")


def bind_candidates(kit_rtl_json, kr, name):
    """paths tried for bind sidecar `name`, kit copy first"""
    out = []
    side = (kr or {}).get("bind_sidecars") or {}
    if kit_rtl_json:
        out.append(Path(kit_rtl_json).parent / (side.get("dir") or KIT_BIND_DIR) / name)
    if (kr or {}).get("bind_out"):
        out.append(Path(kr["bind_out"]) / name)
    return out


def bind_file(kit_rtl_json, kr, name):
    """-> the first existing sidecar path (a kit copy must match its recorded sha256), or None"""
    want = ((kr or {}).get("bind_sidecars") or {}).get("files", {}).get(name)
    for i, p in enumerate(bind_candidates(kit_rtl_json, kr, name)):
        if p.is_file():
            if i == 0 and kit_rtl_json and want and hashlib.sha256(p.read_bytes()).hexdigest() != want:
                raise ValueError(f"kit bind sidecar {p}: sha256 differs from the kit_rtl.json bind_sidecars record")
            return p
    return None


def missing_text(kit_rtl_json, kr, name):
    tried = ", ".join(str(p) for p in bind_candidates(kit_rtl_json, kr, name)) or "(no bind_out, no kit copy)"
    return f"{name} not found on host {socket.gethostname().split('.')[0]}; tried {tried}"


def read_bind_json(kit_rtl_json, kr, name):
    p = bind_file(kit_rtl_json, kr, name)
    if p is None:
        raise FileNotFoundError(missing_text(kit_rtl_json, kr, name))
    return json.loads(p.read_text())


def declared(kit_rtl_json, width=4, lane_widths=None):
    # KV-102 11-14: width = R8.strap_pad_width(type) (r8_strap_pad_max 26 -> 5 bits), was a hard 4 (kv3_pc_v3 hsl3_fi)
    kr = json.loads(Path(kit_rtl_json).read_text())
    ports = {r['port']: (r['dir'], r['width']) for r in kr.get('bound_only_pins', [])}
    if not kr.get('bind_out'):
        if any(name.startswith('strap_r8pad_') for name in ports):
            raise ValueError('R8 count ports lack their bind authority')
        # Native station/source manifests have no binder metadata to project.
        return []
    mf = bind_file(kit_rtl_json, kr, 'bind_parent_id_straps.json')
    if mf is None:
        if any(name.startswith('strap_r8pad_') for name in ports):
            raise ValueError('R8 count ports lack their bind manifest: '
                             + missing_text(kit_rtl_json, kr, 'bind_parent_id_straps.json'))
        return []
    manifest = json.loads(mf.read_text())
    rows = manifest.get('types', {}).get(kr.get('bound_type', kr.get('type')), {})
    result = []
    for name, row in rows.items():
        if row.get('kind') != 'r8pad_strap':
            continue
        # KV-PCV3-R8 11-16: each strap carries its OWN bind width, 4 (default) or the type's strap_pad_width when a
        # bus of that type needs more (kv3_pc_v3: hsl3_fi 5 bits, slg_vreq 4 bits); `width` is the type maximum.
        # FAM-KV-IOPC-R3 11-21: bind.r8_pad_width gives max(4, span.bit_length()) per site, so any width 4..type maximum is
        # the bind's own (D27d2 kv3_pc_v3, r8_strap_pad_max 63 -> type width 6: hsl3_fi 5, slg_x_tep 6, others 4; gen refused 5).
        w = row.get('width')
        # KV-ALLFIX 11-24: a lane-count strap (strap_r8pad_lane_*, bind.lane_count_width / bind_lane_counts) takes the
        # plan count_straps width verbatim (A5t3 kv3_pc_v1__cl4ea58a5c__r8*: i_hsl_Q_N_fo span 1 -> width 1, CW=1 bank);
        # only R8 pad sites use max(4, span.bit_length()).
        lane_w = (lane_widths or {}).get(name)
        legal = (w == lane_w and w >= 1) if lane_w is not None else (type(w) is int and 4 <= w <= max(4, width))
        if type(w) is not int or not legal or not re.fullmatch(r'strap_r8pad_[A-Za-z0-9_]+', name) or ports.get(name) != ('input', w):
            raise ValueError(f'invalid bound R8 count declaration: {name}')
        audit = read_bind_json(kit_rtl_json, kr, 'bind_r8pad_strap_audit.json')
        if audit.get('verdict') != 'PASS' or audit.get('errors') or audit.get('checked_bits', 0) < w:
            raise ValueError(f'R8 count value audit not PASS: {name}')
        owners = kr.get('instances', [])
        if (not isinstance(owners, list) or not owners or any(not isinstance(q, str) for q in owners)
                or len(set(owners)) != len(owners)):
            raise ValueError(f'R8 count lacks exact owning instances: {name}')
        values = [manifest.get('instances', {}).get(q, {}).get(name, {}) for q in owners]
        if any(v.get('kind') != 'r8pad_strap' or v.get('width') != w or type(v.get('value')) is not int or not 0 <= v['value'] < (1 << w) for v in values):
            raise ValueError(f'R8 count owning-instance ties absent/invalid: {name}')
        result.append({'name': name, 'width': w})
    actual_r8 = {name for name in ports if name.startswith('strap_r8pad_')}
    if actual_r8 != {row['name'] for row in result}:
        raise ValueError('R8 count ports disagree with the declared bind inventory')
    return result


def project(raw, kit_rtl):
    result = raw
    for tn, fl in (kit_rtl or {}).items():
        kit_json = Path(fl).with_name('kit_rtl.json')
        if not kit_json.is_file():
            # A plain native filelist carries no bound metadata to promote.
            continue
        try:
            import r8 as _R8
            _w = _R8.strap_pad_width(raw.get('partition_types', {}).get(tn, {}))
        except ImportError:
            _w = 4
        _lw = {r['name']: r['width'] for r in raw.get('partition_types', {}).get(tn, {}).get('count_straps', ())
               if str(r.get('name', '')).startswith('strap_r8pad_lane_') and type(r.get('width')) is int}
        additions = declared(kit_json, _w, _lw)
        if not additions:
            continue
        kr = json.loads(kit_json.read_text())
        parts = {p['name']: p['type'] for p in raw.get('partitions', [])}
        if kr.get('plan_type') != tn or any(parts.get(q) != tn for q in kr['instances']):
            raise ValueError(f'type {tn}: R8 kit instances disagree with owning plan type')
        if result is raw:
            result = copy.deepcopy(raw)
        t = result['partition_types'][tn]
        existing = {r['name']: r for r in t.get('id_straps', []) + t.get('count_straps', [])}
        for row in additions:
            old = existing.get(row['name'])
            if old and old['width'] != row['width']:
                raise ValueError(f'conflicting R8 count declaration: {row["name"]}')
            if not old:
                t.setdefault('count_straps', []).append(row)
                existing[row['name']] = row
    return result
