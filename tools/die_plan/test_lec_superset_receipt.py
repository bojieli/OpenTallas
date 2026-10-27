"""ROOT-MERGE-30 (COORD RULING HBM-CORE-LAT-R4 (3), R5 collar 03:02): OT_LEC_SUPERSET_VEC=1 is accepted only with a
per-run list of the extra kept gate bits shown unobservable (lec.py superset_report -> lec.json superset_vec), and
sign-off checks it, including that the routed LEC passed the same flag explicitly (signoff.lec_superset_problems)."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
import signoff  # noqa: E402
from test_lec import _sim_prove  # noqa: E402


def vec_design(bits, rec1_from_rec0=False):
    """flops u_dut.rec[b] (next state = input d); optionally rec[1]' = d & rec[0] (the extra bit observable)."""
    m = lec.Aig()
    d0 = m.add_input('d')
    q = [m.add_input(str(i)) for i in range(len(bits))]
    nxt = [d0] * len(bits)
    if rec1_from_rec0:
        nxt[bits.index(1)] = m.AND(d0, q[bits.index(0)])
    d = dict(I=1, L=len(bits), O=0, A=len(m.ands) // 2, latches=nxt, outputs=[], ands=m.ands)
    mp = {'input': {0: [('d', 0)]}, 'output': {},
          'latch': {i: [(f'u_dut.rec[{b}]$_DFF_P_.lecq', 0)] for i, b in enumerate(bits)}}
    return d, mp


def run(monkeypatch, observable):
    monkeypatch.setenv('OT_LEC_SUPERSET_VEC', '1')
    g, gm = vec_design([1, 2])
    t, tm = vec_design([0, 1, 2], rec1_from_rec0=observable)
    L = lec.Lec(g, gm, t, tm)
    m, kind = L.build(with_compare=True, with_hyp=True)
    st = _sim_prove(m)
    verdict = "EQUIVALENT" if set(st.values()) == {"proved"} else "NOT EQUIVALENT"
    return L, verdict, lec.superset_report(L, m, kind, verdict)


def test_dead_extra_bit_listed_and_shown(monkeypatch):
    L, verdict, r = run(monkeypatch, observable=False)
    assert verdict == "EQUIVALENT"
    assert r["enabled"] and r["n_extra"] == 1 and r["all_shown"]
    (e,) = r["extra_bits"]
    assert e["bit"] == "ff:u_dut.rec[0]" and e["key"] == "ff:u_dut.rec#t[0]"
    assert e["binding"] == "free" and e["observers"] == 0 and e["shown"]


def test_observable_extra_bit_not_shown(monkeypatch):
    L, verdict, r = run(monkeypatch, observable=True)
    assert verdict == "NOT EQUIVALENT"                 # the extra bit reaches matched rec[1]'s next state
    (e,) = r["extra_bits"]
    assert e["binding"] == "free" and e["observers"] >= 1 and not e["shown"] and not r["all_shown"]


def test_default_off_records_nothing(monkeypatch):
    monkeypatch.delenv('OT_LEC_SUPERSET_VEC', raising=False)
    g, gm = vec_design([1, 2])
    t, tm = vec_design([0, 1, 2])
    assert lec.Lec(g, gm, t, tm).superset_extra == []


def receipt(netlist, verdict="EQUIVALENT", superset=True, shown=True, legacy=False):
    r = dict(verdict=verdict, netlist=netlist)
    if superset:
        bits = ["ff:u.rec[0]"] if legacy else [dict(bit="ff:u.rec[0]", key="ff:u.rec#t[0]", binding="free",
                                                     observers=0, shown=shown)]
        r["superset_vec"] = dict(enabled=True, n_extra=1, extra_bits=bits, all_shown=shown)
    return r


def test_signoff_obligation():
    syn, rt = "/work/run/results/asap7/x/base/1_2_yosys.v", "/work/run/results/asap7/x/base/6_final.v"
    P = signoff.lec_superset_problems
    assert P([("lec", receipt(syn, superset=False))]) is None                     # no flag: no obligation
    assert P([("lec", receipt(syn)), ("lec_routed", receipt(rt))]) == []
    assert any("no routed" in x for x in P([("lec", receipt(syn))]))
    assert any("explicitly" in x for x in P([("lec", receipt(syn)), ("lec_routed", receipt(rt, superset=False))]))
    assert any("not shown" in x for x in P([("lec", receipt(syn, shown=False)), ("lec_routed", receipt(rt))]))
    assert any("per-bit" in x for x in P([("lec", receipt(syn, legacy=True)), ("lec_routed", receipt(rt))]))
    assert any("verdict UNPROVEN" in x for x in P([("lec", receipt(syn)), ("r", receipt(rt, verdict="UNPROVEN"))]))


def test_signoff_evaluate_blocks_only_flagged_kits(tmp_path):
    kit = tmp_path / "kit"
    (kit / "lec").mkdir(parents=True)
    (kit / "lec" / "lec.json").write_text(json.dumps(dict(verdict="EQUIVALENT", netlist="1_2_yosys.v")))
    rec = signoff.evaluate(dict(corners={}, inputs=dict(kit=str(kit))))
    assert "lec_superset" not in rec["checks"]                                     # default unchanged
    (kit / "lec" / "lec.json").write_text(json.dumps(receipt("1_2_yosys.v")))
    rec = signoff.evaluate(dict(corners={}, inputs=dict(kit=str(kit))))
    assert rec["checks"]["lec_superset"]["verdict"] == "FAIL"
    assert any(r.startswith("lec_superset: FAIL") for r in rec["reasons"])
    (kit / "lec_routed").mkdir()
    (kit / "lec_routed" / "lec.json").write_text(json.dumps(receipt("6_final.v")))
    rec = signoff.evaluate(dict(corners={}, inputs=dict(kit=str(kit))))
    assert rec["checks"]["lec_superset"]["verdict"] == "PASS"
    assert signoff.main(["lec-check", str(kit)]) == 0
