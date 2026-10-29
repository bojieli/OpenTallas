import pytest
from kvspc_input_collar import transform_wrapper

WRAP = """module qkd_kvs_pc (
    input wire [0:0] ck,
    input wire ft_ck_i_0,
    input wire [7:0] i_next,
    input wire [0:0] rst_n,
    input wire [2:0] strap_id,
    output wire [7:0] out
);
    leaf u_leaf (
        .ck(ck[0]),
        .data(i_next[7:0]),
        .rst_n(rst_n[0]),
        .strap_id(strap_id[2:0]),
        .out(out[7:0])
    );
endmodule
"""

def test_default_is_byte_identical():
    text, receipt=transform_wrapper(WRAP)
    assert text==WRAP and receipt["input_cycles"]==0

def test_coherent_inputs_clocks_straps_unchanged():
    text, receipt=transform_wrapper(WRAP,enabled=True,declared_straps=["strap_id"])
    assert receipt["flops"]==9 and receipt["input_cycles"]==1 and receipt["boot_cycles"]==1
    assert '.data(pcin_i_next[7:0])' in text and '.rst_n(pcin_rst_n[0])' in text
    assert '.strap_id(strap_id[2:0])' in text and '.ck(ck[0])' in text
    assert 'pcin_ck' not in text and 'pcin_ft_ck' not in text and 'pcin_strap' not in text
    assert 'negedge' not in text and 'always @(posedge ck[0])' in text

def test_unknown_strap_is_rejected():
    with pytest.raises(ValueError,match="not an input"):
        transform_wrapper(WRAP,enabled=True,declared_straps=["typo"])

def test_duplicate_transform_is_rejected():
    text,_=transform_wrapper(WRAP,enabled=True)
    with pytest.raises(ValueError,match="already present"):
        transform_wrapper(text,enabled=True)

def test_unconsumed_functional_input_is_rejected():
    with pytest.raises(ValueError,match="no leaf use"):
        transform_wrapper(WRAP.replace('.data(i_next[7:0]),','.data(8\'d0),'),enabled=True)


def test_interior_reset_is_local_without_relocating_edge_ports():
    from kvspc_input_collar import interior_captures, interior_tcl
    pins=[dict(bus="rst_n",bit=0,x=199.128,y=181.44,face="interior"),
          dict(bus="hrst_n",bit=0,x=2.472,y=0.0,face="S")]
    inner=interior_captures(pins,[dict(port="rst_n"),dict(port="hrst_n")])
    assert inner==pins[:1]
    text=interior_tcl(inner)
    assert "{rst_n[0]}" in text and "199.128" in text and "181.44" in text
    assert "ff_put_near" in text and "hrst_n" not in text
