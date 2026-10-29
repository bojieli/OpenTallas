p = "gen_core_kit_hbm.py"
t = open(p).read()
reps = [
    ('f"export DIE_AREA = 0 0 {w:g} {h:g}",', 'f"export DIE_AREA = 0 0 {_um(w)} {_um(h)}",'),
    ('f"export CORE_AREA = {m:g} {m:g} {w - m:g} {h - m:g}",',
     'f"export CORE_AREA = {_um(m)} {_um(m)} {_um(w - m)} {_um(h - m)}",'),
    ('cfg += [f"export RTLMP_FENCE_LX = {lx:g}", f"export RTLMP_FENCE_LY = {ly:g}",',
     'cfg += [f"export RTLMP_FENCE_LX = {_um(lx)}", f"export RTLMP_FENCE_LY = {_um(ly)}",'),
    ('f"export RTLMP_FENCE_UX = {ux:g}", f"export RTLMP_FENCE_UY = {uy:g}"]',
     'f"export RTLMP_FENCE_UX = {_um(ux)}", f"export RTLMP_FENCE_UY = {_um(uy)}"]'),
    ("rows.append(f\"  {{{inst}}} {placement['macro']} {x:g} {y:g} {orient}\")",
     "rows.append(f\"  {{{inst}}} {placement['macro']} {_um(x)} {_um(y)} {orient}\")"),
    ("f\"{' '.join(f'{v:g}' for v in g['box_um'])}}}\"", "f\"{' '.join(_um(v) for v in g['box_um'])}}}\""),
]
for a, b in reps:
    assert t.count(a) == 1, (a, t.count(a))
    t = t.replace(a, b)
anchor = "def snap_macro_placement("
helper = '''def _um(v):
    """HBM-CORES-KITS-2: geometry (um) for config.mk / Tcl.  '{v:g}' keeps only 6 significant digits, so the C24 plan
    outline 1635.552 um became DIE_AREA 1635.55 (kit_preflight master_slice FAIL, hfd_hgi_vms_glue_nw_t) and every
    coordinate >= 1000 um lost its last decimal.  10 significant digits keep the plan's 1-nm values and still drop
    float noise (177.98399999999992 -> 177.984); values < 1000 um with <= 3 decimals print as before."""
    return f"{float(v):.10g}"


'''
assert t.count(anchor) == 1
t = t.replace(anchor, helper + anchor)
open(p, "w").write(t)
print("patched")
