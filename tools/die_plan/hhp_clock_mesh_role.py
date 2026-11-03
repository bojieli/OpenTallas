#!/usr/bin/env python3
"""Default-off exact historical HHP clock-role certificate and private normal consumers."""
import argparse
import gzip
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
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
HEAD_HOOK_PINS = {'pc_EN_0': '5b97763f29c05b86a25b27d15ca2737ae367e74e8a7881443491d36d0d5cdb59', 'pc_WN_0': '2333e658acfb47ad82568da1423d1a58319901c6f35aa4efc69803154298f35b'}
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


def closed_reference_census(text, nets, allowed_calls):
    """Fail closed on every role-net reference outside exact declarations/calls.

    This narrow source-family check intentionally rejects unknown syntax rather
    than pretending to parse arbitrary Verilog or infer arbitrary cell directions.
    """
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    for call in allowed_calls:
        require(text.count(call) == 1, "source census expected call missing/duplicated")
        text = text.replace(call, "")
    for net in nets:
        text = re.sub(r"\b(?:input\s+wire|output\s+wire|wire)\s+" + re.escape(net) + r"\s*[,;]", "", text)
    extra = sorted({net for net in nets if re.search(r"\b" + re.escape(net) + r"\b", text)})
    require(not extra, "unclassified extra source driver/use on role nets: " + ", ".join(extra))
    return dict(role_nets=sorted(nets), exact_allowed_calls=len(allowed_calls), unclassified_references=0)


def load_context(capsule, inputs, prep_path, master_receipt_path=None):
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
        require(digest((capsule / part / "historical_HEAD_ft.tcl").read_bytes()) == HEAD_HOOK_PINS[part],
                "genuine HEAD normal physical hook differs")
        for name, sha in info["source_files_sha256"].items():
            require(digest((capsule / part / "rtl" / name).read_bytes()) == sha,
                    "actual source differs: " + part + "/" + name)
    receipt_bytes = (master_receipt_path or ROOT / "results/hhp_clock_mesh_role_1102/canonical_master_family.json").read_bytes()
    require(digest(receipt_bytes) == MASTER_RECEIPT_SHA, "pinned master-family receipt differs")
    receipt = json.loads(receipt_bytes)
    require(receipt["canonical_place_decompressed_sha256"] == PINS["canonical_place.json.gz"], "master-family graph differs")
    data["master_family"] = receipt["cells"]
    return prep, data


def proposal(capsule, inputs, prep_path, part, request_type=TYPE, kind="clock", enable=False, master_receipt_path=None):
    prep, data = load_context(capsule, inputs, prep_path, master_receipt_path)
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
    source_census = {}
    bound_calls = {}
    owners = {"kvpc0": "qkd_kvs_pc_h_head_p", **{f"kvpc{k}": "qkd_kvs_pc" for k in (1, 2, 3)}}
    require(set(r["child"] for r in rows) == set(owners), "missing genuine HEAD or BASE owner")
    for row in rows:
        child, module, k = row["child"], row["module"], row["arc_k"]
        require(module == owners[child] and k in (0, 1), "wrong child source/module")
        require(row["role"] == "mesh_driver" and row["output_net"] == "ck_mesh", "wrong clock role/output")
        call = re.search(r"\b" + module + r"\s+u_core_" + child + r"\s*\((.*?)\);", bound, re.S)
        require(call is not None, "actual child instantiation missing")
        bound_calls[child] = call.group(0)
        for port, net in ((row["input_port"], row["input_net"]), (row["output_port"], "ck_mesh")):
            require(re.search(r"\." + port + r"\(\s*" + net + r"\s*\)", call.group(1)), "actual source edge differs")
        leaf = (capsule / part / "rtl" / (module + ".sv")).read_text()
        edges = cell_edges(leaf)
        require(len(edges) == 4, "raw FT producer census differs")
        if module not in source_census:
            allowed = re.findall(r"\b" + BUF + r"\s+mp_isl[01]_ck[01]\s*\(\.A\(ft_ck_i_[01]\),\s*\.Y\(ft_ck_o_[01](?:__p1)?\)\);", leaf)
            role_nets = {f"ft_ck_{dr}_{i}" for dr in ("i", "o") for i in (0, 1)} | {f"ft_ck_o_{i}__p1" for i in (0, 1)}
            source_census[module] = closed_reference_census(leaf, role_nets, allowed)
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
    for child, call in bound_calls.items():
        expected = Counter(r["input_net"] for r in rows if r["child"] == child)
        expected["ck_mesh"] = 2
        actual = Counter(token for token in re.findall(r"\b\w+\b", call) if token in ports)
        require(actual == expected, "extra role-net connection inside actual child call")
    source_census["bound"] = closed_reference_census(bound, set(ports), list(bound_calls.values()))
    wrapper_call = re.search(r"\b" + TYPE + r"_bound\s*#\(.*?\)\s+u_bound\s*\(.*?\);", wrapper, re.S)
    require(wrapper_call is not None, "normal wrapper bound call missing")
    actual = Counter(token for token in re.findall(r"\b\w+\b", wrapper_call.group(0)) if token in ports)
    require(actual == Counter({net: 2 for net in ports}), "extra role-net connection inside wrapper call")
    source_census["wrapper"] = closed_reference_census(wrapper, set(ports), [wrapper_call.group(0)])
    return dict(schema="opentallas.hhp.intentional_clock_mesh_role.proposal.v1", enabled_by_default=False,
                enabled_for_private_proposal=True, qualified=False, TYPE=TYPE, cohort=COHORT, part=part,
                role="intentional_clock_mesh", kind="clock", common_root="port:root", polarity="noninverting",
                ports=ports, raw_private_edges=raw_edges, source_public_mesh_drivers=public_drivers,
                physical_join_intent=joins, actual_ancestry=paths, closed_source_reference_census=source_census,
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

REQUEST_FILE = '.private_hhp_clock_mesh/request.json'
REQUEST_SCHEMA = 'opentallas.hhp.private_clock_mesh_request.v1'



def private_config_values(kit):
    """Accept only the normal generated literal family, never a partial Make evaluator."""
    text = (Path(kit) / 'config.mk').read_text().replace('\\\n', ' ')
    unique = {'PLATFORM', 'DESIGN_NAME', 'VERILOG_FILES', 'VERILOG_DEFINES', 'VERILOG_TOP_PARAMS',
              'VERILOG_INCLUDE_DIRS', 'SYNTH_INCLUDE_DIRS', 'SYNTH_BLACKBOXES',
              'OT_PRIVATE_HHP_CLOCK_MESH', 'OT_RTL_LINT_FLATTEN', 'TC_LIB_FILES', 'BC_LIB_FILES'}
    values = {}
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'(?:override\s+)?export\s+([A-Za-z_][A-Za-z0-9_]*)\s+=\s*(.*)', line)
        require(match is not None, f'unsupported private generated config assignment/directive at line {number}')
        key, value = match.groups()
        require(not any(c in value for c in ('`', '#', ';')), 'unsupported private config literal: ' + key)
        if '$' in value:
            prefix = {'TC_LIB_FILES': '$(TC_NLDM_LIB_FILES)', 'BC_LIB_FILES': '$(BC_NLDM_LIB_FILES)'}.get(key)
            require(prefix is not None and value.startswith(prefix) and '$' not in value[len(prefix):]
                    and all(re.fullmatch(r'/work/macros/[A-Za-z0-9_.-]+\.lib(?:\.gz)?', x)
                            for x in value[len(prefix):].split()), 'unsupported private config expansion: ' + key)
        require(key not in unique or key not in values, 'duplicate private source config assignment: ' + key)
        values[key] = value.split()
    return values

def private_enabled(kit):
    return private_config_values(kit).get('OT_PRIVATE_HHP_CLOCK_MESH') == ['1']


def _inside(kit, name):
    root = Path(kit).resolve()
    path = (root / name).resolve()
    require(path.is_relative_to(root), 'private clock context escapes the kit')
    return path


def actual_source_config(kit):
    values = private_config_values(kit)
    expected = {'PLATFORM': ['asap7'], 'VERILOG_DEFINES': ['-DSYNTHESIS'], 'VERILOG_TOP_PARAMS': [],
                'VERILOG_INCLUDE_DIRS': [], 'SYNTH_INCLUDE_DIRS': []}
    profile = {}
    for name, value in expected.items():
        actual = values.get(name, [])
        require(actual == value, 'actual parameter/define/include profile differs: ' + name)
        profile[name] = actual
    return profile


def validate_private_request(kit):
    """Fresh whole-capsule/graph proof plus exact actual kit source readset; no trusted caller proof dict."""
    kit = Path(kit)
    require(private_enabled(kit), 'private HHP clock role is disabled')
    request = json.loads((kit / REQUEST_FILE).read_text())
    actual_source_config(kit)
    require(request.get('schema') == REQUEST_SCHEMA and request.get('enabled') is True,
            'explicit private request schema/enable required')
    require(request.get('TYPE') == TYPE and request.get('cohort') == COHORT, 'wrong private TYPE/cohort')
    paths = {key: _inside(kit, request[key]) for key in
             ('capsule', 'inputs', 'source_prep', 'master_receipt', 'certificate')}
    fresh = proposal(paths['capsule'], paths['inputs'], paths['source_prep'], request['part'],
                     request_type=request['TYPE'], kind='clock', enable=True,
                     master_receipt_path=paths['master_receipt'])
    require(json.loads(paths['certificate'].read_text()) == fresh, 'private clock certificate is stale/edited')
    prep = json.loads(paths['source_prep'].read_text())
    expected = prep['parts'][request['part']]['source_files_sha256']
    cfg = private_config_values(kit)
    require(cfg.get('DESIGN_NAME') == [TYPE], 'private clock subject is not exact parent TYPE')
    blackboxes = cfg.get('SYNTH_BLACKBOXES', [])
    require(blackboxes in ([], ['qkd_kvs_pc']), 'only real BASE may be blackboxed; genuine HEAD must remain soft')
    source_values = cfg.get('VERILOG_FILES', [])
    require(source_values, 'private clock subject needs one exact VERILOG_FILES assignment')
    actual = {}
    for token in source_values:
        require(token.startswith('/work/rtl/'), 'private source is outside normal kit rtl directory')
        name = token.removeprefix('/work/rtl/')
        require('/' not in name and name not in actual, 'duplicate/non-flat private source member')
        actual[name] = digest(_inside(kit, 'rtl/' + name).read_bytes())
    require(actual == expected, 'actual kit readset differs from whole certified source; macro projection requires separate exact join')
    if blackboxes:
        native_base_receipt(kit, request)
    certificate_sha = digest(json.dumps(fresh, sort_keys=True, separators=(',', ':')).encode())
    return fresh, certificate_sha


def certificate_arcs(cert):
    return [dict(cell=f"u_bound.u_core_{r['owner']}.{r['cell']}", source=r['parent_input'], sink='ck_mesh', kind='clock')
            for r in cert['raw_private_edges']]


def stage_private_context(kit, bundle, *, top, sources, synth_blackboxes=()):
    """Normal generator opt-in: stage complete private DATA closure before first FT call."""
    import shutil
    kit, bundle = Path(kit), Path(bundle)
    require(top == TYPE, 'private generator context is for the exact HHP TYPE only')
    require(tuple(synth_blackboxes) in ((), ('qkd_kvs_pc',)), 'only genuine BASE hard macros may be registered; HEAD remains soft')
    target = kit / '.private_hhp_clock_mesh'
    require(not target.exists(), 'private context destination must be fresh')
    # The bundle contains a literal request and its complete immutable data closure.
    for file in bundle.rglob('*'):
        require(not file.is_symlink(), 'private context bundle must not contain symlinks')
    shutil.copytree(bundle, target)
    text = f'export PLATFORM = asap7\nexport DESIGN_NAME = {top}\nexport VERILOG_FILES = {" ".join(sources)}\nexport VERILOG_DEFINES = -DSYNTHESIS\nexport OT_PRIVATE_HHP_CLOCK_MESH = 1\n'
    if synth_blackboxes:
        text += 'export SYNTH_BLACKBOXES = ' + ' '.join(synth_blackboxes) + '\n'
    # Honest partial generator source config; the completed config is revalidated below.
    config_path = kit / 'config.mk'
    if config_path.is_file():
        old_config = config_path.read_text()
        require('OT_PRIVATE_HHP_CLOCK_MESH' not in old_config, 'private context already enabled')
        config_path.write_text(old_config + '\nexport OT_PRIVATE_HHP_CLOCK_MESH = 1\n')
    else:
        config_path.write_text(text)
    cert, sha = validate_private_request(kit)
    return cert, sha


def private_declaration(kit, arcs, source):
    cert, cert_sha = validate_private_request(kit)
    expected = sorted((f"u_bound.u_core_{r['owner']}.{r['cell']}", r['parent_input'], 'ck_mesh', 'clock')
                      for r in cert['raw_private_edges'])
    require(all(set(a) == {'cell', 'source', 'sink', 'kind'} for a in arcs), 'private arcs need exact typed fields')
    actual = sorted((a['cell'], a['source'], a['sink'], a['kind']) for a in arcs)
    require(actual == expected, 'private FT declaration does not match exact sixteen-buffer graph')
    pairs = {}
    for cell, src, dst, kind in actual:
        pairs.setdefault((src, dst, kind), []).append(cell)
    ports = [dict(name=n, direction='OUTPUT' if n == 'ck_mesh' else 'INPUT') for n in sorted(cert['ports'])]
    out_arcs = [dict(source=s, sink=d, kind=k, cells=sorted(cells)) for (s, d, k), cells in sorted(pairs.items())]
    return dict(schema=F.SCHEMA, source=source, ports=ports, arcs=out_arcs, sha256=F.digest(ports, out_arcs),
                private_clock_mesh_role=dict(schema=cert['schema'], certificate_sha256=cert_sha,
                                             TYPE=TYPE, part=cert['part'], cohort=COHORT,
                                             common_root=cert['common_root'], polarity=cert['polarity'],
                                             physical_joins='Separate actual native join evidence required; not supplied by declaration'))


def verify_private_install(kit, declaration):
    arcs = [dict(cell=cell, source=a['source'], sink=a['sink'], kind=a['kind'])
            for a in declaration.get('arcs', []) for cell in a.get('cells', [])]
    fresh = private_declaration(kit, arcs, declaration.get('source'))
    require(fresh == declaration, 'installed private FT declaration is stale/edited')



def actual_native_mesh_inventory(kit, design):
    """Use the real elaborated top/instance graph, including parameter-derived module identity."""
    cert, cert_sha = validate_private_request(kit)
    modules = design.get('modules', {})
    require(TYPE in modules, 'native JSON lacks exact configured top')
    top = modules[TYPE]
    require('u_bound' in top.get('cells', {}), 'native JSON lacks actual u_bound instance')
    bound_cell = top['cells']['u_bound']
    module_name = bound_cell['type']
    require(module_name in modules, 'native actual bound module missing')
    bound = modules[module_name]
    for name in cert['ports']:
        require(len(top['ports'][name]['bits']) == 1 and bound_cell['connections'][name] == top['ports'][name]['bits'],
                'actual native wrapper cut forwarding differs')
        require(len(bound['ports'][name]['bits']) == 1 and isinstance(bound['ports'][name]['bits'][0], int),
                'actual native cut is constant or not scalar')
    top_cut_bits = {top['ports'][name]['bits'][0] for name in cert['ports']}
    require(len(top_cut_bits) == 5, 'native wrapper aliases distinct cut ports')
    require(len({bound['ports'][name]['bits'][0] for name in cert['ports']}) == 5, 'native bound aliases distinct cut ports')
    for name, cell in top.get('cells', {}).items():
        if name != 'u_bound':
            require(not any(top_cut_bits.intersection(b for b in bits if isinstance(b, int))
                            for bits in cell.get('connections', {}).values()), 'extra actual native wrapper cut use')
    bit = bound['ports']['ck_mesh']['bits'][0]
    require(bound['ports']['ck_mesh']['direction'] == 'output', 'native mesh is not an output')
    for name in cert['ports'][:-1]:
        require(bound['ports'][name]['direction'] == 'input', 'native cut direction differs')
    owner_modules = {'kvpc0': 'qkd_kvs_pc_h_head_p', **{f'kvpc{k}': 'qkd_kvs_pc' for k in (1, 2, 3)}}
    expected = []
    expected_loads = set()
    for owner, child_module in owner_modules.items():
        child = bound['cells']['u_core_' + owner]
        require(child['type'] == child_module, 'actual native child TYPE differs')
        edges = [r for r in cert['raw_private_edges'] if r['owner'] == owner and not r['Y'].endswith('__p1')]
        for edge in edges:
            expected.append((edge['Y'], 'u_core_' + owner, child_module))
            expected_loads.add(('u_core_' + owner, edge['A'], bound['ports'][edge['parent_input']]['bits'][0]))
            require(child['connections'][edge['Y']] == [bit], 'actual native public mesh edge differs')
            require(child['connections'][edge['A']] == bound['ports'][edge['parent_input']]['bits'],
                    'actual native pre-mesh input edge differs')
    drivers = []
    input_bits = {bound['ports'][name]['bits'][0] for name in cert['ports'][:-1]}
    for name, cell in bound.get('cells', {}).items():
        directions = cell.get('port_directions', {})
        for port, bits in cell.get('connections', {}).items():
            if bit not in bits and not input_bits.intersection(x for x in bits if isinstance(x, int)):
                continue
            require(port in directions, 'native driver direction is unknown')
            if directions[port] == 'input':
                require(bit not in bits, 'actual native data consumer on mesh output')
                require(len(bits) == 1 and (name, port, bits[0]) in expected_loads, 'extra actual native pre-mesh input consumer')
            if directions[port] in ('output', 'inout'):
                require(not input_bits.intersection(x for x in bits if isinstance(x, int)), 'native cell drives a pre-mesh input')
                if bit in bits:
                    require(bits == [bit] and directions[port] == 'output', 'native mesh driver is not exact scalar output')
                    drivers.append((port, name, cell['type']))
    require(sorted(drivers) == sorted(expected), 'complete actual native driver census differs')
    return dict(certificate_sha256=cert_sha, actual_elaborated_module=module_name,
                actual_native_public_drivers=drivers,
                native_json_sha256=digest(json.dumps(design, sort_keys=True, separators=(',', ':')).encode()))

def classify_native_clock_conflict(kit, log, native_rc, elaborated):
    """Only one exact native check problem with complete real public-driver inventory is typed clock mesh."""
    cert, cert_sha = validate_private_request(kit)
    inventory = actual_native_mesh_inventory(kit, elaborated)
    require(native_rc == 1, 'only the known native check failure status can be classified')
    problem = [ln for ln in log.splitlines() if re.match(r'^Warning: .*', ln) and
               re.search(r'driver|logic loop|conflict|undriven', ln)]
    require(len(problem) == 1, 'other/missing native check problems')
    header = re.fullmatch(r'Warning: multiple conflicting drivers for (.*):', problem[0])
    require(header is not None and header[1].replace('\\', '') == (inventory['actual_elaborated_module'] + '.ck_mesh').replace('\\', ''),
            'native conflict is not exact certified bound clock mesh')
    block = log.split(problem[0], 1)[1].splitlines()[1:]
    driver_lines = []
    for line in block:
        if not line.startswith(' '):
            break
        if line.strip():
            driver_lines.append(line.strip())
    actual = []
    for line in driver_lines:
        m = re.fullmatch(r'port (ft_ck_o_[01])\[0\] of cell (u_core_kvpc[0-3]) \((qkd_kvs_pc(?:_h_head_p)?)\)', line)
        require(m is not None, 'unclassified actual native driver on clock mesh')
        actual.append(tuple(m.groups()))
    modules = {'kvpc0': 'qkd_kvs_pc_h_head_p', **{f'kvpc{k}': 'qkd_kvs_pc' for k in (1, 2, 3)}}
    expected = [(f'ft_ck_o_{k}', 'u_core_' + owner, module) for owner, module in modules.items() for k in (0, 1)]
    require(sorted(actual) == sorted(expected), 'actual native mesh driver inventory differs')
    errors = re.findall(r'^ERROR:.*$', log, re.M)
    require(len(errors) == 1 and re.fullmatch(r"ERROR: Found (?:and reported )?1 problems? in 'check -assert'\.", errors[0]),
            'other native errors cannot be classified')
    return dict(role='intentional_clock_mesh', certificate_sha256=cert_sha, native_check_rc=native_rc,
                native_elaborated_inventory=inventory,
                native_problem=problem[0], actual_native_public_drivers=actual,
                private_parallel_joins='Not asserted by lint; require actual native physical evidence',
                scope='Private exact source only; generic driver/data rejection unchanged')

NATIVE_BASE_RECEIPT_SHA = '77efedbab1e1463d4a31f458a01e128aaf4c7162c8486cf9fc5994d72810bf27'


def native_base_receipt(kit, request):
    path = _inside(kit, request['base_native_join'])
    require(digest(path.read_bytes()) == NATIVE_BASE_RECEIPT_SHA, 'actual BASE native join receipt differs')
    receipt = json.loads(path.read_text())
    require(receipt['master'] == 'qkd_kvs_pc' and receipt['qualified'] is False, 'wrong actual BASE view class')
    for name, sha in receipt['model_sha256'].items():
        require(digest((Path(kit) / 'macros' / name).read_bytes()) == sha, 'staged real BASE model differs: ' + name)
    return receipt


def install_generated_partition(kit, bundle, type_name, macros):
    """Exact private partition hook. No M7 adapter, fake pin, source alias or canonical plan mutation."""
    kit = Path(kit)
    require(type_name == TYPE, 'private partition hook is for exact TYPE only')
    selected = [m for m in macros if m[1] == 'qkd_kvs_pc']
    require(len(selected) == 3, 'private historical partition requires three registered genuine BASE views')
    require(not any(m[1] == 'qkd_kvs_pc_h_head_p' for m in macros), 'genuine HEAD must remain soft')
    cfg = (kit / 'config.mk').read_text()
    require('SYNTH_BLACKBOXES' not in cfg, 'private case needs explicit clean BASE blackbox registration')
    (kit / 'config.mk').write_text(cfg + '\nexport SYNTH_BLACKBOXES = qkd_kvs_pc\n')
    cert, cert_sha = stage_private_context(kit, bundle, top=TYPE,
        sources=[], synth_blackboxes=('qkd_kvs_pc',))
    request = json.loads((kit / REQUEST_FILE).read_text())
    receipt = native_base_receipt(kit, request)
    expected = {r['inst']: r for r in receipt['parent_macro_sites']}
    require({m[0] for m in selected} == set(expected), 'wrong real BASE macro owners')
    for inst, module, _lef, _lib, x, y, orient in selected:
        r = expected[inst]
        require(module == r['master'] and abs(x-r['x_um']) < 1e-7 and abs(y-r['y_um']) < 1e-7 and orient == r['orient'],
                'actual registered BASE parent pose differs: ' + inst)
    prep = json.loads(_inside(kit, request['source_prep']).read_text())
    shapes = prep['parts'][cert['part']]['actual_cut_shapes']
    require(set(shapes) == set(cert['ports']), 'actual five-port native shape inventory differs')
    pins_path = kit / 'pins.json'
    rows = json.loads(pins_path.read_text())
    require(isinstance(rows, list), 'private partition expects ordinary generated pin rows')
    existing = {r['bus'] if r.get('bit') is None else f"{r['bus']}[{r['bit']}]" for r in rows}
    require(not (existing & set(cert['ports'])), 'private cut already placed/classified')
    logical, native_rows = [], []
    lines = ['# Exact PRIVATE historical native multiPORT clock cut; no M7 replacement or via credit.',
             'set ot_mp_u [[ord::get_db_block] getDbUnitsPerMicron]']
    for name in cert['ports']:
        boxes = [[s['layer'], *[round(float(v), 9) for v in s['rect_um']]] for s in shapes[name]]
        require(all(b[0] == ('M9' if name == 'ck_mesh' else 'M1') for b in boxes), 'wrong actual native cut layer')
        layer, a, b, c, d = boxes[0]
        x, y = round((a+c)/2, 6), round((b+d)/2, 6)
        native_rows.append(dict(bus=name, bit=None, layer=layer, x=x, y=y, face='island',
                                native_rects=boxes, declared_native_shape=True,
                                private_clock_mesh_certificate_sha256=cert_sha))
        logical.append(dict(name=name, layer=layer, x=x, y=y))
        lines += [f'set ot_mp_bt [[ord::get_db_block] findBTerm {{{name}}}]',
                  'if {$ot_mp_bt eq "NULL" || $ot_mp_bt eq ""} {error "PRIVATE_CLOCK missing actual source BTerm"}',
                  '$ot_mp_bt setSigType CLOCK', 'set ot_mp_net [$ot_mp_bt getNet]',
                  'if {$ot_mp_net eq "NULL" || $ot_mp_net eq ""} {error "PRIVATE_CLOCK disconnected actual source BTerm"}',
                  '$ot_mp_net setSigType CLOCK',
                  'foreach ot_mp_old [$ot_mp_bt getBPins] {odb::dbBPin_destroy $ot_mp_old}',
                  'set ot_mp_bp [odb::dbBPin_create $ot_mp_bt]', '$ot_mp_bp setPlacementStatus FIXED']
        for layer, *rect in boxes:
            coords = ' '.join(f'[expr {{int(round({v:.9f}*$ot_mp_u))}}]' for v in rect)
            lines.append(f'odb::dbBox_create $ot_mp_bp [[ord::get_db_tech] findLayer {layer}] {coords}')
    (kit / 'io.tcl').write_text((kit / 'io.tcl').read_text() + '\n' + '\n'.join(lines) + '\n')
    pins_path.write_text(json.dumps(rows + native_rows, indent=1) + '\n')
    pb = kit / 'port_bind_pins.json'
    data = json.loads(pb.read_text())
    data += [dict(bus=name, bit=None) for name in cert['ports']]
    pb.write_text(json.dumps(data, indent=1) + '\n')
    decl = F.declaration(certificate_arcs(cert), 'PRIVATE exact historical source and actual BASE native joins',
                         private_clock_mesh_kit=kit)
    F.install(kit, decl)
    metadata = dict(enabled_by_default=False, TYPE=TYPE, part=cert['part'], cohort=COHORT,
                    certificate_sha256=cert_sha, source_prep_sha256=PREP_SHA,
                    master_family_sha256=MASTER_RECEIPT_SHA, graph_sha256=PINS,
                    base_native_join_sha256=NATIVE_BASE_RECEIPT_SHA,
                    actual_BASE_private_joins='Native PC0355 HDL/DEF and exact canonical owner pose join',
                    HEAD_private_joins='Genuine source producer/runtime guard only; native NOT RUN',
                    canonical_adoption=False, parent_qualification=False, logical_pins=logical)
    hook = _inside(kit, request['capsule']) / cert['part'] / 'historical_HEAD_ft.tcl'
    require(digest(hook.read_bytes()) == HEAD_HOOK_PINS[cert['part']], 'genuine HEAD hook changed')
    hook_name = 'private_hhp_HEAD_ft.tcl'
    require(not (kit / hook_name).exists(), 'HEAD physical hook destination must be fresh')
    hook_text = hook.read_text()
    # The original normal producer is relative to the bound parent. The actual
    # normal partition source has one wires-only u_bound wrapper around it.
    for owner in range(4):
        hook_text = hook_text.replace(f'u_core_kvpc{owner}', f'u_bound.u_core_kvpc{owner}')
    (kit / hook_name).write_text(hook_text)
    for filename, action, prepend in [('face_keep_release.tcl', 'ot_ft_keep', False),
                                      ('face_flops.tcl', 'ot_ft_place', True),
                                      ('face_flops_release.tcl', 'ot_ft_check', True),
                                      ('cts_post.tcl', 'ot_ft_check', False),
                                      ('grt_post.tcl', 'ot_ft_check', False)]:
        path = kit / filename
        require(path.is_file(), 'normal physical hook missing: ' + filename)
        text = path.read_text()
        require('private_hhp_HEAD_ft' not in text, 'HEAD hook already installed')
        call = 'source /work/' + hook_name + '; ' + action + '\n'
        path.write_text(call + text if prepend else text + '\n' + call)
    metadata['genuine_HEAD_source_hook_sha256'] = HEAD_HOOK_PINS[cert['part']]
    metadata['genuine_HEAD_partition_hook_sha256'] = digest((kit / hook_name).read_bytes())
    metadata['physical_source_namespace'] = 'u_bound.'
    metadata['HEAD_runtime_hooks'] = ['POST_SYNTH keep', 'PRE_GLOBAL_PLACE actual p1 short/place/check',
                                      'PRE_DETAIL_PLACE check', 'POST_CTS check', 'POST_GLOBAL_ROUTE check']
    metadata['native_PG_birth'] = 'NOT RUN; future native jobs require separately qualified canonical before-RC protection'
    (kit / 'private_clock_mesh.json').write_text(json.dumps(metadata, indent=1) + '\n')
    return logical, metadata

if __name__ == "__main__":
    main()
