"""--cfifo-crsplit (H-C27 c27b, S-DIE / DIE-CLOCK 10-16): the column FIFO becomes the closed dsfd_cfifo_crs r5f view
(physical/ref_tile/s81coll_cfifo_crs/views/dsfd_cfifo_crs, 280.8 x 69.12; RTL rtl/dsrom_sys/s81_die_bind/glue/
dsfd_cfifo_crs.sv).  It has no stream clock input (ck), no column-clock root output (co) and no forwarded return clock
(rf); cr / cr_s / xf / xf2 are same-PLL phase-0 sinks of the column's regional tree.

Re-wiring of every root r (applied to the built model before finalize_r8):
  * the column clock net ck_col_<r> is driven by the x lane's last forwarded station clock (the cx<r> chain's fn0 that
    formerly fed cf.xf: F1, the hub-side chain forwards its clock and drives the column tree);
  * its loads: every former column-clock sink (cf.cr included) + cf.cr_s + cf.xf + cf.xf2 + cob<r>.fi;
  * cob<r> (one clock buffer in the cfifo row, E of the cfifo, inside the column cluster) drives co_<r> -> the first
    return station's fi (formerly cf.rf).  DIE-CLOCK 10-16: co is a balanced leaf of the cluster tree at the
    return-launch registers' branch, ck_col -> co is a plain ETM arc; hop 1 is a neighbour pair <= 80 ps TT/FF;
  * cf.ck (clk_stream) is dropped from the stream clock; the x2 lane's last-station fn0 stays an unused output.
Cycle notes for the compiler (S-ELEM receipt bd9235f06 results/rtl/s81_cfifo_crs_1016/r5f/routed_507e1b0c3):
status +1 edge (ri -> rd), forwarded marker after the 4th root reset edge (N edge 2 / S edge 4).
"""
from __future__ import annotations

MASTER = 'dsfd_cfifo_crs'
OUTLINE = (280.8, 69.12)
RETURN_CLOCK = 'co_buffer'    # DIE-CLOCK 10-16: return first station fi0 = co, one ck_col-tree buffer at the return-launch branch
CO_MASTER = 'dsfd_lkck_NS'     # one forwarded-clock buffer (glue: assign fo = fi; the cluster CTS sizes / balances it)
RTL_FILES = ('rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_crs.sv',
             'rtl/dsrom_sys/s81_die_bind/ot_s81_static_column_ingress_hr.sv',
             'rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross_hr.sv',
             'rtl/hdc/ot_hdc_cg.sv')
CYCLES = dict(status_ri_to_rd=+1, forwarded_marker_after_root_reset_edge=4,
              receipt='results/rtl/s81_cfifo_crs_1016/r5f/routed_507e1b0c3/receipt.json')


def rewire(G, m):
    """in place; returns a per-root record."""
    B = m['buses']
    by = {it.name: it for it in m['insts']}
    idx = {}
    for k, b in enumerate(B):
        for j, (inst, port) in enumerate(b[3]):
            idx.setdefault((inst, G.pslice(port)[0]), []).append((k, j))
    drop, rec = set(), {}
    roots = sorted(int(n[2:]) for n in by if n.startswith('cf') and n[2:].isdigit())
    for r in roots:
        cf = f'cf{r}'
        it = by[cf]
        it.master = MASTER
        # the x lane's forwarded clock into xf (cx<r>_fn) and the x2 lane's (cx<r>_fn2)
        (kx, jx), = idx[(cf, 'xf')]
        bx = B[kx]
        assert bx[1] == 'fclk' and jx == 1 and len(bx[3]) == 2, ('xf is not a 2-pin forwarded clock', bx[0])
        drv = bx[3][0]
        drop.add(kx)
        for k2, j2 in idx.get((cf, 'xf2'), []):
            assert B[k2][1] == 'fclk' and j2 == 1 and len(B[k2][3]) == 2, ('xf2 is not a 2-pin forwarded clock', B[k2][0])
            drop.add(k2)
        # the return chain's first station clock (cf.rf -> fi)
        ret = []
        for k3, j3 in idx.get((cf, 'rf'), []):
            assert j3 == 0, ('rf is not a driver', B[k3][0])
            ret += [e for e in B[k3][3][1:]]
            drop.add(k3)
        # the column clock: driver cf.co today
        (kc, jc), = idx[(cf, 'co')]
        bc = B[kc]
        assert jc == 0, ('co is not the column clock driver', bc[0])
        loads = [e for e in bc[3][1:] if not (e[0] == cf and G.pslice(e[1])[0] in ('cr',))]
        cob = place_co_buffer(G, m, it, r)
        loads = [(cf, 'cr'), (cf, 'cr_s'), (cf, 'xf'), (cf, 'xf2')] + loads + [(cob.name, 'fi')]
        B[kc] = (bc[0], bc[1], bc[2], [drv] + loads)
        B.append((f'co_{r}', 'fclk', 1, [(cob.name, 'fo')] + ret))
        # stream clock: drop cf.ck
        for k4, j4 in idx.get((cf, 'ck'), []):
            b4 = B[k4]
            B[k4] = (b4[0], b4[1], b4[2], [e for e in b4[3] if e != b4[3][j4]])
        rec[r] = dict(column_clock_driver=list(drv), return_first_station=[list(e) for e in ret],
                      column_clock_sinks=len(loads))
    B[:] = [b for k, b in enumerate(B) if k not in drop]
    for k_ in ('_by', '_nets_of', '_nets_of_o'):
        m.pop(k_, None)
    m['cfifo_crsplit'] = dict(master=MASTER, outline_um=list(OUTLINE), return_clock=RETURN_CLOCK, cycles=CYCLES,
                              roots=len(rec), removed_buses=len(drop))
    return rec


def place_co_buffer(G, m, cf, r):
    """the co clock buffer: first free 8.64-um site in the cfifo row E of the cfifo (inside the column cluster)."""
    w, h = G.LKCK_WH[0] - G.SHAVE, G.LKCK_WH[1] - G.SHAVE
    reg = f'frame_{r}'
    boxes = [i.box() for i in m['insts'] if i.region == reg]
    y = cf.y
    x = G.up(cf.x + cf.w + 4.32, G.GX)
    f = m['frames'][r]
    while x + w <= f['x'] + G.COL_W8 - 4.32:
        bx = (x, y, x + w, y + h)
        if not any(bx[0] < b[2] + .432 and b[0] < bx[2] + .432 and bx[1] < b[3] + .432 and b[1] < bx[3] + .432 for b in boxes):
            it = G.Inst(f'cob{r}', CO_MASTER, x, y, w, h, 'R0', kind='lkck', region=reg, domain='fwd')
            m['insts'].append(it)
            return it
        x = G.up(x + 4.32, G.GX)
    raise ValueError(f'--cfifo-crsplit: no co buffer site E of cf{r}')


def rtl_text(root):
    """the crs RTL (and its two ingress primitives + clock gate) appended to the die glue for the port-bind check."""
    out = ['// --cfifo-crsplit: closed dsfd_cfifo_crs RTL (verbatim)']
    for p in RTL_FILES:
        out.append(f'// ---- {p}')
        out.append((root / p).read_text())
    return '\n'.join(out) + '\n'
