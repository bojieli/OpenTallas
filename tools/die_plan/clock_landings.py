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


def network_lane_cycles(plan):
    """Exact nominal data cycles from source-bound physical forwarded edges.

    Monitor edges add boot time only. Native fixed_cycles is left intact.
    The endpoint names are checked, so arbitrary clock metadata cannot price
    a functional lane or silently add a second copy of a physical crossing.
    """
    net=plan.get("clock",{}).get("landing_network")
    if not net:return {}
    if net.get("data_cycles_per_crossing")!=3:raise LandingError("clock landing network requires the proved nominal +3 contract")
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
        out[owners[pid][0]]+=3
    return dict(out)


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
    for r in table["ports"]:
        p = ports[r["port"]]
        sp, sb, dp, db = p["src"]["part"], p["src"]["bus"], p["dst"]["part"], p["dst"]["bus"]
        if (sp, dp, int(p["width"])) != (r["src"], r["dst"], int(r["width"])):
            raise LandingError(f"stale clock landing endpoints/width on {r['port']}")
        masks[sp]["outputs"].add(sb)
        masks[dp]["inputs"].add(db)
        lanes[r["lane"]] += 3
        pin_refs.append(dict(port=r["port"], lane=r["lane"], src=sp, dst=dp,
                             src_bus=sb, dst_bus=db, width=p["width"],
                             required_src_pin=f"fclk_out_{sb}",
                             required_dst_pins=[f"fclk_in_{db}", f"landing_ready_{db}", f"landing_fault_{db}"],
                             extra_cycles=3))
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
                nominal_added_cycles_per_crossing=3,
                pending=["reserve forwarded-clock and observed status pin tracks", "split nonuniform landing masks",
                         "update lane/R8/calendar price", "emit actual landing RTL", "ring window STA and token pass"])


class LandingError(ValueError):
    pass


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
    def __init__(self, plan, table, *, require_geometry=True):
        self.plan = plan
        self.collector = table.get("collector")
        self.dataflow = bool(self.collector) and self.collector.get("monitor", "reset") == "dataflow"
        if self.collector and self.collector.get("monitor", "reset") not in ("reset", "dataflow"):
            raise LandingError(f"clock landing: unknown monitor mode {self.collector.get('monitor')}")
        self.parts = {p["name"]: p for p in plan["partitions"]}
        self.types = plan["partition_types"]
        ports = {p["id"]: p for p in plan["ports"]}
        self.rows = []
        self.region = {}
        self.emitted_types = set()
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
            row = dict(r, src_bus=sb, dst_bus=db, added_cycles=3,
                       module="ot_dp_clk_landing", ring_depth=4, ring_offset=2,
                       ring_read_registered=True)
            self.rows.append(row)
            self.ins[dp][db] = row
            self.outs[sp].add(sb)
        # All copies of a type must expose identical hardware. Re-plan a type
        # split rather than changing only the first bound replica's wrapper.
        masks = defaultdict(dict)
        for pn, p in self.parts.items():
            mask = (tuple(sorted(self.ins[pn])), tuple(sorted(self.outs[pn])))
            masks[p["type"]].setdefault(mask, []).append(pn)
        bad = {tn: list(ms.values()) for tn, ms in masks.items() if len(ms) > 1}
        if bad:
            raise LandingError(f"clock landing TYPE_SPLIT required: {bad}")
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
                if (tb is None)!=bool(info["mask"].get("observer")) or (tb is not None and tb not in mask[1]):
                    raise LandingError(f"clock landing {tn}: dataflow tree bus {tb} is not one of its landed outputs")
                if not mask[0]:raise LandingError(f"clock landing {tn}: dataflow monitor needs a landed input (ring reset)")
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

    def type_rtl(self, tn, text, base=None):
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
        for b in mask["outputs"]:
            extra.append(f"    output wire fclk_out_{b}")
            logic.append(f"    assign fclk_out_{b} = clk;")
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
            geom = next((x for x in t.get("buses", []) if x["name"] == b), None)
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
            taps = t.get("clock", {}).get("taps", [])
            if hard_tree:
                tap, xy = None, [x, y]
            elif taps:
                tap = min(range(len(taps)), key=lambda i: abs(taps[i]["xy"][0]-x) + abs(taps[i]["xy"][1]-y))
                xy = taps[tap]["xy"]
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
            if self.dataflow:
                extra += [f"    input wire cland_dn_ready_{b}", f"    input wire cland_dn_fault_{b}"]
            if self.collector:
                logic.append(f"    wire landing_ready_{b}, landing_fault_{b};")
            else:
                extra += [f"    output wire landing_ready_{b}",f"    output wire landing_fault_{b}"]
            landed = f"cland_{b}"
            body = re.sub(r"\b" + re.escape(b) + r"\b", landed, body)
            if self.dataflow:
                # ring W+2: {fault, ready} of the sender's status ride the spare padded ring bits under the same
                # forwarded write clock; no extra data cycle, no die-top status wire beside the bus.
                ring = f"cland_ring_{b}"
                logic += [f"    wire [{w+1}:0] {ring};", f"    wire [{w-1}:0] {landed};",
                          f"    assign {landed} = {ring}[{w-1}:0];",
                          f"    ot_dp_clk_landing #(.W({w+2})) u_cland_{b} (",
                          f"        .fclk(fclk_in_{b}), .clk(clk), .rst_n({reset}), .d({{cland_dn_fault_{b}, cland_dn_ready_{b}, {b}}}), .q({ring}),",
                          f"        .ready(landing_ready_{b}), .fault(landing_fault_{b}));",
                          f"    wire cland_ok_{b} = {ring}[{w}] && landing_ready_{b} && !landing_fault_{b};",
                          f"    wire cland_bad_{b} = landing_fault_{b} || (landing_ready_{b} && {ring}[{w+1}]);"]
                continue
            logic += [f"    wire [{w-1}:0] {landed};",
                      f"    ot_dp_clk_landing #(.W({w})) u_cland_{b} (",
                      f"        .fclk(fclk_in_{b}), .clk(clk), .rst_n({reset}), .d({b}), .q({landed}),",
                      f"        .ready(landing_ready_{b}), .fault(landing_fault_{b}));"]
        if self.dataflow:
            body = self._dataflow_monitor(tn, key, mask, collector_info, extra, logic, body)
        elif active_collector:
            import landing_collector as LC
            if collector_info["mask"].get("observer"):
                logic.append("    wire cland_up_ready, cland_up_fault;")
            else:extra += ["    output wire cland_up_ready", "    output wire cland_up_fault"]
            if collector_info["mask"]["up_seam"]:
                extra.append("    output wire fclk_out_cland_up")
                logic.append("    assign fclk_out_cland_up = clk;")
            sources=list(collector_info["local_sources"])
            for ch in collector_info["children"]:
                i=ch["index"]
                extra += [f"    input wire {ch['ready']}", f"    input wire {ch['fault']}"]
                src=dict(ch,name=f"child{i}")
                if ch["seam"]:
                    extra.append(f"    input wire fclk_in_cland_dn_{i}")
                    reset=LC.raw(ch.get("node",f"rst_n_t{ch.get('tap',0)}"))
                    if not re.search(r"\bwire\b[^;]*\b"+reset+r"\b",body):
                        raise LandingError(f"{tn}: raw monitor receiver reset {reset} missing")
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

    def _dataflow_monitor(self, tn, key, mask, info, extra, logic, body):
        """Registered dataflow monitor: local = AND(landing_ready) / OR(landing_fault), aggregate = AND(in_ok) /
        OR(in_bad) over every landed input (in_ok includes the local ring ready), registered
        local_registered_depth times. Every output pin gets its OWN dedicated output register (the last stage):
        the tree bus carries the aggregate, every other landed output the local status. The observer type keeps
        the aggregate on cland_up_ready/fault for gate_observer (never new IO)."""
        ins = list(mask["inputs"]); n = len(ins)
        depth = int(info["local_registered_depth"])
        if depth < 1:raise LandingError(f"{tn}: dataflow monitor depth {depth} < 1")
        rp = self.reset_placements[tn]
        root_xy = info.get("collector_root_xy")
        # One existing raw ring reset (nearest to the collector root): the monitor must train before START.
        def dist(b):
            xy = rp[b]["xy_um"];return (abs(xy[0]-root_xy[0])+abs(xy[1]-root_xy[1])) if root_xy else 0, b
        rst = rp[min(ins, key=dist)]["net"]
        ready_l = ", ".join(f"landing_ready_{b}" for b in ins); fault_l = ", ".join(f"landing_fault_{b}" for b in ins)
        ok_l = ", ".join(f"cland_ok_{b}" for b in ins); bad_l = ", ".join(f"cland_bad_{b}" for b in ins)
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
        for b in mask["outputs"]:
            extra += [f"    output wire cland_up_ready_{b}", f"    output wire cland_up_fault_{b}"]
            if b == tree_bus:
                collect(f"u_cland_up_{b}", final_n, final_in[0], final_in[1], f"cland_up_ready_{b}", f"cland_up_fault_{b}")
                outputs.append(dict(bus=b, carries="aggregate", registered_depth=depth))
            else:
                collect(f"u_cland_up_{b}", n, ready_l, fault_l, f"cland_up_ready_{b}", f"cland_up_fault_{b}")
                outputs.append(dict(bus=b, carries="local", registered_depth=1))
        if tree_bus is None:
            spec = self.collector.get("observer") or {}
            if "OPEN" in (spec.get("module"), spec.get("instance_suffix"), spec.get("fault_port"), spec.get("ready_port")):
                raise LandingError(f"{tn}: dataflow monitor observer RTL ports still OPEN in the sidecar")
            logic.append("    wire cland_up_ready, cland_up_fault;")
            collect("u_cland_up_observer", final_n, final_in[0], final_in[1], "cland_up_ready", "cland_up_fault")
            body = gate_observer(body, self.collector["observer"])
        rp["monitor"] = dict(mode="dataflow", raw_reset=rst, depth=depth, tree_bus=tree_bus, stages=stages,
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
        local_observer=self.collector and self.collector.get("observer")
        if not local_observer:names += ["clock_landing_ready", "clock_landing_fault"]
        match = re.search(r"(?m)^module (\w+) \(([^;]*)\);", text)
        if not match:
            raise LandingError("clock landing: binder non-ANSI die header not found")
        header = f"module {match.group(1)} ({match.group(2)}, " + ", ".join(names) + ");"
        text = text[:match.start()] + header + text[match.end():]
        decl = [f"    input wire clk_region_{ident(r)};" for r in clocks]
        if not local_observer:
            decl += (["    output wire clock_landing_ready;","    output wire clock_landing_fault;"] if self.collector else
                     [f"    output wire [{n-1}:0] clock_landing_ready;",f"    output wire [{n-1}:0] clock_landing_fault;"])
        fwd = {(r["src"], r["src_bus"]): f"clock_landing_fwd_{ident(r['src'])}__{ident(r['src_bus'])}"
               for r in self.rows}
        decl += [f"    wire {w};" for w in sorted(set(fwd.values()))]
        mon = {}
        if self.dataflow:
            # one wire pair per sender status pin (a source bus fanning out to several sinks shares its pin)
            mon = {(r["src"], r["src_bus"]): f"cland_mon_{ident(r['src'])}__{ident(r['src_bus'])}" for r in self.rows}
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
            body, count = re.subn(r"\.clk\(clk_\w+\)", f".clk(clk_region_{ident(self.region[pn])})", m.group(2), count=1)
            if count != 1:
                raise LandingError(f"clock landing: default clock connection not found on {pn}")
            conn = [f"        .fclk_out_{b}({fwd[(pn,b)]})" for b in sorted(self.outs[pn])]
            if self.dataflow:
                for b in sorted(self.outs[pn]):
                    conn += [f"        .cland_up_ready_{b}({mon[(pn,b)]}_ready)", f"        .cland_up_fault_{b}({mon[(pn,b)]}_fault)"]
            for b, r in sorted(self.ins[pn].items()):
                i = index[(pn,b)]
                conn += [f"        .fclk_in_{b}({fwd[(r['src'],r['src_bus'])]})"]
                if self.dataflow:
                    w = mon[(r["src"], r["src_bus"])]
                    conn += [f"        .cland_dn_ready_{b}({w}_ready)", f"        .cland_dn_fault_{b}({w}_fault)"]
                elif not self.collector:
                    conn += [f"        .landing_ready_{b}(clock_landing_ready[{i}])",f"        .landing_fault_{b}(clock_landing_fault[{i}])"]
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
        self.emitted_top = True
        return text

    def manifest(self):
        by_lane = defaultdict(int)
        for r in self.rows:
            by_lane[r["lane"]] += 3
        return dict(schema="opentallas.clock_landing_rtl.v1",
                    implemented=self.emitted_top and self.emitted_types == set(self.types),
                    physical_qualified=False, added_cycles_per_crossing=3,
                    crossings=len(self.rows), ports=self.rows,
                    lane_added_cycles=dict(sorted(by_lane.items())),
                    types=self.by_type, reset_placements=self.reset_placements,
                    collector=self.collector,
                    observer_source=getattr(self,"observer_source",None),
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
