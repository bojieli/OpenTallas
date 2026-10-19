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
already uses for producers outside the slice. These are component diagnostics,
never complete-layer or native-chain proof: expected-reference carry is not
measured RTL state. Native scope requests are refused, even if every part passes.

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


def split(rep, man, nev, scope="component_probe"):
    if scope != "component_probe" or rep.get("scope") in ("native_layer", "native_chain"):
        raise ValueError("split_replay: native layer/chain scope refused; carry uses expected reference, not measured RTL state")
    cap = nev - 1
    prog_of = {}
    for p in man["su_programmes"]:
        for r in p["records"]:
            prog_of[r] = p["programme"]
    ev = rep["events"]
    initial_seeds = set(rep.get("state_seed_provenance", []))
    if not initial_seeds and any(e["k"] == "M" for e in ev):
        initial_seeds.add("released_checkpoint_fixture" if man.get("fixtures") else "unspecified_initial_image")
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
                              row=(sec & 0x1fff) >> 3, val=f"{v:064x}", src="image:VM_carry(earlier part commit)",
                              state_seed_provenance="expected_reference"))
        for e in mine:
            if e["k"] == "C" and e["port"].startswith("vm:"):
                sec = int(e["port"][3:], 16)
                if sec not in written or written[sec][0] <= e["cyc"]:
                    written[sec] = (e["cyc"], e["val"], e.get("mask", "f" * 64))
        r = {k: v for k, v in rep.items() if k != "events"}
        r.update(scope="component_probe", qualifies_native_layer=False, qualifies_native_chain=False,
                 state_seed_provenance=sorted(initial_seeds |
                     ({"expected_reference"} if carry else set())),
                 qualification_limit="independent component diagnostics; no measured state transfer between parts")
        r["split"] = dict(programmes=pk, records=sorted({e["rec"] for e in mine if "rec" in e}),
                          carried_sectors=len(carry),
                          state_seed_provenance="expected_reference" if carry else "no_cross_part_carry")
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
    ap.add_argument("--scope", choices=["component_probe", "native_layer", "native_chain"], default="component_probe")
    a = ap.parse_args()
    rep = json.loads(a.replay.read_text())
    man = json.loads(a.manifest.read_text())
    a.out.mkdir(parents=True, exist_ok=True)
    try:
        parts = split(rep, man, a.nev, scope=a.scope)
    except ValueError as e:
        ap.error(str(e))
    idx = []
    for k, r in enumerate(parts):
        nm = f"{a.name}_p{k}" if len(parts) > 1 else a.name
        (a.out / f"{nm}.json").write_text(json.dumps(r) + "\n")
        nonm = [e for e in r["events"] if e["k"] != "M"]
        idx.append(dict(name=nm, events=len(nonm), preload=len(r["events"]) - len(nonm), cycles=stream_cycles(nonm),
                        **r["split"]))
    (a.out / f"{a.name}_parts.json").write_text(json.dumps(dict(source=str(a.replay), nev=a.nev, parts=idx,
                         scope="component_probe", qualifies_native_layer=False, qualifies_native_chain=False,
                         state_seed_provenance=sorted({v for p in parts for v in p["state_seed_provenance"]})),
                                                           indent=1) + "\n")
    print(json.dumps(idx))


if __name__ == "__main__":
    main()
