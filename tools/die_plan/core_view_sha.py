"""KIT-OPS-6 11-14 (COORD item 10, TYPE-HDEPC): a hard core's lef / lib a kit takes must be the SIGNED view, by sha.
hd_host_e kits since 11-13 16:32 timed against results/head_he_epc_h2_1110/ot_s81hd_he_epc_tt.lib (sha 8aad87, the 11-10 build): the plan binds a
core's lib / lef by PATH under the die src, nothing compared the bytes with the signed record's view (f663e3, setup arcs ~220 ps apart).
check(core, resolve, expected): expected = {module: {"_tt.lib": sha256, "_ff.lib": ..., ".lef": ...}} (the signed views;
tools/autopilot/core_view_audit.py writes it from the signed export index) plus the plan core's own optional lib_sha256 / lef_sha256.
A declared sha that the resolved file does not have raises STALE-CORE-VIEW (fail closed, naming module, path, both shas).
No expected table and no plan sha = unchanged.  Table from env OT_SIGNED_VIEW_SHA (JSON file)."""
import hashlib
import json
import os


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_expected(path=None):
    path = path or os.environ.get("OT_SIGNED_VIEW_SHA")
    if not path:
        return {}
    return json.loads(open(path).read())


def check(core, resolve, expected=None):
    """-> list of (kind, path, kit_sha, signed_sha) mismatches (empty = ok); raises nothing"""
    exp = (expected or {}).get(core.get("module"), {})
    want = {"lef": core.get("lef_sha256") or exp.get(".lef"), "lib": core.get("lib_sha256") or exp.get("_tt.lib")}
    bad = []
    for kind in ("lef", "lib"):
        if not want[kind] or not core.get(kind):
            continue
        p = resolve(core[kind])
        got = sha256_file(p)
        if got != want[kind]:
            bad.append((kind, str(p), got, want[kind]))
    return bad


def gate(core, resolve, expected=None):
    bad = check(core, resolve, expected)
    if bad:
        raise ValueError("STALE-CORE-VIEW " + core.get("module", "?") + ": " + "; ".join(
            f"{k} {p} sha {g[:12]} != signed {w[:12]}" for k, p, g, w in bad))
