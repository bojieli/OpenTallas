"""HBM-BIND-5: SFU ctl and hub HC subtree32 parent cut maps compose with exact terminal equality (synthetic flats)."""
import collections
import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "die_plan"))
import bind_elab as E  # noqa: E402
from bind_compose import compose  # noqa: E402


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Rules:
    def part_of(self, path):
        return "p"


def nets(F):
    nc, dr = collections.defaultdict(set), collections.defaultdict(list)
    for c in F.cells:
        for p, bs in c.ports.items():
            for b in bs:
                if isinstance(b, int):
                    nc[b].add(c.path)
                    if c.dirs[p] == "output":
                        dr[b].append(c.path)
    top = {b for _, bs in F.top_ports.values() for b in bs if isinstance(b, int)}
    return nc, dr, top


def sfu_flat():
    F = E.Flat()
    F.new(40)
    F.top_ports = {"clk": ("input", [1]), "rst": ("input", [2]), "din": ("input", [3, 4])}
    L, G = "leaf", "glue"
    F.cells = [
        E.Cell("s.u_core.u_rst", "ot_rst_relay", {}, dict(clk=[1], rst_n_in=[2], rst_n=[5, 6]),
               dict(clk="input", rst_n_in="input", rst_n="output"), L, ytype="ot_rst_relay"),
        E.Cell("s.u_core.u_vm", "vm", {}, dict(clk=[1], rst_n=[5], drain_data=[10, 11], stage_data=[12, 13]),
               dict(clk="input", rst_n="input", drain_data="input", stage_data="output"), L, ytype="vm"),
        E.Cell("s.u_core.$procdff$1", "$dff", {}, dict(CLK=[1], D=[3, 4], Q=[14, 15]),
               dict(CLK="input", D="input", Q="output"), G, ytype="$dff", yparams=dict(WIDTH="2", CLK_POLARITY="1")),
        # operand store glue: excluded from ctl (u_core.u_engine.u_memory.*)
        E.Cell("s.u_core.u_engine.u_memory.$procdff$2", "$dff", {}, dict(CLK=[1], D=[12, 13], Q=[10, 11]),
               dict(CLK="input", D="input", Q="output"), G, ytype="$dff", yparams=dict(WIDTH="2", CLK_POLARITY="1")),
        # an already-composed lane leaf that reads ctl outputs and the relayed reset
        E.Cell("s.__cut_lane0", "lane", {}, dict(clk=[1], rst_n=[6], x=[14, 15]),
               dict(clk="input", rst_n="input", x="input"), L, ytype="lane"),
    ]
    return F


def test_sfu_ctl_cut_exact():
    T = load("sfu_ctl_parent_cutmap")
    F = sfu_flat()
    nc, _, top = nets(F)
    core, rep = T.cut_slice(F, "s", {"s.__cut_lane0"}, set(), nc, top)
    assert set(core["members"]) == {"s.u_core.u_rst", "s.u_core.u_vm", "s.u_core.$procdff$1"}
    assert rep["excluded_operand_store"] == 1
    P = core["ports"]
    assert P["rst_n"]["dir"] == "input" and P["rst_n"]["bits"] == [[dict(member="s.u_core.u_rst", port="rst_n_in", bit=0)]]
    assert P["clk"]["dir"] == "input" and len(P["clk"]["bits"][0]) == 3     # every member clock terminal anchored
    assert P["u_core_u_vm__stage_data"]["dir"] == "output"                  # read by the excluded store glue
    assert P["u_core_u_rst__rst_n"]["dir"] == "output" and len(P["u_core_u_rst__rst_n"]["bits"]) == 1
    _, receipt = compose(F, Rules(), dict(allow_glue=True, cores=[core]), E.Cell)
    assert receipt["terminal_equality"] and receipt["cores"][0]["terminal_count"] == 15
    assert "s.__cut_ctl" in {c.path for c in F.cells} and "s.u_core.u_vm" not in {c.path for c in F.cells}


def test_sfu_ctl_refuses_without_relay():
    T = load("sfu_ctl_parent_cutmap")
    F = sfu_flat()
    F.cells = [c for c in F.cells if c.path != "s.u_core.u_rst"]
    nc, _, top = nets(F)
    with pytest.raises(SystemExit, match="reset relay"):
        T.cut_slice(F, "s", set(), set(), nc, top)


def qcen_flat(drop=None):
    """native W128 qcen: 127 fp32 adder leaves + per-node ne = nv && |err glue + one |ne reducer."""
    F = E.Flat()
    nid = [0]

    def new(n=1):
        b = F.new(n)
        return list(range(b, b + n))
    clk, rc, lv = new(), new(), new()
    s_i = new(128 * 32)
    F.top_ports = {"clk": ("input", clk), "s_i": ("input", s_i)}
    F.cells = [E.Cell("h.u_cen.u_rst", "ot_rst_relay", {}, dict(clk=clk, rst_n_in=new(), rst_n=rc),
                      dict(clk="input", rst_n_in="input", rst_n="output"), "leaf", ytype="ot_rst_relay"),
               E.Cell("h.u_cen.$procdff$9", "$dff", {}, dict(CLK=clk, D=new(), Q=lv),
                      dict(CLK="input", D="input", Q="output"), "glue", ytype="$dff",
                      yparams=dict(WIDTH="1", CLK_POLARITY="1"))]
    y, v, ne = {}, {}, []
    for l in range(1, 8):
        for i in range(128 >> l):
            if l == 1:
                a, b, va = s_i[64 * i:64 * i + 32], s_i[64 * i + 32:64 * i + 64], lv
            else:
                a, b, va = y[(l - 1, 2 * i)], y[(l - 1, 2 * i + 1)], v[(l - 1, 2 * i)]
            y[(l, i)], v[(l, i)], e = new(32), new(), new(2)
            F.cells.append(E.Cell(f"h.u_cen.g_lvl[{l}].g_n[{i}].u_a", "ot_hdc_fp32_add_lat", {"LAT": "7"},
                                  dict(clk=clk, rst_n=rc, valid_in=va, a=a, b=b, y=y[(l, i)], err=e, valid_out=v[(l, i)]),
                                  dict(clk="input", rst_n="input", valid_in="input", a="input", b="input",
                                       y="output", err="output", valid_out="output"), "leaf", ytype="ot_hdc_fp32_add_lat"))
            if (l, i) == drop:
                continue
            ro, n1 = new(), new()
            nid[0] += 1
            F.cells.append(E.Cell(f"h.u_cen.$reduce_or$q.sv:157${nid[0]}", "$reduce_or", {}, dict(A=e, Y=ro),
                                  dict(A="input", Y="output"), "glue", ytype="$reduce_or",
                                  yparams=dict(A_SIGNED="0", A_WIDTH="2", Y_WIDTH="1")))
            F.cells.append(E.Cell(f"h.u_cen.$and$q.sv:157${nid[0]}", "$and", {}, dict(A=v[(l, i)], B=ro, Y=n1),
                                  dict(A="input", B="input", Y="output"), "glue", ytype="$and",
                                  yparams=dict(A_SIGNED="0", B_SIGNED="0", A_WIDTH="1", B_WIDTH="1", Y_WIDTH="1")))
            ne += n1
    F.cells.append(E.Cell("h.u_cen.$reduce_or$q.sv:166$999", "$reduce_or", {}, dict(A=ne, Y=new()),
                          dict(A="input", Y="output"), "glue", ytype="$reduce_or",
                          yparams=dict(A_SIGNED="0", A_WIDTH=str(len(ne)), Y_WIDTH="1")))
    F.cells.append(E.Cell("h.u_cen.$procdff$10", "$dff", {}, dict(CLK=clk, D=y[(7, 0)], Q=new(32)),
                          dict(CLK="input", D="input", Q="output"), "glue", ytype="$dff",
                          yparams=dict(WIDTH="32", CLK_POLARITY="1")))
    return F


def test_subtree32_cut_exact_abi_and_one_master():
    T = load("hc_subtree32_parent_cutmap")
    F = qcen_flat()
    byp = {c.path: c for c in F.cells}
    nc, dr, top = nets(F)
    cores = [T.cut(F, byp, dr, nc, top, "h", k)[0] for k in range(4)]
    for k, c in enumerate(cores):
        assert c["inst"] == f"h.u_cen.ot_hbm_hc_subtree32_{k}" and len(c["members"]) == 31 + 62
        assert c["ports"]["data"]["bits"][0] == [dict(member=f"h.u_cen.g_lvl[1].g_n[{16 * k}].u_a", port="a", bit=0)]
        assert c["ports"]["sum"]["bits"][0] == [dict(member=f"h.u_cen.g_lvl[5].g_n[{k}].u_a", port="y", bit=0)]
    sources, receipt = compose(F, Rules(), dict(allow_glue=True, cores=cores), E.Cell)
    assert receipt["terminal_equality"]
    assert len(sources) == 1 and sources[0][0] == "ot_hbm_hc_subtree32_core"   # identical structure, one master
    left = {c.path for c in F.cells}
    assert "h.u_cen.g_lvl[6].g_n[0].u_a" in left and "h.u_cen.$reduce_or$q.sv:166$999" in left


def test_subtree32_refuses_missing_node_fault():
    T = load("hc_subtree32_parent_cutmap")
    F = qcen_flat(drop=(3, 1))
    byp = {c.path: c for c in F.cells}
    nc, dr, top = nets(F)
    with pytest.raises(SystemExit, match="node_fault"):
        T.cut(F, byp, dr, nc, top, "h", 0)
