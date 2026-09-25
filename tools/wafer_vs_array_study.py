#!/usr/bin/env python3
"""Iso-area study: can a ROM WAFER design for DeepSeek-V4.1-Flash decode faster than the ROM ARRAY?

The claim under test: "even tightly integrated on a wafer, V4.1 decode is not faster than the array at
equal silicon, so the wafer (much harder to build) should be rejected."

Method (every number below is computed here, from the repository's own machinery):

* **Designs at equal silicon.**  For each wafer count W in (2, 3, 4, 12) the wafer design and an array of
  the same silicon (W x 46,225 mm2 / 815 mm2 dies, rounded DOWN to whole 4-die packages so the array never
  gets more silicon than the wafer; the residual is stated) are sized by the analytical model's own code:
  tools/run_roofline_studies.py `_build_rom_budget` on the n5_vs_b200 study's `array-hw-hybrid` and
  `wafer-hybrid` fabric plans -- ROM sized to the stored weights at the checkpoint's 7.40 bits/parameter,
  graded interconnect/overhead fractions, HBM PHY per stack, compute takes the rest, HBM stacks for the
  200K-context KV of the 4,096-user provisioning batch capped by the die/wafer edge
  (`max_hbm_stacks_per_device`).  The analytical `evaluate` then gives each design's component times,
  which the critical-path model uses as its matrix-sweep input (exactly as decode_critical_path does).
  Points that cannot hold the weights or the provisioning batch's KV are refused with the reason.
* **Decode critical path.**  tools/decode_critical_path.py prices one token bottom-up (measured ASAP7 RTL
  depths, routed clock) on each design, sweeping tensor group x dies-per-package x board topology x
  reduction algorithm (array) or tensor group x field-grid shape x reduction algorithm (wafer); the best
  configuration by batch-1 per-user rate is reported, with batch 64 and 4096 on the same configuration,
  and separately the best batch-4096 aggregate.
* **Axes.**  Wafer fabric: the on-wafer mesh at 125 ns per field crossing (band 75-250; the control), and
  a designed express fabric at 25 / 10 / 5 ns and at the wire limit (28.55 mm x
  latency.global_wire_delay_s_per_mm + one router cycle).  Array links at their technology.json points and
  band ends.  Sinkhorn: the built divider (31 cycles), faster bit-exact dividers (12, 4), an idealised
  one-cycle-per-dependent-operation step, and the chain removed (hypothetical, to isolate the fabric).
* **Crossover.**  For every pair and Sinkhorn variant, the largest wafer field-crossing latency at which
  the wafer's batch-1 rate reaches the array's (array at its control links and at its fast band end).

Output: results/roofline/critical_path/wafer_vs_array_iso_area.json.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

import decode_critical_path as D  # noqa: E402

SCHEMA = "opentallas.wafer-vs-array-iso-area.v1"
OUT = ROOT / "results/roofline/critical_path/wafer_vs_array_iso_area.json"
STUDY = "n5_vs_b200"
CONTEXT = 200_000
BATCHES = (1, 64, 4096)
WAFER_COUNTS = (2, 3, 4, 12)
FIELDS_PER_WAFER = 57                  # technology.json wafer.reticle_regions (decode_critical_path's grid)
DIES_PER_PACKAGE = 4                   # the array's package unit for the iso-area rounding
NL = 40

# -- the axes -----------------------------------------------------------------------------------------------
SINKHORN_VARIANTS = [
    dict(id="fdiv31_built", fdiv_cycles=31, sinkhorn_step_cycles=0, sinkhorn=True,
         grade="measured", note="rtl/hdc/v41/ot_hdc_fdiv.sv DEPTH 31; step = 3 sequential fadd + eps fadd + fdiv "
                                "= 51 cycles"),
    dict(id="fdiv12", fdiv_cycles=12, sinkhorn_step_cycles=0, sinkhorn=True,
         grade="assumed", note="a 12-cycle bit-exact divider (not built); step 32 cycles; also speeds the "
                               "attention normalise and the compressor pool"),
    dict(id="fdiv4", fdiv_cycles=4, sinkhorn_step_cycles=0, sinkhorn=True,
         grade="assumed", note="a 4-cycle bit-exact divider (not built); step 24 cycles"),
    dict(id="step_ideal_5", fdiv_cycles=4, sinkhorn_step_cycles=5, sinkhorn=True,
         grade="assumed", note="IDEALISED FLOOR: one cycle per dependent operation (3 adds, eps, divide) at "
                               "the routed clock; not buildable at ~1 GHz on ASAP7, where a combinational "
                               "fp32 add alone is ~6.4 ns"),
    dict(id="removed", fdiv_cycles=4, sinkhorn_step_cycles=0, sinkhorn=False,
         grade="hypothetical", note="the 20-iteration Sinkhorn costs nothing (NOT the model); isolates the "
                                    "fabric effect"),
]
MESH_CONTROL_NS = 125.0
ROUTER_CYCLES = 1                      # ASSUMED router term of a designed express link (one routed clock)


def wafer_fabric_variants(tech, clock):
    wire = tech["latency"]["global_wire_delay_s_per_mm"]
    pitch = math.sqrt(tech["reticle"]["area_mm2"]["value"])
    router = ROUTER_CYCLES / clock
    wl = pitch * wire["value"] + router
    return [
        dict(id="mesh_125", hop_s=125e-9, grade="derived", role="control",
             note="links.on_wafer_n5.hop_latency_s: Cerebras-style stitched mesh, one 815 mm2 field crossing"),
        dict(id="mesh_75", hop_s=75e-9, grade="derived", role="control band low", note="on_wafer_n5 range_low"),
        dict(id="mesh_250", hop_s=250e-9, grade="derived", role="control band high", note="on_wafer_n5 range_high"),
        dict(id="express_25", hop_s=25e-9, grade="assumed", role="designed express fabric", note="design target"),
        dict(id="express_10", hop_s=10e-9, grade="assumed", role="designed express fabric", note="design target"),
        dict(id="express_5", hop_s=5e-9, grade="assumed", role="designed express fabric",
             note="design target; BELOW the wire-plus-router limit at the point wire delay"),
        dict(id="express_wire_limited", hop_s=wl, grade="derived", role="designed express fabric (floor)",
             note=f"{pitch:.2f} mm x {wire['value'] * 1e12:.0f} ps/mm (latency.global_wire_delay_s_per_mm, "
                  f"assumed, band {wire['range_low'] * 1e12:.0f}-{wire['range_high'] * 1e12:.0f}) = "
                  f"{pitch * wire['value'] * 1e9:.2f} ns + {ROUTER_CYCLES} router cycle "
                  f"({router * 1e9:.2f} ns, assumed)"),
    ]


ARRAY_LINK_VARIANTS = [
    dict(id="links_point", which="value", note="rom_package_ucie 10 ns, rom_board_serdes 100 ns"),
    dict(id="links_low", which="hop_low", note="UCIe 3 ns, board SerDes 40 ns (band low)"),
    dict(id="links_high", which="hop_high", note="UCIe 30 ns, board SerDes 250 ns (band high)"),
]


# -- analytical designs (the roofline code's own sizing) ------------------------------------------------------
def _roofline_env():
    import run_roofline_studies as R
    from opentallas.roofline import Technology
    from opentallas.schema import ModelProfile
    from opentallas.workload import hbm_resident_weight_bytes, kv_traffic
    cfg = R.STUDIES[STUDY]
    tech = R._node_technology(Technology.load(D.TECH), str(cfg["rom_node"]))
    model = ModelProfile.load(D.V41_CONFIG)
    mt = R._model_technology(tech, model.name)
    reticle = tech.graded("reticle", "area_mm2").value
    wafer = tech.graded("wafer", "area_mm2").value
    plans = {plan.label: (plan, area) for plan, area in
             R._fabric_plans(tech, cfg, wafer_area=wafer, reticle_area=reticle)}
    kv = kv_traffic(model, CONTEXT)
    dbk = kv.storage_bytes_per_user * R.PROVISION_BATCH + hbm_resident_weight_bytes(model)
    dbt = (kv.read_bytes + kv.write_bytes) * R.PROVISION_BATCH
    return dict(R=R, cfg=cfg, mt=mt, model=model, reticle=reticle, wafer=wafer, plans=plans,
                stored=R._rom_stored_bytes(model, None), execution=R._execution_format(mt, None, model),
                kv_bytes=dbk, kv_transfer=dbt)


def analytical_design(env, kind, devices):
    """One design sized by run_roofline_studies' own rules, its feasibility, and its points at BATCHES."""
    from opentallas.roofline import evaluate, max_hbm_stacks_per_device
    R, cfg, mt, model = env["R"], env["cfg"], env["mt"], env["model"]
    label = "array-hw-hybrid" if kind == "array" else "wafer-hybrid"
    plan, area = env["plans"][label]
    regions = R._regions_for(plan, devices, env["wafer"] if kind == "wafer" else None,
                             env["reticle"] if kind == "wafer" else None)
    name = f"{model.name}/ROM-{cfg['rom_node']}-native-HBMKV-{label}-x{devices}"
    budget = R._build_rom_budget(
        mt, name=name, node=str(cfg["rom_node"]), area_per_device=area, devices=devices, plan=plan,
        on_wafer_regions=regions, stored_weight_bytes=env["stored"], resident_kv_bytes=env["kv_bytes"],
        kv_transfer_bytes=env["kv_transfer"], kv_store="hbm", hbm_generation=str(cfg["hbm_generation"]),
        weight_amortization="batched", spare_area_policy="sram", weight_bits=None)
    d = budget.to_dict()
    assert d["name"] == name, (d["name"], name)
    usable = mt.hbm(str(cfg["hbm_generation"]), "stack_capacity_bytes").value * mt.efficiency("hbm_capacity").value
    edge = max_hbm_stacks_per_device(mt, generation=str(cfg["hbm_generation"]), die_area_mm2=area)
    reasons = list(budget.reasons)
    if budget.split.compute_mm2 <= 0:
        reasons.append("no compute area left after ROM, PHY, interconnect and overhead")
    if budget.weight_capacity_bytes + 1.0 < env["stored"]:
        reasons.append(f"ROM holds {budget.weight_capacity_bytes / 1e9:.1f} GB < {env['stored'] / 1e9:.1f} GB "
                       "stored weights")
    if edge * devices * usable + 1.0 < env["kv_bytes"]:
        reasons.append(f"edge-limited HBM ({edge} stacks/device) holds {edge * devices * usable / 1e12:.2f} TB "
                       f"< {env['kv_bytes'] / 1e12:.2f} TB provisioning-batch KV")
    points = []
    if not reasons:
        for b in BATCHES:
            step = evaluate(budget, model, context_tokens=CONTEXT, batch_size=b, technology=mt,
                            weight_bits_per_parameter=None, execution_format=env["execution"],
                            prompt_tokens=CONTEXT if b == 1 else None)
            points.append(R._step_row(step, budget, family="rom", design_id=name, model=model))
    split = d["area_split_per_device"]
    summary = dict(
        design=name, kind=kind, devices=devices, area_mm2_per_device=area, silicon_mm2=area * devices,
        fields=devices * FIELDS_PER_WAFER if kind == "wafer" else devices, on_wafer_regions=regions,
        area_split_mm2_per_device={k: split[k] for k in ("rom_mm2", "compute_mm2", "hbm_phy_mm2",
                                                         "interconnect_mm2", "overhead_mm2", "sram_mm2")},
        rom_mm2_total=split["rom_mm2"] * devices, compute_mm2_total=split["compute_mm2"] * devices,
        hbm_stacks_per_device=d["hbm_stacks"], hbm_stacks_total=d["hbm_stacks"] * devices,
        hbm_edge_limit_per_device=edge, kv_read_bytes_s=d["kv_read_bytes_s"],
        kv_capacity_bytes=d["kv_capacity_bytes"], weight_capacity_bytes=d["weight_capacity_bytes"],
        stored_weight_bytes=env["stored"], static_power_w=d["static_power_w"], cooling_limit_w=d["cooling_limit_w"],
        tensor_group=d["topology"]["tensor_group"], feasible=not reasons, reasons=reasons,
        analytical=[dict(batch=q["batch_size"], per_user_tokens_s=q["per_user_tokens_s"],
                         aggregate_tokens_s=q["aggregate_tokens_s"], feasible=q["feasible"],
                         max_resident_users=q["max_resident_users"], power_w=q["power_w"],
                         dynamic_energy_j_per_token=q["dynamic_energy_j_per_token"],
                         component_times_s=q["component_times_s"]) for q in points])
    return summary, d, points


def minimum_devices(env, kind):
    R = env["R"]
    plan, area = env["plans"]["array-hw-hybrid" if kind == "array" else "wafer-hybrid"]
    return R._minimum_devices(
        env["mt"], node=str(env["cfg"]["rom_node"]), area_per_device=area, stored_weight_bytes=env["stored"],
        resident_kv_bytes=env["kv_bytes"], kv_transfer_bytes=env["kv_transfer"], kv_store="hbm",
        hbm_generation=str(env["cfg"]["hbm_generation"]), plan=plan,
        wafer_area=env["wafer"] if kind == "wafer" else None, reticle_area=env["reticle"] if kind == "wafer" else None)


def iso_area_pairs(env):
    per = env["wafer"] / env["reticle"]
    out = []
    for w in WAFER_COUNTS:
        exact = w * per
        dies = int(exact // DIES_PER_PACKAGE) * DIES_PER_PACKAGE
        out.append(dict(wafers=w, wafer_silicon_mm2=w * env["wafer"], array_dies_exact=exact, array_dies=dies,
                        array_packages=dies // DIES_PER_PACKAGE, array_silicon_mm2=dies * env["reticle"],
                        array_residual_mm2=w * env["wafer"] - dies * env["reticle"],
                        array_residual_fraction=1 - dies * env["reticle"] / (w * env["wafer"]),
                        nearest_dies=int(round(exact))))
    return out


# -- critical-path evaluation -------------------------------------------------------------------------------
def layer_fraction():
    d = json.loads(D.V41_CONFIG.read_text())
    return (sum(d["layer_dense_weight_bytes"]) + sum(d["layer_routed_weight_bytes"])) / d["checkpoint_bytes"]


def units_of(kind, devices):
    return devices * FIELDS_PER_WAFER if kind == "wafer" else devices


def per_layer_units(kind, devices, layout):
    """Units (dies or fields) one layer occupies.  rom_packed: the layer's own ROM need (layers are 58.0% of
    the stored bytes; Engram tables, embedding and head fill the remaining units).  uniform: every unit
    carries layer weights and Engram filler alike (units / 40, decode_critical_path's wafer rule)."""
    u = units_of(kind, devices)
    return u * layer_fraction() / NL if layout == "rom_packed" else u / NL


def placement_refusal(kind, devices, m, per_layer):
    """Can the stage groups be placed?  Groups of g units are the allocation grain; the last group of the
    pipeline (or of each layer, when a layer spans several sub-stage groups) may be partial and occupies
    only the units its weights need.  On a wafer a group never straddles two wafers."""
    u, g = units_of(kind, devices), m.group
    sub = m.substages_per_layer
    if sub > 1:
        full = NL * (sub - 1)
        partial = NL * math.ceil(per_layer - (sub - 1) * g - 1e-9)
    else:
        full = m.stages - 1
        partial = math.ceil(NL * per_layer - full * g - 1e-9)
    used = full * g + partial
    if used > u:
        return f"{full} full groups of {g} + {partial} units in partial groups = {used} > {u} units"
    if kind == "wafer":
        wafers = u // FIELDS_PER_WAFER
        slots = wafers * (FIELDS_PER_WAFER // g)
        leftover = FIELDS_PER_WAFER % g                      # fields per wafer outside whole groups
        if sub > 1:     # 40 partial groups of q fields: into leftover fields first, then g // q per free slot
            q = max(1, partial // NL)
            rest = max(0, NL - wafers * (leftover // q))
            fit = full + math.ceil(rest / max(1, g // q)) <= slots
        else:           # the one partial group needs a free slot or one wafer's leftover fields
            fit = full + (0 if partial <= leftover else 1) <= slots
        if not fit:
            return f"{full} full groups of {g} fields (+{partial} partial) do not tile {wafers} wafers " \
                   f"({slots} group slots)"
    return None


ARRAY_GROUPS = D.ARRAY_GROUPS + (64,)          # 64: large arrays must not be capped below their optimum
WAFER_GROUPS = (2,) + D.WAFER_GROUPS


def _links_at(links, which):
    if which == "value":
        return links
    return {k: dict(v, hop=v[which] or v["hop"]) for k, v in links.items()}


def fabrics_for(kind, g, links, devices, fabric_variant):
    """Every physical topology of one fabric variant at tensor group g (reduction algorithm: best per
    collective, as decode_critical_path's 'best')."""
    if kind == "array":
        ln = _links_at(links, fabric_variant["which"])
        for dp in (2, 4, 8):
            for board in D.BOARD_TOPOLOGIES:
                yield dict(dies_per_package=dp, physical=board), D.ArrayFabric(ln, dp, board, g, "best", dies=devices)
    else:
        for shape in ("square", "rect"):
            yield dict(dies_per_package=None, physical=shape), D.WaferFabric(links, g, shape, "best",
                                                                              hop_s=fabric_variant["hop_s"])


def _machine(ctx, kind, g, batch, p, clock, layout, iso_hbm=None):
    pts, des = ctx["points"], ctx["designs"]
    d = des[ctx["name"]]
    if iso_hbm:
        d = dict(d, kv_read_bytes_s=d["kv_read_bytes_s"] * iso_hbm)
        des = {ctx["name"]: d}
    return D.v41_machine(kind, g, batch, pts, des, p, clock, design=ctx["name"],
                         units=units_of(kind, ctx["devices"]), per_layer=per_layer_units(kind, ctx["devices"], layout),
                         g_ref=ctx["tensor_group"])


def best_config(ctx, kind, p, clock, links, fabric_variant, layout="rom_packed", batches=BATCHES, iso_hbm=None,
                c=None):
    """Sweep group x topology for one design, fabric variant and parameter set.  Returns the best row by
    batch-1 per-user rate (with its batch-64/4096 figures) and the best batch-4096 aggregate row."""
    c = c or D.v41_shape()
    rows, refused = [], []
    for g in (ARRAY_GROUPS if kind == "array" else WAFER_GROUPS):
        built = {}
        for bt in batches:
            m = _machine(ctx, kind, g, bt, p, clock, layout, iso_hbm)
            why = placement_refusal(kind, ctx["devices"], m, per_layer_units(kind, ctx["devices"], layout))
            if why:
                refused.append(dict(group=g, reason=why))
                built = None
                break
            built[bt] = D.Built(m, p, clock, D.v41_graph, c, m.context)
        if not built:
            continue
        for topo, fab in fabrics_for(kind, g, links, ctx["devices"], fabric_variant):
            if fab.refused:
                continue
            row = dict(group=g, stages=built[batches[0]].mach.stages,
                       substages_per_layer=built[batches[0]].mach.substages_per_layer, **topo)
            ok = True
            for bt, b in built.items():
                r = b.evaluate(fab)
                if not math.isfinite(r["period"]):
                    ok = False
                    break
                row[f"tok_s_user_b{bt}"] = 1 / r["period"]
                row[f"aggregate_tok_s_b{bt}"] = bt / r["period"]
                row[f"binding_b{bt}"] = "critical_path" if r["T"] >= r["occupancy_bound_s"] else "occupancy"
                if bt == batches[0]:
                    row["breakdown_us_b1"] = {k: round(v * 1e6, 3) for k, v in r["cats"].items()}
                    row["critical_path_us_b1"] = r["T"] * 1e6
                    row["algorithms_b1"] = sorted({e["algo"] for e in r["events"] if e["op"] != "hop"})
            if ok:
                rows.append(row)
    if not rows:
        return dict(best_b1=None, best_b64=None, best_aggregate_b4096=None, refused=refused, configs=0)
    out = dict(configs=len(rows), refused=refused)
    # best_b1 is ONE fixed configuration (its batch-64/4096 figures are that configuration's); best_b64 and
    # best_aggregate_b4096 let each batch pick its own group and topology
    for bt, key in ((1, "best_b1"), (64, "best_b64"), (4096, "best_aggregate_b4096")):
        out[key] = max(rows, key=lambda r: r[f"tok_s_user_b{bt}"]) if bt in batches else None
    return out


def params_for(sv):
    return replace(D.Params(), fdiv_cycles=sv["fdiv_cycles"], sinkhorn_step_cycles=sv["sinkhorn_step_cycles"],
                   sinkhorn=sv["sinkhorn"])


def sinkhorn_chain_us(sv, clock, mb=1.0):
    """Per-token Sinkhorn chain if it were serial: 80 sublayers x (2 + fadd + exp + 40 x step) cycles."""
    if not sv["sinkhorn"]:
        return 0.0
    c = D.v41_shape()
    half = sv["sinkhorn_step_cycles"] or (3 * D.FADD + D.FADD + sv["fdiv_cycles"])
    step = max(half, math.ceil(mb))
    per = 2 + D.FADD + D.SU["EXP"] + 2 * c["hc_sinkhorn_iters"] * step
    return 2 * NL * per / clock * 1e6


# -- worker ----------------------------------------------------------------------------------------------------
_CTX = {}


def _init(ctxs, clock, links):
    _CTX.update(ctxs=ctxs, clock=clock, links=links)


def _job(job):
    ctx = _CTX["ctxs"][job["key"]]
    p = replace(params_for(job["sinkhorn"]), clock_hz=_CTX["clock"], **job.get("extra", {}))
    fv = job["fabric"]
    links = _CTX["links"]
    if job.get("serdes_hop_s"):
        links = dict(links, rom_wafer_serdes=dict(links["rom_wafer_serdes"], hop=job["serdes_hop_s"]))
    r = best_config(ctx, ctx["kind"], p, _CTX["clock"], links, fv, layout=job.get("layout", "rom_packed"),
                    batches=job.get("batches", BATCHES), iso_hbm=job.get("iso_hbm"))
    return dict(job=dict(key=job["key"], sinkhorn=job["sinkhorn"]["id"], fabric=fv["id"],
                         layout=job.get("layout", "rom_packed"), tag=job.get("tag")), result=r)


def metrics(ds, res):
    """Per-batch best rates, per-mm2 and derived per-W figures for one design under one variant."""
    b1, b64, b4k = res["best_b1"], res["best_b64"], res["best_aggregate_b4096"]
    e = {a["batch"]: a["dynamic_energy_j_per_token"] for a in ds["analytical"]}

    def cfg(r):
        pk = f"{r['dies_per_package']}/" if r["dies_per_package"] else ""
        return f"g{r['group']} {pk}{r['physical']} x{r['stages']}"
    out = dict(tok_s_user_b1=b1["tok_s_user_b1"], tok_s_user_b64=b64["tok_s_user_b64"],
               aggregate_tok_s_b64=b64["aggregate_tok_s_b64"], aggregate_tok_s_b4096=b4k["aggregate_tok_s_b4096"],
               tok_s_user_b4096=b4k["tok_s_user_b4096"], config_b1=cfg(b1), config_b64=cfg(b64),
               config_b4096=cfg(b4k), breakdown_us_b1=b1["breakdown_us_b1"],
               critical_path_us_b1=b1["critical_path_us_b1"])
    for bt, agg in ((64, out["aggregate_tok_s_b64"]), (4096, out["aggregate_tok_s_b4096"])):
        pw = ds["static_power_w"] + e[bt] * agg
        out[f"tok_s_per_mm2_b{bt}"] = agg / ds["silicon_mm2"]
        out[f"power_w_b{bt}_derived"] = pw
        out[f"tok_s_per_w_b{bt}_derived"] = agg / pw
    return out


def slim(row):
    if row is None:
        return None
    keep = ("group", "dies_per_package", "physical", "stages", "substages_per_layer", "tok_s_user_b1",
            "tok_s_user_b64", "aggregate_tok_s_b64", "tok_s_user_b4096", "aggregate_tok_s_b4096", "binding_b1",
            "binding_b4096", "critical_path_us_b1", "breakdown_us_b1", "algorithms_b1")
    return {k: row[k] for k in keep if k in row}


def crossover_hop(ctx, p, clock, links, target, lo=0.0, hi=250e-9, tol=0.05e-9):
    """Largest field-crossing latency at which the wafer's best batch-1 rate is >= target (None if even a
    zero-latency fabric does not reach it; hi if the mesh band's top already does)."""
    def rate(h):
        r = best_config(ctx, "wafer", p, clock, links, dict(id="x", hop_s=h), batches=(1,))
        return r["best_b1"]["tok_s_user_b1"]
    if rate(lo) < target:
        return None, rate(lo)
    if rate(hi) >= target:
        return hi, rate(hi)
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if rate(mid) >= target:
            lo = mid
        else:
            hi = mid
    return lo, rate(lo)


def _cross_job(job):
    ctx = _CTX["ctxs"][job["key"]]
    p = replace(params_for(job["sinkhorn"]), clock_hz=_CTX["clock"])
    h, r = crossover_hop(ctx, p, _CTX["clock"], _CTX["links"], job["target"])
    return dict(key=job["key"], sinkhorn=job["sinkhorn"]["id"], against=job["against"], target=job["target"],
                max_field_hop_ns=None if h is None else h * 1e9, wafer_rate_at_crossover=r,
                zero_latency_wafer_rate=None if h is not None else r)


# -- the study -------------------------------------------------------------------------------------------------
ASSUMPTIONS = [
    dict(id="A1", grade="derived", statement="Designs are sized by the analytical model's own code "
         "(run_roofline_studies._build_rom_budget, n5_vs_b200, batched, spare area to SRAM, HBM-KV provisioned for "
         "4,096 users at 200K, stacks capped by the die/wafer edge); nothing is re-derived here.",
         direction="neutral: the same rule on both sides"),
    dict(id="A2", grade="derived", statement="Iso-area: the array gets W x 46,225 / 815 dies rounded DOWN to whole "
         "4-die packages (a silicon shortfall of 0.0127 of the wafer area at W = 2-4 and 0.0009 at W = 12).", direction="favours the wafer"),
    dict(id="A3", grade="measured", statement="Operator depths are the repository's routed/campaigned RTL "
         "(decode_critical_path RTL_SOURCES) at the slowest routed clock among the token path's units (1.0339 GHz "
         "ASAP7), applied to N5 on both sides.", direction="common-mode"),
    dict(id="A4", grade="derived", statement="Matrix-sweep time is the analytical design's own (max(compute, "
         "weight_read)/stage balance, scaled by g_ref/g), apportioned per matvec; lanes from routed lane areas.",
         direction="common-mode"),
    dict(id="A5", grade="derived", statement="Layout rom_packed: one layer occupies units x 0.580 (its share of "
         "the stored bytes) / 40; Engram tables, embedding and head fill the other units. The 'uniform' layout "
         "(units/40) is a sensitivity.", direction="favours neither; fewer stages for both"),
    dict(id="A6", grade="derived", statement="Wafer control fabric: links.on_wafer_n5 125 ns per 28.55 mm field "
         "crossing (75-250 ns band); per-field-edge bandwidth on_wafer_n5.bytes_s / 57 / 4; wafers joined by "
         "rom_wafer_serdes (100 ns, 40-250).", direction="the axis under test"),
    dict(id="A7", grade="assumed", statement="Designed express fabric: 25/10/5 ns per field crossing are design "
         "targets with no silicon; the wire limit is 28.55 mm x 150 ps/mm (assumed, 100-250) + one router cycle "
         "(assumed). The express fabric keeps the mesh's bandwidth and is applied to every field crossing "
         "(collectives and pipeline hops).", direction="favours the wafer"),
    dict(id="A8", grade="derived", statement="Array links: rom_package_ucie 10 ns (3-30), rom_board_serdes 100 ns "
         "(40-250), package SerDes lanes scale with the package edge; one switch tier 250 ns assumed.",
         direction="the array's axis"),
    dict(id="A9", grade="measured/assumed", statement="Sinkhorn: 20 iterations x 2 normalisations per sublayer, each "
         "3 sequential fadd + eps + fdiv (31 cycles, built); fdiv 12/4 and the 5-cycle step are unbuilt what-ifs; "
         "'removed' is hypothetical and not the model.", direction="common-mode per token"),
    dict(id="A10", grade="assumed", statement="HBM random-row gather latency 100 ns (no constant in "
         "technology.json), charged only on index-source layers.", direction="common-mode"),
    dict(id="A11", grade="derived", statement="Power = the design's static power + the analytical point's dynamic "
         "energy per token x the critical-path aggregate rate (a derived estimate; no measured power).",
         direction="neutral"),
    dict(id="A12", grade="derived", statement="Uniform expert routing (the router trace is synthetic); experts "
         "striped over the tensor group (deterministic); reduction algorithm best per collective.",
         direction="common-mode"),
]


def build(workers=8, quick=False):
    tech = json.loads(D.TECH.read_text())
    links = D.link_consts(tech)
    clock, clock_rows = D.routed_clock()
    env = _roofline_env()
    pairs = iso_area_pairs(env)
    ctxs, designs_out = {}, {}
    for pr in pairs:
        for kind, n in (("wafer", pr["wafers"]), ("array", pr["array_dies"])):
            summary, d, pts = analytical_design(env, kind, n)
            key = f"{kind}_x{n}"
            designs_out[key] = summary
            if summary["feasible"]:
                ctxs[key] = dict(kind=kind, devices=n, name=d["name"], designs={d["name"]: d}, points=pts,
                                 tensor_group=d["topology"]["tensor_group"])
    # cross-check: the published analytical artifact at the counts it emits
    published = {q["design"]: q for q in json.loads(D.V41_POINTS.read_text()) if q["batch_size"] == 1}
    xcheck = []
    for kind, n in [("wafer", w) for w in WAFER_COUNTS] + [("array", 188)] + \
                   [("array", pr["nearest_dies"]) for pr in pairs]:
        s, d, pts = analytical_design(env, kind, n)
        pub = published.get(d["name"])
        xcheck.append(dict(design=d["name"], regenerated_per_user_b1=pts[0]["per_user_tokens_s"] if pts else None,
                           published_per_user_b1=pub["per_user_tokens_s"] if pub else None,
                           equal=bool(pub and pts and math.isclose(pub["per_user_tokens_s"],
                                                                     pts[0]["per_user_tokens_s"], rel_tol=1e-9))))
        if kind == "array" and n != 188 and s["feasible"]:
            ctxs.setdefault(f"array_x{n}", dict(kind=kind, devices=n, name=d["name"], designs={d["name"]: d},
                                                points=pts, tensor_group=d["topology"]["tensor_group"]))
            designs_out.setdefault(f"array_x{n}", s)
    floors = dict(wafer=minimum_devices(env, "wafer"), array=minimum_devices(env, "array"))

    wf = wafer_fabric_variants(tech, clock)
    svs = SINKHORN_VARIANTS if not quick else SINKHORN_VARIANTS[:1] + SINKHORN_VARIANTS[-1:]
    jobs = []
    for pr in pairs:
        for key, variants in ((f"wafer_x{pr['wafers']}", wf if not quick else wf[:1] + wf[-1:]),
                              (f"array_x{pr['array_dies']}", ARRAY_LINK_VARIANTS if not quick else ARRAY_LINK_VARIANTS[:1])):
            if key not in ctxs:
                continue
            for sv in svs:
                for fv in variants:
                    jobs.append(dict(key=key, sinkhorn=sv, fabric=fv))
    # sensitivities at the control fabrics, built divider and Sinkhorn removed
    sens_jobs = []
    if not quick:
        for pr in pairs:
            wk, ak = f"wafer_x{pr['wafers']}", f"array_x{pr['array_dies']}"
            for sv in (SINKHORN_VARIANTS[0], SINKHORN_VARIANTS[-1]):
                for key, fv in ((wk, wf[0]), (ak, ARRAY_LINK_VARIANTS[0]), (wk, wf[-1])):
                    if key not in ctxs:
                        continue
                    sens_jobs.append(dict(key=key, sinkhorn=sv, fabric=fv, layout="uniform", tag="layout_uniform"))
                    sens_jobs.append(dict(key=key, sinkhorn=sv, fabric=fv, extra=dict(lanes_from="analytical"),
                                          tag="lanes_from_analytical"))
                    sens_jobs.append(dict(key=key, sinkhorn=sv, fabric=fv, extra=dict(hbm_gather_s=300e-9),
                                          tag="hbm_gather_300ns"))
                    sens_jobs.append(dict(key=key, sinkhorn=sv, fabric=fv, extra=dict(chaining=False),
                                          tag="no_chaining"))
                    if key == wk:
                        for sh in (40e-9, 250e-9):
                            sens_jobs.append(dict(key=key, sinkhorn=sv, fabric=fv, serdes_hop_s=sh,
                                                  tag=f"wafer_serdes_{sh * 1e9:.0f}ns"))
                    if key == ak and wk in ctxs:
                        ratio = designs_out[wk]["hbm_stacks_total"] / designs_out[ak]["hbm_stacks_total"]
                        sens_jobs.append(dict(key=key, sinkhorn=sv, fabric=fv, iso_hbm=ratio,
                                              tag="array_iso_hbm_stacks"))
        # the no-rounding array counts (the user's 113/170/227/681) at the control links
        for pr in pairs:
            k = f"array_x{pr['nearest_dies']}"
            if k in ctxs and pr["nearest_dies"] != pr["array_dies"]:
                for sv in (SINKHORN_VARIANTS[0], SINKHORN_VARIANTS[-1]):
                    sens_jobs.append(dict(key=k, sinkhorn=sv, fabric=ARRAY_LINK_VARIANTS[0], tag="array_nearest_dies"))

    with ProcessPoolExecutor(workers, initializer=_init, initargs=(ctxs, clock, links)) as ex:
        results = list(ex.map(_job, jobs + sens_jobs, chunksize=1))
    main_res = results[:len(jobs)]
    sens_res = results[len(jobs):]

    def lookup(key, sv, fv, res=main_res):
        for r in res:
            if r["job"]["key"] == key and r["job"]["sinkhorn"] == sv and r["job"]["fabric"] == fv:
                return r["result"]
        return None

    # grid rows
    grid = []
    for r in main_res:
        j, res = r["job"], r["result"]
        ctx = ctxs[j["key"]]
        ds = designs_out[j["key"]]
        b = res["best_b1"]
        row = dict(point=j["key"], kind=ctx["kind"], sinkhorn=j["sinkhorn"], fabric=j["fabric"],
                   silicon_mm2=ds["silicon_mm2"], best_b1=slim(b), best_b64=slim(res["best_b64"]),
                   best_aggregate_b4096=slim(res["best_aggregate_b4096"]),
                   configs_evaluated=res["configs"], groups_refused=res["refused"])
        if b:
            row.update(metrics(ds, res))
        grid.append(row)

    # comparisons: every wafer fabric vs the array at each of its link variants
    comps = []
    for pr in pairs:
        wk, ak = f"wafer_x{pr['wafers']}", f"array_x{pr['array_dies']}"
        if wk not in ctxs or ak not in ctxs:
            comps.append(dict(wafers=pr["wafers"], refused=designs_out.get(wk, {}).get("reasons")))
            continue
        for sv in svs:
            for fv in (wf if not quick else wf[:1] + wf[-1:]):
                w = lookup(wk, sv["id"], fv["id"])
                for av in (ARRAY_LINK_VARIANTS if not quick else ARRAY_LINK_VARIANTS[:1]):
                    a = lookup(ak, sv["id"], av["id"])
                    if not (w and a and w["best_b1"] and a["best_b1"]):
                        continue
                    wb, ab = w["best_b1"], a["best_b1"]
                    wm, am = metrics(designs_out[wk], w), metrics(designs_out[ak], a)
                    comps.append(dict(
                        wafers=pr["wafers"], array_dies=pr["array_dies"], sinkhorn=sv["id"], wafer_fabric=fv["id"],
                        wafer_hop_ns=fv["hop_s"] * 1e9, array_links=av["id"],
                        wafer=wm, array=am,
                        wafer_b1=wb["tok_s_user_b1"], array_b1=ab["tok_s_user_b1"],
                        ratio_b1=wb["tok_s_user_b1"] / ab["tok_s_user_b1"],
                        ratio_b64=wm["tok_s_user_b64"] / am["tok_s_user_b64"],
                        ratio_b4096_aggregate=wm["aggregate_tok_s_b4096"] / am["aggregate_tok_s_b4096"],
                        ratio_b64_fixed_b1_config=wb["tok_s_user_b64"] / ab["tok_s_user_b64"],
                        ratio_b4096_fixed_b1_config=wb["aggregate_tok_s_b4096"] / ab["aggregate_tok_s_b4096"],
                        ratio_tok_s_per_w_b4096=wm["tok_s_per_w_b4096_derived"] / am["tok_s_per_w_b4096_derived"]))

    # crossover field-hop latency per pair x Sinkhorn variant, against the array at its point and fast links
    cross = []
    if not quick:
        cjobs = []
        for pr in pairs:
            wk, ak = f"wafer_x{pr['wafers']}", f"array_x{pr['array_dies']}"
            if wk not in ctxs or ak not in ctxs:
                continue
            for sv in svs:
                for av in (ARRAY_LINK_VARIANTS[0], ARRAY_LINK_VARIANTS[1]):
                    a = lookup(ak, sv["id"], av["id"])
                    cjobs.append(dict(key=wk, sinkhorn=sv, target=a["best_b1"]["tok_s_user_b1"], against=av["id"]))
        with ProcessPoolExecutor(workers, initializer=_init, initargs=(ctxs, clock, links)) as ex:
            cross = list(ex.map(_cross_job, cjobs, chunksize=1))

    sens = []
    for r in sens_res:
        j, res = r["job"], r["result"]
        base = lookup(j["key"], j["sinkhorn"], j["fabric"])
        sens.append(dict(point=j["key"], sinkhorn=j["sinkhorn"], fabric=j["fabric"], sensitivity=j["tag"],
                         metrics=metrics(designs_out[j["key"]], res) if res["best_b1"] else None,
                         base=metrics(designs_out[j["key"]], base) if base and base["best_b1"] else None))

    def sget(key, sv, fv, tag):
        for x in sens:
            if (x["point"], x["sinkhorn"], x["fabric"], x["sensitivity"]) == (key, sv, fv, tag):
                if x["metrics"] is None:
                    raise ValueError(f"no feasible configuration for {key} under {tag}")
                return x["metrics"]
        return None
    sens_ratios = []
    if not quick:
        tags = sorted({x["sensitivity"] for x in sens})
        for pr in pairs:
            wk, ak = f"wafer_x{pr['wafers']}", f"array_x{pr['array_dies']}"
            if wk not in ctxs or ak not in ctxs:
                continue
            for sv in (SINKHORN_VARIANTS[0], SINKHORN_VARIANTS[-1]):
                for fv in (wf[0], wf[-1]):
                    wbase = metrics(designs_out[wk], lookup(wk, sv["id"], fv["id"]))
                    abase = metrics(designs_out[ak], lookup(ak, sv["id"], ARRAY_LINK_VARIANTS[0]["id"]))
                    for tag in ["baseline"] + tags:
                        try:
                            if tag == "array_nearest_dies":
                                nk = f"array_x{pr['nearest_dies']}"
                                a = sget(nk, sv["id"], ARRAY_LINK_VARIANTS[0]["id"], tag)
                                w = wbase
                            else:
                                w = sget(wk, sv["id"], fv["id"], tag) or wbase
                                a = sget(ak, sv["id"], ARRAY_LINK_VARIANTS[0]["id"], tag) or abase
                        except ValueError as e:
                            sens_ratios.append(dict(wafers=pr["wafers"], sinkhorn=sv["id"], wafer_fabric=fv["id"],
                                                    sensitivity=tag, infeasible=str(e)))
                            continue
                        if tag != "baseline" and w is wbase and a is abase:
                            continue
                        if not (w and a):
                            continue
                        sens_ratios.append(dict(
                            wafers=pr["wafers"], sinkhorn=sv["id"], wafer_fabric=fv["id"], sensitivity=tag,
                            wafer_b1=w["tok_s_user_b1"], array_b1=a["tok_s_user_b1"],
                            ratio_b1=w["tok_s_user_b1"] / a["tok_s_user_b1"],
                            ratio_b64=w["tok_s_user_b64"] / a["tok_s_user_b64"],
                            ratio_b4096_aggregate=w["aggregate_tok_s_b4096"] / a["aggregate_tok_s_b4096"]))

    rec = dict(schema=SCHEMA, tool="tools/wafer_vs_array_study.py", study=STUDY, context_tokens=CONTEXT,
               claim="Even tightly integrated on a wafer, V4.1 decode is not faster than the array at equal "
                     "silicon, so the wafer (much harder to build) should be rejected.",
               clock=dict(hz=clock, blocks=clock_rows), params_default=asdict(D.Params()),
               layer_weight_fraction=layer_fraction(), links=links,
               axes=dict(sinkhorn=[dict(v, chain_us_per_token_b1=sinkhorn_chain_us(v, clock)) for v in svs],
                         wafer_fabric=[dict(v, hop_ns=v["hop_s"] * 1e9) for v in wf],
                         array_links=ARRAY_LINK_VARIANTS),
               minimum_devices_to_hold_design=floors, pairs=pairs, designs=designs_out,
               analytical_cross_check=xcheck, grid=grid, comparisons=comps, crossover=cross, sensitivities=sens,
               sensitivity_ratios=sens_ratios,
               assumptions=ASSUMPTIONS)
    rec["summary"] = summarize(rec)
    return rec


def summarize(rec):
    """The headline table (built divider, control fabrics) and the verdict's conditions."""
    comps = rec["comparisons"]

    def c(w, s, f, a="links_point"):
        for x in comps:
            if x.get("wafers") == w and x.get("sinkhorn") == s and x.get("wafer_fabric") == f and x.get("array_links") == a:
                return x
        return None
    out = dict(headline=[], best_wafer_ratio_b1=None, conditions=[])
    best = None
    for x in comps:
        if "ratio_b1" in x and x["array_links"] == "links_point":
            if best is None or x["ratio_b1"] > best["ratio_b1"]:
                best = x
    out["best_wafer_ratio_b1"] = best
    for w in WAFER_COUNTS:
        h = c(w, "fdiv31_built", "mesh_125")
        if h:
            out["headline"].append(h)
    wins = [x for x in comps if "ratio_b1" in x and x["ratio_b1"] > 1.0 and x["array_links"] == "links_point"]
    out["wafer_wins_b1_cells"] = len(wins)
    out["cells_b1"] = sum(1 for x in comps if "ratio_b1" in x and x["array_links"] == "links_point")
    for cr in rec["crossover"]:
        out["conditions"].append(dict(wafers=cr["key"], sinkhorn=cr["sinkhorn"], against=cr["against"],
                                      wafer_matches_array_b1_at_field_hop_ns_at_most=cr["max_field_hop_ns"]))
    # flat, id-keyed rows: what docs/WAFER_VS_ARRAY_ISO_AREA.md binds its figures to
    cells = []
    for x in comps:
        if "ratio_b1" not in x or x["array_links"] != "links_point":
            continue
        w, a = x["wafer"], x["array"]
        cells.append(dict(id=f"W{x['wafers']}.{x['sinkhorn']}.{x['wafer_fabric']}",
                          wafer_b1=w["tok_s_user_b1"], array_b1=a["tok_s_user_b1"], ratio_b1=x["ratio_b1"],
                          wafer_b64=w["tok_s_user_b64"], array_b64=a["tok_s_user_b64"], ratio_b64=x["ratio_b64"],
                          wafer_agg_b4096=w["aggregate_tok_s_b4096"], array_agg_b4096=a["aggregate_tok_s_b4096"],
                          ratio_b4096=x["ratio_b4096_aggregate"],
                          wafer_tok_s_mm2_b4096=w["tok_s_per_mm2_b4096"], array_tok_s_mm2_b4096=a["tok_s_per_mm2_b4096"],
                          wafer_power_w_b4096=w["power_w_b4096_derived"], array_power_w_b4096=a["power_w_b4096_derived"],
                          wafer_tok_s_w_b4096=w["tok_s_per_w_b4096_derived"],
                          array_tok_s_w_b4096=a["tok_s_per_w_b4096_derived"],
                          ratio_tok_s_w_b4096=x["ratio_tok_s_per_w_b4096"],
                          wafer_config_b1=w["config_b1"], array_config_b1=a["config_b1"],
                          wafer_cp_breakdown_us_b1=w["breakdown_us_b1"], array_cp_breakdown_us_b1=a["breakdown_us_b1"]))
    out["cells"] = cells
    out["crossover_ns"] = [dict(id=f"{cr['key'].replace('wafer_x', 'W')}.{cr['sinkhorn']}.{cr['against']}",
                                ns=cr["max_field_hop_ns"]) for cr in rec["crossover"]]
    out["sensitivity_cells"] = [dict(id=f"W{x['wafers']}.{x['sinkhorn']}.{x['wafer_fabric']}.{x['sensitivity']}",
                                     **{k: x.get(k) for k in ("ratio_b1", "ratio_b64", "ratio_b4096_aggregate",
                                                              "infeasible")})
                                for x in rec.get("sensitivity_ratios", [])]
    ctl = [c_ for c_ in cells if c_["id"].endswith(".mesh_125") and ".fdiv31_built." in c_["id"]]
    fast = [c_ for c_ in cells if c_["id"].split(".")[-1].startswith("express")]
    b1r = [c_["ratio_b1"] for c_ in cells]
    out["extremes"] = dict(
        control_ratio_b1_min=min(c_["ratio_b1"] for c_ in ctl), control_ratio_b1_max=max(c_["ratio_b1"] for c_ in ctl),
        all_ratio_b1_max=max(b1r),
        express_ratio_b1_max=max(c_["ratio_b1"] for c_ in fast),
        builtdiv_express_ratio_b1_max=max(c_["ratio_b1"] for c_ in fast if ".fdiv31_built." in c_["id"]),
        ratio_b64_min=min(c_["ratio_b64"] for c_ in cells), ratio_b64_max=max(c_["ratio_b64"] for c_ in cells),
        ratio_b4096_min=min(c_["ratio_b4096"] for c_ in cells), ratio_b4096_max=max(c_["ratio_b4096"] for c_ in cells),
        crossover_ns_vs_point_min=min(cr["max_field_hop_ns"] for cr in rec["crossover"]
                                      if cr["against"] == "links_point" and cr["max_field_hop_ns"] is not None),
        crossover_ns_vs_point_max=max(cr["max_field_hop_ns"] for cr in rec["crossover"]
                                      if cr["against"] == "links_point" and cr["max_field_hop_ns"] is not None),
        crossover_ns_vs_low_min=min(cr["max_field_hop_ns"] for cr in rec["crossover"]
                                    if cr["against"] == "links_low" and cr["max_field_hop_ns"] is not None),
        crossover_ns_vs_low_max=max(cr["max_field_hop_ns"] for cr in rec["crossover"]
                                    if cr["against"] == "links_low" and cr["max_field_hop_ns"] is not None),
    ) if cells and rec["crossover"] else {}
    return out


def print_summary(rec):
    print(f"clock {rec['clock']['hz'] / 1e9:.4f} GHz; floors {rec['minimum_devices_to_hold_design']}")
    for k, d in rec["designs"].items():
        print(f"  {k:12s} {d['silicon_mm2']:9.0f} mm2 feasible={d['feasible']} rom={d['rom_mm2_total']:8.0f} "
              f"compute={d['compute_mm2_total']:8.0f} stacks={d['hbm_stacks_total']} {d['reasons']}")
    for x in rec["comparisons"]:
        if "ratio_b1" in x and x["array_links"] == "links_point":
            print(f"  W{x['wafers']:<2} {x['sinkhorn']:13s} {x['wafer_fabric']:22s} wafer {x['wafer_b1']:8.0f} array "
                  f"{x['array_b1']:8.0f} b1 {x['ratio_b1']:.3f} b64 {x['ratio_b64']:.3f} "
                  f"b4096agg {x['ratio_b4096_aggregate']:.3f} tok/J {x['ratio_tok_s_per_w_b4096']:.3f}")
    for cr in rec["crossover"]:
        print(f"  crossover {cr['key']:10s} {cr['sinkhorn']:13s} vs {cr['against']:11s}: "
              f"{cr['max_field_hop_ns']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    rec = build(args.workers, args.quick)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rec, indent=1) + "\n")
    print_summary(rec)


if __name__ == "__main__":
    main()
