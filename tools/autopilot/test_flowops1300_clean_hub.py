"""FLOW-OPS-1300 item 7 (FAM-QC-COLL-R2): run-item off the hub must never delete the only gen copy (clean_hub rm -rf W/gen)."""
import inspect, types
import kit_wave as KW


def fake(rc, out):
    calls = []
    def run(argv, **k):
        calls.append(argv)
        return types.SimpleNamespace(returncode=rc, stdout=out)
    return run, calls


def test_relay_copy_removed_only_when_the_gen_host_is_another_machine_with_the_kit():
    run, calls = fake(0, "bbbb\nKW_GEN_KIT_OK\n")
    assert KW.hub_copy_removable("epyc10", "intel2", "/w/gen/t", run=run, local_id="aaaa") == (True, "")
    assert calls[0][:2] == ["ssh", "-o"] and "epyc10" in calls[0]
    run, _ = fake(0, "aaaa\nKW_GEN_KIT_OK\n")                                   # run-item running ON the gen host
    assert KW.hub_copy_removable("epyc10", "intel2", "/w/gen/t", run=run, local_id="aaaa")[0] is False
    run, _ = fake(0, "bbbb\n")                                                  # kit not on G: the local copy may be the only one
    assert KW.hub_copy_removable("epyc10", "intel2", "/w/gen/t", run=run, local_id="aaaa")[0] is False
    run, _ = fake(255, "")
    assert KW.hub_copy_removable("epyc10", "intel2", "/w/gen/t", run=run, local_id="aaaa")[0] is False
    assert KW.hub_copy_removable("localhost", "intel2", "/w/gen/t", run=run, local_id="aaaa")[0] is False


def test_clean_hub_goes_through_the_check():
    src = inspect.getsource(KW.run_item)
    i = src.index('run("clean_hub"')
    assert "hub_copy_removable(G, hub, K)" in src[max(0, i - 600):i]
