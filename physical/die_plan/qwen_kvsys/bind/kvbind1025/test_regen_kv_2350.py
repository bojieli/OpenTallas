"""TOK-KV-4 10-29 (KV-024 + HOST record abort): regen_kv_2350.txdp applies the committed pair image record only when it is
the image of THIS bind: K, XDIE_SEAM_K and HOST_REC_RT re-derived from the landed legs (regen_constants laws)."""
import importlib.util
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

HERE = Path(__file__).resolve().parent


def _hook():
    s = importlib.util.spec_from_file_location("regen_kv_2350_t", HERE / "regen_kv_2350.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


H = _hook()
RC = H._load("rc_t", HERE.parents[4] / "tools" / "die_plan" / "regen_constants.py")


def _ctx(seam=(90, 90, 88, 88, 88, 77, 77), out=86, back=67):
    cells = [NS(path="top.sys_c.d2d_kv", module="qkd_d2d_static_sfm", params={}),
             NS(path="top.sys_c.kvs_attn", module="qkd_kvs_attn", params={}),
             NS(path="top.hub_Wi.host", module="qkd_host_root", params={})]
    ix = {"d2d_kv": 0, "kvs_attn": 1}
    sinks, bitcyc = {}, {}

    def x(dst, dpn, src, spn, asb, landed):
        b = len(sinks)
        sinks[(dst, dpn, b)] = ("x", "p_src", src, spn, b, asb, "p_dst")
        bitcyc[("p_src", "p_dst", src, spn, b)] = landed
    for (s, (sl, sp, dl, dp)), v in zip(RC.KV_SEAM.items(), seam):
        for _ in range(2):
            x(ix[dl], dp, ix[sl], sp, 5, 5 + v - RC.KV_ANCHOR["seam"][s])
    for spn in ("record_send_kind", "record_witness_slot"):
        x(2, spn, 0, spn, 1, out)
    for pn in ("record_tx", "record_tx_observed_v"):
        x(0, pn, 2, pn, 0, back)
    return NS(F=NS(cells=cells), sinks=sinks, bitcyc=bitcyc)


def _with_record(monkeypatch, **kw):
    r = json.loads(H.PAIR.read_text())
    r.update(kw)
    if "D2D_TXDP_K" in kw:
        k = kw["D2D_TXDP_K"]
        r["sv_literal"] = f"32'h{k[0] | k[1] << 8 | k[2] << 16 | k[3] << 24:08x}"
    p = Path(tempfile.mkdtemp(), "pair_image_txdp.json")
    p.write_text(json.dumps(r))
    monkeypatch.setattr(H, "PAIR", p)


def test_bind_law_matches_regen_constants():
    assert H.bind_txdp(_ctx()) == ([169, 157, 3, 3], "90,90,88,88,88,77,77", 153)
    assert H.bind_txdp(_ctx(seam=(90, 90, 88, 88, 88, 78, 78)))[0] == [170, 157, 3, 3]
    assert H.SEAM_NAMES == tuple(RC.KV_SEAM)


def test_committed_record_is_the_bind_of_record_image():
    params, rec = H.txdp(_ctx())
    assert params == {"top.sys_c.d2d_kv": {"TXDP": "32'h03039da9"}}


def test_stale_k0_record_fails_closed(monkeypatch):     # KV-024 mutant: bind5 record (SK_TXP 78) on the SK_TXP 77 bind
    _with_record(monkeypatch, D2D_TXDP_K=[170, 157, 3, 3], XDIE_SEAM_K="90,90,88,88,88,78,78")
    with pytest.raises(ValueError, match="stale for this bind"):
        H.txdp(_ctx())


def test_old_k1_record_fails_closed(monkeypatch):       # the 38406 abort mutant: HOST next to the end (K1 = 4)
    _with_record(monkeypatch, D2D_TXDP_K=[169, 4, 3, 3], HOST_REC_RT=0)
    with pytest.raises(ValueError, match="stale for this bind"):
        H.txdp(_ctx())


def test_unequal_host_bundle_errors():
    c = _ctx()
    k = next(k for k, d in c.sinks.items() if d[3] == "record_witness_slot")
    d = c.sinks[k]
    c.bitcyc[(d[1], d[6], d[2], d[3], d[4])] = 85
    with pytest.raises(ValueError, match="lands unequal"):
        H.bind_txdp(c)
