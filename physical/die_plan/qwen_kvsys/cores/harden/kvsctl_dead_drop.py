#!/usr/bin/env python3
"""KV-CORES-R2/KVSCTL-2 10-27: qkd_kvs_ctl proven-dead input drop (COORD ruling (b) 01:33; precedent kvspc_face_ports.py).

The B32 raw cut qkd_kvs_ctl has 250 input pin bits with NO load after hierarchy/proc/flatten/opt_clean
(hr_face_ports.py report `dropped_in`): d2d__svc 138, boot__boot_pr 67, kg 23 (stale plan pin, no reference at all),
cht 12, d2d__srx 10.  Plan drop, never a tie at a pin: the wrapper keeps only the live bit ranges as ports
(`P` for the piece that starts at bit 0, else `P_<lo>`), the leaf's dead input bits are bound to constants that have
no load inside (as kvs_pc land_er).  `lec_harness` writes a pure-wiring wrapper with the ORIGINAL ports (dead bits left
unconnected) so yosys equiv proves pre(original) == narrowed core for every value of the dead bits.
usage: kvsctl_dead_drop.py WRAPPER.sv REPORT.json OUT_DIR [--pins PINS.json]
  -> OUT_DIR/qkd_kvs_ctl.sv, OUT_DIR/qkd_kvs_ctl_lech.sv, OUT_DIR/dead_drop.json (+ OUT_DIR/kvs_ctl_pins.json)"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

DECL = re.compile(r"^(\s*)(input|output) wire (?:\[(\d+):0\] )?(\w+)(,?)\s*$")


def ranges(bits):
    bits = sorted(bits); out = []
    for b in bits:
        if out and b == out[-1][1] + 1:
            out[-1][1] = b
        else:
            out.append([b, b])
    return [tuple(r) for r in out]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wrapper"); ap.add_argument("report"); ap.add_argument("out")
    ap.add_argument("--pins")
    ap.add_argument("--core-json", help="kv_core_rtl <mod>_core.json to rewrite for the narrowed wrapper (files/ports/pin_class)")
    a = ap.parse_args()
    rep = json.load(open(a.report))
    dead = defaultdict(set)
    for x in rep["dropped_in"]:
        m = re.match(r"(.*)\[(\d+)\]$", x)
        dead[m[1]].add(int(m[2]))
    t = Path(a.wrapper).read_text()
    lines = t.split("\n")
    ports = []            # (dir, width, name) original order
    pieces = {}           # name -> [(piece, hi, lo)]
    new = []
    for ln in lines:
        m = DECL.match(ln)
        if not m or m[4] in pieces:
            new.append(ln); continue
        ind, d, hi, nm, comma = m[1], m[2], int(m[3] or 0), m[4], m[5]
        ports.append((d, hi + 1, nm))
        if nm not in dead:
            new.append(ln); continue
        assert d == "input", nm
        live = [b for b in range(hi + 1) if b not in dead[nm]]
        ps = [((nm if lo == 0 else f"{nm}_{lo}"), h, lo) for lo, h in ranges(live)]
        pieces[nm] = ps
        for pn, h, lo in ps:
            new.append(f"{ind}input wire [{h - lo}:0] {pn},")
    t2 = "\n".join(new)
    for nm, ps in pieces.items():
        w = next(w for d, w, n in ports if n == nm)
        old = f".{nm}({nm}[{w - 1}:0])"
        n_ref = len(re.findall(r"\b%s\b" % re.escape(nm), t2))
        if not ps:                       # whole port dead
            assert old not in t2 and n_ref == 0, (nm, n_ref)
            continue
        items = []; b = w - 1
        for pn, h, lo in sorted(ps, key=lambda x: -x[1]):
            if b > h:
                items.append(f"{b - h}'d0")
            items.append(f"{pn}[{h - lo}:0]")
            b = lo - 1
        if b >= 0:
            items.append(f"{b + 1}'d0")
        assert t2.count(old) == 1, (nm, t2.count(old))
        t2 = t2.replace(old, f".{nm}({{{', '.join(items)}}})   /* dead bits: plan drop (KVSCTL-2), no load inside */")
        assert old not in t2 and f"{nm}[{w - 1}:" not in t2, nm
    # the last port declaration must not end with a comma
    t2 = re.sub(r",(\s*\n\s*\);)", r"\1", t2, count=1)
    t2 = t2.replace("module qkd_kvs_ctl (", "// KV-CORES-R2/KVSCTL-2 10-27 (kvsctl_dead_drop.py): 250 proven-dead input bits dropped (plan delta)\nmodule qkd_kvs_ctl (", 1)
    o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
    (o / "qkd_kvs_ctl.sv").write_text(t2)
    # LEC harness: original ports, pure wiring, dead bits unconnected
    h = ["`default_nettype none", "module qkd_kvs_ctl_lech ("]
    h += [f"    {d} wire [{w - 1}:0] {n}," for d, w, n in ports]
    h[-1] = h[-1].rstrip(",")
    h += [");", "    qkd_kvs_ctl u_core ("]
    conn = []
    for d, w, n in ports:
        if n in pieces:
            conn += [f"        .{pn}({n}[{hh}:{lo}])" for pn, hh, lo in pieces[n]]
        else:
            conn.append(f"        .{n}({n})")
    h += [",\n".join(conn), "    );", "endmodule", ""]
    (o / "qkd_kvs_ctl_lech.sv").write_text("\n".join(h))
    summ = dict(module="qkd_kvs_ctl", dropped_bits=sum(len(v) for v in dead.values()),
                per_port={k: dict(width=next(w for d, w, n in ports if n == k), dead=len(v), dead_ranges=ranges(v),
                                  live_pieces=[dict(port=pn, hi=hh, lo=lo) for pn, hh, lo in pieces[k]])
                          for k, v in sorted(dead.items())},
                rule="COORD 10-27 01:33 (b): proven dead (no load after flatten/opt_clean) + LEC with the pins removed EQUIVALENT; plan drop, no pin ties")
    if a.pins:
        P = json.load(open(a.pins)); keep = []; drop = 0
        for p in P["pins"]:
            m = re.match(r"(.*)\[(\d+)\]$", p["name"])
            if m and m[1] in dead:
                k = int(m[2])
                if k in dead[m[1]]:
                    drop += 1; continue
                pn, hh, lo = next(x for x in pieces[m[1]] if x[2] <= k <= x[1])
                p = dict(p, name=f"{pn}[{k - lo}]")
            keep.append(p)
        P["pins"] = keep
        P["source"] += " | KV-CORES-R2/KVSCTL-2 10-27: 250 proven-dead input bits dropped (d2d__svc/srx, cht, boot__boot_pr, kg), live pieces renamed P_<lo>"
        (o / "kvs_ctl_pins.json").write_text(json.dumps(P, indent=1) + "\n")
        summ["pins_dropped"] = drop; summ["pins_after"] = len(keep)
    if a.core_json:
        C = json.load(open(a.core_json))
        wp = str(Path(a.wrapper).resolve())
        C["files"] = [str((o / "qkd_kvs_ctl.sv").resolve()) if str(Path(f).resolve()) == wp else f for f in C["files"]]
        pd, pc = {}, {}
        for n, v in C["port_decl"].items():
            if n not in dead:
                pd[n] = v; continue
            for pn, hh, lo in pieces[n]:
                pd[pn] = [v[0], hh - lo, 0]
        for n, c in C["pin_class"].items():
            m = re.match(r"(.*)\[(\d+)\]$", n)
            if m and m[1] in dead:
                k = int(m[2])
                if k in dead[m[1]]:
                    continue
                pn, hh, lo = next(x for x in pieces[m[1]] if x[2] <= k <= x[1])
                n = f"{pn}[{k - lo}]"
            pc[n] = c
        C["port_decl"], C["pin_class"] = pd, pc
        C["ports"], C["pin_bits"] = len(pd), len(pc)
        cl = {}
        for c in pc.values():
            cl[c] = cl.get(c, 0) + 1
        C["classes"] = cl
        C["dead_drop"] = {k: v for k, v in summ.items() if k != "per_port"} | dict(file="dead_drop.json")
        (o / "qkd_kvs_ctl_core.json").write_text(json.dumps(C, indent=1) + "\n")
        summ["core_json"] = dict(ports=len(pd), pin_bits=len(pc), classes=cl)
    (o / "dead_drop.json").write_text(json.dumps(summ, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summ.items() if k != "per_port"}))


if __name__ == "__main__":
    main()
