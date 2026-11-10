"""LEF-only correction of a child view at the point a type kit takes its macro LEF (COORD 11-09, class DRT-0073).

lef_overrides/map.json names, per LEF file name, the plan LEF it replaces (base_sha256) and the corrected LEF
(lef_overrides/<name>, md5 + sha256).  The plan is not touched, so no row key changes; netlist and timing views are not
touched.  A plan LEF other than base_sha256 is left alone (a different view of the module); a corrected file that does not
match its md5 stops the gen.  A kit that took a correction carries lef_override.json with both hashes."""
import hashlib
import json
from pathlib import Path

DIR = Path(__file__).resolve().with_name("lef_overrides")
_map = None
APPLIED = {}


def _hash(path, name):
    return hashlib.new(name, Path(path).read_bytes()).hexdigest()


def rows():
    global _map
    if _map is None:
        f = DIR / "map.json"
        _map = json.loads(f.read_text()) if f.is_file() else {}
    return _map


def select(lef, resolve, log=print):
    """the LEF path a kit should use for this plan LEF path"""
    if not lef:
        return lef
    name = Path(str(lef)).name
    row = rows().get(name)
    if not row:
        return lef
    plan = Path(resolve(lef))
    if not plan.is_file():
        return lef
    if _hash(plan, "sha256") != row["base_sha256"]:
        log("OT_LEF_OVERRIDE " + json.dumps(dict(lef=name, action="not applied: plan LEF is not the base of this correction")))
        return lef
    if (plan.parent / "landing_evidence").exists():
        raise ValueError(f"LEF override {name}: the view carries hard landing evidence, which proves the signed LEF by hash")
    f = DIR / name
    if not f.is_file() or _hash(f, "md5") != row["md5"] or _hash(f, "sha256") != row["sha256"]:
        raise ValueError(f"LEF override {name}: {f} does not match its recorded md5 {row['md5']}")
    if str(f) not in APPLIED:
        APPLIED[str(f)] = dict(lef=name, plan_lef=str(lef), base_sha256=row["base_sha256"], sha256=row["sha256"], md5=row["md5"],
                               source=row.get("source", ""))
        log("OT_LEF_OVERRIDE " + json.dumps(dict(lef=name, action="applied", md5=row["md5"])))
    return str(f)


def write_receipt(kd, macros):
    """kd/lef_override.json for the corrected LEFs this kit staged; nothing written when none (byte-identical kits)"""
    used = {str(m[2]) for m in macros} & set(APPLIED)
    if used:
        (Path(kd) / "lef_override.json").write_text(json.dumps(dict(
            schema="opentallas.lef_override.v1", rows=[APPLIED[u] for u in sorted(used)]), indent=2) + "\n")
