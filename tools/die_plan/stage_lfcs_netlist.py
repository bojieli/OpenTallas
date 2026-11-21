#!/usr/bin/env python3
"""LF-CS stage (S81-LEAF-FLOOR-2 11-12): the plan's leaf station depths onto the die netlist's slice instances.

    stage_lfcs_netlist.py PLAN.json DIE_NETLIST.v OUT_NETLIST.v [--report OUT.json]

For every leaf partition s_<slice>_L<k> (= u_s_<slice>...u_lf<k>) of an ot_s81sl_leaf__* or
ot_s81sl_kv_leaf__* type, the depth of class c is the deepest plan internal_stations row of that class
(leaf_cs_depth.plan_depths: the strict bind gate's own definition).  hi / ho trees: GS = D (every hi / ho stage is a
shared group stage, as the bound form today; kv leaves GS 0, per lane, as DIE-S81-70), H_G 4.  The die instance u_s_<slice> gets #(.LF_CS_<C>(20'h...)) for
all 17 parameters; a nibble with no plan leaf keeps the slice module's default (read from its RTL header).
cs rows have no RTL realisation (re-planned in the floorplan stage) and are reported, never staged.

S81-STRIP form B (11-17): with --vp-xr TYPE:1 the plan's HI depth of that leaf is its EFFECTIVE depth and includes the one
per-lane HI stage XR adds in ot_s81sl_vp (CS_HI_E = CS_HI_D + XR); the source gets HI_D = plan HI - 1 (GS follows), so a
plan HI 3 stages source 2 / GS 2 and elaborates to 3, not 4.  The die instance's LF_VP_XR mask must agree with the
contracts bit by bit (a mask bit with no contract refuses).

S81-LEAF-REGRID (11-21): the rule is the same on the kv slice.  Leaves 1-4 of ot_s81sl_slice_w3 (types ot_s81sl_kv_leaf__*)
are ot_s81sl_leaf instances whose u_vp reads LF_VP_XR[k] like any other leaf, so a kv leaf with hard cores takes a
--vp-xr contract and the source gets HI_D = plan HI - 1 (the netlist of record: u_s_3N mask 5'b11111, plan hi 2, HI_D
20'h11110; GS stays 0, per lane).  Only a leaf with no hard cores (the KV bank leaf, kv_leaf t2) has nothing to stage:
its mask bit is not checked and a contract on it refuses.  Restaging the unchanged plan reproduces the record byte for byte.

VP_SR (S81 J7 vp_sr, 11-21): with --vp-sr TYPE:1 the plan's HO depth of that leaf is its EFFECTIVE depth and includes the
one per-lane output station SR adds in ot_s81sl_vp (u_cst_ho D = CS_HO_D - CS_HO_GS + SRO); the source gets HO_D = plan
HO - 1.  The J7 plan prices ho + 1 on every staged leaf against the same netlist of record; SR has no mask on the die
instance (it is a define of the bound type), so the contract is explicit and the strict bind's LF_CS_DEPTH gate judges it.

S81-LEAF-SWR (11-20): --update CLASS (repeatable, e.g. SWR_D) re-prices only those classes on an already staged netlist
(the D8i bind dropped 5 SWR rows: plan 1-2 stages, staged LF_CS_SWR_D nibble 0); XR / group classes need a full stage."""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import leaf_cs_depth as LCD  # noqa: E402

CL = ["HI_D", "HI_GS", "HO_D", "HO_GS", "H_G", "VNI_D", "VNO_D", "Y_D", "U_D", "SW_D", "SWR_D", "RA_D", "RAR_D",
      "VE_D", "VER_D", "PVS_D", "VSP_D"]
CLS = {"HI_D": "hi", "HO_D": "ho", "VNI_D": "vni", "VNO_D": "vno", "Y_D": "y", "U_D": "u", "SW_D": "sw", "SWR_D": "swr",
       "RA_D": "ra", "RAR_D": "rar", "VE_D": "ve", "VER_D": "ver", "PVS_D": "pvs", "VSP_D": "vsp"}
PART = re.compile(r"^s_(\w+?)_L([0-4])$")
INST = re.compile(r"^(?P<lead>\s*(?P<mod>ot_s81sl_slice\w*)\s+)(?:#\((?P<p>(?:[^()]|\([^()]*\))*)\)\s*)?(?P<inst>u_s_\w+)\s*\(", re.M)


def _sv_val(v):
    v = v.strip()
    m = re.fullmatch(r"(\d+)?'h([0-9a-fA-F_]+)", v)
    if m:
        return int(m.group(2).replace("_", ""), 16)
    m = re.fullmatch(r"(\d+)?'d(\d+)", v)
    if m:
        return int(m.group(2))
    m = re.fullmatch(r"\{5\{4'd(\d+)\}\}", v)
    if m:
        return int("".join([format(int(m.group(1)), "x")] * 5), 16)
    raise ValueError(f"default {v!r}")


def module_defaults(rtl_root, mod):
    for f in Path(rtl_root).rglob("*.sv"):
        t = re.sub(r"//[^\n]*", "", f.read_text(errors="replace"))
        m = re.search(rf"\bmodule\s+{mod}\s*#\((.*?)\)\s*\(", t, re.S)
        if m:
            d = {}
            for x in CL:
                mm = re.search(rf"parameter\s*\[19:0\]\s*LF_CS_{x}\s*=\s*([^,)]+)", m.group(1))
                if not mm:
                    raise SystemExit(f"{mod} ({f}): no LF_CS_{x} parameter (forwarding missing)")
                d[x] = _sv_val(mm.group(1))
            return d
    raise SystemExit(f"{mod}: no #(...) module header under {rtl_root}")


def leaf_depths(plan, tree_overrides=None, vp_xr=None, vp_sr=None):
    """{(slice, k): {param: depth}}, report rows."""
    tree_overrides = tree_overrides or {}
    vp_xr = vp_xr or {}
    vp_sr = vp_sr or {}
    PT = plan["partition_types"]
    known = {p["type"] for p in plan["partitions"] if LCD.LEAF_TYPE.match(p["type"])}
    unknown = (set(tree_overrides) | set(vp_xr) | set(vp_sr)) - known
    if unknown:
        raise SystemExit(f"unknown leaf tree override types: {sorted(unknown)}")
    for typ, value in vp_xr.items():
        if isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1):
            raise SystemExit(f"{typ}: VP_XR contract must be integer 0 or 1")
    for typ, value in vp_sr.items():
        if isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1):
            raise SystemExit(f"{typ}: VP_SR contract must be integer 0 or 1")
    out, rep = {}, []
    for p in plan["partitions"]:
        if not LCD.LEAF_TYPE.match(p["type"]):
            continue
        m = PART.match(p["name"])
        if not m:
            raise SystemExit(f"leaf partition {p['name']}: not s_<slice>_L<k>")
        k = int(m.group(2))
        t = PT[p["type"]]
        if not t.get("hard_cores"):
            if vp_xr.get(p["type"]) or vp_sr.get(p["type"]):
                raise SystemExit(f"{p['name']}: VP_XR / VP_SR contract on a leaf with no hard cores (no VP to stage)")
            rep.append(dict(part=p["name"], type=p["type"], skipped="no hard cores (no leaf chains)"))
            continue
        missing = LCD.unmapped_core_rows(t)
        if missing:
            raise SystemExit(f"{p['name']}: {len(missing)} planned core station rows have no RTL class; "
                             "no LF_CS source staged")
        want, dis = LCD.plan_depths(t)
        d = {x: want.get(c, 0) for x, c in CLS.items()}
        xr = vp_xr.get(p["type"], 0)
        plan_hi = d["HI_D"]
        if xr:
            if d["HI_D"] < 1:
                raise SystemExit(f"{p['name']}: effective HI depth must include the XR stage")
            # The plan/native count includes XR's one per-lane HI stage.
            # LF_CS_HI_D prices only the source's pre-XR stages.
            d["HI_D"] -= xr
        sr = vp_sr.get(p["type"], 0)
        plan_ho = d["HO_D"]
        if sr:
            if d["HO_D"] < 1:
                raise SystemExit(f"{p['name']}: effective HO depth must include the SR output station")
            # ot_s81sl_vp SR 1: per-lane ho stations = CS_HO_D - CS_HO_GS + 1 (SRO); the plan / bound count includes it.
            d["HO_D"] -= sr
        kv = "kv_leaf" in p["type"]          # DIE-S81-70 kv leaves: per-lane hi / ho stages (GS 0), as bound today
        d["HI_GS"], d["HO_GS"], d["H_G"] = (0, 0, 4) if kv else (d["HI_D"], d["HO_D"], 4)
        for param, value in tree_overrides.get(p["type"], {}).items():
            if param not in {"HI_GS", "HO_GS"} or isinstance(value, bool) or not isinstance(value, int):
                raise SystemExit(f"{p['name']}: invalid shared-stage override {param}={value}")
            if not 0 <= value <= d[param.replace("GS", "D")]:
                raise SystemExit(f"{p['name']}: shared stages must lie between zero and class depth: {param}={value}")
            d[param] = value
        if any(v > 15 for v in d.values()):
            raise SystemExit(f"{p['name']}: depth > 15 does not fit a nibble: {d}")
        out[(m.group(1), k)] = d
        rep.append(dict(part=p["name"], type=p["type"], slice="u_s_" + m.group(1), k=k, depths=d, disagree=dis,
                        cs_rows=want.get("cs", 0), vp_xr=xr, plan_hi_d=plan_hi, vp_sr=sr, plan_ho_d=plan_ho))
    return out, rep


def stage(plan, net_text, rtl_root, tree_overrides=None, vp_xr=None, vp_sr=None):
    vp_xr = vp_xr or {}
    depths, rep = leaf_depths(plan, tree_overrides, vp_xr, vp_sr)
    selected = {(PART.match(p["name"]).group(1), int(PART.match(p["name"]).group(2))): p["type"]
                for p in plan["partitions"] if LCD.LEAF_TYPE.match(p["type"]) and PART.match(p["name"])}
    slices = sorted({s for s, _ in depths})
    done, defaults = set(), {}

    def sub(m):
        s = m.group("inst")[4:]
        if s not in slices:
            return m.group(0)
        mod = m.group("mod")
        # setdefault evaluates its fallback eagerly: re-reading every RTL file
        # per slice made a 16-slice production staging take several minutes.
        if mod not in defaults:
            defaults[mod] = module_defaults(rtl_root, mod)
        dft = defaults[mod]
        vals = []
        for x in CL:
            v = 0
            for k in range(5):
                nib = depths[(s, k)][x] if (s, k) in depths else (dft[x] >> (4 * k)) & 0xF
                v |= nib << (4 * k)
            vals.append(f".LF_CS_{x}(20'h{v:05x})")
        old = m.group("p")
        # The die netlist's LF_VP_XR mask and the explicit contracts must agree leaf by leaf, also when no contract
        # is given: an XR leaf staged on the old path gets source HI_D = plan HI (effective HI + 1).
        mask = re.search(r"\.LF_VP_XR\(\s*5'b([01]{5})\s*\)", old or "")
        if "LF_VP_XR" in (old or "") and not mask:
            raise SystemExit(f"u_s_{s}: LF_VP_XR must be a literal five-bit mask (5'bxxxxx) to stage this slice")
        bits = int(mask.group(1), 2) if mask else 0
        for (part, k), typ in selected.items():
            if (part, k) not in depths:      # a leaf with no hard cores (kv_leaf t2, the KV bank leaf): nothing is
                continue                     # staged on it, its nibbles keep the module default, its mask bit is not priced
            if part == s and ((bits >> k) & 1) != vp_xr.get(typ, 0):
                raise SystemExit(f"u_s_{s} leaf {k}: LF_VP_XR mask bit {(bits >> k) & 1} differs from the VP_XR contract "
                                 f"{vp_xr.get(typ, 0)} of {typ} (pass --vp-xr {typ}:1 for an XR leaf)")
        if old and "LF_CS_" in old:
            raise SystemExit(f"u_s_{s}: netlist already sets LF_CS_* ({old[:80]})")
        done.add(s)
        p = (old + ", " if old else "") + ", ".join(vals)
        return f"{m.group('lead')}#({p}) {m.group('inst')} ("

    out = INST.sub(sub, net_text)
    miss = sorted(set(slices) - done)
    if miss:
        raise SystemExit(f"plan leaf slices not instantiated in the netlist: {miss}")
    return out, rep


def update(plan, staged_text, classes):
    """S81-LEAF-SWR 11-20: re-price only `classes` (e.g. SWR_D) on an ALREADY staged netlist.  Every slice instance that
    holds a plan leaf gets the nibbles of those classes recomputed from the plan (leaf_cs_depth.plan_depths, the strict
    gate's own definition); every other class, nibble, parameter (LF_VP_XR) and instance stays byte-identical.  Fails
    closed on a class not in CL, an XR / group dependent class, an instance without a literal LF_CS_<C>, a depth > 15."""
    bad = [c for c in classes if c not in CL or c in ("HI_D", "HI_GS", "HO_GS", "H_G")]
    if bad:
        raise SystemExit(f"--update: {bad} not updatable (HI_D/HI_GS/HO_GS/H_G depend on XR / group contracts: full stage)")
    PT = plan["partition_types"]
    want = {}
    for p in plan["partitions"]:
        m = PART.match(p["name"])
        if not (LCD.LEAF_TYPE.match(p["type"]) and m) or not PT[p["type"]].get("hard_cores"):
            continue
        d, _ = LCD.plan_depths(PT[p["type"]])
        for c in classes:
            v = d.get(CLS[c], 0)
            if v > 15:
                raise SystemExit(f"{p['name']}: {c} depth {v} > 15")
            want.setdefault(m.group(1), {})[(c, int(m.group(2)))] = v
    rep, done = [], set()

    def sub(m):
        s = m.group("inst")[4:]
        if s not in want:
            return m.group(0)
        p = m.group("p") or ""
        for c in classes:
            r = re.search(rf"\.LF_CS_{c}\(\s*20'h([0-9a-fA-F]{{5}})\s*\)", p)
            if not r:
                raise SystemExit(f"u_s_{s}: no literal .LF_CS_{c}(20'h.....) to update (stage the slice first)")
            v0 = int(r.group(1), 16)
            v = v0
            for k in range(5):
                if (c, k) in want[s]:
                    v = (v & ~(0xF << (4 * k))) | (want[s][(c, k)] << (4 * k))
            if v != v0:
                rep.append(dict(slice="u_s_" + s, cls=c, old=f"20'h{v0:05x}", new=f"20'h{v:05x}"))
            p = p[:r.start(1)] + f"{v:05x}" + p[r.end(1):]
        done.add(s)
        return f"{m.group('lead')}#({p}) {m.group('inst')} ("

    out = INST.sub(sub, staged_text)
    miss = sorted(set(want) - done)
    if miss:
        raise SystemExit(f"plan leaf slices not instantiated in the netlist: {miss}")
    return out, rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("netlist")
    ap.add_argument("out")
    ap.add_argument("--rtl", default="rtl")
    ap.add_argument("--report")
    ap.add_argument("--hi-gs", action="append", default=[], metavar="TYPE:N")
    ap.add_argument("--ho-gs", action="append", default=[], metavar="TYPE:N")
    ap.add_argument("--vp-xr", action="append", default=[], metavar="TYPE:0|1",
                    help="explicit selective XR contract: plan effective HI depth includes XR; source depth excludes it")
    ap.add_argument("--vp-sr", action="append", default=[], metavar="TYPE:0|1",
                    help="explicit SR contract (ot_s81sl_vp SR 1, OT_S81SL_VP_SRAMREG): plan effective HO depth includes the SR "
                         "output station; source HO_D excludes it")
    ap.add_argument("--update", action="append", default=[], metavar="CLASS",
                    help="re-price only these classes (e.g. SWR_D) on an already staged netlist; all else unchanged")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    if a.update:
        out, rep = update(plan, Path(a.netlist).read_text(), a.update)
        Path(a.out).write_text(out)
        if a.report:
            Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
        print(f"LF_CS update {a.update}: {len(rep)} slice nibble words changed: "
              + "; ".join(f"{r['slice']} {r['cls']} {r['old']}->{r['new']}" for r in rep))
        return 0
    overrides = {}
    for param, values in (("HI_GS", a.hi_gs), ("HO_GS", a.ho_gs)):
        for item in values:
            try:
                typ, value = item.rsplit(":", 1)
                value = int(value)
            except ValueError:
                ap.error(f"invalid {param} override {item!r}; expected TYPE:N")
            if param in overrides.setdefault(typ, {}):
                ap.error(f"duplicate {param} override for {typ}")
            overrides[typ][param] = value
    xr = {}
    for item in a.vp_xr:
        try:
            typ, value = item.rsplit(":", 1)
            value = int(value)
        except ValueError:
            ap.error(f"invalid VP_XR contract {item!r}; expected TYPE:0|1")
        if typ in xr or value not in (0, 1):
            ap.error(f"duplicate or invalid VP_XR contract {item!r}")
        xr[typ] = value
    sr = {}
    for item in a.vp_sr:
        try:
            typ, value = item.rsplit(":", 1)
            value = int(value)
        except ValueError:
            ap.error(f"invalid VP_SR contract {item!r}; expected TYPE:0|1")
        if typ in sr or value not in (0, 1):
            ap.error(f"duplicate or invalid VP_SR contract {item!r}")
        sr[typ] = value
    out, rep = stage(plan, Path(a.netlist).read_text(), a.rtl, overrides, xr, sr)
    Path(a.out).write_text(out)
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    n = sum(1 for r in rep if "depths" in r)
    print(f"LF_CS stage: {n} leaves on {len({r['slice'] for r in rep if 'slice' in r})} slice instances; "
          f"cs rows (not staged) on {sum(1 for r in rep if r.get('cs_rows'))} leaves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
