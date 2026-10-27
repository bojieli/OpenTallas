"""Die IO planning (PLAN-TOOL5, COORD DIE-PLAN VISUAL REVIEW 10-23 item (a)).

Every die's external interfaces (SerDes, UCIe, HBM PHY) and its host link must be planned as die IO: a `die.io`
window over the PHY footprint, on the die shoreline, with enough bump sites for the off-die signals. Until 10-23 the
plans had none (die_io windows 0 / ports 0 on all four dies), so the die boundary was unchecked.

The PHY macros are licensed-IP abstracts whose off-die side is modelled (owner 10-14: only PHY / off-chip signals are
modelled). Their off-die signals therefore exist only as bump counts, not as RTL ports. A window says so with
`iface` + `signals`, and lists `ports` only when the plan has real @die ports (S81-P5 form, check_die_io).

    die.io[] = {name, kind: phy_macro, iface: serdes|ucie|hbm_phy|host, part, rect_um, sites, pitch_um, signals,
                host: true (this window also carries the die's host link), basis, note}

Catalog (CLASSES): content module regex -> interface class, off-die signals per instance, bump pitch.
  serdes   4 per lane (TX+/-, RX+/-) + 2 refclk. Lanes from the module name (_x12 / _x6); ot_pdie_serdes = 6
           (half of the 112G strip, 512-b flit per 833-ps cycle = 614 Gb/s -> 6 x 112G PAM4). C4 pitch 150 um.
  ucie     one x64 advanced module: 2 x (64 data + valid + track + 2 clock) + 2 x 4 redundant = 144. Pitch 45 um
           (UCIe-A 25-55 um).
  hbm_phy  ~1,900 per HBM3/3E stack (16 ch x ~117: 64 DQ, ECC / DBI / SEV, strobes, row/col CA, CK, plus globals);
           a 4-PC slice (qkd_hbm3e_phy_pc) is 1/8 stack, the v41x _s4 view 1/4. Micro-bump pitch 55 um.
  All counts are ASSUMED interface-class values (the PHY views carry no bump map); a plan may override `signals`.

G0C (`check.py --completeness`, check name 'die_io_plan'):
  - every placed instance of an IO-class content has a window of its class over it (inside its partition);
  - each window is on the shoreline: its rect within budgets.io_edge_max_um (200) of a die edge;
  - signals <= sites;
  - the die names its host link: one window with iface 'host' or host: true;
  - die.io empty -> one die-level ERROR.

Host link: no die has a host PHY macro; the host rides a die link PHY (serdes / ucie). `plan` marks the link PHY
nearest (port-graph hops) to the host logic (host_rt / seq_host / host_cp / sys_face) host: true -- CONFIRM it.

The plan's die.io wins; without it check.py reads PLANDIR/die_io.json (written by `plan --out`), so the windows
survive the die generators' regeneration of die_plan.json.

    python3 tools/die_plan/die_io.py plan PLAN.json [--inplace] [--out PLANDIR/die_io.json]   # propose from the catalog
"""
import argparse
import json
import math
import re
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402
from schema import DIE_PART  # noqa: E402

HBM_STACK_SIGNALS = 1900
UCIE_X64_SIGNALS = 2 * (64 + 1 + 1 + 2) + 2 * 4
# (class, module regex, signals(module) -> int, bump pitch um, basis)
CLASSES = [
    ("hbm_phy", re.compile(r"hbm3e?_phy", re.I),
     lambda m: HBM_STACK_SIGNALS // 8 if re.search(r"_pc$", m) else
     HBM_STACK_SIGNALS // 4 if re.search(r"_s4$", m) else HBM_STACK_SIGNALS, 55.0,
     "HBM3/3E stack ~1,900 signals (16 ch x ~117 + globals; ASSUMED class value), 55-um micro-bumps"),
    ("ucie", re.compile(r"ucie_x\d+_phy|pdie_ucie", re.I), lambda m: UCIE_X64_SIGNALS, 45.0,
     "UCIe-A x64 module: 2 x (64 data + valid + track + 2 clk) + 2 x 4 redundant = 144, 45-um bumps (ASSUMED)"),
    ("serdes", re.compile(r"serdes.*phy|pdie_serdes", re.I),
     lambda m: 4 * int((re.search(r"_x(\d+)", m) or [None, 6])[1]) + 2, 150.0,
     "112G PAM4 SerDes: 4 per lane (TX/RX pairs) + 2 refclk; lanes from _xN, ot_pdie_serdes 6 (614 Gb/s); C4 150 um"),
]
HOST_RE = re.compile(r"host_rt|seq_host|host_cp|sys_face|host_static_ingress", re.I)
HOST_CARRIERS = ("serdes", "ucie")      # the host link rides a die link PHY (no host PHY macro on any die)
EDGE_MAX_UM = 200.0
EPS = 1e-6


def classify(module):
    for cls, rx, sig, pitch, basis in CLASSES:
        if rx.search(module or ""):
            return cls, sig(module), pitch, basis
    return None


def io_instances(P):
    """[(part, content inst, class, signals, pitch, basis, die rect of the content footprint)] for every placed
    instance of an IO-class content (footprint = contents[].origin/outline, else the whole partition)."""
    out = []
    for pn in P.parts:
        t = P.ptype(pn)
        cs = t.get("contents") or [dict(inst=pn, module=t.get("module", ""))]
        for c in cs:
            k = classify(c.get("module", ""))
            if not k:
                continue
            if "origin_um" in c and "outline_um" in c:
                (x0, y0), (w, h) = c["origin_um"], c["outline_um"]
                a, b = P.to_die(pn, (x0, y0)), P.to_die(pn, (x0 + w, y0 + h))
                r = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
                pr = P.rect(pn)            # clip to the partition (a macro outline may overhang its slot)
                r = (max(r[0], pr[0]), max(r[1], pr[1]), min(r[2], pr[2]), min(r[3], pr[3]))
            else:
                r = P.rect(pn)
            out.append((pn, c.get("inst", pn), k[0], k[1], k[2], k[3], r))
    return out


def edge_dist(P, r):
    return min(r[0], r[1], P.W - r[2], P.H - r[3])


def host_parts(P):
    hp = []
    for pn in P.parts:
        t = P.ptype(pn)
        if any(HOST_RE.search(c.get("module", "") + " " + c.get("inst", "")) for c in t.get("contents", [])):
            hp.append(pn)
    return hp


def port_graph(P):
    g = {}
    for pr in P.ports.values():
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if DIE_PART in (a, b):
            continue
        g.setdefault(a, set()).add(b)
        g.setdefault(b, set()).add(a)
    return g


def nearest_io(P, starts, io_parts):
    """BFS over the port graph from the host-logic partitions to the nearest IO partition: (part, hops)."""
    g = port_graph(P)
    seen = {s: 0 for s in starts}
    q = deque(starts)
    while q:
        u = q.popleft()
        if u in io_parts:
            return u, seen[u]
        for v in sorted(g.get(u, ())):
            if v not in seen:
                seen[v] = seen[u] + 1
                q.append(v)
    return None, None


def plan(P):
    """proposed die.io list from the catalog (one window per IO-class content instance)."""
    io = []
    names = set()
    inst = io_instances(P)
    for pn, ci, cls, sig, pitch, basis, r in inst:
        nm = re.sub(r"[^A-Za-z0-9_]", "_", f"io_{pn}_{ci}")
        while nm in names:
            nm += "_"
        names.add(nm)
        w, h = r[2] - r[0], r[3] - r[1]
        sites = max(1, int(math.floor(w / pitch)) * int(math.floor(h / pitch)))
        io.append(dict(name=nm, kind="phy_macro", iface=cls, part=pn, rect_um=[round(v, 4) for v in r],
                       sites=sites, pitch_um=pitch, signals=sig,
                       basis=basis + f"; shoreline {edge_dist(P, r):.0f} um", note=f"die_io.py plan: {ci}"))
    hp = host_parts(P)
    if io and hp:
        via, hops = nearest_io(P, hp, {w["part"] for w in io if w["iface"] in HOST_CARRIERS})
        if via:
            w = next(x for x in io if x["part"] == via and x["iface"] in HOST_CARRIERS)
            w["host"] = True
            w["note"] += f"; host link (BFS {hops} port hop(s) from {', '.join(sorted(hp)[:3])}): CONFIRM"
    return io


def check(P, R, edge_max=None):
    """G0C die IO plan rules (see the module docstring). Returns the summary dict."""
    io = P.die.get("io") or []
    edge_max = float(P.budgets.get("io_edge_max_um", EDGE_MAX_UM) if edge_max is None else edge_max)
    inst = io_instances(P)
    summ = dict(windows=len(io), iface_windows=sum(1 for w in io if w.get("iface")), io_instances=len(inst),
                by_class={}, host=None, uncovered=0, off_shore=0, over_sites=0)
    for _, _, cls, sig, *_ in inst:
        d = summ["by_class"].setdefault(cls, dict(instances=0, signals=0))
        d["instances"] += 1
        d["signals"] += sig
    if not io:
        cls_txt = ", ".join(f"{k} {v['instances']}" for k, v in sorted(summ["by_class"].items()))
        R.err("die_io_plan", f"no die IO planned (die.io empty): {len(inst)} IO-class instances "
              f"({cls_txt or 'none'}) and the "
              "host link have no bump / pad window (generate: python3 tools/die_plan/die_io.py plan PLAN --inplace)")
        summ["uncovered"] = len(inst)
        return summ
    for pn, ci, cls, sig, pitch, basis, r in inst:
        ok = [w for w in io if w.get("iface") == cls and w.get("part") == pn]
        if not ok:
            summ["uncovered"] += 1
            R.err("die_io_plan", f"{cls} {pn}.{ci}: no die.io window (iface {cls}) over it", type=P.parts[pn]["type"],
                  part=pn)
    for w in io:
        r = w["rect_um"]
        d = edge_dist(P, r)
        tn = P.parts[w["part"]]["type"] if w.get("part") in P.parts else None
        if w.get("iface") in ("serdes", "ucie", "hbm_phy") and d > edge_max + EPS:
            summ["off_shore"] += 1
            R.err("die_io_plan", f"io window {w['name']} ({w['iface']}): {d:.0f} um from the die edge > io_edge_max_um "
                  f"{edge_max:g} (the bump field / PHY must sit on the shoreline)", type=tn, part=w.get("part"))
        sig = w.get("signals")
        if sig is not None and sig > w["sites"]:
            summ["over_sites"] += 1
            R.err("die_io_plan", f"io window {w['name']}: {sig} off-die signals > {w['sites']} sites", type=tn,
                  part=w.get("part"))
    hw = [w["name"] for w in io if w.get("iface") == "host" or w.get("host")]
    summ["host"] = hw
    if not hw:
        R.err("die_io_plan", "no host link window (a die.io entry with iface 'host' or host: true)")
    return summ


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["plan"])
    ap.add_argument("plan_json")
    ap.add_argument("--inplace", action="store_true", help="write die.io into the plan (keeps existing port windows)")
    ap.add_argument("--out", help="write the proposed die.io list to this JSON file")
    a = ap.parse_args(argv)
    raw = S.load(a.plan_json)
    P = S.Plan(raw)
    io = plan(P)
    keep = [w for w in (raw["die"].get("io") or []) if not w.get("iface")]
    new = keep + io
    if a.out:
        Path(a.out).write_text(json.dumps(new, indent=1) + "\n")
    if a.inplace:
        raw["die"]["io"] = new
        Path(a.plan_json).write_text(json.dumps(raw, indent=1) + "\n")
    for w in io:
        print(f"{w['name']:40s} {w['iface']:8s} sites {w['sites']:6d} signals {w['signals']:5d} "
              f"{'HOST ' if w.get('host') else ''}{w['basis'].split('; ')[-1]}")
    print(f"{len(io)} io windows ({len(keep)} port windows kept)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
