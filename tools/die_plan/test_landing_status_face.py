"""DIE-S81-29 (COORD DIE-S81-28-PARK (2)): a same-region (non-seam) collector status input pin loads only its own
face capture flop (face_guard 'unregistered' on the reduction's reset AND2); +1 boot status cycle, 0 data cycles.
Types without such inputs are unchanged."""
import copy
from clock_landings import Landings, STATUS_FACE_CYCLES


def pin(n, d):
    return dict(name=n, dir=d, width=1, face="E", window_um=[1, 2], layers=["M4"])


A_BODY = "module a_mod (\n input wire clk,\n output wire [4:0] x\n);\n wire rst_root_n; wire rr_t0;\n assign x=0;\nendmodule\n"


def collector_vehicle(seam):
    from test_clock_landings import vehicle
    p, t = vehicle()
    for ty in p["partition_types"].values():
        ty["buses"] += [pin("cland_up_ready", "out"), pin("cland_up_fault", "out")]
    p["partition_types"]["A"]["buses"] += [pin("cland_dn_ready_0", "in"), pin("cland_dn_fault_0", "in")]
    if seam:
        p["partition_types"]["A"]["buses"].append(pin("fclk_in_cland_dn_0", "in"))
        p["partition_types"]["B"]["buses"].append(pin("fclk_out_cland_up", "out"))
    tree = dict(root=[1, 1], n_clock_taps=1, relays=[dict(q="rst_n_t0", d="rst_root_n", xy=[2, 1])])
    t["collector"] = dict(root="a", parts={"a": dict(parent=None, active=True), "b": dict(parent="a", active=True)},
        edges=[dict(src="b", dst="a", dst_index=0, seam=seam)], types={
            "A": dict(mask=dict(active=True, up_seam=False), tree=tree, local_sources=[], children=[
                dict(index=0, tap=0, node="rst_n_t0", seam=seam, ready="cland_dn_ready_0", fault="cland_dn_fault_0", xy_um=[2, 1])]),
            "B": dict(mask=dict(active=True, up_seam=seam), tree=tree, children=[], local_sources=[
                dict(name="y", tap=0, ready="landing_ready_y", fault="landing_fault_y", xy_um=[10, 1.5])])})
    return p, t


def test_same_region_child_gets_own_face_flops():
    p, t = collector_vehicle(seam=False)
    L = Landings(p, t)
    aa = L.type_rtl("A", A_BODY)
    assert "ot_dp_landing_face u_cland_face_ready_0 (.clk(clk), .d(cland_dn_ready_0), .q(cland_dn_fq_ready_0));" in aa
    assert "ot_dp_landing_face u_cland_face_fault_0 (.clk(clk), .d(cland_dn_fault_0), .q(cland_dn_fq_fault_0));" in aa
    # the pin is read exactly once (the face flop D); the reduction reads the flop q
    assert aa.count("(cland_dn_ready_0)") == 1 and aa.count("(cland_dn_fault_0)") == 1
    assert ".ready_i({cland_dn_fq_ready_0})" in aa and ".fault_i({cland_dn_fq_fault_0})" in aa
    assert "u_cland_monitor_0" not in aa and "fclk_in_cland_dn_0" not in aa
    insts = L.reset_placements["A"]["collector"]["instances"]
    faces = [i for i in insts if i["module"] == "ot_dp_landing_face"]
    assert [f["name"] for f in faces] == ["u_cland_face_ready_0", "u_cland_face_fault_0"]
    assert all(f["flops"] == 1 and f["status_cycles_added"] == STATUS_FACE_CYCLES == 1 and f["data_cycles_added"] == 0
               and f["xy_um"] == [2, 1] for f in faces)
    assert L.reset_placements["A"]["collector"]["data_cycles_added"] == 0


def test_seam_child_and_childless_types_unchanged():
    """No same-region input -> no face flop and no new manifest key (default-unchanged form)."""
    p, t = collector_vehicle(seam=True)
    L = Landings(copy.deepcopy(p), copy.deepcopy(t))
    aa = L.type_rtl("A", A_BODY)
    assert "ot_dp_landing_face" not in aa and "cland_dn_fq_" not in aa
    assert "ot_dp_clk_landing #(.W(2)) u_cland_monitor_0" in aa
    assert not [i for i in L.reset_placements["A"]["collector"]["instances"] if i["module"] == "ot_dp_landing_face"]
