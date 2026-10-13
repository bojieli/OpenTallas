#!/usr/bin/env python3
"""Expand the retired attention-half parents into real hard cells.

Elaboration uses the production half RTL and the closed Liberty interfaces. No
half timing model is invented. The small fpipe registers become padded existing
136-bit banks, with exactly one register edge per original stage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWS = {
    "ot_attn_bank_sn544": "physical/hbm_attn_tile_r/bank_v12/sn544_rec/view",
    "ot_attn_bank_sn136": "physical/hbm_attn_tile_r/bank_v12/sn136_rec/view",
    "ot_attn_bank_ew544": "physical/hbm_attn_tile_r/bank_v12/ew544_rec/view",
    "ot_attn_bank_ew136": "physical/hbm_attn_tile_r/bank/ot_attn_bank_ew136",
    "ot_attn_tile_m6h1q": "physical/hbm_attn_tile_r/quad_b_tc/04424cd9f_pka/view",
    "ot_attn_lo_root": "physical/ref_tile/hattn_lo_root/views/ot_attn_lo_root",
    "ot_attn_hi_merge": "physical/ref_tile/hattn_hi_merge/views/ot_attn_hi_merge",
    "ot_attn_ks_entry": "physical/ref_tile/hattn_ks_entry/views/ot_attn_ks_entry",
}
PARAMS = {
    "lo": dict(CG=1, ROWEW=1, NK=3, NC=1, NR=2, PMID=3, NFR=4,
               NLL=3, NXP=3, LDKR=16),
    "hi": dict(CG=1, ROWEW=1, PMID=2, NFC=2, NL=8, NLL=3, NI=6),
}


def module(text, name):
    match = re.search(r"\bmodule\s+" + re.escape(name) + r"\b.*?\bendmodule", text, re.S)
    if not match:
        raise ValueError(f"missing module {name}")
    return match.group()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle_connections(endpoints):
    """Keep exact Yosys bit identities while coalescing parallel bus lanes."""
    result = []
    for bit, eps in endpoints.items():
        eps = sorted(eps, key=lambda e: (e["instance"], e["port"]))
        prev = result[-1] if result else None
        if (prev and bit.isdigit() and prev["bits"][-1].isdigit()
                and int(bit) == int(prev["bits"][-1]) + 1
                and len(eps) == len(prev["endpoints"])
                and all(e["instance"] == q["instance"] and e["port"] == q["port"]
                        and e["lsb"] == q["lsb"] + q["width"]
                        for e, q in zip(eps, prev["endpoints"]))):
            prev["bits"].append(bit)
            for ep in prev["endpoints"]:
                ep["width"] += 1
        else:
            result.append(dict(net=f"n{bit}", bits=[bit], endpoints=[dict(e) for e in eps],
                               kind="constant" if bit in ["0", "1", "x"] else "signal"))
    return result


def bundle_boundary(boundary):
    result = []
    for row in sorted(boundary, key=lambda e: (e["parent_port"], e["child_instance"], e["child_port"], e["parent_lsb"])):
        prev = result[-1] if result else None
        if (prev and all(row[k] == prev[k] for k in ["parent_port", "child_instance", "child_port"])
                and row["parent_lsb"] == prev["parent_lsb"] + prev["width"]
                and row["child_lsb"] == prev["child_lsb"] + prev["width"]):
            prev["width"] += 1
        else:
            result.append(dict(row))
    return result


def candidate_placement(half, cells):
    old = ROOT / f"physical/hbm_attn_tile_r/half_v11/hfd_attn_half_{half}/macro_placement.tcl"
    pattern = r"-macro_name \{([^}]*)\} -location \{([\d.]+) ([\d.]+)\} -orientation (\w+)"
    places = {n.replace("\\", ""): (float(x), float(y), o)
              for n, x, y, o in re.findall(pattern, old.read_text())}
    if half == "lo":
        places["g_rt.u_rt"] = (850.014, 300.24, "R0")
        places["u_kse"] = (1250.046, 20.25, "R0")
        # Local input clusters around the formatter's actual port faces.
        for prefix, stage, count, x, y in [("u_pc", 1, 3, 610, 300),
                                         ("u_pk", 3, 2, 610, 440),
                                         ("u_pr", 2, 3, 1170, 300),
                                         ("u_pks", 2, 3, 1170, 440)]:
            for c in range(count):
                places[f"{prefix}.gn.g_s[{stage}].g_c[{c}].g_sn.u_b"] = (x, y + 34 * c, "R0")
        for c in range(3):
            places[f"u_pks.gn.g_s[0].g_c[{c}].g_sn.u_b"] = (1370, 20 + 34*c, "R0")
            places[f"u_pks.gn.g_s[1].g_c[{c}].g_sn.u_b"] = (1295, [234, 300, 370][c], "R0")
            places[f"u_pc.gn.g_s[1].g_c[{c}].g_sn.u_b"] = (660 + 40*c, 285 - 34*c, "R0")
            places[f"g_y0.u_mid.gn.g_s[2].g_c[{c}].g_sn.u_b"] = (840, 810 + 110*c, "R0")
        for c in range(2):
            places[f"u_pk.gn.g_s[2].g_c[{c}].g_sn.u_b"] = (700, 200 + 34*c, "R0")
        places["u_pr.gn.g_s[1].g_c[0].g_sn.u_b"] = (1330, 174, "MX")
        places["u_pq.gn.g_s[1].g_c[0].g_sn.u_b"] = (1450, 122, "R0")
        places["u_pq.gn.g_s[2].g_c[0].g_sn.u_b"] = (1130, 155, "MX")
        for s, (x, y) in enumerate([(1590, 122), (1550, 156), (1160, 122), (900, 240)]):
            places[f"u_pqx.u_hard.gn.g_s[{s}].g_c[0].g_sn.u_b"] = (x, y, "R0")
        places["u_pq.gn.g_s[3].g_c[0].g_sn.u_b"] = (900, 206, "R0")
        for c in range(3):
            places[f"g_y0.u_mid.gn.g_s[0].g_c[{c}].g_sn.u_b"] = (800 + 108 * c, 620, "R0")
            places[f"g_y0.u_mid.gn.g_s[1].g_c[{c}].g_sn.u_b"] = (800 + 108 * c, 700, "R0")
            places[f"g_xpp.u_xpp.gn.g_s[0].g_c[{c}].g_sn.u_b"] = (800 + 108 * c, 654, "R0")
            places[f"u_fr.gn.g_s[0].g_c[{c}].g_sn.u_b"] = (620, 520 + 34 * c, "MX")
    else:
        places["g_mt.u_mt"] = (1570, 0, "R0")
        for c in range(3):
            places[f"g_y1.u_mid.gn.g_s[0].g_c[{c}].g_sn.u_b"] = (840, 250 + 110*c, "R0")
        places["g_y1.u_mid.gn.g_s[0].g_c[2].g_sn.u_b"] = (895, 410, "R0")
    for row in cells:
        x, y, orient = places[row["instance"]]
        row.update(xy_um=[round(round(x / .432) * .432, 6), round(round(y / 2.16) * 2.16, 6)],
                   orientation=orient)


def geometry_ledger(component):
    rows = component["children"]
    errors = []
    width, height = component["outline_um"]
    for i, a in enumerate(rows):
        ax, ay = a["xy_um"]
        if ax < 0 or ay < 0 or ax + a["w_um"] > width or ay + a["h_um"] > height:
            errors.append(dict(kind="outside", instance=a["instance"]))
        for b in rows[i + 1:]:
            bx, by = b["xy_um"]
            if max(ax, bx) < min(ax + a["w_um"], bx + b["w_um"]) and max(ay, by) < min(ay + a["h_um"], by + b["h_um"]):
                errors.append(dict(kind="overlap", instances=[a["instance"], b["instance"]]))
    by = {r["instance"]: r for r in rows}
    pin_cache = {}
    for row in rows:
        master = row["logical_module"]
        if master in pin_cache:
            continue
        text = (ROOT / row["view_lef"]).read_text()
        pins = {}
        for name, body in re.findall(r"\bPIN\s+(\S+)\s*(.*?)\n\s*END\s+\S+", text, re.S):
            rect = re.search(r"RECT\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)", body)
            if rect:
                x0, y0, x1, y1 = map(float, rect.groups())
                pins[name] = ((x0 + x1) / 2, (y0 + y1) / 2)
        pin_cache[master] = pins
    cuts = {axis: [dict(at_um=extent * f, bits=0) for f in [.25, .5, .75]]
            for axis, extent in [("x", width), ("y", height)]}
    seams = {}
    for conn in component["connections"]:
        if conn["kind"] == "constant":
            continue
        eps = conn["endpoints"]
        # Clock is separately distributed and balanced, not a data-stage wire.
        if all(e["port"] == "clk" for e in eps):
            continue
        for offset in range(len(conn["bits"])):
            points = []
            for e in eps:
                r = by[e["instance"]]
                pins = pin_cache[r["logical_module"]]
                name = f'{e["port"]}[{e["lsb"] + offset}]'
                point = pins.get(name, pins.get(e["port"]))
                if point is None:
                    raise ValueError(f"missing real LEF pin {r['logical_module']}/{name}")
                x, y = point
                if r["orientation"] in ["MY", "R180"]:
                    x = r["w_um"] - x
                if r["orientation"] in ["MX", "R180"]:
                    y = r["h_um"] - y
                points.append((x + r["xy_um"][0], y + r["xy_um"][1], e.get("direction")))
            if len(points) < 2:
                continue
            drivers = [p for p in points if p[2] == "output"]
            sinks = [p for p in points if p[2] != "output"]
            # Fanout HPWL covers the whole tree; a stage's wire reach is each
            # driver->capture segment, not the sum of its two branches.
            span = max((abs(s[0] - d[0]) + abs(s[1] - d[1])
                        for d in (drivers or points) for s in (sinks or points)), default=0)
            key = tuple(sorted({e["instance"] for e in eps}))
            rec = seams.setdefault(key, dict(instances=list(key), bits=0, max_hpwl_um=0))
            rec["bits"] += 1
            rec["max_hpwl_um"] = max(rec["max_hpwl_um"], round(span, 3))
            for axis, dim in [("x", 0), ("y", 1)]:
                for cut in cuts[axis]:
                    if min(p[dim] for p in points) < cut["at_um"] < max(p[dim] for p in points):
                        cut["bits"] += 1
    long = [r for r in seams.values() if r["max_hpwl_um"] > 500]
    for axis, extent in [("x", height), ("y", width)]:
        # Local component channels can use M2..M7. Conservative 128nm pitch
        # lower-bounds capacity on each directional layer, reserving 40% for PG
        # and other users. Actual child OBS remove tracks on EACH layer.
        for cut in cuts[axis]:
            layer_capacity = {}
            for layer in (["M2", "M4", "M6"] if axis == "x" else ["M3", "M5", "M7"]):
              blocked = []
              for r in rows:
                x, y = r["xy_um"]
                # Count the actual view's OBS, allowing die tracks over closed
                # leaves when their top layer is below the cut's die layer.
                text = (ROOT / r["view_lef"]).read_text()
                obs = text.split("\n  OBS", 1)[-1] if "\n  OBS" in text else ""
                for part in re.split(r"\bLAYER\s+", obs)[1:]:
                    if not part.startswith(layer + " ") and not part.startswith(layer + ";"):
                        continue
                    for rect in re.findall(r"RECT\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)", part):
                        x0, y0, x1, y1 = map(float, rect)
                        if r["orientation"] in ["MY", "R180"]:
                            x0, x1 = r["w_um"] - x1, r["w_um"] - x0
                        if r["orientation"] in ["MX", "R180"]:
                            y0, y1 = r["h_um"] - y1, r["h_um"] - y0
                        if axis == "x" and x+x0 < cut["at_um"] < x+x1:
                            blocked.append((y+y0, y+y1))
                        if axis == "y" and y+y0 < cut["at_um"] < y+y1:
                            blocked.append((x+x0, x+x1))
              merged = []
              for start, end in sorted(blocked):
                if merged and start <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], end)
                else:
                    merged.append([start, end])
              free = extent - sum(b - a for a, b in merged)
              layer_capacity[layer] = dict(free_channel_um=round(free, 3), usable_tracks=int(free / .128 * .6))
            cut.update(layer_capacity=layer_capacity, usable_tracks=sum(r["usable_tracks"] for r in layer_capacity.values()),
                       layers="M2..M7 in component channels, actual LEF OBS excluded; conservative128nm pitch")
            cut["ratio"] = round(cut["bits"] / max(1, cut["usable_tracks"]), 3)
    return dict(schema="opentallas.native_component.geometry.v1", errors=errors,
                cuts=cuts, long_data_seams=long, max_data_hpwl_um=max(r["max_hpwl_um"] for r in seams.values()),
                verdict="PASS" if not errors and not long and all(c["ratio"] <= .6 for v in cuts.values() for c in v) else "FAIL",
                note="Pin-level logical HPWL and conservative channel ledger; routed RC and clock closure still required.")


def prepare(out):
    tile = (ROOT / "rtl/hdc/v41x/ot_hdc_v41x_attn_die_tile_b.sv").read_text()
    half = (ROOT / "rtl/hdc/v41x/ot_hdc_v41x_attn_die_half_b.sv").read_text()
    # Synthesis never parameterises the hardened quad.
    text = "`define OT_ATTN_QCG\n"
    text += module(tile, "ot_attn_bpipe") + "\n" + module(tile, "ot_attn_bpipe136") + "\n"
    text += """
module ot_attn_fpipe #(parameter W=1, parameter N=1)
 (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
  // Same bank semantics, one edge per stage. Spare bits are tied low.
  ot_attn_bpipe136 #(.W(W),.N(N)) u_hard (.clk(clk),.d(d),.q(q));
endmodule
"""
    text += module(half, "hfd_attn_half_lo") + "\n" + module(half, "hfd_attn_half_hi") + "\n"
    # Dead initial guards are not synthesis cells; params are pinned above.
    text = re.sub(r"initial if \([^;]*?\$fatal\([^;]*?;", "", text)
    (out / "native_source.sv").write_text(text)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--yosys", default="yosys")
    a = p.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    prepare(out)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    children = {}
    for name, directory in VIEWS.items():
        view = ROOT / directory
        lef = view / f"{name}.lef"
        lint = subprocess.run(["python3", str(ROOT / "tools/hier_contract/child_lint.py"),
                               str(lef), "--libs", str(view), "--json"],
                              capture_output=True, text=True, check=True)
        report = json.loads(lint.stdout)
        (out / f"{name}_child_lint.json").write_text(json.dumps(report, indent=1) + "\n")
        children[name] = dict(logical_module=name, view_lef=str(lef.relative_to(ROOT)),
                             view_lib={c: str((view / f"{name}_{c}.lib").relative_to(ROOT))
                                       for c in ["tt", "ff", "ss"]},
                             w_um=report["info"]["W"], h_um=report["info"]["H"],
                             pg_top=report["info"]["pg_layer"], closure_status="closed_leaf",
                             source_commit=source,
                             sha256={f.name: digest(f) for f in view.iterdir()
                                     if f.suffix in [".lef", ".lib"]})
    for half, params in PARAMS.items():
        top = f"hfd_attn_half_{half}"
        script = "\n".join(f'read_liberty -lib "{ROOT / d / (n + "_tt.lib")}"'
                           for n, d in VIEWS.items())
        script += f'\nread_verilog -sv "{out / "native_source.sv"}"\n'
        script += "chparam " + " ".join(f"-set {k} {v}" for k, v in params.items()) + f" {top}\n"
        script += f"hierarchy -check -top {top}\nproc\nflatten\nopt_clean\ncheck -assert\n"
        script += f'write_json "{out / (half + ".netlist.json")}"\n'
        script += f'write_verilog -noattr "{out / (half + ".v")}"\n'
        path = out / f"{half}.ys"
        path.write_text(script)
        with (out / f"{half}.elaboration.log").open("w") as log:
            subprocess.run([a.yosys, "-Q", "-s", str(path)], stdout=log, stderr=subprocess.STDOUT, check=True)
        netlist = json.loads((out / f"{half}.netlist.json").read_text())["modules"][top]
        cells = netlist["cells"]
        unknown = sorted({v["type"] for v in cells.values()} - set(VIEWS))
        if unknown:
            raise ValueError(f"soft cells remain: {unknown}")
        endpoints = {}
        for instance, cell in cells.items():
            for port, bits in cell["connections"].items():
                for i, bit in enumerate(bits):
                    endpoints.setdefault(str(bit), []).append(dict(instance=instance, port=port, lsb=i, width=1,
                                                                  direction=cell["port_directions"][port]))
        boundary = []
        ports = {}
        for port, desc in netlist["ports"].items():
            ports[port] = dict(direction=desc["direction"], width=len(desc["bits"]),
                               role="clock" if port == "ck" else "data")
            for i, bit in enumerate(desc["bits"]):
                for ep in endpoints.get(str(bit), []):
                    boundary.append(dict(parent_port=port, parent_lsb=i, width=1,
                                         child_instance=ep["instance"], child_port=ep["port"], child_lsb=ep["lsb"]))
        component = dict(schema="opentallas.native_component.v1", component=f"attention_{half}",
                         logical_module=top, source_commit=source, params=params,
                         outline_um=[1778.52, 1263.6 if half == "lo" else 689.04],
                         boundary_ports=ports,
                         children=[dict(children[v["type"]], instance=k, xy_um=None, orientation="R0")
                                   for k, v in cells.items()],
                         connections=bundle_connections(endpoints),
                         boundary_binding=bundle_boundary(boundary),
                         ownership=dict(owner="Codex:hbm_norm_attn_physical", integration_owner="Codex:hbm_die_compiler",
                                        legacy_half_route="retired; expand directly into native die children"),
                         unresolved=["Actual die/cluster registered-seam STA, detailed routing and IR remain pending.",
                                     "Die clock distribution must balance actual child ETM insertion.",
                                     "External ports must use real boundary bindings; no whole-half ETM is provided."],
                         closed=False)
        candidate_placement(half, component["children"])
        ledger = geometry_ledger(component)
        (out / f"{half}.geometry.json").write_text(json.dumps(ledger, indent=1) + "\n")
        component["geometry_verdict"] = ledger["verdict"]
        exact = out / "fpipe_exact.log"
        mutant = out / "fpipe_mutant.log"
        component["additional_exactness"] = dict(
            mechanism="W39,N4 fpipe -> padded closed sn136 banks, same four register edges",
            proof="SAT arbitrary input/initial-state equivalence after four fill edges, ten edges checked",
            positive="PASS" if exact.exists() and "no model found: SUCCESS!" in exact.read_text() else "pending",
            negative="FAIL as required" if mutant.exists() and "model found: FAIL!" in mutant.read_text() else "pending",
            retained_transaction_gate="results/rtl/hbm_attn_twolevel_lockh_20261012")
        (out / f"{half}.component.json").write_text(json.dumps(component, indent=1) + "\n")
        (out / f"{half}.placement.tcl").write_text("\n".join(
            "place_macro -macro_name {" + r["instance"] + "} -location {" + str(r["xy_um"][0]) + " "
            + str(r["xy_um"][1]) + "} -orientation " + r["orientation"] + " -exact"
            for r in component["children"]) + "\n")
        print(f"{half}: {len(cells)} real child instances; {len(boundary)} boundary bindings; no soft cells")


if __name__ == "__main__":
    main()
