#!/usr/bin/env python3
"""Generate FUP local-reset candidates from an ACTUAL six-column connection dump.

Use after the existing face/core placement hooks, then release before DPL. This
never changes a plan: the compose lane appends the emitted clock sinks, keeps
qfd_dv_s6_rst2_local, and opts full qfd_dv_s6_fup leaves into the explicit
qfd_dv_s6_fup_reset_local as-built variant. An actual post-DPL complete reset
and data reach census is still required. Clock/timing/route are not qualified.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


def read_conn(path):
    rows = {}
    drivers = defaultdict(list)
    for line in Path(path).read_text().splitlines():
        parts = line.split('\t')
        if len(parts) != 6:
            raise ValueError('connection dump must have six fields')
        name, ref, x, y, ins, outs = parts
        name = name.replace('\\', '').replace('/', '.')
        rows[name] = dict(ref=ref, xy=[float(x), float(y)], ins=ins.split(), outs=outs.split())
        for net in outs.split():
            drivers[net].append(name)
    return rows, drivers


def reset_sources(nets, rows, drivers):
    seen, todo, ends = set(), list(nets), set()
    while todo:
        net = todo.pop()
        if net in seen:
            continue
        seen.add(net)
        for name in drivers.get(net, ()):
            row = rows[name]
            if 'DFF' in row['ref'] or row['ref'] == 'PORT':
                ends.add(name)
            else:
                todo.extend(row['ins'])
    return ends


def distance(a, b):
    return sum(abs(x-y) for x, y in zip(a, b))


def centre(points):
    # L1 minimax centre, with no source-index/layout inference.
    u = [x+y for x, y in points]
    v = [x-y for x, y in points]
    cu, cv = (max(u)+min(u))/2, (max(v)+min(v))/2
    return [(cu+cv)/2, (cu-cv)/2]


def candidate(conn, type_name):
    rows, drivers = read_conn(conn)
    first = [n for n, r in rows.items() if 'DFF' in r['ref'] and re.search(r'\.u_rl\.rs1\$_DFF', n)]
    if len(first) != 1:
        raise ValueError(f'{type_name}: expected one full-FUP rst stage, got {len(first)}; inspect actual master')
    prefix = first[0].split('.u_rl.rs1')[0]
    roots = reset_sources(rows[first[0]]['ins'], rows, drivers)
    if len(roots) != 1:
        raise ValueError(f'{type_name}: expected one delivered-reset source, got {sorted(roots)}')
    root_name, = roots
    root = rows[root_name]['xy']
    groups = {}
    clock_sinks, anchors = [], []
    for group, tail, wanted in [('agu', r'agu_q\[\d+\]', 10),
                                ('chu', r'chu_q\[(?:547|1094)\]', 2),
                                ('cmd', r'cmd_o\[0\]', 1)]:
        names = [n for n, r in rows.items() if 'DFF' in r['ref'] and
                 re.match(re.escape(prefix)+r'\.'+tail+r'\$_DFF', n)]
        if len(names) != wanted:
            raise ValueError(f'{type_name} {group}: expected {wanted} real control FFs, got {len(names)}')
        pts = [rows[n]['xy'] for n in names]
        target = centre(pts)
        second = list(target)
        axis = max(range(2), key=lambda a: abs(root[a]-target[a]))
        # Leave an eight-um strip around the existing FIRM control cells.
        second[axis] += 8 if root[axis] > target[axis] else -8
        first_xy = [(a+b)/2 for a, b in zip(root, second)]
        hops = [distance(root, first_xy), distance(first_xy, second)] + [distance(second, p) for p in pts]
        if max(hops) > 405:
            raise ValueError(f'{type_name} {group}: candidate still needs {max(hops):.3f}um >405')
        groups[group] = dict(cells=names, centre_um=target, stage1_um=first_xy, stage2_um=second,
                             root_to_stage1_um=hops[0], stage1_to_stage2_um=hops[1],
                             stage2_to_controls_max_um=max(hops[2:]), max_hop_um=max(hops))
        for stage, xy in [('rs1', first_xy), ('(?:rs2|rst)', second)]:
            pat = '^'+re.escape(prefix)+r'\.g_local_reset\.u_'+group+r'\.'+stage+r'\$_DFF'
            anchors.append([pat, *xy])
            clock_sinks.append([*xy, 1])
    report = dict(type=type_name, source=str(conn), verdict='PASS-COND PLACE CANDIDATE ONLY',
                  master='qfd_dv_s6_fup', variant='qfd_dv_s6_fup_reset_local',
                  root=dict(name=root_name, xy_um=root), groups=groups, anchors=anchors,
                  clock_sink_sites_um_append=clock_sinks,
                  synth_keep_modules_append=['qfd_dv_s6_rst2_local'],
                  added_data_cycles=0, added_reset_cycles=0,
                  required='post-DPL all data/reset arcs <=405um; clock/timing/route NOT RUN')
    return report, rows


def tcl(report, release=False):
    body = ['# Generated from actual '+report['type']+' control FFs; no guessed sites.',
            'set fup_blk [ord::get_db_block]', 'set fup_dbu [[ord::get_db_tech] getDbUnitsPerMicron]',
            'set fup_rows {']
    body += [' {{%s} %.6f %.6f}' % tuple(a) for a in report['anchors']]
    body += ['}', 'foreach row $fup_rows {', ' lassign $row pat x y', ' set matches {}',
             ' foreach i [$fup_blk getInsts] {', '  set m [$i getMaster]',
             '  if {![string match *DFF* [$m getName]]} continue',
             '  set name [string map {\\\\ {} / .} [$i getName]]',
             '  if {[regexp $pat $name]} {lappend matches $i}', ' }',
             ' if {[llength $matches] != 1} {error "FUP reset anchor $pat found [llength $matches] FFs"}',
             ' set i [lindex $matches 0]']
    if release:
        body += [' $i setPlacementStatus PLACED']
    else:
        body += [' $i setPlacementStatus PLACED',
                 ' $i setLocation [expr {round($x*$fup_dbu)}] [expr {round($y*$fup_dbu)}]',
                 ' $i setPlacementStatus FIRM']
    return '\n'.join(body+['}', ''])


def plot(report, rows, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 12), dpi=110)
    xy = [r['xy'] for r in rows.values() if 'DFF' in r['ref']]
    ax.scatter([p[0] for p in xy], [p[1] for p in xy], s=.12, c='#bbb')
    root = report['root']['xy_um']
    ax.scatter(*root, s=70, marker='*', c='k', label='delivered reset FF')
    for (group, g), color in zip(report['groups'].items(), ['#1674aa', '#d4800c', '#bd2873']):
        a, b = g['stage1_um'], g['stage2_um']
        ax.plot([root[0], a[0], b[0]], [root[1], a[1], b[1]], '-o', c=color,
                label=group+' max %.1fum'%g['max_hop_um'])
        for n in g['cells']:
            q = rows[n]['xy']
            ax.plot([b[0], q[0]], [b[1], q[1]], c=color, lw=.6)
        ax.text(b[0]+8, b[1]+8, group, c=color)
    ax.set_aspect('equal'); ax.legend(fontsize=8)
    ax.set_title(report['type']+' private two-stage reset candidate\nactual source/control sites; no timing/route claim')
    fig.savefig(path, bbox_inches='tight')


def load_fe_reset_overlay(path):
    """I/O boundary: read the committed compose overlay and its exact site reports."""
    path = Path(path).resolve()
    overlay = json.loads(path.read_text())
    # Paths in compose_overlay.json are repository relative, never machine paths.
    root = path.parents[2]
    overlay["site_reports"] = {name: json.loads((root / rel).read_text())
                               for name, rel in overlay["per_type"].items()}
    return overlay


def apply_fe_reset_overlay(raw, asbuilt, *, enabled=False, overlay=None):
    """Pure, default-OFF dictionary transform. Pass parsed load_fe_reset_overlay data.

    Returns independent raw/asbuilt copies plus a short change record. The
    caller owns writing files and applying this inside the single QC event.
    """
    from copy import deepcopy
    raw, asbuilt = deepcopy(raw), deepcopy(asbuilt)
    record = dict(enabled=bool(enabled), changed_types=[], holds=[], added_data_cycles=0, added_reset_cycles=0)
    if not enabled:
        return raw, asbuilt, record
    if overlay is None or "site_reports" not in overlay:
        raise ValueError("enabled FE reset overlay needs parsed compose_overlay.json + site_reports")
    substitutions = asbuilt.setdefault("substitute_inst", [])
    for sub in overlay["asbuilt_substitute_inst_append"]:
        same = [x for x in substitutions if x["inst"] == sub["inst"]]
        if same and any(x["module"] != sub["module"] for x in same):
            raise ValueError("FE reset substitution conflicts with existing as-built variant")
        if not same:
            substitutions.append(deepcopy(sub))
    for name, sites in overlay["site_reports"].items():
        if name not in raw["partition_types"]:
            raise ValueError("FE reset candidate type absent: " + name)
        t = raw["partition_types"][name]
        reset = t.setdefault("reset", {})
        stages = reset.setdefault("physical_stages", [])
        by_selector = {x["selector"]: deepcopy(x) for x in stages}
        for selector, x, y in sites["anchors"]:
            if not (0 <= x <= t["outline_um"][0] and 0 <= y <= t["outline_um"][1]):
                raise ValueError("FE reset site outside type " + name)
            by_selector[selector] = dict(selector=selector, xy_um=[x, y])
        reset["physical_stages"] = list(by_selector.values())
        modules = reset.setdefault("keep_modules", [])
        for module in sites["synth_keep_modules_append"]:
            if module not in modules:
                modules.append(module)
        sinks = t.setdefault("clock", {}).setdefault("sink_sites_um", [])
        for row in sites["clock_sink_sites_um_append"]:
            if row not in sinks:
                sinks.append(deepcopy(row))
        record["changed_types"].append(name)
    record["holds"] = sorted(overlay.get("hold", {}))
    record["unchanged"] = deepcopy(overlay.get("unchanged", {}))
    return raw, asbuilt, record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--conn', required=True); p.add_argument('--type', required=True)
    p.add_argument('--out', required=True); p.add_argument('--png', action='store_true')
    a = p.parse_args(); out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    report, rows = candidate(a.conn, a.type)
    Path(str(out)+'.json').write_text(json.dumps(report, indent=2)+'\n')
    Path(str(out)+'.place.tcl').write_text(tcl(report))
    Path(str(out)+'.release.tcl').write_text(tcl(report, True))
    if a.png: plot(report, rows, str(out)+'.png')
    print(a.type, {k:round(v['max_hop_um'],3) for k,v in report['groups'].items()})


if __name__ == '__main__': main()
