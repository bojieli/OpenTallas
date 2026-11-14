"""WF-1 11-14: a missing priority child view is synced from another host, else INFRA-VIEW-MISSING (never the stale view)."""
import kit_wave as K


def test_view_sync_missing_uses_other_host_and_reports_left():
    calls = []

    def rs(src, dst):
        calls.append(src)
        return 0 if src.startswith("epyc4:") and src.endswith("a.lef") else 1
    left, synced = K.view_sync_missing(["epyc7:/v/a.lef rc=23", "epyc7:/v/b.lib rc=23"], "/d/", ["epyc9", "epyc4"], rs)
    assert synced == ["epyc4:/v/a.lef"]
    assert left == ["epyc7:/v/b.lib rc=23"]
    assert "epyc9:/v/a.lef" in calls and "epyc4:/v/b.lib" in calls


def test_view_sync_local_path_error():
    left, synced = K.view_sync_missing(["/v/a.lef rc=23"], "/d/", ["epyc2"], lambda s, d: 0)
    assert synced == ["epyc2:/v/a.lef"] and left == []


def test_priority_candidate_kinds():
    assert K.view_priority_candidate({"job": "COUNTED m x"})
    assert K.view_priority_candidate({"job": "die-config prov_view_sources"})
    assert K.view_priority_candidate({"job": "PRIVATE TL /k"})
    assert not K.view_priority_candidate({"job": "abc123def456"})


def test_fallback_line_names_item_module_path_and_choice():
    ln = K.view_fallback_line("pcf_h", "mod_x", ["epyc4:/v/mod_x.lef rc=23"], "candidate c1 lef sha 0123456789ab")
    assert ln.startswith("VIEW-FALLBACK pcf_h mod_x: missing epyc4:/v/mod_x.lef") and "chosen candidate c1 lef sha" in ln


def test_infra_view_missing_is_infra_class():
    cls, why = K.classify("prov_views", "INFRA-VIEW-MISSING: VIEW-FALLBACK x m: missing p; chosen plan-contract abstract\nPROVISIONAL view FAIL")
    assert cls == "INFRA"
