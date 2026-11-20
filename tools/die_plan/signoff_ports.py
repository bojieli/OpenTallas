#!/usr/bin/env python3
"""REAL-VIEWS-PORTS 11-19 (COORD): per-port pin-register clock arrivals for an EXISTING signed record.

    signoff_ports.py RECORD/signoff.json --out DIR [--corners tt,ff] [--image IMG] [--docker CMD] [--dry]

New sign-offs write corners.<c>.port_pinflops themselves (signoff.py SO_CKP).  For records signed before that, this
re-runs only the setup + clock-arrival part of the signoff.py session on the record's own routed DB (inputs.odb /
inputs.base, same kit libraries, SDC, parasitics and nomcap as signoff.run_corner): no timing reports, no checks.
Self-check: the re-measured insertion_pinflops (n/min/max) must equal the record's own within TOL_PS, else the sidecar
says MISMATCH and real_views.py does not use it.

Writes DIR/signoff_ports.json (schema real_views.ports.v1): {record, record_sha256, odb, corners: {TT|FF: {port: {n, min,
max, in, out}}}, check: {TT|FF: {record, remeasured, match}}, verdict MATCH|MISMATCH}.  Never touches the record itself;
publish_sidecar() copies the sidecar next to a record only when none is there yet (append only)."""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import signoff as SO  # noqa: E402

TOL_PS = 0.5
SCHEMA = "real_views.ports.v1"
CUT_A = "# ---- timing with the block's own SDC ----"
CUT_B = "# ---- clock: active-edge arrival at register clock pins, pin flops ----"


def light_session(text):
    """setup (libraries, DB, parasitics, SDC, propagated clocks, port lists) + the clock-arrival block only."""
    if text.count(CUT_A) != 1 or text.count(CUT_B) != 1 or text.find(CUT_A) > text.find(CUT_B):
        raise ValueError("signoff_ports: session template anchors changed")
    return text[:text.find(CUT_A)] + text[text.find(CUT_B):]


def disc_from_record(rec):
    inp = rec.get("inputs") or {}
    if not inp.get("base"):
        raise ValueError("record has no inputs.base")
    d = SO.discover(inp["base"], kit=inp.get("kit"), sdc=inp.get("sdc"))
    for k in ("odb", "spef", "library_config", "sdc_lint_ctx", "ff_bound_ps", "tt_vclk", "ft_ports"):
        if inp.get(k) is not None:
            d[k] = inp[k]
    if not Path(d["odb"]).is_file():
        raise FileNotFoundError(f"routed DB gone: {d['odb']}")
    return d


def check(rec, corner, res):
    a = ((rec.get("corners") or {}).get(corner) or {}).get("insertion_pinflops") or {}
    b = res.get("insertion_pinflops") or {}
    ok = bool(a and b and a.get("n") == b.get("n")
              and all(abs(float(a[k]) - float(b[k])) <= TOL_PS for k in ("min", "max")))
    return dict(record=a or None, remeasured=b or None, match=ok)


def sidecar(rec_path, rec, disc, results):
    corners, chk = {}, {}
    for c, res in results.items():
        C = c.upper()
        corners[C] = res.get("port_pinflops")
        chk[C] = check(rec, c, res)
    ok = all(v["match"] for v in chk.values()) and all(corners.values())
    return dict(schema=SCHEMA, record=str(rec_path), record_sha256=hashlib.sha256(Path(rec_path).read_bytes()).hexdigest(),
                name=rec.get("name"), odb=disc.get("odb"), corners=corners, check=chk,
                verdict="MATCH" if ok else "MISMATCH", tool="tools/die_plan/signoff_ports.py")


def publish_sidecar(src, record_dir):
    """append only: copy the sidecar into a signed-store record dir when it has none; never overwrite."""
    dst = Path(record_dir) / "signoff_ports.json"
    if dst.exists():
        return False
    shutil.copyfile(src, dst)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    ap.add_argument("--corners", default="tt,ff")
    ap.add_argument("--image", default=SO.IMAGE)
    ap.add_argument("--docker", default="sudo docker")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    rec = json.loads(Path(a.record).read_text())
    disc = disc_from_record(rec)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    orig = SO.session_tcl
    SO.session_tcl = lambda *x, **k: light_session(orig(*x, **k))
    try:
        res = {c: SO.run_corner(c, disc, out, image=a.image, docker=a.docker, dry=a.dry)
               for c in a.corners.split(",")}
    finally:
        SO.session_tcl = orig
    if a.dry:
        print(json.dumps({c: r.get("cmd") for c, r in res.items()}, indent=1))
        return 0
    sc = sidecar(a.record, rec, disc, res)
    (out / "signoff_ports.json").write_text(json.dumps(sc, indent=1) + "\n")
    print(f"SIGNOFF_PORTS {sc['verdict']} {rec.get('name')} ports "
          + " ".join(f"{c}:{len(v or {})}" for c, v in sc["corners"].items())
          + " check " + " ".join(f"{c}:{'ok' if v['match'] else 'DIFF'}" for c, v in sc["check"].items()))
    return 0 if sc["verdict"] == "MATCH" else 1


if __name__ == "__main__":
    sys.exit(main())
