"""DeepSeek-V4.1-Flash on r25: the existing TP-96 command stream re-expressed through the interface, and its unit
handlers.

SOURCE STREAM.  The DS HBM accelerator's executed program is tools/w19_hbm_tp96_isa.py's Compiler output (variant
oreduce; committed as results/rtl/dshbm_baseline_measured_20261004/program.json, the program every DS HBM composition
walks).  `lower_ops` turns each of its ops into one interface command (unit, op family, mode fields, operand
references), with nothing left implicit: the W19 driver's `split_ea` step becomes operand slices `ea[lo:hi]` of the
w2 matvecs, the expert-slot weight indirection becomes the SM `slot=expert` mode, the matvec arithmetic class becomes
the SM weight-decode / activation / output modes.

HANDLERS.  `handlers(...)` maps (unit, op) to the unit's arithmetic:
  SM.MATVEC   the SM's modes on the die's own rows: fp8_bd / fp4_bd (hdc_golden_v41.linear_q: FP8 k32 activation,
              exact block dots, csum), bf16 (matvec_c csum, FP32 or BF16 out), grouped (group1024) and K-split
              (head512) wo_a -- implemented here from the golden primitives;
  COLL.*      gather / owner-tree reduce / merge / KV row gather -- implemented here (ownership checked);
  HBM.*       expert fetch (byte accounting) -- implemented here;
  *.DS        the dedicated units (HC, NORM, IDX, SEL, ATT, SU/SFU fused DS chains): the golden's own function of the
              unit on the die's buffers, reached through tools/w19_hbm_tp96_isa.Executor's f_<fn> (the golden
              library; its arguments are rebuilt from the command's mode and args fields, so a field the interface
              drops breaks the result).
"""
from __future__ import annotations

import numpy as np

from . import tp96_ir as iface
from .tp96_ir import Defect, Die

F = np.float32

# fn -> (unit, the buffers it reads, the buffers it writes); buffers matter only for the timing replay's deps
DS_FN = {
    "hc_mixes": ("HC", ["h"], ["{w}_pre", "{w}_post", "{w}_comb", "{w}_res"]),
    "hc_pre_norm": ("NORM", ["h", "pre"], ["x", "{w}_x"]),
    "final_norm": ("NORM", ["h", "pre"], ["x"]),
    "q_norm_kv_row": ("SU", ["qa", "kvraw"], ["qr", "win_new"]),
    "q_rope": ("SU", ["q"], ["q_own"]),
    "compressor": ("SU", ["cmp"], ["new_ik", "new_ckv"]),
    "engram_mix": ("SU", ["h", "eg_kv"], ["h", "engram_h"]),
    "moe_sum": ("SU", ["e0.d", "e1.d", "e2.d", "e3.d", "e4.d", "e5.d", "e6.d"], ["yf"]),
    "router_act": ("SFU", ["gsc"], ["gsc"]),
    "swiglu": ("SFU", ["e{slot}.g", "e{slot}.u", "route_w"], ["ea"]),
    "index_q": ("IDX", ["iq", "iwr"], ["iqf", "iw"]),
    "index_scores": ("IDX", ["iqf", "iw"], ["is_i", "is_v"]),
    "cand_mask": ("IDX", ["is_i", "is_v"], ["is_v"]),
    "topk_local": ("SEL", ["is_i", "is_v"], ["sel_v", "sel_i"]),
    "route": ("SEL", ["gsc"], ["router", "route_ids", "route_w"]),
    "cand_local": ("SEL", ["is_i", "is_v"], ["cand_v", "cand_i", "cand_blocks"]),
    "cand_apply": ("SEL", ["cand_mv", "cand_mi", "cand_blocks"], ["cand_keep"]),
    "attend": ("ATT", ["q_own", "sel_rows"], ["o", "o_own"]),
    "hc_post": ("HC", ["y", "{w}_res", "{w}_post", "{w}_comb"], ["h", "pre"]),
    "argmax_local": ("ARGMAX", ["logits"], ["argmax_v", "argmax_i"]),
    "engram_fetch": ("HBM", [], ["eg_rows"]),
}
DS_UNIT_OP = {"HBM": "ENGRAM_ROWS", "ARGMAX": "DS"}
_LOCAL_ARGS = ("which", "slot", "n", "src", "k", "group", "closes", "yarn")


def _sm_modes(op):
    fn, fmt = op["fn"], op["fmt"]
    mode = dict(acc="csum8", ksplit="none", slot="none")
    if fn == "linear_q":
        mode.update(wfmt={"fp8": "fp8_bd", "fp4": "fp4_bd"}[fmt], act="fp8_k32", out="bf16")
    elif fn == "mv":
        mode.update(wfmt="bf16", act="bf16", out="fp32")
    elif fn == "linear_bf16":
        mode.update(wfmt="bf16", act="bf16", out="bf16")
    elif fn == "wo_a":
        mode.update(wfmt="bf16", act="bf16", out="bf16", ksplit="group1024")
    elif fn == "wo_a_part":
        mode.update(wfmt="bf16", act="bf16", out="fp32", ksplit="head512")
    else:
        raise ValueError(fn)
    w = op["w"]
    if isinstance(w, (list, tuple)) and len(w) == 2 and isinstance(w[0], int):
        mode["slot"] = "expert"
    return mode


def lower_ops(ops, prog: iface.Program, k_exp=6):
    """Append the interface commands of one layer's (or the head's) W19 op list to prog."""
    for op in ops:
        k, L = op["kind"], op["layer"]
        if k == "mv":
            mode = _sm_modes(op)
            w = op["w"]
            x = op["x"]
            if isinstance(x, str) and x.startswith("ea") and x[2:].isdigit():      # W19 split_ea -> operand slice
                e = int(x[2:])
                x = f"ea[{e * 2304}:{(e + 1) * 2304}]"
            args = dict(w=list(w) if isinstance(w, (list, tuple)) else w, n=op["n"], k=op["k"], rows=op["rows"])
            prog.add(unit="SM", op="MATVEC", mode=mode, ranks="all", src=[x], dst=[op["out"]], args=args, layer=L,
                     tag=op["tag"])
        elif k == "local":
            fn = op["fn"]
            unit, rd, wr = DS_FN[fn]
            w = op.get("which", "")
            fill = dict(w=w, slot=op.get("slot", 0))
            args = {a: op[a] for a in _LOCAL_ARGS if a in op}
            prog.add(unit=unit, op=DS_UNIT_OP.get(unit, "DS") if unit in ("HBM",) else "DS",
                     mode={} if unit == "HBM" else dict(fn=fn), ranks=op["ranks"],
                     src=[b.format(**fill) for b in rd], dst=[b.format(**fill) for b in wr], args=args, layer=L,
                     tag=op["tag"])
        elif k == "all_gather":
            prog.add(unit="COLL", op="GATHER", mode={}, ranks="all", src=list(op["bufs"]), dst=list(op["bufs"]),
                     args=dict(dest=op["dest"], elems=op["elems"], bytes=op["bytes"]), layer=L, tag=op["tag"])
        elif k == "all_reduce":
            prog.add(unit="COLL", op="REDUCE", mode=dict(tree="pairwise", round=op["round"]), ranks="all",
                     src=[op["buf"]], dst=[op["out"]],
                     args=dict(groups=op["groups"], per_group=op["per_group"], elems=op["elems"], bytes=op["bytes"],
                               dest=op["dest"]), layer=L, tag=op["tag"])
        elif k == "topk_merge":
            w = op["what"]
            dst = ["token"] if w == "argmax" else [f"{w}_mv", f"{w}_mi"] + (["sel"] if w == "sel" else [])
            prog.add(unit="COLL", op="MERGE", mode=dict(what=w), ranks="all", src=[f"{w}_v", f"{w}_i"], dst=dst,
                     args=dict(k=op["k"], elems=op["elems"], bytes=op["bytes"]), layer=L, tag=op["tag"])
        elif k == "kv_gather":
            prog.add(unit="COLL", op="KV_GATHER", mode={}, ranks="all", src=["sel"], dst=["sel_rows"],
                     args=dict(src=op["src"], dest=op["dest"], elems=op["elems"], bytes=op["bytes"]), layer=L,
                     tag=op["tag"])
        elif k == "expert_fetch":
            prog.add(unit="HBM", op="EXPERT_FETCH", mode={}, ranks="all", src=["route_ids"], dst=["expert_w"],
                     args=dict(experts=op["experts"]), layer=L, tag=op["tag"])
        else:
            raise ValueError(k)
    return prog


def model_descriptor(m=None, pos=None):
    d = dict(model="DeepSeek-V4.1-Flash", tp=96, head_dies=64, key_block=8, dim=5120, hc=4, layers=40, vocab=129280,
             experts_per_token=6, shared_experts=1, attn_heads=64, head_dim=512, context=1048576)
    if pos is not None:
        d["position"] = pos
    if m is not None:
        d.update(ratio=[int(r) for r in m.ratio], kv_of={str(k): int(v) for k, v in m.kv_of.items()},
                 idx_of={str(k): int(v) for k, v in m.idx_of.items()}, window=int(m.window))
    return d


# ----------------------------------------------------------------------------------------------------------------
# handlers
# ----------------------------------------------------------------------------------------------------------------
class DSDie(Die):
    def __init__(self, r):
        super().__init__(r)
        self.win, self.sel_rows, self.cand = {}, {}, None


def handlers(W, golib):
    """W: the tools/w19_hbm_tp96_isa module (its golden imports G, V); golib: a W.Executor bound to the model,
    state, position and token history (the golden library of the dedicated units)."""
    G, V = W.G, W.V
    m = golib.m

    def weight(name, r0, r1):
        return golib.wrows(name, r0, r1)

    def sm_matvec(M, c):
        md, a = c.mode, c.args
        if V.ARITH != "chunk8" or md["acc"] != "csum8":
            raise Defect("SM csum8 mode needs the chunk8 arithmetic contract")
        L = c.layer
        w = a["w"]
        for d in M.dies:
            r0, r1 = a["rows"][d.r]
            if r1 <= r0:
                continue
            name = golib.expert_name(w[0], w[1], L) if md["slot"] == "expert" else w
            x = d.ref(c.src[0])
            if md["ksplit"] == "group1024":                  # row n of group n // 1024 reads x[g * 4096 ...]
                full = m.w[name]
                out = np.empty(r1 - r0, dtype=F)
                for g in range(r0 // 1024, (r1 - 1) // 1024 + 1):
                    lo, hi = max(r0, g * 1024), min(r1, (g + 1) * 1024)
                    out[lo - r0:hi - r0] = V.matvec_c(full[lo:hi], x[g * 4096:(g + 1) * 4096], V.WO_A_SPLIT)
            elif md["ksplit"] == "head512":                  # the die's head (512 inputs) against its group's rows
                j = d.r % 8
                out = V.csum(G.mul(np.asarray(m.w[name][r0:r1, j * 512:(j + 1) * 512], dtype=F),
                                   G.to_bf16(x)[None, :]))
            else:
                wr = weight(name, r0, r1)
                if md["wfmt"] in ("fp8_bd", "fp4_bd"):
                    if md["act"] != "fp8_k32" or md["out"] != "bf16":
                        raise Defect("block-dot SM modes take FP8 k32 activations and give BF16")
                    out = V.linear_q(wr, x)
                elif md["wfmt"] == "bf16":
                    out = V.mv(wr, G.to_bf16(x) if md["out"] == "bf16" else x)
                else:
                    raise Defect(f"DS has no {md['wfmt']} weights")
            if md["out"] == "bf16" and md["wfmt"] == "bf16":
                out = G.to_bf16(out)
            d.put(c.dst[0], out, lo=r0, n=a["n"])

    def ds_local(M, c):
        fn = c.mode["fn"]
        op = dict(layer=c.layer, fn=fn, **c.args)
        f = getattr(golib, "f_" + fn)
        for d in M.ranks_of(c.ranks):
            f(d, op)

    def hbm_engram(M, c):
        op = dict(layer=c.layer, fn="engram_fetch", **c.args)
        for d in M.ranks_of(c.ranks):
            golib.f_engram_fetch(d, op)

    def coll_gather(M, c):
        for name in c.src:
            seg = [(d.r, d.ok[name].copy(), d.mem[name].copy()) for d in M.dies if name in d.mem]
            if not seg:
                raise Defect(f"cmd {c.id}: gather of {name} that no die wrote")
            n = seg[0][2].size
            full = np.zeros(n, dtype=seg[0][2].dtype)
            have = np.zeros(n, dtype=bool)
            for r, ok, v in seg:
                if v.size != n:
                    raise Defect(f"cmd {c.id}: {name} has different extents on different dies")
                if (have & ok).any():
                    raise Defect(f"cmd {c.id}: {name} written by two dies")
                full[ok] = v[ok]
                have |= ok
            if not have.all():
                raise Defect(f"cmd {c.id}: gather of {name} with {int((~have).sum())} elements unwritten")
            for d in M.ranks_of(c.args["dest"]):
                d.put(name, full, n=n)

    def coll_reduce(M, c):
        a = c.args
        n, per = a["elems"], a["per_group"]
        span = n // a["groups"]
        z = np.zeros(n, dtype=F)
        for g in range(a["groups"]):
            parts = [M.dies[g * per + j].get(c.src[0], g * span, (g + 1) * span) for j in range(per)]
            while len(parts) > 1:                            # owner tree, rank order
                parts = [G.add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
            z[g * span:(g + 1) * span] = parts[0]
        if c.mode["round"] == "bf16":
            z = G.to_bf16(z)
        for d in M.ranks_of(a["dest"]):
            d.put(c.dst[0], z, n=n)

    def coll_merge(M, c):
        what = c.mode["what"]
        v = np.concatenate([d.get(f"{what}_v") for d in M.dies])
        i = np.concatenate([d.get(f"{what}_i") for d in M.dies]).astype(np.int64)
        order = np.lexsort((i, -v.astype(np.float64)))           # value descending, lowest index first
        if what == "argmax":
            for d in M.dies:
                d.put("token", np.array([i[order[0]]], dtype=np.int64))
            return
        order = order[:c.args["k"]]
        for d in M.dies:
            d.put(f"{what}_mv", v[order].astype(np.float64), n=len(order))
            d.put(f"{what}_mi", i[order], n=len(order))
        if what == "sel":
            s = np.sort(i[order])
            for d in M.dies:
                d.put("sel", s, n=len(s))

    def coll_kv_gather(M, c):
        s = c.args["src"]
        sel = M.dies[0].get("sel").astype(np.int64)
        own = W.key_owner(sel)
        rows = np.empty((len(sel), m.hd), dtype=F)
        filled = np.zeros(len(sel), dtype=bool)
        for d in M.dies:                                      # each owner contributes only rows it holds
            mine = own == d.r
            rows[mine] = golib.st.ckv[s][sel[mine]]
            filled |= mine
        if not filled.all() or np.isnan(rows).any():
            raise Defect(f"cmd {c.id}: a selected compressed row has no owner or was never written")
        for d in M.ranks_of(c.args["dest"]):
            d.sel_rows[s] = rows.copy()

    def hbm_expert_fetch(M, c):
        ids = golib.route_ids
        if len(ids) != c.args["experts"]:
            raise Defect(f"cmd {c.id}: route register holds {len(ids)} ids, descriptor {c.args['experts']}")

    h = {("SM", "MATVEC"): sm_matvec, ("COLL", "GATHER"): coll_gather, ("COLL", "REDUCE"): coll_reduce,
         ("COLL", "MERGE"): coll_merge, ("COLL", "KV_GATHER"): coll_kv_gather,
         ("HBM", "EXPERT_FETCH"): hbm_expert_fetch, ("HBM", "ENGRAM_ROWS"): hbm_engram}
    for u in ("SU", "SFU", "NORM", "HC", "ATT", "IDX", "SEL", "ARGMAX"):
        h[(u, "DS")] = ds_local
    return h
