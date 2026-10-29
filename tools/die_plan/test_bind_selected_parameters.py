"""Unknown overrides on selected opaque masters must fail before binding."""
import pytest
import bind_elab as E


def files(tmp_path, decl="parameter W=64, parameter NQ=2", override=".W(128), .NQ(2)"):
    top=tmp_path/"top.sv"; leaf=tmp_path/"selected.sv"
    top.write_text(f"module top(input a,output y);\ncore #({override}) u_c(.a(a),.y(y));\nendmodule\n")
    leaf.write_text(f"module core #({decl})(input a,output y);\nendmodule\n")
    return top,leaf


def test_selected_valid_values_keep_frontend_responsibility(tmp_path):
    t,l=files(tmp_path)
    rows=E.validate_selected_parameters([t],[],[l])
    assert rows[0]["requested"]==["W","NQ"] and rows[0]["declared"]==["NQ","W"]


def test_packed_typed_face_masks_are_declared(tmp_path):
    # Production S81 dsdv_svc_rs_c / sx / rs_up use a packed first mask,
    # followed by inherited-type comma declarations.  Missing the first mask
    # incorrectly rejects their valid overrides before Slang can elaborate.
    t,l=files(tmp_path,decl="parameter logic [39:0] FM={40{1'b1}}, FM_GI=4'hf, parameter bit signed [3:0] FM_UI=4'hf",
              override=".FM(40'h123456789a), .FM_GI(4'h3), .FM_UI(4'h2)")
    rows=E.validate_selected_parameters([t],[],[l])
    assert rows[0]["declared"]==["FM","FM_GI","FM_UI"]
    t.write_text(t.read_text().replace(".FM_UI(4'h2)",".FM_BAD(4'h2)"))
    with pytest.raises(E.ElabError,match="FM_BAD not declared"):
        E.validate_selected_parameters([t],[],[l])


def test_actual_fixed_width_wrong_source_fails(tmp_path):
    t,l=files(tmp_path)
    l.write_text("module core(input a,output y); endmodule\n")
    with pytest.raises(E.ElabError,match=r"core u_c: parameter\(s\) NQ, W not declared.*selected.sv"):
        E.validate_selected_parameters([t],[],[l])


def test_selected_load_order_not_any_compatible_definition(tmp_path):
    t,l=files(tmp_path); old=tmp_path/"fixed.sv"
    old.write_text("module core(input a,output y); endmodule\n")
    with pytest.raises(E.ElabError,match="not declared"):
        E.validate_selected_parameters([t],[],[l,old])
    assert E.validate_selected_parameters([t],[],[old,l])


def test_body_parameter_localparam_and_nested_expressions(tmp_path):
    t,l=files(tmp_path,override=".W((1 << 7)), .NQ($clog2(4))")
    l.write_text("module core(a,y); parameter W=64, NQ=2; localparam FIXED=4; input a; output y; endmodule\n")
    assert E.validate_selected_parameters([t],[],[l])
    t.write_text(t.read_text().replace(".NQ($clog2(4))", ".FIXED(2)"))
    with pytest.raises(E.ElabError,match="FIXED not declared"):
        E.validate_selected_parameters([t],[],[l])


def test_inactive_defines_and_positional_limits(tmp_path):
    t,l=files(tmp_path,override="128, 2")
    assert E.validate_selected_parameters([t],[],[l])
    t.write_text(t.read_text().replace("128, 2", "128, 2, 4"))
    with pytest.raises(E.ElabError,match=r"positional\[2\]"):
        E.validate_selected_parameters([t],[],[l])
    t.write_text("module top;\n`ifdef OLD\ncore #(.BAD(4)) u_bad();\n`else\ncore #(.W(128)) u_good();\n`endif\nendmodule\n")
    assert len(E.validate_selected_parameters([t],[],[l]))==1
    with pytest.raises(E.ElabError,match="BAD not declared"):
        E.validate_selected_parameters([t],[],[l], ["OLD"])


def test_elab_rejects_unknown_before_frontend_runs(tmp_path, monkeypatch):
    t,l=files(tmp_path)
    l.write_text("module core(input a,output y); endmodule\n")
    calls=[]
    monkeypatch.setattr(E,"run_yosys",lambda *a,**k:calls.append(a))
    ab=dict(top="top",frontend="slang",netlist=[str(t)],files=[str(l)],rtl_roots=[])
    with pytest.raises(E.ElabError,match="not declared"):
        E.elab(ab,tmp_path,tmp_path/"out")
    assert calls==[]


def test_repeated_overrides_mask_each_source_once(tmp_path, monkeypatch):
    import die_port_bind as D
    top, leaf = files(tmp_path)
    body = '\n'.join(f'core #(.W("parens ) ( remain text"), .NQ($clog2((1 << 2)))) u_scaling_{i}(.a(a), .y());'
                     for i in range(32))
    top.write_text('module top(input a);\n'+body+'\nendmodule\n')
    mask = D._lexical_mask
    whole_top_calls = []
    def counted(text, strings=False):
        if 'u_scaling_31' in text and text.lstrip().startswith('module top'):
            whole_top_calls.append(strings)
        return mask(text, strings=strings)
    monkeypatch.setattr(D, '_lexical_mask', counted)
    rows = E.validate_selected_parameters([top], [], [leaf])
    assert len(rows) == 32
    assert all(row['requested'] == ['W', 'NQ'] for row in rows)
    # One parse_modules mask and one reused override-validation mask; scaling
    # with instance count here formerly re-scanned the complete die text.
    assert whole_top_calls == [True, True]
