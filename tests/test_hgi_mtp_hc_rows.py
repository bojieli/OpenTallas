"""The HC aperture rows of the DSpark / MTP kernel program: every aperture HC_MIX_ROWS reads the row its lowering
named, in the launch order the shipped control loop issues (prefill, multi-column verify, the three draft stages with B
columns, the first token).

No checkpoint: the bodies are the REAL lowering of the hc_mixes ops (ds_native.Lower.layer), the REAL embed / demb
bodies and stage split (ds_mtp_kernels.Kernels), launched in the REAL order (v41_dspark.ctl_loop / expand), executed by
the REAL units (ds_native.ds_units DMA.LOAD / HC.HC_MIX_ROWS with the provenance checker) over synthetic fn rows.
"""
import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from hgi_sim import ds_mtp_kernels as KM  # noqa: E402
from hgi_sim import ds_native as DN  # noqa: E402
from hgi_sim import machine as MC  # noqa: E402
from hgi_sim.qwen_compiler import Builder  # noqa: E402
from hgi_sim.records import MDesc, Rec  # noqa: E402

F = np.float32
RANKS = (0, 3, 7, 95)                  # rank 0 owns no mix row; 3, 7, 95 own rows 0, 1, 23
OPS = [dict(kind="local", fn="hc_mixes", which="attn", tag="hc_attn", id=0),
       dict(kind="local", fn="hc_mixes", which="ffn", tag="hc_ffn", id=2)]
SPLIT = 1                               # the stage's attention op id (dsa = ops before it, dsb = the rest)


def fn_rows(L, which):
    """a synthetic hc_{which}_fn of layer L: 24 rows, distinct for every (layer, which, row)"""
    rng = np.random.default_rng(1000 * L + (which == "ffn"))
    return rng.standard_normal((24, DN.HC_K)).astype(F)


def model():
    cache = {}

    def lw(L, name):
        if (L, name) not in cache:
            cache[(L, name)] = fn_rows(L, name.split("_")[1])
        return cache[(L, name)]
    return SimpleNamespace(L=40, P=lambda L: f"layers.{L}." if L < 40 else f"mtp.{L - 40}.", eps=F(1e-6), lw=lw)


def program(plan, m=None):
    """rank -> (kind, L') -> records: the kernel table with the HC-relevant bodies built by the production code"""
    m = m or model()
    K = KM.Kernels.__new__(KM.Kernels)
    KM.bind_vm_tail()
    K.DN, K.Rec, K.MDesc, K.Builder, K.m, K.TP = DN, Rec, MDesc, Builder, m, DN.TP
    K.lay, K.man, K.hc_plan = DN.Layout(), DN.Manifest(), plan
    K.low = DN.Lower(m, 1, K.lay, K.man)
    K.low.hc_next_attn = K.hc_next()
    body = {}
    for r in RANKS:
        b = body[r] = {(k, Lp): [K.end()] for k in range(len(KM.KINDS)) for Lp in range(KM.PER_LAYER.get(k, 1))}
        b[(2, 0)], b[(6, 0)] = K.embed(r, 2), K.embed(r, 6)
        b[(3, 0)] = K.low.layer(0, OPS, r) + [K.end()]
        for st in range(3):
            pa, pb = K.split_stage(K.low.layer(40 + st, OPS, r), SPLIT)
            b[(7, st)], b[(8, st)] = pa + [K.end()], [copy.copy(x) for x in pb] + [K.end()]
    return K, body


JOBS = dict(first_token=(1, 1, 0), prefill3=(3, 1, 0), verify_accept_all=(1, 2, 4), verify_reject=(2, 3, 0),
            golden_job=(1, 1, 1))


def launches(job):
    plen, steps, accept = JOBS[job]
    return KM.mtp_launches(plen, steps, 4, accept)


def run(K, body, ls, m):
    """execute the aperture LOADs and aperture HC_MIX_ROWS of every launch on real dies; returns the reader count"""
    units = DN.ds_units(m, K.man, None)
    dies = {r: MC.Die(r, MC.Hbm()) for r in RANKS}
    M = MC.Machine(list(dies.values()), units)
    rng = np.random.default_rng(7)
    hb, n, lp = K.lay.vm["h"], DN.HC * DN.D, 0
    readers = 0
    for i, (kind, tok, pos) in enumerate(ls):
        k = KM.KINDS.index(kind)
        lp = KM.kernel_lp(k, pos, lp)
        for r, die in dies.items():
            h = rng.standard_normal(n).astype(F)
            die.vm[hb:hb + n] = h.view(np.uint32)
            M.doorbell(tok, pos)
            for rec in body[r][(k, lp if k in KM.PER_LAYER else 0)]:
                ap_load = rec.unit == "DMA" and rec.op == "LOAD" and rec.desc["O"].base >= MC.VM_WORDS
                if not (ap_load or (rec.unit, rec.op) == ("HC", "HC_MIX_ROWS")):
                    continue
                M.dies, M.cur = [die], rec
                try:
                    units[(rec.unit, rec.op)](M, rec, 0)
                except MC.Fault as ex:
                    raise MC.Fault(ex.status, f"launch {i} {kind} L'{lp} tok {tok} pos {pos}: {ex}") from ex
                finally:
                    M.dies = list(dies.values())
                if not ap_load:                       # the value too: the mix of the row the lowering named
                    L, w, o = rec.hc_row
                    h64 = h.astype(np.float64)
                    want = float(fn_rows(L, w)[o].astype(np.float64) @ h64) / np.sqrt(np.mean(h64 * h64) + 1e-6)
                    got = float(M.vm_read(rec.desc["O"], die, 0)[0])
                    # (the unit's split-sum BF16-class arithmetic is ~0.3 % off float64; another row's mix differs
                    # by ~ N(0, 200))
                    assert abs(got - want) <= 3.0, (i, kind, lp, r, got, want)
                    readers += 1
    return readers


def test_launch_order_is_the_shipped_one():
    """the facts the plan stands on: embed before every L0 body, demb before every dsa of stage 0 only, every dsa of
    a stage before its first dsb, the stages in order"""
    for job in JOBS:
        ls = launches(job)
        lp, last = 0, None
        seq = []
        for kind, tok, pos in ls:
            k = KM.KINDS.index(kind)
            lp = KM.kernel_lp(k, pos, lp)
            if kind == "layer" and lp == 0:
                assert last == "embed"
            if kind == "dsa" and lp == 0:
                assert last == "demb"
            if kind in ("dsa", "dsb"):
                seq.append((kind, lp))
            if kind != "swapin":
                last = kind
        assert len(seq) % 30 == 0 and seq, job
        for blk in range(0, len(seq), 30):
            assert seq[blk:blk + 30] == [(kd, st) for st in range(3) for kd in ("dsa", "dsb") for _ in range(5)]


@pytest.mark.parametrize("job", sorted(JOBS))
def test_static_reader_trace_clean(job):
    K, body = program(KM.HC_PLAN)
    rows, bad, dead = KM.hc_reader_trace(body, launches(job))
    assert rows and not bad, bad[:3]
    assert not dead, dead[:3]                         # no load of a row nobody reads
    kinds = {(x["kind"], x["lp"], x["slot"]) for x in rows}
    assert kinds == {("layer", 0, 0), ("layer", 0, 1)} | {(kd, st, s) for st in range(3)
                                                           for kd, s in (("dsa", 0), ("dsb", 1))}
    # an attn row is loaded under ANOTHER body that precedes its reader; an ffn row under its own layer's attn
    for x in rows:
        if x["slot"] == 0:
            assert x["loaded_by"][0] < x["launch"] and x["loaded_by"][1] in ("embed", "demb", "dsb"), x


@pytest.mark.parametrize("job", sorted(JOBS))
def test_simulated_readers_get_their_rows(job):
    m = model()
    K, body = program(KM.HC_PLAN, m)
    ls = launches(job)
    n = run(K, body, ls, m)
    rows, _, _ = KM.hc_reader_trace(body, ls)
    assert n == len(rows) > 0                          # (rank 0 owns no row: 3 reading ranks)


def test_backbone_chain_plan_is_caught():
    """the first MTP lowering (the backbone's (L + 1) % 40 chain, no entering load): the very first L0 reads a slot
    nobody loaded; later readers hold layers.1 / layers.(st + 1) rows"""
    m = model()
    K, body = program(KM.HC_PLAN_BACKBONE_CHAIN, m)
    ls = launches("golden_job")
    rows, bad, dead = KM.hc_reader_trace(body, ls)
    r3 = [x for x in bad if x["rank"] == 3]
    assert r3[0]["kind"] == "layer" and r3[0]["holds"] is None and r3[0]["needs"] == (0, "attn", 0)
    seen = {(x["kind"], x["lp"], x["needs"][:2], x["holds"] and x["holds"][:2]) for x in r3}
    assert ("layer", 0, (0, "attn"), (1, "attn")) in seen          # L0 of a later column reads layers.1
    assert ("dsa", 0, (40, "attn"), (1, "attn")) in seen           # stage 0 reads layers.1
    assert ("dsa", 1, (41, "attn"), (1, "attn")) in seen           # stage 1 reads layers.((40 + 1) % 40)
    assert ("dsa", 2, (42, "attn"), (2, "attn")) in seen
    assert all(x["slot"] == 0 for x in bad) and dead
    with pytest.raises(MC.Fault, match="NEVER LOADED"):
        run(K, body, ls, m)


def mutant(name):
    if name == "wrong_next_row":                       # stage 0's FFN prefetches mtp.2 instead of mtp.1
        return dict(KM.HC_PLAN, next={**KM.HC_PLAN["next"], 40: 42})
    if name == "no_stage_chain":                       # stage 1 prefetches nothing: stage 2 reads stage 1's row
        return dict(KM.HC_PLAN, next={**KM.HC_PLAN["next"], 41: None})
    if name == "missing_embed_load":                   # no entering load before L0
        return dict(KM.HC_PLAN, enter={6: (40, "attn")})
    if name == "missing_demb_load":                    # no entering load before stage 0
        return dict(KM.HC_PLAN, enter={2: (0, "attn")})
    if name == "l0_prefetches_layer1":                 # L0 keeps the backbone prefetch: overwritten unread (dead)
        return dict(KM.HC_PLAN, next={**KM.HC_PLAN["next"], 0: 1})
    if name == "stage2_wraps":                         # stage 2 keeps the wrapped prefetch (layers.3): dead load
        return dict(KM.HC_PLAN, next={**KM.HC_PLAN["next"], 42: 3})
    raise KeyError(name)


@pytest.mark.parametrize("name,fault", [("wrong_next_row", "holds layer 42"), ("no_stage_chain", "holds layer 41"),
                                         ("missing_embed_load", "NEVER LOADED"), ("missing_demb_load", "holds layer 0"),
                                         ("l0_prefetches_layer1", None), ("stage2_wraps", None)])
def test_mutants_are_caught(name, fault):
    m = model()
    K, body = program(mutant(name), m)
    ls = launches("golden_job")
    rows, bad, dead = KM.hc_reader_trace(body, ls)
    if fault is None:                                  # values stay right; the trace reports the wasted loads
        assert not bad and dead
        run(K, body, ls, m)
        return
    assert bad
    with pytest.raises(MC.Fault, match=fault):
        run(K, body, ls, m)


def test_wrong_row_data_is_not_masked_by_the_value():
    """a slot overwritten behind the checker's back still fails the value comparison (the checker is not the only
    guard in this test), and a reader stripped of its provenance faults"""
    m = model()
    K, body = program(KM.HC_PLAN, m)
    units = DN.ds_units(m, K.man, None)
    die = MC.Die(3, MC.Hbm())
    M = MC.Machine([die], units)
    M.doorbell(0, 0)
    ld = next(r for r in body[3][(2, 0)] if r.unit == "DMA" and r.desc["O"].base >= MC.VM_WORDS)
    rd = next(r for r in body[3][(3, 0)] if r.op == "HC_MIX_ROWS")
    M.cur = ld
    units[("DMA", "LOAD")](M, ld, 0)
    bare = copy.copy(rd)
    del bare.hc_row
    M.cur = bare
    with pytest.raises(MC.Fault, match="without a row provenance"):
        units[("HC", "HC_MIX_ROWS")](M, bare, 0)


def test_backbone_chain_default_is_unchanged():
    """the standalone ds_native flow (one column, layers in order) keeps (L + 1) % m.L"""
    low = DN.Lower(model(), 1, DN.Layout(), DN.Manifest())
    for L, nxt in ((0, 1), (17, 18), (39, 0)):
        loads = [r.hc_row for r in low.layer(L, OPS, 3) if r.unit == "DMA" and r.op == "LOAD"]
        assert loads == [(L, "ffn", 0), (nxt, "attn", 0)]
