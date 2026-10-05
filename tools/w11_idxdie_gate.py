#!/usr/bin/env python3
"""W11 idxdie: the adopted indexer path (X_IDX 2, IDX_RING 1 at full ring capacity) on this tree (W17's L20 base).

Runs the full-capacity two-user ring die gate (tools/w11_die_idx_ring_mu_gate.py: four reduced V4.1 decode steps
through ot_chip_v41x_die with IDX_RING 1, RSB 64, RTAIL 32, every logit / the vector memory / the KV cache
bit-exact against the ISA model, each user's key ring carried in HBM between its steps) and writes its record to
results/rtl/w11_idxdie_ring_gate.json (that tool's own record, a VM-H-era one, is left as it is).  It then checks
tools/w11_idx_ring_place.py, the placement W17's full-shape images use, against the bench's own placement
(rtl/test/tb_chip_v41x_die_ring_mu.sv ring_image, transcribed) on every step image: every region, every user.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import w11_die_idx_ring_mu_gate as mu  # noqa: E402
import w11_idx_ring_place as P  # noqa: E402

OUT = ROOT / "results/rtl/w11_idxdie_ring_gate.json"


def bench_place(img: dict[int, int], u: int, rsb: int, rtail: int, ikh_slice: int, ikh_words: int) -> dict:
    """tb_chip_v41x_die_ring_mu.sv ring_image (place), transcribed: {stack: {sector: word}}."""
    c, ublk = P.geometry(rsb, rtail)
    out = {0: {}, 1: {}, 2: {}, 3: {}}
    r = 0
    while (r + 1) * 2176 <= ikh_words and (r + 1) * ublk * 128 <= ikh_slice:
        cnt = 0
        for t in range(1024):
            cs = (17 * r + 1 + t // 64) * 128 + 2 * (t % 64); ss = 17 * r * 128 + t // 8
            if img.get(cs, 0) or img.get(cs + 1, 0) or (img.get(ss, 0) >> (32 * (t % 8))) & 0xFFFFFFFF:
                cnt = t + 1
        qs = (cnt // 32) * 8
        ub = u * (ikh_slice // 128) + r * ublk
        for t in range(cnt):
            q = 0 if t < qs else 1 if t < 2 * qs else 2 if t < 3 * qs else 3
            cs = (17 * r + 1 + t // 64) * 128 + 2 * (t % 64); ss = 17 * r * 128 + t // 8
            sl = t % c
            rcs = (ub + 17 * (sl // 1024) + 1 + (sl % 1024) // 64) * 128 + 2 * (sl % 64)
            rss = (ub + 17 * (sl // 1024)) * 128 + (sl % 1024) // 8
            m = out[q]
            m[rcs] = img.get(cs, 0); m[rcs + 1] = img.get(cs + 1, 0)
            m[rss] = m.get(rss, 0) | (((img.get(ss, 0) >> (32 * (t % 8))) & 0xFFFFFFFF) << (32 * (sl % 8)))
        r += 1
    return {q: {s: w for s, w in m.items() if w} for q, m in out.items()}, r


def tool_place(img: dict[int, int], u: int, rsb: int, rtail: int, ikh_slice: int, nreg: int) -> dict:
    """w11_idx_ring_place.place, region by region (the region's legacy image re-based to 0)."""
    _, ublk = P.geometry(rsb, rtail)
    out = {0: {}, 1: {}, 2: {}, 3: {}}
    for r in range(nreg):
        lo, hi = 17 * r * 128, 17 * (r + 1) * 128
        sub = {s - lo: w for s, w in img.items() if lo <= s < hi}
        st = P.place(sub, None, u * (ikh_slice // 128) + r * ublk, rsb, rtail)
        for q, m in st.items():
            out[q].update(m)
    return {q: {s: w for s, w in m.items() if w} for q, m in out.items()}


def read_dense(p: Path) -> dict[int, int]:
    """A $readmemh image (with @address records) as {word: value}."""
    img, a = {}, 0
    for x in p.read_text().split():
        if x.startswith("@"):
            a = int(x[1:], 16)
            continue
        v = int(x, 16)
        if v:
            img[a] = v
        a += 1
    return img


def main() -> int:
    mu.OUT = OUT
    rc = mu.main()
    rec = json.loads(OUT.read_text())
    scratch = Path(sys.argv[sys.argv.index("--scratch") + 1]) if "--scratch" in sys.argv else \
        Path("/tmp/claude-1000/w11s/rd/mu_gate")
    checks = []
    for k, u in (("a1", mu.USERS[0]), ("b1", mu.USERS[1]), ("a2", mu.USERS[0]), ("b2", mu.USERS[1])):
        img = read_dense(scratch / f"img_{k}" / "ikhbm.hex")
        ref, nreg = bench_place(img, u, mu.PARAMS["RSB"], mu.PARAMS["RTAIL"], mu.PARAMS["IKH_SLICE"], 1 << 18)
        got = tool_place(img, u, mu.PARAMS["RSB"], mu.PARAMS["RTAIL"], mu.PARAMS["IKH_SLICE"], nreg)
        checks.append({"image": k, "user": u, "regions": nreg,
                       "sectors": {q: len(m) for q, m in ref.items()}, "equal": ref == got})
    rec["placement_tool_check"] = {
        "tool": "tools/w11_idx_ring_place.py", "sha256": mu.sha(ROOT / "tools/w11_idx_ring_place.py"),
        "against": "tb_chip_v41x_die_ring_mu.sv ring_image (place), transcribed in tools/w11_idxdie_gate.py",
        "cases": checks, "all_equal": all(c["equal"] for c in checks)}
    rec["sources_sha256"]["tools/w11_idxdie_gate.py"] = mu.sha(Path(__file__))
    rec["sources_sha256"]["tools/w11_idx_ring_place.py"] = mu.sha(ROOT / "tools/w11_idx_ring_place.py")
    if not rec["placement_tool_check"]["all_equal"]:
        rec["status"] = "fail"
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(rec["status"], rec["placement_tool_check"]["cases"])
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
