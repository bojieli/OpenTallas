"""Kit gen side of CLAND-BIN plan sites (FABLE-GENBUG G2, DIE-QC-103 PLAN-KEY 11-15).

Sidecar <plan stem>.cland_bin_sites.json, schema opentallas.cland_bin_sites.v1, type-frame um:
  {types: {<type>: {<bus>: {u_bin: [x, y], u_st: [x, y], route_um, equal_hop_um, plan_stations}}}}
becomes the kit file cland_bin_sites.tcl read by landing_placement.tcl (OT_CLAND_BIN=eq):
  set cland_bin_sites { <bus> {x y}  <bus>:bin {x y} ... }       (<bus> = u_st site, <bus>:bin = u_bin site)
"""
import json
from pathlib import Path

SCHEMA = "opentallas.cland_bin_sites.v1"


def sidecar_path(plan_path):
    p = Path(plan_path)
    return p.with_name(p.stem + ".cland_bin_sites.json")


def _num(v, what):
    if not (isinstance(v, (int, float)) and not isinstance(v, bool)) or v != v or abs(v) > 1e6:
        raise ValueError(f"cland_bin_sites: {what}: {v!r} is not a finite number")
    return float(v)


def _xy(v, what):
    if not isinstance(v, (list, tuple)) or len(v) != 2:
        raise ValueError(f"cland_bin_sites: {what}: need [x, y], got {v!r}")
    return _num(v[0], what), _num(v[1], what)


def table(doc, type_name):
    """Tcl text for one type, or '' when the sidecar has no entry for it (the hook then walks forward as before)."""
    if doc.get("schema") != SCHEMA:
        raise ValueError(f"cland_bin_sites: schema {doc.get('schema')!r}, need {SCHEMA}")
    types = doc.get("types") or {}
    row = types.get(type_name)
    if row is None:
        row = types.get(type_name.split("__")[0])
    if not row:
        return ""
    out = ["set cland_bin_sites {"]
    for bus in sorted(row):
        if not bus.replace("_", "").isalnum():
            raise ValueError(f"cland_bin_sites: bus name {bus!r}")
        e = row[bus]
        if "u_st" in e:
            x, y = _xy(e["u_st"], f"{type_name}/{bus}/u_st")
            out.append(f" {bus} {{{x:.3f} {y:.3f}}}")
        if "u_bin" in e:
            x, y = _xy(e["u_bin"], f"{type_name}/{bus}/u_bin")
            out.append(f" {bus}:bin {{{x:.3f} {y:.3f}}}")
    out.append("}")
    return "\n".join(out) + "\n"


def for_kit(plan_path, type_name):
    """'' when there is no plan path or no sidecar; the kit then has no cland_bin_sites.tcl."""
    if not plan_path:
        return ""
    sc = sidecar_path(plan_path)
    if not sc.is_file():
        return ""
    return table(json.loads(sc.read_text()), type_name)


if __name__ == "__main__":
    import sys
    sys.stdout.write(table(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2]))
