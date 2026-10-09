#!/usr/bin/env python3
"""RTL campaign for the DS-ROM Engram lookup (stream engram, 2026-10-08): the HBM-resident Engram tables.

DUT (rtl/dsrom_sys/engram/): ot_dsrom_engram_idwin (S0: per-user n-gram window, official blocking rule) ->
2 layers x 4 TP ranks of ot_dsrom_engram_lookup (hash -> 6 own-column row reads from a behavioural HBM region ->
alignment, CRC check -> row beats) -> behavioural TP4 all-gather -> 2 x 4 ot_dsrom_engram_rowsink (FP8 -> BF16
decode into the prefetch buffer).  Bench rtl/test/tb_dsrom_engram_lookup.sv.

Every expected value comes from the golden:
* windows: the official NgramHashState rule (inference/engram.py: per-position look-back through the per-user
  cache, blocked by the sequence start and by DEAD tokens), restated here on the cache exactly as the code does;
* rows: tools/hdc_golden_v41.EngramTables.hashes on the shipped tables (hdc_v41_engram_shipped.shipped_tables)
  for the window; content = hdc_v41_engram_shipped.row_bytes; decode = the golden's own
  to_bf16((E4M3[codes] * np.exp2(sc)).astype(F)) (rtl_hdc_v41_engram_gather_campaign.expected_words).
Rank 0's buffer is compared element for element; the bench checks the 4 ranks' buffers are identical.

Streams: 8 users interleaved at random, with sequence restarts, DEAD (image) spans, the pad id, id extremes and
uniform random compressed ids.  Modes: ideal HBM (240-cycle = 200 ns read, the technology.json upper bound), an
isolated token with the modelled all-gather (latency), a stressed one (random latency, reordering across and within
requests, stalls, gaps, input bubbles, consumer delays, all-gather jitter), CRC error injection (every 7th window's
row 0 on rank 0 of both layers: those tokens must come back poisoned and every other token exact), and an 8-slot
build (MTP prefetch depth, the routed configuration).  Mutations must be caught.  Writes results/rtl/dsrom_engram_lookup_campaign.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_v41_engram_shipped as ES  # noqa: E402
import rtl_hdc_v41_engram_gather_campaign as GC  # noqa: E402

OUT = ROOT / "results/rtl/dsrom_engram_lookup_campaign.json"
D = ROOT / "rtl/dsrom_sys/engram"
IDWIN, LOOKUP, SINK = D / "ot_dsrom_engram_idwin.sv", D / "ot_dsrom_engram_lookup.sv", D / "ot_dsrom_engram_rowsink.sv"
GATHER = ROOT / "rtl/hdc/v41/ot_hdc_engram_gather.sv"          # ot_hdc_engram_e4m3_bf16 (the decode cell)
TB = ROOT / "rtl/test/tb_dsrom_engram_lookup.sv"
HARNESS = ROOT / "rtl/test/hdc_v41_tb_harness.cpp"
WRAPPER = D / "dsfd_engram_lkp.sv"
SOURCES = [ES.PKG, ES.HASH_OUT, GATHER, IDWIN, LOOKUP, SINK, WRAPPER]
LINT = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-BLKSEQ", "-Wno-PINCONNECTEMPTY",
        "-Wno-IMPORTSTAR")
VL = ("--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ")
CV = ES.SHIPPED["engram_compressed_vocab_size"]
PAD = 2
DEAD = -1
NU = 8
AG_MODEL = 1426     # modelled TP4 all-gather of 1,584 B a rank (design.json transport.allgather_cycles)
RE_E = re.compile(r"ENGRAM tokens=(\d+) windows=(\d+) window_errors=(\d+) dumped=(\d+) xrank_errors=(\d+) "
                  r"poisoned=(\d+) injected=\d+ faults=([01]+) cycles=(\d+) lat0_min=(\d+) lat0_max=(\d+) "
                  r"lat0_sum=(\d+) lat1_min=(\d+) lat1_max=(\d+) lat1_sum=(\d+)")
MODES = [
    ("ideal_hbm_200ns", dict(LAT=240), None, 2),
    ("ideal_hbm_200ns_core_unwrapped", dict(LAT=240), 400, (2, 0, 0)),
    ("isolated_token_hbm_200ns_allgather_model", dict(LAT=240, SPACED=1, AGLAT=AG_MODEL), 120, 2),
    ("isolated_token_hbm_200ns_local_allgather", dict(LAT=240, SPACED=1, AGLAT=4), 120, 2),
    ("stressed", dict(LAT=60, JIT=400, STALL=30, GAP=30, REORD=1, BUB=40, CDEL=300, AGLAT=20, AGJIT=60), None, 2),
    ("crc_injection_stressed", dict(LAT=60, JIT=200, STALL=20, GAP=20, REORD=1, BUB=30, CDEL=100, AGLAT=20,
                                    AGJIT=40, ERR=1), 400, 2),
    ("stressed_8_slots_mtp", dict(LAT=60, JIT=400, STALL=30, GAP=30, REORD=1, BUB=10, CDEL=300, AGLAT=20, AGJIT=60), 500, 8),
    ("stressed_pipe1", dict(LAT=60, JIT=400, STALL=30, GAP=30, REORD=1, BUB=40, CDEL=300, AGLAT=20, AGJIT=60), 600, (2, 1)),
    ("crc_injection_pipe1", dict(LAT=60, JIT=200, STALL=20, GAP=20, REORD=1, BUB=30, CDEL=100, AGLAT=20,
                                 AGJIT=40, ERR=1), 300, (2, 1)),
    ("isolated_token_pipe1_local_allgather", dict(LAT=240, SPACED=1, AGLAT=4), 60, (2, 1)),
]
MUT_MODE = ("mutation", dict(LAT=60, JIT=200, STALL=20, GAP=20, REORD=1, BUB=30, CDEL=150, AGLAT=20, AGJIT=40, ERR=1),
            160)
MUTATIONS = [
    (LOOKUP, "row alignment ignored (offset in atom forced 0)", "roff[j] <= r8[j][4:3];", "roff[j] <= 2'd0;"),
    (LOOKUP, "column offset not subtracted", "wire [RW-1:0] lr = row_m - off_q;", "wire [RW-1:0] lr = row_m;"),
    (LOOKUP, "neighbouring column read (wrong column of the rank)",
     "assign rows_c[RW*gc +: RW]  = hrow[RW*C +: RW];", "assign rows_c[RW*gc +: RW]  = hrow[RW*(C ^ 1) +: RW];"),
    (LOOKUP, "rank strap ignored for the column base", "assign cbs_c[ABW*gc +: ABW] = CB[ABW-1:0];",
     "assign cbs_c[ABW*gc +: ABW] = col_base(gc / 4, 0, gj);"),
    (LOOKUP, "scale taken from the atom's first byte", "e2_scale <= e1_a8s[7:0];", "e2_scale <= e1_a8[7:0];"),
    (LOOKUP, "hash history not reset per window", ".in_first(hfeed && fcnt == 2'd0)", ".in_first(1'b0)"),
    (LOOKUP, "CRC check disabled", "st_bad <= (crc_byte(crc, e3_scale) != e3_exp);", "st_bad <= 1'b0;"),
    (LOOKUP, "credits ignored", "if ((acc_n - rel_n[r]) >= NSLOT[CW-1:0]) credit_ok = 1'b0;", "credit_ok = 1'b1;"),
    (SINK, "slot ready one beat early", "assign rdy[gt] = (cnt[gt] == TOT[TW-1:0]) &&",
     "assign rdy[gt] = (cnt[gt] >= TOT[TW-1:0] - 1) &&"),
    (SINK, "row statuses not awaited", "&& (scnt[gt] == NC[5:0]);", ";"),
    (IDWIN, "DEAD history does not block", "wire           b1 = b0 | (n < 4'd1) | hdd[a1];",
     "wire           b1 = b0 | (n < 4'd1);"),
    (IDWIN, "MTP rewind ignored", "wp[3*rb_user +: 3] <= rwp - rb_n;", "wp[3*rb_user +: 3] <= rwp;"),
    (IDWIN, "MTP rewind leaves the position count", "np[4*rb_user +: 4] <= rnp - {1'b0, rb_n};",
     "np[4*rb_user +: 4] <= rnp;"),
    (IDWIN, "sequence start not honoured", "wire [3:0]     n   = t_first ? 4'd0 : np[4*t_user +: 4];",
     "wire [3:0]     n   = np[4*t_user +: 4];"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# -- vectors --------------------------------------------------------------------------------
def official_windows(events):
    """The official NgramHashState rule on a per-user cache: for position p of a user's sequence,
    source_k = cache[max(p - k, 0)], blocked_k = blocked_(k-1) | (p < k) | (source_k == DEAD), w_k = pad if
    blocked_k else source_k (inference/engram.py NgramHashState.forward, decode one position at a time)."""
    cache, out = {}, []
    for kind, u, first, dead, cid in events:
        if kind:                                   # MTP rejected drafts: the cache truncated to the accepted prefix
            del cache[u][len(cache[u]) - cid:]
            continue
        if first or u not in cache:
            cache[u] = []
        cache[u].append(DEAD if dead else cid)
        p = len(cache[u]) - 1
        blocked, w = False, []
        for k in range(4):
            src = cache[u][max(p - k, 0)]
            blocked = blocked or p < k or src == DEAD
            w.append(PAD if blocked else src)
        out.append(w)
    return out


def build_events(rng, n_tok):
    special = [PAD, 0, CV - 1, (1 << ES.ID_W) - 1, 1]
    ev, started, ntok = [], set(), 0
    dead_left = {u: 0 for u in range(NU)}
    seqlen = {u: 0 for u in range(NU)}
    since = {u: 0 for u in range(NU)}            # tokens pushed since the last rewind (a step's drafts)
    while ntok < n_tok:
        u = int(rng.integers(0, NU))
        if u in started and since[u] > 0 and rng.random() < 0.08:
            nmax = min(5, seqlen[u] - 1, since[u])
            if nmax >= 1:
                n = int(rng.integers(1, nmax + 1))
                ev.append((1, u, 0, 0, n))
                seqlen[u] -= n
                since[u] = 0
                continue
        first = u not in started or rng.random() < 0.02
        started.add(u)
        if dead_left[u] == 0 and rng.random() < 0.03:
            dead_left[u] = int(rng.integers(1, 6))
        dead = dead_left[u] > 0
        dead_left[u] = max(0, dead_left[u] - 1)
        r = rng.random()
        cid = int(rng.choice(special)) if r < 0.08 else int(rng.integers(0, CV))
        ev.append((0, u, int(first), int(dead), cid))
        seqlen[u] = 1 if first else seqlen[u] + 1
        since[u] = 0 if first else since[u] + 1
        ntok += 1
    return ev


def write_vectors(path: Path, ev, wins):
    it, lines = iter(wins), []
    for k, u, f, d, c in ev:
        w = [0, 0, 0, 0] if k else next(it)
        lines.append(f"{k:x} {u:x} {f:x} {d:x} {c:x} " + " ".join(f"{x:x}" for x in w) + "\n")
    path.write_text("".join(lines))


def expected(t, w, li):
    rows = ES.hashes(t, [w[3], w[2], w[1], w[0]])[li]
    return GC.expected_words(li, rows)


def compare(out_path: Path, t, wins, injected):
    lines = out_path.read_text().split("\n")
    i, dumps, elems, bad, seen, pois = 0, 0, 0, 0, set(), set()
    while i < len(lines) and lines[i].startswith("T "):
        _, tk, _, li, _, p = lines[i].split()
        tk, li, p = int(tk), int(li), int(p)
        got = lines[i + 1:i + 1 + 192]
        if p:
            pois.add((tk, li))
        else:
            exp = expected(t, wins[tk], li)
            for g, e in zip(got, exp):
                elems += 32
                if g != e:
                    bad += sum(g[4 * j:4 * j + 4] != e[4 * j:4 * j + 4] for j in range(32))
            bad += 32 * max(0, 192 - len(got))
        seen.add((tk, li))
        dumps += 1
        i += 193
    want_pois = {(tk, li) for tk in injected for li in range(2)}
    return dumps, elems, bad, seen == {(tk, li) for tk in range(len(wins)) for li in range(2)}, pois, want_pois


# -- simulation -----------------------------------------------------------------------------
def build(obj: Path, sources, nslot, pipe=0, wrap=1):
    exe = obj / "Vtb_dsrom_engram_lookup"
    subprocess.run(["verilator", *VL, "--top-module", "tb_dsrom_engram_lookup", f"-GNSLOT={nslot}", f"-GPIPE={pipe}",
                    f"-GWRAP={wrap}",
                    "-Mdir", str(obj),
                    *map(str, sources), str(TB), str(HARNESS), "-CFLAGS", "-O1 -DVTOP=Vtb_dsrom_engram_lookup"],
                   check=True, capture_output=True)
    return exe


def run_mode(exe, s: Path, t, ev, wins, name, args, limit):
    n = len(ev) if limit is None else min(limit, len(ev))
    nt = sum(1 for e in ev[:n] if e[0] == 0)
    vec, out = s / f"{name}.vec", s / f"{name}.out"
    write_vectors(vec, ev[:n], wins[:nt])
    text = subprocess.run([str(exe), f"+VEC={vec}", f"+OUT={out}", *(f"+{k}={v}" for k, v in args.items())],
                          capture_output=True, text=True, timeout=7200).stdout
    m = RE_E.search(text)
    if not m:
        return {"pass": False, "log": text[-1500:]}
    v = m.groups()
    injected = sorted(int(x) for x in re.findall(r"^INJ (\d+)$", text, re.M))
    nt = int(v[0])
    rec = {"tokens": nt, "windows": int(v[1]), "window_errors": int(v[2]), "dumps": int(v[3]),
           "xrank_errors": int(v[4]), "poisoned_dumps": int(v[5]), "engine_faults": v[6], "cycles": int(v[7]),
           "latency_cycles_window_to_slot_ready": {
               "layer_1": {"min": int(v[8]), "max": int(v[9]), "mean": round(int(v[10]) / max(nt, 1), 1)},
               "layer_14": {"min": int(v[11]), "max": int(v[12]), "mean": round(int(v[13]) / max(nt, 1), 1)}},
           "bench_pass": "DONE" in text, "injected_tokens": len(injected)}
    d, e, b, complete, pois, want = compare(out, t, wins[:nt], injected)
    out.unlink(missing_ok=True)
    rec.update(dumps_compared=d, elements_compared=e, element_mismatches=b, all_dumps_present=complete,
               poisoned_as_injected=(pois == want), rewinds=n - nt)
    clean = nt * 2 - len(want)
    rec["pass"] = bool(rec["bench_pass"] and b == 0 and complete and pois == want and rec["window_errors"] == 0
                       and rec["xrank_errors"] == 0 and e == clean * 24 * 256
                       and (args.get("ERR") or rec["engine_faults"].count("1") == 0)
                       and (not args.get("ERR") or len(injected) > 0))
    rec["model"] = args
    return rec


def mutations(s: Path, t, ev, wins):
    name, args, limit = MUT_MODE
    res = []
    ctrl = run_mode(build(s / "mut_ctrl", SOURCES, 2), s, t, ev, wins, "mut_ctrl", args, limit)
    res.append({"mutation": "none (control)", "control": True, "caught": not ctrl["pass"]})
    for i, (src, what, a, b) in enumerate(MUTATIONS):
        text = src.read_text()
        assert text.count(a) == 1, (what, text.count(a))
        d = s / f"mut{i}"
        d.mkdir()
        m = d / src.name
        m.write_text(text.replace(a, b))
        srcs = [m if p == src else p for p in SOURCES]
        try:
            rec = run_mode(build(d / "obj", srcs, 2), d, t, ev, wins, f"mut{i}", args, limit)
            caught = not rec["pass"]
            detail = {k: rec.get(k) for k in ("window_errors", "element_mismatches", "xrank_errors",
                                              "poisoned_as_injected", "bench_pass", "all_dumps_present")}
        except subprocess.CalledProcessError as e:
            caught, detail = True, {"build_failed": (e.stderr or b"")[-300:].decode(errors="replace")}
        res.append({"mutation": what, "file": str(src.relative_to(ROOT)), "caught": caught, "detail": detail})
        print("mutation", what, "caught" if caught else "MISSED", flush=True)
    return res


def run(quick=False, no_mut=False) -> dict:
    rng = np.random.default_rng(20261008)
    t = ES.shipped_tables()
    ev = build_events(rng, 120 if quick else 1500)
    wins = official_windows(ev)
    lint = {}
    for top, files in (("ot_dsrom_engram_lookup", [ES.PKG, ES.HASH_OUT, LOOKUP]),
                       ("ot_dsrom_engram_lookup -GPIPE=1", [ES.PKG, ES.HASH_OUT, LOOKUP]),
                       ("dsfd_engram_lkp", [ES.PKG, ES.HASH_OUT, LOOKUP, WRAPPER]),
                       ("ot_dsrom_engram_rowsink", [ES.PKG, GATHER, SINK]), ("ot_dsrom_engram_idwin", [IDWIN])):
        extra = ["-GPIPE=1"] if "PIPE=1" in top else []
        r = subprocess.run(["verilator", "--lint-only", *LINT, *extra, "--top-module", top.split()[0], *map(str, files)],
                           capture_output=True, text=True)
        lint[top] = {"returncode": r.returncode, "messages": r.stderr.strip().splitlines()[:10]}
    modes = {}
    with tempfile.TemporaryDirectory(prefix="engram-lkp-", dir="/tmp/claude-1000") as scratch:
        s = Path(scratch)
        exes = {}
        for name, args, limit, bp in (MODES[:1] if quick else MODES):
            nslot, pipe, wrap = (tuple(bp) + (1,))[:3] if isinstance(bp, tuple) else (bp, 0, 1)
            key = (nslot, pipe, wrap)
            if key not in exes:
                exes[key] = build(s / f"obj{nslot}_{pipe}_{wrap}", SOURCES, nslot, pipe, wrap)
            modes[name] = run_mode(exes[key], s, t, ev, wins, name, args, limit)
            modes[name].update(nslot=nslot, pipe=pipe, wrapped_element=bool(wrap))
            print(name, "pass" if modes[name].get("pass") else "FAIL",
                  {k: modes[name].get(k) for k in ("elements_compared", "element_mismatches", "poisoned_dumps",
                                                   "latency_cycles_window_to_slot_ready")}, flush=True)
        muts = [] if (quick or no_mut) else mutations(s, t, ev, wins)
    ok = (all(m.get("pass") for m in modes.values()) and all(v["returncode"] == 0 for v in lint.values())
          and all(m["caught"] != bool(m.get("control")) for m in muts))
    return {
        "schema": "opentallas.dsrom-engram-lookup-campaign.v1",
        "status": "pass" if ok else "fail",
        "claim_boundary": "functional cycle-level Verilator simulation of the window former, the shipped-table hash, "
                          "the HBM row lookup (address, alignment, CRC) and the row sink against the golden, with a "
                          "BEHAVIOURAL HBM region and a behavioural TP4 all-gather.  Table CONTENT is synthetic "
                          "(hdc_v41_engram_shipped.row_bytes); HBM and all-gather latencies are parameters.  No "
                          "physical result: route specs are drafts awaiting review (review_queue/engram.md).",
        "tokens": len(ev), "users": NU,
        "dead_tokens": sum(e[3] for e in ev if e[0] == 0), "sequence_starts": sum(e[2] for e in ev if e[0] == 0),
        "mtp_rewinds": sum(e[0] for e in ev), "rewound_tokens": sum(e[4] for e in ev if e[0] == 1),
        "rows_per_token": 48, "elements_per_token_checked": 48 * 256,
        "modes": modes, "mutations": muts, "verilator_lint": lint,
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (*SOURCES, TB, HARNESS, Path(__file__))},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-mutations", action="store_true")
    ap.add_argument("--mutant", type=int, help="negative bench: run mutation IDX only; exits 1 ('ENGRAM_NEG FAIL as "
                                                 "required') when the mutant fails the bench, 0 when it is missed")
    a = ap.parse_args()
    if a.mutant is not None:
        src, what, x, y = MUTATIONS[a.mutant]
        t = ES.shipped_tables()
        ev = build_events(np.random.default_rng(20261008), 160)
        wins = official_windows(ev)
        with tempfile.TemporaryDirectory(prefix="engram-neg-", dir="/tmp") as sc:
            d = Path(sc)
            text = src.read_text()
            assert text.count(x) == 1, what
            (d / src.name).write_text(text.replace(x, y))
            srcs = [d / src.name if q == src else q for q in SOURCES]
            name, args, limit = MUT_MODE
            try:
                rec = run_mode(build(d / "obj", srcs, 2), d, t, ev, wins, "neg", args, limit)
                caught = not rec["pass"]
            except subprocess.CalledProcessError:
                caught = True
        print(f"mutant {what}: " + ("ENGRAM_NEG FAIL as required" if caught else "ENGRAM_NEG MISSED"))
        return 1 if caught else 0
    rec = run(a.quick, a.no_mutations)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(rec["status"])
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
