#!/usr/bin/env python3
"""Current-main vs historical comparison for the S81 PQ full-shape design (Claude, 2026-10-07).

Reads reproduce/design.json (historical, d95b57661 inputs) and current_main/design.json (current-main inputs) and writes
current_main/comparison_current_main.json: every leaf of the base design that changed, and every current-basis
refinement with its historical value and the reason.  Fails if a base-design number changed without a listed reason.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'results/uarch/dsrom_s81_pq_fullshape_design_20261007'
PROVENANCE = {'.sources.geometry_extract_sha256', '.sources.snapshot', '.sources.snapshot_origin',
              '.sources.spine_rtl_sha256', '.sources.stream_stats_sha256'}


def leaves(x, y, p=''):
    out = []
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            out += leaves(x.get(k), y.get(k), f'{p}.{k}')
    elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
        for i, (u, v) in enumerate(zip(x, y)):
            out += leaves(u, v, f'{p}[{i}]')
    elif x != y:
        out.append(dict(key=p, historical=x, current=y))
    return out


def main():
    h = json.loads((D / 'reproduce/design.json').read_text())
    c = json.loads((D / 'current_main/design.json').read_text())
    base = [r for r in leaves(h, {k: v for k, v in c.items() if k not in ('current_basis', 'model_basis')})]
    unexplained = [r['key'] for r in base if r['key'] not in PROVENANCE]
    assert not unexplained, unexplained
    cb = c['current_basis']
    rw = [r for r in cb['budget_sheets']['rows'] if r['block'].startswith('rwb')]
    rwb_hist = h['per_die_area']['rwb_mm2']
    n = {r['regions']: r for r in c['blocks']['rwb']['per_instance']}
    rwb_cur = sum(r['note']['outline_um'][0] * r['note']['outline_um'][1] * sum(
        1 for z in c['blocks']['rwb']['per_instance'] if z['regions'] == int(r['block'][7:-1])) for r in rw) / 1e6
    ch = [
        dict(item='spine source for the native PQ parent', historical='rtl/v41die/ot_v41_spine_pqc_w17w10.sv (main, 1b1ca919)',
             current='d0178820d v13b (ecac11e1), pinned under current_main/inputs/rtl',
             reason='Codex native_elaboration.json (committed on main) elaborates the production partition from the '
                    'v13b sources; main\'s rtl file is the older pqc. Broadcast width (1,633), field order and buffer '
                    'storage (298,752 b) are identical, so lanes, pins and SRAM maps do not change'),
        dict(item='spine parameters', historical=cb['historical_spine_params'], current=cb['spine_params'],
             reason='v13b: RG 16 -> 8 replica groups, RPT 2 repeater stages on broadcast / root inputs / row writes'),
        dict(item='added cycles per phase (vs the native production parent)', historical=h['cost']['added_cycles_per_phase'],
             current=cb['cycles']['added_cycles_per_phase'],
             reason='root contract (tools/s81_root_contract.py): pipelined CAM +1 cycle per root pass, <= 4 passes on a '
                    'row chain (was 3), + 2 in/out stations of the 142.56 um return strip (new); the v13b parent already '
                    'pays RPT=2 on its root inputs, which the split replaces (row-count path to the core stays 13 '
                    'stations)'),
        dict(item='AR loss estimate', historical=h['cost']['AR_loss_fraction_est'], current=cb['cycles']['AR_loss_fraction_est'],
             reason='same historical per-cycle sensitivity x the new per-phase delta; ' + cb['cycles']['price_status']),
        dict(item='VM write FIFO depth per region', historical=h['credits']['vm_write']['depth_per_region'],
             current={k: cb[k]['vm_write']['fifo_depth'] for k in ('half', 'full')},
             reason='max rows per region per phase from native mappings (half %d, full %d): FIFO >= burst, so the '
                    'historical 0.75/cycle sustain-rate requirement is retired' % (
                        cb['half']['vm_write']['max_rows_region_phase'], cb['full']['vm_write']['max_rows_region_phase'])),
        dict(item='serial lane W3 (option D) cost', historical='unknown (input requested)',
             current={k: cb[k]['serial_lane_W3'] for k in ('half', 'full')},
             reason='measured from native_stream on both mappings: HALF has <= 2 back-to-back BF beats and every delay '
                    'is absorbed inside the phase (0 extra end cycles, beats shift <= 2 cycles); FULL has runs of 6 and '
                    'costs 1,280 cycles over 139 BF phases (<= 32 a phase)'),
        dict(item='RWB outline / area', historical=dict(area_mm2_total=rwb_hist, shape='square (area-limited estimate)'),
             current=dict(area_mm2_total=round(rwb_cur, 3), outlines=[r['note']['outline_um'] for r in rw]),
             reason='budget sheet: 722 / 794 return pins on one face at the r8 station pin density make the RWB '
                    'pin-limited (cell utilisation ~15 %)'),
        dict(item='RWB replica copies', historical='1 per RWB (RG 16 >= 11 regions)', current=sorted({r['replica_copies'] for r in cb['rwb_replica_groups']}),
             reason='RG 8 < 10/11 regions per RWB: two kept internal replica copies; pins unchanged (one cfg input word)'),
        dict(item='clock insertion targets', historical=None, current={r['block']: r['insertion_target'] for r in cb['budget_sheets']['rows']},
             reason='new: per-block targets from the measured insertion of the nearest measured analogue block'),
        dict(item='die geometry (frames, slots, corridors, hub, end blocks, stations)', historical='geometry_extract.json',
             current='current_main/geometry_extract.json',
             reason='generator drift is 5aba116fc only (an exact-rectangle pin kind for the HBM VM8 retile); the S81 '
                    'layer die has no such ports and every geometric field is identical (only generator hash / base '
                    'commit differ)'),
        dict(item='root placement', historical='frame empty q position (design recommendation (1))',
             current={k: cb['placement_pq_parent'][k] for k in ('root_rows', 'root_row_h_um', 'root_strip_w_um',
                      'roots_per_die_mm2', 'root_cell_outline_um2', 'frame_spare_um', 'status')},
             reason='pq_parent packing: mixed 1,792 frames are 9 fully occupied rows (4 BF full-width + 10 q half-width): '
                    'no empty positions; roots move to a 164.16 um row in the first 6 tier channels; 1,792 pairs kept'),
        dict(item='PQ core slot', historical=dict(slot='VM north 1015 x 795 (WFC child relocation)', est_mm2=h['per_die_area']['pq_core_mm2']),
             current=dict(slot='449.28 x 1,728 um after the VM', slot_mm2=cb['placement_pq_parent']['core_slot_mm2'],
                          fits=cb['placement_pq_parent']['core_fits']),
             reason='pq_parent explicit core slot; capture-up / SU restack keeps the 25.61188 mm2 SU'),
        dict(item='root storage per root', historical='16,768 native + 256 parity',
             current='16,768 native + 256 parity + 128 bv shadow + 3 pipe/station parity = 17,155',
             reason='root contract parity definition (bv protected by a kept shadow, not parity)'),
        dict(item='stages / layer dies / pins / lane widths / SRAM / roots', historical='unchanged', current='unchanged',
             reason='mappings reproduced byte-identically from 9a31097cd (half 8dfa6dae, full bf7863a4); inventories '
                    'and pq_parent_binding committed on main with the snapshot hashes'),
    ]
    out = dict(schema='opentallas.s81.pq-fullshape.comparison-current-main.v1', model_basis=c['model_basis'],
               historical_design_sha256=hashlib.sha256((D / 'reproduce/design.json').read_bytes()).hexdigest(),
               current_design_sha256=hashlib.sha256((D / 'current_main/design.json').read_bytes()).hexdigest(),
               base_design_leaf_changes=base, unexplained=unexplained, changes=ch,
               verdict_note='historical verdict (README sections 1-4, design.json) unchanged; current-basis refinement: '
                            'option D (serial 568-b lane) costs 0 phase cycles on HALF and becomes the preferred lane '
                            'for HALF BF dies (+0.4 vs +9.8 mm2) subject to its exactness gate; FULL keeps C')
    (D / 'current_main/comparison_current_main.json').write_text(json.dumps(out, indent=1, default=str) + '\n')
    for r in ch:
        print('-', r['item'], ':', str(r['historical'])[:60], '->', str(r['current'])[:90])


if __name__ == '__main__':
    main()
