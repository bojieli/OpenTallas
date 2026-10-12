#!/usr/bin/env python3
"""qwen-tp8 2026-10-12: the TP8 track-A ROM die contract (opentallas.hier_contract.v1, die qwen_rom_tp8) from the TP4 v5
contract and the tp8a generator case (tools/qwen_rom_fulldie_b3r2.py <mode> --recipe tp8a --work CASE).

Per slot: every hard instance of CASE/die.v (relays are die_top_logic, not slots), origin from CASE/place.tcl.  A cell
whose CASE/elements.lef outline and pin-bus set equal its v5 slot keeps the v5 slot template (pins with the v5 deltas
D1/D2/D5/D6 already applied, layers, clock entry, budgets, evidence notes); a cell the TP8 recipe changed (outline or
ports: the two-level collective, the 3-SerDes CDC cluster, the 3-band tree top / VM / slabs) is re-derived from the
case LEF with the v4 migrator's face / bus-range rules (tools/qwen_kv_die/hier_contract_migrate.py).

    derive_tp8.py --v5 results/arch/hier_contract_1011/qwen_rom.json --case CASE --out qwen_rom_tp8.json
"""
import argparse, collections, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
from hier_contract_export import parse_lef  # noqa: E402
import hier_contract_migrate as MG  # noqa: E402

RELAY = re.compile(r'^qfd_rly')
TP8_DELTAS = [
    dict(id='T1', slots=['qfd_tile_nk', 'qfd_cst_n', 'qfd_cst_s'], status='decided v1',
         change='tile count 1,536 -> 768 (G 6,144 -> 3,072 lane groups; 64 columns x 12 rows); same qfd_tile_nk master, '
                'outline and pins (SPEC section 1: 20,032 words/die, CODE_BANKS 5); one qfd_cst per tile (768); the tile '
                'RTL re-synthesises at GT 3,072 (tree select widths) with outline / pins held'),
    dict(id='T2', slots=['qfd_port_tiles_0', 'qfd_port_tiles_1', 'qfd_port_tiles_2', 'qfd_sp_band_lanes',
                         'qfd_sp_res_ser'], status='decided v1',
         change='bands 6 -> 3 (3 x 4 tile rows); 48 port groups (16 per band); port slabs 0-2 (+ _f1), band_lanes x3, '
                'res_ser x3; ROW_GAP 518.4 um routing channel between tile rows, link channels before rows 2 and 10 '
                '(die 25.06 x 23.00 mm)'),
    dict(id='T3', slots=['qfd_tt_up4', 'qfd_tt_up4_g', 'qfd_tt_ctlm', 'qfd_sp_vector_memory'], status='decided v1',
         change='tree top adds 3 band words (pw0-2 / lf0-2; NB 3, parameter change of ot_qfd_band_upper); the VM '
                'result ports rb/rc/rk 0-2'),
    dict(id='T4', slots=['qfd_io_collective'], status='decided v1 (budget outline)',
         change='two-level 8-way all-reduce (in-package UCIe pre-fold + owner-half select / all-gather around the '
                '4-rank fold at half width): budget outline 1.5x TP4 area (3,453.6 x 1,563.8 um); SerDes words s/s1/s2 '
                '+ sr/sr1/sr2'),
    dict(id='T5', slots=['qfd_io_serdes', 'qfd_io_xfifo'], status='decided v1',
         change='3 x qfd_io_serdes (one x12 112G link per remote package, K4 board; TP4 1 adapter for 2 destinations): '
                'io_serdes (E of UCIe) + io_serdes_1/_2 (W of the collective, MY); IO-band CDC cluster 700.1 um wide '
                'with i_/o_serdes_tx<k> / rx<k> groups'),
    dict(id='T6', slots=['qfd_tile_nk'], status='decided v1',
         change='reduction-tree balance: every tree node\'s n_a / n_b legs arrive on the same cycle as placed -- the '
                'generator adds tree_pads relays (results/arch/hier_contract_1012/qwen_rom_tp8_tree_pads.json, the '
                'qwen_die_seam array model) at the sink end of the early leg; array bench passes with 0 deskew'),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--v5', required=True)
    ap.add_argument('--case', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--source', default='')
    ap.add_argument('--when', default='2026-10-12')
    a = ap.parse_args()
    C = json.load(open(a.v5))
    case = Path(a.case)
    lef = {}
    for f in sorted(case.glob('*.lef')):
        parse_lef(f, lef)
    master = {}
    for line in open(case / 'die.v'):
        m = re.match(r'\s*(\w+)\s+(\\?\S+)\s*\(', line)
        if m and m.group(1) in lef:
            master[m.group(2).lstrip('\\')] = m.group(1)
    pos = {}
    for line in open(case / 'place.tcl'):
        m = re.search(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', line)
        if m:
            pos[m.group(1)] = (float(m.group(2)), float(m.group(3)), m.group(4))
    dw = dh = None
    for line in open(case / 'run.tcl'):
        m = re.search(r'-die_area \{0 0 ([\d.]+) ([\d.]+)\}', line)
        if m:
            dw, dh = float(m.group(1)), float(m.group(2))
            break
    tmpl = {}
    for s in C['slots']:
        if s['kind'] != 'die':
            tmpl.setdefault(s['cell'], s)

    def lef_buses(cell):
        M = lef[cell]
        out = set()
        for pn, p in M['pins'].items():
            if p['use'] in ('POWER', 'GROUND') or not p['shapes']:
                continue
            out.add(re.sub(r'\[\d+\]$', '', pn))
        return out

    def tmpl_buses(s):
        return {re.sub(r'\[.*\]$', '', p['name']) for p in s.get('pins', [])} | {s['clock_entry']['pin']}

    def derived(cell, t):
        """the v4 migrator rules on the case LEF (faces, bus ranges; D2 tree words on tile_nk; layers kept)"""
        M = lef[cell]
        w, h = M['w'], M['h']
        ents, pg, sig, opn = [], set(), set(), []
        for pn, p in M['pins'].items():
            if not p['shapes']:
                continue
            if p['use'] in ('POWER', 'GROUND'):
                pg |= {s_[0] for s_ in p['shapes'] if s_[0]}
                continue
            m = re.match(r'^(.*)\[(\d+)\]$', pn)
            base, idx = (m.group(1), int(m.group(2))) if m else (pn, None)
            if base in ('ck', 'clk', 'clk_i'):
                continue
            l, *r = p['shapes'][0]
            f, off, area = MG.face(w, h, r)
            if area or MG.LN(l) > 7:
                opn.append(f'{base}: {l} {"area" if area else "face"} pin -> {f} face (D4 review)')
            sig.add(l)
            ents.append((base, idx, f, l, off))
        pgl = max(pg, key=MG.LN) if pg else (t['pg_layer'] if t else 'M7')
        ck = dict(t['clock_entry']) if t else dict(pin='clk' if 'clk' in M['pins'] else 'ck', face='N', layer='M6',
                                                   offset=round(w / 2, 3))
        return MG.bus_ranges(ents), pgl, (max(sig, key=MG.LN) if sig else 'M6'), ck, sorted(set(opn))

    die = 'qwen_rom_tp8'
    slots = [dict(name=die, cell=die, kind='die', parent=None, outline=dict(w=dw, h=dh),
                  origin=dict(x=0.0, y=0.0, orient='R0'), io_budget=dict(in_delay_frac=0.2, out_delay_frac=0.2),
                  clock_entry=dict(pin='ref', face='S', layer='M9'), pg_layer='M9', strap_layer='M9',
                  signal_max_layer='M9', version=1,
                  notes='TP8 track-A ROM die (results/arch/qwen_tp8_1012/SPEC.md section 5): die top M8/M9 only; relays '
                        '(die_top_logic) are its only logic; paired 1:1 with the unchanged qwen_kv die on the S edge')]
    relays, kept, rederived, open_items = collections.Counter(), set(), {}, {}
    for inst in sorted(master, key=lambda n: (master[n], n)):
        cell = master[inst]
        if RELAY.search(cell):
            relays[cell] += 1
            continue
        M = lef[cell]
        t = tmpl.get(cell)
        same = t is not None and abs(t['outline']['w'] - M['w']) < 0.01 and abs(t['outline']['h'] - M['h']) < 0.01 \
            and lef_buses(cell) - {'ck', 'clk', 'clk_i'} == tmpl_buses(t) - {'ck', 'clk', 'clk_i'}
        x, y, o = pos[inst]
        if same:
            s = {k: v for k, v in t.items() if k not in ('name', 'origin', 'version')}
            kept.add(cell)
        else:
            pins, pgl, sigmax, ck, opn = derived(cell, t)
            s = dict(cell=cell, kind='element', parent=die, outline=dict(w=M['w'], h=M['h']), pins=pins,
                     io_budget=dict(in_delay_frac=0.2, out_delay_frac=0.2, registered_in=True, registered_out=True),
                     clock_entry=ck, pg_layer=pgl, strap_layer=f'M{min(MG.LN(pgl) + 1, 9)}',
                     signal_max_layer=t['signal_max_layer'] if t else sigmax)
            for k in ('target_insertion_ps',):
                if t and k in t:
                    s[k] = t[k]
            why = 'new cell' if t is None else 'outline / ports changed by the tp8a recipe'
            s['notes'] = f'TP8 re-derived from the tp8a case LEF ({why}); budget placeholder until re-closed' + \
                (' | v5: ' + t['notes'] if t and t.get('notes') else '')
            rederived[cell] = why
            if opn:
                open_items[cell] = opn
        s = dict(name=inst, **{k: v for k, v in s.items() if k != 'parent'}, parent=die)
        s['origin'] = dict(x=x, y=y, orient=o if o in ('R0', 'MX', 'MY', 'R180') else 'R0')
        s['version'] = 1
        s['parent'] = die
        slots.append(s)
    cells = {s['cell'] for s in slots}
    for c, v in C.get('open_items', {}).items():
        if c in kept:
            open_items[c] = v
    deltas = []
    for d in C['deltas']:
        d = dict(d)
        if isinstance(d['slots'], list):
            d['slots'] = [c for c in d['slots'] if c in cells]
        d['status'] = d['status'] + ' (inherited from qwen_rom v5)'
        deltas.append(d)
    area = collections.Counter()
    for s in slots[1:]:
        area[s['cell']] += s['outline']['w'] * s['outline']['h'] / 1e6
    slot_mm2 = sum(area.values())
    die_mm2 = dw * dh / 1e6
    out = {'schema': 'opentallas.hier_contract.v1', 'die': die, 'version': 1, 'updated': a.when,
           'owner': 'qwen-tp8/die (el1011-qwen-tp8-die)', 'clock_period_ps': C['clock_period_ps'],
           'layer_defaults': C['layer_defaults'],
           'changelog': [dict(version=1, when=a.when, change='TP8 track-A ROM die from the tp8a generator case (' +
                              a.source + '): qwen_rom v5 slot templates for unchanged cells, LEF re-derived for '
                              + ', '.join(sorted(rederived)) + '; v5 deltas D1-D6 inherited; TP8 deltas T1-T6')],
           'slots': slots, 'source': a.source, 'derived_from': dict(contract=a.v5, version=C['version']),
           'fixed': C.get('fixed'), 'deltas': deltas + TP8_DELTAS,
           'seam_check': C.get('seam_check'), 'die_closure': C.get('die_closure'),
           'die_top_logic': dict(relays=dict(sorted(relays.items())), total=sum(relays.values())),
           'floorplan': dict(die_um=[dw, dh], die_mm2=round(die_mm2, 3), slot_mm2=round(slot_mm2, 3),
                             slot_share=round(slot_mm2 / die_mm2, 4), channel_share=round(1 - slot_mm2 / die_mm2, 4),
                             slots_by_cell_mm2={k: round(v, 3) for k, v in sorted(area.items())},
                             rederived_cells=rederived),
           'open_items': {k: sorted(v) for k, v in sorted(open_items.items())}}
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(dict(slots=len(slots), relays=sum(relays.values()), kept=len(kept), rederived=sorted(rederived),
                          slot_share=out['floorplan']['slot_share'], die_um=[dw, dh])))


if __name__ == '__main__':
    main()
