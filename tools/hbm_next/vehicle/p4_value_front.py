#!/usr/bin/env python3
"""HBM-NEXT-VEH (10-19 step 4): VALUE-EXACT P = 4 layer bench, part 1 = the layer front (HC.HC_MIX + FUSED.HC_PRE_NORM
+ FUSED.HC_POST) of ONE layer of the CMTP whole-token images, on the REAL golden operands, on the hnx N-row RTL.

What is real and what is not (stated, not hidden):
  * records   = the CMTP HGI-1R whole-token images (results/arch/hbm_next_1019/cmtp/emitter/whole/{ar_N1,mtp_N6}),
                decoded with isa_rows.decode_one; segment L's first FUSED.HC_PRE_NORM, HC.HC_MIX, FUSED.HC_POST (the
                attention sub-layer's front and back).  Their VM bases / row strides / N / eps (imm_a) drive the benches.
  * operands  = the committed CMTP golden ar_mtp_g5 (released DeepSeek-V4.1-Flash checkpoint, real DSpark drafter:
                draft 1 accepted, draft 2 rejected): the layer-L input h_{p}_{L-1} [4, 5120] and pre_{p}_{L-1} [4] of
                position p (AR: p = 1, N = 1; MTP verify: p = 1..6, N = 6) + layer L's released weights
                (hc_attn_fn [24, 20480] / base / scale, attn_norm.weight) read from the snapshot
                (rtl_v41_fullshape_layer_campaign.Checkpoint, lazy).  Weights are in the case files, not committed.
  * expected  = hdc_golden_v41 chunk8 Model methods on those operands (build_model, the pinned golden of every DS lane):
                hc_mixes(h, L, "attn") (mixes + sigmoid / exp / Sinkhorn tail), rmsnorm_fold(hc_pre(h, pre), w, eps),
                hc_post(y, res, post, comb).
  * HC_POST y = STAND-IN: the attention output of layer L is not in the golden; the bench feeds the layer's own
                attn-norm x (bf16) as y.  res, post and comb are real.  (Bit-exact arithmetic on real operand
                distributions; the attention value itself is the ATT / SM part of the layer bench, pending.)
  * HC_MIX    = tb_hnx_hc_eng4 (ot_hnx_hc_root + 4 qeng rings, production K 20,480 / 24 rows / W 256) with the
                static programme of tools/rtl_hbm_hc_eng_static_gate.py --split (P = N, RAW0 167, RS 104) and the
                released eps (norm_eps, patched into the launch word); x / fn / base / scale / expected overwritten.
CONTRACT CHECK (the FUSED engine's job_ok, ot_hnx_fused_eng.sv): A, B, C, O 8-word aligned, A / B / O one bank phase
(addr[7:3]), row strides of A / B / O multiples of 256, HC_PRE_NORM gain broadcast (rs_B 0) and in VM.  Each FUSED
record is run twice: 'emit' = the record's operands exactly as emitted (an HBM gain is staged in VM at the A phase;
nothing else moved) and 'legal' = the smallest relocation that satisfies job_ok (reported per operand).  An emitted
record that breaks job_ok must FAULT on the RTL (contract witness); 'legal' must PASS bit-exact.

    python3 tools/hbm_next/vehicle/p4_value_front.py gen --layer 2 --out CASES        (local: lazy snapshot reads)
    tools/hbm_next/vehicle/run_value_front.sh CASES OUT                                 (fleet, Verilator 5.050)
    python3 tools/hbm_next/vehicle/p4_value_front.py collect --cases CASES --runs OUT --out JSON
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/hbm_next"))
A_ = "results/arch/hbm_next_1019"
IMG = ROOT / A_ / "cmtp/emitter/whole"
GOLD = ROOT / A_ / "cmtp/goldens/ar_mtp_g5/golden_spec.npz"
MODES = {"ar": dict(img="ar_N1", pos=[1]), "mtp": dict(img="mtp_N6", pos=[1, 2, 3, 4, 5, 6])}
D, K = 5120, 20480
VMW = 1 << 19
F = np.float32


def u32(x):
    return np.asarray(x, dtype=F).view(np.uint32)


def f32_bits(v):
    return int(np.float32(v).view(np.uint32))


def seg_records(mode, L):
    from hbm_next import isa_rows as I
    d = IMG / MODES[mode]["img"]
    e = json.loads((d / "emitter.json").read_text())
    segs = e["token"]["segments"]
    s = next(x for x in segs if x["segment"] == str(L))
    buf = (d / e["token"]["image"]).read_bytes()
    assert hashlib.sha256(buf).hexdigest() == e["token"]["sha256"], "image sha256 != emitter.json"
    off, end, out, k = s["offset"], s["offset"] + s["bytes"], {}, 0
    while off < end:
        r, rx, off = I.decode_one(buf, off)
        k += 1
        key = f"{r.unit}.{r.op}"
        if key in ("FUSED.HC_PRE_NORM", "HC.HC_MIX", "FUSED.HC_POST") and key not in out:
            out[key] = dict(index_in_segment=k, n=(rx.n if rx else 1), rs=(dict(rx.rs) if rx else {}), imm_a=r.imm_a,
                            desc={q: dict(space=v.space, fmt=v.fmt, base=v.base, n=v.n, m=v.m)
                                  for q, v in r.desc.items()})
    return out, dict(image=str((d / e["token"]["image"]).relative_to(ROOT)), image_sha256=e["token"]["sha256"],
                     segment=s)


def job_ok(post, ops, rs):
    """mirror of ot_hnx_fused_eng job_ok; -> list of broken rules"""
    bad = []
    for q in "ABCO":
        if ops[q] % 8:
            bad.append(f"{q} base {ops[q]} not 8-aligned")
    ph = {q: (ops[q] >> 3) & 31 for q in "ABO"}
    if not (ph["A"] == ph["B"] == ph["O"]):
        bad.append(f"bank phase A {ph['A']} / B {ph['B']} / O {ph['O']} differ")
    for q in "ABO":
        if rs.get(q, 0) % 256:
            bad.append(f"rs_{q} {rs.get(q, 0)} not a multiple of 256")
    if rs.get("C", 0) % 8:
        bad.append(f"rs_C {rs['C']} not 8-aligned")
    if not post and rs.get("B", 0):
        bad.append("PRE gain not a broadcast")
    return bad


def spans(ops, rs, n, size):
    return {q: (ops[q], ops[q] + (n - 1) * rs.get(q, 0) + size[q]) for q in ops}


def legalise(ops, rs, n, size, fixed):
    """smallest upward moves of the non-fixed operands so that job_ok holds and no two operand spans overlap"""
    new = dict(ops)
    phase = (new[fixed] >> 3) & 31
    for q in "ABCO":
        if q == fixed:
            continue
        a = new[q]
        while True:
            if q in "ABO":
                a = a + ((phase * 8 - a) % 256)               # next address with the fixed operand's bank phase
            else:
                a = (a + 7) // 8 * 8
            sp = spans(dict(new, **{q: a}), rs, n, size)
            lo, hi = sp[q]
            if hi <= VMW and all(h2 <= lo or hi <= l2 for o, (l2, h2) in sp.items() if o != q):
                new[q] = a
                break
            a += 8
            assert a < VMW, f"no legal place for {q}"
    return new


def fused_case(out, post, n, ops, rs, eps_bits, vin_by_op, vout, note):
    from hnx_fused_vec import job_word
    out.mkdir(parents=True, exist_ok=True)
    vin = {}
    for q, words in vin_by_op.items():                      # q -> list of (offset, row stride, u32 array) per row
        for r, arr in enumerate(words):
            base = ops[q] + r * rs.get(q, 0)
            vin.update({base + i: int(v) for i, v in enumerate(arr)})
    exp = {}
    for r, arr in enumerate(vout):
        base = ops["O"] + r * rs["O"]
        exp.update({base + i: int(v) for i, v in enumerate(arr)})
    eps = np.uint32(eps_bits).view(np.float32)
    job = job_word(int(post), n - 1, ops["A"], ops["B"], ops["C"], ops["O"], rs.get("A", 0), rs.get("B", 0),
                   rs.get("C", 0), rs["O"], 0, eps)
    (out / "vmi.mem").write_text("".join(f"{k:05X}{v:08X}\n" for k, v in sorted(vin.items())))
    (out / "vme.mem").write_text("".join(f"{k:05X}{v:08X}\n" for k, v in sorted(exp.items())))
    (out / "job.mem").write_text(f"{job:055X}\n")
    (out / "plus.txt").write_text(f"+NVMI={len(vin)} +NVME={len(exp)} +OP={'post' if post else 'pre'} +N={n} +RGAP=0\n")
    meta = dict(op="post" if post else "pre", n=n, ops=ops, rs=rs, eps_bits=eps_bits, nvmi=len(vin), nvme=len(exp),
                job_ok_broken=job_ok(post, ops, rs), note=note,
                vme_sha256=hashlib.sha256((out / "vme.mem").read_bytes()).hexdigest())
    (out / "case.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def gen(a):
    import hdc_golden_v41 as G
    import rtl_v41_fullshape_layer_campaign as LC
    import rtl_hdc_v41x_hcp_campaign as HCC
    import rtl_hbm_hc_eng_static_gate as HG
    G.set_arith("chunk8")
    ck = LC.Checkpoint(Path(a.snap)) if a.snap else LC.Checkpoint()
    m, init_sha = LC.build_model(ck, engram=False)
    gz = np.load(GOLD)
    L = a.layer
    fn = np.asarray(m.lw(L, "hc_attn_fn"), dtype=F)
    base, scale = np.asarray(m.lw(L, "hc_attn_base"), F), np.asarray(m.lw(L, "hc_attn_scale"), F)
    wn = np.asarray(m.lw(L, "attn_norm.weight"), F)
    assert fn.shape == (24, K) and base.shape == (24,) and scale.shape == (3,) and wn.shape == (D,)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    summary = dict(schema="opentallas.hbm_next_1019.veh.value_front_cases.v1", layer=L, golden=str(GOLD.relative_to(ROOT)),
                   golden_sha256=hashlib.sha256(GOLD.read_bytes()).hexdigest(), model_init_sha=init_sha,
                   weights_sha256={k: hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest() for k, v in
                                   dict(hc_attn_fn=fn, hc_attn_base=base, hc_attn_scale=scale, attn_norm=wn).items()},
                   eps=dict(norm=float(m.eps), hc=float(m.hc_eps), sinkhorn=int(m.sinkhorn_iters)), modes={})
    for mode in a.modes.split(","):
        recs, src = seg_records(mode, L)
        P = MODES[mode]["pos"]
        n = len(P)
        hs = [np.asarray(gz[f"h_{p}_{L - 1}"], F) for p in P]
        pres = [np.asarray(gz[f"pre_{p}_{L - 1}"], F) for p in P]
        # golden on the real operands (the model's own methods)
        mixes = [m.hc_mixes(h, L, "attn") for h in hs]
        xs = []
        for h, pre in zip(hs, pres):
            x = G.rmsnorm_fold(m.hc_pre(h, pre), wn, m.eps)
            assert not hasattr(x, "rstd"), "nfold active: HC_PRE_NORM expected must be the plain bf16 norm"
            xs.append(np.asarray(x, F))
        md = dict(source=src, records=recs, positions=P, n=n)
        # ---- FUSED.HC_PRE_NORM
        r = recs["FUSED.HC_PRE_NORM"]
        assert r["n"] == n, (r["n"], n)
        assert r["imm_a"] == f32_bits(m.eps), f"record eps {r['imm_a']:#x} != norm_eps {f32_bits(m.eps):#x}"
        rs = dict(A=r["rs"].get("A", 0), B=0, C=r["rs"].get("C", 0), O=r["rs"].get("O", 0))
        if n == 1:
            rs = dict(A=K, B=0, C=8, O=D)                     # AR records carry no RowX: one row, strides unused
        ops = {q: r["desc"][q]["base"] for q in "ACO"}
        b_space = r["desc"]["B"]["space"]
        size = dict(A=K, B=D, C=4, O=D)
        # emitted: the gain (HBM in the record) staged in VM at the A phase above every operand span
        hi = max(h for _, h in spans(dict(ops, B=0), rs, n, size).values())
        ops_e = dict(ops, B=((hi + 255) // 256) * 256 + (ops["A"] & 255))
        ops_l = legalise(ops_e, rs, n, size, fixed="A")
        vin = dict(A=[u32(h.reshape(-1)) for h in hs], B=[u32(wn)], C=[u32(p) for p in pres])
        vout = [u32(x) for x in xs]
        md["pre"] = dict(record_B_space=b_space,
                         emit=fused_case(out / mode / "pre_emit", False, n, ops_e, rs, r["imm_a"], vin, vout,
                                         "record operands as emitted; gain staged in VM (record B in %s)" % b_space),
                         legal=fused_case(out / mode / "pre_legal", False, n, ops_l, rs, r["imm_a"], vin, vout,
                                          "smallest job_ok relocation"),
                         moved={q: [ops_e[q], ops_l[q]] for q in "ABCO" if ops_e[q] != ops_l[q]})
        # ---- FUSED.HC_POST (attention side: res = the layer input h, post / comb = this layer's attn mixes)
        r = recs["FUSED.HC_POST"]
        assert r["n"] == n
        rs = dict(A=r["rs"].get("A", 0), B=r["rs"].get("B", 0), C=r["rs"].get("C", 0), O=r["rs"].get("O", 0))
        if n == 1:
            rs = dict(A=D, B=K, C=24, O=K)
        ops_e = {q: r["desc"][q]["base"] for q in "ABCO"}
        size = dict(A=D, B=K, C=20, O=K)
        ops_l = legalise(ops_e, rs, n, size, fixed="O")
        hout = [np.asarray(m.hc_post(x, h, mx[1], mx[2]), F) for x, h, mx in zip(xs, hs, mixes)]
        vin = dict(A=[u32(x) for x in xs], B=[u32(h.reshape(-1)) for h in hs],
                   C=[u32(np.concatenate([mx[1], mx[2].reshape(-1)])) for mx in mixes])
        md["post"] = dict(emit=fused_case(out / mode / "post_emit", True, n, ops_e, rs, 0, vin,
                                          [u32(h.reshape(-1)) for h in hout], "record operands as emitted"),
                          legal=fused_case(out / mode / "post_legal", True, n, ops_l, rs, 0, vin,
                                           [u32(h.reshape(-1)) for h in hout], "smallest job_ok relocation"),
                          moved={q: [ops_e[q], ops_l[q]] for q in "ABCO" if ops_e[q] != ops_l[q]},
                          y="STAND-IN: the layer's attn-norm x (attention output not in the golden)")
        # ---- HC.HC_MIX (tb_hnx_hc_eng4 programme for P = n, real values)
        r = recs["HC.HC_MIX"]
        assert r["n"] == n
        hd = out / mode / "hcmix"
        HG.EPS = f32_bits(m.eps)
        argv = sys.argv
        sys.argv = ["rtl_hbm_hc_eng_static_gate.py", "--run", str(hd), "--split", "--npos", str(n), "--raw0", "167",
                    "--rs", "104"]
        try:
            HG.main()
        finally:
            sys.argv = argv
        x = np.stack([h.reshape(-1) for h in hs])
        mixv = np.stack([HCC.golden_mixes(fn, h, m.eps)[2] for h in hs])
        tail = np.stack([np.concatenate([mx[0], mx[1], mx[2].reshape(-1)]) for mx in mixes])
        tref = np.stack([HG.tail_ref(mixv[i], base, scale) for i in range(n)])
        assert np.array_equal(u32(tail), u32(tref)), "tail_ref != Model.hc_mixes on the real operands"
        np.savetxt(hd / "wmem.mem", u32(fn).reshape(-1), fmt="%08x")
        np.savetxt(hd / "xmem.mem", u32(x).reshape(-1), fmt="%08x")
        np.savetxt(hd / "expmix.mem", u32(mixv).reshape(-1), fmt="%08x")
        np.savetxt(hd / "exptail.mem", u32(tail).reshape(-1), fmt="%08x")
        with open(hd / "tbl.mem", "w") as f:
            words = list(u32(base)) + list(u32(scale)) + [0]
            for s in range(3):
                for r4 in range(4):
                    f.write("0" * 8 + "".join("%08x" % words[r4 * 7 + i] for i in reversed(range(7))) + "\n")
        md["hcmix"] = dict(n=n, eps_bits=HG.EPS, tail_eq_model=True,
                           exptail_sha256=hashlib.sha256((hd / "exptail.mem").read_bytes()).hexdigest())
        summary["modes"][mode] = md
        print(mode, "N", n, "pre broken:", md["pre"]["emit"]["job_ok_broken"], "moved", md["pre"]["moved"],
              "| post broken:", md["post"]["emit"]["job_ok_broken"], "moved", md["post"]["moved"])
    (out / "cases.json").write_text(json.dumps(summary, indent=1) + "\n")


def collect(a):
    cases = json.loads((Path(a.cases) / "cases.json").read_text())
    runs = Path(a.runs)
    res = dict(schema="opentallas.hbm_next_1019.veh.value_front.v1", rule=__doc__, layer=cases["layer"],
               golden=cases["golden"], golden_sha256=cases["golden_sha256"], sim=None, modes={})
    vt = runs / "verilator.txt"
    res["sim"] = vt.read_text().strip() if vt.exists() else None
    for mode, md in cases["modes"].items():
        r = dict(n=md["n"], positions=md["positions"], records=md["records"])
        for tag in ("pre_emit", "pre_legal", "post_emit", "post_legal", "pre_legal_mut1", "post_legal_mut1"):
            f = runs / mode / tag / "run.log"
            if f.exists():
                t = f.read_text()
                c = re.search(r"HNX_FUSED_CYCLES .*cycles=(\d+) done=(\d) fault=(\d)", t)
                r[tag] = dict(pass_="HNX_FUSED PASS" in t, fail="HNX_FUSED FAIL" in t,
                              cycles=int(c.group(1)) if c else None, fault=int(c.group(3)) if c else None)
        for tag in ("hcmix", "hcmix_mut1"):
            f = runs / mode / tag / "run.log"
            if f.exists():
                t = f.read_text()
                c = re.search(r"HC_MIX_CYCLES=(\d+)", t)
                r[tag] = dict(pass_=bool(re.search(r"^HC_ENG PASS", t, re.M)), fail="HC_ENG FAIL" in t,
                              cycles=int(c.group(1)) if c else None)
        r["pre_moved"], r["post_moved"] = md["pre"]["moved"], md["post"]["moved"]
        r["pre_emit_broken"], r["post_emit_broken"] = md["pre"]["emit"]["job_ok_broken"], md["post"]["emit"]["job_ok_broken"]
        res["modes"][mode] = r
    ok = all(m_.get(t, {}).get("pass_") for m_ in res["modes"].values() for t in ("pre_legal", "post_legal", "hcmix"))
    wit = all(m_.get(t, {}).get("fail") or m_.get(t, {}).get("fault") for m_ in res["modes"].values()
              for t in ("pre_emit", "post_emit") if m_.get(f"{t}_broken".replace("_emit_broken", "_emit_broken")))
    res["verdict"] = dict(legal_bit_exact=ok, emitted_contract_faults=wit,
                          mutants_caught=all(m_.get(t, {}).get("fail") for m_ in res["modes"].values()
                                             for t in ("pre_legal_mut1", "hcmix_mut1") if t in m_))
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res["verdict"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("gen")
    g.add_argument("--layer", type=int, default=2)
    g.add_argument("--modes", default="ar,mtp")
    g.add_argument("--snap", default=None)
    g.add_argument("--out", required=True)
    c = sp.add_parser("collect")
    c.add_argument("--cases", required=True)
    c.add_argument("--runs", required=True)
    c.add_argument("--out", required=True)
    a = ap.parse_args()
    gen(a) if a.cmd == "gen" else collect(a)


if __name__ == "__main__":
    main()
