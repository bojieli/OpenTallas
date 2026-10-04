#!/usr/bin/env python3
"""Minimum-component images for one DSpark MTP speculative step on the as-built V4.1 core.

The ITER program (tools/hdc_program_v41.py build_mtp, gamma 5, m = 1) is cut at its section boundaries
(draft embed, the three DSpark draft stages L40-L42, the draft tail, the DYN + per-slot Engram prologue, each
of the 40 verify layers over the 6 slots, the DSpark row seeding after target layers 36-39, the verify head,
the seeding tail, ACCEPT).  The ISA model runs the prompt and then the step instruction by instruction; at
every boundary its full state is captured.  Each slice image holds the slice's instructions plus END, the
vector memory and KV SRAM before it, the slot tokens / verify targets before it, the Engram history (prime),
and the state after it, so rtl/test/tb_hdc_core_v41_mtp_slice.sv simulates exactly one section and checks
it bit for bit.  The ROMs are written once (DIR/rom).

Runs the NumPy golden (model inference): GPU host only.

    python3 tools/dsrom_dspark_step_slices.py --out DIR [--prompt gold4] [--gamma 5]
"""
import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41_mtp_campaign as C  # noqa: E402  (fixes the as-built campaign's arithmetic classes)

P, G, I, V, F = C.P, C.G, C.I, C.V, C.F


def section(tag):
    s = tag.split(".")[0]
    return s


def plan(prog, entry):
    """[(name, a, b)] contiguous sections of the ITER program, END excluded."""
    tags = [prog[n].get("_tag", "") for n in range(entry, len(prog))]
    end = entry + next(i for i, t in enumerate(tags) if t == "end")
    out, n = [], entry
    first_l0 = next(i for i in range(entry, end) if section(prog[i]["_tag"]) == "L0")
    dyn = next(i for i in range(entry, end) if section(prog[i]["_tag"]) == "dyn")
    seen = {}
    while n < end:
        if n == dyn:
            out.append(("prologue", dyn, first_l0))
            n = first_l0
            continue
        s = section(prog[n]["_tag"])
        m = n
        while m < end and m != dyn and section(prog[m]["_tag"]) == s:
            m += 1
        k = seen.get(s, 0)
        seen[s] = k + 1
        name = s if k == 0 else f"{s}_{k}"
        if n < dyn:
            name = "draft_" + name if not name.startswith("draft") else name
        out.append((name, n, m))
        n = m
    return out, end


def snap(m):
    return {"vm": m.vm.copy(), "kv": m.kv.copy(), "stok": list(m.stok), "ttok": list(m.ttok),
            "heads": len(m.head_log), "accepted": m.accepted}


def step(m, prog, a, b):
    """Machine.run's loop body over [a, b) without its per-start reset."""
    for n in range(a, b):
        f = prog[n]
        f = {name: f.get(name, 0) for name, _ in I.FIELDS} | {"_tag": f.get("_tag", "")}
        if f["unit"] == I.UNIT_CTL:
            assert f["ctl"] != I.CTL_END
            m.control(f)
            continue
        m.dyn = m.banks[f["dslot"]]
        p = m.pos + f["dslot"]
        if f["pred"] == I.PRED_ODD and not (p & 1):
            continue
        if f["pred"] == I.PRED_NZ and p == 0:
            continue
        {I.UNIT_ME: m.me, I.UNIT_SU: m.su, I.UNIT_QE: m.qe, I.UNIT_XU: m.xu, I.UNIT_HE: m.he}[f["unit"]](f)


def vm_words(vm):
    v = np.zeros(I.VM_ELEMS_MTP, dtype=F)
    v[:len(vm)] = vm
    return G.bits(v)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--prompt", default="gold4")
    ap.add_argument("--gamma", type=int, default=5)
    ap.add_argument("--prefixes", help="debug: NAME:k1,k2,..  also write NAME's first k instructions as slices")
    ap.add_argument("--forced", action="store_true", help="the campaign's forced drafter (golden continuation, "
                                                          "one draft corrupted per step): nonzero acceptance")
    a = ap.parse_args()
    model = V.Model()
    prompt = C.prompts()[a.prompt]
    lay = P.mtp_layout(model, a.gamma)
    prog, entry = P.build_mtp(lay, a.gamma, 1)
    sections, end = plan(prog, entry)
    dyn_pc = next(s0 for nm, s0, _ in sections if nm == "prologue")
    rom = a.out / "rom"
    P.write_images(rom, lay, prog)
    m = P.Machine(lay, np.zeros(I.KV_WORDS * C.P.W, dtype=F), np.zeros(lay.vm.size, dtype=F))
    for p, t in enumerate(prompt):
        m.run(prog, t, p, entry=0)
    y, pos = int(m.argmax), len(prompt)
    toks, _ = C.golden_run(model, prompt, 1 + a.gamma + 1)
    assert y == toks[0], (y, toks[0])
    if a.forced:
        fd = C.forced_drafter(list(prompt) + [int(t) for t in toks], a.gamma)
        m.force = lambda d, q=len(prompt) - 1: fd(q, d)
    # the history the step's EHASHes extend (the RTL hash unit holds the last ENG_N - 1 committed ids)
    prime = [int(model.engram.token_map[t]) for t in m.tokens][-3:]
    # Machine.run's MTP setup for a step at pos with the pending token y
    m.token, m.pos = y, pos
    m.stok = [y] + [0] * (I.NSLOT - 1)
    m.ttok = [0] * I.NSLOT
    m.banks = [I.dyn_values(m.stok[j], pos + j) for j in range(I.NSLOT)]
    m.accepted, m.drafts, m.slot_logits = None, [], {}
    endw = I.encode(**{k: v for k, v in prog[end].items() if not k.startswith("_")})
    manifest = {"prompt": a.prompt, "drafter": "forced" if a.forced else "dspark", "gamma": a.gamma, "pos": pos, "token": y, "entry": entry, "end": end,
                "iter_instructions": end - entry, "slices": []}
    pre = {}
    if a.prefixes:
        nm, ks = a.prefixes.split(":")
        pre = {nm: [int(k) for k in ks.split(",")]}

    def emit(mach, name, s0, s1, record=True):
        before = snap(mach)
        step(mach, prog, s0, s1)
        after = snap(mach)
        d = a.out / name
        d.mkdir(parents=True, exist_ok=True)
        words = [I.encode(**{k: v for k, v in f.items() if not k.startswith("_")}) for f in prog[s0:s1]] + [endw]
        (d / "prog.hex").write_text(P.hexwords(words, I.INSTR_BITS))
        (d / "vm_init.hex").write_text(P.hexwords(vm_words(before["vm"]), 32))
        (d / "kv_init.hex").write_text(P.hexwords(G.bits(before["kv"]).reshape(-1), 32))
        (d / "expect_vm.hex").write_text(P.hexwords(vm_words(after["vm"]), 32))
        (d / "expect_kv.hex").write_text(P.hexwords(G.bits(after["kv"]).reshape(-1), 32))
        # the DYN control step (the prologue's first instruction) is where a forced drafter replaces the
        # drafts (as tb_hdc_core_v41_mtp's +FORCE does): load the forced slot tokens before it
        (d / "stok.hex").write_text(P.hexwords(after["stok"] if s0 == dyn_pc else before["stok"], 16))
        (d / "ttok.hex").write_text(P.hexwords(before["ttok"], 16))
        (d / "prime.hex").write_text(P.hexwords(prime, 16))
        heads = mach.head_log[before["heads"]:after["heads"]]
        hw = G.bits(np.concatenate([np.asarray(h, dtype=F) for h in heads])) if heads else [0]
        (d / "exp_heads.hex").write_text(P.hexwords(hw, 32))
        acc = after["accepted"] if after["accepted"] is not None and before["accepted"] is None else -1
        args = [f"+TOKEN={y}", f"+POS={pos}", f"+NPRIME={len(prime)}", f"+NHEAD={len(heads)}",
                f"+EXPACC={acc + 1 if acc >= 0 else 0}"]
        (d / "run.args").write_text(" ".join(args) + "\n")
        units = {}
        for f in prog[s0:s1]:
            units[f["unit"]] = units.get(f["unit"], 0) + 1
        if record:
            manifest["slices"].append({"name": name, "pc": [s0, s1], "instructions": s1 - s0, "heads": len(heads),
                                       "units": {str(k): v for k, v in sorted(units.items())},
                                       "accepted": acc if acc >= 0 else None})
        print(name, s0, s1, len(heads), flush=True)

    for name, s0, s1 in sections:
        for k in pre.get(name, []):
            sub = copy.copy(m)
            sub.vm, sub.kv = m.vm.copy(), m.kv.copy()
            sub.stok, sub.ttok, sub.head_log, sub.tokens = list(m.stok), list(m.ttok), list(m.head_log), list(m.tokens)
            sub.banks = [list(b) for b in m.banks]
            emit(sub, f"{name}_p{k}", s0, s0 + k, record=False)
        emit(m, name, s0, s1)
    # the null slice: END alone from the final state (the fixed start + END cost of a slice)
    d = a.out / "null"
    d.mkdir(parents=True, exist_ok=True)
    (d / "prog.hex").write_text(P.hexwords([endw], I.INSTR_BITS))
    for nm, arr in (("vm_init", vm_words(m.vm)), ("expect_vm", vm_words(m.vm))):
        (d / f"{nm}.hex").write_text(P.hexwords(arr, 32))
    for nm in ("kv_init", "expect_kv"):
        (d / f"{nm}.hex").write_text(P.hexwords(G.bits(m.kv).reshape(-1), 32))
    (d / "stok.hex").write_text(P.hexwords(m.stok, 16))
    (d / "ttok.hex").write_text(P.hexwords(m.ttok, 16))
    (d / "prime.hex").write_text(P.hexwords(prime, 16))
    (d / "exp_heads.hex").write_text(P.hexwords([0], 32))
    (d / "run.args").write_text(f"+TOKEN={y} +POS={pos} +NPRIME={len(prime)} +NHEAD=0 +EXPACC=0\n")
    # the step's tokens against the golden's non-speculative greedy stream
    a_ = m.accepted
    manifest["accepted"] = a_
    manifest["emitted"] = [int(t) for t in m.emitted]
    manifest["drafts"] = [int(t) for t in m.drafts]
    manifest["targets"] = [int(t) for t in m.ttok[:a.gamma + 1]]
    manifest["golden_next"] = [int(t) for t in toks[1:1 + a_ + 1]]
    manifest["emitted_equal_golden"] = manifest["emitted"] == manifest["golden_next"]
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print("emitted", manifest["emitted"], "golden", manifest["golden_next"], manifest["emitted_equal_golden"])


if __name__ == "__main__":
    main()
