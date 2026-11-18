"""route_env: the ONE function that decides the route-stage environment exports that are a pure function of the job spec.

WAVE-FLOW-R2 11-17 (COORD): a kit's job.json route command did not carry the exports the closure loop adds when it builds the job (OT_ROUTE_HOLD_CORNERS=mm, HM,
OT_ORFS_CORNER, ...), so a hand / ref_tile launch from job.json failed closed at CTS ("BC scene unavailable"; the svc split lost 6 core runs).  closure_loop.launch_stage
and tools/ref_tile gen_job both call route_exports(), so the loop's env and job.json's env cannot drift (test_route_env.py compares them)."""
import shlex
import time

HM_DEFAULT_SINCE = "2026-10-06T20:40"
HM_LOW_SINCE = "2026-10-07T04:17"      # new jobs from here: route hold margin 10 ps, hold closed by the post-route ECO
# FLOW-HOLD (2026-10-07): jobs created from here route with multi-mode hold repair (OT_ROUTE_HOLD_CORNERS=mm: SS setup +
# FF hold under the FF sign-off constraints at CTS / global route) and HM_MM route hold margin (applies at FF only)
MM_SINCE = "2026-10-07T21:00"
# OWNER OPTION B (2026-10-07 20:45): closure = setup at TT + hold at FF + DRC 0.  Every calibrate / route launched from here routes with CORNER=TC
OPTB_SINCE = "2026-10-07T20:20"
HM_MM = 0.050


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def route_exports(spec, kind="route", created="", pg_strict=False, now=None):
    """-> {NAME: value (str)} in launch order: the exports the loop sets for a calibrate / route stage from the spec alone.
    created = the job's creation stamp (the date-gated defaults), pg_strict = the source-bound PG policy of the job."""
    out = {}
    now = now or now_iso()
    out["OT_PG_JOB_STRICT"] = str(int(bool(pg_strict)))
    if not pg_strict:
        out["OT_PG_STRICT"] = "0"
    if spec.get("macro_cts") is False:
        out["OT_CTS_MACRO_CLUSTER"] = "0"
    if kind in ("calibrate", "route") and created >= HM_DEFAULT_SINCE:
        hm_default = 0.010 if created >= HM_LOW_SINCE else 0.035
        if created >= MM_SINCE and spec.get("route_hold_corners", "mm") == "mm":
            hm_default = HM_MM
        out["HM"] = str(spec.get("route_hold_margin_ns", hm_default))
    if kind == "route" and now >= OPTB_SINCE and spec.get("route_corner", "TC") != "keep":
        out["OT_ORFS_CORNER"] = str(spec.get("route_corner", "TC"))
    if kind in ("calibrate", "route"):
        rhc = spec.get("route_hold_corners", "mm" if created >= MM_SINCE else "primary")
        if rhc != "keep":
            out["OT_ROUTE_HOLD_CORNERS"] = str(rhc)
    return out


def shell_exports(env):
    """`export K=V` lines (the loop's env text) for an exports dict"""
    return "".join(f"export {k}={shlex.quote(v)}\n" for k, v in env.items())


def cmd_prefix(env):
    """the same exports as one shell prefix for a command line: `export K=V; export K2=V2; `"""
    return "".join(f"export {k}={shlex.quote(v)}; " for k, v in env.items())
