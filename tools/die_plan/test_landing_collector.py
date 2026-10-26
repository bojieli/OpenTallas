import pytest
from landing_collector import build_local


def tree():
    return dict(root=[0,0],relays=[
        dict(q="rst_n_t0",d="rst_root_n",xy=[100,0]),
        dict(q="rst_n_t1",d="rst_n_t0",xy=[200,0]),
        dict(q="rst_n_t2",d="rst_root_n",xy=[0,300])])


def test_reverse_tree_prunes_unused_child_and_publishes_real_depth():
    t=tree();s=[dict(name="ring",tap=1,ready="r",fault="f",xy_um=[200,0])]
    body="wire rst_root_n;\nwire rr_t0;\n"
    r=build_local(t,s,body)
    assert r["depth"]==3
    assert r["max_hop_um"]==100
    assert all("rst_n_t2" not in x for x in r["rtl"])
    assert sum(i["module"]=="ot_dp_landing_collect" for i in r["instances"])==3
    assert any(i["role"]=="raw pre-START reset copy" for i in r["instances"] if "role" in i)
    assert ".ready_o(cland_up_ready)" in "\n".join(r["rtl"])
    assert all("1'b" not in x for x in r["rtl"])


def test_no_active_source_emits_no_status_pin_tie():
    assert build_local(tree(),[],"")["rtl"]==[]


def test_long_reversed_edge_fails_instead_of_unregistered_shortcut():
    t=tree();t["relays"][1]["xy"]=[600,0]
    s=[dict(name="ring",tap=1,ready="r",fault="f",xy_um=[600,0])]
    with pytest.raises(ValueError,match="exceeds405"):
        # Spaces are intentionally flexible in the diagnostic below.
        try:build_local(t,s,"wire rr_t0;")
        except ValueError as e:raise ValueError(str(e).replace(" ",""))


def test_real_two_inputs_remain_two_inputs():
    s=[dict(name="a",tap=0,ready="ra",fault="fa"),dict(name="b",tap=0,ready="rb",fault="fb")]
    r=build_local(tree(),s,"wire rr_t0;")
    assert any(i.get("active_inputs")==2 for i in r["instances"])
    assert any("{ra, rb}" in line for line in r["rtl"])
