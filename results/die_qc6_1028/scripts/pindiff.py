import json, sys
from pathlib import Path
def load(f):
    d = json.loads(Path(f).read_text())
    L = d if isinstance(d, list) else d.get("pins", d)
    out = {}
    for p in L:
        out[p["name"]] = p
    return out
pairs = [("qfd_dv_s8x_vmr", "cores/su/sle_su_c_u_suvm_u_vm8q_u_va_pins.json"), ("qfd_dv_s8_crh_rp1", "cores/su/slw_su_c_u_suvm_u_vm8q_u_ch_pins.json"),
         ("qfd_dv_s8x_prog", "cores/su/sle_su_c_u_suvm_u_vm8q_u_pg_pins_aspect1713.json"), ("qfd_dv_s5_su8_rst3", "cores/su/sle_su_c_u_suvm_u_su8_pins.json"),
         ("qfd_dv_s8x_crh", "cores/su/sle_su_c_u_suvm_u_vm8q_u_ch_pins.json")]
for m, pf in pairs:
    s = load(Path(sys.argv[1]) / m / "pins.json"); p = load(Path(sys.argv[2]) / pf)
    only_s, only_p = set(s) - set(p), set(p) - set(s)
    common = set(s) & set(p)
    k = next(iter(common)) if common else None
    moved = sum(1 for n in common if (round(float(s[n].get("x", 0)), 3), round(float(s[n].get("y", 0)), 3), s[n].get("layer")) != (round(float(p[n].get("x", 0)), 3), round(float(p[n].get("y", 0)), 3), p[n].get("layer")))
    print(m, "signed", len(s), "plan", len(p), "only_signed", len(only_s), sorted(only_s)[:4], "only_plan", len(only_p), sorted(only_p)[:4], "moved", moved, "keys s", sorted(s[k])[:8] if k else None, "keys p", sorted(p[k])[:8] if k else None)
    if k: print("   e.g.", k, {x: s[k].get(x) for x in ("x","y","layer","dir","direction")}, {x: p[k].get(x) for x in ("x","y","layer","dir","direction")})
