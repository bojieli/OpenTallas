#!/usr/bin/env python3
"""DS on HGI-1 as SIMT.RUN(pc) records (spec section 3.8): the committed OTG-1 DeepSeek-V4.1 decode program
(tools/gpu_sys/v41_hbm.py: kernels embed / layer / head on 2 dies x 2 SMs, reduced-v2 model) re-encoded as an HGI-1
record stream and executed by the simulator's SIMT unit, against the existing command-list execution and the golden.

Today's command list (v41_hbm.emit cmd_d{d}.hex): LAUNCH embed, 40 x LAUNCH layer, LAUNCH head, END, each LAUNCH a
64-bit word {op 1, SM mask [59:44], entry PC [31:0]} into ot_ds_hbm_cmdproc20.  The HGI-1 program is
    SIMT.RUN(param = embed PC, imm_a = SM mask)
    CTL.LOOP(param = 40)  SIMT.RUN(layer PC)  CTL.ENDLOOP
    SIMT.RUN(head PC)
    CTL.END                       (no A operand: the token is the kernel's RESULT payload, as cmdproc20 posts it)
plus the unrolled form (42 SIMT.RUN records).  The SIMT unit fetches the kernel from the linked IMEM image AT the
record's PC (v41_hbm.link), not by name, so a wrong PC or a wrong image is a mismatch.

PROOF, every position of the reference prompt:
  (a) the HGI image encodes / decodes / re-encodes byte-identically, and its SIMT.RUN PCs and masks equal the
      command-list words;
  (b) after EVERY record, every byte of both dies' memories equals the legacy command-list execution's (a second
      gpu_sys Machine driven by the LAUNCH words), and the completion tokens are equal;
  (c) the tokens equal the golden's (hdc_golden_v41 chunk8), as v41_hbm.check does.

    python3 -m hgi_sim.ds_simt --npos 3 --out REC.json        (from tools/)
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "gpu_sys"))
import hbm_generic_iface as HGI  # noqa: E402

from hgi_sim.records import Rec, decode_program, encode_program  # noqa: E402


def gs():
    import v41_hbm as D
    return D


def cmd_words(D, model, entries):
    seq = [(nm, entries[nm]) for nm in D.launches(model.L)]
    return [(1 << 60) | (((1 << D.NSM) - 1) << 44) | pc for _, pc in seq] + [2 << 60]


def hgi_program(words, nlayers, rolled=True):
    """Re-encode cmdproc20 LAUNCH words as HGI-1 records."""
    recs = []
    launches = [w for w in words if w >> 60 == 1]
    pcs = [(w & 0xFFFFFFFF, (w >> 44) & 0xFFFF) for w in launches]
    embed, layer, head = pcs[0], pcs[1], pcs[-1]
    assert all(p == layer for p in pcs[1:1 + nlayers]) and len(pcs) == nlayers + 2
    recs.append(Rec("SIMT", "RUN", param=embed[0], imm_a=embed[1], tag="embed"))
    if rolled:
        recs.append(Rec("CTL", "LOOP", param=nlayers, tag="layers"))
        recs.append(Rec("SIMT", "RUN", param=layer[0], imm_a=layer[1], tag="layer"))
        recs.append(Rec("CTL", "ENDLOOP", tag="layers"))
    else:
        recs += [Rec("SIMT", "RUN", param=layer[0], imm_a=layer[1], tag=f"layer{i}") for i in range(nlayers)]
    recs.append(Rec("SIMT", "RUN", param=head[0], imm_a=head[1], tag="head"))
    recs.append(Rec("CTL", "END", tag="end"))
    return recs


class Simt:
    """The SIMT unit: an OTG-1 grid launch at the record's PC on the SMs of its mask (gpu_sys reference machine)."""

    def __init__(self, D, mach, images, entries):
        self.D, self.mach, self.images = D, mach, images
        self.kern = {}
        isa = sys.modules["isa"]
        byname = {pc: nm for nm, pc in entries.items()}
        ends = sorted(entries.values()) + [len(next(iter(images.values())))]
        for nm, pc in entries.items():
            nxt = min(e for e in ends if e > pc)
            code = {}
            for key, img in images.items():
                words = []
                for w in img[pc:nxt]:                       # IMEM at PC; branch targets back to kernel-relative
                    op = (w >> 56) & 0xFF
                    if op in (isa.OPS["BRA"], isa.OPS["BNZ"]):
                        w = (w & ~0xFFFFFFFF) | ((w & 0xFFFFFFFF) - pc)
                    words.append(w)
                code[key] = words
            self.kern[pc] = code
        self.byname = byname
        self.result = None

    def run(self, rec: Rec, token, pos):
        pc, mask = rec.param, rec.imm_a
        if pc not in self.kern:
            raise RuntimeError(f"SIMT.RUN at PC {pc}: no kernel entry there")
        if mask != (1 << self.D.NSM) - 1:
            raise RuntimeError(f"SIMT.RUN mask {mask:#x}: the program's kernels run on every SM")
        self.mach.launch(self.kern[pc], token, pos)
        self.result = self.mach.dies[0].sms[0].result


def run_hgi(recs_bytes, simt, token, pos, after=None):
    recs = decode_program(recs_bytes)
    pc, loop, L, nrun = 0, None, 0, 0
    while pc < len(recs):
        r = recs[pc]
        if r.unit == "CTL" and r.op == "LOOP":
            loop, L, pc = (pc + 1, r.param), 0, pc + 1
            continue
        if r.unit == "CTL" and r.op == "ENDLOOP":
            L += 1
            if L < loop[1]:
                pc = loop[0]
                continue
            loop, L, pc = None, 0, pc + 1
            continue
        if r.unit == "CTL" and r.op == "END":
            if "A" in r.desc:
                raise RuntimeError("END with an A operand: DS posts the token as the kernel RESULT payload")
            return simt.result, nrun
        if r.unit != "SIMT":
            raise RuntimeError(f"unexpected {r.unit}.{r.op}")
        simt.run(r, token, pos)
        nrun += 1
        if after:
            after(nrun, r)
        pc += 1
    raise RuntimeError("no END")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--npos", type=int, default=3)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    D = gs()
    import hdc_golden_v41 as V
    t0 = time.time()
    model, prog, graph, code = D.build()
    images, entries = D.link(code)
    words = cmd_words(D, model, entries)
    rolled = hgi_program(words, model.L, rolled=True)
    unrolled = hgi_program(words, model.L, rolled=False)
    res = dict(model_layers=model.L, entries=entries, cmd_words=len(words))
    checks = {}
    for nm, recs in (("rolled", rolled), ("unrolled", unrolled)):
        b = encode_program(recs)
        d = decode_program(b)
        checks[nm] = dict(records=len(recs), image_bytes=len(b), sha256=hashlib.sha256(b).hexdigest(),
                          roundtrip=encode_program(d) == b,
                          pcs_match=[(r.param, r.imm_a) for r in d if r.unit == "SIMT"] ==
                          ([(w & 0xFFFFFFFF, (w >> 44) & 0xFFFF) for w in words if w >> 60 == 1] if nm == "unrolled"
                           else [(w & 0xFFFFFFFF, (w >> 44) & 0xFFFF) for w in words if w >> 60 == 1][:2] +
                           [(words[-2] & 0xFFFFFFFF, (words[-2] >> 44) & 0xFFFF)]))
    res["encoding"] = checks
    # the HGI path and the legacy command-list path, each on its own machine, compared after every launch
    m_h = D.Machine(nd=D.TP, nsm=D.NSM, nl=D.NL, mem_bytes=prog.mem_bytes, L=D.L16)
    m_l = D.Machine(nd=D.TP, nsm=D.NSM, nl=D.NL, mem_bytes=prog.mem_bytes, L=D.L16)
    D.load_images(m_h, prog)
    D.load_images(m_l, prog)
    simt = Simt(D, m_h, images, entries)
    kc = dict(code)
    seq = D.launches(model.L)
    prompt, _ = V.prompt_and_expected()
    gm = V.Model()
    st = gm.new_state()
    rows = []
    allok = all(c["roundtrip"] and c["pcs_match"] for c in checks.values())
    image = encode_program(rolled)
    for pos, tok in enumerate(prompt[:a.npos]):
        gold = int(np.argmax(gm.decode_token(tok, pos, st)))
        diffs = []
        k = [0]

        def after(n, r):
            nm = seq[k[0]]
            m_l.launch(kc[nm], tok, pos)                    # the legacy LAUNCH of the same step
            k[0] += 1
            same = all(np.array_equal(m_h.dies[d].mem, m_l.dies[d].mem) for d in range(D.TP))
            if not same:
                diffs.append(dict(launch=k[0] - 1, kernel=nm))
        got, nrun = run_hgi(image, simt, tok, pos, after)
        legacy = m_l.dies[0].sms[0].result
        ok = not diffs and got == legacy == gold and nrun == len(seq)
        rows.append(dict(position=pos, input=int(tok), hgi_token=got, legacy_token=legacy, golden_token=gold,
                         launches=nrun, memory_identical_after_every_record=not diffs, first_diffs=diffs[:3],
                         verdict="pass" if ok else "fail"))
        print(rows[-1], flush=True)
        allok &= ok
    res["positions"] = rows
    rec = dict(schema="opentallas.hgi_sim.ds_simt_roundtrip.v1", status="pass" if allok else "fail",
               spec="HGI-1 v0.9 (024fa2af1) SIMT.RUN", host=os.uname().nodename, wall_s=round(time.time() - t0, 1),
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               claim_boundary="the committed reduced-shape DS OTG-1 program (2 dies x 2 SMs, reduced-v2) re-encoded as "
                              "HGI-1 SIMT.RUN records: identical memories after every launch and identical tokens vs "
                              "the cmdproc20 LAUNCH list, and golden tokens; functional (gpu_sys reference machine), "
                              "no RTL cycles",
               result=res,
               source_sha256={p: hashlib.sha256((TOOLS / p).read_bytes()).hexdigest() for p in (
                   "hgi_sim/ds_simt.py", "hgi_sim/records.py", "gpu_sys/v41_hbm.py", "gpu_sys/machine.py",
                   "gpu_sys/isa.py", "hdc_golden_v41.py", "hbm_generic_iface.py")})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=int) + "\n")
    print(rec["status"])
    return 0 if allok else 1


if __name__ == "__main__":
    raise SystemExit(main())
