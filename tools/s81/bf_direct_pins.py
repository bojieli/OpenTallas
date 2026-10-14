"""Exact compact199 BF pin geometry for the direct die assembly.

These rectangles describe closed views. They do not qualify or bind those views;
native BF16 transport and the child access gates remain separate requirements.
"""
VIEW = "physical/s81_die_views/bf_compact199"
SEAM_UM = 1.188


def groups(column=False):
    def bus(n, w):
        return [f"{n}[{i}]" for i in range(w)] if w > 1 else [n]
    seam = [("issue", 1), ("a_ctr", 14), ("i1_v", 1), ("i1_bk", 1), ("i1_bf", 1), ("i1_t", 17),
            ("i2x_q0", 256), ("i2x_e0", 10), ("i2x_q1", 256), ("i2x_e1", 10), ("ze_d", 1),
            ("so_row", 128), ("so_idx", 40), ("so_n", 40)]
    names = [p for n, w in seam for p in bus(n, w)]
    if column:
        return dict(ci=names, qy=["qy_bkf"], ck=["clk"], rs=["rst_n_pin"],
                    r=[p for n, w in [("pv", 1), ("pval", 32), ("prow", 16), ("pseg", 5),
                                      ("pnseg", 5), ("perr", 1), ("ppos", 3)] for p in bus(n, w)])
    return dict(c0=["c0_" + n for n in names], c1=["c1_" + n for n in names],
                qy0=["c_qy_bkf_in[0]"], qy1=["c_qy_bkf_in[1]"],
                x0=[p for n, w in [("xs_q0", 256), ("xs_e0", 10), ("xs_b", 3), ("xs_p", 8),
                                   ("xs_pos", 3), ("xs_sv", 2), ("xs_v", 1)] for p in bus(n, w)],
                x1=bus("xs_q1", 256) + bus("xs_e1", 10), go=["go"],
                cfg=bus("cfg_a", 5) + bus("cfg_d", 48) + ["cfg_v"],
                st=["busy", "fault"], ck=["clk"], rs=["rst_n"])


def populate(generator, master, column, ports):
    native = "ot_v41_bf_col" if column else "ot_s81_bf_front"
    view = generator.real_lef(f"{VIEW}/{native}/{native}.lef")
    assert abs(master.w - view["w"]) < 1e-6 and abs(master.h - view["h"]) < 1e-6, (
        master.name, (master.w, master.h), (view["w"], view["h"]))
    mapping = groups(column)
    for port, (_, width) in ports.items():
        names = mapping[port]
        assert len(names) == width, (master.name, port, len(names), width)
        master.ports[port] = ("rects", [(f"{port}[{i}]", *view["pins"][name]) for i, name in enumerate(names)])
        master.order.append(port)


def coverage(generator):
    """Explicit uncovered pins prevent a geometry screen being mistaken for native closure."""
    out = {}
    for column in (False, True):
        native = "ot_v41_bf_col" if column else "ot_s81_bf_front"
        view = generator.real_lef(f"{VIEW}/{native}/{native}.lef")
        covered = {n for ns in groups(column).values() for n in ns}
        out[native] = dict(covered=len(covered), uncovered=sorted(set(view["pins"]) - covered),
                           view=f"{VIEW}/{native}/{native}.lef")
    return out
