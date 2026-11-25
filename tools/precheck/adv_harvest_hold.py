#!/usr/bin/env python3
"""adv_harvest_hold.py -- ADV-HOLDCELL-BUDGET cache (KV-HOLD-STRUCT 11-25): measured hold-pad volume and residual port hold per (die, type).

Source: <kit>/gen/<type>/pregrt_ff_hold.log of every kit under the given roots (the R-CLOCK HOLD BUILD log).  Per kit it keeps
  pad_cells / pad_ends   sum / first-pass 'ends' of the OT_HOLD_PAD rr<N> lines (the family-margin reg-to-reg planned pad: HB4 cells)
  margin                 the rr margin (ps)
  hold_cells, insts      the 'OT_PREGRT_FF_HOLD after wns' line (all hold cells, instances)
  open_n, open_wns       endpoints and worst slack the build could not close ('after wns <w> endpoints <n>'): class port_in in
                         pregrt_ff_hold_open.tsv (ring / bin / station flop behind an input port; ports are excepted from the repair)
Per (die, base type) it keeps the newest record (by log mtime).  Read-only, no jobs; seconds per few hundred kits.
  adv_harvest_hold.py OUT.json DIE ROOT [ROOT ...]     (ROOT is searched to depth 9 for pregrt_ff_hold.log)"""
import json
import os
import re
import sys
import time

SUFFIX = re.compile(r"(?:__(?:cl|pv)[0-9a-f]{6,})+$")
PAD = re.compile(r"^OT_HOLD_PAD rr\d+ margin ([\d.]+) ends (\d+) padded (\d+) cells (\d+)")
AFTER = re.compile(r"OT_PREGRT_FF_HOLD after wns (-?[\d.]+) endpoints (\d+) cross_tap_wns \S+ tap_ports \d+ hold_cells (\d+) insts (\d+)")
KIT = re.compile(r"(kv3_\w+?|[a-z0-9_]+?)_(\d{10})$")


def parse(path):
    """-> record dict of one pregrt_ff_hold.log, or None when the build never printed its 'after' line"""
    pad_cells = pad_ends = 0
    margin = None
    rec = None
    with open(path, errors="replace") as f:
        for ln in f:
            if ln.startswith("OT_HOLD_PAD rr"):
                m = PAD.match(ln)
                if m:
                    margin = float(m.group(1))
                    pad_cells += int(m.group(4))
                    if ln.startswith("OT_HOLD_PAD rr1 "):
                        pad_ends = int(m.group(2))
            elif "OT_PREGRT_FF_HOLD after wns" in ln:
                m = AFTER.search(ln)
                if m:
                    rec = dict(open_wns=float(m.group(1)), open_n=int(m.group(2)), hold_cells=int(m.group(3)), insts=int(m.group(4)))
    if rec is None:
        return None
    rec.update(pad_cells=pad_cells, pad_ends=pad_ends, margin=margin)
    return rec


def type_of(path):
    """gen/<type>/pregrt_ff_hold.log -> base type name"""
    return SUFFIX.sub("", os.path.basename(os.path.dirname(path)))


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if len(a) < 3:
        print(__doc__)
        return 2
    out, die, roots = a[0], a[1], a[2:]
    db, n = {}, 0
    for root in roots:
        base = root.rstrip("/").count("/")
        for d, dirs, files in os.walk(root):
            if d.count("/") - base >= 9:
                dirs[:] = []
            if "pregrt_ff_hold.log" not in files:
                continue
            p = os.path.join(d, "pregrt_ff_hold.log")
            try:
                rec = parse(p)
                ts = os.path.getmtime(p)
            except OSError:
                continue
            if rec is None:
                continue
            n += 1
            rec.update(ts=round(ts), kit=p, exact=os.path.basename(d))
            k = db.setdefault(die, {}).setdefault(type_of(p), {})
            if "last" not in k or ts > k["last"]["ts"]:
                k["last"] = rec
    json.dump(dict(schema="adv-holdcell.cache.v1", made=time.strftime("%Y-%m-%d %H:%M"), results=n, hold=db),
              open(out, "w"), indent=0, sort_keys=True)
    print(f"HARVEST_HOLD {n} kits, " + ", ".join(f"{k} {len(v)} types" for k, v in sorted(db.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
