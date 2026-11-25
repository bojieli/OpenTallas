"""adv_stn_deadlane.py -- PRECHECK ADV-STN-DEADLANE (KV-OWN-PV-R2 11-25, COORD): internal-station rows on 0-bit lanes, report only.

The strict bind stops at the FIRST internal_stations row whose partition has no outgoing link on that bus (native_istations:
'expected one outgoing lane'); the lane exists in the plan but the bind gave it 0 items (KV A5t8: L55 pv_N_2 o_astk_E, then 13
more types with the same row).  stn_deadlane.py lists them all with the bind's own lane rule (the bind head up to annotate).
The head needs the elab netlist, which a plain PRE does not have, so this check:

  - reads a finished scan: kw stn_deadlane= / $OT_STN_DEADLANE_REPORT (an OUT/stn_deadlane.json of stn_deadlane.py) whose
    plan_sha equals this plan's sha (a report of another plan is ignored: 'not checked (stale report)'), or
  - runs the scan when kw elab= / $OT_STN_DEADLANE_ELAB names an elab out dir (with asbuilt.json) and kw asbuilt= /
    $OT_STN_DEADLANE_ASBUILT the as-built (a subprocess, minutes; its OUT is a fresh temp dir), else
  - prints 'WARN ADV-STN-DEADLANE not checked (no elab netlist ...)'.

Lines: WARN ADV-STN-DEADLANE DEAD-TYPE <type> <bus> ... (fix: drop the row, latency-neutral; stn_deadlane.py --ops writes the
plan_ops.v1 row) / DEAD-PARTIAL (per-instance: split or a carrying lane) / MULTI.  Never a FAIL, never raises.
findings(raw, plan_path, tree=None, **kw) -> WARN lines."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

CHECK = "ADV-STN-DEADLANE"
MAX_LINES = 40
HERE = Path(__file__).resolve().parent


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def lines_from_report(rep, sha):
    if rep.get("plan_sha") != sha:
        return [_w(f"not checked (stale report: plan_sha {rep.get('plan_sha')} != {sha})")]
    out = []
    for f in rep.get("findings", []):
        parts = f.get("dead_parts") or f.get("multi_parts") or []
        fix = {"DEAD-TYPE": "drop the row (0 bits ride it; latency-neutral)",
               "DEAD-PARTIAL": "per-instance: split the type or give the dead partitions a carrying lane",
               "MULTI": "one outgoing lane per partition and bus"}.get(f.get("state"), "")
        out.append(_w(f.get("state"), f.get("type"), f.get("bus"), f"parts={','.join(parts[:6])} of {len(f.get('parts', []))}",
                      f"(fix: {fix})"))
    if len(out) > MAX_LINES:
        out = out[:MAX_LINES] + [_w(f"... {len(out) - MAX_LINES} more in the stn_deadlane.json report")]
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        sha = hashlib.sha256(Path(plan_path).read_bytes()).hexdigest()[:12]
        rp = kw.get("stn_deadlane") or os.environ.get("OT_STN_DEADLANE_REPORT")
        if rp and Path(rp).is_file():
            return lines_from_report(json.loads(Path(rp).read_text()), sha)
        elab = kw.get("elab") or os.environ.get("OT_STN_DEADLANE_ELAB")
        ab = kw.get("asbuilt") or os.environ.get("OT_STN_DEADLANE_ASBUILT")
        if not (elab and ab and (Path(elab) / "asbuilt.json").is_file()):
            return [_w("not checked (no elab netlist: set OT_STN_DEADLANE_ELAB=<bind.py elab --out dir> + OT_STN_DEADLANE_ASBUILT, "
                       "or OT_STN_DEADLANE_REPORT=<stn_deadlane.json>)")]
        with tempfile.TemporaryDirectory(prefix="stn_deadlane_") as td:
            r = subprocess.run([sys.executable, "-I", "-B", str(HERE / "stn_deadlane.py"), str(plan_path), "--asbuilt", str(ab),
                                "--elab", str(elab), "--out", td], cwd=tree or None, capture_output=True, text=True,
                               timeout=int(os.environ.get("OT_STN_DEADLANE_TIMEOUT", "3600")))
            js = Path(td) / "stn_deadlane.json"
            if not js.is_file():
                tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [f"rc {r.returncode}"]
                return [_w(f"not checked ({tail[0][:200]})")]
            return lines_from_report(json.loads(js.read_text()), sha)
    except Exception as exc:  # noqa: BLE001 advisory: never raises
        return [_w(f"not checked ({type(exc).__name__}: {str(exc)[:200]})")]
