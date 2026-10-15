#!/usr/bin/env python3
"""Continuous run, stage 0 (s81-functional-token r3, 2026-10-14): the RTL embed row read -> L0's HIDDEN flits.

tools/dsrom_1m_embed.py golden writes the token's via map + expected words; rtl tb_s81_embed_dump runs
ot_dsrom_embed_row_reader on it and dumps every output word.  This tool rebuilds the row from the RTL words (word
w = h*8 + b, lane l = element h*128 + l*8 + b), asserts it equals the golden L0 entry (4 copies of the row = shard
h_in), and writes the HIDDEN message (a header flit + the 640 BF16-packed h rows of hc_gate.Run.h_rows) for
tb_s81_die_layer +HIN.  The 4-copy expand and the framing are this tool's (the die's are the stream unit and the
hop framer; their RTL is exercised from L0 on).

    python3 tools/s81_ftok/embed_hin.py --words embed_words.mem --out hin_L0.mem
"""
import argparse, os, sys
from pathlib import Path
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "tools/s81_suhc"))
GOLD = Path(os.environ.get("OT_DSROM_1M_GOLD", "/home/ubuntu/w17work/ref/ctx1048576_seed20260930"))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--words", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    import hc_gate as HG
    u16 = np.zeros(5120, np.uint32)
    seen = set()
    for ln in a.words.read_text().split("\n"):
        if not ln.strip():
            continue
        idx, d = ln.split()
        idx, d = int(idx), int(d, 16)
        h, b = divmod(idx, 8)
        for l_ in range(16):
            u16[h * 128 + l_ * 8 + b] = (d >> (32 * l_ + 16)) & 0xFFFF
        seen.add(idx)
    assert seen == set(range(320)), len(seen)
    row = (u16 << 16).astype(np.uint32).view(np.float32)
    z = np.load(GOLD / "ctx1048576_L00.npz")
    h = np.repeat(row[None, :], 4, axis=0)
    assert np.array_equal(h.view(np.uint32), z["h_in"].astype(np.float32).view(np.uint32)), "RTL embed row != L0 h_in"
    rows = HG.Run(256).h_rows(h)
    hdr = 0
    with open(a.out, "w") as f:
        f.write(f"{hdr:0128x}\n")
        for r in rows:
            f.write(f"{r:0128x}\n")
    print(f"embed -> {a.out}: 640 HIDDEN rows from the RTL reader's 320 words == 4 x embed row == L0 h_in")


if __name__ == "__main__":
    main()
