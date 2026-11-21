"""Parent connections and strict pin receipts for an explicitly unused plain feedthrough."""
import json
import re
from pathlib import Path

import schema as S


def declared(raw, types=None):
    """Return {instance: {slot: slot row}}. A spare is an entire unobserved, unlanded epoch-carrying slot."""
    from gen_rtl import ft_hop_lockup

    parts = raw.get("partitions", [])
    named = [p for p in parts if p.get("spare_ends") and (types is None or p["type"] in types)]
    if not named:
        return {}
    used = {(pr[side]["part"], pr[side]["bus"]): pr for pr in raw.get("ports", []) for side in ("src", "dst")}
    out = {}
    by_type = {}
    for part in named:
        pn, tn = part["name"], part["type"]
        t = raw["partition_types"][tn]
        if not t.get("superset"):
            raise ValueError(f"{pn}: spare FT requires superset")
        names = set(part["spare_ends"])
        slots = {}
        for sl in t.get("ft_slots", []):
            n = sl["name"]
            ends = {n + "_i", n + "_o"}
            if n not in names and not names.intersection(ends):
                continue
            if n not in names and not ends <= names:
                raise ValueError(f"{pn}.{n}: spare FT requires both ends")
            names.difference_update(ends | {n})
            if any((pn, b) in used for b in ends):
                raise ValueError(f"{pn}.{n}: declared spare FT has a connected die port")
            if any(not (sl.get(side + "_face") and sl.get(side + "_window_um") and
                        sl.get(side + "_layers", sl.get("layers"))) for side in ("in", "out")):
                raise ValueError(f"{pn}.{n}: spare FT needs both declared type windows and layers")
            if sl["stations"] < 1:
                raise ValueError(f"{pn}.{n}: spare FT requires a registered station chain")
            type_slots = by_type.setdefault(tn, {})
            if n not in type_slots:
                # A local landing, forwarded clock/start, or count strap needs its own
                # dormant protocol; a zero on the data input cannot implement that.
                clock = t.get("clock", {})
                contract = clock.get("landing_contract", {})
                names_at_clock = [r["name"] for r in contract.get("pins", [])]
                names_at_clock += [r.get("port", "") for r in clock.get("edge_clocks", [])]
                names_at_clock += [r["name"] for r in t.get("count_straps", [])]
                sources = {r["name"] for r in contract.get("collector_local_sources", [])}
                # UNIFY-TOOLS-R3 DORMANT: a landed class slot with its dormant strap (strap_ca_off_<n>_i) keeps its
                # count-aligned ring pins; clock_landings masks the ring and ties its clock / start on this copy
                dormant = {f"fclk_in_{n}_i", f"cland_fstart_in_{n}_i", f"fclk_out_{n}_o", f"cland_fstart_out_{n}_o",
                           f"landing_ready_{n}_i", f"landing_fault_{n}_i", f"strap_ca_k_{n}_i", f"strap_ca_off_{n}_i"} \
                    if f"strap_ca_off_{n}_i" in {r["name"] for r in t.get("count_straps", [])} else set()
                if (ends.intersection(sources) or ends.intersection(contract.get("bands", {})) or
                        any(pin.endswith(("_" + n + "_i", "_" + n + "_o")) and pin not in dormant
                            for pin in names_at_clock)):
                    raise ValueError(f"{pn}.{n}: landing or clock role on declared spare FT")
                if (raw.get("built_station_extra", {}).get(tn, {}).get(n) or
                        (ft_hop_lockup(raw, tn) and (S.ft_hop_xtap(raw, tn, n) or
                         any(S.ft_hop_latched(raw, tn, n, k) for k in range(sl["stations"] - 1))))):
                    raise ValueError(f"{pn}.{n}: spare FT requires a plain station chain")
                type_slots[n] = sl
            slots[n] = sl
        if names:
            raise ValueError(f"{pn}: only whole plain FT spares supported, got {sorted(names)}")
        out[pn] = slots
    for part in parts:
        pn = part["name"]
        for n, sl in by_type.get(part["type"], {}).items():
            if n in out.get(pn, {}):
                continue
            for suf in ("_i", "_o"):
                pr = used.get((pn, n + suf))
                if not pr or pr["width"] != sl["width"] or not S.has_epoch(pr):
                    raise ValueError(f"{pn}.{n}: peer of spare FT must bind both full-width ends with epoch")
    return out


def add_native_chains(binder, slots):
    """Use the same native station emitter and identity for the live and spare copies."""
    if not slots:
        return
    by_type = {}
    for pn, sp in slots.items():
        binder.members.setdefault(pn, [])
        by_type.setdefault(binder.parts[pn]["type"], {}).update(sp)
        for n, sl in sp.items():
            if any(h["slot"] == n for _, h in binder.ft_bus[pn]):
                raise ValueError(f"{pn}.{n}: spare FT has a native crossing")
            # Never add the synthetic hop to links, latency, or lane inventory.
            binder.ft_bus[pn].append((dict(width=sl["width"], lane="declared_spare", src=pn, dst=pn),
                                      dict(slot=n, ibus=n + "_i", obus=n + "_o", stations=sl["stations"])))
    for pn, part in binder.parts.items():
        for n, sl in by_type.get(part["type"], {}).items():
            hops = [(link["width"], hop["stations"], hop["ibus"], hop["obus"])
                    for link, hop in binder.ft_bus[pn] if hop["slot"] == n]
            if hops != [(sl["width"], sl["stations"], n + "_i", n + "_o")]:
                raise ValueError(f"{pn}.{n}: native FT width/stages {hops} disagree with class slot")


def check_native_kit(slots, ports, text, out):
    """An opted-in class kit must contain the native chain and its per-instance parent proof."""
    if not slots:
        return
    receipt_path = Path(out) / "bind_declared_ties.json"
    if not receipt_path.is_file():
        raise ValueError("spare FT kit needs a native bind with parent tie receipts")
    rows = [r for r in json.loads(receipt_path.read_text()) if r.get("scope") == "parent_spare_ft"]
    for pn, declared_slots in slots.items():
        for n, sl in declared_slots.items():
            width = sl["width"] + 1
            ip, op = n + "_i", n + "_o"
            if ports.get(ip) != ("input", width) or ports.get(op) != ("output", width):
                raise ValueError(f"{pn}.{n}: native spare FT kit requires full {width}-bit input and output")
            pattern = r"\bu_ft_" + re.escape(op) + r"_(\d+)\s*\("
            if sorted(map(int, re.findall(pattern, text))) != list(range(sl["stations"])):
                raise ValueError(f"{pn}.{n}: native spare FT chain differs from {sl['stations']} declared stages")
            matches = [r for r in rows if r.get("instance") == pn and r.get("port") == ip]
            if len(matches) != 1 or matches[0].get("value") != 0 or matches[0].get("bits") != list(range(width)):
                raise ValueError(f"{pn}.{n}: missing or mismatched native spare FT parent tie receipt")


def connections(slots):
    for n, sl in sorted(slots.items()):
        yield n + "_i", f"{sl['width'] + 1}'d0"
        yield n + "_o", ""


def write_pads(slots, f, text, ident, masters, *, port_id=None):
    """Verify each explicit tie/open in the emitted top before admitting these exact pins in strict port-bind."""
    if not slots:
        return {}
    import reset_tree as RT
    instances = {m[2]: (m[1], m[3]) for m in RT._WF_INST.finditer(text)}
    path = Path(str(f) + ".pads.json")
    doc = json.loads(path.read_text()) if path.exists() else {}
    ties = {}
    for pn, sp in slots.items():
        inst = ident(pn)
        if inst not in instances:
            raise ValueError(f"spare FT instance {inst} missing from top")
        master, body = instances[inst]
        if master != masters[pn]:
            raise ValueError(f"{inst}: expected spare FT master {masters[pn]}, got {master}")
        entry = doc.setdefault("instances", {}).setdefault(inst, dict(master=master, ports={},
                       reason="Instance-declared spare feedthrough including epoch"))
        if entry["master"] != master:
            raise ValueError(f"{inst}: spare FT master differs from pad declaration")
        for n, value in connections(sp):
            port = port_id(n) if port_id else n
            matches = re.findall(r'\.' + re.escape(port) + r'\s*\(\s*([^)]*?)\s*\)', body)
            if matches != [value]:
                raise ValueError(f"{inst}.{port}: expected spare FT connection {value!r}, got {matches}")
            bounds = [[0, sp[n[:-2]]["width"]]]
            if port in entry["ports"] and entry["ports"][port] != bounds:
                raise ValueError(f"{inst}.{port}: conflicting pad permission")
            entry["ports"][port] = bounds
            if value:
                ties[(inst, port)] = value
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return ties
