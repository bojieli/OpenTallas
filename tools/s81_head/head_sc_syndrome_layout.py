#!/usr/bin/env python3
"""Prepare an opt-in SC syndrome placement fallback; never modify RTL or plans.

Run against a private SC kit's face_flops.tcl. The output is a candidate only:
existing GRT must be read, and PLACE/clock/hold review precedes any release.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

PREFIX = 'u_phy.u_link.u_dec.u_syn.'
COUNTS = {'sc_q': 550, 'sp0': 300, 'sp1': 300, 'S_q': 300}
ANCHOR = 'set hf1_n 0; set hf1_miss {}'
MARKER = '# CODEX_SC_SYNDROME_BEGIN'


def sites(style: str) -> dict[str, tuple[float, float]]:
    if style != 'core-two-bank':
        raise ValueError('old northward variants cross VDDPHY y>=150; use core-two-bank')
    out = {}
    for family, count in COUNTS.items():
        for bit in range(count):
            if family == 'S_q':
                x, y = 1269 + (bit % 7) * 6.48, 8.64 + (bit // 7) * 1.08
            else:
                col, row = bit % 16, bit // 16
                x = (1435.32 if col < 8 else 1504.44) + (col % 8) * 6.48
                origin = {'sp1': 8.64, 'sc_q': 69.12, 'sp0': 70.20}[family]
                y = origin + row * 2.16
            out[f'{PREFIX}{family}[{bit}]'] = (round(x, 6), round(y, 6))
    if max(y for x,y in out.values()) + 1.08 >= 150:
        raise ValueError('core standard cells must remain below VDDPHY domain y=150')
    return out


def rewrite(source: str, style: str) -> tuple[str, dict]:
    if MARKER in source or source.count(ANCHOR) != 1:
        raise ValueError('expected one fresh HF1 placement loop')
    existing = re.findall(r'\{u_phy\.u_link\.u_dec\.u_syn\.(sc_q|sp0|sp1|S_q)\[(\d+)\]\}\s+\{[\d.]+\s+[\d.]+\}', source)
    have = {f: set() for f in COUNTS}
    for family, bit in existing:
        have[family].add(int(bit))
    for family in ('sc_q', 'sp1', 'S_q'):
        if have[family] != set(range(COUNTS[family])):
            raise ValueError(f'incomplete {family} placement table')
    # sp0 exists in the measured gate netlist but was left to GPL. Explicit
    # interleaved sites reserve room for it instead of packing it at the west edge.
    target = sites(style)
    lines = [MARKER + ' style=' + style,
             '# Placement only: PIN CYCLES 0; macro/clock/child adoption HOLD stays.',
             '# Source proof and timing are separate; no RTL or SDC change.']
    for name, (x, y) in target.items():
        lines.append(f'dict set hf1_sites {{{name}}} {{{x:.6f} {y:.6f}}}')
    if style == 'core-two-bank':
        # Keep combinational logic out too; an FF-only gap is not a channel.
        lines += [
            'set cs_blk [ord::get_db_block]; set cs_u [[ord::get_db_tech] getDbUnitsPerMicron]',
            'set cs_box {1482.84 65.34 1504.44 146.88}',
            'set cs_v [lmap z $cs_box {expr {int(round($z*$cs_u))}}]',
            'lassign $cs_v cs_x0 cs_y0 cs_x1 cs_y1; set cs_have 0',
            'foreach cs_b [$cs_blk getBlockages] { set cs_r [$cs_b getBBox]; if {[list [$cs_r xMin] [$cs_r yMin] [$cs_r xMax] [$cs_r yMax]] eq $cs_v} {set cs_have 1} }',
            'if {!$cs_have} {odb::dbBlockage_create $cs_blk $cs_x0 $cs_y0 $cs_x1 $cs_y1}',
            'if {![llength [info commands ff_reserve_explicit]]} {error "SC_SYNDROME: station-grid reservation helper required"}',
            'ff_reserve_explicit $cs_x0 $cs_y0 [expr {$cs_x1-$cs_x0}] [expr {$cs_y1-$cs_y0}]',
            'set cs_die [$cs_blk getDieArea]; set cs_phy_y [expr {round(150*$cs_u)}]',
            'ff_reserve_explicit [$cs_die xMin] $cs_phy_y [expr {[$cs_die xMax]-[$cs_die xMin]}] [expr {[$cs_die yMax]-$cs_phy_y}]',
            'puts "OT_SC_SYNDROME_CORRIDOR hard placement and station-grid reservation $cs_box; VDDPHY y>=150 excluded"',
        ]
    lines.append('# CODEX_SC_SYNDROME_END')
    output = source.replace(ANCHOR, '\n'.join(lines) + '\n' + ANCHOR, 1)
    if style == 'core-two-bank':
        guard_anchor = 'puts "OT_HF1_SITES placed $hf1_n flops FIRM"'
        if output.count(guard_anchor) != 1:
            raise ValueError('missing unique post-site guard anchor')
        guard = r'''
# Reject a fixed face/landing site in the reserved channel before GPL.
foreach cs_i [$cs_blk getInsts] {
 if {[$cs_i getPlacementStatus] ni {FIRM LOCKED} || [[$cs_i getMaster] isBlock]} continue
 # Supply tap/filler cells already exist in the retained floorplan; the
 # signal-routing corridor excludes functional fixed cells, not PG cells.
 if {[regexp {^(TAPCELL|FILLER|DECAP)} [[$cs_i getMaster] getName]]} continue
 set cs_r [$cs_i getBBox]
 set cs_nm [string map {\\ {}} [$cs_i getName]]
 if {[string match "u_phy.u_link.u_dec.u_syn.*" $cs_nm] && [regexp {\.(sc_q|sp0|sp1|S_q)\[} $cs_nm] && [$cs_r yMax]>$cs_phy_y} {
  error "SC_SYNDROME_POWER: selected register crosses VDDPHY boundary: [$cs_i getName]"
 }
 if {[$cs_r xMin]<$cs_x1 && [$cs_r xMax]>$cs_x0 && [$cs_r yMin]<$cs_y1 && [$cs_r yMax]>$cs_y0} {
  error "SC_SYNDROME_CORRIDOR: fixed cell in reserved channel: [$cs_i getName]"
 }
}
'''
        output = output.replace(guard_anchor, guard_anchor + guard, 1)
    bounds = {}
    for family in COUNTS:
        p = [p for n, p in target.items() if n.startswith(PREFIX + family + '[')]
        bounds[family] = [min(x for x,y in p), min(y for x,y in p), max(x for x,y in p), max(y for x,y in p)]
    receipt = {
        'schema': 'opentallas.head.sc_syndrome_candidate.v1',
        'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'style': style, 'counts': COUNTS, 'sites': len(target),
        'bounds_um': bounds, 'pin_cycles': 0, 'rtl_changed': False,
        'sdc_changed': False, 'macros_changed': False,
        'die_outline_um': [2885.76, 1226.88],
        'core_vdd_y_limit_um': 150.0,
        'phy_power_domain_avoided': True,
        'measured_rows_y_um': [4.32, 1222.56],
        'macro_gap_x_um': [1430.676, 1560.006],
        'central_corridor_um': 21.60 if style == 'core-two-bank' else None,
        'reserved_placement_blockage_um': [1482.84, 65.34, 1504.44, 146.88] if style == 'core-two-bank' else None,
        'held': ['READ_CURRENT_GRT', 'PLACE_REVIEW', 'CLOCK_HOLD', 'CHILD_ADOPTION', 'DO_NOT_COUNT', 'HOLD_ROUTE'],
        'note': 'Candidate geometry only. All 300 S_q bits broadcast to all three western BM children; their existing long consumer reach is not qualified by this change.'}
    return output, receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--face-flops', type=Path, required=True)
    ap.add_argument('--style', choices=('core-two-bank',), required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--receipt', type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists() or a.receipt.exists():
        ap.error('candidate output/receipt already exists; keep previous evidence')
    text, rec = rewrite(a.face_flops.read_text(), a.style)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.receipt.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(text)
    a.receipt.write_text(json.dumps(rec, indent=2) + '\n')
    print(f'SC_CANDIDATE {a.style} sites={rec["sites"]} PIN_CYCLES=0 HELD')

if __name__ == '__main__':
    main()
