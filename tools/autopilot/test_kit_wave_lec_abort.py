"""KW-FIX-8 11-04: a pre-route LEC stopped with its flow says nothing about why the flow stopped."""
import importlib.util, os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location("kit_wave", os.path.join(HERE, "kit_wave.py"))
K = importlib.util.module_from_spec(spec)
spec.loader.exec_module(K)

ABORT = "LEC_ASYNC 2026-11-04 20:01:24 aborted with its flow (exit 137)\n"
STOP = "LEC_ASYNC flow stopped rc 2 before a place checkpoint: pre-route LEC aborted\n"


def test_abort_line_does_not_hide_pdn_error():
    text = ("[ERROR PDN-0006] VDD on M5 is blocked by obstructions on M6, M7 for u_bound.u_kvpc0\n"
            "Error: pdn.tcl, 7 PDN-0006\n" + STOP + ABORT)
    cls, why = K.classify("place", text)
    assert cls == "PLAN", (cls, why)
    assert "PDN-0006" in why


def test_abort_line_does_not_hide_cland_error():
    text = ("Error: global_place.tcl, 5 OT_CLAND no legal nonoverlapping row/site in reserved band for "
            "u_cland_raw_fs_ft1_o\n" + STOP + ABORT)
    cls, why = K.classify("place", text)
    assert cls == "FLOW", (cls, why)
    assert "OT_CLAND" in why


def test_flow_killed_stays_infra():
    cls, _ = K.classify("place", "make: *** [do-3_3] Killed\nflow exit 137\n" + ABORT)
    assert cls == "INFRA"


def test_real_oom_still_infra_with_abort_only_other_line():
    cls, _ = K.classify("place", "Out of memory: Killed process 12 (openroad)\n" + ABORT)
    assert cls == "INFRA"


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("ok", n)
