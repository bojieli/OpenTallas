#!/usr/bin/env python3
"""LB2-HBM2-RPL (10-18): split one slice replay (layer_images / qwen_layer_images replay.json + manifest.json) into
parts that fit a BUILT slice testbench's event array (tb_slice.sv localparam NEV; the SW slice binary of record has
NEV 6309 = 6308 events + end), so a layer replay runs on that binary without a rebuild.

A part = consecutive SU programmes (D events carry 'prog'; C / M events carry 'rec', mapped to the programme through
manifest su_programmes).  Every event keeps its ABSOLUTE scheduled cycle (fixed-delay schedule: a record's commit
assertions stay at the cycle the layer schedule gives them).  VM state a part's records read that an EARLIER part
produced in the full run (the compiler preloads only sectors not written earlier in the run) is preloaded as an image:
the last committed check value of every sector an earlier part wrote (C events on vm:<sector>, masked words 0 =
inactive lanes), unless the part preloads that sector itself.  This is the same image-load substitution the replay
already uses for producers outside the slice.

    python3 split_replay.py --replay DIR/replay.json --manifest DIR/manifest.json --nev 6309 --out OUTDIR --name NAME
writes OUTDIR/NAME_p<k>.json (replay.v1) + OUTDIR/NAME_parts.json (parts, records, cycles to run)."""
import argparse
import json
import math
from pathlib import Path


def stream_cycles(events, ratio=4 / 3, margin=512):
    """stream edges to run (TB +CYCLES counts stream edges): last serial event x 4/3 (3:4 serial domain) + margin."""
    ls = max([e["cyc"] for e in events if e["dom"] == "serial"] + [0])
    lt = max([e["cyc"] for e in events if e["dom"] == "stream" and e["k"] != "M"] + [0])
    return int(math.ceil(max(ls * ratio, lt))) + margin


def split(rep, man, nev):
    cap = nev - 1
    prog_of = {}
    for p in man["su_programmes"]:
        for r in p["records"]:
            prog_of[r] = p["programme"]
    ev = rep["events"]
    cnt = {}
    for e in ev:
        if e["k"] == "M":
            continue
        k = e["prog"] if "prog" in e else prog_of[e["rec"]]
        cnt[k] = cnt.get(k, 0) + 1
    parts, cur, n = [], [], 0
    for k in sorted(cnt):
        if cnt[k] > cap:
            raise SystemExit(f"split_replay: programme {k} alone has {cnt[k]} events > {cap}")
        if cur and n + cnt[k] > cap:
            parts.append(cur)
            cur, n = [], 0
        cur.append(k)
        n += cnt[k]
    if cur:
        parts.append(cur)
    out, written = [], {}                        # sector -> (cyc, val, mask) last committed check of earlier parts
    for pk in parts:
        ps = set(pk)
        mine = [e for e in ev if (e["prog"] if "prog" in e else prog_of.get(e.get("rec"))) in ps]
        own_pre = {e["sector"] for e in mine if e["k"] == "M"}
        quarter = next((e["quarter"] for e in ev if e["k"] == "M"), 0)
        carry = []
        for sec, (_, val, msk) in sorted(written.items()):
            if sec in own_pre:
                continue
            v = int(val, 16) & int(msk, 16)
            carry.append(dict(k="M", dom="stream", cyc=0, mem="vm", quarter=quarter, sector=sec, bank=sec % 8,
                              row=(sec & 0x1fff) >> 3, val=f"{v:064x}", src="image:VM_carry(earlier part commit)"))
        for e in mine:
            if e["k"] == "C" and e["port"].startswith("vm:"):
                sec = int(e["port"][3:], 16)
                if sec not in written or written[sec][0] <= e["cyc"]:
                    written[sec] = (e["cyc"], e["val"], e.get("mask", "f" * 64))
        r = {k: v for k, v in rep.items() if k != "events"}
        r["split"] = dict(programmes=pk, records=sorted({e["rec"] for e in mine if "rec" in e}),
                          carried_sectors=len(carry))
        r["events"] = carry + mine
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--nev", type=int, default=6309, help="NEV of the built tb_slice.sv")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--name", required=True)
    a = ap.parse_args()
    rep = json.loads(a.replay.read_text())
    man = json.loads(a.manifest.read_text())
    a.out.mkdir(parents=True, exist_ok=True)
    parts = split(rep, man, a.nev)
    idx = []
    for k, r in enumerate(parts):
        nm = f"{a.name}_p{k}" if len(parts) > 1 else a.name
        (a.out / f"{nm}.json").write_text(json.dumps(r) + "\n")
        nonm = [e for e in r["events"] if e["k"] != "M"]
        idx.append(dict(name=nm, events=len(nonm), preload=len(r["events"]) - len(nonm), cycles=stream_cycles(nonm),
                        **r["split"]))
    (a.out / f"{a.name}_parts.json").write_text(json.dumps(dict(source=str(a.replay), nev=a.nev, parts=idx),
                                                           indent=1) + "\n")
    print(json.dumps(idx))


if __name__ == "__main__":
    main()
