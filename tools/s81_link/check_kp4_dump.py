#!/usr/bin/env python3
"""DIE-HEAD-85/TXF 2026-11-07: rs544 check of a KP4 encoder word dump (tb_kp4_enc_fold.sv +DUMP=<file>).

Each line: <epoch> <544-bit word hex>.  Every epoch starts on frame word 0; 10 words = one codeword (5440 bits, word w =
codeword bits [5439 - 544 w -: 544]).  Each complete frame must carry the AM header 0xA5C, a seq that counts by one,
and parity == tools/s81_link/rs544.encode(message).  Exit 1 on any failure or on fewer than --min frames.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rs544 as R  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump", type=Path)
    ap.add_argument("--min", type=int, default=10)
    a = ap.parse_args()
    ep = {}
    for ln in a.dump.read_text().split("\n"):
        if ln.strip():
            e, w = ln.split()
            ep.setdefault(int(e), []).append(int(w, 16))
    good = bad = 0
    for e, ws in sorted(ep.items()):
        last = None
        for f in range(len(ws) // 10):
            v = 0
            for w in ws[10 * f: 10 * f + 10]:
                v = (v << 544) | w
            cw = [(v >> (5430 - 10 * s)) & 0x3FF for s in range(R.N)]
            hdr = v >> 5420
            seq = hdr & 0xFF
            ok = (hdr >> 8) == R.AM and R.encode(cw[:R.K]) == cw and not any(R.syndromes(cw))
            ok = ok and (last is None or seq == (last + 1) & 0xFF)
            last = seq
            good += ok
            bad += not ok
            if not ok and bad <= 3:
                print(f"BAD epoch {e} frame {f} hdr {hdr:05x}")
    res = "PASS" if bad == 0 and good >= a.min else "FAIL"
    print(f"CHECK_KP4_DUMP {res} frames_ok={good} frames_bad={bad} epochs={len(ep)}")
    return 0 if res == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
