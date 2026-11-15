"""HARD-IP view records and the archive-local read for COUNT-DIRECT host AGIdock (EXPLORER-FABLE-1 11-14, COORD order)."""
import importlib.util, json, pathlib
spec = importlib.util.spec_from_file_location("rtp_hip", str(pathlib.Path(__file__).with_name("release_tree_plan.py"))); rtp = importlib.util.module_from_spec(spec); spec.loader.exec_module(rtp)
CS = rtp._PROV_NS["counts_signed"]
HIP = dict(schema="opentallas.hard_ip_view.v1", name="phy_serdes", verdict="HARD-IP", checks=dict(bind=dict(errors=0), port_bind="PASS", face_guard_fails={}))


def test_hard_ip_view_counts_when_clean():
    assert CS(HIP) is True


def test_hard_ip_view_rejected_on_any_failed_check_or_other_schema():
    assert not CS(dict(HIP, checks=dict(HIP["checks"], bind=dict(errors=2))))
    assert not CS(dict(HIP, checks=dict(HIP["checks"], port_bind="FAIL")))
    assert not CS(dict(HIP, checks=dict(HIP["checks"], face_guard_fails={"a": 1})))
    assert not CS(dict(HIP, schema="opentallas.signoff.v1"))
    assert not CS(dict(verdict="HARD-IP"))


def test_archive_local_read(tmp_path, monkeypatch):
    p = "/archive/opentallas-signed-1114/qwen_compute/phy_serdes/signoff.json"
    (tmp_path / "agidock_archive_index.json").write_text(json.dumps(dict(agidock_signoffs={p: HIP, "/archive/x/bad/signoff.json": dict(verdict="NOT SIGNED")})))
    monkeypatch.setattr(rtp, "CACHE", tmp_path / "release_tree_plan_cache.json")
    recs = rtp.read_direct("AGIdock", [p, "/archive/x/bad/signoff.json", "/archive/x/missing/signoff.json"])
    assert [r["name"] for r in recs] == ["phy_serdes"]
    r = recs[0]; assert r["scan_host"] == "AGIdock" and r["direct"] and r["hard_ip"] and r["path"] == p and "phy_serdes" in rtp.rec_keys(r)


def test_direct_paths_keeps_agidock_rows(tmp_path, monkeypatch):
    (tmp_path / "lanes").mkdir(); (tmp_path / "lanes/COUNT-DIRECT.tsv").write_text("# c\nAGIdock\t/archive/a/signoff.json\nnosuchhost\t/x/signoff.json\n")
    monkeypatch.setattr(rtp, "COORD_DIR", tmp_path)
    dp = rtp.direct_paths()
    assert dp.get("AGIdock") == ["/archive/a/signoff.json"] and "nosuchhost" not in dp
