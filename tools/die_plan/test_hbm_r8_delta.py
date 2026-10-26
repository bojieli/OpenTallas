"""PATH-HBM-R8 delta: bank k-cycle exchange + hub distribution on small synthetic types."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_r8_delta as D  # noqa: E402


def _bank():
    cores = [dict(inst=f"u_c{i}", module=f"m{i}", origin_um=[17.28, 17.28 + 200 * i], outline_um=[200.0, 150.0])
             for i in range(4)]
    st = []
    for i in range(4):
        for j in range(4):
            if i != j:
                a = [117.28, 167.28 + 200 * i]
                b = [117.28, 17.28 + 200 * j]
                st.append(dict(conn=f"q{i}{j}", launch=f"u_c{i}.q_b", capture=f"u_c{j}", from_um=a, to_um=b,
                               bits=568, regs_um=[]))
                st.append(dict(conn=f"k{i}{j}", launch=f"u_c{i}.key", capture=f"u_c{j}", from_um=a, to_um=b,
                               bits=544, regs_um=[]))
                st.append(dict(conn=f"v{i}{j}", launch=f"u_c{i}.qv_b", capture=f"u_c{j}", from_um=a, to_um=b,
                               bits=1, regs_um=[]))
    return dict(outline_um=[240.0, 840.0], hard_cores=cores, internal_stations=st)


def test_serialise_classes():
    t = _bank()
    n = D.serialise_bank(t, 4, 2)
    assert n == {"q": 12, "key": 12}
    b = {s["conn"][0]: s["bits"] for s in t["internal_stations"]}
    assert b == {"q": 142, "k": 272, "v": 1}           # control/valid keeps its width


def test_choose_k_reaches_limit():
    t = _bank()
    u0, _ = D.bank_cut(t)
    best, eq, rows = D.choose_k(t)
    assert u0 > 0.6 and best["ok"] and eq["ok"] and eq["kq"] == eq["kk"]
    tt = copy.deepcopy(t)
    D.serialise_bank(tt, eq["kq"], eq["kk"])
    assert D.bank_cut(tt)[0] <= 0.6 + 1e-9
    if eq["kq"] > 1:
        t2 = copy.deepcopy(t)
        D.serialise_bank(t2, eq["kq"] - 1, eq["kk"] - 1)
        assert D.bank_cut(t2)[0] > 0.6                 # smallest equal k


def test_distribute_hub_lands_lanes_locally(tmp_path):
    W, H = 1728.0, 864.0
    star = dict(inst="u_s", module="star_core", origin_um=[786.24, 345.6], outline_um=[155.52, 172.8])
    loc = dict(inst="u_l", module="loc_core", origin_um=[86.4, 86.4], outline_um=[103.68, 103.68])
    st = []
    for x in (172.8, 518.4, 1209.6, 1555.2):
        st.append(dict(conn="bus:L", launch="face bus L%d" % int(x), capture="u_s.p", from_um=[x, H],
                       to_um=[786.24, 432.0], bits=1200, regs_um=[]))
    st.append(dict(conn="c", launch="u_s.o", capture="u_l.i", from_um=[941.76, 432.0], to_um=[190.08, 138.24],
                   bits=100, regs_um=[[500.0, 138.24]]))
    t = dict(outline_um=[W, H], hard_cores=[star, loc], internal_stations=st, contents=[], clock=dict(taps=[]))
    rep, pins = D.distribute_hub("q_hub_t", t, 2, tmp_path, {}, star_min_bits=1000, log=lambda *a: None)
    assert list(rep["star_cores"]) == ["u_s"]
    names = sorted(h["inst"] for h in t["hard_cores"])
    assert names == ["u_l", "u_s__s0", "u_s__s1"]
    hc = {h["inst"]: h for h in t["hard_cores"]}
    for s in t["internal_stations"]:
        if s["launch"].startswith("face"):
            k = 0 if s["from_um"][0] < W / 2 else 1
            c = hc[f"u_s__s{k}"]
            assert c["origin_um"][0] <= s["to_um"][0] <= c["origin_um"][0] + c["outline_um"][0]
            assert (k == 0) == (s["to_um"][0] < W / 2)          # lands in its own segment
    gather = [s for s in t["internal_stations"] if s["capture"] == "u_l.i"]
    assert len(gather) == 2 and all(s["bits"] == 50 for s in gather)
    json.dumps(rep)
