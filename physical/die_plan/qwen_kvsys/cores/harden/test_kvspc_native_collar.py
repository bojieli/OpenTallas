from types import SimpleNamespace
import pytest
from kvspc_native_collar import PARAM, TARGETS, projection, regen_parameters, transform, enabled_in_wrapper, physical_receipt


def source(module):
    widths = {}
    for name, span, _ in projection(module):
        if span is None:
            widths[name] = ""
        else:
            widths[name] = f"[{max(span[0], int(widths.get(name, '[0:0]')[1:].split(':')[0]))}:0]"
    header = ",\n".join(["    input wire ck", "    input wire hck"] +
                         [f"    input wire {w} {n}" for n, w in widths.items()] +
                         ["    output wire out"])
    params = " #(parameter [4:0] PC = 0)" if module.endswith("head_p") else ""
    return f"module {module}{params} (\n{header}\n);\n    leaf u_pc (.ck(ck), .hck(hck), .rst_n(rst_n), .data(i_next), .out(out));\nendmodule\n"


@pytest.mark.parametrize("module,bits", [(TARGETS[0], 1831), (TARGETS[1], 1502)])
def test_exact_projection_default_and_native_body(module, bits):
    before = source(module)
    after, receipt = transform(before, module)
    assert receipt["flops"] == bits and receipt["default"] == 0
    assert f"parameter {PARAM} = 0" in after
    assert ".ck(ck), .hck(hck), .rst_n(pcin_native_rst_n)" in after
    assert ".data(pcin_native_i_next)" in after
    assert "posedge ck" in after and "negedge" not in after
    assert "assign pcin_native_i_next = i_next;" in after
    assert "pcin_pc__land_er_259[260]" in after
    assert "pc__land_er[258]" in after  # eliminated native bits stay direct
    assert "reg [260:0] pcin_pc__land_er" not in after
    if module.endswith("head_p"):
        assert "parameter [4:0] PC = 0" in after
        assert "pcin_pc__ki_15[20]" in after and "pc__ki[21]" in after


def test_double_source_application_rejected():
    after, _ = transform(source(TARGETS[0]), TARGETS[0])
    with pytest.raises(ValueError, match="already present"):
        transform(after, TARGETS[0])


def test_regen_requires_actual_provider_and_prices_each_instance_once():
    cells = [SimpleNamespace(path="pc0", module=TARGETS[0], ytype="a", params={}),
             SimpleNamespace(path="hhp0", module=TARGETS[1], ytype="b", params={})]
    ctx = SimpleNamespace(F=SimpleNamespace(cells=cells), param_defaults={})
    with pytest.raises(ValueError, match="install source before binding"):
        regen_parameters(ctx)
    ctx.param_defaults = {(c.ytype, c.module): {PARAM: "0"} for c in cells}
    rec = regen_parameters(ctx)
    assert rec["params"] == {"pc0": {PARAM: 1}, "hhp0": {PARAM: 1}}
    assert rec["record"]["input_cycles"] == rec["record"]["boot_cycles"] == 1


def test_native_physical_recognition_does_not_add_outer_stage():
    for value in ("1", "32'd1", "1'b1", "32'sd1"):
        assert enabled_in_wrapper(f"leaf #(.{PARAM}({value})) u_leaf ();")
    assert not enabled_in_wrapper(f"leaf #(.{PARAM}(0)) u_leaf ();")
    assert not enabled_in_wrapper(f"parameter {PARAM} = 1;")
    for module, count in zip(TARGETS, (1831,1502)):
        receipt=physical_receipt(module)
        assert receipt["flops"]==count and not receipt["outer_collar_added"]


def test_stage_replaces_preferred_sources_and_composes_existing_rules(tmp_path):
    import importlib.util
    import json
    from kvspc_stage_parent_collar import stage
    normal=tmp_path/"normal.sv";normal.write_text(source(TARGETS[0]))
    hhp=tmp_path/"hhp.sv";hhp.write_text(source(TARGETS[1]))
    hook=tmp_path/"existing.py"
    hook.write_text('def regen(ctx):return {"params":{"other":{"EXISTING":7}},"record":{"kept":True}}\n')
    recipe=tmp_path/"recipe.json"
    recipe.write_text(json.dumps(dict(base=".",files=["normal.sv"],prefer=["normal.sv","hhp.sv"],
                                     compose="existing_compose.json",param_regen=dict(file="existing.py"))))
    out=tmp_path/"new"
    stage(recipe,normal,hhp,out)
    staged=json.loads((out/"recipe_pc_input_collar.json").read_text())
    assert staged["compose"]=="existing_compose.json"
    assert "normal.sv" not in staged["prefer"] and "hhp.sv" not in staged["prefer"]
    assert recipe.read_text().find(PARAM)<0
    cells=[SimpleNamespace(path=n,module=m,ytype=n,params={}) for n,m in zip(("pc","hhp"),TARGETS)]
    ctx=SimpleNamespace(F=SimpleNamespace(cells=cells),param_defaults={(c.ytype,c.module):{PARAM:"0"} for c in cells})
    spec=importlib.util.spec_from_file_location("staged_hook",staged["param_regen"]["file"])
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=module.regen(ctx)
    assert result["params"]["other"]=={"EXISTING":7}
    assert result["params"]["pc"]==result["params"]["hhp"]=={PARAM:1}
