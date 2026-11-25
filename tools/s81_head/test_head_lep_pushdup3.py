"""LEP-PUSHDUP-3 generator knob (HEAD-ALLFIX 11-25, COORD H9): regen with the knob == the W8 RTL, without == the W8 base.

W8 = event head_rp21z20NF15f_r18w8b, private tree epyc12 head-allfix/trees/s81_head_w8b; hand patch pushdup3/pd3.py with
orig/ (patch base) and new/ (W8 RTL).  The W8 tree's generator inputs are main's at W8_SRC_PIN (its portfix178
ot_s81sl_slice_lep.sv is blob 81d2ae13e716, main at f72013a6506, the parent of 30205bf4fe3 (S81 lep CRP); the other three sources are unchanged since).
The split form ot_s81hd_lep0N_split_tx_io_stages.sv is tree-only, so its W8 base is a checked-in fixture.
"""
import hashlib
import importlib.util
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = HERE / "testdata" / "pushdup3"
W8_SRC_PIN = "f72013a6506"
SHA = {  # sha256 of the W8 files (epyc12 head-allfix/pushdup3/{orig,new}; new == trees/s81_head_w8b)
    "gen_orig": "cda6cc3238131b88e0617db5707a4f63625150e85240e0dfa71876a97e3ae68a",
    "gen_new": "80c2ed52821d2f4122f6ee53e4bbcb610db6327a625e70a5ac1afd67d18e734b",
    "split_orig": "0844883f78d0b09b57887dd028a23525075df133268e5dfad6598f135c718e6b",
    "split_new": "5faf31874f1814b4a507fd10b286d1a87054a60bed44024a8747e4886002923b",
}


def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


GEN = _load("head_lep_nr_sources", HERE / "head_lep_nr_sources.py")
PD3 = _load("head_lep_pushdup3", HERE / "head_lep_pushdup3.py")


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


@pytest.fixture(scope="module")
def w8_root(tmp_path_factory):
    """the four generator sources as the W8 tree had them (main at W8_SRC_PIN)"""
    root = tmp_path_factory.mktemp("w8src")
    for p in GEN.SOURCES:
        r = subprocess.run(["git", "-C", str(ROOT), "show", f"{W8_SRC_PIN}:{p}"], capture_output=True)
        if r.returncode != 0:
            pytest.skip(f"git object {W8_SRC_PIN}:{p} not available (shallow clone)")
        (root / p).parent.mkdir(parents=True, exist_ok=True)
        (root / p).write_bytes(r.stdout)
    return root


def test_regen_with_knob_is_w8_rtl(w8_root):
    text, record = GEN.derive(w8_root, txp="4'b1000")
    assert sha(text) == SHA["gen_new"]
    assert record["txp"] == "4'b1000"


def test_regen_without_knob_is_w8_base(w8_root):
    text, record = GEN.derive(w8_root)
    assert sha(text) == SHA["gen_orig"]
    assert "txp" not in record and "LEP-PUSHDUP-3" not in text and "RST-FAN-1" in text


def test_knob_delta_on_current_main_is_the_w8_delta(w8_root):
    """the knob adds the same lines on current main's sources as on the W8 sources (nothing else moves)"""
    import difflib

    def delta(a, b):
        return [l for l in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
                if l[:1] in "+-" and l[:3] not in ("+++", "---")]
    w_off, _ = GEN.derive(w8_root)
    w_on, _ = GEN.derive(w8_root, txp="4'b1000")
    m_off, _ = GEN.derive(ROOT)
    m_on, _ = GEN.derive(ROOT, txp="4'b1000")
    assert delta(m_off, m_on) == delta(w_off, w_on) and len(delta(w_off, w_on)) == 22


def _split_orig():
    return (DATA / "ot_s81hd_lep0N_split_tx_io_stages.w8base.sv").read_text()


def test_split_with_knob_is_w8_rtl():
    src = _split_orig()
    assert sha(src) == SHA["split_orig"]
    assert sha(PD3.apply(src, "split", "4'b1000")) == SHA["split_new"]


def test_split_without_knob_is_w8_base():
    src = _split_orig()
    for off in (None, "off", "0000"):
        assert PD3.apply(src, "split", off) == src


def test_split_sources_entry_point(tmp_path):
    src = tmp_path / "in.sv"
    src.write_text(_split_orig())
    out = tmp_path / "out.sv"
    subprocess.run(["python3", "-I", str(HERE / "head_lep_split_sources.py"), "--io-stages", str(src), "--io-out", str(out),
                    "--txp", "4'b1000"], check=True, capture_output=True)
    assert sha(out.read_text()) == SHA["split_new"]


def test_fails_closed():
    src = _split_orig()
    with pytest.raises(SystemExit):
        PD3.apply(PD3.apply(src, "split", "4'b1000"), "split", "4'b1000")   # not re-applicable
    with pytest.raises(SystemExit):
        PD3.apply(src.replace("assign tx_wd[t*(H+1)+:H+1] = {sq[t/2],(t%2==0)?hf0:hf1};\n", ""), "split", "4'b1000")
    with pytest.raises(SystemExit):
        PD3.txp_value("4'b10")
