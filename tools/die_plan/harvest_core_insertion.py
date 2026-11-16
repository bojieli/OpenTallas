#!/usr/bin/env python3
"""LEVER 8 (FABLE-METHOD, PLAN-READERS-1): write insertion.json beside the liberty of every hard core that has no measured clock
contract, from the MEASURED pin-register clock arrivals of its signed routed run (signoff.json corners.<tt|ff>.insertion_pinflops
of the signed export: boundary flop CK arrival mean / min / max over the routed SPEF database, never liberty arcs).

  harvest_core_insertion.py PLAN --root SRC_ROOT --export DIR [--write] [--tsv OUT]
  DIR = <die>/<element>/signoff.json copies of the signed export (rtx-pro /home/ubuntu/signed-export-1114, AGIdock
        /archive/opentallas-signed-1114).  Read only; nothing is run on rtx-pro.

For every hard_cores[] lib of the plan whose directory has no clock_contract.json / signoff.json / insertion.json: find the export
element whose name is the core module (or whose signed design is the module), check the clock port identity against the lib's
single clock pin, and write insertion.json in the form core_clock_contract.load reads (raw_source true, parasitics spef, tt / ff
boundary stats).  Status per core: WRITTEN | EXISTS | NO-EXPORT (no signed run: e.g. SRAM / ROM macros have no flop clock tree)
| NO-PINFLOPS | PORT-MISMATCH | MULTI-CLOCK.  --write off = report only."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def index_export(export):
    """{module/element name: [signoff.json Path]} over <die>/<element>/signoff.json; designs of the records too"""
    out = {}
    for f in sorted(Path(export).glob("*/*/signoff.json")):
        out.setdefault(f.parent.name, []).append(f)
    return out


def best_record(paths, module):
    """prefer SIGNED, then LOCAL_PASS_NEEDS_PARENT; the record whose design names the module"""
    rank = {"SIGNED": 0, "LOCAL_PASS_NEEDS_PARENT": 1}
    recs = []
    for p in paths:
        try:
            d = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        design = ((d.get("corners") or {}).get("tt") or {}).get("design") or ""
        recs.append((rank.get(d.get("verdict"), 9), 0 if (design == module or design.endswith("_" + module)) else 1, str(p), p, d))
    recs.sort(key=lambda r: r[:3])
    return recs[0][3:] if recs else (None, None)


def build(module, pin, rec, path):
    c = rec.get("corners") or {}
    out = dict(lib_clock_pin=pin, module=module, raw_source=True, parasitics="spef")
    for corner in ("tt", "ff"):
        item = c.get(corner) or {}
        st = item.get("insertion_pinflops") or {}
        if not st.get("n"):
            return None, "NO-PINFLOPS"
        ports = item.get("clock_ports") or []
        if ports and ports != [pin]:
            return None, f"PORT-MISMATCH {ports} != {[pin]}"
        out[corner] = dict(boundary={k: st[k] for k in ("n", "min", "mean", "max", "spread") if k in st})
    out["source"] = (f"PLAN-READERS-1 lever 8: signoff.json corners.{{tt,ff}}.insertion_pinflops of the signed run (verdict {rec.get('verdict')}), "
                     f"{path} sha256 {hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]}")
    return out, "WRITTEN"


def main(argv=None):
    import schema as S
    import cores as C
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--root", required=True)
    ap.add_argument("--export", required=True)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--tsv")
    a = ap.parse_args(argv)
    raw = S.load(a.plan)
    idx = index_export(a.export)
    rows, seen = [], set()
    for tn, t in raw["partition_types"].items():
        for core in t.get("hard_cores", []) or []:
            lib = core.get("lib")
            mod = core.get("module", core["inst"])
            if not lib or (mod, lib) in seen:
                continue
            seen.add((mod, lib))
            p = C.resolve(lib, a.root)
            d = p.parent
            if not p.is_file():
                rows.append((mod, str(lib), "NO-LIB", "")); continue
            if any((d / n).is_file() for n in ("clock_contract.json", "signoff.json", "insertion.json")):
                rows.append((mod, str(lib), "EXISTS", "")); continue
            if len(list(d.glob("*_tt.lib"))) > 1:
                rows.append((mod, str(lib), "SHARED-DIR", f"{len(list(d.glob('*_tt.lib')))} core libs share this directory: one insertion.json cannot be attributed")); continue
            pins = sorted(C.clock_pins(core, a.root))
            if len(pins) != 1:
                rows.append((mod, str(lib), "MULTI-CLOCK" if pins else "NO-CLOCK", ",".join(pins))); continue
            sp, rec = best_record(idx.get(mod, []), mod)
            if rec is None:
                rows.append((mod, str(lib), "NO-EXPORT", "no signed run in the export (memory macros have no flop clock tree)")); continue
            out, st = build(mod, pins[0], rec, sp)
            if out is None:
                rows.append((mod, str(lib), st.split()[0], st)); continue
            if a.write:
                (d / "insertion.json").write_text(json.dumps(out, indent=1) + "\n")
            rows.append((mod, str(lib), "WRITTEN" if a.write else "WOULD-WRITE",
                         f"tt mean {out['tt']['boundary'].get('mean')} n {out['tt']['boundary']['n']} ff mean {out['ff']['boundary'].get('mean')}"))
    txt = "module\tlib\tstatus\tdetail\n" + "".join("\t".join(map(str, r)) + "\n" for r in rows)
    print(txt)
    if a.tsv:
        Path(a.tsv).write_text(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
