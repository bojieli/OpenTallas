#!/usr/bin/env python3
"""Q-LINK 2026-10-15: compiler pass for the static Qwen D2D link (rtl/qwen_sys/d2d_static_20261015).

Input: one cross-die message list per calendar run (one decode layer) with each message's compiled SEND cycle relative to
the sending die's cal_start, its producer port, kind and beat; the fixed latencies of the implemented RTL (TXL: tx_slot
to PHY pin, PHY: FDI-to-far-FDI, OFS: receiver cal_start minus sender cal_start). Output: the four calendar images
(compute TX/RX, KV TX/RX; 32-b entries {dt14, last1, port3, kind4, beat5, 0}) and the expected event table.

Hard checks (fail closed): one TX frame per cycle per end; one RX arrival per cycle per end; per-end write-capture
cycles (send + TXD[port]) unique; dt in 1..16383; entries <= NE; every message has a receiver port.
No runtime arbitration exists to absorb a conflict: a conflicting program is rejected here.
"""
import argparse, json, sys

NE = 128


def entry(dt, last, port, kind, beat):
    assert 1 <= dt < (1 << 14), dt
    assert 0 <= port < 8 and 0 <= kind < 16 and 0 <= beat < 32
    return (dt << 18) | (last << 17) | (port << 14) | (kind << 10) | (beat << 5)


def image(events):
    """events: sorted list of (cycle, port, kind, beat), cycle >= 1 relative to cal_start."""
    out, prev = [], 0
    for i, (c, p, k, b) in enumerate(events):
        out.append(entry(c - prev, int(i == len(events) - 1), p, k, b))
        prev = c
    if len(out) > NE:
        raise SystemExit(f"calendar has {len(out)} entries > NE {NE}")
    return out


def bench_layer():
    """Bench layer profile (native typed548, LINK.md section 3 counts): C->S CMD + 32 Q beats + 1 kind-15 status;
    S->C 32 RESULT beats + 1 STATUS."""
    m = []
    m.append(dict(src="C", cyc=2, tx_port=0, rx_port=0, kind=1, beat=0))
    for b in range(32):
        m.append(dict(src="C", cyc=3 + b, tx_port=0, rx_port=0, kind=2, beat=b))
    m.append(dict(src="C", cyc=40, tx_port=2, rx_port=2, kind=15, beat=0))
    for b in range(32):
        m.append(dict(src="K", cyc=50 + b, tx_port=0, rx_port=0, kind=3, beat=b))
    m.append(dict(src="K", cyc=83, tx_port=0, rx_port=0, kind=4, beat=0))
    return m


def dies_layer():
    """Die-wrapper profile: bench layer + 4 KVN words (port 3, kind 5, codec 2 edges) per layer."""
    m = bench_layer()
    for i in range(4):
        m.append(dict(src="C", cyc=42 + i, tx_port=3, rx_port=3, kind=5, beat=i))
    return m


def compile_cal(msgs, txl, phy, ofs, txd):
    """txd: {'C': [..], 'K': [..]} per-end producer codec latency; txl = slot-to-pin latency at codec latency 1."""
    ends = {"C": dict(tx=[], rx=[]), "K": dict(tx=[], rx=[])}
    table = []
    for m in msgs:
        s, r = m["src"], "K" if m["src"] == "C" else "C"
        # receiver-relative arrival cycle at the PHY pins; receiver cal_start is OFS later on the K die (OFS<0: earlier)
        arr = m["cyc"] + txd[s][m["tx_port"]] - 1 + txl + phy - (ofs if r == "K" else -ofs)
        if arr < 1:
            raise SystemExit(f"arrival before receiver start: {m}")
        ends[s]["tx"].append((m["cyc"], m["tx_port"], m["kind"], m["beat"]))
        ends[r]["rx"].append((arr, m["rx_port"], m["kind"], m["beat"]))
        table.append(dict(m, arrive=arr, rx_out=arr + 2, wr=m["cyc"] + txd[s][m["tx_port"]]))
    for e, d in ends.items():
        for k in ("tx", "rx"):
            d[k].sort()
            cyc = [x[0] for x in d[k]]
            if len(set(cyc)) != len(cyc):
                raise SystemExit(f"{e} {k}: two frames in one cycle")
        wr = sorted(t["wr"] for t in table if t["src"] == e)
        if len(set(wr)) != len(wr):
            raise SystemExit(f"{e}: two write captures in one cycle (TXD collision)")
    imgs = {f"{e}_{k}": image(d[k]) for e, d in ends.items() for k in ("tx", "rx")}
    return imgs, table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--txl", type=int, required=True)
    ap.add_argument("--phy", type=int, default=5)
    ap.add_argument("--ofs", type=int, default=0)
    ap.add_argument("--txd-c", default="1,1,1,1", help="compute end codec latency per TX port")
    ap.add_argument("--txd-k", default="1,1,1,1", help="KV end codec latency per TX port")
    ap.add_argument("--spec", help="message list JSON (default: bench layer profile)")
    ap.add_argument("--profile", default="bench", choices=["bench", "dies"])
    a = ap.parse_args()
    txd = {"C": [int(x) for x in a.txd_c.split(",")], "K": [int(x) for x in a.txd_k.split(",")]}
    msgs = json.load(open(a.spec)) if a.spec else (dies_layer() if a.profile == "dies" else bench_layer())
    imgs, table = compile_cal(msgs, a.txl, a.phy, a.ofs, txd)
    import os
    os.makedirs(a.out, exist_ok=True)
    for k, v in imgs.items():
        with open(f"{a.out}/cal_{k}.memh", "w") as f:
            f.write("\n".join(f"{x:08x}" for x in v + [0] * (NE - len(v))) + "\n")
    span = max(max(t["rx_out"], t["cyc"]) for t in table)
    json.dump(dict(txl=a.txl, phy=a.phy, ofs=a.ofs, txd=txd, entries={k: len(v) for k, v in imgs.items()},
                   span=span, messages=table), open(f"{a.out}/calendar.json", "w"), indent=1)
    print(json.dumps(dict(entries={k: len(v) for k, v in imgs.items()}, span=span)))


if __name__ == "__main__":
    sys.exit(main())
