#!/usr/bin/env python3
"""bind_reset_core_class: does the wavefront reset contract (bind_reset.json types[].core_resets) match the bound RTL?

KV-RSTREACH 11-24 (FABLE-RC-KV 01:23 second finding): reset_tree.wf_plan lists every hard-core reset pin as a
wavefront consumer on its own tap rst_n_t<tap>, from the plan alone.  The binder can instead land that pin on a reset
spine (asbuilt.reset_spines: the as-built netlist ties it to host.die_rst_n), e.g. the kv3_pv* join cores
(ot_qwen_tp8_pv_join_t .rst_n = rs_ri_pv_u_g*_j_rst_n_r<k>, a spine tail copy).  The tap is then a dead keep wire and
every tool that reads bind_reset.json (release order, reach, reset-hold tables) works on a wrong map for that core.

REPORT ONLY: classify each listed core reset by what actually drives the pin in the emitted type RTL; bind_reset.json
itself is not changed.  -> OUT/bind_reset_core_class.json  {types: {tn: [{inst, pin, tap, rtl_net, rtl_class,
agrees}]}, mismatches: n, by_class: {...}}.  rtl_class: wavefront (the listed tap rst_n_t<tap>, or a relay copy of it),
spine (a reset-spine port ri_* / its synchroniser or tail copy rs_ri_*), other (anything else), missing (instance or
pin not found in the type RTL), ambiguous (matched leaves disagree on the pin driver).
"""
import json
import re
import sys
from pathlib import Path


def _leaf(c):
    """the instance name in the type RTL: last segment of physical_inst (u_bound.u_pv_u_g0_j -> u_pv_u_g0_j)."""
    p = c.get("physical_inst") or c.get("inst", "")
    return re.split(r"[./]", p)[-1]


def _resolve(text, c):
    """(instance, net) for the core reset pin: physical_inst's leaf, else the nearest ancestor instance present in the
    flat type RTL (a pin inside a bound hard core, e.g. u_bound.u_pvfin.g_sl[0].u_sl -> u_pvfin.rst_n)."""
    p = c.get("physical_inst") or c.get("inst", "")
    segs = [re.sub(r"\[[^\]]*\]$", "", x) for x in re.split(r"[./]", p) if x and x != "u_bound"]
    for inst in reversed(segs):
        net = _pin_net(text, inst, c.get("pin", "rst_n"))
        if net is not None:
            return inst, net
    return _leaf(c), None


def _pin_net(text, inst, pin):
    """net on .<pin>( ... ) of instance <inst> in a flat Verilog module text, or None."""
    m = re.search(r"(?m)^\s*\w+\s*(?:#\s*\((?:[^()]|\([^()]*\))*\)\s*)?" + re.escape(inst) + r"\s*\(", text)
    if not m:
        return None
    depth, i, n = 1, m.end(), len(text)
    while i < n and depth:
        depth += {"(": 1, ")": -1}.get(text[i], 0)
        i += 1
    body = text[m.end():i - 1]
    pm = re.search(r"\.\s*" + re.escape(pin) + r"\s*\(\s*([^()]*?)\s*\)", body)
    return pm.group(1) if pm else None


def classify(net, tap):
    if net is None:
        return "missing"
    base = re.sub(r"\[[^\]]*\]$", "", net.strip())
    if base == f"rst_n_t{tap}":
        return "wavefront"
    if re.fullmatch(r"(rs_)?ri_\w+", base):
        return "spine"
    return "other"


def check(W, type_text, core_leaves=None):
    """Classify emitted reset drivers, using bind_core_resets leaf identities when available."""
    core_leaves = core_leaves or {}
    types, by, bad = {}, {}, 0
    for tn, T in sorted(W.get("types", {}).items()):
        rows = []
        txt = type_text.get(tn)
        leaves = {}
        for mapped in core_leaves.get(tn, ()):
            key = mapped["inst"], mapped["pin"]
            leaves.setdefault(key, set()).add(mapped["leaf"])
        for c in T.get("core_resets", []):
            pin = c.get("pin", "rst_n")
            mapped = sorted(leaves.get((c.get("inst"), pin), ()))
            ambiguous = False
            if txt is None:
                ri, net = _leaf(c), None
            elif mapped:
                ri = mapped[0]
                nets = {_pin_net(txt, leaf, pin) for leaf in mapped}
                ambiguous = len(nets) > 1
                net = None if ambiguous else next(iter(nets))
            else:
                ri, net = _resolve(txt, c)
            cl = "ambiguous" if ambiguous else classify(net, c.get("tap"))
            ok = cl == "wavefront"
            bad += not ok
            by[cl] = by.get(cl, 0) + 1
            rows.append(dict(inst=c.get("inst"), pin=c.get("pin"), tap=c.get("tap"), rtl_inst=ri,
                             rtl_net=net, rtl_class=cl, agrees=ok))
        if rows:
            types[tn] = rows
    return dict(mode="report-only", mismatches=bad, by_class=dict(sorted(by.items())), types=types,
                note="bind_reset.json core_resets vs the pin driver in the emitted type RTL; bind_reset.json unchanged")


def _stages(text, net):
    """total reset stages of a spine landing from its driver line comment ('N stage(s) total'), else None."""
    if not text or not net:
        return None
    base = re.sub(r"\[[^\]]*\]$", "", net.strip())
    m = re.search(r"(?m)^.*\.q\(\s*" + re.escape(base) + r"(?:\[[^\]]*\])?\s*\)\s*\)\s*;.*?(\d+) stage\(s\) total", text)
    if m:
        return int(m.group(1))
    # the pin takes the spine synchroniser output itself (no tail copy): its S parameter is the stage count
    m = re.search(r"(?m)^\s*ot_dp_rsync\s*#\(([^;]*?)\)\s*\w+\s*\([^;]*\.q\(\s*" + re.escape(base) + r"\s*\)", text)
    sm = re.search(r"\.S\((\d+)\)", m.group(1)) if m else None
    return int(sm.group(1)) if sm else None


def apply_spine(W, R, type_text):
    """KV-RSTREACH 11-24 (COORD ruling): publish what the RTL does.  Every core reset that R classifies 'spine' is
    re-published in W (bind_reset.json) as a spine-reset consumer: types[tn].core_resets[i] gets reset_class 'spine',
    rtl_net, tap_used False, spine_stages; every partition of that type drops its wavefront core_release value for the
    target (that number was never true) and lists it under spine_release (released by the reset spine, i.e. die
    rst_n spine deassert + spine_stages own clocks; NOT on the wavefront).  Wavefront-driven cores are unchanged.
    Returns the number of targets moved.  W is changed in place."""
    moved = 0
    by_type = {}
    for tn, rows in R.get("types", {}).items():
        for r in rows:
            if r["rtl_class"] == "spine":
                by_type.setdefault(tn, {})[(r["inst"], r["pin"])] = r
    for tn, sp in by_type.items():
        T = W.get("types", {}).get(tn)
        if not T:
            continue
        for c in T.get("core_resets", []):
            r = sp.get((c.get("inst"), c.get("pin")))
            if r is None:
                continue
            c.update(reset_class="spine", rtl_net=r["rtl_net"], tap_used=False,
                     spine_stages=_stages(type_text.get(tn), r["rtl_net"]))
            moved += 1
        for part in W.get("parts", {}).values():
            if part.get("type") != tn:
                continue
            for (inst, pin), r in sp.items():
                tgt = f"{inst}.{pin}"
                cr = part.get("core_release", {})
                if tgt in cr:
                    cr.pop(tgt)
                c = next((x for x in T.get("core_resets", []) if (x.get("inst"), x.get("pin")) == (inst, pin)), {})
                part.setdefault("spine_release", {})[tgt] = dict(
                    source="reset spine (asbuilt.reset_spines, die rst_n)", rtl_net=r["rtl_net"],
                    spine_stages=c.get("spine_stages"), wavefront_release=None)
    if moved:
        W["core_reset_classes"] = dict(spine=moved, by_class=R.get("by_class", {}),
                                       note="core resets driven by a reset spine in the bound RTL are published as "
                                            "spine consumers (spine_release), not wavefront core_release")
    return moved


def main(argv):
    """bind_reset_core_class.py BIND_OUT [TYPE_MODULE_MAP.json]: reads BIND_OUT/bind_reset.json + BIND_OUT/rtl/*.sv."""
    out = Path(argv[1])
    W = json.loads((out / "bind_reset.json").read_text())
    texts = {}
    for f in (out / "rtl").glob("*.sv"):
        t = f.read_text(errors="replace")
        for mm in re.finditer(r"(?m)^module\s+(\w+)", t):
            texts[mm.group(1)] = t
    tmap = {}
    report = out / "bind_report.json"
    if report.is_file():
        tmap = {tn: row["module"] for tn, row in json.loads(report.read_text()).get("types", {}).items()
                if row.get("module")}
    if len(argv) > 2:
        tmap.update(json.loads(Path(argv[2]).read_text()))
    type_text = {tn: texts.get(tmap.get(tn, tn)) or texts.get(tn + "_part") for tn in W.get("types", {})}
    type_text = {k: v for k, v in type_text.items() if v is not None}
    mapped = out / "bind_core_resets.json"
    core_leaves = json.loads(mapped.read_text()).get("types", {}) if mapped.is_file() else {}
    R = check(W, type_text, core_leaves)
    (out / "bind_reset_core_class.json").write_text(json.dumps(R, indent=1) + "\n")
    print(f"BIND-RESET-CORE-CLASS report-only mismatches={R['mismatches']} by_class={R['by_class']}")
    for tn, rows in R["types"].items():
        for r in rows:
            if not r["agrees"]:
                print(f"  {tn} {r['inst']}.{r['pin']} contract tap {r['tap']} rtl {r['rtl_class']} {r['rtl_net']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
