p="tools/die_plan/bind.py"; s=open(p).read()
o="""                    for d in t.get("hard_cores", []) for strap, native in (d.get("physical_id_alias") or {}).items()}"""
n="""                    for d in t.get("contents", []) + t.get("hard_cores", [])
                    for strap, native in (d.get("physical_id_alias") or {}).items()}"""
assert s.count(o)==1; open(p,"w").write(s.replace(o,n))
p="tools/die_plan/test_strap_alias.py"; s=open(p).read()
s=s.replace("""def _bind_vehicle(module, alias=True, value=16):""","""def _bind_vehicle(module, alias=True, value=16, leaf_ports=(A,)):""")
o="""    b.F.cells = [SimpleNamespace(path="p.u_su", ports={A: list(range(1, W + 1))}, module=module, params={})]
    b.G.dirs = {0: {A: "input"}}
    b.G.kind = ["leaf"]
    b.members[part] = [0]
    b.rel_of = lambda ci: "u_su"
    b.tparams["src"] = {("strap", "u_su", A, i): [str((value >> i) & 1)] for i in range(W)}
    b.tvals["src"] = {part: {k: v[0] for k, v in b.tparams["src"].items()}}
    b.sinks = {(0, A, i): ("strap",) for i in range(W)}"""
n="""    b.F.cells = [SimpleNamespace(path="p.u_su", ports={q: list(range(1 + W * k, W * (k + 1) + 1))
                                                       for k, q in enumerate(leaf_ports)}, module=module, params={})]
    b.G.dirs = {0: {q: "input" for q in leaf_ports}}
    b.G.kind = ["leaf"]
    b.members[part] = [0]
    b.rel_of = lambda ci: "u_su"
    b.tparams["src"] = {("strap", "u_su", q, i): [str((value >> i) & 1)] for q in leaf_ports for i in range(W)}
    b.tvals["src"] = {part: {k: v[0] for k, v in b.tparams["src"].items()}}
    b.sinks = {(0, q, i): ("strap",) for q in leaf_ports for i in range(W)}"""
assert s.count(o)==1; s=s.replace(o,n)
s+='''

# DIE-HBM-31 plan/binder mapping (OWNER 10-30 (3)(B)): the HBM die binds RTL cuts of the canonical lane core, whose
# leaf exposes the NATIVE lane_lane_id; the declared alias maps it to the parent-tied partition strap.
CUT = "ot_hnx_su_exp__rst3"


def test_binder_alias_maps_native_cut_leaf_to_parent_tied_strap(tmp_path):
    raw, b = _bind_vehicle(CUT, leaf_ports=(N,))
    b.emit(tmp_path)
    assert not any("u_su" in g for g in getattr(b, "emit_gaps", []))
    (nm, d), = b.parent_id_ports["src"].items()
    assert nm.startswith("strap_") and d == dict(leaf="u_su", port=N, width=W)
    rtl = (tmp_path / "rtl" / (raw["partition_types"]["src"]["module"] + ".sv")).read_text()
    assert f"input wire [{W - 1}:0] {nm}" in rtl and f".{N}({nm}" in rtl
    assert {v[nm]["value"] for v in b.parent_id_values.values()} == {16}


@pytest.mark.parametrize("alias,value,leaf_ports", [(False, 16, (N,)), (True, 17, (N,)), (True, 16, (N, A))])
def test_binder_native_cut_leaf_needs_mapping_value_and_one_pin(tmp_path, alias, value, leaf_ports):
    raw, b = _bind_vehicle(CUT, alias, value, leaf_ports)
    if value == 17:            # declared 17, as-built literal 16
        part = next(iter(b.tvals["src"]))
        b.tparams["src"] = {("strap", "u_su", q, i): [str((16 >> i) & 1)] for q in leaf_ports for i in range(W)}
        b.tvals["src"] = {part: {k: v[0] for k, v in b.tparams["src"].items()}}
    b.emit(tmp_path)
    assert any("u_su" in g or "physical_id_alias" in g for g in b.emit_gaps)
    assert not (tmp_path / "rtl/tiny_bound_top.sv").exists()
'''
open(p,"w").write(s); print("ok")
