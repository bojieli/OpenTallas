#!/usr/bin/env python3
"""DIE-HBM-61 d44v part 6a (one-block plan pin event, the part-3 mk_mpisl recipe): query_static q7b2 mesh-island
feed-through pins.

SS24 20:16: the re-signed ot_hbm_idx_query_static (q7b2 routed DB, re-sign ss24/q7b2_w_hbm, flow-20261103-w-hbm, SIGNED
TT +0.35 / FF +6.54, LEC EQ, DEF sha256 88f7ef6a00a78f36) does not count: design_unmatched = 4 extra pins
mp_isl0_{ck,rst}_{i,o}, the 12.2a1 pushdown island ft ports the kit adds from core_infra_plan.json (the same class as
hcol_h1, d44v part 3).  This step adds them to the plan table at the signed DEF layer / centre / rect, so the signed
design is the plan design, and records each pin's parent connection (12.2a1):
  mp_isl0_ck_i  <- die clock tap: M9->M5 clock stack at the island centre (die mesh/tree drop)
  mp_isl0_ck_o  -> die mesh/tree feed-through net (independent of the core clock pin)
  mp_isl0_rst_i <- die regional reset stack (M9->M5) at the island centre
  mp_isl0_rst_o -> die reset feed-through net (independent of the core reset pin)
  arcs ck_i->ck_o via fixed BUFx12f mp_isl0_ck0, rst_i->rst_o via fixed BUFx4 mp_isl0_rst0 (no core logic, LEC-exempt).
Writes cores/<table>__mpisl.json, repoints every query_static pins_file, writes cores/<module>__d44v_mpisl_parent.json
+ mpisl_q_event.json.     python3 mk_mpisl_q.py PLAN_DIR"""
import hashlib, json, sys
from pathlib import Path

M = 'ot_hbm_idx_query_static'
OLD = 'cores/ot_hbm_idx_query_static__170.64x164.16__canon__d16f__codex_g21__fr28__d32q.json'
NEW = 'cores/ot_hbm_idx_query_static__170.64x164.16__canon__d16f__codex_g21__fr28__d32q__mpisl.json'
SIGNED = dict(resign='/srv/opentallas-scratch2/claude/ss24/q7b2_w_hbm (epyc2, PROVENANCE kind resign, SIGNED)',
              def_='codex-hbm-cores-1101/query/q7b2/run/results/asap7/hbc_ot_hbm_idx_query_static/base/6_final.def',
              def_sha256_16='88f7ef6a00a78f36', routed_db_sha256_16='c00d6a8e025e859a', flow_tag='flow-20261103-w-hbm')
# signed DEF PINS (nm, M5): centre + rect half sizes
RECT = {'mp_isl0_ck_i': (85320, 84240, 24, 240), 'mp_isl0_ck_o': (87480, 84240, 24, 240),
        'mp_isl0_rst_i': (85320, 79920, 16, 96), 'mp_isl0_rst_o': (87480, 79920, 16, 96)}
CELL = {'ck': ('BUFx12f_ASAP7_75t_R', (85.914, 82.35)), 'rst': ('BUFx4_ASAP7_75t_R', (86.238, 81.27))}
PARENT = {('ck', 'i'): ('die_clock_tap', 'die M9 clock stack (M9->M5 at the island centre): die mesh/tree tap'),
          ('ck', 'o'): ('die_clock_feed', 'die mesh/tree feed-through net; independent core clock pin'),
          ('rst', 'i'): ('die_reset_tap', 'die regional reset stack (M9->M5 at the island centre)'),
          ('rst', 'o'): ('die_reset_feed', 'die reset feed-through net; independent core reset pin')}
DLY = {'ck': (18.77, 21.19, 14.21, 15.42), 'rst': (24.89, 27.88, 18.4, 19.59)}   # signoff/ft_interface.json

r3 = lambda v: round(v, 3)
d = Path(sys.argv[1]); P = json.loads((d / 'die_plan.json').read_text())
rows = json.loads((d / OLD).read_text())
assert not any(str(q['name']).startswith('mp_isl') for q in rows), 'already has mp_isl pins'
add, par, arcs = [], [], []
for s in ('ck', 'rst'):
    for io in ('i', 'o'):
        n = f'mp_isl0_{s}_{io}'; cx, cy, hx, hy = RECT[n]
        add.append(dict(name=n, layer='M5', x=r3(cx / 1000), y=r3(cy / 1000), w=r3(2 * hx / 1000), h=r3(2 * hy / 1000)))
        kind, how = PARENT[(s, io)]
        par.append(dict(name=n, direction='INPUT' if io == 'i' else 'OUTPUT', layer='M5',
                        rect_um=[r3((cx - hx) / 1000), r3((cy - hy) / 1000), r3((cx + hx) / 1000), r3((cy + hy) / 1000)],
                        island='isl0', island_role='clock_entry', parent=kind, connect=how))
    dl = DLY[s]
    arcs.append(dict(source=f'mp_isl0_{s}_i', sink=f'mp_isl0_{s}_o', kind='clock' if s == 'ck' else 'reset',
                     cells=[f'mp_isl0_{s}0'], master=CELL[s][0], cell_xy_um=list(CELL[s][1]),
                     tt_ps=dict(min=dl[0], max=dl[1]), ff_ps=dict(min=dl[2], max=dl[3])))
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
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
side = dict(schema='opentallas.core_mesh_island_parent.v1', module=M, event='DIE-HBM-61 d44v part 6a',
            plan_core_pins=NEW, plan_core_pins_sha256=sha(d / NEW), previous_core_pins=OLD, outline_um=[170.64, 164.16],
            core_signal_pins=len(rows), mesh_island_ft_pins=par, ft_arcs=arcs, signed_view=SIGNED,
            rule='12.2a1 pushdown island ft ports are plan core pins (d35a master-plan form); the die connects each '
                 '_i pin to its tap (M9->M5 stack at the island centre) and each _o pin to its feed-through net; '
                 'clock arcs are pass-through in die clock STA, reset arcs are interface arcs in die STA; no core logic.')
sp = d / 'cores' / f'{M}__d44v_mpisl_parent.json'
sp.write_text(json.dumps(side, indent=1) + '\n')
ev = dict(event='DIE-HBM-61 d44v part 6a: query_static +4 mesh-island ft pins (signed q7b2 DEF xy)', module=M,
          table_before=OLD, table_after=NEW, pins_before=len(rows), pins_after=len(new), pins_file_refs=n_rep,
          added=[q['name'] for q in add], parent_sidecar=str(sp.relative_to(d)))
(d / 'mpisl_q_event.json').write_text(json.dumps(ev, indent=1) + '\n')
f = d / 'die_plan.json'; f.unlink(); f.write_text(json.dumps(P, indent=1) + '\n')
print('mpisl_q:', M, len(rows), '->', len(new), 'pins; refs', n_rep)
