"""NOMCAP-1118 r708: die_sta_related register characterisation reads the nominal clock-pin-cap SEQ copy (stock with OT_NOMCAP=0)."""
import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_sta_related as D


def test_nomcap_seq_staged(monkeypatch):
    monkeypatch.delenv("OT_NOMCAP", raising=False)
    d = tempfile.mkdtemp()
    p, nom = D.reg_seq_lib("TT", d)
    assert nom and p == "/w/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib.gz" and (Path(d) / Path(p).name).is_file()
    assert "read_liberty $::env(SEQLIB)" in D.REG_TCL


def test_stock_when_off(monkeypatch):
    monkeypatch.setenv("OT_NOMCAP", "0")
    p, nom = D.reg_seq_lib("FF", tempfile.mkdtemp())
    assert not nom and p.startswith("/OpenROAD-flow-scripts/") and p.endswith("SEQ_RVT_FF_nldm_220123.lib")
