#!/usr/bin/env python3
"""ADV-DEPTH-VS-RTL (PRECHECK-R2 11-22, static estimator, never a gate): plan stage counts vs the depths the RTL binds.

Two advisories, both read-only and seconds-scale:

(1) LF_CS (S81 leaves).  The strict bind's LF_CS_DEPTH gate (leaf_cs_depth.check, run after emit) compares, per
    (leaf type, class), the plan depth (deepest internal_stations row of the class, kit_istations.core_class) with the
    stage registers counted in the bound partition.  The bound count is fixed BEFORE the bind by the die netlist of the
    as-built manifest: each slice instance u_s_<slice> carries #(.LF_CS_<C>_D(20'h.....)) with one nibble per leaf k
    (stage_lfcs_netlist.py stages them from a plan); the leaf of partition s_<slice>_L<k> elaborates
        hi = nibble(HI_D) + XR      (XR = LF_VP_XR mask bit k, ot_s81sl_vp CS_HI_E = CS_HI_D + XR)
        ho = nibble(HO_D) + SR      (SR = 1 under define OT_S81SL_VP_SRAMREG, ot_s81sl_vp u_cst_ho D + SRO)
        other class c = nibble(<C>_D)
    A plan depth != that number fails the strict bind (J8 istation_respace 53cab071c82f: 100 LF_CS_DEPTH errors,
    bind FAILED 11-22 13:39).  This check reads the plan + the manifest's netlist text and predicts those rows.
    Fix: restage the netlist from this plan (tools/die_plan/stage_lfcs_netlist.py, --vp-xr / --vp-sr contracts as the
    netlist of record) in the same event, or drop the extra plan station(s).

(2) Lane cycles.  lanes[].fixed_cycles must equal latency.lanes[id].fixed, and latency cycles must be
    fixed + boundary + stations + clock_landing + pad (natural = cycles - pad).  A plan event that adds stations without re-pricing
    leaves these inconsistent.

    findings(raw, plan_path, tree=None, asbuilt=None, netlist=None) -> ["WARN ADV-DEPTH-VS-RTL ...", ...]
"""
import json
import os
import re
import sys
import time
from pathlib import Path

TAG = "WARN ADV-DEPTH-VS-RTL"
CAP = 20
LEAF_TYPE = re.compile(r"^ot_s81sl_(kv_)?leaf__")
PART = re.compile(r"^s_(\w+?)_L([0-4])$")
CL = ["HI_D", "HO_D", "VNI_D", "VNO_D", "Y_D", "U_D", "SW_D", "SWR_D", "RA_D", "RAR_D", "VE_D", "VER_D", "PVS_D", "VSP_D"]
INST = re.compile(r"^\s*(?P<mod>ot_s81sl_slice\w*)\s+(?:#\((?P<p>(?:[^()]|\([^()]*\))*)\)\s*)?(?P<inst>u_s_\w+)\s*\(", re.M)
SR_DEFINE = "OT_S81SL_VP_SRAMREG"
XR_DEFINE = "OT_S81SL_VP_XR"

# Fallback copy of kit_istations.CORE_CLASSES / core_class (used only if the sibling module cannot be imported).
_P = r"core:u_lf\."
_CORE_CLASSES = [
    ("cs", rf"^{_P}u_vn\.u_a\.c_s\|u_lf\.u_vn\.u_b", True),
    ("hi", rf"^{_P}u_vn\.u_[ab]\.(hq_|hr_)\w+\|u_lf\.u_vp\.g_ln\[\d+\]\.u_l$", True),
    ("ho", rf"^{_P}u_vn\.u_[ab]\.hw_\w+\|u_lf\.u_vp\.g_ln\[\d+\]\.u_l$", False),
    ("vni", rf"^{_P}u_vn\.u_[ab]\.(n_go|n_pre|wl_\w+|hw_\w+|hr_\w+)\|u_lf\.u_vp\.u_b[01]$", False),
    ("vno", rf"^{_P}u_vn\.u_[ab]\.hq_\w+\|u_lf\.u_vp\.u_b[01]$", True),
    ("y", rf"^{_P}u_vn\.u_[ab]\.y\w*\|u_lf\.u_vq\.", True),
    ("y", rf"^{_P}u_vq\.y\w*\|u_lf\.u_vn\.", False),
    ("u", rf"^{_P}u_vq\.(u|um)\w*\|u_lf\.u_vs\.", False),
    ("u", rf"^{_P}u_vs\.(u|um)\w*\|u_lf\.u_vq\.", True),
    ("sw", rf"^{_P}u_vs\.sw_\w+\|u_lf\.u_vsw\.i_", True),
    ("swr", rf"^{_P}u_vs\.sw_\w+\|u_lf\.u_vsw\.o_", False),
    ("sw", rf"^{_P}u_vsw\.i_\w+\|u_lf\.u_vs\.", False),
    ("swr", rf"^{_P}u_vsw\.o_\w+\|u_lf\.u_vs\.", True),
    ("ra", rf"^{_P}u_vs\.ra_\w+\|u_lf\.u_rxsf\.", True),
    ("rar", rf"^{_P}u_vs\.ra_\w+\|u_lf\.u_rxsb\.", False),
    ("rar", rf"^{_P}u_rxsb\.o_\w+\|u_lf\.u_vs\.", True),
    ("ve", rf"^{_P}u_vs\.ve_(r|a)\w*\|u_lf\.u_ve\.", True),
    ("ver", rf"^{_P}u_vs\.ve_\w+\|u_lf\.u_ve\.", False),
    ("ve", rf"^{_P}u_ve\.u_[ms]\.(r|a)_\w+\|u_lf\.u_vs\.", False),
    ("ver", rf"^{_P}u_ve\.u_[ms]\.\w+\|u_lf\.u_vs\.", True),
    ("pvs", rf"^{_P}u_vs\.x_q\w+\|u_lf\.u_vp\.u_b[01]$", False),
    ("vsp", rf"^{_P}u_vs\.x_\w+\|u_lf\.u_vp\.u_b[01]$", True),
]
_CC = [(c, re.compile(rx)) for c, rx, _ in _CORE_CLASSES]


def _fallback_core_class(e):
    launch = e.get("launch", e["conn"].split("|")[0])
    capture = e.get("capture", e["conn"].split("|")[-1]).removeprefix("core:")
    if launch.startswith("u_lf."):
        launch = "core:" + launch
    if capture == "u_lf.u_vsw" and launch.startswith("core:u_lf.u_vs."):
        pin = launch.rsplit(".", 1)[-1]
        if pin in ("sw_v", "sw_d", "sw_w", "sw_lim"):
            return "sw"
        if pin in ("sw_vi", "sw_ri", "sw_fi"):
            return "swr"
    if capture == "u_lf.u_vs" and re.fullmatch(r"core:u_lf\.u_rxsf\.i_(v|x)", launch):
        return "ra"
    if re.fullmatch(r"u_lf\.u_(vs|vq|vn|ve|vsw|rxsf|rxsb)", capture):
        capture += "."
    key = f"{launch}|{capture}"
    for c, rx in _CC:
        if rx.match(key):
            return c
    return None


def _core_class_fn(tree):
    """kit_istations.core_class of this tools dir (or the tree's), else the embedded copy."""
    for d in [Path(__file__).resolve().parent] + ([Path(tree) / "tools" / "die_plan"] if tree else []):
        if not (d / "kit_istations.py").is_file():
            continue
        try:
            sys.path.insert(0, str(d))
            import kit_istations as KI  # noqa: E402
            return lambda e: KI.core_class(e)[0], "kit_istations"
        except Exception:
            continue
        finally:
            if sys.path and sys.path[0] == str(d):
                sys.path.pop(0)
    return _fallback_core_class, "embedded"


def plan_depths(t, core_class):
    """{class: deepest row}, {class: distinct counts} (leaf_cs_depth.plan_depths)."""
    rows = {}
    for e in t.get("internal_stations") or []:
        if str(e.get("conn", "")).startswith("bus:"):
            continue
        try:
            c = core_class(e)
        except Exception:
            c = None
        if c is None:
            continue
        rows.setdefault(c, []).append(len(e.get("regs_um") or []))
    return {c: max(v) for c, v in rows.items()}, {c: sorted(set(v)) for c, v in rows.items() if len(set(v)) > 1}


def _sv_val(v):
    v = v.strip()
    m = re.fullmatch(r"(\d+)?'h([0-9a-fA-F_]+)", v)
    if m:
        return int(m.group(2).replace("_", ""), 16)
    m = re.fullmatch(r"(\d+)?'d(\d+)", v)
    if m:
        return int(m.group(2))
    m = re.fullmatch(r"(\d+)?'b([01_]+)", v)
    if m:
        return int(m.group(2).replace("_", ""), 2)
    m = re.fullmatch(r"\{5\{4'd(\d+)\}\}", v)
    if m:
        return int("".join([format(int(m.group(1)), "x")] * 5), 16)
    if re.fullmatch(r"\d+", v):
        return int(v)
    raise ValueError(v)


def _params(ptxt):
    out = {}
    for m in re.finditer(r"\.(\w+)\s*\(\s*([^()]*?)\s*\)", ptxt or ""):
        try:
            out[m.group(1)] = _sv_val(m.group(2))
        except ValueError:
            pass
    return out


def slice_params(net_text):
    """{slice: (module, {param: int})} for every u_s_<slice> instance of an ot_s81sl_slice* module."""
    out = {}
    for m in INST.finditer(net_text):
        out[m.group("inst")[4:]] = (m.group("mod"), _params(m.group("p")))
    return out


def module_defaults(tree, mod, cache):
    """LF_CS_* / LF_VP_XR defaults from the slice module header under <tree>/rtl (only when the netlist omits them)."""
    if mod in cache:
        return cache[mod]
    d = {}
    root = Path(tree) / "rtl" if tree else None
    if root and root.is_dir():
        rx = re.compile(rf"\bmodule\s+{re.escape(mod)}\s*#\((.*?)\)\s*\(", re.S)
        for f in root.rglob("*.sv"):
            try:
                txt = f.read_text(errors="replace")
            except OSError:
                continue
            if mod not in txt:
                continue
            m = rx.search(re.sub(r"//[^\n]*", "", txt))
            if m:
                for mm in re.finditer(r"parameter\s*(?:\[[^\]]*\])?\s*(LF_\w+)\s*=\s*([^,)]+)", m.group(1)):
                    try:
                        d[mm.group(1)] = _sv_val(mm.group(2))
                    except ValueError:
                        pass
                break
    cache[mod] = d
    return d


def _load_asbuilt(tree, asbuilt):
    cands = []
    if asbuilt:
        cands.append(Path(asbuilt))
    if tree:
        cands += sorted(Path(tree).glob("physical/die_plan/*/plan_of_record/native_bind/asbuilt_run.json"))
    for c in cands:
        try:
            ab = json.loads(Path(c).read_text())
        except Exception:
            continue
        if ab.get("netlist"):
            return c, ab
    return None, None


def lfcs_findings(raw, tree, asbuilt=None, netlist=None, core_class=None):
    PT = raw.get("partition_types") or {}
    leaf_parts = [p for p in raw.get("partitions") or [] if LEAF_TYPE.match(str(p.get("type", "")))]
    if not leaf_parts:
        return [], None
    ab_path, ab = _load_asbuilt(tree, asbuilt)
    net_files = [Path(netlist)] if netlist else []
    if not net_files and ab:
        nl = ab.get("netlist")
        for n in (nl if isinstance(nl, list) else [nl]):
            f = Path(n) if os.path.isabs(n) else Path(tree or ".") / n
            net_files.append(f)
    net_files = [f for f in net_files if f.is_file()]
    if not net_files:
        return [f"{TAG} not checked: LF_CS (no as-built die netlist found under tree "
                f"{tree or '-'}; pass asbuilt=/netlist=)"], None
    sp = {}
    for f in net_files:
        sp.update(slice_params(f.read_text(errors="replace")))
    if not sp:
        return [f"{TAG} not checked: LF_CS (netlist {net_files[0]} has no ot_s81sl_slice* u_s_* instance)"], None
    gdefs = set(str(x).split("=")[0] for x in (ab or {}).get("defines") or [])
    core_class = core_class or _core_class_fn(tree)[0]
    dcache, over, under, nodata, rows = {}, [], [], [], 0
    per_type = {}
    for p in leaf_parts:
        m = PART.match(str(p.get("name", "")))
        tn = p["type"]
        t = PT.get(tn) or {}
        if not m or not t.get("hard_cores"):
            continue
        s, k = m.group(1), int(m.group(2))
        if s not in sp:
            nodata.append(f"{p['name']} ({tn}): slice u_s_{s} not in the netlist")
            continue
        mod, prm = sp[s]
        dft = None

        def nib(name):
            nonlocal dft
            key = "LF_CS_" + name if name != "XR" else "LF_VP_XR"
            if key in prm:
                v = prm[key]
            else:
                if dft is None:
                    dft = module_defaults(tree, mod, dcache)
                if key not in dft:
                    return None
                v = dft[key]
            return (v >> k) & 1 if name == "XR" else (v >> (4 * k)) & 0xF
        xr = nib("XR")
        if xr is None:
            xr = 1 if XR_DEFINE in gdefs else 0
        tdefs = set(str(x).split("=")[0] for x in t.get("verilog_defines") or [])
        sr = 1 if (SR_DEFINE in tdefs or SR_DEFINE in gdefs) else 0
        want, dis = plan_depths(t, core_class)
        bound = {}
        for x in CL:
            c = x[:-2].lower()
            v = nib(x)
            if v is None:
                continue
            bound[c] = v + (xr if c == "hi" else 0) + (sr if c == "ho" else 0)
        key = tn
        if key in per_type:          # one type, several partitions: the bind checks the type once (first bound file)
            continue
        per_type[key] = 1
        for c in sorted(set(want) | {c for c, v in bound.items() if v}):
            if c == "cs":
                if want.get("cs"):
                    over.append((tn, c, want["cs"], 0, p["name"], "vn_a->vn_b c_s rows have no RTL stage"))
                continue
            if c not in bound:
                continue
            rows += 1
            pl, b = want.get(c, 0), bound[c]
            if pl > b:
                over.append((tn, c, pl, b, p["name"], f"u_s_{s} LF_CS_{c.upper()}_D nibble {k}"))
            elif pl < b:
                under.append((tn, c, pl, b, p["name"], f"u_s_{s} LF_CS_{c.upper()}_D nibble {k}"))
    out = []
    for tn, c, pl, b, pn, src in over:
        out.append(f"{TAG} {tn} {c}: plan {pl} stage(s) (deepest row) > RTL {b} ({src}, {pn}); strict bind LF_CS_DEPTH "
                   f"will fail -> restage the netlist from this plan (stage_lfcs_netlist.py) or drop the extra station(s)")
    for tn, c, pl, b, pn, src in under:
        out.append(f"{TAG} {tn} {c}: plan {pl} stage(s) < RTL {b} ({src}, {pn}); unplanned RTL cycle, strict bind "
                   f"LF_CS_DEPTH will fail -> restage the netlist from this plan or price the stage in the plan")
    for x in nodata[:3]:
        out.append(f"{TAG} {x}")
    summ = dict(rows=rows, over=len(over), under=len(under), nodata=len(nodata), netlist=str(net_files[0]),
                asbuilt=str(ab_path) if ab_path else None)
    return out, summ


def lane_findings(raw):
    lanes = raw.get("lanes")
    lat = ((raw.get("latency") or {}).get("lanes")) or {}
    if not isinstance(lanes, list) or not lat:
        return [], 0, 0
    out, bad, seen = [], 0, 0
    for ln in lanes:
        if not isinstance(ln, dict) or "id" not in ln:
            continue
        L = lat.get(ln["id"])
        if not isinstance(L, dict):
            continue
        seen += 1
        fc = ln.get("fixed_cycles")
        msg = []
        if fc is not None and L.get("fixed") is not None and fc != L["fixed"]:
            msg.append(f"lanes.fixed_cycles {fc} != latency.fixed {L['fixed']}")
        try:
            need = (int(L["fixed"]) + int(L.get("boundary", 0)) + int(L.get("stations", 0))
                    + int(L.get("clock_landing", 0)) + int(L.get("pad", 0)))
            if L.get("cycles") is not None and int(L["cycles"]) != need:
                msg.append(f"latency.cycles {L['cycles']} != fixed+boundary+stations+clock_landing+pad {need}")
            if L.get("natural") is not None and int(L["natural"]) != int(L["cycles"]) - int(L.get("pad", 0)):
                msg.append(f"latency.natural {L['natural']} != cycles-pad {int(L['cycles']) - int(L.get('pad', 0))}")
        except (KeyError, TypeError, ValueError):
            pass
        if msg:
            bad += 1
            out.append(f"{TAG} lane {ln['id']}: {'; '.join(msg)} -> re-price the lane (latency table) in the same event")
    return out, bad, seen


def findings(raw, plan_path, tree=None, **kw):
    try:
        t0 = time.time()
        lf, summ = lfcs_findings(raw, tree, kw.get("asbuilt"), kw.get("netlist"))
        la, nbad, nseen = lane_findings(raw)
        out = lf[:CAP] + la[:max(5, CAP - len(lf[:CAP]))]
        if summ is not None or nseen:
            s = summ or {}
            lfs = (f"LF_CS {s.get('over', 0)} plan>RTL + {s.get('under', 0)} plan<RTL over {s.get('rows', 0)} "
                   f"(type, class) rows (netlist {s.get('netlist', '-')})") if summ else "LF_CS n/a (no S81 leaf types)"
            out.append(f"{TAG} summary: {lfs}; lanes {nbad}/{nseen} inconsistent fixed/cycles; {time.time() - t0:.1f} s")
        return out
    except Exception as ex:  # never raise
        return [f"{TAG} not checked: {type(ex).__name__}: {ex}"]


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--tree")
    ap.add_argument("--asbuilt")
    ap.add_argument("--netlist")
    a = ap.parse_args(argv)
    t0 = time.time()
    raw = json.loads(Path(a.plan).read_text())
    t1 = time.time()
    for x in findings(raw, a.plan, a.tree, asbuilt=a.asbuilt, netlist=a.netlist):
        print(x)
    print(f"# load {t1 - t0:.1f} s, check {time.time() - t1:.1f} s")


if __name__ == "__main__":
    main()
