#!/usr/bin/env python3
"""Stage programs, message contents and ISA-level pipeline model of a V4.1 ROM array.

    python3 tools/hdc_program_v41_array.py --out DIR --body N [--head-parts P] [--head-mcast]
                                           [--shared relay|mcast] [--balance]

Splits the V4.1 decode program (tools/hdc_program_v41.py) by layer ranges over
N body packages, each one V4.1 decode core, plus P vocabulary-split lm_head
packages (P = 0: the final norm and lm_head share the last body package).

WHAT CROSSES A PACKAGE BOUNDARY (per user and step).
* The hop (HIDDEN message) from a body package to the next carries the 4-copy
  hyper-connection residual H (640 FP32, 40 words) and one word of scalars:
  the residual's sum of squares SSX (the next layer's mix normaliser) and the
  pending pre-mix PF of the last FFN sublayer (the next attention sublayer's
  hc_pre weights).  Everything else a layer reads is recomputed or local.
* Shared compressed-KV and index state.  V4.1 layers share compressed KV rows
  (source layers 2/8/14/20 serve 2-7/8-13/14-19/20-39), index keys (the
  indexers at 24/28/32/36 read source 20's) and index selections (index
  sources 2/8/14/20/24/28/32/36 serve the layers up to the next one).  Each
  step a source appends at most one compressed row (32 FP32, FP4-QDQ'd) and
  one index key row (32), and an index source makes one selection (16 ids).
  A consumer package keeps its own copy of a source's compressed rows and
  index keys (appended each step), so the new row, not the history, crosses:
  - `relay` (point-to-point chain): the items ride in the hop after the
    scalars word, and every package between producer and last consumer
    forwards them (+2 words for a row, +1 for a selection);
  - `mcast` (switched fabric): the producing package sends one SIDE message
    with its items to a router multicast group of its consumer packages; each
    receiver's controller writes the payload into that user's staging slot
    (the per-user persistent segment) and the step starts only once the
    step's SIDE messages have arrived.
* Engram (layers 1 and 14): the hash reads the token history, so every
  package holding an Engram layer runs the hash itself; the token travels in
  the message header and the package restores the user's hash history (the
  last three compressed ids) before the step.
* lm_head: with P >= 2 the vocabulary splits over P packages; `chain`: part 0
  applies the final norm and forwards the normalised state (10 words) with its
  argmax, each part keeps the better (strictly greater logit, ties the lower
  row, as numpy); `--head-mcast`: the last body package multicasts the hop to
  all parts, each normalises and sends its argmax to package 0, which reduces.

PER-USER STATE.  A package's KV SRAM has a slice per user (the controller's
kv_base); the persistent vector-memory segment [PB, PB + PS) -- compressor
slots, compressed rows, SIDE staging -- has a per-user copy (the memory adds
user * PS); the Engram hash history is primed per user.

The ISA-level pipeline model runs the stage programs on one tools/
hdc_program_v41 Machine per (package, prompt), moving exactly the message
payloads between them, and checks every step's logits (all 4,040, bit for bit)
and argmax against hdc_golden_v41.Model.decode_token for two prompts.  The RTL
(tools/rtl_hdc_v41_array_campaign.py) is checked against the same images.
"""
import argparse
import copy
import json
from pathlib import Path

import numpy as np

import hdc_golden as G
import hdc_golden_v41 as V
import hdc_isa_v41 as I
import hdc_program_v41 as P

W = I.W_LANES
DY = I.DYN
PS = 16384                 # per-user persistent vector-memory segment (elements)
KVW = I.KV_WORDS           # per-user KV slice (words)
NGEN = 3
PARTS = (2, 4)             # vocabulary splits placed in the weight ROM
ITEM = {"ckv": 32, "ik": 32, "sel": 16}
SCAL_WORD = 40             # hop word of the scalars (SSX, PF): T[0..4]


NPMAX, SMAX = 8, 16        # prompt tokens and steps the RTL bench provisions per prompt


def prompts(length=NPMAX):
    """Two prompts: the oracle's, and its first eight generated ids (a
    different context, so per-user state mixing cannot go unseen); a shorter
    `length` takes a prefix of each."""
    prompt, expected = V.prompt_and_expected()
    return [list(prompt)[:length], list(expected[:len(prompt)])[:length]]


# -- partition -----------------------------------------------------------------------------
def split(m, n, weights=None):
    """n contiguous layer ranges; balanced by `weights` (cycles per layer) if given."""
    L = m.L
    if weights is None:
        b = [round(k * L / n) for k in range(n + 1)]
        return [list(range(b[k], b[k + 1])) for k in range(n)]
    cum = np.concatenate([[0], np.cumsum(weights)])
    b = [0]
    for k in range(1, n):
        target = cum[-1] * k / n
        j = int(np.argmin(np.abs(cum - target)))
        b.append(min(max(j, b[-1] + 1), L - (n - k)))
    b.append(L)
    return [list(range(b[k], b[k + 1])) for k in range(n)]


def consumers(m, item):
    kind, s = item
    out = []
    for L in range(m.L):
        if not m.ratio[L]:
            continue
        if kind == "ckv" and m.kv_of[L] == s:
            out.append(L)
        if kind == "sel" and m.idx_of[L] == s and L != s:
            out.append(L)
        if kind == "ik" and m.idx_of[L] == L and m.kv_of[L] == s and L != s:
            out.append(L)
    return out


def all_items(m):
    return [("ckv", s) for s in m.kv_src] + [("ik", s) for s in m.kv_src] + [("sel", i) for i in m.idx_src]


class Plan:
    """Packages, their programs' inputs and outputs, and the message topology."""

    def __init__(self, lay, body, head_parts=0, head_mcast=False, shared="relay"):
        m = self.m = lay.m
        self.lay = lay
        assert head_parts in (0, 1) + PARTS
        assert not (head_mcast and head_parts < 2)
        self.body = body
        self.nb, self.hp = len(body), head_parts
        self.n = self.nb + self.hp
        self.head_mcast, self.shared = head_mcast, shared
        self.pkg_of = {L: k for k, ls in enumerate(body) for L in ls}
        self.vocab = m.w["head.weight"].shape[0]
        V_ = lay.vm.map
        self.pb = V_["SLOT2"]
        assert V_["H"] == 0 and V_["T"] == SCAL_WORD * W        # the hop: H words, then T
        assert self.pb == min(a for a, _ in lay.vm_persist) and self.pb % 32 == 0
        # items crossing a boundary: produced below it, consumed at or above it
        live = [(it, consumers(m, it)) for it in all_items(m)]
        live = [(it, c) for it, c in live if c]
        self.inn, self.out = {}, {}              # package -> [(item, element address, region)]
        self.side = {}                           # producer package -> (payload words, consumer packages)
        stg = -(-lay.vm.top // 32) * 32          # SIDE staging, inside the per-user segment
        for k in range(self.n):
            self.inn[k], self.out[k] = [], []
        if shared == "relay":
            def hop_items(b):                    # items live across the boundary below package b
                first = body[b][0]
                return [it for it, c in live if it[1] < first and max(c) >= first]
            for k in range(1, self.nb):
                off = (SCAL_WORD + 1) * W
                for it in hop_items(k):
                    self.inn[k].append((it, V_["H"] + off, "T"))
                    self.out[k - 1].append((it, V_["H"] + off, "T"))
                    off += ITEM[it[0]] if it[0] != "sel" else W
        else:
            for q in range(self.nb):
                mine = [(it, c) for it, c in live if self.pkg_of[it[1]] == q and
                        any(self.pkg_of[L] != q for L in c)]
                if not mine:
                    continue
                off, dests = 0, set()
                for it, c in mine:
                    self.out[q].append((it, V_["IQ"] + off, "IQ"))
                    for L in c:
                        if self.pkg_of[L] != q:
                            self.inn[self.pkg_of[L]].append((it, stg + off, f"STG{q}"))
                            dests.add(self.pkg_of[L])
                    off += ITEM[it[0]] if it[0] != "sel" else W
                self.side[q] = dict(words=off // W, dests=sorted(dests), txb=V_["IQ"] // W, rxb=stg // W)
                stg += off
            for k in self.inn:                   # dedupe (an item consumed by several layers)
                self.inn[k] = list(dict.fromkeys(self.inn[k]))
            assert stg <= self.pb + PS
        self.check_outputs()

    def check_outputs(self):
        """An outgoing item is copied from the region the stage leaves it in:
        SEL / IKQ hold the stage's LAST index selection / index key row."""
        m = self.m
        for k, items in self.out.items():
            if k >= self.nb:
                continue
            last = self.body[k][-1]
            for (kind, s), _, _ in items:
                if kind == "sel":
                    assert s == max(i for i in m.idx_src if i <= last), (k, kind, s)
                if kind == "ik":
                    assert s == max(i for i in m.kv_src if i <= last), (k, kind, s)

    def role(self, k):
        """Stage k's program parameters: layers, embed, head spec, and messages."""
        nb, hp = self.nb, self.hp
        XN = self.lay.vm.map["XN"] // W
        side_in = sorted({reg for _, _, reg in self.inn[k] if reg.startswith("STG")})
        r = dict(layers=self.body[k] if k < nb else [], embed=k == 0, head=None, side_in=len(side_in),
                 rxb=0, rxw=0, txb=0, txw=0, hid_dest=-1, send_result=0, row0=0, combine=0,
                 side=self.side.get(k))
        hopw = SCAL_WORD + 1 + sum(ITEM[it[0]] // W if it[0] != "sel" else 1 for it, _, _ in self.out[k]) \
            if self.shared == "relay" else SCAL_WORD + 1
        if k < nb:
            if k > 0:
                r["rxw"] = self.tx_words(k - 1)
            if k < nb - 1 or hp >= 1:
                r["txw"], r["hid_dest"] = hopw, k + 1
                if k == nb - 1 and self.head_mcast:
                    r["hid_dest"] = "HEADS"
            if k == nb - 1 and hp == 0:
                r["head"], r["send_result"] = True, 1
        else:
            part = k - nb
            if hp == 1:
                r["head"] = True
            else:
                r["head"] = (part, hp)
                r["row0"] = part * (self.vocab // hp)
            if self.head_mcast or part == 0:
                r["rxw"] = self.tx_words(nb - 1)
            else:
                r["rxb"], r["rxw"], r["combine"] = XN, 10, 1
            if not self.head_mcast and hp >= 2 and part < hp - 1:
                r["txb"], r["txw"], r["hid_dest"] = XN, 10, k + 1
            else:
                r["send_result"] = 1
        return r

    def tx_words(self, k):
        if k < self.nb:
            if self.shared == "relay":
                return SCAL_WORD + 1 + sum(ITEM[it[0]] // W if it[0] != "sel" else 1 for it, _, _ in self.out[k])
            return SCAL_WORD + 1
        return 10

    def ehash(self, k):
        return k == 0 or any(L in self.m.engram.layer_ids for L in (self.body[k] if k < self.nb else []))

    def result_parts(self):
        return self.hp if (self.head_mcast and self.hp >= 2) else 1


# -- stage programs ------------------------------------------------------------------------
class StageBuilder(P.Builder):
    def copy(self, src, n, dst, reads, writes, tag, a_d=0, o_d=0, pred=0):
        self.su(reads, writes, tag, pred=pred, su_nout=1, su_nin=n, a_base=src, a_si=1, a_d=a_d, dst=I.DST_VM,
                o_base=dst, o_si=1, o_d=o_d)

    def rowsel(self, kind, s):
        r = self.m.ratio[s]
        if kind == "ckv":
            return DY["CKV2"] if r == 2 else DY["ROW"]
        return DY["N2M1"] if r == 2 else DY["POS"]

    def item_in(self, item, addr, region):
        kind, s = item
        V_, K = self.V, self.K
        t = f"hop.in.{kind}{s}"
        if kind == "ckv":
            self.copy(addr, 32, V_[f"CKV{s}"], {region}, {f"CKV{s}"}, t, o_d=self.rowsel(kind, s))
        elif kind == "ik":
            self.copy(addr, 32, V_["IKQ"], {region}, {"IKQ"}, t)
            self.kvt_write("IKQ", f"IK{s}", K[f"IK{s}"], self.rowsel(kind, s), t,
                           I.PRED_ODD if self.m.ratio[s] == 2 else 0)
        else:
            self.copy(addr, 16, V_["SEL"], {region}, {"SEL"}, t)

    def item_out(self, item, addr, region):
        kind, s = item
        V_ = self.V
        t = f"hop.out.{kind}{s}"
        if kind == "ckv":
            self.copy(V_[f"CKV{s}"], 32, addr, {f"CKV{s}"}, {region}, t, a_d=self.rowsel(kind, s))
        elif kind == "ik":
            self.copy(V_["IKQ"], 32, addr, {"IKQ"}, {region}, t)
        else:
            self.copy(V_["SEL"], 16, addr, {"SEL"}, {region}, t)

    def stage(self, plan, k):
        m, V_, lay = self.m, self.V, self.lay
        r = plan.role(k)
        T = V_["T"]
        if r["embed"]:
            self.xu(set(), {"EH"}, "embed", xu_op=I.XU_EHASH, xu_src=lay.cb["tmap"])
            self.su(set(), {"PF"}, "embed", su_nout=1, su_nin=4, a_src=I.SRC_CLO, a_base=lay.cb["pre0"], a_si=1,
                    dst=I.DST_VM, o_base=V_["PF"], o_si=1)
            self.su(set(), {"H", "SSX"}, "embed", su_nout=4, su_nin=160, a_src=I.SRC_WROM,
                    a_base=lay.emb_word * W * P.GR, a_d=DY["EMBED"], a_si=1, dst=I.DST_VM, o_base=V_["H"],
                    o_so=160, o_si=1, red=I.RED_SUM, red_sq=1, red_tree=1, r_base=V_["SSX"])
        else:
            if plan.ehash(k):
                self.xu(set(), {"EH"}, "hop.in", xu_op=I.XU_EHASH, xu_src=lay.cb["tmap"])
            if r["rxb"] == 0:                       # a hop: H arrived in place, the scalars in T[0..4]
                self.copy(T, 1, V_["SSX"], {"T"}, {"SSX"}, "hop.in")
                self.copy(T + 1, 4, V_["PF"], {"T"}, {"PF"}, "hop.in")
            for item, addr, region in plan.inn[k]:
                self.item_in(item, addr, region)
        for L in r["layers"]:
            if L in m.engram.layer_ids:
                self.engram(L)
            self.hc_mix_issue(L, "attn")
            self.hc_pre("PF", "X", f"L{L}.attn_norm", "SS")
            self.rmsnorm("X", 160, lay.cb[(L, "attn_norm")], "XN", f"L{L}.attn_norm", have_ss="SS")
            self.attention(L, hook=lambda: self.hc_mix_finish(L, "attn"))
            self.hc_post("Y", "POA", "CA", f"L{L}.hc_post")
            self.hc_mix_issue(L, "ffn")
            self.hc_pre("PA", "X", f"L{L}.ffn_norm", "SS")
            self.rmsnorm("X", 160, lay.cb[(L, "ffn_norm")], "XN", f"L{L}.ffn_norm", have_ss="SS")
            self.moe(L, hook=lambda: self.hc_mix_finish(L, "ffn"))
            self.hc_post("Y", "POF", "CF", f"L{L}.hc_post")
        head = r["head"]
        if head is not None:
            mat = lay.mat["head"] if head is True else lay.mat[("head",) + tuple(reversed(head))]
            if head is True or head[0] == 0 or plan.head_mcast:
                self.hc_pre("PF", "X", "head", "SS")
                self.rmsnorm("X", 160, lay.cb["norm"], "XN", "head", have_ss="SS")
            self.me(mat, V_["XN"], 0, {"XN"}, set(), "head", me_amax=1, me_oen=0)
        if r["txw"] and k < plan.nb:                # a body hop: scalars, then relayed items
            self.copy(V_["SSX"], 1, T, {"SSX"}, {"T"}, "hop.out")
            self.copy(V_["PF"], 4, T + 1, {"PF"}, {"T"}, "hop.out")
        for item, addr, region in plan.out[k]:
            self.item_out(item, addr, region)
        self.emit(dict(unit=I.UNIT_END, wait=31), set(), set(), "end")
        return P.schedule(self.prog)


def place_head_parts(lay):
    head = lay.m.w["head.weight"]
    n = head.shape[0]
    for parts in PARTS:
        assert n % parts == 0
        vp = n // parts
        for k in range(parts):
            lay.mat[("head", parts, k)] = lay.place(head[k * vp:(k + 1) * vp])


def stage_programs(plan):
    return [StageBuilder(plan.lay).stage(plan, k) for k in range(plan.n)]


# -- ISA-level pipeline model -----------------------------------------------------------------
def okey(v):
    b = int(G.bits(np.float32(v)))
    return (~b & 0xFFFFFFFF) if b >> 31 else (b | 0x80000000)


class Pipeline:
    """One Machine per package for one user; messages copy exactly the payload
    words the controllers move."""

    def __init__(self, plan, progs, base):
        self.plan, self.progs = plan, progs
        self.pk = []
        for _ in range(plan.n):
            mc = copy.copy(base)
            mc.vm = np.zeros(I.VM_ELEMS, dtype=np.float32)
            mc.kv = np.zeros(I.KV_WORDS * W, dtype=np.float32)
            mc.tokens, mc.eh, mc.argmax, mc.logits = [], None, None, []
            self.pk.append(mc)

    def hop(self, src, dst):
        rs, rd = self.plan.role(src), self.plan.role(dst)
        assert rs["txw"] == rd["rxw"], (src, dst, rs["txw"], rd["rxw"])
        a, b = rs["txb"] * W, rd["rxb"] * W
        self.pk[dst].vm[b:b + rd["rxw"] * W] = self.pk[src].vm[a:a + rs["txw"] * W]

    def side(self, q):
        s = self.plan.side[q]
        a, b, n = s["txb"] * W, s["rxb"] * W, s["words"] * W
        for d in s["dests"]:
            self.pk[d].vm[b:b + n] = self.pk[q].vm[a:a + n]

    def step(self, token, pos):
        """Returns (argmax, value bits, full logits) of the step."""
        plan = self.plan
        nb = plan.nb
        best = None
        parts = []
        for k in range(plan.n):
            if k > 0:
                src = nb - 1 if (k >= nb and (plan.head_mcast or k == nb)) else k - 1
                self.hop(src, k)
            self.pk[k].run(self.progs[k], token, pos)
            if k in plan.side:
                self.side(k)
            r = plan.role(k)
            if r["head"] is not None:
                mc = self.pk[k]
                idx = mc.argmax + r["row0"]
                val = mc.logits[mc.argmax]
                parts.append(mc.logits.copy())
                if best is None or okey(val) > okey(best[1]) or (okey(val) == okey(best[1]) and idx < best[0]):
                    best = (idx, val)
        return best[0], int(G.bits(np.float32(best[1]))), np.concatenate(parts)


def golden_runs(model, n_gen=NGEN, cache=None, prompt_len=NPMAX):
    """Per prompt: every step's input token, argmax, logit bits (golden)."""
    if cache:
        cache = Path(cache)
        if (prompt_len, n_gen) != (NPMAX, NGEN):
            cache = cache.with_name(f"{cache.stem}_p{prompt_len}g{n_gen}{cache.suffix}")
    if cache and cache.exists():
        return json.loads(cache.read_text())
    out = []
    for pr in prompts(prompt_len):
        st = model.new_state()
        seq, steps = list(pr), []
        for p in range(len(pr) + n_gen - 1):
            lg = model.decode_token(seq[p], p, st)
            a = int(np.argmax(lg))
            steps.append(dict(pos=p, input=int(seq[p]), argmax=a, logits=[int(x) for x in G.bits(lg)]))
            if p >= len(pr) - 1:
                seq.append(a)
        out.append(dict(prompt=pr, generated=seq[len(pr):], steps=steps))
    if cache:
        Path(cache).write_text(json.dumps(out))
    return out


def run_pipeline(plan, progs, base, gold):
    """Runs every prompt through the pipeline; returns per-prompt records and
    final package states."""
    recs, states = [], []
    for g in gold:
        pipe = Pipeline(plan, progs, base)
        exact, tok_ok = True, True
        for st in g["steps"]:
            a, vb, lg = pipe.step(st["input"], st["pos"])
            exact &= bool(np.array_equal(G.bits(lg), np.array(st["logits"], dtype=np.uint32)))
            tok_ok &= a == st["argmax"] and vb == st["logits"][st["argmax"]]
        recs.append(dict(logits_bit_exact_every_step=exact, argmax_and_value_every_step=tok_ok))
        states.append([(mc.kv.copy(), mc.vm[plan.pb:plan.pb + PS].copy()) for mc in pipe.pk])
    return recs, states


# -- images -----------------------------------------------------------------------------------
def write_roms(out, lay):
    out.mkdir(parents=True, exist_ok=True)
    P.write_images(out, lay, [dict(unit=I.UNIT_END, wait=31, _tag="end")])


def write_config(out, plan, progs, gold, states):
    out.mkdir(parents=True, exist_ok=True)
    for k, prog in enumerate(progs):
        words = [I.encode(**{a: v for a, v in f.items() if not a.startswith("_")}) for f in prog]
        (out / f"prog_stage{k:02d}.hex").write_text(P.hexwords(words, I.INSTR_BITS))
        (out / f"prog_stage{k:02d}_tags.txt").write_text("".join(f"{n} {f['_tag']}\n" for n, f in enumerate(prog)))
    npr = len(gold)
    steps = len(gold[0]["steps"])
    assert steps <= SMAX and len(gold[0]["prompt"]) <= NPMAX
    pad = [0] * len(gold[0]["steps"][0]["logits"])
    (out / "prompts.hex").write_text(P.hexwords(
        [t for g in gold for t in g["prompt"] + [0] * (NPMAX - len(g["prompt"]))], 16))
    (out / "expect_tokens.hex").write_text(P.hexwords(
        [s["argmax"] for g in gold for s in g["steps"] + [dict(argmax=0)] * (SMAX - steps)], 16))
    (out / "expect_logits.hex").write_text(P.hexwords(
        [x for g in gold for s in g["steps"] + [dict(logits=pad)] * (SMAX - steps) for x in s["logits"]], 32))
    for k in range(plan.n):
        for p in range(npr):
            kv, vm = states[p][k]
            (out / f"expect_kv{k:02d}_{p}.hex").write_text(P.hexwords(G.bits(kv), 32))
            (out / f"expect_vm{k:02d}_{p}.hex").write_text(P.hexwords(G.bits(vm), 32))
    return steps


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--roms", type=Path, help="also write the shared ROM images here")
    ap.add_argument("--body", type=int, default=2)
    ap.add_argument("--head-parts", type=int, default=0)
    ap.add_argument("--head-mcast", action="store_true")
    ap.add_argument("--shared", choices=("relay", "mcast"), default="relay")
    ap.add_argument("--gold-cache", type=Path)
    args = ap.parse_args()
    model = V.Model()
    lay = P.Layout(model)
    place_head_parts(lay)
    plan = Plan(lay, split(model, args.body), args.head_parts, args.head_mcast, args.shared)
    progs = stage_programs(plan)
    gold = golden_runs(model, cache=args.gold_cache)
    base = P.Machine(lay, np.zeros(I.KV_WORDS * W, dtype=np.float32), np.zeros(I.VM_ELEMS, dtype=np.float32))
    recs, states = run_pipeline(plan, progs, base, gold)
    print("stages", [len(p) for p in progs], "pipeline", recs)
    if args.roms:
        write_roms(args.roms, lay)
    if args.out:
        write_config(args.out, plan, progs, gold, states)
    return 0 if all(r["logits_bit_exact_every_step"] and r["argmax_and_value_every_step"] for r in recs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
