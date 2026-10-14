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

RELAY = re.compile(r'^q[fk]d_rly|^qfd_rst_rep')    # die_top_logic: data relays and reset-tree repeaters (v4 T11)
HARD_IP = ('ot_hbm3e_phy', 'qfd_io_serdes', 'qfd_io_ucie', 'qkd_pll', 'qfd_clkrx', 'ot_qfd_serdes_112g_x12_phy')
CLUSTER = ('qfd_tile_nk', 'qfd_tile_h3c', 'qfd_tile_h3s')
CLUSTER_SLOT = (311.04, 1296.0)
# slot requests logged to the die lead (el1011-qwen-tp8.log), recorded on the v3 slots
SLOT_REQ = {
    'qfd_sp_vector_memory': dict(
        target_insertion_ps=240.0,
        note='VM = ot_qfd_vm_grp CLUSTER (8 vm_grp tiles + MEE): clock entry budgeted at the cluster insertion ~240 ps '
             '(coordinator); q-sp 11:19: closed bank_t/su_t routed insertion 319/371 ps mean -> cluster may export '
             '~450-500 ps TT, re-budget on the qfd_vm_grp_c gated number',
        # coordinator 15:00: qfd_vm_grp_c (r6c-da28dc03e) outline 1149.12 um square (8 bank_t + 6 su_t children; old
        # 993.6 x 648 could not hold them); first clock-spine pass 2,093 ps arrival spread across children.  8 groups
        # per VM -> 4 x 2 = 4596.48 x 2298.24 before the MEE: the 2332.776 x 2073.576 VM slot cannot hold it (10.56 mm2
        # of groups vs 4.84 mm2) -> the VM leaves the spine stack (W field or a split VM), die floorplan regen.
        outline_req=(4596.48, 2298.24, 'coordinator 15:00: vm_grp cluster 1149.12 sq x 8 (4 x 2, excl. MEE); '
                                       'insertion 240 ps budget vs 2,093 ps first-pass child spread -> re-check')),
    # coordinator 15:30: the KV hub cluster qkd_ahub_ref (job qkd_ahub_ref-q8-fcb9fa5a5) grew to 889.92 x 760.32 (+61%;
    # failed at util 0.90 in 648 x 648).  KV-centre sub-column fit (it25 plan): column x 17589.3-18366.9 is free W of
    # 17589 at that height and N of pll 15163 -> keep the E edge at 18366.9 (E corridor to tile col 18487 untouched),
    # grow W by 112.3 (x0 17477.0) and push seq/embgw/pll N by 112.3 (pll top 15275.5); re-run the KVc fine cuts.
    'qkd_ahub': dict(outline_req=(889.92, 760.32, 'coordinator 15:30: qkd_ahub_ref 124.8k hub + 274.3k children; '
                                                  'E edge fixed at 18366.9, W +112.3, seq/embgw/pll N +112.3')),
    'qfd_io_collective': dict(outline_req=(1166.4, 950.4, 'qwen-tp8/coll 07:11: W up/dp y 43-475, ur/dr y 475-907; S in_* '
                                                         'x 43-302; N out_*/fault* x 43-302, clk/rst_n x 562-605')),
    # Owner 19:00 narrowed M5: crom_g/cbuf_g growth requests are withdrawn.
    # Keep accepted closed outlines; pin density alone gets an M6 pin-only grant.
    'qfd_tile_nk': dict(note='q-tile 10:03 face pins: W n_a 356-456 n_b 457-557 t_out 557-657 n_y 658-758 li 758-946; E ib '
                             '400-520 ib_go 520-524 xl 524-580 tile_id 580-600 fault 600-604 rst_n 640-644 clk 660-664 lo '
                             '758-946 (M4)'),
}
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
    ap.add_argument('--version', type=int, default=1)
    ap.add_argument('--recipe', default='tp8a')
    ap.add_argument('--tile-cap', default=None, help='v3: tile layer cap (M5): slot signals + PG <= cap, strap cap+1; '
                    'the die top owns cap+1 .. M9 (M6 / M7 over tiles, M8 / M9 die-only); hard IP keeps its layers')
    ap.add_argument('--prev', default=None, help='the previous version of this contract (its changelog is kept)')
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
        s['version'] = a.version
        s['parent'] = die
        if a.tile_cap and cell in CLUSTER:
            # coordinator DECISION 2026-10-12 12:15 (q-tile request A/B 10:03): qfd_tile_nk / h3c / h3s is a CLUSTER
            # slot (hard ROM/SRAM/leaf children): slot 311.04 x 1296 (content >= 288.36), layers M2-M7 with PG M7,
            # pins M4 only on the W/E faces; the die routes over it on M8+ only (cuts.py CLUSTER)
            s['outline'] = dict(w=CLUSTER_SLOT[0], h=CLUSTER_SLOT[1] if a.version < 5 else 1317.6)
            s.update(signal_max_layer='M7', pg_layer='M7', strap_layer='M8', pin_layers=['M4'])
            s['layer_cap'] = dict(cap='M7', kind='cluster', die_over='M8+', pin_layers=['M4'],
                                  layer_cap_grant='qwen-tp8 die lead: ROM/SRAM-band cluster, macros block M1-M4; pins '
                                                  'M4 only (coordinator DECISION 2026-10-12 12:15)')
            for pn in s.get('pins', []):
                pn['layer'] = 'M4'
            if s.get('clock_entry', {}).get('layer'):
                s['clock_entry'] = dict(s['clock_entry'], layer='M4')
        elif a.tile_cap and cell not in HARD_IP:
            # M5 defaults apply to new/redesigned leaves, not every existing view.
            sig_layers = [sh[0] for p_ in lef[cell]['pins'].values()
                          if p_['use'] not in ('POWER', 'GROUND')
                          for sh in p_['shapes'] if sh[0]]
            pg_layers = [sh[0] for p_ in lef[cell]['pins'].values()
                         if p_['use'] in ('POWER', 'GROUND')
                         for sh in p_['shapes'] if sh[0]]
            sig_top = max(sig_layers, key=MG.LN) if sig_layers else s['signal_max_layer']
            pg_top = max(pg_layers, key=MG.LN) if pg_layers else s['pg_layer']
            # Prefer inherited measured-view metadata over placeholder case pin layers.
            view = s.get('view_layers', {})
            sig_top = view.get('signal_max_layer', sig_top)
            pg_top = view.get('pg_layer', pg_top)
            hi = max((sig_top, pg_top, s.get('view_cap', sig_top)), key=MG.LN)
            s.update(signal_max_layer=sig_top, pg_layer=pg_top,
                     strap_layer=f'M{MG.LN(pg_top) + 1}')
            s['layer_cap'] = dict(cap=hi, view_max_layer=hi, conforms=True,
                                  default_new_cap=a.tile_cap,
                                  validation='layer metadata only; routed OBS and pin access require child_lint',
                                  reroute_policy='horizontal fine cut >0.60 or real overflow over this tile',
                                  layer_cap_grant='qwen-tp8 die lead: owner 2026-10-12 19:00 preserves existing '
                                                  'closed views; case-view layers retained, closure evidence '
                                                  'and child_lint still required for adoption')
            s.pop('pin_replan', None)
            s['view_status'] = 'Existing view retained under owner 19:00 policy; requires original closure evidence and child_lint'
        for k, v in SLOT_REQ.get(cell, {}).items():
            if k == 'outline_req':
                if abs(s['outline']['w'] - v[0]) > 0.05 or abs(s['outline']['h'] - v[1]) > 0.05:
                    msg = (f'slot request: outline {v[0]} x {v[1]} ({v[2]}); case LEF has {s["outline"]["w"]} x '
                           f'{s["outline"]["h"]} -> die floorplan regen')
                    if msg not in open_items.get(cell, []):
                        open_items.setdefault(cell, []).append(msg)
            elif k == 'note':
                s['notes'] = s.get('notes', '') + ' | ' + v
            else:
                s[k] = v
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
    if a.tile_cap:
        slots[0].update(signal_max_layer='M9', notes=f'TP8 track-B single die (F2, ROM + merged KV halves, host SerDes '
                        f'slot on every die), contract v{a.version}: new leaves default to {a.tile_cap}; existing views retain real layers; die routes '
                        f'M{MG.LN(a.tile_cap) + 1}-M9 (M{MG.LN(a.tile_cap) + 1}/M{MG.LN(a.tile_cap) + 2} over tiles, '
                        f'M8/M9 die-only); relays (die_top_logic) are its only logic')
        slots[0]['version'] = a.version
    prevlog = json.load(open(a.prev)).get('changelog', []) if a.prev else []
    out = {'schema': 'opentallas.hier_contract.v1', 'die': die, 'version': a.version, 'updated': a.when,
           'owner': 'qwen-tp8/die (el1011-qwen-tp8-die)', 'clock_period_ps': C['clock_period_ps'],
           'layer_defaults': C['layer_defaults'],
           'changelog': prevlog + [dict(version=a.version, when=a.when, change=f'TP8 ROM die from the {a.recipe} generator case (' +
                              a.source + '): qwen_rom v5 slot templates for unchanged cells, LEF re-derived for '
                              + ', '.join(sorted(rederived)) + '; v5 deltas D1-D6 inherited; TP8 deltas T1-T6' +
                              (f'; new leaf default {a.tile_cap}; existing view layers preserved (owner 19:00 narrowed reroute policy)' if a.tile_cap else ''))],
           'slots': slots, 'source': a.source, 'derived_from': dict(contract=a.v5, version=C['version']),
           'fixed': C.get('fixed'), 'deltas': deltas + TP8_DELTAS,
           'seam_check': C.get('seam_check'), 'die_closure': C.get('die_closure'),
           'die_top_logic': dict(relays=dict(sorted(relays.items())), total=sum(relays.values())),
           'floorplan': dict(die_um=[dw, dh], die_mm2=round(die_mm2, 3), slot_mm2=round(slot_mm2, 3),
                             slot_share=round(slot_mm2 / die_mm2, 4), channel_share=round(1 - slot_mm2 / die_mm2, 4),
                             slots_by_cell_mm2={k: round(v, 3) for k, v in sorted(area.items())},
                             rederived_cells=rederived),
           'open_items': {k: sorted(v) for k, v in sorted(open_items.items())}}
    if a.version >= 4:
        # v4 slot change answers (stations / heads _d/_r, cdc_wleaf, rhead cluster, VM region): one idempotent pass
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import contract_v4_tp8 as V4
        rg = ROOT / 'results/arch/hier_contract_1012/qwen_rom_tp8_v4_regen.json'
        out = V4.apply(out, a.when, json.load(open(rg)) if rg.exists() else {}, source_note=a.source,
                       skip=('qkd_rhead', 'qfd_sp_vector_memory') if a.version >= 5 else ())
        if a.version >= 5:
            # v5 (die lead r8): the generator follows v4 / v4b; the contract is the case + the v4b / v5 records
            import contract_v4b_tp8 as V4B
            import contract_v5_tp8 as V5
            out = V4B.apply(out)
            out = V5.apply(out, json.load(open(a.prev)) if a.prev else None, a.when, source_note=a.source)
        out['version'] = a.version
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(dict(slots=len(slots), relays=sum(relays.values()), kept=len(kept), rederived=sorted(rederived),
                          slot_share=out['floorplan']['slot_share'], die_um=[dw, dh])))


if __name__ == '__main__':
    main()
