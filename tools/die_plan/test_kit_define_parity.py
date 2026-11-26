"""kit_define_parity: report-only; SRX 0 kit vs SRX 7 bind is flagged, a matching kit and an unrelated define are not."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_define_parity as KP


def _kit(tmp, kit_defs, bind_defs, src, type_defines=None):
    rtl = tmp / "items" / "t1" / "rtl"
    rtl.mkdir(parents=True)
    (rtl / "kit_rtl.json").write_text(json.dumps({"defines": bind_defs, "plan_type": "svc_t", "type_defines": type_defines or []}))
    (rtl / "kit_rtl.f").write_text("")
    kit = tmp / "kit"
    kit.mkdir()
    (kit / "src.sv").write_text(src)
    (kit / "config.mk").write_text("export DESIGN_NAME = m\nexport VERILOG_FILES = " + str(kit / "src.sv") +
                                   "\nexport VERILOG_DEFINES = " + " ".join(["-DSYNTHESIS"] + ["-D" + d for d in kit_defs]) + "\n")
    (kit / "kit_rtl_paths.json").write_text(json.dumps({"filelist": str(rtl / "kit_rtl.f")}))
    return kit


SRC = "module m;\n`ifdef OT_SVC_SRX\n localparam integer E = `OT_SVC_SRX;\n`endif\n`ifdef OT_S81SL_VP_CFX\n`endif\nendmodule\n"
BIND = ["OT_SVC_SRX=7", "OT_S81SL_VP_CFX", "OT_UNRELATED", "OT_SVC_GP=1076"]


def test_srx0_kit_against_srx7_bind_is_flagged(tmp_path):
    kit = _kit(tmp_path, ["OT_SVC_SRX=0", "OT_S81SL_VP_CFX"], BIND, SRC)
    assert KP.lines(kit) == ["WARN KITDEF-PARITY svc_t OT_SVC_SRX kit=0 bind=7 LAT=1"]


def test_missing_value_define_is_flagged_and_unread_define_is_not(tmp_path):
    kit = _kit(tmp_path, ["OT_S81SL_VP_CFX"], BIND, SRC)
    assert KP.lines(kit) == ["WARN KITDEF-PARITY svc_t OT_SVC_SRX kit=<unset> bind=7 LAT=1"]


def test_matching_kit_is_clean_and_extra_kit_define_is_flagged(tmp_path):
    kit = _kit(tmp_path, ["OT_SVC_SRX=7", "OT_S81SL_VP_CFX"], BIND, SRC)
    assert KP.lines(kit) == []
    kit2 = _kit(tmp_path / "b", ["OT_SVC_SRX=7", "OT_S81SL_VP_CFX", "OT_S81SL_VP_SELREP"], BIND, SRC)
    assert KP.lines(kit2) == ["WARN KITDEF-PARITY svc_t OT_S81SL_VP_SELREP kit=1 bind=<unset> LAT=1"]


def test_type_define_in_both_is_clean_and_no_kit_rtl_is_skipped_not_passed(tmp_path):
    kit = _kit(tmp_path, ["OT_SVC_SRX=7", "OT_S81SL_VP_CFX", "A_TYPE"], BIND, SRC, type_defines=["A_TYPE"])
    assert KP.lines(kit) == []
    (tmp_path / "bare").mkdir()
    (tmp_path / "bare" / "config.mk").write_text("export DESIGN_NAME = m\n")
    assert KP.lines(tmp_path / "bare")[0].startswith("KITDEF-PARITY SKIP")
    assert KP.main([str(kit)]) == 0


def test_script_receipt_prefixes_preserve_values_presence_and_type_precedence(tmp_path):
    src = SRC.replace("endmodule", "`ifdef SYNTHESIS\n`endif\n`ifndef OT_COLL_NATIVE32_OFF\n`endif\nendmodule")
    bind = ["-DSYNTHESIS", "-DOT_COLL_NATIVE32_OFF", "-DOT_SVC_SRX=7", "-DUNUSED"]
    typed = ["-DOT_SVC_SRX=8"]
    kit = _kit(tmp_path / "matching", ["OT_COLL_NATIVE32_OFF", "OT_SVC_SRX=8"], bind, src, typed)
    assert KP.lines(kit) == []

    drift = _kit(tmp_path / "drift", ["OT_SVC_SRX=0"], bind, src, typed)
    assert KP.lines(drift) == [
        "WARN KITDEF-PARITY svc_t OT_COLL_NATIVE32_OFF kit=<unset> bind=1",
        "WARN KITDEF-PARITY svc_t OT_SVC_SRX kit=0 bind=8 LAT=1",
    ]
