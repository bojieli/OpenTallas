"""S81-KITS-F 10-30: kit_wave/image_params.py (S81 kit-RTL script: image-only per-instance parameters, bind.f overlay)."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("image_params", Path(__file__).resolve().parent / "kit_wave" / "image_params.py")
IP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(IP)

BOUND = """module colx_bound #(
    parameter P_a_INSTANCE = "f0.a",
    parameter P_k = 3
) (input wire clk);
    ot_rom_m #(.INSTANCE(P_a_INSTANCE), .VIAMAP("")) u_a (.clk(clk));
    soft_m #(.W(P_k)) u_s (.clk(clk));
{extra}endmodule
"""


def make(tmp, extra="", top_params=('#(.P_a_INSTANCE("f0.a"))', '#(.P_a_INSTANCE("f1.a"))'), hard=("ot_rom_m",)):
    out = tmp / "out"
    (out / "rtl").mkdir(parents=True)
    (out / "rtl" / "colx_bound.sv").write_text(BOUND.format(extra=extra))
    (out / "rtl" / "s81_bound_top.sv").write_text(
        "module s81_bound_top;\n" + "".join(f"    colx_bound {p} fE{i}_p (\n    );\n" for i, p in enumerate(top_params)) + "endmodule\n")
    (out / "bind_report.json").write_text(json.dumps(dict(errors=[], types={"colx": {"module": "colx_bound"}},
                                                          extra_lib=[])))
    plan = tmp / "plan.json"
    plan.write_text(json.dumps(dict(partition_types={"colx": dict(hard_cores=[dict(inst="u_a", module=m, lef="x.lef")
                                                                              for m in hard])})))
    return out, plan


def test_image_only_param_takes_named_first_instance(tmp_path):
    out, plan = make(tmp_path)
    r = IP.image_choice(out, plan, "colx")
    assert r["image_params"] == ["P_a_INSTANCE"] and r["instance"] == "fE0_p" and r["instances"] == 2
    assert r["consumers"] == {"P_a_INSTANCE": ["ot_rom_m:u_a.INSTANCE"]}


def test_uniform_params_need_no_instance(tmp_path):
    out, plan = make(tmp_path, top_params=('#(.P_a_INSTANCE("f0.a"))',) * 2)
    r = IP.image_choice(out, plan, "colx")
    assert r["image_params"] == [] and r["instance"] is None


def test_differing_param_into_logic_fails_closed(tmp_path):
    out, plan = make(tmp_path, extra="    wire [7:0] w = P_a_INSTANCE;\n")
    with pytest.raises(IP.KitError, match="outside a child parameter port"):
        IP.image_choice(out, plan, "colx")


def test_differing_param_into_soft_child_fails_closed(tmp_path):
    out, plan = make(tmp_path, top_params=('#(.P_a_INSTANCE("f0.a"), .P_k(3))', '#(.P_a_INSTANCE("f1.a"), .P_k(4))'))
    with pytest.raises(IP.KitError, match="not a black-box hard core"):
        IP.image_choice(out, plan, "colx")


def test_differing_param_into_hard_core_without_lef_fails_closed(tmp_path):
    out, plan = make(tmp_path, hard=())
    with pytest.raises(IP.KitError, match="not a black-box hard core"):
        IP.image_choice(out, plan, "colx")


def test_differing_param_in_expression_fails_closed(tmp_path):
    out, plan = make(tmp_path, extra='    ot_rom_m #(.INSTANCE({P_a_INSTANCE, "x"})) u_b (.clk(clk));\n')
    with pytest.raises(IP.KitError):
        IP.image_choice(out, plan, "colx")


def test_overlay_rewrites_dead_worktree_paths_only(tmp_path):
    out, _plan = make(tmp_path)
    src = tmp_path / "src"
    (src / "rtl").mkdir(parents=True)
    (src / "rtl" / "a.sv").write_text("module a; endmodule\n")
    live = out / "rtl" / "colx_bound.sv"
    dead = "/srv/opentallas-scratch2/claude/wt/gone-wt-1030/rtl/a.sv"
    (out / "bind.f").write_text(f"{dead}\n{live}\n")
    rep = json.loads((out / "bind_report.json").read_text())
    rep["extra_lib"] = [dead]
    (out / "bind_report.json").write_text(json.dumps(rep))
    before = (out / "bind_report.json").read_bytes()
    ov = tmp_path / "ov"
    r = IP.overlay(out, src, ov)
    assert r["rewritten"] == 2
    assert (ov / "bind.f").read_text().split() == [str((src / "rtl" / "a.sv").resolve()), str(live)]
    assert json.loads((ov / "bind_report.json").read_text())["extra_lib"] == [str((src / "rtl" / "a.sv").resolve())]
    assert (ov / "rtl").is_symlink() and (out / "bind_report.json").read_bytes() == before   # source bind untouched
    IP.overlay(out, src, ov)                                                                # rerun is idempotent
    assert (out / "bind_report.json").read_bytes() == before


def test_overlay_missing_source_fails_closed(tmp_path):
    out, _plan = make(tmp_path)
    (out / "bind.f").write_text("/srv/opentallas-scratch2/claude/wt/gone-wt-1030/rtl/missing.sv\n")
    with pytest.raises(IP.KitError, match="is gone"):
        IP.overlay(out, tmp_path / "src", tmp_path / "ov")
