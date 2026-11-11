#!/usr/bin/env python3
"""S81-PLANMODEL-1 11-11: plan connectivity model of the S81 leaf types, derived from the leaf RTL (ADVISORY).

Why: core_conns lists every u_vn.u_a/u_b hq_d/hw_d/hr_*/hw_* port against all 16 lane cores at full port width and the plan
carries FIRM "+1 cycle" internal_stations for those links, so route_supply / feas / wcut charge ~522 b per lane (one private
register chain per lane).  The bound netlist has none of that (S81-STN-SHARE 5fc9da6757): the leaf stations u_cst_hi/ho/vni/..
are depth 0 (wires), the vp glue already shares the registers, and hw_d is a gather.  This tool derives the real nets from
ot_s81sl_vp.sv (the g_ln generate, the b_lr / b_hw / cf register blocks) and from the CS_* depths of the bound leaf, and writes a
core_conns sidecar that route_supply reads with --core-conns:

  core_conns[TYPE]           the type's conns with the vn<->lane / vn<->vp-glue entries replaced
  fanout_nets[TYPE]          [{name, kind, bits, pins:[[inst, port]..], glue_of:[[inst, port]..]}]  one RUDY net each:
                               hi_fan   the vp glue register -> its 4 lane sinks (1024 nets: 160 b quad-shared cf, 96 b gl%4-shared ly+lr)
                               hi_feed  vn_a / vn_b hq_d -> that glue register (placed at the centroid of glue_of)
                               ho       lane o/vo/fault (18 b a lane) -> vn_a / vn_b hw_d
                               (--sram) rd_out -> cf / ly / hw_d, hq_d -> wd_in
  unrealised_stations[TYPE]  {phantom: [{idx, conn, launch, capture, bits}]}  plan stations of a class whose bound depth is 0
  claimed ports are those named in a net's pins (route_supply does not also draw them as glue escapes / core_conns nets).

usage: s81_leaf_conns.py PLAN.json --repo REPO --out OUT.json [--types T,..|--match RE] [--sram] [--audit AUDIT.tsv]
       [--bound-rtl TYPE=FILE ...]   (bound RTL: the CS_* depths are COUNTED from its stage registers, kit_istations.native_params)
"""
import argparse
import importlib.util
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SLICE = "rtl/dsrom_sys/s81_dv/slice"


def _kit():
    spec = importlib.util.spec_from_file_location("kit_istations", HERE / "kit_istations.py")
    sys.path.insert(0, str(HERE))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------------------------------------------ RTL
def _ev(expr, env):
    expr = expr.strip()
    if not re.fullmatch(r"[0-9a-zA-Z_ +*()/%\-]*", expr):
        raise ValueError(f"unsupported index expression {expr!r}")
    return int(eval(expr.replace("/", "//"), {"__builtins__": {}}, env))


def parse_vp(txt):
    """lane input / output nets of ot_s81sl_vp from its RTL.  Returns
    {hi: [{kind, key, bits, sinks: [(lane, port)]}], ho: {lane: bits}, lane_ports: {...}, hw_from_sram: bool, hs_from_hq: bool}.
    Raises on any pattern it does not recognise (the model must follow the RTL)."""
    # lane input bundle fields, MSB first
    m = re.search(r"assign\s+hi_s\[\s*256\s*\*\s*gl\s*\+:\s*256\s*\]\s*=\s*\{(.*?)\};", txt, re.S)
    if not m:
        raise ValueError("vp: hi_s assign not found")
    fields = [f.strip() for f in re.split(r",\s*(?![^\[]*\])", m.group(1).replace("\n", " ")) if f.strip()]
    # lane port <- li[hi:lo]
    ports = {}
    for p, hi, lo in re.findall(r"\.(\w+)\(\s*li\[(\d+):(\d+)\]\s*\)", txt):
        ports[p] = (int(lo), int(hi))
    if len(ports) < 10:
        raise ValueError(f"vp: lane input ports not found ({ports})")
    # field widths: cf 32, ly 32, lr[..][m][31:16] 16
    off = 256
    layout = []
    for f in fields:
        w = 16 if re.search(r"\[31:16\]$", f) else 32
        off -= w
        layout.append((f, off, w))
    if off != 0:
        raise ValueError(f"vp: hi_s fields sum to {256 - off} b, not 256")
    # register D sources
    lr_d = {}   # (k,i,m) -> D slice start of hqd_c
    ly_d = {}
    for k in range(4):
        for i in range(4):
            env = dict(k=k, i=i)
            for e1, mm, e2 in re.findall(r"lr\[([^\]]+)\]\[(\d)\]\s*<=\s*\{hqd_c\[(.+?)\s*\+:\s*16\],\s*16'd0\}", txt):
                lr_d[(_ev(e1, env), int(mm))] = _ev(e2, env)
            for e1, e2 in re.findall(r"ly\[([^\]]+)\]\s*<=\s*yrow_d\[YA\]\[(.+?)\s*\+:\s*32\]", txt):
                ly_d[_ev(e1, env)] = _ev(e2, env)
    if len(lr_d) != 64 or len(ly_d) != 16:
        raise ValueError(f"vp: lr/ly register blocks not recognised ({len(lr_d)}, {len(ly_d)})")
    cf_d = {}
    for e1, e2 in re.findall(r"cf\[([^\]]+)\]\s*<=\s*q1r\[(.+?)\s*\+:\s*32\]", txt):
        for i in range(4):
            for j in range(1, 5):
                for e1_ in (e1,):
                    try:
                        cf_d[_ev(e1_, dict(i=i, j=j))] = _ev(e2, dict(i=i, j=j))
                    except (ValueError, NameError):
                        pass
    cf_idx = {x for x in cf_d if 0 <= x < 20}
    if len(cf_idx) != 20:
        raise ValueError(f"vp: cf rows not recognised ({sorted(cf_idx)})")
    # sinks per register D-source
    groups = defaultdict(lambda: dict(sinks=[], bits=0))
    for gl in range(16):
        env = dict(gl=gl, KK=gl // 4, II=gl % 4)
        for f, lo, w in layout:
            port = next((p for p, (plo, phi) in ports.items() if plo == lo and phi == lo + w - 1), None)
            if port is None:
                raise ValueError(f"vp: no lane port for field {f} [{lo + w - 1}:{lo}]")
            mc = re.fullmatch(r"cf\[(.+)\]", f)
            ml = re.fullmatch(r"ly\[(.+)\]", f)
            mr = re.fullmatch(r"lr\[(.+?)\]\[(\d)\]\[31:16\]", f)
            if mc:
                idx = _ev(mc.group(1), env)
                key = ("cf", idx)
                kind, bits = "cf", 32
            elif ml:
                key = ("yrow", ly_d[_ev(ml.group(1), env)])
                kind, bits = "ly", 32
            elif mr:
                key = ("hqd_c", lr_d[(_ev(mr.group(1), env), int(mr.group(2)))])
                kind, bits = "lr", 16
            else:
                raise ValueError(f"vp: field {f!r} not recognised")
            g = groups[key]
            g.update(kind=kind, bits=bits)
            g["sinks"].append((gl, port))
    hi = []
    for key, g in sorted(groups.items()):
        hi.append(dict(kind=g["kind"], key=key, bits=g["bits"], sinks=sorted(g["sinks"])))
    if sum(g["bits"] for g in hi) != 1024 or any(len(g["sinks"]) != 4 for g in hi):
        raise ValueError("vp: lane inputs are not 1024 four-sink nets: "
                         f"{sum(g['bits'] for g in hi)} b, sinks {sorted({len(g['sinks']) for g in hi})}")
    # lane outputs -> hw_d
    ho_ok = re.search(r"hw_d\[\(4 \* k \+ i\) \* 16 \+: 16\] <= lo\[4 \* k \+ i\]\[31:16\]", txt) is not None
    ho_glue = re.search(r"assign\s+ho_l\[18 \* gl \+: 18\]\s*=\s*\{lqv, lq\}", txt) is not None
    if not (ho_ok and ho_glue):
        raise ValueError("vp: hw_d gather not recognised")
    return dict(hi=hi, ho_bits=18,
                hw_from_sram=bool(re.search(r"hw_d\s*<=\s*\{qo,\s*qe\}", txt)),
                hs_from_hq=bool(re.search(r"hs_d\s*<=\s*hqd_c", txt)))


def leaf_defaults(slice_txt):
    """CS_*_D defaults of ot_s81sl_leaf (the bound depth of every ot_s81sl_leaf type unless the bind overrides it)."""
    i = re.search(r"\bmodule\s+ot_s81sl_leaf\b", slice_txt)
    if not i:
        raise ValueError("slice RTL: module ot_s81sl_leaf not found")
    rest = slice_txt[i.start():]
    head = rest[: rest.index("\n) (")] if "\n) (" in rest else rest[:6000]
    return {k: int(v) for k, v in re.findall(r"parameter integer (CS_\w+?)\s*=\s*(\d+)", head)}


def kv_leaf_depths(w3_txt):
    """{kv_leaf type suffix: {CS_<C>_D: depth}} from the slice_w3 bind: .LF_CS_<C>_D(20'h...) nibble k is the depth of leaf
    lf[k]; the comment on that instance names which kv_leaf type sits at lf[k] (lf[1] = ot_s81sl_kv_leaf__t3 ...)."""
    nib = {c: v for c, v in re.findall(r"\.LF_CS_(\w+?)_D\(20'h([0-9a-fA-F]+)\)", w3_txt)}
    at = {int(k): t for k, t in re.findall(r"lf\[(\d)\] = (?:ot_s81sl_kv_leaf)?__(t\d+)", w3_txt)}
    out = {}
    for k, t in at.items():
        out[t] = {f"CS_{c}_D": int(v.zfill(5)[::-1][k], 16) for c, v in nib.items()}
    return out


def bound_depths(kit, defaults, bound_txt=None):
    """{CS_<CLASS>_D: depth} of a type: counted from a bound native RTL when given, else the leaf defaults."""
    if bound_txt is not None:
        have = kit.native_params(bound_txt)
        if have:
            return dict(defaults, **{k: v for k, v in have.items() if k.endswith("_D")}), "bound-rtl"
    return dict(defaults), "leaf-default"


# ------------------------------------------------------------------------------------------------ model
LANE_RX = re.compile(r"^(.*u_vp)\.g_ln\[(\d+)\]\.u_l$")


def type_insts(hard_cores):
    """lane / vn / sram instance names of a leaf type, or None when the type has no 16-lane leaf."""
    lanes, vn, sram, pre = {}, {}, {}, None
    for h in hard_cores:
        i = h["inst"]
        m = LANE_RX.match(i)
        if m:
            lanes[int(m.group(2))] = i
            pre = m.group(1)[: -len(".u_vp")]
        elif i.endswith(".u_vn.u_a"):
            vn["a"] = i
        elif i.endswith(".u_vn.u_b"):
            vn["b"] = i
        elif re.search(r"\.u_vp\.u_b[01]$", i):
            sram[i[-2:]] = i
    if len(lanes) != 16 or set(vn) != {"a", "b"}:
        return None
    return dict(lanes=lanes, vn=vn, sram=sram, leaf=pre)


def _stations(t, depths, kit):
    """plan internal_stations vs the bound depth of their CS_* class -> dict(phantom, audit)."""
    phantom, audit = [], defaultdict(lambda: dict(stations=0, bits=0, plan_depth=set(), bound=None, cycles=0))
    for idx, e in enumerate(t.get("internal_stations") or []):
        cls, _, _ = kit.core_class(e)
        if cls is None:
            continue
        param = kit.CLASS_PARAM.get(cls, "CS_CS_D")
        bd = depths.get(param, 0) if cls != "cs" else 0
        a = audit[cls]
        a["stations"] += 1
        a["bits"] += int(e.get("bits", 1) or 1)
        a["plan_depth"].add(len(e.get("regs_um") or []))
        a["bound"] = bd
        pd = len(e.get("regs_um") or [])
        if pd > bd:
            a["cycles"] += pd - bd
            if bd == 0:
                phantom.append(dict(idx=idx, conn=e.get("conn"), launch=e.get("launch"), capture=e.get("capture"),
                                    bits=int(e.get("bits", 1) or 1), cls=cls, plan_depth=pd, bound_depth=bd))
    return dict(phantom=phantom, audit=dict(audit))


def build_type(tn, t, vp, depths, kit, sram=False, base=None, model=True):
    """-> dict(conns, nets, phantom, audit) for one type, or None when it has no 16-lane leaf.  model=False (kv_leaf types:
    real per-lane stations at the bound depth) only audits plan stations against the bound depth."""
    if not model:
        return dict(conns=base or {}, nets=[], **_stations(t, depths, kit))
    ins = type_insts(t.get("hard_cores") or [])
    if ins is None:
        return None
    lanes, vn, sr = ins["lanes"], ins["vn"], ins["sram"]
    nets = []
    for g in vp["hi"]:
        sinks = [[lanes[gl], p] for gl, p in g["sinks"]]
        tag = f"{g['key'][0]}{g['key'][1]}"
        nets.append(dict(name=f"hi_fan:{tag}", kind="hi_fan", bits=g["bits"], pins=sinks))
        if g["kind"] == "lr":
            for v in ("a", "b"):
                nets.append(dict(name=f"hi_feed:{tag}:{v}", kind="hi_feed", bits=g["bits"], pins=[[vn[v], "hq_d"]],
                                 glue_of=sinks))
    for gl in range(16):
        nets.append(dict(name=f"ho:{gl}", kind="ho", bits=vp["ho_bits"],
                         pins=[[lanes[gl], "o"], [lanes[gl], "vo"], [lanes[gl], "fault"], [vn["a"], "hw_d"], [vn["b"], "hw_d"]]))
    if sram and sr:
        rd = [[sr[k], "rd_out"] for k in sorted(sr)]
        for s in range(4):
            sinks = [[lanes[gl], p] for g in vp["hi"] if g["key"] in (("yrow", 32 * s),) + tuple(("cf", c) for c in range(20) if c % 4 == s)
                     for gl, p in g["sinks"]]
            nets.append(dict(name=f"sram_feed:{s}", kind="sram_feed", bits=32, pins=rd, glue_of=sinks))
        if vp["hw_from_sram"]:
            nets.append(dict(name="sram_hw", kind="sram_hw", bits=256, pins=rd + [[vn["a"], "hw_d"], [vn["b"], "hw_d"]]))
        if vp["hs_from_hq"]:
            nets.append(dict(name="hq_wd", kind="hq_wd", bits=256,
                             pins=[[vn["a"], "hq_d"], [vn["b"], "hq_d"]] + [[sr[k], "wd_in"] for k in sorted(sr)]))
    claimed = {(i, p) for n in nets for i, p in n["pins"]}
    # conns: vn ports that talked to the lanes through the plan stations / per-lane broadcast now go to the vp glue
    conns = json.loads(json.dumps(base or {}))
    lane_set = set(lanes.values())

    def to_lane(d):
        d = str(d)
        return d.startswith("core:") and (d[5:] in lane_set or d[5:].rpartition(".")[0] in lane_set)

    for inst in (vn["a"], vn["b"]):
        ent = conns.get(inst)
        if ent is None:
            continue
        for port, dl in list(ent.items()):
            if (inst, port) in claimed:
                ent[port] = ["glue"]
            elif any(to_lane(d) for d in dl):
                ent[port] = [d for d in dl if not to_lane(d)] or ["glue"]
    return dict(conns=conns, nets=nets, **_stations(t, depths, kit))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--die", default="s81")
    ap.add_argument("--out", required=True)
    ap.add_argument("--types")
    ap.add_argument("--match", default=r"^ot_s81sl_(kv_)?leaf__")
    ap.add_argument("--sram", action="store_true", help="also model the vp SRAM paths (rd_out -> cf/ly/hw_d, hq_d -> wd_in)")
    ap.add_argument("--audit", help="TSV of plan-vs-bound station rows")
    ap.add_argument("--bound-rtl", action="append", default=[], metavar="TYPE=FILE")
    ap.add_argument("--conns", help="base core_conns file (default: route_supply's own sources)")
    a = ap.parse_args(argv)
    repo = Path(a.repo).resolve()
    plan = Path(a.plan)
    P = json.loads(plan.read_text())
    T = P["partition_types"]
    kit = _kit()
    vp = parse_vp((repo / SLICE / "ot_s81sl_vp.sv").read_text())
    defaults = leaf_defaults((repo / SLICE / "ot_s81sl_slice.sv").read_text())
    rs_spec = importlib.util.spec_from_file_location("route_supply", HERE / "route_supply.py")
    RS = importlib.util.module_from_spec(rs_spec)
    rs_spec.loader.exec_module(RS)
    die_dir = repo / "physical" / "die_plan" / a.die
    if not die_dir.is_dir():
        die_dir = plan.parent
    conns = RS.load_conns(die_dir, a.conns, plan.parent, [])
    bound = {k: Path(v).read_text() for k, v in (x.split("=", 1) for x in a.bound_rtl)}
    w3 = repo / SLICE / "cap_end" / "ot_s81sl_slice_w3.sv"
    kvd = kv_leaf_depths(w3.read_text()) if w3.exists() else {}
    names = [n for n in T if (n in a.types.split(",") if a.types else re.search(a.match, n))]
    out = dict(schema="s81_leaf_conns/1", plan=str(plan), advisory=True, sram=a.sram,
               core_conns={}, fanout_nets={}, unrealised_stations={}, audit={})
    rows = []
    for n in names:
        cc_key = next((k for k in (n, re.sub(r"__cl[0-9a-f]{8}.*$", "", n), re.sub(r"__.*$", "", n)) if conns.get(k)), None)
        depths, src = bound_depths(kit, defaults, bound.get(n))
        kv = n.startswith("ot_s81sl_kv_leaf__")
        if kv:
            depths = dict(defaults, **kvd.get(re.sub(r"^ot_s81sl_kv_leaf__(t\d+).*$", r"\1", n), {}))
            src = "slice_w3 LF_CS_*"
        r = build_type(n, T[n], vp, depths, kit, a.sram, conns.get(cc_key) if cc_key else None, model=not kv)
        if r is None:
            continue
        if not kv:
            out["core_conns"][n] = r["conns"]
            out["fanout_nets"][n] = r["nets"]
            out["unrealised_stations"][n] = dict(phantom=r["phantom"])
        out["audit"][n] = dict(depth_source=src, classes={c: dict(v, plan_depth=sorted(v["plan_depth"])) for c, v in r["audit"].items()})
        for c, v in sorted(r["audit"].items()):
            rows.append((n, c, v["stations"], v["bits"], ",".join(map(str, sorted(v["plan_depth"]))), v["bound"],
                         max(v["plan_depth"]) - v["bound"], src))
    Path(a.out).write_text(json.dumps(out, indent=1))
    if a.audit:
        with open(a.audit, "w") as f:
            f.write("type\tclass\tstations\tbits\tplan_depth\tbound_depth\tdelta_cycles_max\tdepth_source\n")
            for r in rows:
                f.write("\t".join(map(str, r)) + "\n")
    print(f"s81_leaf_conns: {len(out['fanout_nets'])} modelled types, {len(out['audit'])} audited, {sum(len(v['phantom']) for v in out['unrealised_stations'].values())} unrealised stations -> {a.out}")


if __name__ == "__main__":
    main()
