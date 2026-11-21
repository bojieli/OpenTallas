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

def _rck4_capsule(directory):
    root = Path(__file__).resolve().parents[2] / "rtl/dsrom_sys/s81_link"
    rtl = Path(directory) / "rtl"
    rtl.mkdir()
    sources = ["lp/ot_s81_kp4_dec_native_flat_lp.sv", "ot_s81_kp4_dsyn.sv",
               "col/ot_pdie_serdes_col.sv", "ot_pdie_serdes_locksafe.sv"]
    for rel in sources:
        (rtl / Path(rel).name).write_bytes((root / rel).read_bytes())
    cfg = ["export VERILOG_FILES = " + " ".join("/work/rtl/" + Path(rel).name for rel in sources)]
    defines = ["-DOT_S81_RCK_RELAY4", "-DOT_S81_KP4_AM_FACE3", "-DOT_S81_SERDES_RXNEG",
               "-DOT_S81_SERDES_TXPIPE", "-DOT_S81_SERDES_RXPIPE",
               "-DOT_S81_SERDES_RM_RPC8", "-DOT_S81_SERDES_RST_TREE"]
    return cfg, defines


def test_rck4_actual_source_emits_portable_joint_hook():
    import json
    with tempfile.TemporaryDirectory() as d:
        cfg, defines = _rck4_capsule(d)
        out = G.txl_mid_exports(cfg, d, env={}, defines=[flag + "=1" for flag in defines])
        assert out[-1] == "export POST_GLOBAL_PLACE_TCL = /work/rck_transport_mid.tcl"
        assert "export OT_TXL_MID_RXNEG_PAIR = 1" in out
        assert "export OT_S81_RCK4_FACE = 1" in out
        assert "export OT_LEAF_AFF_DEPTH = 12" in out
        assert (Path(d) / "rck_transport_mid.tcl").read_bytes() == Path(G.__file__).with_name("rck_transport_mid.tcl").read_bytes()
        contract = json.loads((Path(d) / "rck4_source_contract.json").read_text())
        assert contract["expected_actual_synth_ff"] == {"transport": 2216, "reset": 4, "AM": 9, "RPC": 24, "LOCAL_EMPTY": 0}
        assert len(contract["source_sha256"]) == 4


def test_rck4_missing_companion_flags_is_explicit():
    for missing in ("OT_S81_KP4_AM_FACE3", "OT_S81_SERDES_RXNEG"):
        with tempfile.TemporaryDirectory() as d:
            defines = ["OT_S81_RCK_RELAY4", "OT_S81_KP4_AM_FACE3", "OT_S81_SERDES_RXNEG"]
            defines.remove(missing)
            try:
                G.txl_mid_exports([], d, env={}, defines=defines)
            except AssertionError as error:
                assert missing in str(error)
            else:
                raise AssertionError("missing source companion accepted")
            assert not (Path(d) / "rck_transport_mid.tcl").exists()


def test_rck4_rejects_actual_frozen_or_wrong_shape_native_body():
    with tempfile.TemporaryDirectory() as d:
        cfg, defines = _rck4_capsule(d)
        lp = Path(d) / "rtl/ot_s81_kp4_dec_native_flat_lp.sv"
        lp.write_text(lp.read_text().replace(".W(554), .N(4)", ".W(553), .N(4)"))
        try:
            G.txl_mid_exports(cfg, d, env={}, defines=defines)
        except AssertionError as error:
            assert "u_rck_transport4 W=554 N=4 absent" in str(error)
        else:
            raise AssertionError("old or malformed source accepted")
        assert not (Path(d) / "rck_transport_mid.tcl").exists()


def test_rck4_rejects_rpc_native_caller_bypass():
    with tempfile.TemporaryDirectory() as d:
        cfg, defines = _rck4_capsule(d)
        try:
            G.txl_mid_exports(cfg, d, env={}, defines=defines + ["-DOT_S81_RM_STAGED"])
        except AssertionError as error:
            assert "native _rt caller" in str(error)
        else:
            raise AssertionError("RM_STAGED silently bypassed RPC8")


def test_rck4_am_clock_cohort_is_explicit_optin():
    with tempfile.TemporaryDirectory() as d:
        cfg, defines = _rck4_capsule(d)
        base = G.txl_mid_exports(cfg, d, env={}, defines=defines)
        assert "export OT_S81_RCK_AM_COHORT = 1" not in base
        assert not (Path(d) / "rck_am_cohort.tcl").exists()
        selected = G.txl_mid_exports(cfg, d, env={"OT_S81_RCK_AM_COHORT": "1"}, defines=defines)
        assert "export OT_S81_RCK_AM_COHORT = 1" in selected
        assert (Path(d) / "rck_am_cohort.tcl").read_bytes() == Path(G.__file__).with_name("rck_am_cohort.tcl").read_bytes()


def test_rck4_local_empty_source_and_default_boot_dependency():
    import json
    with tempfile.TemporaryDirectory() as d:
        cfg, defines = _rck4_capsule(d)
        G.txl_mid_exports(cfg, d, env={}, defines=defines + ["-DOT_S81_SERDES_RM_LOCAL_EMPTY8"])
        record = json.loads((Path(d) / "rck4_source_contract.json").read_text())
        assert record["expected_actual_synth_ff"]["LOCAL_EMPTY"] == 8
        dep = Path(d) / "rtl/ot_pdie_serdes_locksafe.sv"
        dep.write_text(dep.read_text().replace("module ot_pdie_pma_release_chain", "module wrong_release_name"))
        try:
            G.txl_mid_exports(cfg, d, env={}, defines=defines)
        except AssertionError as error:
            assert "default0 boot release module absent" in str(error)
        else:
            raise AssertionError("default0 unconditional module dependency silently missing")


def test_rck4_rm_locality_composes_current_mechanisms():
    with tempfile.TemporaryDirectory() as d:
        cfg, defines = _rck4_capsule(d)
        out = G.txl_mid_exports(cfg, d, env={"OT_SERDES_RM_LOCAL": "1"},
                                defines=defines + ["-DOT_S81_SERDES_RM_LOCAL_EMPTY8"])
        assert out[-1] == "export POST_GLOBAL_PLACE_TCL = /work/serdes_post_gpl.tcl"
        assert "export OT_SERDES_RM_LOCAL_EMPTY8 = 1" in out
        assert (Path(d) / "serdes_post_gpl.tcl").read_text().splitlines() == [
            "source /work/rck_transport_mid.tcl", "source /work/serdes_rm_local.tcl"]
        assert (Path(d) / "serdes_rm_local.tcl").read_bytes() == Path(G.__file__).with_name("serdes_rm_local.tcl").read_bytes()


def test_rck4_lpl_actual_source_and_frozen_reader_refusal():
    import subprocess
    import json
    with tempfile.TemporaryDirectory() as d:
        cfg, defines = _rck4_capsule(d)
        root = Path(__file__).resolve().parents[2]
        source = root / "rtl/common/landed_parent/ot_pl_land.sv"
        text = source.read_text() if source.exists() else subprocess.check_output(
            ["git", "-C", str(root), "show", "HEAD:rtl/common/landed_parent/ot_pl_land.sv"], text=True)
        local = Path(d) / "rtl/ot_pl_land.sv"
        local.write_text(text)
        cfg[0] += " /work/rtl/ot_pl_land.sv"
        G.txl_mid_exports(cfg, d, env={}, defines=defines + ["-DOT_S81_LPL_CHUNK"])
        record = json.loads((Path(d) / "rck4_source_contract.json").read_text())
        assert record["expected_local_ring_instances"] == {"read": 89, "write": 89}
        assert record["expected_actual_synth_ff"]["LPL_read_onehot"] == 356
        local.write_text(text.replace("module ot_pl_land_local_r", "module wrong_local_reader"))
        try:
            G.txl_mid_exports(cfg, d, env={}, defines=defines + ["-DOT_S81_LPL_CHUNK"])
        except AssertionError as error:
            assert "actual local writer/reader modules absent" in str(error)
        else:
            raise AssertionError("frozen landing source silently accepted")


def test_rck4_rm_wpl8_requires_local_empty_and_actual_source():
    import json
    with tempfile.TemporaryDirectory() as d:
        cfg, defines = _rck4_capsule(d)
        try:
            G.txl_mid_exports(cfg, d, env={}, defines=defines + ["-DOT_S81_SERDES_RM_WPL8"])
        except AssertionError as error:
            assert "RM_WPL8 requires LOCAL_EMPTY8" in str(error)
        else:
            raise AssertionError("RM_WPL8 without LOCAL_EMPTY8 accepted")
        both = defines + ["-DOT_S81_SERDES_RM_LOCAL_EMPTY8", "-DOT_S81_SERDES_RM_WPL8"]
        G.txl_mid_exports(cfg, d, env={}, defines=both)
        record = json.loads((Path(d) / "rck4_source_contract.json").read_text())
        assert record["expected_actual_synth_ff"]["LOCAL_WP"] == 36 and record["RM_read_added_edges"] == 1
        try:
            G.txl_mid_exports(cfg, d, env={"OT_SERDES_RM_LOCAL": "1"}, defines=both)
        except AssertionError as error:
            assert "no RM_WPL8 scope" in str(error)
        else:
            raise AssertionError("RM locality helper accepted the RM_WPL8 profile")


# FAM-S81-SERDES-R4 11-21: OT_S81_SERDES_DEC_CORE shell (u_dec = hard core): no hook names a cell inside the decoder core.
T4_DEFINES = ["-DOT_KP4_DEC_HARD", "-DOT_S81_SERDES_TXPIPE", "-DOT_S81_SERDES_RXPIPE", "-DOT_S81_SERDES_RXNEG",
              "-DOT_S81_KP4_AM_FACE3", "-DOT_S81_RCK_RELAY4", "-DOT_S81_SERDES_RM_RPC8", "-DOT_S81_SERDES_BOOT_RELEASE3",
              "-DOT_S81_LPL_CHUNK", "-DOT_S81_SERDES_RM_LOCAL_EMPTY8", "-DOT_S81_SERDES_RM_WPL8", "-DOT_S81_KP4_AMOK_PIPE",
              "-DOT_S81_SERDES_TXL4"]


def test_dec_core_shell_drops_decoder_internal_hooks():
    with tempfile.TemporaryDirectory() as d:
        # no VERILOG_FILES: the RCK4 native-source contract belongs to the core kit, not the shell
        out = G.txl_mid_exports([], d, env={"OT_TXL_MID": "1", "OT_TXL_MID_CHAINS": "u_txl,u_dec.u_rck_transport4"},
                                defines=T4_DEFINES + ["-DOT_S81_SERDES_DEC_CORE"])
        assert "export OT_TXL_MID_CHAINS = u_txl u_rxf" in out
        assert not any("u_dec." in c for c in out)
        assert out[-1] == "export POST_GLOBAL_PLACE_TCL = /work/txl_mid.tcl"
        assert "export OT_S81_RCK4_FACE = 1" not in out and "export OT_TXL_MID_RXNEG_PAIR = 1" not in out
        assert "export OT_LEAF_AFF_DEPTH = 12" in out
        assert not (Path(d) / "rck_transport_mid.tcl").exists()


def test_dec_core_shell_refuses_am_cohort():
    with tempfile.TemporaryDirectory() as d:
        try:
            G.txl_mid_exports([], d, env={"OT_S81_RCK_AM_COHORT": "1"}, defines=T4_DEFINES + ["-DOT_S81_SERDES_DEC_CORE"])
        except AssertionError:
            return
        raise AssertionError("expected refusal")


def test_dec_core_shell_has_no_h4_meta_reflow():
    with tempfile.TemporaryDirectory() as d:
        names = {x[2:] for x in T4_DEFINES} | {"OT_S81_SERDES_DEC_CORE"}
        out = G.serdes_h_lines([], d, names, {"OT_SERDES_COHORTS": "0"}, "txl_mid.tcl")
        assert not any("h4_meta_reflow" in c for c in out)
        out = G.serdes_h_lines([], d, names - {"OT_S81_SERDES_DEC_CORE"}, {"OT_SERDES_COHORTS": "0"}, "txl_mid.tcl")
        assert "export PRE_RESIZE_TCL = /work/h4_meta_reflow.tcl" in out
