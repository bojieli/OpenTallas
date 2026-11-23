#!/usr/bin/env python3
"""harvest_flops.py -- PRECHECK-R2 TAP-LOAD cache (one gen host): per kit type the synthesized netlist flop count
(kit_scan FOLD state: <kit>.fold.json netlist_flops = DFF cells of 1_2_yosys.v, soft logic incl., hard-core internals
excluded), the placed per-tap load (kit_scan PLACED state: <kit>.placed.json skew {tap: [ps, sinks]}) and the placed
register sites binned to BIN um (<kit>.placed_raw.json regs, type frame, with die_um).
  harvest_flops.py OUT.json [STATE_DIR] [BIN_UM]     read-only; newest kit per type wins"""
import glob, json, os, re, socket, sys, time

STAGE = re.compile(r"^(.+?)-(route|place|cts|grt|kit|sign|signoff|flow|full)-.*-(\d{9,})$")


def kit_of(path):
    b = os.path.basename(path).split(".")[0]
    m = STAGE.match(b)
    return (m.group(1), int(m.group(3)), b) if m else (None, 0, b)


def main():
    out = sys.argv[1]
    sd = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/.local/state/precheck-kit-scan")
    binum = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    host = socket.gethostname()
    fl, pl, rw = {}, {}, {}
    for f in glob.glob(os.path.join(sd, "*.fold.json")):
        tn, ts, kit = kit_of(f)
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if not tn or not isinstance(d.get("netlist_flops"), int):
            continue
        if tn not in fl or ts > fl[tn]["ts"]:
            fl[tn] = dict(flops=d["netlist_flops"], top=d.get("top"), ts=ts, kit=f"{host}:{kit}")
    for f in glob.glob(os.path.join(sd, "*.placed.json")):
        tn, ts, kit = kit_of(f)
        try:
            d = json.load(open(f))
        except Exception:
            continue
        sk = d.get("skew") or {}
        if not tn or not sk:
            continue
        loads = {t: int(v[1]) for t, v in sk.items() if isinstance(v, list) and len(v) > 1}
        if not loads:
            continue
        top = max(loads, key=loads.get)
        if tn not in pl or ts > pl[tn]["ts"]:
            pl[tn] = dict(n_regs=d.get("n_regs"), taps=len(loads), max_tap=top, max_load=loads[top],
                          over1500=sorted(([t, n] for t, n in loads.items() if n > 1500), key=lambda r: -r[1])[:12],
                          ts=ts, kit=f"{host}:{kit}")
    for f in glob.glob(os.path.join(sd, "*.placed_raw.json")):
        tn, ts, kit = kit_of(f)
        if not tn or (tn in rw and ts <= rw[tn]["ts"]):
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        regs = d.get("regs") or []
        if not regs:
            continue
        b = {}
        for x, y in regs:
            k = (int(x // binum), int(y // binum))
            b[k] = b.get(k, 0) + 1
        rw[tn] = dict(die_um=d.get("die_um"), bin_um=binum, n_regs=len(regs), ts=ts, kit=f"{host}:{kit}",
                      bins=[[round((i + 0.5) * binum, 2), round((j + 0.5) * binum, 2), n] for (i, j), n in sorted(b.items())])
    json.dump(dict(schema="precheck-r2.flops_cache.v1", host=host, made=time.strftime("%Y-%m-%d %H:%M"),
                   flops=fl, placed=pl, placed_bins=rw), open(out, "w"))
    print(f"HARVEST_FLOPS {host}: fold {len(fl)} placed {len(pl)} raw {len(rw)}")


if __name__ == "__main__":
    main()
