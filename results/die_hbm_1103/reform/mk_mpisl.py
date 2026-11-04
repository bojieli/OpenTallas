#!/usr/bin/env python3
"""DIE-HBM-61/PLAN d44v part 3 (one-block plan fix after freeze): hcol_h1 mesh-island feed-through pins.

SS24 10:06: the signed ot_hbm_idx_score_hcol_h1 (hcol_h1_w90 routed DB, re-signed ss23/hcol_w90_r_hbm, flow-20261102-r-hbm,
DEF sha256 8ce38d2e9978acd4) carries 1228 pins; the plan table (d35a codex_g21) has 1216.  The 12 extra pins are exactly
the 12.2a1 pushdown island ft ports mp_isl{0,1,2}_{ck,rst}_{i,o} the kit adds from core_infra_plan.json (the d35a
master-plan pushdown form).  This step adds them to the plan table at the signed DEF layer / centre / rect, so the
signed design is the plan design (DESIGN-MATCH), and records each pin's parent connection (d35a form, 12.2a1):
  mp_islK_ck_i  <- die clock tap: M9->M5 clock stack at island K centre (die mesh/tree drop)
  mp_islK_ck_o  -> die mesh/tree feed-through net (independent of the core clock pin clk_pair[0])
  mp_islK_rst_i <- die regional reset stack (M9->M5) at island K centre
  mp_islK_rst_o -> die reset feed-through net (independent of the core reset pin)
  arcs ck_i->ck_o via fixed BUFx8 mp_islK_ck0, rst_i->rst_o via fixed BUFx4 mp_islK_rst0 (no core logic, LEC-exempt).
Writes cores/<table>__mpisl.json, repoints every hcol_h1 pins_file, writes cores/<module>__d44v_mpisl_parent.json +
mpisl_event.json.     python3 mk_mpisl.py PLAN_DIR"""
import hashlib, json, sys
from pathlib import Path

M = 'ot_hbm_idx_score_hcol_h1'
OLD = 'cores/ot_hbm_idx_score_hcol_h1__218.592x187.488__canon__codex_g21.json'
NEW = 'cores/ot_hbm_idx_score_hcol_h1__218.592x187.488__canon__codex_g21__mpisl.json'
SIGNED = dict(resign='/home/ubuntu/scratch-root/claude/ss23/hcol_w90_r_hbm (epyc2, PROVENANCE kind resign, SIGNED)',
              def_='die-hbm-58-cores/hcol_h1_w90/run/results/asap7/hbc_ot_hbm_idx_score_hcol_h1/base/6_final.def',
              def_sha256_16='8ce38d2e9978acd4', ft_ports_sha256_16='194b72723511f722',
              flow_tag='flow-20261102-r-hbm')
# signed DEF PINS rects (nm, M5), name -> (x0, y0, x1, y1)
RECT = {'mp_isl0_ck_i': (106896, 96960, 106944, 97440), 'mp_isl0_ck_o': (109056, 96960, 109104, 97440),
        'mp_isl0_rst_i': (106904, 92784, 106936, 92976), 'mp_isl0_rst_o': (109064, 92784, 109096, 92976),
        'mp_isl1_ck_i': (55056, 96960, 55104, 97440), 'mp_isl1_ck_o': (57216, 96960, 57264, 97440),
        'mp_isl1_rst_i': (55064, 92784, 55096, 92976), 'mp_isl1_rst_o': (57224, 92784, 57256, 92976),
        'mp_isl2_ck_i': (163056, 96960, 163104, 97440), 'mp_isl2_ck_o': (165216, 96960, 165264, 97440),
        'mp_isl2_rst_i': (163064, 92784, 163096, 92976), 'mp_isl2_rst_o': (165224, 92784, 165256, 92976)}
CELL = {'ck': ('BUFx8_ASAP7_75t_R', 95.58), 'rst': ('BUFx4_ASAP7_75t_R', 94.5)}
ISLX = {0: 107.976, 1: 56.16, 2: 164.16}
ROLE = {0: 'clock_entry', 1: 'tree_leaf', 2: 'tree_leaf'}
PARENT = {('ck', 'i'): ('die_clock_tap', 'die M9 clock stack (M9->M5 at the island centre): die mesh/tree tap'),
          ('ck', 'o'): ('die_clock_feed', 'die mesh/tree feed-through net; independent core clock pin'),
          ('rst', 'i'): ('die_reset_tap', 'die regional reset stack (M9->M5 at the island centre)'),
          ('rst', 'o'): ('die_reset_feed', 'die reset feed-through net; independent core reset pin')}
# ft_interface.json (signed kit, TT/FF ps, min/max)
DLY = {(0, 'ck'): (23.16, 26.08, 17.3, 18.43), (0, 'rst'): (25.0, 27.99, 18.49, 19.68),
       (1, 'ck'): (23.39, 26.3, 17.46, 18.59), (1, 'rst'): (25.03, 28.02, 18.51, 19.69),
       (2, 'ck'): (23.44, 26.35, 17.5, 18.62), (2, 'rst'): (25.2, 28.18, 18.64, 19.82)}

r3 = lambda v: round(v, 3)
d = Path(sys.argv[1]); P = json.loads((d / 'die_plan.json').read_text())
rows = json.loads((d / OLD).read_text())
assert len(rows) == 1216 and not any(str(q['name']).startswith('mp_isl') for q in rows), len(rows)
add, par, arcs = [], [], []
for k in range(3):
    for s in ('ck', 'rst'):
        for io in ('i', 'o'):
            n = f'mp_isl{k}_{s}_{io}'; x0, y0, x1, y1 = RECT[n]
            add.append(dict(name=n, layer='M5', x=r3((x0 + x1) / 2000), y=r3((y0 + y1) / 2000),
                            w=r3((x1 - x0) / 1000), h=r3((y1 - y0) / 1000)))
            kind, how = PARENT[(s, io)]
            par.append(dict(name=n, direction='INPUT' if io == 'i' else 'OUTPUT', layer='M5',
                            rect_um=[r3(x0 / 1000), r3(y0 / 1000), r3(x1 / 1000), r3(y1 / 1000)], island=f'isl{k}',
                            island_role=ROLE[k], parent=kind, connect=how))
        dl = DLY[(k, s)]
        arcs.append(dict(source=f'mp_isl{k}_{s}_i', sink=f'mp_isl{k}_{s}_o', kind='clock' if s == 'ck' else 'reset',
                         cells=[f'mp_isl{k}_{s}0'], master=CELL[s][0], cell_xy_um=[ISLX[k], CELL[s][1]],
                         **({} if dl[0] is None else dict(tt_ps=dict(min=dl[0], max=dl[1]), ff_ps=dict(min=dl[2], max=dl[3])))))
new = rows + add
(d / NEW).write_text(json.dumps(new, indent=1) + '\n')
n_rep = 0
def walk(o):
    global n_rep
    if isinstance(o, dict):
        for kk, v in o.items():
            if kk == 'pins_file' and v == OLD: o[kk] = NEW; n_rep += 1
            else: walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(P)
assert n_rep > 0
isl = (P.get('clock', {}).get('mesh', {}).get('core_islands', {}) or {}).get(M, {})
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
side = dict(schema='opentallas.core_mesh_island_parent.v1', module=M, event='DIE-HBM-61/PLAN d44v part 3',
            plan_core_pins=NEW, plan_core_pins_sha256=sha(d / NEW), previous_core_pins=OLD,
            outline_um=[218.592, 187.488], core_signal_pins=1216, mesh_island_ft_pins=par,
            island_rects_um=isl.get('rects_um'), ft_arcs=arcs, signed_view=SIGNED,
            rule='12.2a1 pushdown island ft ports are plan core pins (d35a master-plan form); the die connects each '
                 '_i pin to its tap (M9->M5 stack at the island centre) and each _o pin to its feed-through net; '
                 'clock arcs are pass-through in die clock STA, reset arcs are interface arcs in die STA; no core logic.')
sp = d / 'cores' / f'{M}__d44v_mpisl_parent.json'
sp.write_text(json.dumps(side, indent=1) + '\n')
ev = dict(event='DIE-HBM-61/PLAN d44v part 3: hcol_h1 +12 mesh-island ft pins (signed-DEF xy)', module=M,
          table_before=OLD, table_after=NEW, pins_before=len(rows), pins_after=len(new), pins_file_refs=n_rep,
          added=[q['name'] for q in add], parent_sidecar=str(sp.relative_to(d)))
(d / 'mpisl_event.json').write_text(json.dumps(ev, indent=1) + '\n')
f = d / 'die_plan.json'; f.unlink(); f.write_text(json.dumps(P, indent=1) + '\n')
print('mpisl:', M, len(rows), '->', len(new), 'pins; refs', n_rep)
