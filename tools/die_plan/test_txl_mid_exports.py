"""KW-FIX-43: gen_phys.txl_mid_exports, the opt-in OT_TXL_MID generator hook (unset = no config lines)."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G  # noqa: E402


def test_unset_is_byte_identical():
    with tempfile.TemporaryDirectory() as d:
        assert G.txl_mid_exports([], d, env={}) == []
        assert G.txl_mid_exports([], d, env={"OT_TXL_MID": "0"}) == []
        assert not (Path(d) / "txl_mid.tcl").exists()


def test_set_copies_hook_and_writes_chains():
    with tempfile.TemporaryDirectory() as d:
        out = G.txl_mid_exports(["export X = 1"], d, env={"OT_TXL_MID": "1", "OT_TXL_MID_CHAINS": "u_txl,u_dec.u_rck_transport4"})
        assert "export OT_TXL_MID = 1" in out
        assert "export OT_TXL_MID_CHAINS = u_txl u_dec.u_rck_transport4" in out
        assert out[-1] == "export POST_GLOBAL_PLACE_TCL = /work/txl_mid.tcl"
        assert (Path(d) / "txl_mid.tcl").read_bytes() == Path(G.__file__).with_name("txl_mid.tcl").read_bytes()
        assert not any(c.startswith("export OT_TXL_MID_CHAINS") for c in G.txl_mid_exports([], d, env={"OT_TXL_MID": "1"}))


def test_refuses_second_post_global_place_hook():
    with tempfile.TemporaryDirectory() as d:
        try:
            G.txl_mid_exports(["export POST_GLOBAL_PLACE_TCL = /work/cons_midflop.tcl"], d, env={"OT_TXL_MID": "1"})
        except AssertionError:
            return
        raise AssertionError("expected refusal")


def test_serdes_pipe_defines_turn_hook_on_with_face():
    with tempfile.TemporaryDirectory() as d:
        assert G.txl_mid_exports([], d, env={}, defines=["-DSYNTHESIS", "-DOT_KP4_DEC_HARD"]) == []
        out = G.txl_mid_exports([], d, env={}, defines=["-DSYNTHESIS", "-DOT_S81_SERDES_TXPIPE", "-DOT_S81_SERDES_RXPIPE"])
        assert "export OT_TXL_MID = 1" in out and "export OT_TXL_MID_FACE = 1" in out
        assert "export OT_TXL_MID_CHAINS = u_txl u_rxf u_dec.u_face_p_d" in out
        assert out[-1] == "export POST_GLOBAL_PLACE_TCL = /work/txl_mid.tcl"
        assert (Path(d) / "txl_mid.tcl").exists()
        tx = G.txl_mid_exports([], d, env={}, defines=["OT_S81_SERDES_TXPIPE"])
        assert "export OT_TXL_MID_CHAINS = u_txl" in tx
        both = G.txl_mid_exports([], d, env={"OT_TXL_MID": "1", "OT_TXL_MID_CHAINS": "u_dec.u_rck_transport4"},
                                 defines=["-DOT_S81_SERDES_TXPIPE"])
        assert "export OT_TXL_MID_CHAINS = u_dec.u_rck_transport4 u_txl" in both


def test_env_only_has_no_face_line():
    with tempfile.TemporaryDirectory() as d:
        assert not any("OT_TXL_MID_FACE" in c for c in G.txl_mid_exports([], d, env={"OT_TXL_MID": "1"}))
