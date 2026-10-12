#!/usr/bin/env python3
"""s81-vm-1011 (2026-10-11): pin plan of the VM master v2 hard tile dsfd_vm_bgq28 (rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq_sys.sv:
dsfd_vm_bgq at NP 28 / NPR 10, NSTG 2, one 128-b bit slice, 8 banks = 8 x ot_sram_1r1w_512x128_m4_r2c2) and the master
composition record.

Tile 537.6 x 500.04 um: the 28-port request bus (4,144 b) + 10-lane read return (1,297 b) enter the N face and leave the
S face at identical x (abutted chain of 4 tiles per slice), all on M5 at 2 tracks (10.4 pins/um < the 12 pins/um/layer
lint limit); the macro column sits at the W edge (place_macros_vm28.tcl), the E channel carries the bus.  The master
(dsfd_sp_vm_m) = FE (N) + 4 slices x 4 tiles + BE (S); slab = 4 x 460.8 wide.

Writes physical/s81_ph_views/ports/contract_vm24/dsfd_vm_bgq28/{ports.json, io_place.tcl, ports.svh} and
physical/s81_ph_views/vm_master/composition.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s81_ph_coll_tiles as T   # noqa: E402

T.CONTRACT = 'contract_vm28'
W, H, NT, NS = 345.6, 500.04, 4, 4    # W = 32 x the 10.8-um M7 PG pitch (tile M7 pins stay clear of every block's stripes)
SLAB_W = 1520.064                  # ds-1010 hub-column VM slab width (FE / BE span it; the 4 tile columns are centred)
X0 = 0.0                            # tile columns from the slab's W edge (M7 / M5 / PG grids coincide)
CH = 43.2                           # s81die-1011 contract v3: channel between tile columns so every tile W-face pin (ck / rs /
                                    # grp, M4) is reachable from die-level routing (abutted columns 1-3 buried them);
                                    # 43.2 = 4 x the 10.8 M7 PG pitch = 675 x 0.064 (M7) = 450 x 0.096 (M5 pin grid) = 800 sites
PX = W + CH                         # column pitch 388.8; 4 columns + 3 channels = 1,512.0 <= SLAB_W
assert X0 + 4 * W + 3 * CH <= SLAB_W, "VM tile columns + channels exceed the slab"
NP, NPR, RA, DW = 28, 10, 14, 128
FE_H, BE_H = 594.0, 108.0          # el1011-ds-vm/fe 10-11 v5 (3c93919d3): 473.04 -> 594.00 (FLOORPLAN_MARGIN 68.1% -> ~54.2%); earlier FE 311.04 -> 473.04 (hierarchical FE: 16 x dsfd_vm_clt 230.04-um tiles under the N face + landing macros / parent band below); was         # slab height 2,419.2 (ds-1010: 2.42 mm)          # FE / BE outline heights (first estimate: FE ~125k flops + 16.8k die pins; BE ~10k)


M7P, M7O = 0.064, 0.016            # ORFS asap7 make_tracks M7 x pitch / offset
M7S = (1.0, 10.8, 0.288)            # view PDN M7 stripes (pdn_coll.tcl): offset, pitch, width (VDD at off, VSS at off + 5.4)


class Plan2(T.Plan):
    """T.Plan with M7 pins on their own track grid (0.064 / 0.016), kept clear of the M7 PG stripes"""
    def put(self, port, bit, face, layer, coord):
        if layer not in ('M6', 'M7') or face not in 'NS':
            return super().put(port, bit, face, layer, coord)
        t = round((coord - M7O) / M7P)
        pos = M7O + t * M7P
        key = (face, layer, t)
        assert key not in self.used, (self.m, port, bit, face, coord)
        self.used.add(key)
        # M6 (tile-signal layer contract <= M6, el1011-ds-vm 10-12): the former M7 pin at the same x, 0.064 wide so it spans
        # >= 1 M5 track (0.048 pitch) for a V5 access, 0.32 deep (clear of the M6 PG straps at y 0.456 / H - 0.456 - ...)
        hw, d = (0.032, 0.32) if layer == 'M6' else (0.016, 0.256)
        if face == 'S': r = (pos - hw, 0.0, pos + hw, d)
        else: r = (pos - hw, self.h - d, pos + hw, self.h)
        self.pins.append((f'{port}[{bit}]', layer) + tuple(T.r4(v) for v in r))


def m7_ok(x):
    for base in (M7S[0], M7S[0] + 5.4):
        u = (x - base) % M7S[1]
        if u > M7S[1] - 0.2 or u < M7S[2] + 0.2:
            return False
    return True


def tracks(w):
    """the pin x positions of a W-wide face: M5 every 2 tracks, then M7 every 2 tracks off the stripes"""
    xs = [('M5', 0.012 + 0.096 * i) for i in range(25, int((w - 2.4) / 0.096))]
    xs += [('M7', M7O + 2 * M7P * i) for i in range(20, int((w - 2.4) / (2 * M7P))) if m7_ok(M7O + 2 * M7P * i)]
    return xs


def tile():
    pl = Plan2('dsfd_vm_bgq28', W, H)
    pairs = [('i_v', 'f_v', NP), ('i_we', 'f_we', NP), ('i_row', 'f_row', NP * RA), ('i_mask', 'f_mask', NP * DW // 32),
             ('i_d', 'f_d', NP * DW), ('r_v', 'o_v', NPR), ('r_d', 'o_d', NPR * DW), ('r_f', 'o_f', 4), ('r_o', 'o_o', 3)]
    # tile signal pins <= M6 (contract layer_defaults signal_max M6 under the parent's M8 straps; the tile's own M7 is PG):
    # the second pin set keeps its M7-grid x (clear of the tile M7 stripes) on M6, so FE S / BE N / BE-slice N follow by x
    tr = [('M6' if ly == 'M7' else ly, x) for ly, x in tracks(W)]
    need = sum(b for _, _, b in pairs)
    assert need <= len(tr), (need, len(tr))
    k = 0
    for i_n, o_n, b in pairs:
        pl.dirs[i_n] = ('input', b); pl.dirs[o_n] = ('output', b)
        for bit in range(b):
            ly, x = tr[k]; k += 1
            pl.put(i_n, bit, 'N', ly, x); pl.put(o_n, bit, 'S', ly, x)
    x = k
    pl.bus('ck', 1, 'input', 'W', 'M4', H / 2); pl.bus('rs', 1, 'input', 'W', 'M4', H / 2 + 4.8)
    pl.bus('grp', 2, 'input', 'W', 'M4', H / 2 + 9.6)
    pl.emit('VM master v2 tile (dsfd_vm_bgq NP 28 / NPR 10, 8 banks x 128 b = 8 SRAM macros); N face = request / read-data chain '
            'in, S face = the same signals out at identical x (4 abutted tiles a slice, 4 slices W -> E)')
    return x


def tile_x():
    """tile pin (layer, x) per (port, bit) from the tile plan just emitted"""
    d = json.loads((T.ROOT / 'physical/s81_ph_views/ports' / T.CONTRACT / 'dsfd_vm_bgq28/ports.json').read_text())
    xs = {}
    for port, rec in d['ports'].items():
        for nm, ly, x0, y0, x1, y1 in rec['pins']:
            xs[nm] = (ly, (x0 + x1) / 2)
    return xs


def place_die_face(pl, ports, face, w):
    """die pins of ports [(name, bits, dir)] packed on a face over the M5 + M7 pin tracks"""
    tr = tracks(w)
    k = 0
    for nm, bits, d in ports:
        pl.dirs[nm] = (d, bits)
        for b in range(bits):
            assert k < len(tr), (pl.m, nm)
            ly, x = tr[k]; k += 1
            pl.put(nm, b, face, ly, x)
    return k


def put_t(pl, port, bit, face, h, xs, tname):
    ly, x = xs[tname]
    pl.put(port, bit, face, ly, X0 + h * PX + x)


def fe(xs):
    pl = Plan2('dsfd_vm_fe', SLAB_W, FE_H)
    # S face: the slice request buses at the tile-0 N pins (abutment), slice-major port bits as dsfd_sp_vm_m
    for port, tport, per in (('m_v', 'i_v', 1), ('m_we', 'i_we', 1), ('m_row', 'i_row', RA), ('m_mask', 'i_mask', DW // 32),
                             ('m_d', 'i_d', DW)):
        pl.dirs[port] = ('output', NS * NP * per)
        for h in range(NS):
            for b in range(NP * per):
                put_t(pl, port, h * NP * per + b, 'S', h, xs, f'{tport}[{b}]')
    pl.dirs['m_rf'] = ('output', NS * 4)
    for h in range(NS):
        for b in range(4):
            put_t(pl, 'm_rf', h * 4 + b, 'S', h, xs, f'r_f[{b}]')
    # N face: the die pins (capture first: the capture slab abuts the VM's N face)
    place_die_face(pl, [('f_cap', 13376, 'input'), ('f_svc', 1027, 'input'), ('f_coll', 2100, 'input'), ('t_cts', 3, 'output'),
                        ('f_sel', 515, 'input'), ('f_col', 515, 'input'), ('f_hc', 1026, 'input'),
                        ('f_swv', 1, 'input'), ('f_swd', 527, 'input'), ('t_swg', 1, 'output'), ('f_srv', 1, 'input'),
                        ('f_srd', 31, 'input'), ('t_srg', 1, 'output'), ('t_ks', 53, 'output'),
                        ('vwe', 1, 'input'), ('vwa', 14, 'input'), ('vwd', 512, 'input'), ('vre', 1, 'input'), ('vra', 14, 'input'),
                        ('cv', 1, 'input'), ('cd', 84, 'input'), ('dv', 1, 'output'), ('dt', 8, 'output'),
                        ('c_wv', 1, 'output'), ('c_wd', 10, 'output'), ('c_wr', 1, 'input'), ('t_rdy', 4, 'output')],
                    'N', SLAB_W)
    # E face: composition nets to / from the BE (status down, P2 credit up); W face: clocks / resets
    pl.bus('fe_flt', 16, 'output', 'E', 'M4', 20.0); pl.bus('f_p2c', 1, 'input', 'E', 'M4', 40.0)
    # W pins below the clt tile wall (y 226.8 .. 456.84; tile 0 abuts the W edge)
    pl.bus('ck', 1, 'input', 'W', 'M4', 100.0); pl.bus('rst', 1, 'input', 'W', 'M4', 104.8)
    pl.bus('cks', 1, 'input', 'W', 'M4', 109.6); pl.bus('rss', 1, 'input', 'W', 'M4', 114.4)
    pl.emit('VM master v3 front end: S face = the 4 slice request buses at the tile-0 N pins; N face = every client die pin')


def be(xs):
    pl = Plan2('dsfd_vm_be', SLAB_W, BE_H)
    for port, tport, per in (('o_v', 'o_v', 1), ('o_d', 'o_d', DW)):
        pl.dirs[port] = ('input', NS * NPR * per)
        for h in range(NS):
            for b in range(NPR * per):
                put_t(pl, port, h * NPR * per + b, 'N', h, xs, f'{tport}[{b}]')
    for port, tport, n in (('o_f', 'o_f', 4), ('o_o', 'o_o', 3)):
        pl.dirs[port] = ('input', NS * n)
        for h in range(NS):
            for b in range(n):
                put_t(pl, port, h * n + b, 'N', h, xs, f'{tport}[{b}]')
    # slice 0 forward metadata (tile-3 f_*): P2 (port 5) and the X ports {9, 8, 2, 7, 6}
    pl.dirs['f_v5'] = ('input', 1); put_t(pl, 'f_v5', 0, 'N', 0, xs, 'f_v[5]')
    pl.dirs['f_we5'] = ('input', 1); put_t(pl, 'f_we5', 0, 'N', 0, xs, 'f_we[5]')
    pl.dirs['f_m5'] = ('input', 92)
    for b in range(92):
        put_t(pl, 'f_m5', b, 'N', 0, xs, f'f_d[{5 * DW + b}]')
    xp = (6, 7, 2, 8, 9)
    for nm, tp in (('f_vx', 'f_v'), ('f_wex', 'f_we')):
        pl.dirs[nm] = ('input', 5)
        for i, q in enumerate(xp):
            put_t(pl, nm, i, 'N', 0, xs, f'{tp}[{q}]')
    pl.dirs['f_mx'] = ('input', 20)
    for i, q in enumerate(xp):
        for b in range(4):
            put_t(pl, 'f_mx', 4 * i + b, 'N', 0, xs, f'f_d[{q * DW + b}]')
    place_die_face(pl, [('t_srq', 1026, 'output'), ('t_err', 1, 'output'), ('vrv', 1, 'output'), ('vrq', 512, 'output'),
                        ('t_bl', 16 * 513, 'output'), ('c_l0v', 1, 'output'), ('c_l0d', 604, 'output'), ('c_l0r', 1, 'input'),
                        ('flt', 1, 'output'), ('fvec', 32, 'output'), ('max_occ', 3, 'output')], 'S', SLAB_W)
    pl.bus('fe_flt', 16, 'input', 'E', 'M4', 20.0); pl.bus('t_p2c', 1, 'output', 'E', 'M4', 40.0)
    pl.bus('ck', 1, 'input', 'W', 'M4', BE_H / 2); pl.bus('rst', 1, 'input', 'W', 'M4', BE_H / 2 + 4.8)
    pl.bus('cks', 1, 'input', 'W', 'M4', BE_H / 2 + 9.6); pl.bus('rss', 1, 'input', 'W', 'M4', BE_H / 2 + 14.4)
    pl.emit('VM master v3 back end: N face = the tile-3 S pins of the 4 slices (+ slice-0 forward metadata); S face = response die pins')


def main():
    x = tile()
    xs = tile_x()
    fe(xs)
    be(xs)
    comp = dict(
        schema='opentallas.s81_ph.composition.v1', slab='dsfd_sp_vm v2 (VM master, s81-vm-1011)',
        slab_um=[SLAB_W, FE_H + NT * H + BE_H],
        source='rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv module dsfd_sp_vm_m (the exact composition netlist; gate '
               'tools/s81_vm/s81_vm_gate.py)',
        instances=[dict(inst='u_fe', master='dsfd_vm_fe', xy=[0.0, T.r4(BE_H + NT * H)], orient='R0', um=[SLAB_W, FE_H])]
        + [dict(inst=f'g_h[{h}].g_t[{t}].u_bg', master='dsfd_vm_bgq28', xy=[T.r4(X0 + h * PX), T.r4(BE_H + (NT - 1 - t) * H)],
                orient='R0', grp=t, slice=h) for h in range(NS) for t in range(NT)]
        + [dict(inst='u_be', master='dsfd_vm_be', xy=[0.0, 0.0], orient='R0', um=[SLAB_W, BE_H])],
        nets=dict(chain='per slice h: g_t[t].f_* -> g_t[t+1].i_*, g_t[t].o_* -> g_t[t+1].r_* by abutment; FE m_* slice h -> '
                        'g_t[0].i_* (FE S face at the tile x); g_t[0].r_v / r_d / r_o = chain head (0), r_f = FE status; '
                        'g_t[3].o_* -> BE (BE N face at the tile x); slice 0 g_t[3].f_v[5] / f_we[5] / f_d[5*128 +: 92] -> BE '
                        '(P2 metadata); FE fe_flt[16] -> BE (sticky status, multicycle); BE t_p2c -> FE f_p2c (credit)',
                  clock='ck = serial 0.9 GHz to FE, every tile and BE; cks = stream 1.2 GHz to FE / BE (dsfd_sp_ctrl side: '
                        'engine adapter, ratio CDC FIFOs)'),
        ports='NP 28: p0 / p1 WFC kit (dsfd_vm_wfc_ep RD2), p2 X2, p3 / p4 dsfd_sp_ctrl VM lanes A / B, p5 P2 reader, p6 / p7 '
              'X0 / X1, p8 / p9 X3 / X4, p10 / p11 landing drains, p12 .. p27 capture lanes 0 .. 15 (write only)',
        latency='fixed read latency 24 serial cycles from the client pins (ports 0, 1, 2, 6, 7); ctrl reads via CDC (vrv)')
    (T.ROOT / 'physical/s81_ph_views/vm_master').mkdir(parents=True, exist_ok=True)
    (T.ROOT / 'physical/s81_ph_views/vm_master/composition.json').write_text(json.dumps(comp, indent=1) + '\n')
    print('ok last x', round(x, 2), 'slab', comp['slab_um'])


if __name__ == '__main__':
    main()
