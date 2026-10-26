#!/usr/bin/env python3
"""TOK-DS 10-25: per-slice rstd (finish root) edges from a compiled --entry-norm-check all programme, and the XQ / XB
all-gather line occupancy those edges imply (norm_q.py).  Usage: norm_q_report.py <prog dir> <die src tree> [out.json]
(OT_S81_SELECTED_SOURCE_ROOT as for the compile)."""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import dv_layer_compile as C      # noqa: E402
import norm_nx as N               # noqa: E402
import norm_q as Q                # noqa: E402


Q_NOMINAL = Q.Q_AFTER_ROOT  # measured on fully reclocked cut_0S/0N/7, see norm_q


def main(prog, tree, out=None):
    S = json.loads((Path(prog) / 'schedule.json').read_text())
    if tree == '-':
        # The compiled programme already contains the exact die-build link
        # endpoints/ages. Reuse those rather than parsing the full RTL again.
        class CompiledDie:
            links = S.get('all_links') or S['links']

            def slices(self):
                out = {}
                for event in S['events']:
                    if event.get('kind') != 'NX' or not event.get('words'):
                        continue
                    sid = (int(event['words'][0][1], 16) >> 9) & 15
                    if event['inst'] in out and out[event['inst']]['sid'] != sid:
                        raise ValueError('compiled NX headers disagree on slice SID')
                    out[event['inst']] = dict(sid=sid)
                if sorted(v['sid'] for v in out.values()) != list(range(16)):
                    raise ValueError('compiled NX programme lacks one of 16 source SIDs')
                return out

        die = CompiledDie()
    else:
        die = C.Die(tree)
    sl = die.slices()
    by_sid = {v['sid']: k for k, v in sl.items()}
    words = []
    for e in S['events']:
        m = re.fullmatch(r'attn\.nx\.o(\d+)\.h(\d+)', str(e.get('tag', '')))
        if e.get('kind') != 'NX' or not m:
            continue
        o, h = int(m.group(1)), int(m.group(2))
        lk, dst, inport, age = N._lane0(die, e['inst'], e['port'])
        words.append(dict(inst=e['inst'], port=e['port'], edge=e['cycle'], hops=h, origin=o, dst=dst, land=e['cycle'] + age,
                          own=(e['inst'] == by_sid[o] and h in (N.HE, N.HW))))
    arr = Q.arrivals(words)
    root = {}
    for inst, dl in sorted(arr.items()):
        assert len(dl) == Q.NS, (inst, len(dl))
        root[inst] = Q.finish_root(dl)
    last = {inst: max(dl.values()) for inst, dl in arr.items()}
    r0 = min(root.values())
    doc = dict(n_words=len(words), c_in=Q.C_IN,
               slices={inst: dict(sid=sl[inst]['sid'], last_flit_dl=last[inst], first_flit_dl=min(arr[inst].values()),
                                  root_wb=root[inst], root_rel=root[inst] - r0) for inst in sorted(root, key=lambda x: sl[x]['sid'])},
               root_spread=max(root.values()) - r0)
    # XQ / XB all-gather on the lines: positions, line / V lane ages from the die; q = root + a nominal constant (only
    # differences matter for collisions)
    pos = {inst: (sl[inst]['sid'] >> 1, sl[inst]['sid'] & 1) for inst in sl}
    by_ct = {v: k for k, v in pos.items()}
    age, vage = {}, {}
    for inst, (col, t) in pos.items():
        for side, port in (('e', 'ro_e'), ('w', 'ro_w')):
            if (side == 'e' and col < 7) or (side == 'w' and col > 0):
                age[(inst, side)] = N._lane0(die, inst, port)[3]
        vage[inst] = N._lane0(die, inst, 'vo')[3]
    # fc31 selected contracts: BK_COL is a vstop (2), BK_SEL adds its
    # face relay (3), seqhost's RL1 rung is 6+RL (7), both directions.
    bridges = dict(u_bk_col=2, u_bk_sel=3, u_seqhost=7, u_gunit=12, u_eng=2)
    vpaths = Q.v_paths(die, bridges)
    Q.V_ASM = None
    qn = {inst: root[inst] + Q_NOMINAL for inst in root}
    res = {}
    for va in ['per_slice']:
        Q.V_ASM = {i: p['assembled_after_own_line'] for i, p in vpaths.items()}
        occ, cl, coa = Q.allgather(qn, dict(pos=pos, age=age, partner={i: by_ct[(c, 1 - t)] for i, (c, t) in pos.items()}))
        load = defaultdict(int)
        span = defaultdict(lambda: [1 << 30, -1])
        for (inst, side, e), v in occ.items():
            load[(inst, side)] += len(v)
            span[(inst, side)][0] = min(span[(inst, side)][0], e)
            span[(inst, side)][1] = max(span[(inst, side)][1], e)
        worst = max(load, key=lambda k: load[k])
        res[va] = dict(line_collision_edges=len(cl), beats_in_collision=sum(len(v) for v in cl.values()),
                       own_asm_same_edge=len(coa), worst_side=f'{worst[0]}.{worst[1]}', worst_beats=load[worst],
                       worst_window_edges=span[worst][1] - span[worst][0] + 1,
                       first_collision=min(cl, key=lambda k: k[2]) if cl else None)
    doc.update(line_age={f'{i}.{s}': a for (i, s), a in sorted(age.items())}, v_age=vage, allgather=res,
               v_assembly_age=Q.V_ASM, v_paths=vpaths, v_paths_complete=True, v_bridge_cycles=bridges,
               q_nominal_after_root=Q_NOMINAL)
    txt = json.dumps(doc, indent=1, default=str)
    if out:
        Path(out).write_text(txt + '\n')
    print(txt)


if __name__ == '__main__':
    main(*sys.argv[1:])
