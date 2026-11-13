#!/usr/bin/env python3
"""LF-CS stage (S81-LEAF-FLOOR-2 11-12): the plan's leaf station depths onto the die netlist's slice instances.

    stage_lfcs_netlist.py PLAN.json DIE_NETLIST.v OUT_NETLIST.v [--report OUT.json]

For every leaf partition s_<slice>_L<k> (= u_s_<slice>...u_lf<k>) of an ot_s81sl_leaf__* or
ot_s81sl_kv_leaf__* type, the depth of class c is the deepest plan internal_stations row of that class
(leaf_cs_depth.plan_depths: the strict bind gate's own definition).  hi / ho trees: GS = D (every hi / ho stage is a
shared group stage, as the bound form today; kv leaves GS 0, per lane, as DIE-S81-70), H_G 4.  The die instance u_s_<slice> gets #(.LF_CS_<C>(20'h...)) for
all 17 parameters; a nibble with no plan leaf keeps the slice module's default (read from its RTL header).
cs rows have no RTL realisation (re-planned in the floorplan stage) and are reported, never staged."""
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


def leaf_depths(plan):
    """{(slice, k): {param: depth}}, report rows."""
    PT = plan["partition_types"]
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
            rep.append(dict(part=p["name"], type=p["type"], skipped="no hard cores (no leaf chains)"))
            continue
        missing = LCD.unmapped_core_rows(t)
        if missing:
            raise SystemExit(f"{p['name']}: {len(missing)} planned core station rows have no RTL class; "
                             "no LF_CS source staged")
        want, dis = LCD.plan_depths(t)
        d = {x: want.get(c, 0) for x, c in CLS.items()}
        kv = "kv_leaf" in p["type"]          # DIE-S81-70 kv leaves: per-lane hi / ho stages (GS 0), as bound today
        d["HI_GS"], d["HO_GS"], d["H_G"] = (0, 0, 4) if kv else (d["HI_D"], d["HO_D"], 4)
        if any(v > 15 for v in d.values()):
            raise SystemExit(f"{p['name']}: depth > 15 does not fit a nibble: {d}")
        out[(m.group(1), k)] = d
        rep.append(dict(part=p["name"], type=p["type"], slice="u_s_" + m.group(1), k=k, depths=d, disagree=dis,
                        cs_rows=want.get("cs", 0)))
    return out, rep


def stage(plan, net_text, rtl_root):
    depths, rep = leaf_depths(plan)
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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("netlist")
    ap.add_argument("out")
    ap.add_argument("--rtl", default="rtl")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    out, rep = stage(plan, Path(a.netlist).read_text(), a.rtl)
    Path(a.out).write_text(out)
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    n = sum(1 for r in rep if "depths" in r)
    print(f"LF_CS stage: {n} leaves on {len({r['slice'] for r in rep if 'slice' in r})} slice instances; "
          f"cs rows (not staged) on {sum(1 for r in rep if r.get('cs_rows'))} leaves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
