#!/usr/bin/env python3
"""HEAD reset START raw exports: re-derive every reset_start_raw_exports row (and its landing pin) from the re-solved
reset tree after a re-solve moved or renumbered relays (reset column mode, rp18).  One rule for the whole class.

    python3 -I tools/s81_head/head_reset_exports.py fix   OLD_PLAN IN_PLAN OUT_PLAN
    python3 -I tools/s81_head/head_reset_exports.py check PLAN            (exit 1 on any bad row)

OLD_PLAN is the last plan whose rows were bound (rp17): it gives each export's pin site and its physical source.
Per type, per row:
  * existing_port rst_o_<k>: the export IS an out port.  If an out of the re-solved tree still sits on the export's
    pin site (<= PIN_TOL_UM), the row reuses that out (renamed if the out index moved) and its source is the deepest
    raw START relay at that out.  Otherwise the row becomes a PRIVATE export at the same pin site.
  * private: source = the same physical relay as in OLD (same xy, same START role, same depth offset from the
    type release) when it exists and is still unused; else the same-role same-offset relay nearest the pin; if the
    OLD row named no relay of the OLD tree (a stale row), the raw-role relay nearest the pin.  Never a relay already
    used by another private row (kit_rtl head_start_raw_private: one export_q per ot_dp_rrelay), nor a relay the
    generated RTL already makes a reader raw export pair (reader START stage on a port-driving relay, r2).
  * every private row has exactly one landing_contract pin named after its port (created at the pin site, M7 out
    ctl, when the row was an existing_port reuse), whose source_* fields name the row's relay.
check: every private row has its pin, private sources are unique and no reader raw export pair, every (instance, net) is a START relay of the
solved tree, pin source fields match, every existing_port names an out that sits on the row's xy.
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))
import reset_tree as RT  # noqa: E402
import schema as S  # noqa: E402

PIN_TOL_UM = 2.0
SAME_UM = 1e-3
RAW_ROLES = ("raw", "boot", "bootstrap_transport")
CREATED = []   # (type, port) of landing pins created for former existing_port reuses


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def pool(T):
    return (RT.start_relays(T) if T.get("start") else [])


def load(path):
    raw = json.loads(Path(path).read_text())
    return raw, S.Plan(raw, str(path))


def pin_template(port, xy):
    return dict(dir="out", epoch=False, kind="ctl", layer="M7", name=port, xy_um=[round(xy[0], 4), round(xy[1], 4)])


def set_pin_source(pin, r):
    pin.update(source_instance=r["name"], source_net=pin["name"], source_output_pin="export_q",
               source_copy_from_net=r["q"], source_registered=True)


def reader_pairs(t, pn, outs, rows):
    """Relays the generated RTL already turns into a reader raw export pair (clock_landings._reader_start_rtl, FLOW-6):
    a landing_reader_start stage whose raw_reset is the plain Q of a relay that also drives an rst_o port gets
    `ot_dp_head_raw_export_pair <relay> (... .export_q(<raw>_reader_raw))`.  That relay's one export_q is taken, so a
    private START export can not also use it.  A stage remapped by landing_raw_branches reads a generated copy, not the
    relay.  A relay drives a port when it is the deepest raw relay on an out site or an existing_port row names it."""
    clock = t.get("clock") or {}
    remapped = {c for b in (clock.get("landing_raw_branches") or []) for c in b.get("consumers", [])}
    port_q = {row["net"] for row in rows if row.get("existing_port")}
    for xy in outs.values():
        at = [r for r in pn if r.get("role") == "raw" and man(r["xy"], xy) < SAME_UM]
        if at:
            port_q.add(max(at, key=lambda r: (r["depth"], r["name"]))["q"])
    by_q = {r["q"]: r for r in pn}
    occ = {}
    for bus, b in sorted(((clock.get("landing_reader_start") or {}).get("branches") or {}).items()):
        for i, st in enumerate((b.get("stages") or []) if isinstance(b, dict) else []):
            q = st.get("raw_reset")
            if f"reader:{bus}:{i}" in remapped or q not in port_q or q not in by_q:
                continue
            occ.setdefault(by_q[q]["name"], f"{q}_reader_raw ({bus} stage {i})")
    return occ


def fix_type(Po, Pn, T_out, tn, log):
    rows = T_out.get("reset_start_raw_exports") or []
    if not rows:
        return 0
    To, Tn = RT.for_type(Po, tn), RT.for_type(Pn, tn)
    po, pn = pool(To), pool(Tn)
    outs = {o[0]: (o[1], o[2]) for o in RT.out_pins(Pn, tn)}
    occupied = reader_pairs(T_out, pn, outs, rows)
    old_rows = {r["port"]: r for r in (Po.types[tn].get("reset_start_raw_exports") or [])}
    pins = T_out.setdefault("clock", {}).setdefault("landing_contract", {}).setdefault("pins", [])
    by_pin = {p["name"]: p for p in pins}
    n = 0
    # pass 1: existing-port reuse that still has an out on its pin site
    private = []
    for row in rows:
        o = old_rows.get(row["port"], row)
        site = tuple(o["xy_um"]) if o.get("existing_port") else tuple((by_pin.get(row["port"]) or o)["xy_um"])
        if o.get("existing_port") or row.get("existing_port"):
            at = sorted(nm for nm, xy in outs.items() if man(xy, site) <= PIN_TOL_UM)
            if at:
                ep = row.get("existing_port") if row.get("existing_port") in at else at[0]
                src = max((r for r in pn if r.get("role") == "raw" and man(r["xy"], outs[ep]) < SAME_UM),
                          key=lambda r: (r["depth"], r["name"]))
                new = dict(port=row["port"], instance=src["name"], net=src["q"], xy_um=list(src["xy"]), existing_port=ep)
                if new != row:
                    log.append(f"{tn}.{row['port']}: reuse {ep} via {src['name']}/{src['q']}")
                    row.clear(); row.update(new); n += 1
                continue
            log.append(f"{tn}.{row['port']}: no out on its pin {list(site)} any more -> private export")
            row.pop("existing_port", None); n += 1
        private.append((row, o, site))
    # pass 2: private rows, physical identity first, unique sources
    used = set(occupied)       # reader raw export pairs already own their relay's export_q
    for nm, why in sorted(occupied.items()):
        if any(row["instance"] == nm for row, _, _ in private):
            log.append(f"{tn}: {nm} is a reader raw export pair {why}: no private export may use it")
    def pick(row, o, site, strict):
        old = next((r for r in po if r["name"] == o.get("instance") and r["q"] == o.get("net")), None)
        if old is None:
            cand = [r for r in pn if r.get("role") in RAW_ROLES and r["name"] not in used]
            return min(cand, key=lambda r: (man(r["xy"], site), r["name"])), "nearest raw (stale OLD row)"
        off = To["depth"] - old["depth"]
        cand = [r for r in pn if r.get("role") == old.get("role") and Tn["depth"] - r["depth"] == off
                and r["name"] not in used]
        same = [r for r in cand if man(r["xy"], old["xy"]) < SAME_UM]
        if same:
            return sorted(same, key=lambda r: r["name"])[0], "same relay"
        if strict:
            return None, None
        return min(cand, key=lambda r: (man(r["xy"], site), r["name"])), f"moved, offset {off}"
    rest = []
    for row, o, site in private:          # physical matches claim their relay first
        r, why = pick(row, o, site, True)
        if r is None:
            rest.append((row, o, site)); continue
        used.add(r["name"]); n += apply(tn, row, r, site, why, by_pin, pins, log)
    for row, o, site in rest:
        r, why = pick(row, o, site, False)
        used.add(r["name"]); n += apply(tn, row, r, site, why, by_pin, pins, log)
    return n


def apply(tn, row, r, site, why, by_pin, pins, log):
    ch = 0
    if (row["instance"], row["net"]) != (r["name"], r["q"]) or man(row["xy_um"], r["xy"]) > SAME_UM:
        log.append(f"{tn}.{row['port']}: {row['instance']}/{row['net']} -> {r['name']}/{r['q']} d{r['depth']} ({why}; "
                   f"{man(r['xy'], site):.1f} um to the pin)")
        row.update(instance=r["name"], net=r["q"], xy_um=list(r["xy"])); ch = 1
    pin = by_pin.get(row["port"])
    if pin is None:
        pin = pin_template(row["port"], site); pins.append(pin); by_pin[row["port"]] = pin
        CREATED.append((tn, row["port"]))
        log.append(f"{tn}.{row['port']}: landing pin created at {pin['xy_um']}"); ch = 1
    before = dict(pin); set_pin_source(pin, r)
    return ch or int(before != pin)


def check(Pn, raw):
    bad = []
    st = (raw.get("clock") or {}).get("landing_network", {}).get("start_tree") or {}
    uses_open = list(st.get("uses", [])) + list(st.get("open", []))
    for tn, t in sorted(raw["partition_types"].items()):
        rows = t.get("reset_start_raw_exports") or []
        if not rows:
            continue
        Tn = RT.for_type(Pn, tn); pn = pool(Tn)
        outs = {o[0]: (o[1], o[2]) for o in RT.out_pins(Pn, tn)}
        pins = {p["name"]: p for p in (t.get("clock") or {}).get("landing_contract", {}).get("pins", [])}
        seen = {}
        occupied = reader_pairs(t, pn, outs, rows)
        parts = [n_ for n_, p_ in Pn.parts.items() if p_["type"] == tn]
        for row in rows:
            src = [r for r in pn if r["name"] == row["instance"] and r["q"] == row["net"]]
            if not src:
                bad.append(f"{tn}.{row['port']}: {row['instance']}/{row['net']} is not a START relay of the solved tree")
            if row.get("existing_port"):
                xy = outs.get(row["existing_port"])
                if xy is None or man(xy, row["xy_um"]) > PIN_TOL_UM:
                    bad.append(f"{tn}.{row['port']}: existing_port {row['existing_port']} not at {row['xy_um']}")
                continue
            if row["instance"] in seen:
                bad.append(f"{tn}.{row['port']}: shares relay {row['instance']} with {seen[row['instance']]}")
            seen[row["instance"]] = row["port"]
            if row["instance"] in occupied:
                bad.append(f"{tn}.{row['port']}: relay {row['instance']} is already the reader raw export pair "
                           f"{occupied[row['instance']]}")
            pin = pins.get(row["port"])
            if pin is None:
                bad.append(f"{tn}.{row['port']}: no landing_contract pin")
            elif sum((u["part"], u["pin"]) in ((pn, row["port"]) for pn in parts) for u in uses_open) != len(parts):
                bad.append(f"{tn}.{row['port']}: not used or declared open exactly once on every instance")
            elif (pin.get("source_instance"), pin.get("source_copy_from_net")) != (row["instance"], row["net"]):
                bad.append(f"{tn}.{row['port']}: pin source {pin.get('source_instance')}/{pin.get('source_copy_from_net')}"
                           f" != row {row['instance']}/{row['net']}")
    return bad


def main(argv):
    if argv[:1] == ["check"] and len(argv) == 2:
        raw, P = load(argv[1]); bad = check(P, raw)
        print("\n".join(bad)); print(json.dumps(dict(bad=len(bad))))
        return 1 if bad else 0
    if argv[:1] == ["fix"] and len(argv) == 4:
        _, Po = load(argv[1]); raw, Pn = load(argv[2]); out = copy.deepcopy(raw); log = []
        n = sum(fix_type(Po, Pn, out["partition_types"][tn], tn, log) for tn in sorted(out["partition_types"])
                if tn in Po.types)
        # a former existing_port reuse had no die-level reader (no start_tree use, no sidecar reset_inputs entry): its new
        # private output launches nothing, so every instance declares it OPEN (landing_contract start_tree: an unused
        # raw output is not a tie), never a fake use.
        st = out["clock"]["landing_network"]["start_tree"]
        have = {(u["part"], u["pin"]) for u in st.get("uses", [])} | {(o["part"], o["pin"]) for o in st.get("open", [])}
        for tn, port in CREATED:
            for pn in sorted(n_ for n_, p_ in Pn.parts.items() if p_["type"] == tn):
                if (pn, port) not in have:
                    st.setdefault("open", []).append(dict(part=pn, pin=port)); n += 1
            log.append(f"{tn}.{port}: declared open on every instance (no die-level reader)")
        Path(argv[3]).write_text(json.dumps(out, indent=1) + "\n")
        print("\n".join(log)); print(json.dumps(dict(changed=n)))
        return 0
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
