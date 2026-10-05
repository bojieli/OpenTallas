#!/usr/bin/env python3
"""L1, the FUSED DSpark draft head on the V4.1 decode core (default off: --fused-head / enable()).

As built (tools/hdc_program_v41.py Builder.draft_body) each of the 5 serial draft-chain steps runs the lm_head
matvec (ME, logits LG written to the vector memory), the Markov row gather (SU), the Markov matvec (ME, MB), a
vocab-length LG + MB add (SU, AD_C) and a vocab-length top-1 SELECT (XU), then TOKX latches the XU's result.
The verify head already takes its argmax on the matrix engine's output stream (me_amax).  The fused head reuses
that datapath: the Markov op adds LG to every result on the engine's output stream, before the argmax tree
(rtl/hdc/v41/dspark_fused_head/ot_hdc_v41_matvec.sv, i_oacc), writes the argmax index where the next row's Markov
gather reads it (i_iwe), and TOKX latches the ME argmax.  The vocab-length SU add and XU SELECT are gone.

Exact: logits[i] = add(lm_head(h_i), Markov(e_prev)) is the golden's one RNE binary32 add per element (the
fused adder takes the addend LG first, as the golden does), and the argmax tree is the verify head's (largest,
ties to the lower row).  The drafts and every argmax value are checked against hdc_golden_v41.Model.draft.

Encoding (no ISA field added, hdc_isa_v41 / hdc_program_v41 / the as-built RTL stay byte-identical): an ME op
with the stream-unit field ad = AD_C is fused; its dst = DST_VM writes the index at element o_base (+ copy);
a TOKX with me_amax = 1 takes the ME argmax.  No as-built ME instruction sets ad or dst (asserted).

L2 compatibility (one ROM sweep for all slot vectors): the fused stage reads the addend at each copy's own output
address (+ p * ops) and writes copy p's index at o_base + p, so a batched lm_head that writes LG[slot p] composes
with a per-step Markov + fused add + argmax unchanged.

    python3 tools/dsrom_fused_draft_head.py slices --out DIR [--prompt gold4] [--forced] [--variant fused|as_built]
        (runs the NumPy golden: GPU host only)
    python3 tools/dsrom_fused_draft_head.py run --slices DIR --run-dir DIR [--as-built-core] [--jobs N]
        (Verilator, the slice bench rtl/test/tb_hdc_core_v41_mtp_slice_fh.sv; no model inference)
    python3 tools/dsrom_fused_draft_head.py record --runs DIR [--out results/rtl/dsrom_fused_draft_head_20261004]
        (collects the runs, prices the measured chain step at full shape with tools/dsrom_dspark_l1l2_compose.py)
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
SUCCESSOR = ROOT / "rtl/hdc/v41/dspark_fused_head"
NAMES = ("ot_hdc_v41_matvec.sv", "ot_hdc_core_v41.sv")
TB_FH = ROOT / "rtl/test/tb_hdc_core_v41_mtp_slice_fh.sv"
TB_ASBUILT = ROOT / "rtl/test/tb_hdc_core_v41_mtp_slice.sv"
HARNESS = ROOT / "rtl/test/hdc_core_v41_mtp_slice_harness.cpp"
DEFINE = "+define+OT_MTP_FUSED_HEAD=1"


def select(sources, *, enable=False):
    """The RTL source list with the fused-head successor (default off: unchanged)."""
    paths = list(map(Path, sources))
    if not enable:
        return dict(sources=paths, defines=[], enabled=False)
    for name in NAMES:
        if sum(p.name == name for p in paths) != 1:
            raise ValueError("missing/ambiguous source: " + name)
    return dict(sources=[SUCCESSOR / p.name if p.name in NAMES else p for p in paths], defines=[DEFINE],
                enabled=True)


# -- program and ISA model (patched in only by enable(True)) ---------------------------------------------------
def _imports():
    import hdc_isa_v41 as I
    import hdc_program_v41 as P
    import hdc_golden as G
    return I, P, G


def fused_draft_body(self, rows, sample=None):
    """Builder.draft_body with the fused head: per row, the lm_head op writes LG; the Markov op adds LG on its
    output stream and takes the argmax (no write of the sums), writing the index at DTOK + i; TOKX takes it."""
    I, P, _ = _imports()
    m, V_, lay = self.m, self.V, self.lay
    i = self.slot
    off = sample is not None and i >= sample
    self.draft_last = rows - 1
    self.su(set(), {"PF"}, "draft.embed", su_nout=1, su_nin=4, a_src=I.SRC_CLO, a_base=lay.cb["pre0"],
            a_si=1, dst=I.DST_VM, o_base=V_["PF"], o_si=1)
    emb = dict(a_d=P.DY["EMBED"]) if i == 0 else dict()
    self.su(set(), {"H", "SSX"}, "draft.embed", su_nout=4, su_nin=160, a_src=I.SRC_WROM,
            a_base=lay.emb_word * P.W * P.GR + (0 if i == 0 else m.noise_id * m.dim), a_si=1, dst=I.DST_VM,
            o_base=V_["H"], o_so=160, o_si=1, red=I.RED_SUM, red_sq=1, red_tree=1, r_base=V_["SSX"], **emb)
    for st in range(m.n_mtp):
        self.layer(m.L + st, draft=True)
    t = "draft.head"
    self.hc_pre("PF", "X", t, "SS")
    self.rmsnorm("X", 160, lay.cb["mtp_norm"], "XN", t, have_ss="SS")
    self.serial(True)               # the sampling chain: row i needs row i-1's token
    z = dict(me_nout=0) if off else {}
    self.me(lay.mat["head"], V_["XN"], V_["LG"], {"XN"}, {"LG"}, t, **z)
    g = dict(a_d=P.DY["TOK32"]) if i == 0 else dict(a_ind=I.IND_O, a_ibase=V_["DTOK"] + i - 1, a_so=32)
    self.su({"DTOK"}, {"MBX"}, t, su_nout=0 if off else 1, su_nin=32, a_src=I.SRC_WROM,
            a_base=lay.memb_word * P.W * P.GR, a_si=1, dst=I.DST_VM, o_base=V_["MBX"], o_si=1, **g)
    self.me(lay.mat["markov"], V_["MBX"], V_["LG"], {"MBX", "LG"}, {"DTOK"}, t, me_oen=0, me_amax=1,
            ad=I.AD_C, dst=I.DST_VM, o_base=V_["DTOK"] + i, **z)
    self.emit(dict(unit=I.UNIT_CTL, ctl=I.CTL_TOKX, ctl_slot=i + 1, ctl_lane=0, wait=1 << (I.UNIT_ME - 1),
                   me_amax=1), set(), set(), t)
    self.serial(False)


def is_fused(f):
    I, _, _ = _imports()
    return f["unit"] == I.UNIT_ME and f.get("ad", 0) == I.AD_C


def fused_me_lane(self, f, n, tiles, K, lane, ret=False):
    """Machine.me_lane for a fused op: the Markov sums, + the word at each result's own output address (the
    golden's add(lm_head, Markov)), the argmax of the sums (np.argmax: largest, first on ties), the index write."""
    I, P, G = _imports()
    if ret or not is_fused(f):
        return _ORIG["me_lane"](self, f, n, tiles, K, lane, ret)
    assert f["me_mmode"] == 0 and f["me_ots"] == P.IL and f["me_ojs"] == 1 and not f["me_wsrc"]
    ob = (f["me_obase"] + self.dyn[f["me_d_obase"]] + lane * f["mx_ops"]) * P.W
    addend = self.vm[ob:ob + n].copy()
    _ORIG["me_lane"](self, dict(f, me_oen=1, me_amax=0), n, tiles, K, lane)
    acc = self.vm[ob:ob + n].copy()
    s = G.add(addend, acc)
    self.vm[ob:ob + n] = s if f["me_oen"] else addend
    idx = int(np.argmax(s))
    self.amax_lane[lane] = idx
    self.fh_log.append((idx, int(G.bits(np.asarray([s[idx]], dtype=np.float32))[0])))
    if f.get("dst", 0) == I.DST_VM:
        self.vm[f["o_base"] + lane] = np.array([idx], dtype=np.uint32).view(np.float32)[0]


def fused_control(self, f):
    I, _, _ = _imports()
    if f["ctl"] == I.CTL_TOKX:
        j = f["ctl_slot"]
        tok = self.amax_lane[f["ctl_lane"]] if f.get("me_amax", 0) else self.sel_first
        self.tokx_log.append(int(tok))
        self.stok[j] = tok
        self.drafts = self.stok[1:j + 1]
        return
    return _ORIG["control"](self, f)


_ORIG = {}


def enable(on=True):
    """Patch the builder's draft body (fused head) and the ISA model (fused ME op, TOKX from the ME); the ISA
    model's TOKX / fused logs are installed either way (enable(False) restores the as-built draft body)."""
    _, P, _ = _imports()
    if not _ORIG:
        _ORIG.update(draft_body=P.Builder.draft_body, me_lane=P.Machine.me_lane, control=P.Machine.control,
                     init=P.Machine.__init__)

        def init(self, *a, **k):
            _ORIG["init"](self, *a, **k)
            self.fh_log, self.tokx_log = [], []
        P.Machine.__init__ = init
        P.Machine.me_lane = fused_me_lane
        P.Machine.control = fused_control
    P.Builder.draft_body = fused_draft_body if on else _ORIG["draft_body"]


# -- slices -----------------------------------------------------------------------------------------------------
def golden_drafts(model, prompt, gamma, step, forced=None):
    """hdc_golden_v41: speculative step `step`'s DSpark drafts and logit rows (Model.draft); with `forced`, every
    step's drafts are then replaced by the forced drafter's (as the ISA model's / RTL's DYN step does)."""
    got = []

    def drafter(y, q, state):
        d, lg = model.draft(y, q, state)
        got.append(([int(x) for x in d], [np.asarray(x, dtype=np.float32) for x in lg]))
        return forced(q, list(d)[:gamma]) if forced else d
    model.generate_spec(prompt, 2 + (gamma + 1) * step, gamma=gamma, drafter=drafter)
    d, lg = got[step]
    return d[:gamma], lg[:gamma]


def cmd_slices(a):
    import rtl_hdc_v41_mtp_campaign as C
    import dsrom_dspark_step_slices as S
    I, P, G = _imports()
    V = C.V
    enable(a.variant == "fused")
    model = V.Model()
    prompt = C.prompts()[a.prompt]
    lay = P.mtp_layout(model, a.gamma)
    prog, entry = P.build_mtp(lay, a.gamma, 1)
    for n in range(entry, len(prog)):
        f = prog[n]
        if f["unit"] == I.UNIT_ME and not is_fused(f):
            assert not f.get("ad", 0) and not f.get("dst", 0), (n, f.get("_tag"))
    sections, end = S.plan(prog, entry)
    names = [nm for nm, _, _ in sections]
    upto = names.index("draft_1")                      # the draft chain: the last draft section
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    rom = out / "rom"
    if not (rom / "prog.hex").exists() or a.variant_rom:
        P.write_images(rom, lay, prog)
    m = P.Machine(lay, np.zeros(I.KV_WORDS * C.P.W, dtype=np.float32), np.zeros(lay.vm.size, dtype=np.float32))
    for p, t in enumerate(prompt):
        m.run(prog, t, p, entry=0)
    y, pos = int(m.argmax), len(prompt)
    forced = None
    if a.forced:
        toks, _ = C.golden_run(model, prompt, 1 + (a.gamma + 1) * (a.steps_before + 1) + 1)
        forced = C.forced_drafter(list(prompt) + [int(t) for t in toks], a.gamma)
    for k in range(a.steps_before):                    # whole earlier speculative steps (ISA model)
        if forced:
            m.force = lambda d, q=pos - 1: forced(q, d)
        m.run(prog, y, pos, entry=entry)
        pos, y = pos + 1 + m.accepted, int(m.argmax)
    m.force = None
    gd, glog = golden_drafts(model, prompt, a.gamma, a.steps_before, forced)
    prime = [int(model.engram.token_map[t]) for t in m.tokens][-3:]
    m.token, m.pos = y, pos
    m.stok = [y] + [0] * (I.NSLOT - 1)
    m.ttok = [0] * I.NSLOT
    m.banks = [I.dyn_values(m.stok[j], pos + j) for j in range(I.NSLOT)]
    m.accepted, m.drafts, m.slot_logits = None, [], {}
    m.fh_log, m.tokx_log = [], []
    endw = I.encode(**{k: v for k, v in prog[end].items() if not k.startswith("_")})
    rec = {"prompt": a.prompt, "variant": a.variant, "gamma": a.gamma, "pos": pos, "token": y, "entry": entry,
           "drafter": "forced" if a.forced else "dspark", "steps_before": a.steps_before,
           "slices": []}
    for k, (name, s0, s1) in enumerate(sections[:upto + 1]):
        if name != "draft_1" and not a.all_draft:
            S.step(m, prog, s0, s1)
            continue
        before = S.snap(m)
        nt = len(m.tokx_log)
        nf = len(m.fh_log)
        S.step(m, prog, s0, s1)
        after = S.snap(m)
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        words = [I.encode(**{k_: v for k_, v in f.items() if not k_.startswith("_")}) for f in prog[s0:s1]] + [endw]
        (d / "prog.hex").write_text(P.hexwords(words, I.INSTR_BITS))
        (d / "vm_init.hex").write_text(P.hexwords(S.vm_words(before["vm"]), 32))
        (d / "kv_init.hex").write_text(P.hexwords(G.bits(before["kv"]).reshape(-1), 32))
        (d / "expect_vm.hex").write_text(P.hexwords(S.vm_words(after["vm"]), 32))
        (d / "expect_kv.hex").write_text(P.hexwords(G.bits(after["kv"]).reshape(-1), 32))
        (d / "stok.hex").write_text(P.hexwords(before["stok"], 16))
        (d / "ttok.hex").write_text(P.hexwords(before["ttok"], 16))
        (d / "prime.hex").write_text(P.hexwords(prime, 16))
        (d / "exp_heads.hex").write_text(P.hexwords([0], 32))
        (d / "exp_stok.hex").write_text(P.hexwords(after["stok"], 16))
        toks = m.tokx_log[nt:]
        vals = [v for _, v in m.fh_log[nf:]] if a.variant == "fused" else [0] * len(toks)
        tw = [w for tv in zip(toks, vals) for w in tv] or [0]
        (d / "exp_tokx.hex").write_text(P.hexwords(tw, 32))
        args = [f"+TOKEN={y}", f"+POS={pos}", f"+NPRIME={len(prime)}", "+NHEAD=0", "+EXPACC=0",
                f"+NTOKX={len(toks)}", f"+NTOKVAL={1 if a.variant == 'fused' else 0}"]
        (d / "run.args").write_text(" ".join(args) + "\n")
        units = {}
        for f in prog[s0:s1]:
            units[f["unit"]] = units.get(f["unit"], 0) + 1
        rec["slices"].append({"name": name, "pc": [s0, s1], "instructions": s1 - s0,
                              "units": {str(k_): v for k_, v in sorted(units.items())}, "tokx": toks})
        print(name, s0, s1, toks, flush=True)
    drafts = [int(x) for x in m.stok[1:a.gamma + 1]]
    gvals = [int(G.bits(np.asarray([lg[t]], dtype=np.float32))[0]) for lg, t in zip(glog, gd)]
    gargmax = [int(np.argmax(lg)) for lg in glog]
    rec["isa_drafts"] = drafts
    rec["golden_drafts"] = gd
    rec["golden_argmax_of_logits"] = gargmax
    rec["drafts_equal_golden"] = drafts == gd == gargmax
    if a.variant == "fused":
        rec["isa_argmax_values"] = [v for _, v in m.fh_log[:a.gamma]]
        rec["golden_argmax_values"] = gvals
        rec["values_equal_golden"] = rec["isa_argmax_values"] == gvals
    (out / "manifest.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in rec if k != "slices"}))
    ok = rec["drafts_equal_golden"] and rec.get("values_equal_golden", True)
    return 0 if ok else 1


# -- RTL ----------------------------------------------------------------------------------------------------------
SLICE = re.compile(r"SLICE cycles=(\d+) heads=(\d+) head_mismatches=(\d+) acc_n=(\d+) exp_acc_n=(\d+) "
                   r"vm_mismatch=(\d+) kv_mismatch=(\d+) fault=(\d+) busy_me=(\d+) busy_su=(\d+) busy_qe=(\d+) "
                   r"busy_xu=(\d+) busy_he=(\d+)")
FH = re.compile(r"FH tokx=(\d+) exp_tokx=(\d+) tokx_bad=(\d+) stok_bad=(\d+)")
TOKX = re.compile(r"TOKX (\d+) tok=(\d+) val=([0-9a-fx]+) cyc=(\d+)")
KEYS = ("cycles", "heads", "head_mismatches", "acc_n", "exp_acc_n", "vm_mismatch", "kv_mismatch", "fault",
        "busy_me", "busy_su", "busy_qe", "busy_xu", "busy_he")


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sources(fused, sink=True):
    import rtl_hdc_v41_mtp_campaign as C
    from dsrom_sink_handshake import select as sink_select
    s = sink_select(C.RTL, enable=sink)
    f = select(s["sources"], enable=fused)
    return f["sources"], s["defines"] + f["defines"], C


def cmd_run(a):
    fused = not a.as_built_core
    srcs, defs, C = sources(fused)
    if a.capture_cut:
        if not fused: raise ValueError("capture cut requires fused candidate")
        candidate=SUCCESSOR/'capture_candidate'
        srcs=[candidate/p.name if p.name in NAMES else p for p in srcs]
        srcs=srcs+[ROOT/"rtl/hdc"/(n+".sv") for n in ("ot_hdc_fastfp","ot_hdc_prefix","ot_hdc_fp32_add_lat")]
        defs=defs+["+define+OT_FH_ALAT=7","+define+OT_FH_CAPTURE=1",f"+define+OT_FH_RETURN_EXTRA={a.capture_return_extra}"]
        tb=candidate/'tb_hdc_core_v41_mtp_slice_capture.sv'
    else:
        tb = TB_FH if fused else TB_ASBUILT
    obj = a.run_dir / "obj"
    a.run_dir.mkdir(parents=True, exist_ok=True)
    if not (obj / "Vtb_hdc_core_v41_mtp_slice").exists():
        subprocess.run(["verilator", "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                        "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "--top-module", "tb_hdc_core_v41_mtp_slice", "-Mdir",
                        str(obj), f"-I{C.SVH.parent}", f"+define+HDC_SW={C.I.SU_LANES}", "+define+HDC_MP=1", *defs,
                        *map(str, srcs), str(tb), str(HARNESS), "-CFLAGS", "-O1", "-j", "8"], check=True)
    exe = obj / "Vtb_hdc_core_v41_mtp_slice"
    rom = (a.slices / "rom").resolve()
    names = [s.name for s in sorted(a.slices.iterdir()) if (s / "prog.hex").exists() and s.name != "rom"]

    def run(name):
        d = (a.slices / name).resolve()
        log = a.run_dir / f"{name}.log"
        with log.open("w") as fh:
            rc = subprocess.run([str(exe), f"+DIR={d}", f"+ROMDIR={rom}", *(d / "run.args").read_text().split()],
                                stdout=fh, stderr=subprocess.STDOUT).returncode
        out = log.read_text(errors="replace")
        m = SLICE.search(out)
        r = {"name": name, "returncode": rc, "pass": rc == 0 and m is not None and "PASS" in out.split()}
        if m:
            r.update(zip(KEYS, map(int, m.groups())))
        fh_m = FH.search(out)
        if fh_m:
            r.update(zip(("tokx", "exp_tokx", "tokx_bad", "stok_bad"), map(int, fh_m.groups())))
        r["tokx_events"] = [dict(tok=int(t), val=v, cyc=int(c)) for _, t, v, c in TOKX.findall(out)]
        if not m:
            r["tail"] = out.splitlines()[-10:]
        return r

    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        res = list(ex.map(run, names))
    rec = {"core": "ot_hdc_core_v41" + (" + dspark_fused_head" if fused else ""), "sink_handshake": True,
           "fused_core": fused, "defines": defs, "tb": str(tb.relative_to(ROOT)), "slices": res,
           "all_pass": all(r["pass"] for r in res),
           "manifest": json.loads((a.slices / "manifest.json").read_text()),
           "input_sha256": {str(Path(p).resolve().relative_to(ROOT)): digest(p) for p in
                            (C.SVH, *srcs, tb, HARNESS, Path(__file__).resolve())}}
    (a.run_dir / "result.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"all_pass": rec["all_pass"], "slices": [{k: r.get(k) for k in ("name", "pass", "cycles",
                                                                                     "busy_me", "busy_su", "busy_xu")}
                                                             for r in res]}, indent=1))
    return 0 if rec["all_pass"] else 1


REC = ROOT / "results/rtl/dsrom_fused_draft_head_20261004"
COMP = ROOT / "results/rtl/dsrom_dspark_step_slices_20261004/composition.json"
FULL_DIM, MARKOV_IN, FULL_HEAD_CYC = 4096, 32, 12.37 * 1200     # S81 head occupancy at the 1.2 GHz stream clock


def cmd_record(a):
    out = a.out
    (out / "runs").mkdir(parents=True, exist_ok=True)
    runs = {}
    for d in sorted(a.runs.iterdir()):
        if (d / "result.json").exists():
            r = json.loads((d / "result.json").read_text())
            (out / "runs" / f"{d.name}.json").write_text(json.dumps(r, indent=1) + "\n")
            runs[d.name] = r

    def chain(r):
        s = r["slices"][0]
        cyc = [0] + [e["cyc"] for e in s["tokx_events"]]
        return dict(cycles=s["cycles"], steps=[b - a_ for a_, b in zip(cyc, cyc[1:])], busy_me=s["busy_me"],
                    busy_su=s["busy_su"], busy_xu=s["busy_xu"], pass_=s["pass"])
    fused = {k: chain(v) for k, v in runs.items() if v["fused_core"] and k.startswith("fused-")}
    asb = {k: chain(v) for k, v in runs.items() if k.startswith("as_built-") and not v["fused_core"]}
    off = {k: chain(v) for k, v in runs.items() if k.startswith("as_built-") and v["fused_core"]}
    comp = json.loads(COMP.read_text())
    head6 = comp["measured_reduced"]["verify_head6_cycles"]
    f_step = next(iter(fused.values()))["steps"][-1]
    a_step = comp["measured_reduced"]["draft_head_chain5_cycles"] / 5
    me_tail = (next(iter(fused.values()))["busy_me"] - next(iter(asb.values()))["busy_me"]) / 5
    r_red = f_step / (head6 / 6)
    r_full = 1 + MARKOV_IN / FULL_DIM + me_tail / FULL_HEAD_CYC
    ok = all(v["pass_"] for d in (fused, asb, off) for v in d.values())
    same = all(len(set(json.dumps([v["cycles"], v["steps"]]) for v in d.values())) == 1 for d in (fused, asb, off))
    off_identical = all(off[k]["cycles"] == asb[k.replace(".fusedcore", ".asbuiltcore")]["cycles"] for k in off
                        if k.replace(".fusedcore", ".asbuiltcore") in asb)
    exact = {k: {x: v["manifest"].get(x) for x in ("prompt", "drafter", "steps_before", "pos", "isa_drafts",
                                                    "golden_drafts", "drafts_equal_golden", "isa_argmax_values",
                                                    "golden_argmax_values", "values_equal_golden")}
             for k, v in runs.items() if k.startswith("fused-")}
    comp_out = out / "l1_compose.json"
    subprocess.run([sys.executable, str(ROOT / "tools/dsrom_dspark_l1l2_compose.py"), "--out", str(comp_out),
                    "--l1-chain-ratio", f"{r_full:.6f}"], check=True, capture_output=True)
    l1 = json.loads(comp_out.read_text())
    rec = dict(schema="opentallas.dsrom-fused-draft-head.v1",
               lever="L1: fused DSpark draft head (bias add + argmax on the ME output stream), default off",
               all_pass=ok, chain_steps_identical_across_prompts_drafters=same,
               default_off_cycle_identical=off_identical,
               exact=exact, drafts_and_values_equal_golden=all(e["drafts_equal_golden"] and e["values_equal_golden"]
                                                               for e in exact.values()),
               measured_reduced=dict(fused_chain5_cycles=next(iter(fused.values()))["cycles"],
                                     as_built_chain5_cycles=next(iter(asb.values()))["cycles"],
                                     fused_step_cycles=f_step,
                                     as_built_step_cycles=next(iter(off.values()))["steps"][-1],
                                     as_built_step_cycles_composition=a_step,
                                     verify_head_step_cycles=head6 / 6, fused_me_tail_cycles_per_step=me_tail,
                                     fused_chain_step_over_head_step=round(r_red, 5),
                                     model_expectation_reduced=1 + MARKOV_IN / 160),
               full_shape=dict(l1_chain_ratio=round(r_full, 6),
                               basis="1 + Markov/lm_head MACs (32/4096) + the measured fused ME tail (cycles) over "
                                     "the S81 head occupancy (12.37 us x 1.2 GHz); the reduced vehicle measures "
                                     f"{r_red:.4f} against its model 1.2 (the gather hides behind the lm_head op)",
                               compose=l1),
               source_commit=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                            text=True).stdout.strip())
    (out / "record.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("all_pass", "default_off_cycle_identical", "drafts_and_values_equal_golden",
                                          "measured_reduced")}, indent=1))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("slices")
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--prompt", default="gold4")
    s.add_argument("--gamma", type=int, default=5)
    s.add_argument("--variant", choices=("fused", "as_built"), default="fused")
    s.add_argument("--forced", action="store_true", help="earlier steps use the campaign's forced drafter")
    s.add_argument("--steps-before", type=int, default=0, help="whole speculative steps run before the chain")
    s.add_argument("--all-draft", action="store_true", help="also emit the draft embed / block slices")
    s.add_argument("--variant-rom", action="store_true", help="rewrite the ROM images even if present")
    r = sub.add_parser("run")
    r.add_argument("--slices", type=Path, required=True)
    r.add_argument("--capture-cut", action="store_true", help="Default-off protected return/capture candidate")
    r.add_argument("--capture-return-extra", type=int, choices=(2,3), default=2, help="Matched protected return extra stages;2 retained,3 decode-split")
    r.add_argument("--run-dir", type=Path, required=True)
    r.add_argument("--as-built-core", action="store_true")
    r.add_argument("--jobs", type=int, default=8)
    c = sub.add_parser("record")
    c.add_argument("--runs", type=Path, required=True)
    c.add_argument("--out", type=Path, default=REC)
    a = ap.parse_args()
    return {"slices": cmd_slices, "run": cmd_run, "record": cmd_record}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
