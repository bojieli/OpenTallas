from pathlib import Path

SRC = (Path(__file__).resolve().parent / "gen_phys.py").read_text()


def test_nonport_hold_is_default_on_and_port_inclusion_needs_the_explicit_opt_in():
    assert 'os.environ.get("OT_GRT_NONPORT_HOLD", "1") == "1"' in SRC
    assert 'os.environ.get("OT_GRT_PORT_HOLD_PORTS") == "1"' in SRC
    i = SRC.index('export OT_GRT_PORT_HOLD_INCLUDE = 1')
    assert 'OT_GRT_PORT_HOLD_PORTS' in SRC[i - 260:i + 120]
    assert "required=os.environ.get" in SRC


def test_chain_without_a_base_is_a_noop_unless_required(tmp_path):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import gen_phys as G
    (tmp_path / "config.mk").write_text("export X = 1\n")
    assert G.grt_nonport_hold_chain(tmp_path, required=False) is None
    try:
        G.grt_nonport_hold_chain(tmp_path)
        assert False
    except SystemExit:
        pass
