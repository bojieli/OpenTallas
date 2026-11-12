"""LF-CS-FWD (S81-LEAF-FLOOR-2 11-12): every leaf reachable from a die slice instance takes its CS_* depths from the
slice's LF_CS_* parameters (no hard-coded leaf depth), and every slice module on the way declares and forwards all of
them, so the die netlist (stage_lfcs_netlist) can set the plan's depths per leaf."""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SL = REPO / "rtl/dsrom_sys/s81_dv/slice"
DIE = REPO / "physical/die_plan/s81/bind/inputs/die_b178.v"
PORTFIX = REPO / "physical/die_plan/s81/bind/source_modules/portfix178"   # the as-built's source copies (they win)
CL = ["HI_D", "HI_GS", "HO_D", "HO_GS", "H_G", "VNI_D", "VNO_D", "Y_D", "U_D", "SW_D", "SWR_D", "RA_D", "RAR_D",
      "VE_D", "VER_D", "PVS_D", "VSP_D"]
PL = r"#\((?P<p>(?:[^()]|\((?:[^()]|\([^()]*\))*\))*)\)"


def _strip(t):
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", t, flags=re.S))


def _modules():
    mods = {}
    for f in sorted(SL.rglob("*.sv")) + sorted(PORTFIX.glob("*.sv")):
        if "/test/" in str(f):
            continue
        t = _strip(f.read_text(errors="replace"))
        for m in re.finditer(r"\bmodule\s+(\w+)(.*?)\bendmodule\b", t, re.S):
            mods[m.group(1)] = (f, m.group(2))
    return mods


def _insts(body, names):
    for m in re.finditer(rf"\b(\w+)\s*(?:{PL})?\s*(u_\w+)\s*\(", body):
        if m.group(1) in names:
            yield m.group(1), m.group("p") or "", m.group(3)


def _die_slices():
    t = DIE.read_text()
    return sorted({m.group(1) for m in re.finditer(r"^\s*(ot_s81sl_slice\w*)\s+(?:#\(.*?\)\s*)?u_s_\w+\s*\(", t, re.M)})


def check(mods, tops):
    errs, reach = [], {}

    def reaches(m, stack=()):
        if m in reach:
            return reach[m]
        if m == "ot_s81sl_leaf":
            return True
        r = False
        for c, _, _ in _insts(mods[m][1], set(mods) | {"ot_s81sl_leaf"}):
            if c not in stack and reaches(c, stack + (m,)):
                r = True
        reach[m] = r
        return r

    seen = set()
    todo = [t for t in tops if t in mods]
    errs += [f"{t}: die slice module not found under {SL}" for t in tops if t not in mods]
    while todo:
        m = todo.pop()
        if m in seen or not reaches(m):
            continue
        seen.add(m)
        f, body = mods[m]
        hdr = body.split(";", 1)[0]
        for c, p, inst in _insts(body, set(mods) | {"ot_s81sl_leaf"}):
            if c == "ot_s81sl_leaf":
                for x in CL:
                    if not re.search(rf"\.CS_{x}\(\s*LF_CS_{x}\s*\[", p):
                        errs.append(f"{f.name}:{m}.{inst}: CS_{x} not taken from LF_CS_{x}")
            elif reaches(c):
                for x in CL:
                    if not re.search(rf"parameter\s*\[19:0\]\s*LF_CS_{x}\b", hdr):
                        errs.append(f"{f.name}:{m}: no LF_CS_{x} parameter")
                    if not re.search(rf"\.LF_CS_{x}\(\s*LF_CS_{x}\s*\)", p):
                        errs.append(f"{f.name}:{m}.{inst} ({c}): LF_CS_{x} not forwarded")
                todo.append(c)
    return errs, seen


def test_every_die_slice_forwards_lf_cs_to_every_leaf():
    mods = _modules()
    tops = _die_slices()
    assert len(tops) >= 8, tops
    errs, seen = check(mods, tops)
    assert not errs, "\n".join(errs[:40])
    assert {"ot_s81sl_slice_c1x_k8_cap5r_lp_e6", "ot_s81sl_slice_c1x_k8_cap5r_lp_w3", "ot_s81sl_slice_c3x_k8_cap5r_lp_w3", "ot_s81sl_slice_w3"} <= seen
    assert str(mods["ot_s81sl_slice_lepw_mab_hbc_prod_mu_72"][0]).startswith(str(PORTFIX))


def test_a_hard_coded_leaf_depth_or_dropped_forward_is_caught():
    mods = _modules()
    f, body = mods["ot_s81sl_slice_c1x_k8_cap5r_lp_w3"]
    bad = dict(mods)
    bad["ot_s81sl_slice_c1x_k8_cap5r_lp_w3"] = (f, re.sub(r"\.CS_Y_D\(LF_CS_Y_D\[4 \* 3 \+: 4\]\)", ".CS_Y_D(1)", body, count=1))
    errs, _ = check(bad, ["ot_s81sl_slice_c1x_k8_cap5r_w_w3"])
    assert errs == ["ot_s81sl_slice_c1x_k8_cap5r_lp_w3.sv:ot_s81sl_slice_c1x_k8_cap5r_lp_w3.u_lf3: CS_Y_D not taken from LF_CS_Y_D"]
    f, body = mods["ot_s81sl_slice_c1x_k8_cap5r_w_w3"]
    bad = dict(mods)
    bad["ot_s81sl_slice_c1x_k8_cap5r_w_w3"] = (f, body.replace(", .LF_CS_SW_D(LF_CS_SW_D)", "", 1))
    errs, _ = check(bad, ["ot_s81sl_slice_c1x_k8_cap5r_w_w3"])
    assert errs and all("LF_CS_SW_D not forwarded" in e for e in errs)
