#!/usr/bin/env python3
"""Standalone, default-off historical HHP clock mesh role proposal. Never installs FT policy."""
import argparse
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import ft_ports as F

TYPE = "kv3_pc__cl5a95b461"
COHORT = "PRIVATE_HISTORICAL_D25_FULLM25"
BUF = "BUFx24_ASAP7_75t_R"
PINS = {
    "canonical_mesh.json.gz": "6294fefcd5db18b1f8c0efe2271a51c63a504278b8cd0216a63795c0fc90f4a6",
    "canonical_place.json.gz": "cb45c2b9dbad9fd69bd0c0f59c4054d9125004598adff8e52260fba5049bff4a",
    "canonical_sites.json.gz": "d25f60c6f22e6921a36d73a850b3bc8a3822f0e5545879ff05e84bd1755513db",
    "historical_ft_manifest.json": "6204f0d885ba697ceb261a6d9cfb9e99b757ff56d4b16d90d3c2ab4ff966307b",
}
MASTER_RECEIPT_SHA = "91547a79f7671f58226daff55050f92ce6c5d662b60fa84481611935b8c85838"
PREP_SHA = "5323c1ed3853aa9ebd8bb191f93631b531391ce475ca5231f4b3df5a921dfed7"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def ancestry(node, incoming, placed, certified_family=None):
    """Trace actual fixed-wire edges; a shared clock label alone is insufficient."""
    path = []
    while node != "port:root":
        require(node not in path, "clock ancestry cycle")
        require(node in placed, "missing ancestry cell")
        cell = placed[node]
        require(cell.get("kind") in ("node", "rep"), "wrong ancestry cell role")
        master = cell.get("lib")
        if master is None and certified_family is not None:
            entry = certified_family.get(node, {})
            require(entry.get("kind") == cell.get("kind"), "missing explicit pinned source-family master receipt")
            master = entry.get("master")
        require(master is not None, "missing actual master or explicit pinned source-family receipt")
        require(master == BUF, "ancestry master/polarity is not certified noninverting BUF")
        require(len(incoming.get(node, [])) == 1, "missing or multiple ancestry drivers")
        path.append(node)
        node = incoming[node][0]["drv"]
    return path + ["port:root"]


def cell_edges(text):
    return {name: (master, a, y) for master, name, a, y in re.findall(
        r"(\w+)\s+(mp_isl[01]_ck[01])\s*\(\.A\((\w+)\),\s*\.Y\((\w+)\)\);", text)}


def load_context(capsule, inputs, prep_path):
    raw = prep_path.read_bytes()
    require(digest(raw) == PREP_SHA, "source receipt differs")
    prep = json.loads(raw)
    require(prep["cohort"] == COHORT and not prep["qualified"], "wrong source cohort")
    data = {}
    for name, sha in PINS.items():
        b = (inputs / name).read_bytes()
        if name.endswith(".gz"):
            b = gzip.decompress(b)
        require(digest(b) == sha, "pinned graph/manifest differs: " + name)
        data[name.split(".")[0]] = json.loads(b)
    for part, info in prep["parts"].items():
        for name, sha in info["source_files_sha256"].items():
            require(digest((capsule / part / "rtl" / name).read_bytes()) == sha,
                    "actual source differs: " + part + "/" + name)
    receipt_bytes = (ROOT / "results/hhp_clock_mesh_role_1102/canonical_master_family.json").read_bytes()
    require(digest(receipt_bytes) == MASTER_RECEIPT_SHA, "pinned master-family receipt differs")
    receipt = json.loads(receipt_bytes)
    require(receipt["canonical_place_decompressed_sha256"] == PINS["canonical_place.json.gz"], "master-family graph differs")
    data["master_family"] = receipt["cells"]
    return prep, data


def proposal(capsule, inputs, prep_path, part, request_type=TYPE, kind="clock", enable=False):
    prep, data = load_context(capsule, inputs, prep_path)
    manifest = data["historical_ft_manifest"]
    require(part in prep["parts"] and part in manifest["parts"], "wrong parent owner")
    rows = [r for r in manifest["arcs"] if r["part"] == part]
    arcs = [{"cell": r["child"] + "." + c["native_cell"], "source": r["input_net"],
             "sink": r["output_net"], "kind": kind} for r in rows for c in r["parallel_cells"]]
    if not enable:
        # The existing generic policy continues to reject this multi-input short.
        return F.declaration(arcs, "historical HHP disabled proposal")
    require(request_type == TYPE and all(r["type"] == TYPE for r in rows), "wrong exact TYPE")
    require(kind == "clock", "only clock mesh role is permitted")
    require(len(rows) == 8 and len(arcs) == 16, "incomplete 16-buffer mesh graph")
    mesh, placed, sites = (data["canonical_" + x] for x in ("mesh", "place", "sites"))
    incoming = {}
    for wire in mesh["fixed_wires"]:
        for load in wire["loads"]:
            incoming.setdefault(load, []).append(wire)
    bound = (capsule / part / "rtl" / (TYPE + "_bound.sv")).read_text()
    wrapper = (capsule / part / "rtl" / (TYPE + ".sv")).read_text()
    raw_edges, public_drivers, joins, paths = [], [], [], {}
    owners = {"kvpc0": "qkd_kvs_pc_h_head_p", **{f"kvpc{k}": "qkd_kvs_pc" for k in (1, 2, 3)}}
    require(set(r["child"] for r in rows) == set(owners), "missing genuine HEAD or BASE owner")
    for row in rows:
        child, module, k = row["child"], row["module"], row["arc_k"]
        require(module == owners[child] and k in (0, 1), "wrong child source/module")
        require(row["role"] == "mesh_driver" and row["output_net"] == "ck_mesh", "wrong clock role/output")
        call = re.search(r"\b" + module + r"\s+u_core_" + child + r"\s*\((.*?)\);", bound, re.S)
        require(call is not None, "actual child instantiation missing")
        for port, net in ((row["input_port"], row["input_net"]), (row["output_port"], "ck_mesh")):
            require(re.search(r"\." + port + r"\(\s*" + net + r"\s*\)", call.group(1)), "actual source edge differs")
        leaf = (capsule / part / "rtl" / (module + ".sv")).read_text()
        edges = cell_edges(leaf)
        require(len(edges) == 4, "raw FT producer census differs")
        fixed = incoming.get(row["driver_pair"][0], [])
        require(len(fixed) == 1 and fixed[0]["name"] == row["input_net"] and fixed[0]["drv"] == row["input_driver"], "wrong actual pre-mesh source")
        require(set(mesh["drivers"][row["mesh_driver_id"]]["cells"]) == set(row["driver_pair"]), "wrong canonical pair")
        paths[row["input_net"]] = ancestry(row["input_driver"], incoming, placed, data["master_family"])
        for j, c in enumerate(row["parallel_cells"]):
            name = f"mp_isl{k}_ck{j}"
            y = row["output_port"] + ("__p1" if j else "")
            require(c["native_cell"] == name and edges.get(name) == (BUF, row["input_port"], y), "raw BUF edge/master differs")
            require(c["mesh_cell"] in fixed[0]["loads"], "driver is not an actual fixed-wire load")
            require(sites["pushdown_cells"][c["mesh_cell"]] == part + "/" + child, "wrong canonical owner")
            require([placed[c["mesh_cell"]]["x"], placed[c["mesh_cell"]]["y"]] == c["die_bbox_ll_um"], "wrong canonical cell site")
            raw_edges.append(dict(owner=child, module=module, cell=name, master=BUF,
                                  A=row["input_port"], Y=y, parent_input=row["input_net"]))
            if j == 0:
                public_drivers.append(dict(owner=child, cell=name, parent_output="ck_mesh"))
            else:
                joins.append(dict(owner=child, private_output=y, public_output=row["output_port"],
                                  parent_output="ck_mesh", intent="physical join; absent in raw RTL"))
    ports = sorted(set(r["input_net"] for r in rows)) + ["ck_mesh"]
    require(len(ports) == 5 and set(ports) == set(prep["parts"][part]["actual_parent_nets"]), "five-port cut differs")
    for port in ports:
        direction = "output" if port == "ck_mesh" else "input"
        for text in (bound, wrapper):
            header = re.sub(r"//[^\n]*", "", text).split(");", 1)[0]
            require(re.search(r"\b" + direction + r"\s+wire\s+" + port + r"\b", header), "actual five-port cut missing")
        require(re.search(r"\." + port + r"\(\s*" + port + r"\s*\)", wrapper), "wrapper cut forwarding differs")
    return dict(schema="opentallas.hhp.intentional_clock_mesh_role.proposal.v1", enabled_by_default=False,
                enabled_for_private_proposal=True, qualified=False, TYPE=TYPE, cohort=COHORT, part=part,
                role="intentional_clock_mesh", kind="clock", common_root="port:root", polarity="noninverting",
                ports=ports, raw_private_edges=raw_edges, source_public_mesh_drivers=public_drivers,
                physical_join_intent=joins, actual_ancestry=paths,
                source_prep_sha256=PREP_SHA, pinned_graphs=PINS,
                master_family_receipt_sha256=MASTER_RECEIPT_SHA,
                generic_ft_policy_changed=False, new_CAD=False,
                holds=["Standalone proposal, not a normal FT declaration or installed waiver",
                       "Physical joins are intent, not already-short raw private outputs",
                       "Private historical cohort only; P1-P7 programme/canonical clock/adoption HOLD",
                       "No characterization, geometry, PG, timing or parent qualification"])


def fixture(result):
    """Clock-only class witness; never a functional parent replacement."""
    lines = ["// Diagnostic clock-role class fixture only; NOT full capsule qualification.",
             "module hhp_clock_mesh_role_fixture (", ",\n".join("input wire " + p for p in result["ports"][:-1]) + ",", "output wire ck_mesh);"]
    for edge in result["raw_private_edges"]:
        lines.append(f"{BUF} {edge['owner']}_{edge['cell']} (.A({edge['parent_input']}), .Y(ck_mesh));")
    return "\n".join(lines + ["endmodule", ""])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capsule", type=Path, required=True)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--source-prep", type=Path, required=True)
    p.add_argument("--part", required=True)
    p.add_argument("--enable-private-proposal", action="store_true")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = proposal(a.capsule, a.inputs, a.source_prep, a.part, enable=a.enable_private_proposal)
    a.out.mkdir(parents=True, exist_ok=False)
    (a.out / "proposal.json").write_text(json.dumps(result, indent=2) + "\n")
    (a.out / "clock_only_fixture.sv").write_text(fixture(result))

if __name__ == "__main__":
    main()
