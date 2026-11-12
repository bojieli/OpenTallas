"""KW-FIX-45 LEAF-AFF-ASYNC: opt-in async-pin grouping in leaf_affinity.tcl and its gen_phys export."""
import re
from pathlib import Path

D = Path(__file__).resolve().parent


def test_tcl_default_off_and_gated():
    tcl = (D / "leaf_affinity.tcl").read_text()
    assert "set la_async [la_env OT_LEAF_AFF_ASYNC 0]" in tcl
    blk = tcl[tcl.index("foreach p [all_registers -async_pins]"):]
    blk = blk[:blk.index("proc la_is_bufinv")]
    # opt-in keeps the async pin; default drops it as before
    assert re.search(r"if \{\$la_async\} \{\s*dict set la_d .*\} else \{\s*dict unset la_d", blk, re.S)


def test_gen_phys_export_only_when_env_set():
    src = (D / "gen_phys.py").read_text()
    line = [l for l in src.splitlines() if "export OT_LEAF_AFF_ASYNC = 1" in l]
    assert len(line) == 1
    assert 'os.environ.get("OT_LEAF_AFF_ASYNC", "").strip() == "1"' in line[0]
    # emitted right after the POST_CTS_TCL hook that sources leaf_affinity
    i = src.index('"export POST_CTS_TCL = /work/cts_post.tcl"')
    assert src.index("export OT_LEAF_AFF_ASYNC = 1") - i < 400
