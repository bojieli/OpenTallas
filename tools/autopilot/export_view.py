#!/usr/bin/env python3
"""Export the signed hard-core timing view of an ALREADY SIGNED run (CORE-VIEWS-1, COORD 10-28).

The die STA (die_sta_related.py --core-view MODULE=VIEWDIR) reads VIEWDIR/{<module>_tt.lib, <module>_ff.lib,
<module>.core.json, provenance.json (kit.pins_sha256 / kit.pins_canon_sha256 / kit.outline_um)}.  The autopilot
publishes that view when it archives a run it signed off (autopilot.PROBE_VIEW_READ + view_payload + the view part of
PROBE_ARCHIVE).  This is the same exporter with a command line for runs signed before (or outside) the autopilot: it
runs the autopilot's own PROBE_VIEW_READ on the kit / base / signoff dirs, builds the view with view_payload, and
writes the same files.  No second exporter: the view content and the pin identity (die_sta_related.canon_sha256) are
the autopilot's.

What it adds for a hand-signed run, all recorded in provenance.json 'export':
  * the verdict says what the run is (signoff.json verdict + the routed-LEC record when one is given), never the
    autopilot chain text;
  * signoff.json sha256 + generated time, and a FRESHNESS check: the signed 6_final.odb (base) must not be newer
    than signoff.json 'generated' (stale sign-off log lesson, 10-27) -- a newer odb makes the view 'incomplete';
  * kit.pins_sha256 = whole-file sha256 of the kit pins.json when the kit freeze/core record carries none, and that
    pins.json is copied into the view (die_sta_related.signed_pins_doc verifies the signed pin content by that sha,
    which enables the exact MX/MY/R180 mirror match).
It never re-runs sign-off and never edits the run.

  export_view.py --kit KIT --signoff KIT/signoff/signoff.json --out VIEWS_ROOT --die s81 [--base BASE] [--lec lec.json]
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import autopilot as AP  # noqa: E402


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def run_probe(code, args):
    """run an autopilot probe locally (the same code the autopilot runs over ssh)"""
    r = subprocess.run([sys.executable, "-I", "-c", code, json.dumps(args)], capture_output=True, text=True, timeout=600)
    for line in r.stdout.splitlines():
        if line.startswith("AP_JSON "):
            return json.loads(line[8:])
    raise RuntimeError(f"probe failed rc {r.returncode}: {r.stderr[-400:]}")


def find_base(kit, module):
    """the run's results dir holding <module>.lef: ORFS run/results/asap7/<design>/base, or an autopilot archive's
    <archive>/base next to <archive>/kit; None when there is none"""
    cands = (sorted(Path(kit).glob("run/results/asap7/*/base")) + sorted(Path(kit).glob("*/run/results/asap7/*/base"))
             + [Path(kit).parent / "base"])
    for c in cands:
        if c.is_dir() and (module is None or (c / f"{module}.lef").exists()):
            return str(c)
    return None


def parse_time(s):
    try:
        return datetime.datetime.fromisoformat(str(s)).timestamp()
    except (TypeError, ValueError):
        return None


def so_record(signoff):
    d = json.loads(Path(signoff).read_text())
    corners = d.get("corners") or {}

    def wns(c, key):
        v = corners.get(c) or corners.get(c.upper()) or {}
        return v.get(key) if isinstance(v, dict) else None
    return d, dict(verdict=d.get("verdict"), path=str(signoff), tt_wns=wns("tt", "std_wns_max"),
                   ff_wns=wns("ff", "std_wns_min"), core_latency=d.get("core_latency"))


def export(kit, signoff, out_root, die, base=None, lec=None, src_commit=None, flow_tag=None, note=None):
    kit = os.path.realpath(kit)
    sdoc, so = so_record(signoff)
    sdir = os.path.dirname(os.path.realpath(signoff))
    first = run_probe(AP.PROBE_VIEW_READ, {"kit": kit, "base": base or kit, "signoff_dir": sdir})
    base = base or find_base(kit, first.get("module")) or kit
    r = run_probe(AP.PROBE_VIEW_READ, {"kit": kit, "base": base, "signoff_dir": sdir}) if base != kit else first
    lec_doc = json.loads(Path(lec).read_text()) if lec else {}
    lec_v = lec_doc.get("verdict") or lec_doc.get("result")
    j = dict(id="export-view:" + sha256(signoff)[:12], die=die, type=r.get("module") or "?", src=kit,
             geom="n/a (view export of a signed run; geometry was reviewed at sign-off)",
             chain=dict(lec_verdict=lec_v, lec=lec, lec_all_shown=lec_doc.get("all_shown")),
             src_commit=src_commit or sdoc.get("src_commit"), flow_tag=flow_tag or sdoc.get("flow_tag"))
    mod = r.get("module")
    lib_basis = {}
    for corner, orfs in (("tt", "tc"), ("ff", "bc")):     # the routed run's own ETM (ORFS finish write_timing_model of
        rel, alt = f"{mod}_{corner}.lib", os.path.join(base, f"{mod}_{orfs}.lib")   # 6_final), as s81_eco/publish_view.sh
        if mod and rel not in (r.get("files") or {}) and os.path.isfile(alt):
            r.setdefault("files", {})[rel] = alt
            lib_basis[rel] = f"base {mod}_{orfs}.lib (ORFS finish ETM of 6_final; no kit/views or signoff-dir lib)"
    view, gates, problems = AP.view_payload(r, j, so)
    prov = view["provenance"]
    kitblk = prov["kit"]
    pf = os.path.join(kit, "pins.json")
    if os.path.isfile(pf):
        view["files"]["pins.json"] = pf
        if not kitblk.get("pins_sha256"):
            kitblk.update(pins_sha256=sha256(pf), pins_sha256_basis="kit pins.json (no freeze/core pins_sha256)")
    odb = os.path.join(base, "6_final.odb")
    gen = parse_time(sdoc.get("generated"))
    fresh = None
    if os.path.isfile(odb) and gen is not None:
        fresh = os.path.getmtime(odb) <= gen + 60
        if not fresh:
            problems.append("6_final.odb is newer than signoff.json generated (stale sign-off record)")
    if (so.get("verdict") or "").upper() not in ("SIGNED", "PASS", "SIGNED-OFF", "SIGNED_OFF"):
        problems.append(f"signoff.json verdict {so.get('verdict')!r} is not SIGNED")
    prov.update(verdict=f"SIGNED (signoff.py verdict {so.get('verdict')}"
                        + (f"; routed LEC {lec_v}" if lec else "; routed LEC record not given") + ")",
                views_status="signoff" if not problems else "incomplete: " + "; ".join(problems),
                autopilot_id=None)
    prov["export"] = dict(tool="tools/autopilot/export_view.py (autopilot PROBE_VIEW_READ + view_payload)",
                          exported=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                          kit=kit, base=base, signoff=os.path.realpath(signoff), signoff_sha256=sha256(signoff),
                          signoff_generated=sdoc.get("generated"), odb=odb if os.path.isfile(odb) else None,
                          odb_not_newer_than_signoff=fresh, lec=lec, note=note, lib_basis=lib_basis or None,
                          files_sha256={k: sha256(v) for k, v in sorted(view["files"].items())})
    gates.update(view_complete=not problems, view_problems=problems)
    if not mod:
        raise SystemExit("no module found (kit freeze/core record or a single base LEF)")
    vd = Path(out_root) / mod
    vd.mkdir(parents=True, exist_ok=True)
    for rel, src in sorted(view["files"].items()):
        shutil.copy2(src, vd / rel)
    if view.get("core"):
        (vd / f"{mod}.core.json").write_text(json.dumps(view["core"], indent=1))
    (vd / "provenance.json").write_text(json.dumps(prov, indent=1))
    (vd / "gates.json").write_text(json.dumps(gates, indent=1))
    return dict(module=mod, view=str(vd), complete=not problems, problems=problems,
                pins_sha256=kitblk.get("pins_sha256"), pins_canon_sha256=kitblk.get("pins_canon_sha256"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit", required=True)
    ap.add_argument("--signoff", required=True, help="the SIGNED signoff.json of the run")
    ap.add_argument("--out", required=True, help="views root; the view goes to OUT/<module>/")
    ap.add_argument("--die", required=True)
    ap.add_argument("--base", help="run results dir with <module>.lef (default: found under the kit)")
    ap.add_argument("--lec", help="routed LEC json of the signed netlist")
    ap.add_argument("--src-commit")
    ap.add_argument("--flow-tag")
    ap.add_argument("--note")
    a = ap.parse_args(argv)
    res = export(a.kit, a.signoff, a.out, a.die, a.base, a.lec, a.src_commit, a.flow_tag, a.note)
    print(json.dumps(res))
    return 0 if res["complete"] else 2


if __name__ == "__main__":
    sys.exit(main())
