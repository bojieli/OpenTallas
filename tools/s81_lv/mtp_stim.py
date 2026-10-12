#!/usr/bin/env python3
"""S81 layer vehicle, seam S8 (layer h -> hrow -> MTP sequencer): stimulus of tb_s81lv_mtp_s8 from the 1M token.

  hstore.mem  the 640 golden H_STORE rows (rows S_BASE..) of the die-layer stimulus (tools/s81_ctrl/die_layer_stim.py
              expa.mem / expd.mem: the 1M-token chain's layer output h, CPU golden pinned by su_cases_v2_ildr.pkl)
  writes.mem  the HC master's H_STORE beats: every row split into 1..3 lane-masked writes (masks partition the 16
              lanes), all writes in a seeded random order -> {row[13:0], mask[15:0]}
  meta.mem    nwr, user, pos 1,048,575, epoch, glen, plen 1,048,576 (the token closes the prompt), argmax token,
              argmax value, seed -- the head RESULT is the HGI exporter's ds_head export (next_token, the winning
              rank's argmax_local {value, index} from coll_<merge>.bin)
Usage: mtp_stim.py --stim <die-layer stim dir> --head <ds_head export dir> --out <dir> [--seed N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np

S_BASE, HROWS = 6144, 640


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stim", type=Path, required=True)
    ap.add_argument("--head", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=20261012)
    ap.add_argument("--user", type=int, default=5)
    ap.add_argument("--epoch", type=int, default=3)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    adr = [int(x, 16) for x in (a.stim / "expa.mem").read_text().split()]
    dat = (a.stim / "expd.mem").read_text().split()
    rows = {r - S_BASE: d for r, d in zip(adr, dat) if r >= S_BASE}
    assert sorted(rows) == list(range(HROWS)), f"H_STORE rows {len(rows)} != {HROWS}"
    writes = []
    for r in range(HROWS):
        lanes = rng.permutation(16)
        cuts = sorted(rng.choice(np.arange(1, 16), size=int(rng.integers(0, 3)), replace=False))
        for part in np.split(lanes, cuts):
            writes.append((r << 16) | int(sum(1 << int(l) for l in part)))
    writes = [writes[i] for i in rng.permutation(len(writes))]
    assert len(writes) <= 4096
    # head RESULT from the exporter's head run
    meta = json.loads((a.head / "meta.json").read_text())
    tok = int(re.search(r'"next_token": (\d+)', (a.head / "ds_native_run.json").read_text()).group(1))
    merge = next(r for r in meta["records"] if r["op"] == "ARGMAX_MERGE")
    parts = np.frombuffer((a.head / f"coll_{merge['k']}.bin").read_bytes(), "<u4").reshape(-1, 2)
    vals = parts[:, 0].view("<f4")
    win = int(np.argmax(vals))                                   # the winning rank's {value bits, index}
    val = int(parts[win, 0])
    pos = meta["position"]
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "hstore.mem").write_text("".join(f"{rows[r]}\n" for r in range(HROWS)))
    (a.out / "writes.mem").write_text("".join(f"{w:08x}\n" for w in writes))
    m = [len(writes), a.user, pos, a.epoch, 16, pos + 1, tok, val, a.seed]
    (a.out / "meta.mem").write_text("".join(f"{v & 0xFFFFFFFF:08x}\n" for v in m + [0] * (16 - len(m))))
    rec = dict(stim=str(a.stim), head=str(a.head), position=pos, next_token=tok, argmax_value_bits=f"{val:08x}",
               winner_rank=win, winner_index=int(parts[win, 1]), hstore_rows=HROWS, writes=len(writes),
               inputs={str(p): sha(p) for p in (a.stim / "expa.mem", a.stim / "expd.mem", a.head / "meta.json")})
    (a.out / "manifest.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec))


if __name__ == "__main__":
    main()
