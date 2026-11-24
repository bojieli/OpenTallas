"""pytest: ADV-CTLM-AGES on the QC C1g tt_ctlm positive (program 19/19/17/17 vs delivered 14/10; core XPF 21 vs 1 + R_HR = 20)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_ctlm_ages as A  # noqa: E402


def test_c1g_positive():
    r = A.judge({"R_CMD": 19, "R_HR": 19, "R_SS": 17, "R_AG": 17}, 20, {"core_1": 21}, {"R_CMD": 14, "R_HR": 10})
    kinds = [k for k, _ in r]
    assert kinds.count("AGE") == 2 and "XPF-CORE" in kinds and "XPF-PROG" not in kinds
    assert any("21 != 1 + program R_HR 19 = 20" in t for _, t in r)


def test_consistent_program_passes():
    assert A.judge({"R_CMD": 14, "R_HR": 10, "R_ST": 10}, 11, {"core_1": 11}, {"R_CMD": 14, "R_HR": 10, "R_ST": 10}) == []


def test_xpf_rule_on_program_value():
    assert [k for k, _ in A.judge({"R_HR": 19}, 21, {}, {})] == ["XPF-PROG"]


def test_never_raises():
    assert A.findings({}, "p", None)[0].startswith("WARN ADV-CTLM-AGES not checked")


def test_delivered_uses_observed_w5_return_lanes(tmp_path):
    lane_ids = {
        "R_CMD": ("tt_ctlm__cmd_cmd_wi", 14, 19),
        "R_HR": ("tt_ctlm__hr_hr_wi", 10, 19),
        "R_ST": ("tt_ctlm__tl_st_wi", 10, 19),
        "R_SS": ("sl_W5_fw__ss_wo_ss5", 10, 17),
        "R_AG": ("sl_W5_fw__ag_wo_ag5", 13, 17),
    }
    lanes = [
        dict(lane=lane, delivered=observed, table=planned, bind_plan_cycles=planned)
        for lane, observed, planned in lane_ids.values()
    ]
    metrics = tmp_path / "bind_lane_asbuilt.json"
    metrics.write_text(json.dumps({"lanes": lanes}))
    observed = A._delivered(tmp_path)
    assert observed == {key: values[1] for key, values in lane_ids.items()}

    relay = {key: values[2] for key, values in lane_ids.items()}
    assert [kind for kind, _ in A.judge(relay, 20, {}, observed)] == ["AGE"] * 5

    lanes[-1].pop("delivered")
    metrics.write_text(json.dumps({"lanes": lanes}))
    assert "R_AG" not in A._delivered(tmp_path)


def test_endpoint_age_adds_only_the_relative_landing_pad(tmp_path):
    measured = {"R_CMD": 19, "R_HR": 19, "R_ST": 19, "R_SS": 17, "R_AG": 17}
    groups = [
        dict(sink_part="sl_W5_fw", members=[
            dict(lane="tt_ctlm__cmd_cmd_wi", sink_port="cmd_i", sink_bits=[[0, 115]], bound_stages=18, landed_stages=22),
            dict(lane="tt_ctlm__hr_hr_wi", sink_port="hr_i", sink_bits=[[0, 226]], bound_stages=19, landed_stages=23),
            dict(lane="tt_ctlm__hr_hr_wi", sink_port="hr_i", sink_bits=[[227, 452]], bound_stages=19, landed_stages=23),
            dict(lane="tt_ctlm__tl_st_wi", sink_port="st_up_i", sink_bits=[[0, 1087]], bound_stages=19, landed_stages=19),
        ]),
        dict(sink_part="tt_ctlm", members=[
            dict(lane="sl_W5_fw__ss_wo_ss5", sink_port="ss5", sink_bits=[[0, 106]], bound_stages=17, landed_stages=17),
            dict(lane="sl_W5_fw__ag_wo_ag5", sink_port="ag5", sink_bits=[[0, 9]], bound_stages=17, landed_stages=17),
        ]),
    ]
    path = tmp_path / "bus_groups.json"
    path.write_text(json.dumps({"landing": groups}))
    assert A._endpoint_delivered(tmp_path, measured) == measured | {"R_CMD": 23, "R_HR": 23}

    groups[0]["members"][2]["landed_stages"] = 24
    groups[1]["members"][1]["sink_bits"] = [[0, 8]]
    path.write_text(json.dumps({"landing": groups}))
    assert A._endpoint_delivered(tmp_path, measured) == {"R_CMD": 23, "R_ST": 19, "R_SS": 17}
