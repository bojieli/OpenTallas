"""Opt-in real clock-region landings for the as-built binder.

The regional clock report's table identifies PHYSICAL port hops, not lane
endpoints. This adapter puts the landing inside the receiving partition, exports
the sender clock beside its bus, and exposes ready/fault (never dropped). It
requires declared clock/status pins and uniform type masks; it does not invent
placement, waive clocks, or silently split hardened types.
"""
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


_RING_PLAN = {}
LAND_SLOTS_SCHEMA = "land_slots/3"   # /2 ring_start; /3 explicitly typed origin_start


def ring_taps(plan, tn):
    """[(x, y)] of the taps whose wavefront relays drive rst_n_t<i> in type tn (type frame): the index space a ring
    reset node rst_n_t<i> refers to.  A plan clock.taps list of kind 'core' entries (S81 12.8a plan-defined core
    clock entries) is NOT that index space: the reset tree numbers its relays over schema.tap_grid
    (reset_tree._taps), so such types use the reset tree's own taps.  Every other type keeps clock.taps."""
    taps = plan["partition_types"][tn].get("clock", {}).get("taps", [])
    if not any(x.get("kind") == "core" for x in taps):
        return [tuple(x["xy"]) for x in taps]
    import schema
    import reset_tree as RT
    e = _RING_PLAN.get(id(plan))
    if e is None or e[0] is not plan:
        e = _RING_PLAN[id(plan)] = (plan, schema.Plan(plan))
    return [(x, y) for _, x, y in RT._taps(e[1], tn)]


def network_lane_cycles(plan):
    """Exact nominal data cycles from source-bound physical forwarded edges.

    Monitor edges add boot time only. Native fixed_cycles is left intact.
    The endpoint names are checked, so arbitrary clock metadata cannot price
    a functional lane or silently add a second copy of a physical crossing.
    """
    net=plan.get("clock",{}).get("landing_network")
    if not net:return {}
    ca=net.get("data_cycles_per_crossing")=="count_aligned"
    if not ca and net.get("data_cycles_per_crossing")!=3:raise LandingError("clock landing network requires the proved nominal +3 contract")
    if ca and not isinstance(net.get("count_aligned_cycles"),dict):raise LandingError("count-aligned landing network needs per-crossing count_aligned_cycles")
    ports={p["id"]:p for p in plan["ports"]};owners=defaultdict(list)
    for lane in plan["lanes"]:
        for pid in lane["ports"]:owners[pid].append(lane["id"])
    out=defaultdict(int);seen=set()
    for edge in net.get("edges",[]):
        if not edge["id"].startswith("cland_clk__"):continue
        pid=edge["id"][len("cland_clk__"):];p=ports.get(pid)
        if p is None or pid in seen:raise LandingError("stale/duplicate functional clock landing "+pid)
        seen.add(pid)
        expected=dict(src=dict(part=p["src"]["part"],bus="fclk_out_"+p["src"]["bus"]),dst=dict(part=p["dst"]["part"],bus="fclk_in_"+p["dst"]["bus"]))
        if edge.get("kind")!="clock" or any(edge[k]!=expected[k] for k in ("src","dst")):
            raise LandingError("clock landing physical endpoints changed "+pid)
        if len(owners[pid])!=1:raise LandingError("clock landing must identify exactly one logical lane "+pid)
        if ca and pid not in net["count_aligned_cycles"]:raise LandingError("count-aligned crossing has no planned latency "+pid)
        out[owners[pid][0]]+=int(net["count_aligned_cycles"][pid]) if ca else 3
    return dict(out)


START_PIN_IN = "cland_tstart_in"     # == count_align_bind.START_PIN_IN
START_PIN_OUT = "cland_tstart_out"   # == count_align_bind.START_PIN_OUT


def start_net_name(x):
    """die-level start-stage net name part of a region (== start_stage_emit.sv_name)"""
    return re.sub(r"\W", "_", x)


def start_pins(plan, ca):
    """START-TREE compose slice (DIE-HEAD-11): the dedicated start pins of a count-aligned table with start_ports.
    -> dict(ports={pid: dict(src, dst, src_part, dst_part)}, type_pins={type: {pin: dir}}, plan_ports=[real -> real],
            die_inputs=[real -> stage: top output rs_<region>], die_outputs=[stage -> real: top input pst_<region>]).
    A start port's real ends are its launch partition (src region origin) and capture partition (dst region origin); a
    virtual region ('st:' / regions[].virtual) is a die-level stage (start_stage_emit.py), never a partition."""
    parts = {p["name"]: p for p in plan["partitions"]}
    reg = ca["regions"]

    def real(x):
        if x not in reg:
            raise LandingError(f"start port end {x}: not a start-tree region")
        return not str(x).startswith("st:")
    ports, tp = {}, defaultdict(dict)
    plan_ports, die_in, die_out = [], [], []
    for pid, c in sorted(ca["start_ports"].items()):
        s_real, d_real = real(c["src"]), real(c["dst"])
        sp = (c.get("src_part") or c.get("launch_part")) if s_real else None
        dp = (c.get("dst_part") or c.get("capture_part")) if d_real else None
        for what, x, q in (("launch", c["src"], sp), ("capture", c["dst"], dp)):
            if q is not None and q not in parts:
                raise LandingError(f"start port {pid}: {what} partition {q} is not a plan partition")
            if (x == c["src"] and s_real or x == c["dst"] and d_real) and q is None:
                raise LandingError(f"start port {pid}: real region {x} has no {what} partition")
            org = reg[x].get("origin_part")
            if q is not None and org is not None and q != org:
                raise LandingError(f"start port {pid}: {what} partition {q} is not the origin {org} of {x}")
        ports[pid] = dict(src=c["src"], dst=c["dst"], src_part=sp, dst_part=dp)
        if sp:
            tp[parts[sp]["type"]][START_PIN_OUT] = "out"
        if dp:
            tp[parts[dp]["type"]][START_PIN_IN] = "in"
        if sp and dp:
            plan_ports.append(dict(port=pid, src_part=sp, dst_part=dp))
        elif sp:
            die_in.append(dict(port=pid, src_part=sp, net=f"rs_{start_net_name(c['src'])}", stage_region=c["dst"]))
        elif dp:
            die_out.append(dict(port=pid, dst_part=dp, net=f"pst_{start_net_name(c['dst'])}", stage_region=c["src"]))
    # a die-level stage reads one rs_<region> net per real parent region (fan-out inside the stage module)
    seen = {}
    for e in die_in:
        if seen.setdefault(e["net"], e["src_part"]) != e["src_part"]:
            raise LandingError(f"start net {e['net']}: two launch partitions")
    return dict(ports=ports, type_pins={k: dict(v) for k, v in sorted(tp.items())}, plan_ports=plan_ports,
                die_inputs=die_in, die_outputs=die_out, die_input_nets=sorted(seen),
                pins=dict(input=START_PIN_IN, output=START_PIN_OUT))


def requirements(plan, table):
    """Publish concrete type-mask/pin/latency work before changing a plan.

    Pin faces/windows are copied as placement references only. A scalar clock
    pin still needs a legal track and a status pin needs a destination; copying
    the data window does not constitute a physical placement approval.
    """
    parts = {p["name"]: p for p in plan["partitions"]}
    types = plan["partition_types"]
    ports = {p["id"]: p for p in plan["ports"]}
    masks = {pn: dict(inputs=set(), outputs=set()) for pn in parts}
    pin_refs, lanes = [], defaultdict(int)
    ca = table.get("count_aligned")
    for r in table["ports"]:
        p = ports[r["port"]]
        sp, sb, dp, db = p["src"]["part"], p["src"]["bus"], p["dst"]["part"], p["dst"]["bus"]
        if (sp, dp, int(p["width"])) != (r["src"], r["dst"], int(r["width"])):
            raise LandingError(f"stale clock landing endpoints/width on {r['port']}")
        masks[sp]["outputs"].add(sb)
        masks[dp]["inputs"].add(db)
        cyc = ca_cycles(ca, r["port"])
        lanes[r["lane"]] += cyc
        pin_refs.append(dict(port=r["port"], lane=r["lane"], src=sp, dst=dp,
                             src_bus=sb, dst_bus=db, width=p["width"],
                             required_src_pin=f"fclk_out_{sb}",
                             required_dst_pins=[f"fclk_in_{db}", f"landing_ready_{db}", f"landing_fault_{db}"]
                             + ([f"cland_fstart_in_{db}"] if ca else []),
                             **({"required_src_start_pin": f"cland_fstart_out_{sb}"} if ca else {}),
                             extra_cycles=cyc))
    cohorts = defaultdict(dict)
    for pn, p in parts.items():
        mask = {k: sorted(v) for k, v in masks[pn].items()}
        key = json.dumps(mask, sort_keys=True)
        cohorts[p["type"]].setdefault(key, []).append(pn)
    groups = {}
    row_by_sink = {(r["dst"], r["dst_bus"]): r for r in pin_refs}
    for tn, cs in cohorts.items():
        groups[tn] = [dict(mask=json.loads(k), instances=ps,
                          proposed_type=tn if len(cs) == 1 else tn + "__cl" + hashlib.sha256(k.encode()).hexdigest()[:8])
                      for k, ps in sorted(cs.items())]
        for g in groups[tn]:
            rows = [row_by_sink[(g["instances"][0], b)] for b in g["mask"]["inputs"]]
            g["added_live_data_storage_flops"] = sum(5 * (int(r["width"]) + 1) for r in rows)
            g["control_flops_upper_estimate"] = sum(73 + 4 * ((int(r["width"]) + 64) // 64) for r in rows)
            g["padded_data_storage_flops_upper_estimate"] = sum(5 * 64 * ((int(r["width"]) + 64) // 64) for r in rows)
            g["clock_sink_addition_upper_estimate"] = g["added_live_data_storage_flops"] + g["control_flops_upper_estimate"]
            g["placement_required"] = [dict(bus=r["dst_bus"], ring_instance=f"u_cland_{r['dst_bus']}.u_ring",
                                            data_storage_flops=5 * (int(r["width"]) + 1),
                                            write_clock_pin=f"fclk_in_{r['dst_bus']}", read_clock="clk",
                                            window="received bus face; actual legal sites/tracks NOT assigned") for r in rows]
    return dict(schema="opentallas.clock_landing_requirements.v1", implemented=False,
                source_table_sha256=hashlib.sha256(json.dumps(table, sort_keys=True).encode()).hexdigest(),
                crossings=len(pin_refs),
                required_new_scalar_pins=len({(r["src"], r["src_bus"]) for r in pin_refs}) + 3 * len(pin_refs),
                added_live_data_storage_flops=sum(5 * (int(r["width"]) + 1) for r in pin_refs),
                type_count_before=len(types), type_count_after=sum(map(len, groups.values())),
                split_types={tn: g for tn, g in groups.items() if len(g) > 1},
                cohorts=groups, ports=pin_refs, lane_added_cycles=dict(sorted(lanes.items())),
                nominal_added_cycles_per_crossing="count_aligned (per crossing)" if ca else 3,
                pending=["reserve forwarded-clock and observed status pin tracks", "split nonuniform landing masks",
                         "update lane/R8/calendar price", "emit actual landing RTL", "ring window STA and token pass"])


class LandingError(ValueError):
    pass


# count-aligned intra-region start relay: tx flop (origin partition) + rx flop (relay partition); must equal
# count_align_bind.RELAY_STAGES, which shifts the K of the relay partition's crossings by the same counts
RELAY_STAGES = 2
# Strap inputs the strap-form origin declares SCALAR (`input wire strap_ca_efall`, no [0:0]); every other strap is a
# vector.  gen_phys.strap_pin_sites names these pins without a bit index (FLOW-GEN-1 10-28, DIE-HEAD-9 bug 1).
SCALAR_STRAPS = frozenset({"strap_ca_efall", "strap_ca_root"})


def ca_cycles(ca, pid):
    """Added data cycles of one landed crossing: the proved old-ring +3, or (count-aligned form, MESO-INTEG-1) the
    plan's per-crossing schedule latency K + 1 + n_dst - n_src (count_align_bind.py)."""
    if not ca:
        return 3
    c = ca["ports"].get(pid)
    if c is None:
        raise LandingError(f"count-aligned landing {pid}: no K/DEPTH/latency in the bind table")
    return int(c["sched_lat"])


def ident(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def gate_observer(body,spec):
    """Bind the two real one-bit mission/observation inputs, never new IO."""
    module=re.escape(spec["module"])
    pattern=re.compile(r"(?m)^\s*"+module+r"(?:\s*#\([^;]*?\))?\s+(\w+)\s*\(\n",re.S)
    matches=[m for m in pattern.finditer(body) if m.group(1).endswith(spec["instance_suffix"])]
    if len(matches)!=1:raise LandingError(f"clock landing observer: expected one {spec['module']}.{spec['instance_suffix']}, found{len(matches)}")
    m=matches[0];end=body.find("\n    );",m.end())
    if end<0:raise LandingError("clock landing observer: instance terminator not found")
    block=body[m.start():end]
    for port,op,signal in ((spec["fault_port"],"|","cland_up_fault"),(spec["ready_port"],"&","cland_up_ready")):
        hits=list(re.finditer(r"\."+re.escape(port)+r"\s*\(",block))
        if len(hits)!=1:raise LandingError(f"clock landing observer: expected one exact input {port}")
        start=hits[0].end();depth=1;i=start
        while i<len(block) and depth:
            depth+=(block[i]=="(")-(block[i]==")");i+=1
        if depth:raise LandingError(f"clock landing observer: unbalanced input {port}")
        old=block[start:i-1].strip()
        if not old:raise LandingError(f"clock landing observer: empty input {port}")
        block=block[:start]+f"(({old}) {op} {signal})"+block[i-1:]
    return body[:m.start()]+block+body[end:]


def expand_station_types(binder,table):
    """Keep real native OUT stations enabled after phase/clock type splits.

    The compose tool explicitly records each current type's prelanding base.
    Phase type names preserve that original family as a complete prefix token.
    Native annotate still checks the actual source-station count against each
    lane's priced fixed_cycles; this does not exempt a station or add cycles.
    """
    selected=set(binder.ab.get("internal_stations_types",[]))
    if not selected:return
    lineage=table.get("collector",{}).get("types",{})
    out=set();represented=set()
    for tn in binder.types:
        base=lineage.get(tn,{}).get("base_type",tn)
        matches={s for s in selected if tn==s or base==s or base.startswith(s+"_")}
        if matches:out.add(tn);represented.update(matches)
    missing=selected-represented
    if missing:raise LandingError(f"clock landing native station families have no actual cohort: {sorted(missing)}")
    binder.ab["internal_stations_types"]=sorted(out)


class Landings:
    def __init__(self, plan, table, *, require_geometry=True, ca_variants=False):
        """ca_variants (MESO-STRAP-1, LEC only): count-aligned PARAMETER form without the TYPE_SPLIT stop, so
        type_rtl(..., inst=<partition>) can emit one copy's parameter wrapper (the LEC reference of a strap master)."""
        self.plan = plan
        self.ca_variants = ca_variants
        self.collector = table.get("collector")
        # monitor="region" (opt-in, DIE-HEAD-3): the dataflow monitor plus same-region status links (registered ctl
        # pins on the region clock, no ring) from clock_landing_plan.compose(monitor="region").
        self.region_monitor = bool(self.collector) and self.collector.get("monitor", "reset") == "region"
        self.dataflow = bool(self.collector) and self.collector.get("monitor", "reset") in ("dataflow", "region")
        if self.collector and self.collector.get("monitor", "reset") not in ("reset", "dataflow", "region"):
            raise LandingError(f"clock landing: unknown monitor mode {self.collector.get('monitor')}")
        self.parts = {p["name"]: p for p in plan["partitions"]}
        self.types = plan["partition_types"]
        ports = {p["id"]: p for p in plan["ports"]}
        self.rows = []
        self.region = {}
        self.emitted_types = set()
        self.forwarded_clock_only_inputs = {}
        self.emitted_top = False
        self.reset_placements = {}
        for pn, p in self.parts.items():
            w, h = self.types[p["type"]]["outline_um"]
            x, y = p["origin_um"][0] + w / 2, p["origin_um"][1] + h / 2
            candidates = [r["tag"] for r in table["regions"]
                          if r["box_um"][0] <= x < r["box_um"][2]
                          and r["box_um"][1] <= y < r["box_um"][3]]
            if len(candidates) != 1:
                raise LandingError(f"clock landing {pn}: expected one whole-partition region")
            self.region[pn] = candidates[0]
        self.ins = defaultdict(dict)
        self.outs = defaultdict(set)
        self.ca = table.get("count_aligned")
        # MESO-STRAP-1 (OWNER 12.15a, opt-in: count_aligned.strap_form): K / PAD / EDGE_FALL / tree select / root become
        # strap_ca_* input pins of ONE design per type, tied at the parent to count_align_bind.strap_ties() values
        self.strap = None
        if self.ca and self.ca.get("strap_form"):
            import count_align_bind as CAB
            self.strap = CAB.strap_ties(self.ca, plan)
        # START-TREE compose slice (opt-in: count_aligned.start_ports): dedicated start pins, see _start_pins()
        self.tstart = self._start_pins(plan) if self.ca and self.ca.get("start_ports") else None
        seen = set()
        for r in table["ports"]:
            pid = r["port"]
            if pid in seen:
                raise LandingError(f"duplicate clock landing port {pid}")
            seen.add(pid)
            if pid not in ports:
                raise LandingError(f"clock landing has no physical plan port {pid}")
            p = ports[pid]
            if p.get("kind", "data") not in ("data", "ctl"):
                raise LandingError(f"clock landing {pid}: reset/clock needs its own contract")
            sp, sb = p["src"]["part"], p["src"]["bus"]
            dp, db = p["dst"]["part"], p["dst"]["bus"]
            if (sp, dp, int(p["width"])) != (r["src"], r["dst"], int(r["width"])):
                raise LandingError(f"stale clock landing endpoints/width on {pid}")
            if r["src_region"] == r["dst_region"]:
                raise LandingError(f"clock landing {pid} stays in one region")
            for part, region in ((sp, r["src_region"]), (dp, r["dst_region"])):
                if part not in self.parts:
                    raise LandingError(f"clock landing {pid}: non-partition endpoint {part}")
                if part in self.region and self.region[part] != region:
                    raise LandingError(f"clock landing region conflict for {part}")
                self.region[part] = region
            if db in self.ins[dp]:
                raise LandingError(f"two clock landings drive {dp}.{db}")
            # The ring form is a per-row choice (MESO-COUNT-1 may swap in a count-aligned variant): a sidecar row may name
            # ring_module + ring_params (+ ring_ports for extra receiver pins); the default is today's ring.
            rmod = r.get("ring_module", "ot_dp_clk_landing")
            if not re.fullmatch(r"ot_dp_clk_landing\w*", rmod):
                raise LandingError(f"clock landing {pid}: ring_module {rmod} is not an ot_dp_clk_landing variant")
            rpar, rports = dict(r.get("ring_params", {})), dict(r.get("ring_ports", {}))
            for k, v in list(rpar.items()) + list(rports.items()):
                if not re.fullmatch(r"[A-Za-z_]\w*", str(k)) or not re.fullmatch(r"[\w'\[\]:]+", str(v)):
                    raise LandingError(f"clock landing {pid}: bad ring_params/ring_ports entry {k}={v}")
            if {"W", "fclk", "clk", "rst_n", "d", "q", "ready", "fault"} & (set(rpar) | set(rports)):
                raise LandingError(f"clock landing {pid}: ring_params/ring_ports may not override the bound ring pins or W")
            row = dict(r, src_bus=sb, dst_bus=db, added_cycles=3,
                       module=rmod, ring_params=rpar, ring_ports=rports,
                       ring_depth=int(rpar.get("DEPTH", 4)), ring_offset=int(rpar.get("K", 2)),
                       ring_read_registered=True)
            if self.ca:
                if "ring_module" in r or "ring_params" in r or "ring_ports" in r:
                    raise LandingError(f"clock landing {pid}: per-row ring_module/params/ports and the table "
                                       "count_aligned form are exclusive")
                c = self.ca["ports"].get(pid)
                if c is None:
                    raise LandingError(f"count-aligned landing {pid}: no K/DEPTH/latency in the bind table")
                if int(c["depth"]) not in (4, 8, 16):
                    raise LandingError(f"count-aligned landing {pid}: DEPTH {c['depth']} not 4/8/16")
                row.update(added_cycles=int(c["sched_lat"]), module="ot_dp_clk_landing_cas" if self.strap else
                           "ot_dp_clk_landing_ca", ring_depth=int(c["depth"]),
                           ring_offset=None, ring_k=int(c["K"]), start_tree_port=bool(c["tree"]))
            self.rows.append(row)
            self.ins[dp][db] = row
            self.outs[sp].add(sb)
        # All copies of a type must expose identical hardware. Re-plan a type
        # split rather than changing only the first bound replica's wrapper.
        masks = defaultdict(dict)
        for pn, p in self.parts.items():
            form = tuple((b, r["module"], tuple(sorted(r["ring_params"].items())), tuple(sorted(r["ring_ports"].items())))
                         for b, r in sorted(self.ins[pn].items()))
            mask = (tuple(sorted(self.ins[pn])), tuple(sorted(self.outs[pn])), form)
            masks[p["type"]].setdefault(mask, []).append(pn)
        bad = {tn: list(ms.values()) for tn, ms in masks.items() if len(ms) > 1}
        if bad:
            raise LandingError(f"clock landing TYPE_SPLIT required: {bad}")
        self.intra_in, self.intra_out, self.intra_links = defaultdict(set), defaultdict(set), []
        if self.region_monitor:
            self._region_links(ports)
        self.ca_type = self._count_aligned_types() if self.ca else {}
        self.by_type = {}
        for tn, ms in masks.items():
            mask = next(iter(ms))
            self.by_type[tn] = dict(inputs=mask[0], outputs=mask[1])
            if not require_geometry:
                continue
            declared = {b["name"]: b for b in self.types[tn].get("buses", [])}
            contract=self.types[tn].get("clock",{}).get("landing_contract",{})
            for pin in contract.get("pins",[]):
                declared[pin["name"]]=dict(pin,width=1,face="interior",window_um=[0,1],layers=[pin["layer"]])
            required = {f"fclk_out_{b}": "out" for b in mask[1]}
            if self.ca:
                required.update({f"cland_fstart_out_{b}": "out" for b in mask[1]})
                required.update({f"cland_fstart_in_{b}": "in" for b in mask[0]})
                cat = self.ca_type.get(tn)
                if self.tstart:
                    required.update({pin: d for pin, d in self.tstart["type_pins"].get(tn, {}).items()})
                if cat and cat["relay_tx"]:
                    required["cland_rstart_out"] = "out"
                if cat and cat["role"][0] == "relay":
                    required["cland_rstart_in"] = "in"
                if cat and cat.get("straps"):
                    # strap pins: types[].count_straps of the declared width (like id_straps: no plan bus; the parent
                    # ties each bit with its own TIEHI/TIELO next to the pin)
                    cs = {x["name"]: int(x["width"]) for x in self.types[tn].get("count_straps", [])}
                    for sp, w in cat["straps"].items():
                        if cs.get(sp) != int(w):
                            raise LandingError(f"clock landing {tn}: declare count strap {sp}[{w}] in types[].count_straps")
                        if sp in declared:
                            raise LandingError(f"clock landing {tn}.{sp}: a count strap is not a plan bus (types[].count_straps)")
            for b in mask[0]:
                required.update({f"fclk_in_{b}": "in"})
                if not self.collector:
                    required.update({f"landing_ready_{b}": "out", f"landing_fault_{b}": "out"})
            if self.dataflow:
                # monitor="dataflow" (FALLBACK-HEAD-2, opt-in): status rides each landed data crossing; every
                # pin is named by its DATA bus, so all instances of a type expose identical ports.
                info=self.collector["types"][tn]
                if sorted(info["mask"]["inputs"])!=sorted(mask[0]) or sorted(info["mask"]["outputs"])!=sorted(mask[1]):
                    raise LandingError(f"clock landing {tn}: dataflow monitor mask differs from the landed buses")
                for b in mask[1]:
                    required.update({f"cland_up_ready_{b}":"out",f"cland_up_fault_{b}":"out"})
                for b in mask[0]:
                    required.update({f"cland_dn_ready_{b}":"in",f"cland_dn_fault_{b}":"in"})
                tb=info["mask"].get("tree_bus")
                tree_outs=set(mask[1])
                if self.region_monitor:
                    ii,io=self._region_type_mask(tn,info,ms)
                    for b in ii:required.update({f"cland_dn_ready_{b}":"in",f"cland_dn_fault_{b}":"in"})
                    for b in io:required.update({f"cland_up_ready_{b}":"out",f"cland_up_fault_{b}":"out"})
                    tree_outs|=set(io)
                if (tb is None)!=bool(info["mask"].get("observer")) or (tb is not None and tb not in tree_outs):
                    raise LandingError(f"clock landing {tn}: dataflow tree bus {tb} is not one of its landed outputs")
                if not mask[0] and not self.region_monitor:
                    raise LandingError(f"clock landing {tn}: dataflow monitor needs a landed input (ring reset)")
            elif self.collector:
                info=self.collector["types"][tn]
                if info["mask"]["active"]:
                    if not info["mask"].get("observer"):
                        required.update(cland_up_ready="out",cland_up_fault="out")
                    if info["mask"]["up_seam"]:required["fclk_out_cland_up"]="out"
                    for c in info["children"]:
                        required[c["ready"]]="in";required[c["fault"]]="in"
                        if c["seam"]:required[f"fclk_in_cland_dn_{c['index']}"]="in"
            for name, direction in required.items():
                b = declared.get(name)
                if not b or b.get("dir") != direction or int(b.get("width", 0)) != 1:
                    raise LandingError(f"clock landing {tn}: declare placed scalar {direction} pin {name}")
                if not all(k in b for k in ("face", "window_um", "layers")):
                    raise LandingError(f"clock landing {tn}.{name}: missing physical pin geometry")

    def _region_links(self, ports):
        """monitor="region": the composed plan's same-region status ports cland_mon_{ready,fault}__<pid> whose pid is a
        plan port that is NOT a landed row (both ends in one clock region).  Fails closed on a half pair, a landed pid,
        a region-crossing pid or a pin name that does not follow the data bus."""
        rows = {r["port"] for r in self.rows}
        seen = defaultdict(set)
        # compose moves its cland_* pins to clock.landing_network.edges (infra edges); a hand plan may keep them as ports
        for p in list(self.plan["ports"]) + list(self.plan.get("clock", {}).get("landing_network", {}).get("edges", [])):
            m = re.fullmatch(r"cland_mon_(ready|fault)__(.+)", p["id"])
            if not m or m.group(2) in rows:
                continue
            kind, pid = m.groups()
            d = ports.get(pid)
            if d is None:
                raise LandingError(f"clock landing region monitor: {p['id']} names no plan port {pid}")
            sp, sb, dp, db = d["src"]["part"], d["src"]["bus"], d["dst"]["part"], d["dst"]["bus"]
            if (p["src"]["part"], p["src"]["bus"], p["dst"]["part"], p["dst"]["bus"]) != (sp, f"cland_up_{kind}_{sb}", dp, f"cland_dn_{kind}_{db}"):
                raise LandingError(f"clock landing region monitor: {p['id']} pins do not follow data port {pid}")
            if int(p.get("width", 1)) != 1:
                raise LandingError(f"clock landing region monitor: {p['id']} is not scalar")
            if sp not in self.parts or dp not in self.parts or self.region.get(sp) != self.region.get(dp):
                raise LandingError(f"clock landing region monitor: {pid} is not a same-region partition link")
            if db in self.ins[dp]:
                raise LandingError(f"clock landing region monitor: {dp}.{db} is both landed and same-region")
            seen[(pid, sp, sb, dp, db)].add(kind)
        for key, kinds in sorted(seen.items()):
            if kinds != {"ready", "fault"}:
                raise LandingError(f"clock landing region monitor: {key[0]} lacks a ready/fault pair")
            pid, sp, sb, dp, db = key
            self.intra_links.append(key)
            self.intra_out[sp].add(sb)
            self.intra_in[dp].add(db)

    def _region_type_mask(self, tn, info, ms):
        """Same-region monitor pins of type tn: identical on every instance and equal to the sidecar mask."""
        ii, io = info["mask"].get("intra_inputs", []), info["mask"].get("intra_outputs", [])
        for names in ms.values():
            for pn in names:
                got_i, got_o = sorted(self.intra_in[pn]), sorted(self.intra_out[pn] - self.outs[pn])
                if got_i != sorted(ii) or got_o != sorted(b for b in io if b not in self.outs[pn]):
                    raise LandingError(f"clock landing {tn}: region monitor pins of {pn} {got_i}/{got_o} differ from the sidecar {ii}/{io}")
        return sorted(ii), sorted(b for b in io if b not in set(next(iter(ms))[1]))

    def _region_reset(self, tn, key, body, logic, xy):
        """Raw (pre-START) reset for a region-monitor type WITHOUT a landed input: the nearest tap's timed wavefront
        relay copied at the same parent/depth (as the ring resets), or the delivered rst_n of a hard wrapper."""
        info = self.collector["types"][key]
        if (info.get("tree") or {}).get("hard"):
            if not re.search(r"\bwire rst_n = arst_n;", body):
                raise LandingError(f"{tn}: hard wrapper delivered reset rst_n not found (region monitor)")
            return "rst_n", dict(net="rst_n", xy_um=xy, copied_raw_parent="arst_n (delivered)", extra_control_flops=0, hard_wrapper=True)
        taps = ring_taps(self.plan, key)
        tap = min(range(len(taps)), key=lambda i: abs(taps[i][0]-xy[0]) + abs(taps[i][1]-xy[1])) if taps else 0
        reset = f"rst_n_t{tap}"
        relay = re.search(r"ot_dp_r(gate|relay)\s+\w+\s*\([^;]*?\.d\(([^)]+)\)[^;]*?\.q\(" + reset + r"\)\);", body)
        if relay is None:
            raise LandingError(f"{tn}: timed local wavefront reset relay {reset} not found (region monitor)")
        if relay.group(1) == "gate":
            reset = "cland_reset_monitor"
            logic += [f"    wire {reset};", f"    ot_dp_rrelay u_cland_rst_monitor (.clk(clk), .d({relay.group(2)}), .q({reset}));"]
        return reset, dict(net=reset, xy_um=list(taps[tap]) if taps else xy, copied_raw_parent=relay.group(2),
                           extra_control_flops=int(relay.group(1) == "gate"), must_be_ready_before_start=True)
    def _count_aligned_types(self, raise_split=True):
        """Count-aligned form (opt-in): one count origin per region; every copy of a type gets identical ring parameters
        and origin role, else TYPE_SPLIT.  Without a bind "parts" block (MESO-INTEG-1) a region must hold one landed
        partition.  With it (DIE-KV-3/CAORIGIN, COORD 21:14 ASK 3) the region's origin partition hosts the origin and a
        tx relay flop driving cland_rstart_out; every other landed partition of the region is a relay: rx flop on
        cland_rstart_in = its start (count_align_bind RELAY_STAGES = 2 = tx + rx)."""
        ca = self.ca
        regs = defaultdict(list)
        frames = ca.get("frame_clock_regions")
        if frames is not None:
            # Optional independent count origins on one physical clock group.
            # Physical clocks, masks and same-region data/status links continue
            # to use self.region; only START origin/count-frame grouping changes.
            if not ca.get("parts"):
                raise LandingError("count frame clock map requires explicit partition roles")
            for pn, pi in ca["parts"].items():
                if pn in self.parts and frames.get(pi["region"]) != self.region[pn]:
                    raise LandingError(f"count frame clock mismatch for {pn}")
        for pn in self.parts:
            if self.ins[pn] or self.outs[pn]:
                frame = ca["parts"][pn]["region"] if frames is not None else self.region[pn]
                regs[frame].append(pn)
        cparts = ca.get("parts")
        multi = {r: ps for r, ps in regs.items() if len(ps) > 1}
        if multi and cparts is None:
            raise LandingError("count-aligned landing needs one partition per region (intra-region start distribution "
                               f"is not built): {dict(list(multi.items())[:3])}")
        ports = {r["port"]: r for r in self.rows}
        out, per_type = {}, defaultdict(dict)
        self.ca_part_role = {}
        self.ca_part_cat = {}
        for reg, ps in sorted(regs.items()):
            rg = ca["regions"].get(reg)
            if rg is None:
                raise LandingError(f"count-aligned landing: region {reg} ({ps[0]}) not in the start tree")
            if cparts is None:
                org = ps[0]
            else:
                org = rg.get("origin_part")
                bad = [q for q in ps if q not in cparts or cparts[q]["region"] != reg]
                if bad or org not in ps or cparts[org]["role"] != "origin":
                    raise LandingError(f"count-aligned landing: region {reg} partitions {sorted(ps)} do not match the bind "
                                       f"roles (origin {org}, unknown {bad})")
                if sorted(q for q in ps if cparts[q]["role"] == "origin") != [org]:
                    raise LandingError(f"count-aligned landing: region {reg} needs exactly one origin partition")
            for pn in ps:
                if pn != org:
                    c = cparts[pn]
                    if c["role"] != "relay" or c["src"] != org or int(c["stages"]) != RELAY_STAGES:
                        raise LandingError(f"count-aligned landing: {pn} relay role {c} != relay({org}, {RELAY_STAGES})")
                    role = ("relay", org, RELAY_STAGES)
                elif rg["parent"] is None:
                    role = ("root", int(ca.get("root_settle_cycles", 64)))
                elif self.tstart and rg["tree_port"] in self.tstart["ports"]:
                    sp = self.tstart["ports"][rg["tree_port"]]
                    if sp["dst_part"] != pn or sp["src"] != rg["parent"]:
                        raise LandingError(f"count-aligned landing: start port {rg['tree_port']} does not start "
                                           f"{rg['parent']} -> {pn}")
                    role = ("child", START_PIN_IN, bool(rg["edge_fall"]), int(rg["pad"]))
                else:
                    r = ports.get(rg["tree_port"])
                    if r is None or r["dst"] != pn or r["src_region"] != rg["parent"]:
                        raise LandingError(f"count-aligned landing: tree port {rg['tree_port']} does not land {rg['parent']} -> {pn}")
                    role = ("child", r["dst_bus"], bool(rg["edge_fall"]), int(rg["pad"]))
                tx = pn == org and len(ps) > 1
                self.ca_part_role[pn] = dict(region=reg, role=role[0], origin=org, relay_tx=tx)
                sig = (tuple((b, r["ring_k"], r["ring_depth"]) for b, r in sorted(self.ins[pn].items())),
                       role if role[0] != "relay" else role[::2], tx)
                self.ca_part_cat[pn] = dict(rings={b: dict(K=k, depth=d) for b, k, d in sig[0]}, role=sig[1], relay_tx=tx)
                if self.strap:
                    # strap form: K, PAD, EDGE_FALL, tree select and root/child are strap values, not type identity;
                    # only the relay pin list (rx in / tx out) still separates copies (residual TYPE_SPLIT)
                    sig = (tuple(sorted(self.ins[pn])), role[0] == "relay", tx)
                per_type[self.parts[pn]["type"]].setdefault(sig, []).append(pn)
        bad = {tn: [ps for ps in sigs.values()] for tn, sigs in per_type.items() if len(sigs) > 1}
        self.ca_type_split = dict(types_needing_split=len(bad), type_count_before=len(per_type),
                                  type_count_after=sum(len(s) for s in per_type.values()))
        if bad and raise_split and not self.ca_variants:
            what = "relay rx/tx pins differ between copies" if self.strap else "K/DEPTH/origin differ between copies"
            raise LandingError(f"count-aligned landing TYPE_SPLIT required ({what}): "
                               f"{len(bad)} types, e.g. {dict(list(bad.items())[:2])}")
        for tn, sigs in per_type.items():
            pn0 = next(iter(sigs.values()))[0]
            out[tn] = dict(self.ca_part_cat[pn0])
            if self.strap:
                st = self.strap["types"][tn]
                o = st["origin"]
                role = out[tn]["role"]
                if role[0] != "relay" and o["form"] == "strap":
                    role = ("strap", tuple(o["tree_buses"]), o["padw"], int(self.ca.get("root_settle_cycles", 64)),
                            bool(o["root"]))
                out[tn] = dict(rings={b: dict(K=None, depth=v["depth"], kw=v["kw"]) for b, v in st["buses"].items()},
                               role=role, relay_tx=out[tn]["relay_tx"], straps=dict(st["straps"]))
        return out

    def _start_pins(self, plan):
        return start_pins(plan, self.ca)

    def validate_observer(self,binder):
        if not self.collector or not self.collector.get("observer"):return
        spec=self.collector["observer"];pn=spec["part"]
        if "OPEN" in (spec.get("module"),spec.get("instance_suffix"),spec.get("fault_port"),spec.get("ready_port")):
            raise LandingError(f"clock landing observer on {pn}: RTL module/instance/ports still OPEN in the sidecar")
        # The sidecar names the emitted wrapper member. Original ELAB paths
        # can be root-relative ("sys_face"), so use the exact binder emitter's
        # name transformation and still require one actual module/input pair.
        from bind import short_id
        matches=[ci for ci in binder.members.get(pn,[]) if binder.F.cells[ci].module==spec["module"]
                 and short_id("u_"+binder.rel_of(ci),90)==spec["instance_suffix"]]
        if len(matches)!=1:raise LandingError(f"clock landing observer: expected unique actual {pn}.{spec['module']}.{spec['instance_suffix']}")
        ci=matches[0];cell=binder.F.cells[ci]
        for port in (spec["fault_port"],spec["ready_port"]):
            if binder.G.dirs[ci].get(port)!="input" or len(cell.ports.get(port,[]))!=1:
                raise LandingError(f"clock landing observer {cell.path}.{port}: actual one-bit input required")
        self.observer_source=dict(path=cell.path,emitted_instance=spec["instance_suffix"],module=cell.module,ports=[spec["fault_port"],spec["ready_port"]],
                                  added_data_cycles=0,added_external_ports=0)

    def validate_observer_native(self, leaf_text, parse_ports):
        """gen_rtl (native, generated top) form of validate_observer: the observer module must be a declared leaf of
        the observer partition's type and expose the two named ports as ONE-BIT INPUTS in its actual header.  The
        unique instance / single existing connection is then enforced by gate_observer on the emitted body."""
        if not self.collector or not self.collector.get("observer"):return
        spec=self.collector["observer"];pn=spec["part"]
        if "OPEN" in (spec.get("module"),spec.get("instance_suffix"),spec.get("fault_port"),spec.get("ready_port")):
            raise LandingError(f"clock landing observer on {pn}: RTL module/instance/ports still OPEN in the sidecar")
        if pn not in self.parts:raise LandingError(f"clock landing observer partition {pn} missing")
        tn=self.parts[pn]["type"]
        if sum(p["type"]==tn for p in self.parts.values())!=1:
            raise LandingError(f"clock landing observer type {tn} is replicated")
        leaves=[c for c in self.types[tn].get("contents",[]) if c.get("module")==spec["module"]]
        if len(leaves)!=1:raise LandingError(f"clock landing observer: expected one {spec['module']} leaf in {tn}, found {len(leaves)}")
        ports=parse_ports(leaf_text(tn),spec["module"])
        if ports is None:raise LandingError(f"clock landing observer: module {spec['module']} not found in {tn} sources")
        for port in (spec["fault_port"],spec["ready_port"]):
            d,w=ports.get(port,(None,None))
            if d!="input" or w.replace(" ","") not in ("","[0:0]"):
                raise LandingError(f"clock landing observer {spec['module']}.{port}: actual one-bit input required (found {d} {w})")
        self.observer_source=dict(part=pn,type=tn,module=spec["module"],emitted_instance=spec["instance_suffix"],
                                  ports=dict(ready=spec["ready_port"],fault=spec["fault_port"]),gating="ready AND, fault OR",
                                  added_data_cycles=0,added_external_ports=0,check="native leaf header (gen_rtl)")

    def type_rtl(self, tn, text, base=None, inst=None, depth=None):
        """Emit actual landing hardware before each incoming boundary/station.

        Existing data/epoch buses and their station chains stay intact. The
        landing streams ALL bits before the original capture, including epoch.
        """
        # A binder type split (T__vN, split_of=T) copies plan type T with different R8 pad depths only; the landing
        # hardware is per plan type (mask uniformity over all T instances is checked in __init__).
        key = base or tn
        mask = self.by_type[key]
        collector_info=self.collector["types"][key] if self.collector else None
        active_collector=collector_info and collector_info["mask"]["active"]
        if not mask["inputs"] and not mask["outputs"] and not active_collector:
            self.emitted_types.add(tn)
            return text
        marker = "\n);\n"
        if marker not in text:
            raise LandingError(f"{tn}: binder ANSI module header not found")
        head, body = text.split(marker, 1)
        extra, logic = [], []
        cat = self.ca_type.get(key) if self.ca else None
        if inst is not None:
            # MESO-STRAP-1 LEC reference: the parameter wrapper of ONE copy (ca_variants), ring DEPTH from `depth`
            # (the strap master's per-bus DEPTH) so the two forms differ only in parameters vs tied straps
            if self.strap or not self.ca_variants:
                raise LandingError("type_rtl(inst=...) needs the parameter form with ca_variants=True")
            cat = json.loads(json.dumps(self.ca_part_cat[inst]))
            cat["role"] = tuple(cat["role"])
            for b, d in (depth or {}).items():
                cat["rings"][b]["depth"] = int(d)
        # DIE-HEAD-10 FSTART out (strap form, every origin but an intra-region relay rx): each forwarded start pin
        # cland_fstart_out_<b> is the Q of its OWN face flop u_cland_fstart_<b> (ot_dp_landing_relay on the region
        # start's raw reset, d = the start's D-side), equal to cland_start every cycle (0 added cycles); internal
        # loads keep cland_start.  Parameter forms and relay rx partitions keep the shared start.
        face_start = bool(cat) and bool(self.strap) and cat["role"][0] != "relay"
        if cat:
            logic.append("    wire cland_start;  // count origin of this region (count-aligned landings)")
            if face_start:
                logic.append("    wire cland_start_d, cland_start_raw;  // D-side + raw reset of cland_start (FSTART face flops)")
        ca_raw = {}
        # DIE-HEAD-9 FACE (c): a forwarded clock output is sourced in RTL from the SAME port its landing contract
        # declares (source_clock_port, which also feeds create_generated_clock -source and export_tcl); default clk.
        exp_src = {q["name"]: q["source_clock_port"]
                   for q in self.types[key].get("clock", {}).get("landing_contract", {}).get("pins", [])
                   if q.get("kind") == "clock" and q.get("dir") == "out" and q.get("source_clock_port")}

        def _exp(name):
            s_ = exp_src.get(name, "clk")
            if s_ != "clk" and not re.search(r"\binput\s+(?:wire\s+)?" + re.escape(s_) + r"\b", head):
                contract = self.types[key].get("clock", {}).get("landing_contract", {})
                if contract.get("forwarded_clock_only_inputs") is not True:
                    raise LandingError(f"{tn}: {name} contract source_clock_port {s_} is not an input port of the type")
                # The logical leaf may have one clock while its physical
                # wrapper has several planned tap inputs. Expose ONLY a tap
                # already in that physical interface, used by an actual clock
                # export. Do not remap any data or leaf clock.
                import schema
                if not hasattr(self, "_physical_clock_plan"):
                    self._physical_clock_plan = schema.Plan(self.plan)
                planned = {n for n, _x, _y in schema.tap_grid(self._physical_clock_plan, key)}
                if s_ not in planned:
                    raise LandingError(f"{tn}: forwarded clock source {s_} is not a planned physical tap input")
                needed = self.forwarded_clock_only_inputs.setdefault(tn, [])
                if s_ not in needed:
                    needed.append(s_)
                    extra.append(f"    input wire {s_}  /* planned physical tap: forwarded-clock export only */")
            return s_
        for b in mask["outputs"]:
            extra.append(f"    output wire fclk_out_{b}")
            logic.append(f"    assign fclk_out_{b} = {_exp(f'fclk_out_{b}')};")
            if cat:
                # the sender's start, forwarded beside its bus with fclk: resets the receiver ring's write count
                extra.append(f"    output wire cland_fstart_out_{b}")
                if face_start:
                    logic.append(f"    ot_dp_landing_relay u_cland_fstart_{b} (.clk(clk), .rst_raw_n(cland_start_raw), "
                                 f".d(cland_start_d), .q(cland_fstart_out_{b}));")
                else:
                    logic.append(f"    assign cland_fstart_out_{b} = cland_start;")
        part = next(p for p, v in self.parts.items() if v["type"] == key)
        for b in mask["inputs"]:
            r = self.ins[part][b]
            # Plan width excludes the in-band epoch bit; physical binding has
            # the complete width+1 bundle, just like the original station.
            input_decl = re.search(r"input\s+wire\s*\[(\d+):0\]\s+" + re.escape(b) + r"\b", head)
            if not input_decl:
                raise LandingError(f"{tn}: actual bound input {b} not found (unused/stale physical hop)")
            w = int(input_decl.group(1)) + 1
            if w > int(r["width"]) + 1:
                raise LandingError(f"{tn}.{b}: bound width {w} exceeds planned bundle capacity")
            # START must remain low while the rings train. Reusing the usual
            # START-gated rst_n would start training AFTER mission launch.
            # Copy the nearest tap's raw reset relay at the SAME parent/depth.
            # This is a timed local data relay, never another synchronizer.
            t = self.types[key]
            # A bus declaration without face/window is not physical geometry.
            geom = next((x for x in t.get("buses", []) if x["name"] == b and "face" in x and "window_um" in x), None)
            if geom is None and collector_info:
                geom=collector_info.get("bus_geometry",{}).get(b)
            if geom is None:
                slot = next((x for x in t.get("ft_slots", []) if x["name"] + "_i" == b), None)
                if slot:
                    geom = dict(face=slot["in_face"], window_um=slot["in_window_um"])
            if geom is None:
                raise LandingError(f"{tn}.{b}: receiver face geometry not found")
            face = geom["face"]; at = sum(geom["window_um"]) / 2
            tw, th = t["outline_um"]
            x, y = (0 if face == "W" else tw, at) if face in "EW" else (at, 0 if face == "S" else th)
            hard_tree = collector_info and (collector_info.get("tree") or {}).get("hard")
            taps = ring_taps(self.plan, key)
            if hard_tree:
                tap, xy = None, [x, y]
            elif taps:
                tap = min(range(len(taps)), key=lambda i: abs(taps[i][0]-x) + abs(taps[i][1]-y))
                xy = list(taps[tap])
            else:
                tap, xy = 0, t.get("clock", {}).get("tap_um", [tw/2, th/2])
            if hard_tree:
                # Hard partition (no generated reset tree): the ring sits in the
                # soft wrapper at the received window, on the delivered reset
                # that the wrapper's own boundary/ft stations already use.
                if not re.search(r"\bwire rst_n = arst_n;", body):
                    raise LandingError(f"{tn}.{b}: hard wrapper delivered reset rst_n not found")
                reset = "rst_n"
                self.reset_placements.setdefault(tn, {})[b] = dict(net=reset, xy_um=xy, copied_raw_parent="arst_n (delivered)",
                    extra_control_flops=0, must_be_ready_before_start=True, boot_settle_cycles=21, hard_wrapper=True)
                relay = None
            else:
                reset = f"rst_n_t{tap}"
            relay = None if hard_tree else re.search(r"ot_dp_r(gate|relay)\s+\w+\s*\([^;]*?\.d\(([^)]+)\)[^;]*?\.q\(" + reset + r"\)\);", body)
            if relay is None and not hard_tree:
                raise LandingError(f"{tn}.{b}: timed local wavefront reset relay {reset} not found")
            if hard_tree:
                pass
            elif relay.group(1) == "gate":
                reset = f"cland_reset_{b}"
                logic += [f"    wire {reset};",
                          f"    ot_dp_rrelay u_cland_rst_{b} (.clk(clk), .d({relay.group(2)}), .q({reset}));"]
            if not hard_tree:
                self.reset_placements.setdefault(tn, {})[b] = dict(net=reset, xy_um=xy,
                    copied_raw_parent=relay.group(2), extra_control_flops=int(relay.group(1) == "gate"),
                    must_be_ready_before_start=True, boot_settle_cycles=21)
            extra += [f"    input wire fclk_in_{b}"]
            if cat:
                extra += [f"    input wire cland_fstart_in_{b}"]
                ca_raw[b] = reset
                if cat.get("straps"):
                    kw = cat["rings"][b]["kw"]
                    extra += [f"    input wire [{kw-1}:0] strap_ca_k_{b}"]
                    ring_mod = f"ot_dp_clk_landing_cas #(.W({{w}}), .DEPTH({cat['rings'][b]['depth']}))"
                    ring_rst = (f".t_rst_n(cland_fstart_in_{b}), .clk(clk), .rst_n(cland_start), "
                                f".strap_k(strap_ca_k_{b})")
                else:
                    ring_mod = (f"ot_dp_clk_landing_ca #(.W({{w}}), .DEPTH({cat['rings'][b]['depth']}), "
                                f".K({cat['rings'][b]['K']}))")
                    ring_rst = f".t_rst_n(cland_fstart_in_{b}), .clk(clk), .rst_n(cland_start)"
                self.reset_placements[tn][b].update(ring_rst_n="cland_start", origin_raw_reset=reset)
            else:
                # per-row ring form (main: ring_module/ring_params/ring_ports sidecar); default = today's ring
                rpar = "".join(f", .{k}({v})" for k, v in sorted(r.get("ring_params", {}).items()))
                rpin = "".join(f", .{k}({v})" for k, v in sorted(r.get("ring_ports", {}).items()))
                ring_mod = r["module"] + " #(.W({w})" + rpar.replace("{", "{{").replace("}", "}}") + ")"
                ring_rst = f".clk(clk), .rst_n({reset}){rpin}"
            if self.dataflow:
                extra += [f"    input wire cland_dn_ready_{b}", f"    input wire cland_dn_fault_{b}"]
            if self.collector:
                logic.append(f"    wire landing_ready_{b}, landing_fault_{b};")
            else:
                extra += [f"    output wire landing_ready_{b}",f"    output wire landing_fault_{b}"]
            landed = f"cland_{b}"
            # Rename the local NET only: a `.name(` port reference on a child instance is the child's port, never
            # this wrapper's bus (gen_rtl wrappers bind leaves by name: `.lep_fault_i(lep_fault_i_q)`).
            body = re.sub(r"(?<![.\w])" + re.escape(b) + r"\b", landed, body)
            if self.dataflow:
                # ring W+2: {fault, ready} of the sender's status ride the spare padded ring bits under the same
                # forwarded write clock; no extra data cycle, no die-top status wire beside the bus.
                ring = f"cland_ring_{b}"
                logic += [f"    wire [{w+1}:0] {ring};", f"    wire [{w-1}:0] {landed};",
                          f"    assign {landed} = {ring}[{w-1}:0];",
                          f"    {ring_mod.format(w=w+2)} u_cland_{b} (",
                          f"        .fclk(fclk_in_{b}), {ring_rst}, .d({{cland_dn_fault_{b}, cland_dn_ready_{b}, {b}}}), .q({ring}),",
                          f"        .ready(landing_ready_{b}), .fault(landing_fault_{b}));",
                          f"    wire cland_ok_{b} = {ring}[{w}] && landing_ready_{b} && !landing_fault_{b};",
                          f"    wire cland_bad_{b} = landing_fault_{b} || (landing_ready_{b} && {ring}[{w+1}]);"]
                continue
            logic += [f"    wire [{w-1}:0] {landed};",
                      f"    {ring_mod.format(w=w)} u_cland_{b} (",
                      f"        .fclk(fclk_in_{b}), {ring_rst}, .d({b}), .q({landed}),",
                      f"        .ready(landing_ready_{b}), .fault(landing_fault_{b}));"]
        if cat:
            logic += self._origin_rtl(tn, cat, ca_raw, body, extra)
            if self.tstart and self.tstart["type_pins"].get(key, {}).get(START_PIN_OUT):
                # START-TREE: the region start leaves on ONE dedicated pin (fanned out at the die top / to a stage)
                extra.append(f"    output wire {START_PIN_OUT}")
                logic.append(f"    assign {START_PIN_OUT} = cland_start;")
        if self.dataflow:
            body = self._dataflow_monitor(tn, key, mask, collector_info, extra, logic, body)
        elif active_collector:
            import landing_collector as LC
            if collector_info["mask"].get("observer"):
                logic.append("    wire cland_up_ready, cland_up_fault;")
            else:extra += ["    output wire cland_up_ready", "    output wire cland_up_fault"]
            if collector_info["mask"]["up_seam"]:
                extra.append("    output wire fclk_out_cland_up")
                logic.append(f"    assign fclk_out_cland_up = {_exp('fclk_out_cland_up')};")
            sources=list(collector_info["local_sources"])
            monitor_reset_copies = []
            for ch in collector_info["children"]:
                i=ch["index"]
                extra += [f"    input wire {ch['ready']}", f"    input wire {ch['fault']}"]
                src=dict(ch,name=f"child{i}")
                if ch["seam"]:
                    extra.append(f"    input wire fclk_in_cland_dn_{i}")
                    node=ch.get("node",f"rst_n_t{ch.get('tap',0)}")
                    reset, added, copies = LC.raw_reset(collector_info["tree"], node,
                                                       body+"\n"+"\n".join(logic))
                    logic.extend(added)
                    monitor_reset_copies.extend(copies)
                    logic += [f"    wire [1:0] cland_dn_word_{i};",
                              f"    wire cland_dn_trained_{i}, cland_dn_guard_{i};",
                              f"    ot_dp_clk_landing #(.W(2)) u_cland_monitor_{i} (",
                              f"        .fclk(fclk_in_cland_dn_{i}), .clk(clk), .rst_n({reset}),",
                              f"        .d({{{ch['fault']}, {ch['ready']}}}), .q(cland_dn_word_{i}),",
                              f"        .ready(cland_dn_trained_{i}), .fault(cland_dn_guard_{i}));"]
                    src.update(ready=f"(cland_dn_word_{i}[0] && cland_dn_trained_{i} && !cland_dn_guard_{i})",
                               fault=f"(cland_dn_word_{i}[1] || cland_dn_guard_{i})")
                sources.append(src)
            if collector_info["tree"].get("hard"):
                reduction=LC.build_hard_chain(collector_info["tree"],sources)
            else:
                reduction=LC.build_local(collector_info["tree"],sources,body+"\n"+"\n".join(logic),
                    root_node=collector_info.get("collector_root_node","rst_root_n"))
            reduction["instances"] = monitor_reset_copies + reduction["instances"]
            logic.extend(reduction["rtl"])
            self.reset_placements.setdefault(tn,{})["collector"]=reduction
            if collector_info["mask"].get("observer"):
                body=gate_observer(body,self.collector["observer"])
        # The former last port can carry an end-of-line comment.
        lines = head.splitlines()
        code, sep, comment = lines[-1].partition("//")
        lines[-1] = code.rstrip() + "," + ((" //" + comment) if sep else "")
        head = "\n".join(lines) + "\n" + ",\n".join(extra)
        self.emitted_types.add(tn)
        return head + marker + "\n".join(logic) + "\n" + body

    def _origin_rtl(self, tn, cat, ca_raw, body, extra):
        """The region's count origin: root = ot_dp_landing_root (fixed settle count), child = ot_dp_landing_origin on
        the start-tree port (3-FF sync of the parent's forwarded start, edge/PAD from the bind).  Its raw reset is the
        timed local raw-reset relay of the tree bus (child) / of a landed input or tap 0 (root), never START-gated.
        Intra-region relay (ASK 3): the origin partition of a multi-partition region adds the tx flop u_cland_rstart_tx
        -> cland_rstart_out; a relay partition's start is the rx flop u_cland_rstart_rx on cland_rstart_in."""
        role = cat["role"]
        raw_logic = []
        raw_fallback = None

        def local_raw(what):
            nonlocal raw_fallback
            raw = next(iter(ca_raw.values()), None)
            if raw is None:
                if raw_fallback is not None:return raw_fallback
                m = re.search(r"ot_dp_r(gate|relay)\s+\w+\s*\([^;]*?\.d\(([^)]+)\)[^;]*?\.q\((rst_n_t0)\)\);", body)
                raw = m.group(3) if m else ("rst_n" if re.search(r"\bwire rst_n = arst_n;", body) else None)
                if m and m.group(1) == "gate":
                    # The count origin/relay must release before START.  Match the
                    # tap's parent and depth without inheriting its START gate.
                    raw = "cland_origin_reset"
                    raw_logic.extend(["    wire " + raw + ";",
                        f"    ot_dp_rrelay u_cland_origin_rst (.clk(clk), .d({m.group(2)}), .q({raw}));"])
                if raw is None:
                    raise LandingError(f"{tn}: {what} needs a timed raw reset relay (rst_n_t0) or delivered rst_n")
                raw_fallback = raw
            return raw
        if role[0] == "relay":
            raw = local_raw("start relay rx")
            self.reset_placements.setdefault(tn, {})["count_origin"] = dict(kind="relay", raw_reset=raw, stages=role[-1])
            extra.append("    input wire cland_rstart_in")
            return raw_logic + [f"    ot_dp_landing_relay u_cland_rstart_rx (.clk(clk), .rst_raw_n({raw}), .d(cland_rstart_in), "
                    f".q(cland_start));"]
        if role[0] == "strap":
            logic, raw = self._origin_strap_rtl(tn, role, ca_raw, extra, local_raw)
        elif role[0] == "child":
            b = role[1]
            if b == START_PIN_IN:
                # START-TREE: the parent's start on the dedicated start pin; raw reset = a local timed relay
                raw, p_start = local_raw("start-tree origin"), START_PIN_IN
                extra.append(f"    input wire {START_PIN_IN}")
            else:
                raw, p_start = ca_raw.get(b), f"cland_fstart_in_{b}"
            if raw is None:
                raise LandingError(f"{tn}: start-tree bus {b} is not a landed input of this type")
            self.reset_placements.setdefault(tn, {})["count_origin"] = dict(kind="child", tree_bus=b, raw_reset=raw,
                                                                         edge_fall=role[2], pad=role[3])
            logic = [f"    ot_dp_landing_origin #(.PAD({role[3]}), .EDGE_FALL({int(role[2])})) u_cland_origin (",
                     f"        .clk(clk), .rst_raw_n({raw}), .p_start({p_start}), .start(cland_start));"]
        else:
            raw = local_raw("root count origin")
            self.reset_placements.setdefault(tn, {})["count_origin"] = dict(kind="root", raw_reset=raw, settle=role[1])
            if self.strap:
                logic = [f"    ot_dp_landing_root #(.SETTLE({role[1]})) u_cland_origin (.clk(clk), .rst_raw_n({raw}), "
                         ".start(cland_start), .start_d(cland_start_d));", f"    assign cland_start_raw = {raw};"]
            else:
                logic = [f"    ot_dp_landing_root #(.SETTLE({role[1]})) u_cland_origin (.clk(clk), .rst_raw_n({raw}), .start(cland_start));"]
        if cat.get("relay_tx"):
            self.reset_placements[tn]["count_origin"]["relay_tx"] = True
            extra.append("    output wire cland_rstart_out")
            logic.append(f"    ot_dp_landing_relay u_cland_rstart_tx (.clk(clk), .rst_raw_n({raw}), .d(cland_start), "
                         f".q(cland_rstart_out));")
        return raw_logic + logic

    def _origin_strap_rtl(self, tn, role, ca_raw, extra, local_raw):
        """MESO-STRAP-1 strap origin: ot_dp_landing_origin_s (strap_ca_pad / strap_ca_efall), the parent's forwarded
        start and the child raw reset chosen by strap_ca_tsel among the copies' tree buses. Each tree bus has its own
        origin sampler; static selection follows those samplers (out-of-range values take the last bus). An optional
        root counter is chosen by strap_ca_root. The
        raw reset of each choice is exactly the parameter form's (child: the tree bus's timed relay; root: local_raw)."""
        _, tbs, padw, settle, root = role
        copy_export = getattr(self, "types", {}).get(tn, {}).get("clock", {}).get("landing_origin_export_copy", False)
        fwd_param = ", .FWD_COPY(1)" if copy_export else ""
        ca_raw = dict(ca_raw)
        if START_PIN_IN in tbs:
            # START-TREE: the dedicated start pin is one of the choices; its raw reset is a local timed relay
            ca_raw[START_PIN_IN] = local_raw("start-tree origin")
            extra.append(f"    input wire {START_PIN_IN}")

        def pin(b):
            return START_PIN_IN if b == START_PIN_IN else f"cland_fstart_in_{b}"
        for b in tbs:
            if b not in ca_raw:
                raise LandingError(f"{tn}: start-tree bus {b} is not a landed input of this type")
        extra.append(f"    input wire [{padw-1}:0] strap_ca_pad")
        extra.append("    input wire strap_ca_efall")   # SCALAR_STRAPS
        logic = []
        multi = len(tbs) > 1
        if multi:
            tsw = (len(tbs) - 1).bit_length()
            extra.append(f"    input wire [{tsw-1}:0] strap_ca_tsel")
            def sel(names):
                e = names[-1]
                for i in range(len(names) - 2, -1, -1):
                    e = f"(strap_ca_tsel == {tsw}'d{i}) ? {names[i]} : {e}"
                return e
            raw = "cland_oraw"
            logic += [f"    wire cland_oraw = {sel([ca_raw[b] for b in tbs])};"]
        else:
            p_start, raw = pin(tbs[0]), ca_raw[tbs[0]]
        start = "cland_start"
        if root:
            extra.append("    input wire strap_ca_root")   # SCALAR_STRAPS
            rraw = local_raw("root count origin")
            # FSTART face flops of a root+child type: the static strap select picks the D-side and the raw reset
            # BEFORE the flop (never on the port net)
            logic += ["    wire cland_start_child, cland_start_root, cland_start_child_d, cland_start_root_d;",
                      f"    wire cland_raw_sel = strap_ca_root ? {rraw} : {raw};",
                      f"    ot_dp_landing_root #(.SETTLE({settle})) u_cland_root (.clk(clk), .rst_raw_n({rraw}), "
                      ".start(cland_start_root), .start_d(cland_start_root_d));",
                      "    assign cland_start = strap_ca_root ? cland_start_root : cland_start_child;",
                      "    assign cland_start_d = strap_ca_root ? cland_start_root_d : cland_start_child_d;",
                      "    assign cland_start_raw = cland_raw_sel;"]
            start, start_d, raw_used = "cland_start_child", "cland_start_child_d", "cland_raw_sel"
        else:
            raw_used, start_d = raw, "cland_start_d"
            logic.append(f"    assign cland_start_raw = {raw};")
        if multi:
            # Each START owns its sampler. Static selection follows both registered and D-side taps,
            # preserving the dedicated forwarded START face flop's existing zero-cycle contract.
            starts = [f"cland_start_t{i}" for i in range(len(tbs))]
            starts_d = [f"cland_start_t{i}_d" for i in range(len(tbs))]
            logic.append(f"    wire {', '.join(starts + starts_d)};")
            for i, b in enumerate(tbs):
                logic += [f"    ot_dp_landing_origin_s #(.PADW({padw}){fwd_param}) u_cland_origin_t{i} (",
                          f"        .clk(clk), .rst_raw_n({ca_raw[b]}), .p_start({pin(b)}), .strap_efall(strap_ca_efall), "
                          f".strap_pad(strap_ca_pad), .start({starts[i]}), .start_d({starts_d[i]}));"]
            logic += [f"    assign {start} = {sel(starts)};", f"    assign {start_d} = {sel(starts_d)};"]
        else:
            logic += [f"    ot_dp_landing_origin_s #(.PADW({padw}){fwd_param}) u_cland_origin (",
                      f"        .clk(clk), .rst_raw_n({raw}), .p_start({p_start}), .strap_efall(strap_ca_efall), "
                      f".strap_pad(strap_ca_pad), .start({start}), .start_d({start_d}));"]
        self.reset_placements.setdefault(tn, {})["count_origin"] = dict(kind="strap", tree_buses=list(tbs), padw=padw,
                                                                     root=bool(root), raw_reset=raw_used,
                                                                     **({"per_bus_origins": [f"u_cland_origin_t{i}" for i in range(len(tbs))]} if multi else {}))
        return logic, raw_used

    def _dataflow_monitor(self, tn, key, mask, info, extra, logic, body):
        """Registered dataflow monitor: local = AND(landing_ready) / OR(landing_fault), aggregate = AND(in_ok) /
        OR(in_bad) over every landed input (in_ok includes the local ring ready), registered
        local_registered_depth times. Every output pin gets its OWN dedicated output register (the last stage):
        the tree bus carries the aggregate, every other landed output the local status. The observer type keeps
        the aggregate on cland_up_ready/fault for gate_observer (never new IO)."""
        ins = list(mask["inputs"]); n = len(ins)
        depth = int(info["local_registered_depth"])
        if depth < 1:raise LandingError(f"{tn}: dataflow monitor depth {depth} < 1")
        rp = self.reset_placements.setdefault(tn, {})
        root_xy = info.get("collector_root_xy")
        # One existing raw ring reset (nearest to the collector root): the monitor must train before START.
        def dist(b):
            xy = rp[b]["xy_um"];return (abs(xy[0]-root_xy[0])+abs(xy[1]-root_xy[1])) if root_xy else 0, b
        if ins:
            rst = rp[min(ins, key=dist)]["net"]
        else:                                   # monitor="region" only (checked in __init__)
            rst, rp["monitor_reset"] = self._region_reset(tn, key, body, logic, root_xy or [0, 0])
        ready_l = ", ".join(f"landing_ready_{b}" for b in ins); fault_l = ", ".join(f"landing_fault_{b}" for b in ins)
        ok_l = ", ".join(f"cland_ok_{b}" for b in ins); bad_l = ", ".join(f"cland_bad_{b}" for b in ins)
        intra_in, intra_out = [], []
        if self.region_monitor:
            intra_in = sorted(info["mask"].get("intra_inputs", []))
            intra_out = [b for b in sorted(info["mask"].get("intra_outputs", [])) if b not in mask["outputs"]]
            for b in intra_in:
                extra += [f"    input wire cland_dn_ready_{b}", f"    input wire cland_dn_fault_{b}"]
            # same-region status: the sender's dedicated output register on the SAME region clock -> plain inputs
            ok_l = ", ".join([x for x in [ok_l] if x] + [f"cland_dn_ready_{b}" for b in intra_in])
            bad_l = ", ".join([x for x in [bad_l] if x] + [f"cland_dn_fault_{b}" for b in intra_in])
            n = n + len(intra_in)
            if not n:                           # nothing to train or hear: ready one registered cycle after reset
                ok_l, bad_l, n = "1'b1", "1'b0", 1
            if not ins:
                ready_l, fault_l = "1'b1", "1'b0"
        stages = []
        def collect(name, N, rdy, flt, ro, fo):
            logic.extend([f"    ot_dp_landing_collect #(.N({N})) {name} (",
                          f"        .clk(clk), .rst_n({rst}), .ready_i({{{rdy}}}),",
                          f"        .fault_i({{{flt}}}), .ready_o({ro}), .fault_o({fo}));"])
            stages.append(name)
        tree_bus = info["mask"].get("tree_bus")
        prev = None
        for k in range(1, depth):
            ro, fo = f"cland_agg_r{k}", f"cland_agg_f{k}"
            logic.append(f"    wire {ro}, {fo};")
            if prev is None:collect(f"u_cland_agg_{k}", n, ok_l, bad_l, ro, fo)
            else:collect(f"u_cland_agg_{k}", 1, prev[0], prev[1], ro, fo)
            prev = (ro, fo)
        final_in = prev or (ok_l, bad_l)
        final_n = 1 if prev else n
        outputs = []
        for b in list(mask["outputs"]) + intra_out:
            extra += [f"    output wire cland_up_ready_{b}", f"    output wire cland_up_fault_{b}"]
            if b == tree_bus:
                collect(f"u_cland_up_{b}", final_n, final_in[0], final_in[1], f"cland_up_ready_{b}", f"cland_up_fault_{b}")
                outputs.append(dict(bus=b, carries="aggregate", registered_depth=depth))
            else:
                collect(f"u_cland_up_{b}", max(1, len(ins)), ready_l, fault_l, f"cland_up_ready_{b}", f"cland_up_fault_{b}")
                outputs.append(dict(bus=b, carries="local", registered_depth=1))
        if tree_bus is None:
            spec = self.collector.get("observer") or {}
            if "OPEN" in (spec.get("module"), spec.get("instance_suffix"), spec.get("fault_port"), spec.get("ready_port")):
                raise LandingError(f"{tn}: dataflow monitor observer RTL ports still OPEN in the sidecar")
            logic.append("    wire cland_up_ready, cland_up_fault;")
            collect("u_cland_up_observer", final_n, final_in[0], final_in[1], "cland_up_ready", "cland_up_fault")
            body = gate_observer(body, self.collector["observer"])
        rp["monitor"] = dict(mode="region" if self.region_monitor else "dataflow", raw_reset=rst, depth=depth, tree_bus=tree_bus, stages=stages,
                             outputs=outputs, flops=2*len(stages), data_cycles_added=0)
        return body

    def top_rtl(self, text, emitted_modules=None):
        """Connect the new forwarded-clock pins and observed status at die top.

        Region clocks are explicit inputs. No die-top data register or clock
        synthesizer is invented; physical die-clock emission supplies them.
        """
        modules=emitted_modules or {tn:t["module"] for tn,t in self.types.items()}
        if set(modules)!=set(self.types):raise LandingError("clock landing: emitted module/type inventory changed after cohort composition")
        self.emitted_modules=dict(modules)
        clocks = sorted(set(self.region.values()))
        n = len(self.rows)
        if not n:
            self.emitted_top = True
            return text
        names = [f"clk_region_{ident(r)}" for r in clocks]
        # START-TREE: die-level start-stage nets are die-top ports like the region clocks (the die clock emission /
        # start_stage_emit.py ot_die_start_stages drives pst_<region> and reads rs_<region>)
        ts = self.tstart
        ts_in = sorted({e["net"] for e in ts["die_outputs"]}) if ts else []
        ts_out = ts["die_input_nets"] if ts else []
        ts_ports = [(f"input  wire {n}", f"    input wire {n};") for n in ts_in] + \
                   [(f"output wire {n}", f"    output wire {n};") for n in ts_out]
        names += ts_in + ts_out
        local_observer=self.collector and self.collector.get("observer")
        if not local_observer:names += ["clock_landing_ready", "clock_landing_fault"]
        match = re.search(r"(?m)^module (\w+) \(([^;]*)\);", text)
        if not match:
            raise LandingError("clock landing: binder non-ANSI die header not found")
        # gen_rtl (native generated top, LAND-HEAD-BIND-1) emits an ANSI header whose only clock is the die `clk`
        # feeding every partition clock pin (.clk / grid .clk_t<i> / early-core .clk_c<i>).  In the landed form each partition's
        # pins are its REGION clock; the die `clk` port is then unread and removed (the die clock emission supplies
        # the region clocks).  The binder's non-ANSI path below is unchanged.
        ansi = re.search(r"\b(input|output)\b", match.group(2)) is not None
        if ansi:
            if not local_observer:
                raise LandingError("clock landing: native (ANSI) top requires a local observer (dataflow monitor)")
            ports = match.group(2).rstrip()
            ports = re.sub(r"\n    input  wire clk,(?=\n)", "", ports, count=1)
            header = (f"module {match.group(1)} (" + ports + "".join(f",\n    input  wire clk_region_{ident(r)}" for r in clocks)
                      + "".join(f",\n    {a}" for a, _ in ts_ports) + "\n);")
        else:
            header = f"module {match.group(1)} ({match.group(2)}, " + ", ".join(names) + ");"
        text = text[:match.start()] + header + text[match.end():]
        decl = [] if ansi else [f"    input wire clk_region_{ident(r)};" for r in clocks] + [d for _, d in ts_ports]
        if not local_observer:
            decl += (["    output wire clock_landing_ready;","    output wire clock_landing_fault;"] if self.collector else
                     [f"    output wire [{n-1}:0] clock_landing_ready;",f"    output wire [{n-1}:0] clock_landing_fault;"])
        fwd = {(r["src"], r["src_bus"]): f"clock_landing_fwd_{ident(r['src'])}__{ident(r['src_bus'])}"
               for r in self.rows}
        decl += [f"    wire {w};" for w in sorted(set(fwd.values()))]
        fst = {k: v.replace("clock_landing_fwd_", "clock_landing_start_", 1) for k, v in fwd.items()} if self.ca else {}
        decl += [f"    wire {w};" for w in sorted(set(fst.values()))]
        tsw, tsi = {}, {}
        if ts:
            # one start wire per launch partition (its single cland_tstart_out, fanned out here)
            tsw = {e["src_part"]: f"clock_landing_tstart_{ident(e['src_part'])}" for e in ts["plan_ports"] + ts["die_inputs"]}
            decl += [f"    wire {w};" for w in sorted(set(tsw.values()))]
            tsi = {e["dst_part"]: tsw[e["src_part"]] for e in ts["plan_ports"]}
            tsi.update({e["dst_part"]: e["net"] for e in ts["die_outputs"]})
            decl += [f"    assign {e['net']} = {tsw[e['src_part']]};"
                     for e in sorted({e["net"]: e for e in ts["die_inputs"]}.values(), key=lambda e: e["net"])]
        rpr = getattr(self, "ca_part_role", {}) if self.ca else {}
        rst = {r["origin"]: f"clock_landing_rstart_{ident(r['origin'])}" for r in rpr.values() if r["role"] == "relay"}
        decl += [f"    wire {w};" for w in sorted(set(rst.values()))]
        mon = {}
        if self.dataflow:
            # one wire pair per sender status pin (a source bus fanning out to several sinks shares its pin)
            mon = {(r["src"], r["src_bus"]): f"cland_mon_{ident(r['src'])}__{ident(r['src_bus'])}" for r in self.rows}
            for _pid, sp, sb, _dp, _db in self.intra_links:     # monitor="region": same-region status wires
                mon.setdefault((sp, sb), f"cland_mon_{ident(sp)}__{ident(sb)}")
            decl += [f"    wire {w}_ready, {w}_fault;" for w in sorted(set(mon.values()))]
        elif self.collector:
            for pn,p in self.collector["parts"].items():
                if p["active"] and p["parent"] is not None:
                    decl += [f"    wire cland_ready_{ident(pn)}, cland_fault_{ident(pn)};"]
            for e in self.collector["edges"]:
                if e["seam"]:decl.append(f"    wire cland_clock_{ident(e['src'])};")
        match = re.search(r"(?m)^module \w+ \([^;]*\);", text)
        text = text[:match.end()] + "\n" + "\n".join(decl) + text[match.end():]
        index = {(r["dst"], r["dst_bus"]): i for i, r in enumerate(self.rows)}
        for pn, p in self.parts.items():
            # Anchor on the instance, then the binder's own closing line; leaf
            # parameter parentheses can never terminate this module instance.
            pat = re.compile(r"(?m)^(    " + re.escape(modules[p["type"]]) +
                             r"(?: #\([^\n]*\))? " + re.escape(ident(pn)) + r" \(\n)(.*?)(\n    \);)", re.S)
            matches = list(pat.finditer(text))
            if len(matches) != 1:
                raise LandingError(f"clock landing: expected exactly one bound instance {pn}")
            m = matches[0]
            if ansi:
                body, count = re.subn(r"\.(clk(?:_[tc]\d+)?)\(clk\)", lambda mm: f".{mm.group(1)}(clk_region_{ident(self.region[pn])})", m.group(2))
                if not re.search(r"\.clk\(clk_region_", body):
                    raise LandingError(f"clock landing: default clock connection not found on {pn}")
            else:
                body, count = re.subn(r"\.clk\(clk_\w+\)", f".clk(clk_region_{ident(self.region[pn])})", m.group(2), count=1)
            if count < 1:
                raise LandingError(f"clock landing: default clock connection not found on {pn}")
            conn = [f"        .fclk_out_{b}({fwd[(pn,b)]})" for b in sorted(self.outs[pn])]
            # Functional binding uses the region source, as existing grid/core
            # tap connections do. The physical kit keeps the distinct planned
            # input pins and the export's source_clock_port contract.
            for tap in self.forwarded_clock_only_inputs.get(p["type"], []):
                if not re.search(r"\." + re.escape(tap) + r"\s*\(", body):
                    conn.append(f"        .{tap}(clk_region_{ident(self.region[pn])})")
            conn += [f"        .cland_fstart_out_{b}({fst[(pn,b)]})" for b in sorted(self.outs[pn]) if self.ca]
            if ts:
                tpins = ts["type_pins"].get(p["type"], {})
                if START_PIN_OUT in tpins:
                    conn.append(f"        .{START_PIN_OUT}({tsw.get(pn, '')})")
                if START_PIN_IN in tpins:
                    if pn in tsi:
                        conn.append(f"        .{START_PIN_IN}({tsi[pn]})")
                    elif rpr.get(pn, {}).get("role") == "root" and self.strap and tsw.get(pn):
                        # strap root copy of a root+child type: strap_ca_root selects the root counter, p_start unread.
                        # DIE-KV-13 trial: a literal here is not a declared strap_* pin (tie-off audit, OWNER 10-25 B), so
                        # the unread pin takes the copy's OWN start launch wire (its cland_tstart_out = cland_start)
                        conn.append(f"        .{START_PIN_IN}({tsw[pn]})")
                    elif rpr.get(pn, {}).get("role") == "root" and self.strap:
                        conn.append(f"        .{START_PIN_IN}(1'b0)")
                    else:
                        raise LandingError(f"clock landing {pn}: type {p['type']} has {START_PIN_IN} but no start "
                                           "port lands on this copy")
            if pn in rpr and rpr[pn]["relay_tx"]:
                conn.append(f"        .cland_rstart_out({rst[pn]})")
            if pn in rpr and rpr[pn]["role"] == "relay":
                conn.append(f"        .cland_rstart_in({rst[rpr[pn]['origin']]})")
            if self.strap and pn in self.strap["instances"]:
                # OWNER 12.15a / 1.8 rule 3: each strap bit a literal here; die_constant_cells.tcl maps every bit to its
                # own TIEHI/TIELO next to the pin; straps.audit_count_strap_values checks the pattern against the bind
                si = self.strap["instances"][pn]
                widths = self.strap["types"][si["type"]]["straps"]
                for sp in sorted(widths):
                    w = widths[sp]
                    conn.append(f"        .{sp}({w}'b{format(si['values'][sp], '0' + str(w) + 'b')})")
            if self.dataflow:
                for b in sorted(self.outs[pn]):
                    conn += [f"        .cland_up_ready_{b}({mon[(pn,b)]}_ready)", f"        .cland_up_fault_{b}({mon[(pn,b)]}_fault)"]
            for b, r in sorted(self.ins[pn].items()):
                i = index[(pn,b)]
                conn += [f"        .fclk_in_{b}({fwd[(r['src'],r['src_bus'])]})"]
                if self.ca:
                    conn += [f"        .cland_fstart_in_{b}({fst[(r['src'],r['src_bus'])]})"]
                if self.dataflow:
                    w = mon[(r["src"], r["src_bus"])]
                    conn += [f"        .cland_dn_ready_{b}({w}_ready)", f"        .cland_dn_fault_{b}({w}_fault)"]
                elif not self.collector:
                    conn += [f"        .landing_ready_{b}(clock_landing_ready[{i}])",f"        .landing_fault_{b}(clock_landing_fault[{i}])"]
            if self.region_monitor:
                for b in sorted(self.intra_out[pn] - self.outs[pn]):
                    conn += [f"        .cland_up_ready_{b}({mon[(pn,b)]}_ready)", f"        .cland_up_fault_{b}({mon[(pn,b)]}_fault)"]
                for _pid, sp, sb, dp, db in sorted(self.intra_links):
                    if dp == pn:
                        w = mon[(sp, sb)]
                        conn += [f"        .cland_dn_ready_{db}({w}_ready)", f"        .cland_dn_fault_{db}({w}_fault)"]
            if self.collector and not self.dataflow and self.collector["parts"][pn]["active"]:
                cp=self.collector["parts"][pn]
                ready="clock_landing_ready" if cp["parent"] is None else "cland_ready_"+ident(pn)
                fault="clock_landing_fault" if cp["parent"] is None else "cland_fault_"+ident(pn)
                if cp["parent"] is not None or not local_observer:
                    conn += [f"        .cland_up_ready({ready})",f"        .cland_up_fault({fault})"]
                if self.collector["types"][p["type"]]["mask"]["up_seam"]:
                    conn.append(f"        .fclk_out_cland_up(cland_clock_{ident(pn)})")
                for e in self.collector["edges"]:
                    if e["dst"]!=pn:continue
                    i=e["dst_index"];child=ident(e["src"])
                    conn += [f"        .cland_dn_ready_{i}(cland_ready_{child})",f"        .cland_dn_fault_{i}(cland_fault_{child})"]
                    if e["seam"]:conn.append(f"        .fclk_in_cland_dn_{i}(cland_clock_{child})")
            body = ",\n".join(conn + [body])
            text = text[:m.start()] + m.group(1) + body + m.group(3) + text[m.end():]
        if ansi and re.search(r"\(clk\)", text):
            raise LandingError("clock landing: native top still drives a partition pin from the die clk")
        self.emitted_top = True
        return text

    def strap_declarations(self, binder_types=None):
        """MESO-STRAP-1: {type: {strap port: width}} of the strap form (binder_types: {binder type: plan type} for
        binder T__vN splits), for the parent strap manifest the tie-off audit reads."""
        if not self.strap:
            return {}
        out = {}
        for bt, pt in (binder_types or {t: t for t in self.strap["types"]}).items():
            if pt in self.strap["types"]:
                out[bt] = dict(self.strap["types"][pt]["straps"])
        return out

    def strap_expected(self):
        """MESO-STRAP-1: {instance: {strap port: (width, value)}} = count_align_bind.strap_ties tie values"""
        if not self.strap:
            return {}
        return {q: {sp: (self.strap["types"][v["type"]]["straps"][sp], v["values"][sp]) for sp in v["values"]}
                for q, v in self.strap["instances"].items()}

    def land_slots(self, tn):
        """kit land_slots.json of plan type tn for face_guard (DIE-HEAD-21; face_guard.kit_land / land_spec), or None.
        Only the count-aligned ring (ot_dp_clk_landing_ca / _cas -> ot_meso_ring_ca) is declared: its writer stores
        s_d[slot] <= t_d under the write-count enable (own-Q hold, no ICG), i.e. face_guard form "hold_mux", with D =
        the ring DEPTH type_rtl emits for that bus.  With the dataflow monitor the ring d = {cland_dn_fault_b,
        cland_dn_ready_b, b}, so both status pins land the same D slots.  The ring's forwarded START cland_fstart_in_b
        (t_rst_n of the ring writer + p_start of the count origin; no face flop: it would shift the count frame by one
        cycle) is declared {"form": "ring_start", "ring": b}: face_guard proves its fan-out ends only in ring b's writer
        flops and the origin's start sampler flops.  Schema land_slots/2 (/1 had no ring_start entries; face_guard
        ignores the schema string; older guards refuse unknown forms, fail-closed). The dedicated START input has
        explicit origin_start metadata naming its emitted origin instance, even when this type has no input ring. None:
        no count-aligned table or no landed input on tn (the default ot_dp_clk_landing ring and non-landed kits stay as
        they are)."""
        cat = self.ca_type.get(tn) if self.ca else None
        ins = (self.by_type.get(tn) or {}).get("inputs") or ()
        if not cat:
            return None
        buses = {}
        for b in sorted(ins):
            d = {"D": int(cat["rings"][b]["depth"]), "form": "hold_mux"}
            for n in [b] + ([f"cland_dn_ready_{b}", f"cland_dn_fault_{b}"] if self.dataflow else []):
                buses[n] = dict(d)
            buses[f"cland_fstart_in_{b}"] = {"form": "ring_start", "ring": b}    # emitted with every ca landed input
        role = cat["role"]
        origin = None
        if role[0] == "child" and role[1] == START_PIN_IN:
            origin = "u_cland_origin"
        elif role[0] == "strap" and START_PIN_IN in role[1]:
            origin = (f"u_cland_origin_t{role[1].index(START_PIN_IN)}" if len(role[1]) > 1 else "u_cland_origin")
        if origin:
            buses[START_PIN_IN] = {"form": "origin_start", "origin": origin}
        return {"schema": LAND_SLOTS_SCHEMA, "buses": buses} if buses else None

    def manifest(self):
        by_lane = defaultdict(int)
        for r in self.rows:
            by_lane[r["lane"]] += int(r["added_cycles"])
        return dict(schema="opentallas.clock_landing_rtl.v1",
                    implemented=self.emitted_top and self.emitted_types == set(self.types),
                    physical_qualified=False,
                    added_cycles_per_crossing="count_aligned (per crossing)" if self.ca else 3,
                    count_aligned=bool(self.ca),
                    count_straps=self.strap,
                    crossings=len(self.rows), ports=self.rows,
                    lane_added_cycles=dict(sorted(by_lane.items())),
                    types=self.by_type, reset_placements=self.reset_placements,
                    collector=self.collector,
                    observer_source=getattr(self,"observer_source",None),
                    forwarded_clock_only_inputs=self.forwarded_clock_only_inputs,
                    emitted_modules=getattr(self,"emitted_modules",None),
                    remaining_gates=["placed clock/status pins", "landing ring window STA",
                                     "trained region calendar offsets", "token pass"])


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan")
    ap.add_argument("crossings")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    result = requirements(json.loads(Path(args.plan).read_text()), json.loads(Path(args.crossings).read_text()))
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: result[k] for k in ("crossings", "type_count_before", "type_count_after",
                                            "required_new_scalar_pins", "added_live_data_storage_flops")}))
