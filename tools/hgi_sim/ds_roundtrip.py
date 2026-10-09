#!/usr/bin/env python3
"""DS round-trip: the existing TP-96 DeepSeek-V4.1 command stream through the r25 interface, executed in the
simulator, checked bit for bit against the released-checkpoint golden at position 1,048,575 (1M context).

    HDC_V41_ARITH=chunk8 python3 -m hgi_sim.ds_roundtrip --layers 0-39 --head --out REC.json   (from tools/)

Per layer:
  1. the W19 compiler emits the layer's op list (variant oreduce); it must equal the committed executed program
     (results/rtl/dshbm_baseline_measured_20261004/program.json) -- the source stream is the one every DS HBM
     composition walks;
  2. tools/hgi_sim/ds.lower_ops re-expresses it as interface commands; the program is encoded, decoded, and
     re-encoded (byte-identical), and ONLY the decoded program is executed;
  3. the simulator runs it on 96 dies (functional mode) and every region the W19 run checks (attn_norm, window row,
     attention, ffn_norm, router, ffn, block output, hc pre, compressed rows, index scores, selection, experts) is
     compared bit for bit with the golden shard of the W17 reference token; the head's logits digest and next token
     are compared with the reference.
Needs the released checkpoint (OT_V41_FLASH_SNAPSHOT or the HF cache) and the W17 reference shards.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import w19_hbm_tp96_isa as W  # noqa: E402
from hgi_sim import ds  # noqa: E402
from hgi_sim import tp96_ir as iface  # noqa: E402
from hgi_sim.tp96_ir import Defect, OpMachine as Machine  # noqa: E402

PROGRAM = ROOT / "results/rtl/dshbm_baseline_measured_20261004/program.json"
SCHEMA = "opentallas.hgi_sim.ds_roundtrip.v1"
VARIANT = "oreduce"


def canon(x):
    return json.loads(json.dumps(x, default=list))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def lockstep_compare(ex, M, cmd):
    """After op i of the W19 executor and command i of the simulator: every buffer of every die, bitwise."""
    bad = []
    for rk, d in zip(ex.ranks, M.dies):
        for name, v in rk.mem.items():
            if name.startswith("ea") and name[2:].isdigit():
                continue                                  # W19's split_ea copies; the simulator reads ea[lo:hi]
            if name not in d.mem:
                bad.append((d.r, name, "missing"))
                continue
            a, b = np.asarray(v), np.asarray(d.mem[name])
            okm = rk.ok[name]
            if a.shape != b.shape or not np.array_equal(okm, d.ok[name]) or \
                    not np.array_equal(a.view(np.uint8) if a.dtype != object else a,
                                       b.view(np.uint8) if b.dtype != object else b):
                bad.append((d.r, name, "differs"))
        for L, w in rk.win.items():
            if L not in d.win or not np.array_equal(w.view(np.uint32), d.win[L].view(np.uint32)):
                bad.append((d.r, f"win{L}", "differs"))
        for s, w in rk.sel_rows.items():
            if s not in d.sel_rows or not np.array_equal(w.view(np.uint32), d.sel_rows[s].view(np.uint32)):
                bad.append((d.r, f"sel_rows{s}", "differs"))
        if rk.cand != d.cand:
            bad.append((d.r, "cand", "differs"))
    return bad


def run(layers, head, log=print, refs=None, lockstep=False):
    refs = Path(refs) if refs else W.REF_SHARDS
    ref = json.loads(W.REF_RECORD.read_text())
    ctx, seed = ref["context"], ref["seed"]
    pos = ctx - 1
    hist = list(ref["token_history"])
    committed = {str(l["layer"]): l["ops"] for l in json.loads(PROGRAM.read_text())["layers"]}
    ck = W.LC.Checkpoint()
    m, init_sha = W.LC.build_model(ck, engram=any(L in (1, 14) for L in layers))
    t1 = time.time()
    st = W.State(m, ctx, seed, set(layers))
    log(f"state built {time.time() - t1:.0f} s: {st.n}")
    state_check = None
    if set(layers) == set(range(m.L)):
        want = json.loads(ref["state"].replace("'", '"')) if isinstance(ref["state"], str) else ref["state"]
        state_check = dict(state_sha256=st.state_sha256, record=want.get("state_sha256"),
                           match=st.state_sha256 == want.get("state_sha256"))
        if not state_check["match"]:
            raise SystemExit("synthetic state digest mismatch")
    golib = W.Executor(m, st, pos, hist, VARIANT, log)          # the golden library of the dedicated units
    M = Machine(W.TP, ds.handlers(W, golib), head_dies=W.HEAD_DIES, die_cls=ds.DSDie)
    ex = None
    if lockstep:                    # the W19 executor itself, on its own copy of the state, op for op
        ex = W.Executor(m, W.State(m, ctx, seed, set(layers)), pos, hist, VARIANT, log)
    first = layers[0]
    if first == 0:
        h = np.repeat(ck.rows("embed.weight", [hist[-1]]), m.hc, axis=0).astype(W.F)
        pre = np.array([1, 0, 0, 0], dtype=W.F)
    else:
        prev = np.load(refs / f"ctx{ctx}_L{first - 1:02d}.npz")
        h, pre = prev["h_out"], prev["pre_out"]
        carry = json.loads((refs / f"ctx{ctx}_L{first - 1:02d}.json").read_text())["ctx_out"]
        for s in m.kv_src:
            if s < first and s in st.n:
                z = np.load(refs / f"ctx{ctx}_L{s:02d}.npz")
                if f"ckv{s}" in z.files:
                    g = st.n[s]
                    st.ckv[s][g], st.ik[s][g] = z[f"ckv{s}"], z[f"ik{s}"]
                    st.n[s] = g + 1
                    st.slots[s] = {}
        if "sel" in carry:
            for d in M.dies:
                d.put("sel", np.array(carry["sel"], dtype=np.int64))
        if "cand_file" in carry:
            cand = np.load(refs / carry["cand_file"])["cand"]
            for d in M.dies:
                nb = -(-len(cand) // W.KEY_BLOCK)
                d.cand = {int(b): bool(cand[b * W.KEY_BLOCK]) for b in range(d.r, nb, W.TP)}
    for d in M.dies:
        d.put("h", h)
        d.put("pre", pre)
    if ex is not None:
        assert first == 0, "lockstep starts from the embedding"
        for rk in ex.ranks:
            rk.put("h", h)
            rk.put("pre", pre)
    results, programs = [], []
    lock_bad = []
    for L in layers:
        tl = time.time()
        ops = W.Compiler(m, pos, VARIANT).compile_layer(L, first=(L == first))
        same_stream = canon(ops) == canon(committed[str(L)]) if first == 0 else None
        prog = ds.lower_ops(ops, iface.Program(model=ds.model_descriptor(m, pos), cmds=[]))
        blob = iface.encode(prog)
        prog2 = iface.decode(blob)
        rt = iface.encode(prog2) == blob
        programs.append(dict(layer=L, n_cmds=len(prog2.cmds), sha256=hashlib.sha256(blob).hexdigest(),
                             families=iface.family_counts(prog2)))
        z = np.load(refs / f"ctx{ctx}_L{L:02d}.npz")
        js = json.loads((refs / f"ctx{ctx}_L{L:02d}.json").read_text())
        R = M.dies
        regs = [W.check("input", z["h_in"], [(d.r, d.get("h")) for d in R]),
                W.check("input_pre", z["pre_in"], [(d.r, d.get("pre")) for d in R])]
        defect = None
        try:
            if ex is None:
                M.run(prog2.cmds)
            else:
                for op, c in zip(ops, prog2.cmds):
                    ex.run([op])
                    if op["kind"] == "all_gather" and op["tag"] == "expert_intermediate_gather":
                        ex.split_ea()
                    M.run([c])
                    b = lockstep_compare(ex, M, c)
                    if b:
                        lock_bad.append(dict(layer=L, cmd=c.id, tag=c.tag, first=[list(map(str, x)) for x in b[:5]],
                                             n=len(b)))
                        raise Defect(f"lockstep divergence at cmd {c.id} ({c.tag}): {b[:3]}")
        except Defect as e:
            defect = str(e)
            log(f"L{L} DEFECT {e}")
        if defect is None:
            golib.ranks = R                      # region_checks reads ex.ranks / ex.route_ids / ex.m
            regs += W.region_checks(golib, L, lambda k: z[k], lambda k: k in z.files, js["experts"],
                                    js.get("index_select_sha256"))
        ok = defect is None and all(x["bit_exact"] for x in regs) and rt and same_stream is not False
        results.append(dict(layer=L, kind=js["kind"], verdict="pass" if ok else "fail", defect=defect,
                            source_stream_equals_committed=same_stream, encode_roundtrip=rt, regions=regs,
                            experts=js["experts"], cmds=len(prog2.cmds), wall_s=round(time.time() - tl, 1)))
        log(f"L{L:02d} {js['kind']:28s} {'PASS' if ok else 'FAIL'} cmds {len(prog2.cmds)} stream "
            f"{same_stream} rt {rt} {time.time() - tl:.0f} s"
            + ("" if ok else f" bad: {[x['region'] for x in regs if not x['bit_exact']]}"))
        for k in [k for k in m.w if k.startswith(f"layers.{L}.")]:
            del m.w[k]
        for d in R:
            d.clear(keep=("h", "pre", "sel"))
        if ex is not None:
            for rk in ex.ranks:
                rk.clear(keep=("h", "pre", "sel"))
        if not ok:
            break
    head_res = None
    if head and results and all(r["verdict"] == "pass" for r in results) and layers[-1] == m.L - 1:
        ops = W.Compiler(m, pos, VARIANT).compile_head()
        same_stream = canon(ops) == canon(committed["head"])
        prog = ds.lower_ops(ops, iface.Program(model=ds.model_descriptor(m, pos), cmds=[]))
        blob = iface.encode(prog)
        prog2 = iface.decode(blob)
        programs.append(dict(layer="head", n_cmds=len(prog2.cmds), sha256=hashlib.sha256(blob).hexdigest(),
                             families=iface.family_counts(prog2)))
        M.run(prog2.cmds)
        lg = np.zeros(129280, dtype=W.F)
        for d in M.dies:
            r0, r1 = W.even(129280)[d.r]
            lg[r0:r1] = d.get("logits", r0, r1)
        tok = int(M.dies[0].get("token")[0])
        ok = tok == ref["next_token"] and W.LC.digest(lg) == ref["logits_sha256"] and same_stream
        head_res = dict(next_token=tok, reference_next_token=ref["next_token"], logits_sha256=W.LC.digest(lg),
                        reference_logits_sha256=ref["logits_sha256"], source_stream_equals_committed=same_stream,
                        tokens_agree_all_dies=all(int(d.get("token")[0]) == tok for d in M.dies),
                        verdict="pass" if ok else "fail")
        log(f"head: token {tok} (reference {ref['next_token']}) logits "
            f"{'BIT-EXACT' if W.LC.digest(lg) == ref['logits_sha256'] else 'MISMATCH'}")
    return dict(context=ctx, position=pos, seed=seed, variant=VARIANT, state_check=state_check, layers=results,
                lockstep=None if ex is None else dict(divergences=lock_bad),
                head=head_res, programs=programs, model_init_sha256=init_sha)


SOURCES = ("tools/hgi_sim/tp96_ir.py", "tools/hgi_sim/ds.py", "tools/hgi_sim/ds_roundtrip.py",
           "tools/w19_hbm_tp96_isa.py", "tools/hdc_golden_v41.py", "tools/hdc_golden.py",
           "tools/rtl_v41_fullshape_layer_campaign.py", "results/rtl/w17_v41_1m_reference_token.json",
           "results/rtl/dshbm_baseline_measured_20261004/program.json")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layers", default="0")
    ap.add_argument("--head", action="store_true")
    ap.add_argument("--refs", type=Path, help="W17 reference shard directory (default: W19's)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--lockstep", action="store_true", help="also run the W19 executor op for op and compare every "
                    "buffer of every die after each command")
    a = ap.parse_args()
    if W.V.ARITH != "chunk8":
        raise SystemExit("HDC_V41_ARITH must be chunk8")
    feats = getattr(np, "_core", np.core)._multiarray_umath.__cpu_features__
    if feats.get("AVX512F") or feats.get("AVX512_SKX"):
        # the golden's RoPE tables are float64 cos/sin rounded to FP32; numpy's AVX512 (SVML) float64 trig differs in
        # the last ulp from the baseline path the W17 reference shards were generated with (2026-10-09: L0 win0 fails
        # on EPYC with AVX512 dispatch, passes with it disabled)
        raise SystemExit("set NPY_DISABLE_CPU_FEATURES='AVX512F AVX512CD AVX512_SKX AVX512_CLX AVX512_CNL AVX512_ICL "
                         "AVX512_SPR AVX512_KNL AVX512_KNM' (numpy AVX512 float64 trig differs from the reference)")
    layers = W.parse_layers(a.layers)
    t0 = time.time()
    res = run(layers, a.head, refs=a.refs, lockstep=a.lockstep)
    res["wall_s"] = round(time.time() - t0, 1)
    passed = len(res["layers"]) == len(layers) and all(r["verdict"] == "pass" for r in res["layers"]) and \
        (not a.head or (res["head"] is not None and res["head"]["verdict"] == "pass"))
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    rec = dict(schema=SCHEMA, status="pass" if passed else "fail", layers=a.layers, head=a.head,
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               source_commit=head, arith=W.V.ARITH, host=os.uname().nodename,
               source_sha256={s: sha(ROOT / s) for s in SOURCES if (ROOT / s).exists()},
               claim_boundary="Interface-level (transaction) execution of the existing TP-96 DS command stream on 96 "
                              "simulated r25 dies, bit-exact against the released-checkpoint golden (W17 reference "
                              "state, 1M). Unit arithmetic is the goldens'; no RTL, cycle or physical verdict.",
               result=res)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=int) + "\n")
    print(("PASS" if passed else "FAIL") + f": {len(res['layers'])} layers, head {res['head']}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
