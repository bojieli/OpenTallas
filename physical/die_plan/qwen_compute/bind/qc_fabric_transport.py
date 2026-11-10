"""QC-TRANSPORT-FIX-3 11-08: bound-transport shape of the QC fabric and result stations (asbuilt.param_regen, opt-in).

Enabled only by asbuilt key qc_fabric_transport = true (the second QC switch): RTL defaults stay as built and a bind
without the key is unchanged.  Every value is derived from the bound depths of this plan (landed minus as-built per
crossing plus INNER intra-partition tree pads); nothing is a table.  Fail closed: an unreachable or non-uniform shape
raises (the bind reports PARAM_REGEN).

Fabric: a column head launches the 516-b corridor word; the Morton tree nodes of a cluster fault on any a/b valid
mismatch, so all tile return legs of a cluster must join on one edge.  N_PAD / S_PAD on qfd_dv_s5_xhead3 are the minimum
per-column head pads (per side, smallest total stages) that make every join of the near and far cluster of that side
balance.

Stations: E(r) = the stream arrival shift of the far S word.  SKEW_S / SKEW_N make the near word meet the far word in each
pair, HI_PAD delays the N pair sum so both pair sums meet (mode 1 and mode 2), and the region's result shifts by E(r).
RD_PAD / NB_PAD align r_d and nb_od at their shared-valid join (the valid comes from region 0 only).  NB_IN_PAD delays the
received neighbour word by E(r) - E(0) so that the mode-2 result keeps the same region shape as modes 0/1.  The bt_q return
needs no change when its lane shift equals E(r) - E(0); that is asserted."""

import re

SLICES = ["W5", "W4", "W3", "W2", "W1", "W0", "E0", "E1", "E2", "E3", "E4", "E5"]
HOST = {(1, 0): (1, 0), (1, 1): (0, 1), (1, 2): (2, 0), (1, 3): (3, 1), (1, 4): (0, 2), (1, 5): (0, 3), (1, 6): (3, 2),
        (1, 7): (3, 3), (2, 0): (1, 1), (2, 1): (2, 1), (2, 2): (1, 3), (2, 3): (2, 3), (3, 0): (2, 2), (3, 1): (1, 2),
        (4, 0): (0, 0)}
NEAR = {"S": 1, "N": 2}
FAR = {"S": 0, "N": 3}
PORT = {"S": ".s_d", "N": ".n_d"}
SKEW0 = 14                       # as-built near->far line of the station
W_HEAD, W_HI, W_RD, W_NB = 516, 74, 64, 66
MAX_COLUMN_PAD = 9
# DIE-QC-97 11-10 (COORD): u_scale_wait registered-read form (SCALE_ORQ = 1, PIN CYCLES 0) on the station regions of
# the sle_st_b_v2 types only (sl_E1/E3/E5_st_b = regions u_r4..u_r7 of dvs_E1/E3/E5): worst TT -364 ps there was the
# scale_wait macro -> g_sc multiplier with no flop.  asbuilt.qc_scale_orq (a list of leaf paths) overrides; [] = none.
SCALE_ORQ_LEAVES = [f"dvs_{s}.u_core.u_sub.u_r{r}" for s in ("E1", "E3", "E5") for r in range(4, 8)]


class CtxView:
    """Bound depths from the binder: delta = landed - as-built over the bits of a port, one value required."""
    def __init__(self, ctx):
        self.ctx = ctx
        self.index = ctx.cell_index()
        self.memo = {}

    def _bits(self, path, port):
        if (path, port) not in self.memo:
            self.memo[(path, port)] = self.ctx.timing_depths(path, port)
        return self.memo[(path, port)]

    def _leafs(self, d):
        if d["kind"] in ("or", "and"):
            for x in d["inputs"]:
                yield from self._leafs(x)
        elif d["kind"] in ("intra", "crossing"):
            yield d

    def delta(self, path, port, bits=None):
        if path not in self.index:
            raise ValueError(f"{path}: no such leaf")
        view = self._bits(path, port)
        v = set()
        for i, d in view.items():
            if bits is None or bits[0] <= i <= bits[1]:
                v |= {x["landed_stages"] - x["asbuilt_stages"] for x in self._leafs(d)}
        if len(v) > 1:
            raise ValueError(f"{path}.{port}{bits or ''}: shifts {sorted(v)} (one value required)")
        return v.pop() if v else 0

    def source(self, path, port):
        for d in self._bits(path, port).values():
            for x in self._leafs(d):
                return f"{x['source']}.{x['source_port']}"
        raise ValueError(f"{path}.{port}: no driver")


def _morton(i):
    c = r = 0
    for b in range(2):
        c |= ((i >> (2 * b)) & 1) << b
        r |= ((i >> (2 * b + 1)) & 1) << b
    return c, r


def start_shifts(view, s, k, pads):
    """Start shift of every tile of cluster k: head-column pad plus the column entry and tree-column landings."""
    cl = f"c16_{s}_{k}"
    src = view.source(f"{cl}.u_fab.u_x_0_0", "b_d")
    near = "u_xh" in src
    nb = None if near else int(src.split(".")[0].split("_")[-1])
    x = lambda c, name, rr: view.delta(f"{name}.u_fab.u_x_{c}_{rr}", "b_d")
    T = {}
    for c in range(4):
        for r in range(4):
            v = x(c, cl, 0) if near else x(c, f"c16_{s}_{nb}", 0) + x(c, f"c16_{s}_{nb}", 2) + x(c, cl, 0)
            if r >= 2:
                v += x(c, cl, 2)
            T[(c, r)] = v + pads[c]
    return T


def _cluster(view, s, k, pads):
    """Root shift and bad tree joins of cluster k, with per-column head pads."""
    cl = f"c16_{s}_{k}"
    T = start_shifts(view, s, k, pads)
    bad = []

    def out(lv, i):
        if lv == 0:
            return T[_morton(i)]
        h = HOST[(lv, i)]
        a = out(lv - 1, 2 * i) + view.delta(f"{cl}.u_t_{h[0]}_{h[1]}", "n_a")
        b = out(lv - 1, 2 * i + 1) + view.delta(f"{cl}.u_t_{h[0]}_{h[1]}", "n_b")
        if a != b:
            bad.append((lv, i, a, b))
        return max(a, b)

    return out(4, 0), bad


def _column_pads(view, s, side):
    import itertools
    near, far = NEAR[side], FAR[side]
    if PORT[side] not in view.source(f"c16_{s}_{near}.u_fab.u_x_0_0", "b_d"):
        raise ValueError(f"{s} {side}: cluster {near} is not the near cluster of this side")
    best = None
    for p in itertools.product(range(MAX_COLUMN_PAD + 1), repeat=4):
        if min(p) != 0 or (best is not None and sum(p) >= sum(best)):
            continue
        if not any(_cluster(view, s, k, p)[1] for k in (near, far)):
            best = p
    if best is None:
        raise ValueError(f"{s} {side}: no column pad up to {MAX_COLUMN_PAD} balances the tree")
    return best


def _heads(view, s, side):
    """column -> head leaf path, from the near cluster's column entries."""
    out = []
    for c in range(4):
        src = view.source(f"c16_{s}_{NEAR[side]}.u_fab.u_x_{c}_0", "b_d")
        if PORT[side] not in src or "u_xh" not in src:
            raise ValueError(f"{s} {side} column {c}: entry source {src} is not a head corridor")
        out.append(src.rsplit(".", 1)[0])
    return out


def derive(view):
    params, slices, flops = {}, {}, dict(head=0, hi=0, rd=0, nb_out=0, nb_in=0)
    for s in SLICES:
        pads = {side: _column_pads(view, s, side) for side in "SN"}
        for side in "SN":
            for c, head in enumerate(_heads(view, s, side)):
                if pads[side][c]:
                    params.setdefault(head, {})[f"{side}_PAD"] = pads[side][c]
                    flops["head"] += pads[side][c] * W_HEAD
        root = {}
        for side in "SN":
            for k, kind in ((NEAR[side], "near"), (FAR[side], "far")):
                r, bad = _cluster(view, s, k, pads[side])
                if bad:
                    raise ValueError(f"{s} cluster {k}: joins still unbalanced {bad}")
                root[side + kind] = r
        sub = f"dvs_{s}.u_core.u_sub"
        lane = dict(SL=view.delta(f"{sub}.u_frs", "rs_s", (0, 513)), SH=view.delta(f"{sub}.u_frs", "rs_s", (514, 1027)),
                    NL=view.delta(f"{sub}.u_fn", "rs_n", (0, 513)), NH=view.delta(f"{sub}.u_fn", "rs_n", (514, 1027)))
        rows = {}
        for r in range(8):
            u = f"{sub}.u_r{r}"
            sl = root["Snear"] + lane["SL"] + view.delta(u, "rs_s_lo_p")
            sh = root["Sfar"] + lane["SH"] + view.delta(u, "rs_s_hi_p")
            nl = root["Nnear"] + lane["NL"] + view.delta(u, "rs_n_lo_p")
            nh = root["Nfar"] + lane["NH"] + view.delta(u, "rs_n_hi_p")
            for data, ctrl, bits in (("rs_s_lo_p", "rs_s_c_p", (0, 1)), ("rs_s_hi_p", "rs_s_c_p", (2, 3)),
                                     ("rs_n_lo_p", "rs_n_c_p", (0, 1)), ("rs_n_hi_p", "rs_n_c_p", (2, 3))):
                if view.delta(u, data) != view.delta(u, ctrl, bits):
                    raise ValueError(f"{u}: {ctrl}{bits} shift differs from {data}")
            if sh < nh:
                raise ValueError(f"{u}: N pair later than S pair ({nh} > {sh}); the pad belongs on the S sum")
            sks, skn = SKEW0 + sh - sl, SKEW0 + nh - nl
            if not (3 <= sks <= 27 and 3 <= skn <= 27):
                raise ValueError(f"{u}: skew {sks}/{skn} outside the delay-line range 3..27")
            rows[r] = dict(SKEW_S=sks, SKEW_N=skn, HI_PAD=sh - nh, E=sh)
        rd = [rows[r]["E"] + view.delta(f"{sub}.u_ctl", "r_d", (64 * r, 64 * r + 63)) for r in range(8)]
        if rd[0] != max(rd):
            raise ValueError(f"{s}: r_d of region 0 is not the latest; its r_v would need a pad")
        has_nb = _has_port(view, f"{sub}.u_r0", "nb_d_p")
        nbo = [rows[r]["E"] + view.delta(f"{sub}.u_fup", "l9_c", (64 * r, 64 * r + 63)) for r in range(8)] \
            if _has_port(view, f"{sub}.u_fup", "l9_c") else None
        if nbo and nbo[0] != max(nbo):
            raise ValueError(f"{s}: nb_od of region 0 is not the latest; its nb_oc would need a pad")
        nb0 = view.delta(f"{sub}.u_r0", "nb_d_p") if has_nb else 0
        bt0 = view.delta(f"{sub}.u_r0", "bt_q_p")
        for r in range(8):
            u = f"{sub}.u_r{r}"
            row = rows[r]
            row["RD_PAD"] = max(rd) - rd[r]
            row["NB_PAD"] = max(nbo) - nbo[r] if nbo else 0
            row["NB_IN_PAD"] = 0
            if has_nb:
                row["NB_IN_PAD"] = (row["E"] - rows[0]["E"]) - (view.delta(u, "nb_d_p") - nb0)
                if row["NB_IN_PAD"] < 0:
                    raise ValueError(f"{u}: neighbour word arrives later than the region shape needs")
            if view.delta(u, "bt_q_p") - bt0 != row["E"] - rows[0]["E"]:
                raise ValueError(f"{u}: bt_q return shift differs from the region shift")
            params[u] = {k: row[k] for k in ("SKEW_S", "SKEW_N", "HI_PAD", "NB_IN_PAD", "RD_PAD", "NB_PAD")}
            flops["hi"] += row["HI_PAD"] * W_HI
            flops["rd"] += row["RD_PAD"] * W_RD
            flops["nb_out"] += row["NB_PAD"] * W_NB
            flops["nb_in"] += row["NB_IN_PAD"] * W_NB
        slices[s] = dict(column_pads=pads, roots=root, lanes=lane, regions=rows)
    return params, dict(rule=__doc__.split("\n\n")[0], slices=slices, added_flops=flops, added_flops_total=sum(flops.values()))


def _has_port(view, path, port):
    if hasattr(view, "has_port"):
        return view.has_port(path, port)
    ctx = view.ctx
    return port in ctx.F.cells[view.index[path]].ports


def scale_orq(params, record, index, leaves):
    """SCALE_ORQ = 1 on exactly the listed station leaves (fail closed on a missing or non-station path)."""
    for u in leaves:
        if u not in index or not re.fullmatch(r"dvs_[EW]\d\.u_core\.u_sub\.u_r[0-7]", u):
            raise ValueError(f"{u}: SCALE_ORQ leaf is not a bound station region")
        params.setdefault(u, {})["SCALE_ORQ"] = 1
    record["scale_orq"] = dict(leaves=sorted(leaves), added_flops=W_RD * len(leaves), pin_cycles=0)
    return params, record


def regen(ctx):
    if not ctx.ab.get("qc_fabric_transport"):
        return {}, None
    params, record = derive(CtxView(ctx))
    leaves = ctx.ab.get("qc_scale_orq", SCALE_ORQ_LEAVES)
    return scale_orq(params, record, ctx.cell_index(), leaves)
