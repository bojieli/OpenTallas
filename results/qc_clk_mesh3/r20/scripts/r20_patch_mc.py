import sys
p = sys.argv[1]
s = open(p).read()
old = """               tap_slew_ps={p: r3(v) for p, v in zip(parts, sl_ent)}, geometry=a.geometry, feed=getattr(a, "feed", "mesh3"),
               checked="UNCHECKED")"""
new = """               tap_slew_ps={p: r3(v) for p, v in zip(parts, sl_ent)}, geometry=a.geometry, feed=getattr(a, "feed", "mesh3"),
               # R20 (NUMBER-CHECK-QC-R19): the solver states its own MC segment so the pair_u guard can fire.  The fine
               # mesh netlist ends at the partition tap node on the strap (taps = rec taps[].tap); the tap buffer and
               # the tap->entry stub are NOT in it (they are priced by AOCV in pair_u).
               mc_includes_stub=False, mc_segment="die input -> fine-mesh tap node",
               checked="UNCHECKED")"""
assert s.count(old) == 1; s = s.replace(old, new)
old = """    out = dict(summary=summ, samples=[dict(sample=r["sample"], tap_skew_ps=r["tap_skew_ps"], tap_arr_ps=r["tap_arr_ps"]) for r in rows],
               checked="UNCHECKED")"""
new = """    flags = {r.get("mc_includes_stub") for r in rows}
    if None in flags:
        raise SystemExit("collect: a solve json does not state mc_includes_stub (pre-R20 solver); re-run the solve")
    if len(flags) != 1:
        raise SystemExit("collect: solves disagree on mc_includes_stub")
    out = dict(summary=summ, samples=[dict(sample=r["sample"], tap_skew_ps=r["tap_skew_ps"], tap_arr_ps=r["tap_arr_ps"]) for r in rows],
               mc_includes_stub=flags.pop(), checked="UNCHECKED")"""
assert s.count(old) == 1; s = s.replace(old, new)
helper = '''

def _set_mc_stub_flag(docs):
    """R20: pair_u.mc_includes_stub from the collected solve docs (absent = legacy pre-R20 solve: not asserted)."""
    vals = {d.get("mc_includes_stub") for d in docs}
    pair_u.mc_includes_stub = bool(True in vals)
    return pair_u.mc_includes_stub


def cmd_sta_export(a):'''
assert s.count("\n\ndef cmd_sta_export(a):") == 1; s = s.replace("\n\ndef cmd_sta_export(a):", helper, 1)
old = """    solve_ = {c: json.loads(Path(v).read_text()) for c, v in json.loads(a.mesh_skew).items()}
    aocv = json.loads(Path(a.aocv).read_text())["clock_aocv"]
    tap = {t["part"]: t for t in rec["taps"]}
    out = Path(a.out)"""
new = """    solve_ = {c: json.loads(Path(v).read_text()) for c, v in json.loads(a.mesh_skew).items()}
    _set_mc_stub_flag(solve_.values())
    aocv = json.loads(Path(a.aocv).read_text())["clock_aocv"]
    tap = {t["part"]: t for t in rec["taps"]}
    out = Path(a.out)"""
assert s.count(old) == 1; s = s.replace(old, new)
old = """    solve_ = {c: json.loads(Path(v).read_text())["samples"] for c, v in json.loads(a.mesh_skew).items()}
    aocv = json.loads(Path(a.aocv).read_text())["clock_aocv"]
    g = a.g_per_mm"""
new = """    docs_ = {c: json.loads(Path(v).read_text()) for c, v in json.loads(a.mesh_skew).items()}
    _set_mc_stub_flag(docs_.values())
    solve_ = {c: d["samples"] for c, d in docs_.items()}
    aocv = json.loads(Path(a.aocv).read_text())["clock_aocv"]
    g = a.g_per_mm"""
assert s.count(old) == 1; s = s.replace(old, new)
open(p, "w").write(s)
print("patched")
