#!/usr/bin/env python3
"""TOK-DS 10-25: rstd timing of the 16-slice norm and the XQ / XB all-gather on the slice line (prediction + collisions).

Every slice finishes rstd itself (ot_s81dv_xfin -> ot_s81dv_norm_finish) from the 16 NX flits, so its rstd edge is a
function of ITS flit arrival times (the compiled snake words, layer_prog/norm_nx.py).  The finish is a sequenced
dataflow tree (one LAV = 6 adder; ready nodes lowest heap index first, 8-node groups then lowest group, both
registered; a stale pick is a bubble): `finish_root()` is that issue logic cycle by cycle (ot_s81dv_norm_finish RTL
75c077ec9, lines 118-192).  After the root add every edge is fixed (/ D, + eps, rsqrt, vn scale, vq aq12, glue):
one constant, Q_AFTER_ROOT, from the root write-back to the slice's first own XQ beat on its line outputs.

The own beats (ot_s81sl_vq): leaf k's XQ beat at q + 4k, XB at q + 20 + 4k -> 10 beats a slice on the rstop line,
both sides (E hops 7 - col, W hops col; zero-hop side skipped), and as 4 V fragments to the column partner, which
re-assembles and injects them on ITS line both ways (V_ASM edges later).  A line beat moves one stop per
age + LINE_STOP edges.  ot_s81sl_rstop allows ONE source per line side per cycle (forward, NX, own, assembled,
control) and never own + assembled in one cycle: every second source is a sticky fault.  `allgather()` lists them.

Q_AFTER_ROOT was measured on the fully reclocked pre-deskew r4all cuts 0S/0N/7:
model roots 548/549/549 -> own XQ output-register edges 693/694/694. Deskew
changes partial arrival, upstream of the root; its full-cut recheck is pending.
LINE_STOP = 2 is the rstop header's stated latency.
"""
from collections import defaultdict

NS, NVL = 16, 5
NV = NS * NVL
NVP = 1 << (NV - 1).bit_length()
HB = NVP.bit_length() - 1
LAV = 6
LINE_STOP = 2          # rstop: line in pin -> line out pin
TRAIN = [4 * k for k in range(5)] + [20 + 4 * k for k in range(5)]    # XQ k, XB k (edges after q)
KIND = [1] * 5 + [2] * 5
# calibration (re-measured on the deskewed cuts; see the TOK-DS lane log)
C_IN = 2               # landed NX pin -> xstop deliver (dl) edge; own: dl = own out edge - (NX_FWD - 2 - C_IN)
Q_AFTER_ROOT = 145     # root write-back edge -> first own XQ beat on the line outputs
V_ASM = None           # own beat on the line outputs -> the column partner's assembled beat on its line outputs
#                        ({inst: edges} or one value; rstop: 2 + the V lane age, the 4-fragment train being 4 edges a beat)


def v_paths(die, bridge_cycles):
    """Walk the full V rung, including transparent host/BK stops.

    bridge_cycles must be supplied from the selected RTL contracts. A source
    vo lane that lands at seqhost or BK is not the column partner's input.
    """
    import norm_nx as N
    slices = die.slices()
    result = {}
    for origin in slices:
        at, port, total, path, visited = origin, 'vo', 0, [], set()
        while True:
            if (at, port) in visited:
                raise ValueError('cyclic V route from ' + origin)
            visited.add((at, port))
            lane, dst, input_port, age = N._lane0(die, at, port)
            path.append(dict(lane=lane, src=at + '.' + port, dst=dst + '.' + input_port, cycles=age))
            total += age
            if dst in slices:
                if slices[dst]['sid'] != slices[origin]['sid'] ^ 1:
                    raise ValueError('V route ends at a different column: ' + origin + ' -> ' + dst)
                result[origin] = dict(peer=dst, wire_and_bridge_cycles=total,
                                      assembled_after_own_line=total + 2, path=path)
                break
            if dst not in bridge_cycles or input_port not in ('vi_s', 'vi_n'):
                raise ValueError('unmodeled V bridge: ' + dst + '.' + input_port)
            delay = bridge_cycles[dst]
            output_port = 'vo_n' if input_port == 'vi_s' else 'vo_s'
            path.append(dict(bridge=dst, src=input_port, dst=output_port, cycles=delay))
            total += delay
            at, port = dst, output_port
    return result


def isadd(n):
    """the verbatim g_add condition of ot_s81dv_norm_finish"""
    H = HB - (_clog2(n + 1) - 1)
    return 1 <= n < NVP and (((2 * n + 1) << (H - 1)) - NVP) < NV


def _clog2(x):
    return (x - 1).bit_length()


def finish_root(dl):
    """dl = {flit base (5 sid): the edge its dl_v is high} -> the edge the root (node 1) is written back (wr_v)"""
    vd = {}                                   # node -> first cycle VD is 1
    for b, a in dl.items():
        for k in range(NVL):
            vd[NVP + b + k] = a + 2           # dl_v (a) -> iv (a + 1) -> leaf vld (a + 2)
    for ix in range(NV, NVP):
        vd[NVP + ix] = None

    def VD(n, c):
        while n < NVP and not isadd(n):
            n = 2 * n                         # pass node = its left child
        v = vd.get(n)
        return v is not None and c >= v
    adds = [n for n in range(1, NVP) if isadd(n)]
    iss = {}
    o_r = {}                                  # registered stage-1 one-hot: group -> node (or None)
    c = min(dl.values())
    pending = []                              # (write-back cycle, node)
    for _ in range(4096):
        # cycle c: combinational rdy from VD and iss
        rdy = [n for n in adds if VD(2 * n, c) and VD(2 * n + 1, c) and not (n in iss and iss[n] <= c)]
        # win from the stage-1 registers (computed last cycle)
        groups = sorted(g for g, n in o_r.items() if n is not None)
        win = None
        if groups:
            n = o_r[groups[0]]
            if not (n in iss and iss[n] <= c):
                win = n
        if win is not None:
            iss[win] = c + 1
            wb = c + 1 + LAV                  # f_q (c + 1) -> av[LAV]
            vd[win] = wb + 1
            if win == 1:
                return wb
        nxt = {}
        for n in rdy:
            g = n // 8
            if g not in nxt or n < nxt[g]:
                nxt[g] = n
        o_r = nxt
        c += 1
    raise ValueError('norm_q: finish did not complete')


def arrivals(words, nx_fwd=6, c_in=C_IN):
    """snake words (norm_nx: inst, port, edge, hops, origin, + land / dst from the die) -> {inst: {base: dl edge}}"""
    c_out = nx_fwd - 2 - c_in
    out = defaultdict(dict)
    for w in words:
        if w.get('own'):
            out[w['inst']][NVL * w['origin']] = w['edge'] - c_out
        out[w['dst']][NVL * w['origin']] = w['land'] + c_in
    return out


def allgather(q, geo):
    """q = {inst: first own XQ edge on its line outputs}; geo = {inst: (col, tier)} + 'age' {(inst, side): line age},
    'partner' {inst: inst} -> (beats {(inst, side, edge): [src]}, collisions)"""
    occ = defaultdict(list)
    asm_own = defaultdict(list)
    by_ct = {v: k for k, v in geo['pos'].items()}

    def walk(inst, side, edge, hops, src):
        while hops >= 1:
            occ[(inst, side, edge)].append(src)
            if hops == 1:
                return
            col, t = geo['pos'][inst]
            nc = col + (1 if side == 'e' else -1)
            land = edge + geo['age'][(inst, side)]
            inst, edge, hops = by_ct[(nc, t)], land + LINE_STOP, hops - 1

    for inst, q0 in q.items():
        col, t = geo['pos'][inst]
        par = geo['partner'][inst]
        for j, d in enumerate(TRAIN):
            e = q0 + d
            src = (inst, j, 'own')
            asm_own[(inst, e)].append(src)
            if 7 - col:
                walk(inst, 'e', e, 7 - col, src)
            if col:
                walk(inst, 'w', e, col, src)
            ea = e + (V_ASM[inst] if isinstance(V_ASM, dict) else V_ASM)
            src = (inst, j, 'asm@' + par)
            asm_own[(par, ea)].append(src)
            if 7 - col:
                walk(par, 'e', ea, 7 - col, src)
            if col:
                walk(par, 'w', ea, col, src)
    col_line = {k: v for k, v in occ.items() if len(v) > 1}
    col_oa = {k: v for k, v in asm_own.items() if len(v) > 1}
    return occ, col_line, col_oa
