"""HG-SPLIT 11-03 (DIE-KV-64 ruling, EX join fix): the ASTK ep EX-lane parameters from the BOUND lanes.

Each qkd_astk_ep_s_e / qkd_astk_ep_s_head_e sends one xa word to each of its four qkd_astk_ex_s (lane k = g_ex_k) and joins
their xe words at tb_sr[DT-1].  When a die-plan cut puts EX lane k in another partition, bind registers the leg both ways
(u_bout / u_bin, + ft stations / landing): EX_ADD_k = depth(ep.xa -> ex_k.xa) + depth(ex_k.xe -> ep.xe[34k +: 34]).
The variant pads every lane to EXM = max(EX_PAD, EX_ADD_k) and raises DT by EXM.  EX_PAD = the die-wide max, so every
ep of a chain keeps one DT (the zi / zo join and the compiler's exp_age floor stay uniform: + EX_PAD).
No ep with a registered EX leg (every plan before the HG split): no parameter is set, the bound RTL is unchanged.
Fail closed (bind PARAM_REGEN error): a leg whose bits land at different non-zero depths, or a valid bit (xa[0],
xe[34k], xe[34k+1]) off the leg depth."""
import re

EP = ("qkd_astk_ep_s_e", "qkd_astk_ep_s_head_e")


def _leg(ctx, path, port, lo, n, valid, what):
    d = ctx.depth(path, port)
    bits = [d[i] for i in range(lo, lo + n)]
    nz = sorted(set(b for b in bits if b))
    if len(nz) > 1:
        raise ValueError(f"{what}: {path}.{port}[{lo + n - 1}:{lo}] lands at depths {nz} (one depth per EX leg)")
    leg = nz[0] if nz else 0
    for v in valid:
        if d[v] != leg:
            raise ValueError(f"{what}: valid bit {path}.{port}[{v}] at depth {d[v]} != leg depth {leg}")
    return leg


def ex_join(ctx):
    idx = ctx.cell_index()
    eps = sorted(c.path for c in ctx.F.cells if c.kind == "leaf" and c.module in EP)
    table = {}
    for ep in eps:
        m = re.fullmatch(r"(.*)u_ep", ep)
        if not m:
            raise ValueError(f"ep path {ep} does not end in u_ep")
        sep = "." if m.group(1).endswith(".") else "__"
        stem = m.group(1)[:-len(sep)] if m.group(1).endswith(sep) else m.group(1)
        adds = []
        for k in range(4):
            ex = f"{stem}{sep}g_ex_{k}{sep}u_ex"
            if ex not in idx:
                raise ValueError(f"ep {ep}: EX lane {k} leaf {ex} not found")
            out = _leg(ctx, ex, "xa", 0, 66, [0], f"EX{k} xa")
            back = _leg(ctx, ep, "xe", 34 * k, 34, [34 * k, 34 * k + 1], f"EX{k} xe")
            adds.append(out + back)
        table[ep] = adds
    pad = max([max(a) for a in table.values()] + [0])
    if pad == 0:
        return {}, dict(eps=len(eps), ex_pad=0, note="no registered EX leg: no parameter set (bound RTL unchanged)")
    params = {ep: dict({f"EX_ADD{k}": a[k] for k in range(4)}, EX_PAD=pad) for ep, a in table.items()}
    crossed = {ep: a for ep, a in table.items() if any(a)}
    return params, dict(eps=len(eps), ex_pad=pad, crossed=len(crossed), ex_add=table,
                        calendar="ep DT and cal_bad floor (exp_age > DT + 16) rise by EX_PAD on every ep; "
                                 "the ep zo / xo results leave EX_PAD edges later")
