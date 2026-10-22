#!/usr/bin/env python3
"""QK3-PHYCLK 10-21: complete a die-clock targets.json with the die STA's own zero-insertion boundary contract.

The KV die STA (tools/qwen_kv_die/kvsys_clocks.py) times every clock sink of a master WITHOUT a measured view at
R = 0 and lists it in clocks.json 'assumed_ideal' (the off-chip boundary PHY abstracts ot_qkvd_ucie_x64_phy /
ot_qfd_serdes_112g_x12_phy and the generated pin-registered element models in qfd_elements_<c>.lib).  The die clock
build (build.py load_targets) refuses any sink master without an R -- kv_die_clock_regions.sh wrote only the measured
masters, so kvs14r-*-sqk2* DIECLK died on 'missing native insertion R for ot_qkvd_ucie_x64_phy/clk'.

This tool writes the SAME contract the STA uses into targets.json, never an invented number: each assumed master's
cell is read from the run's own bound Liberty (every corner); R = 0 is admitted ONLY when that cell carries no
min/max_clock_tree_path anywhere and every timing arc is related to one of its own clock pins (its boundary timing is
referenced to the clock pin, i.e. there is no internal tree in the model) -- the documented hard-macro convention of
tools/s81/die_sta.py ('hard macro: liberty arcs referenced to the clock pin (no internal tree), R = 0') and of
tools/qwen_tp8/die_sta_libs.py (licensed link-PHY hard macro: its Liberty IS the boundary model).  A cell with a tree
path, an arc referenced to a non-clock pin, a missing corner, or a sink pin the cell does not declare FAILS.

Every such entry is labelled (view, reference_kind, model class, lib sha256) and listed under 'assumed' so the clock
report says which R are model boundaries, not measurements.  Off-chip PHYs are owner-allowed models (only PHY /
off-chip signals may be modeled); internal element models stay 'ASSUMED (ideal 0, no measured view)' exactly as the
compute-die prep (qwen_compute_dieclk_prep.py) labels them.

  boundary_targets.py --clocks RUN/libs/clocks.json --libs RUN/libs --targets DIECLK/targets.json
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

CORNERS = ('ss', 'ff', 'tt')            # build.py order: [ss, ff, tt]
PHY_CLASS = 'OFFCHIP_BOUNDARY_PHY_MODEL'
ELEM_CLASS = 'GENERATED_PIN_REGISTERED_ELEMENT_MODEL'


def groups(text, kind):
    """(name, body) of every `kind (name) { ... }` group at any depth of text (balanced braces)."""
    for m in re.finditer(r'\b' + kind + r'\s*\(\s*"?([^)"]*?)"?\s*\)\s*\{', text):
        i, depth = m.end(), 1
        while depth and i < len(text):
            depth += (text[i] == '{') - (text[i] == '}')
            i += 1
        if depth:
            raise ValueError(f'unterminated Liberty {kind} group {m.group(1)}')
        yield m.group(1).strip(), text[m.end():i - 1]


def cell_body(lib_text, master):
    cells = [b for n, b in groups(lib_text, 'cell') if n == master]
    if len(cells) > 1:
        raise ValueError(f'{master}: {len(cells)} cell groups')
    return cells[0] if cells else None


def boundary_clock_pins(body, master):
    """-> {lib clock pin spelling: base name}; raises unless the cell is a pin-referenced boundary model."""
    if re.search(r'\b(min|max)_clock_tree_path\b', body):
        raise ValueError(f'{master}: Liberty carries a clock_tree_path (internal insertion) -- R is not 0, measure it')
    clocks, others = {}, set()
    for kind in ('pin', 'bus'):
        for name, pb in groups(body, kind):
            head = pb.split('timing', 1)[0]
            if re.search(r'\bclock\s*:\s*true\s*;', head):
                if not re.search(r'\bdirection\s*:\s*input\s*;', head):
                    raise ValueError(f'{master}/{name}: clock pin is not an input')
                clocks[f'{name}[0]' if kind == 'bus' else name] = name
            else:
                others.add(name)
    if not clocks:
        raise ValueError(f'{master}: no clock pin in Liberty')
    related = set(re.findall(r'\brelated_pin\s*:\s*"?([^";\s]+)"?\s*;', body))
    if not related:
        raise ValueError(f'{master}: no timing arcs (boundary timing would be unconstrained)')
    bases = {r.split('[')[0] for r in related}
    stray = bases - set(clocks.values())
    if stray:
        raise ValueError(f'{master}: timing arcs referenced to non-clock pins {sorted(stray)} -- not a pin-referenced model')
    return clocks


def find_cell(libs_dir, master, corner):
    hits = []
    for f in sorted(Path(libs_dir).glob(f'*_{corner}.lib')):
        t = f.read_text(errors='replace')
        if master not in t:
            continue
        b = cell_body(t, master)
        if b is not None:
            hits.append((f, b))
    if len(hits) != 1:
        raise ValueError(f'{master}: {corner} cell in {len(hits)} libs of {libs_dir} ({[str(h[0].name) for h in hits]})')
    return hits[0]


def target(master, libs_dir):
    pins, files = None, {}
    for c in CORNERS:
        f, body = find_cell(libs_dir, master, c)
        p = boundary_clock_pins(body, master)
        if pins is not None and p != pins:
            raise ValueError(f'{master}: clock pins differ across corners {pins} vs {p}')
        pins = p
        files[c] = dict(lib=f.name, sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    phy = master.startswith('ot_') and all(v['lib'] == f'qfd_etm_{master}_{c}.lib' for c, v in files.items())
    cls = PHY_CLASS if phy else ELEM_CLASS
    return dict(
        view='PHY_BOUNDARY_MODEL (licensed-IP abstract)' if phy else 'ASSUMED (ideal 0, no measured view)',
        source='die STA clocks.json assumed_ideal (R 0) + bound Liberty: no clock_tree_path, every arc related to its '
               'own clock pin (pin-referenced boundary; s81/die_sta.py hard-macro convention)',
        reference_kind='LIBERTY_ARCS_PIN_REFERENCED', model_class=cls, internal_tree='NONE_IN_MODEL',
        liberty=files, insertion_per_clock_pin_ps={p: [0.0, 0.0, 0.0] for p in sorted(pins)})


def complete(clocks, libs_dir, targets):
    masters = targets.setdefault('masters', {})
    added = {}
    for m in clocks.get('assumed_ideal', []):
        if m in masters:
            continue
        masters[m] = target(m, libs_dir)
        added[m] = masters[m]['model_class']
    targets['assumed'] = sorted(set(targets.get('assumed', [])) | set(added))
    targets['boundary_contract'] = dict(
        tool='tools/die_clock/boundary_targets.py', rule='R = 0 only for a pin-referenced Liberty boundary (no tree '
        'path, arcs related to own clock pins) = the die STA source latency for the same sinks',
        phy_models=sorted(m for m, c in added.items() if c == PHY_CLASS),
        element_models=sorted(m for m, c in added.items() if c == ELEM_CLASS))
    return added


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--clocks', type=Path, required=True)
    ap.add_argument('--libs', type=Path, required=True)
    ap.add_argument('--targets', type=Path, required=True)
    a = ap.parse_args(argv)
    t = json.loads(a.targets.read_text())
    added = complete(json.loads(a.clocks.read_text()), a.libs, t)
    a.targets.write_text(json.dumps(t, indent=1) + '\n')
    phy = [m for m, c in added.items() if c == PHY_CLASS]
    print(f'BOUNDARY_TARGETS added={len(added)} phy={len(phy)} ({",".join(phy)}) elements={len(added) - len(phy)}')


if __name__ == '__main__':
    main()
