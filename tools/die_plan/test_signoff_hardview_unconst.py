"""UNCONST-IN-HARDVIEW (COORD 11-22, COLROM a6098c6b5f): unconstrained endpoints that are input pins of a SIGNED hard-core view (no check
arc in its lib) do not fail signoff.unconstrained; a soft endpoint, or one under an unsigned view, still does.  Shape of col H: 4 x 51."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signoff as S  # noqa: E402


def kit(tmp_path, soft=0, unsigned=0):
    src = tmp_path / "src"
    for v, mod, verdict in (("col3_c_pw_1115", "ot_v41_bf_col3_c", "SIGNED"), ("bf_col3_1104", "ot_v41_bf16_half", "SIGNED"),
                            ("prov_x", "ot_prov", "NOT SIGNED")):
        d = src / "physical/die_plan/s81/cores/views" / v / mod
        d.mkdir(parents=True)
        (d / "signoff.json").write_text(json.dumps({"verdict": verdict}))
    lib = lambda v, m: f"physical/die_plan/s81/cores/views/{v}/{m}/{m}_tt.lib"   # noqa: E731
    rows, eps = [], []
    for e in ("e5w", "e5e", "e10w", "e10e"):
        rows.append({"inst": f"u_bound.u_u_{e}.u_view.u_c", "module": "ot_v41_bf_col3_c", "lib": lib("col3_c_pw_1115", "ot_v41_bf_col3_c")})
        eps += [f"u_bound.u_u_{e}.u_view.u_c/i1_t[{i}]" for i in range(25)]
        for h in ("ha", "hb"):
            rows.append({"inst": f"u_bound.u_u_{e}.u_view.u_{h}", "module": "ot_v41_bf16_half", "lib": lib("bf_col3_1104", "ot_v41_bf16_half")})
            eps += [f"u_bound.u_u_{e}.u_view.u_{h}/t[{i}]" for i in range(13)]
    rows.append({"inst": "u_bound.u_px", "module": "ot_prov", "lib": lib("prov_x", "ot_prov")})
    eps += [f"u_bound.u_px/a[{i}]" for i in range(unsigned)] + [f"u_bound.u_soft_reg_{i}/D" for i in range(soft)]
    k = tmp_path / "kit"
    (k / "signoff/tt").mkdir(parents=True)
    (k / "core_latency.json").write_text(json.dumps({"rows": rows}))
    (k / "kit_rtl_paths.json").write_text(json.dumps({"src_tree": str(src)}))
    log = ("SO DONE 1\nSO_PATH_BEGIN CHECK_SETUP\n" + f"Warning: There are {len(eps)} unconstrained endpoints.\n"
           + "".join(f"  {x}\n" for x in eps) + "SO_PATH_END\n")
    (k / "signoff/tt/sta.log").write_text(log)
    (k / "signoff/signoff.json").write_text(json.dumps({"corners": {"tt": {"done": True, "check_setup": {"unconstrained": len(eps)}}}}))
    return k, log


def test_col_h_shape_204_to_0(tmp_path):
    k, log = kit(tmp_path)
    hard = S.signed_hard_instances(k)
    assert len(hard) == 12 and "u_bound.u_px" not in hard
    cs = S.check_setup_counts(S.parse_session(log)["blocks"]["CHECK_SETUP"], hard_signed=hard)
    assert cs["unconstrained"] == 0 and cs["hard_view_unconstrained"] == 204
    assert S.check_setup_counts(S.parse_session(log)["blocks"]["CHECK_SETUP"])["unconstrained"] == 204


def test_soft_and_unsigned_view_endpoints_still_fail(tmp_path):
    k, log = kit(tmp_path, soft=2, unsigned=3)
    cs = S.check_setup_counts(S.parse_session(log)["blocks"]["CHECK_SETUP"], hard_signed=S.signed_hard_instances(k))
    assert cs["unconstrained"] == 5 and cs["hard_view_unconstrained"] == 204


def test_rescore_existing_record_without_sta(tmp_path, monkeypatch):
    k, _ = kit(tmp_path, soft=1)
    rec = json.loads((k / "signoff/signoff.json").read_text())
    assert S.rescore_check_setup(rec, k / "signoff/signoff.json") == {"tt": (205, 1)}
    monkeypatch.setenv("OT_SIGNOFF_HARDVIEW_UNCONST", "0")
    rec = json.loads((k / "signoff/signoff.json").read_text())
    assert S.rescore_check_setup(rec, k / "signoff/signoff.json") == {}
