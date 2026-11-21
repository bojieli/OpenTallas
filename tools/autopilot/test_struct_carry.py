"""FLOW-OPS-0900 11-21 (FABLE-FLOW-0745 class a): an owner structural stop follows the TYPE across plan events (every block sha) until struct-lift;
the in-kit floorplan CELL-CAP stop is classified STRUCTURAL."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def _row(item, block, event, status="RUNNING", attempt=1):
    return {"die": "qwen_kvsys", "item": item, "block_sha": block, "event": event, "status": status, "attempt": attempt}


def _cancel(st, carry=True):
    orig = KW.grt_arm_cancel
    KW.grt_arm_cancel = lambda *a, **k: None
    try:
        return KW.cancel_rows_core(object(), {}, st, "qwen_kvsys", "kv3_pv_v*", "owner >3h rule: unsplit pv over 400k cap", "OPUS-FIX-KV-PV-R5", "STRUCTURAL", {}, carry=carry)
    finally:
        KW.grt_arm_cancel = orig


def test_owner_cancel_stop_holds_the_type_on_the_next_event_block():
    st = {"items": {"a": _row("kv3_pv_v1", "2fa2d8a158bc" + "0" * 20, "KV-D25e3"), "b": _row("kv3_pv_v2", "1dc591883bfd" + "0" * 20, "KV-D25e3")}}
    stops, done = _cancel(st)
    assert stops == 2 and len(done) == 2
    assert set(st["struct_stops"]) == {"qwen_kvsys|kv3_pv_v1|carry", "qwen_kvsys|kv3_pv_v2|carry"}
    cfg = {"dies": {"qwen_kvsys": {}}}
    why = KW.struct_stop_gate(None, cfg, st, "qwen_kvsys", "kv3_pv_v1", "816821b62087" + "0" * 20)        # the KV-D26 block of the same unsplit type
    assert why.startswith("LAUNCH-HELD STRUCT-CARRIED STRUCTURAL [owner OPUS-FIX-KV-PV-R5]") and "struct-lift" in why and "2fa2d8a158bc" in why
    assert KW.struct_stop_gate(None, cfg, st, "qwen_kvsys", "kv3_pv_v1", None)                            # no block known: still held
    # a split renames the type: the new types launch by themselves
    assert KW.struct_stop_gate(None, cfg, st, "qwen_kvsys", "kv3_pv_v1_s0", "aaaaaaaaaaaa") == ""
    assert KW.struct_stop_gate(None, cfg, st, "qwen_kvsys", "kv3_hub_c", "aaaaaaaaaaaa") == ""


def test_per_block_keeps_the_old_block_key():
    st = {"items": {"a": _row("kv3_pv_v1", "A" * 32, "KV-D25e3")}}
    _cancel(st, carry=False)
    assert list(st["struct_stops"]) == ["qwen_kvsys|kv3_pv_v1|b" + "A" * 12]
    cfg = {"dies": {"qwen_kvsys": {}}}
    assert KW.struct_stop_gate(None, cfg, st, "qwen_kvsys", "kv3_pv_v1", "A" * 32)
    assert KW.struct_stop_gate(None, cfg, st, "qwen_kvsys", "kv3_pv_v1", "B" * 32) == ""


def test_force_spends_one_launch_of_a_carried_stop():
    st = {"items": {"a": _row("kv3_pv_v1", "A" * 32, "KV-D25e3")}}
    _cancel(st)
    st["struct_stops"]["qwen_kvsys|kv3_pv_v1|carry"]["force_once"] = True
    logs = []
    ap = type("AP", (), {"log": staticmethod(logs.append)})()
    cfg = {"dies": {"qwen_kvsys": {}}}
    assert KW.struct_stop_gate(ap, cfg, st, "qwen_kvsys", "kv3_pv_v1", "B" * 32, consume=True) == ""
    assert KW.struct_stop_gate(None, cfg, st, "qwen_kvsys", "kv3_pv_v1", "B" * 32).startswith("LAUNCH-HELD STRUCT-CARRIED")


def _ns(**kw):
    base = dict(ap_dir=None, config=None, die="qwen_kvsys", item="kv3_pv_v1", block="current", owner="L", verdict="STRUCTURAL", why="w", old_plans_only=False, per_block=False)
    base.update(kw)
    return argparse.Namespace(**base)


def test_struct_stop_cli_carries_and_struct_lift_is_the_only_release(tmp_path):
    st = {"items": {"a": _row("kv3_pv_v1", "A" * 32, "KV-D26")}}
    KW.save_state(st, tmp_path)
    assert KW.struct_cmd(_ns(cmd="struct-stop", ap_dir=str(tmp_path))) == 0
    st = KW.load_state(tmp_path)
    assert st["struct_stops"]["qwen_kvsys|kv3_pv_v1|carry"]["carry"] is True
    assert KW.struct_stop_for(st, "qwen_kvsys", "kv3_pv_v1", "Z" * 32)[0] == "qwen_kvsys|kv3_pv_v1|carry"
    assert KW.struct_cmd(_ns(cmd="struct-release", ap_dir=str(tmp_path))) == 0                      # struct-release names blocks: a carried stop stays
    assert KW.struct_stop_for(KW.load_state(tmp_path), "qwen_kvsys", "kv3_pv_v1", "Z" * 32)[0]
    assert KW.struct_cmd(_ns(cmd="struct-lift", ap_dir=str(tmp_path), item="kv3_pv_*")) == 0
    assert KW.struct_stop_for(KW.load_state(tmp_path), "qwen_kvsys", "kv3_pv_v1", "Z" * 32) == (None, None)


def test_floorplan_cell_cap_report_is_not_a_class_only_the_opt_in_stop_is():
    rep = "OT_CELL_CAP REPORT stage=floorplan: actual standard cells 456123 above the 400000 run cap: the type must be split\nmake: *** [floorplan] Error 1"
    assert KW.classify("floorplan", rep)[0] != "STRUCTURAL"
    stop = "OT_CELL_CAP STOP stage=floorplan: actual standard cells 456123 above the 400000 run cap (OT_CELL_CAP_STOP=1)\nmake: *** [floorplan] Error 1"
    assert KW.classify("floorplan", stop)[0] == "STRUCTURAL"


class _AP:
    DRY = False

    def __init__(self):
        self.logs, self.app = [], []

    def log(self, m):
        self.logs.append(m)

    def coord_append(self, rel, line):
        self.app.append((rel, line))


def test_cell_cap_report_posts_once_per_type_to_owner_and_plan_lane(tmp_path):
    d1, d2 = tmp_path / "a1", tmp_path / "a2"
    d1.mkdir(); d2.mkdir()
    (d1 / "place.live.log").write_text("x\nOT_CELL_CAP REPORT stage=floorplan: actual standard cells 456123 above the 400000 run cap: the type must be split\n")
    (d2 / "unit.log").write_text('KW_CELL_CAP_REPORT kv3_pv_v1 {"schema":"opentallas.cell_cap_report.v1","why":"actual standard cells 456123 above the 400000 run cap"}\n')
    cfg = {"dies": {"qwen_kvsys": {"die_owner": "OPUS-FIX-KV-PV-R5"}}}
    st = {"items": {"k1": dict(_row("kv3_pv_v1", "A" * 32, "KV-D26"), dir=str(d1), stage="place", unit="u1"),
                    "k2": dict(_row("kv3_pv_v1", "B" * 32, "KV-D26", attempt=2), dir=str(d2), stage="place", unit="u2")}}
    ap = _AP()
    assert KW.cell_cap_report_step(ap, cfg, st) == 1
    assert KW.cell_cap_report_step(ap, cfg, st) == 0                       # once per die|type, not per tick or attempt
    rel, line = ap.app[0]
    assert rel == "lanes/posts/KIT-WAVE.md" and "CELL-CAP [KIT-WAVE -> OPUS-FIX-KV-PV-R5; cc KV-PLAN-R3]" in line and "456123" in line and "split" in line
    assert len(ap.app) == 1


def test_cell_cap_report_reads_only_appended_bytes(tmp_path):
    d = tmp_path / "a1"; d.mkdir()
    log = d / "place.live.log"
    log.write_text("floorplan start\n")
    st = {"items": {"k": dict(_row("hub_c", "A" * 32, "KV-D26"), dir=str(d), stage="place")}}
    ap = _AP()
    assert KW.cell_cap_report_step(ap, {"dies": {}}, st) == 0
    off = st["cell_cap_offsets"]["k"]["place.live.log"]
    assert off == len("floorplan start\n")
    with open(log, "a") as f:
        f.write("OT_CELL_CAP REPORT stage=floorplan: projected movable cells 709000 above 517000\n")
    assert KW.cell_cap_report_step(ap, {"dies": {}}, st) == 1 and "cc qwen_kvsys plan owner" not in ap.app[0][1]
