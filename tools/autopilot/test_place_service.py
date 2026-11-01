"""Detached PLACE service survives its worker and cannot be silently relaunched."""
from pathlib import Path
import pytest
import place_service as P


class AP:
    def __init__(self):
        self.launches = []
        self.active = False

    def launch_unit(self, unit, log, argv):
        self.launches.append((unit, log, argv))
        self.active = True
        return True

    def unit_active(self, unit):
        return self.active


def test_resume_retains_original_client_and_rejects_new_scope(tmp_path):
    ap = AP()
    saved = P.start(ap, tmp_path, ["ot-run", "--", "place"], "/scratch/kit", ["intel2"])
    assert len(ap.launches) == 1
    assert P.start(ap, tmp_path, saved["argv"], saved["kit"], saved["hosts"]) == saved
    assert len(ap.launches) == 1
    with pytest.raises(ValueError, match="preserve original owner"):
        P.start(ap, tmp_path, ["ot-run", "--", "other"], "/scratch/kit", ["intel2"])
    assert len(ap.launches) == 1


def test_only_real_client_exit_is_terminal_not_physical_or_admission(tmp_path):
    ap = AP()
    saved = P.start(ap, tmp_path, ["ot-run"], "/scratch/kit", ["intel2"])
    log = Path(saved["logfile"])
    log.write_text("ot-heavy: admitted on intel2 as oth-test\nphysical rc=0\n")
    assert P.status(ap, saved)["state"] == "running"
    ap.active = False
    result = P.status(ap, saved)
    assert result["state"] == "lost" and result["rc"] is None and result["preserve_owner"]
    assert result["ran_on"] is None
    log.write_text(log.read_text() + "ot-run: RAN on intel2 (unit oth-test): command\nAP_RC=11\n")
    result = P.status(ap, saved)
    assert result["state"] == "complete" and result["rc"] == 11 and result["ran_on"] == "intel2"
    P.start(ap, tmp_path, saved["argv"], saved["kit"], saved["hosts"])
    assert len(ap.launches) == 1  # Lost/failed proof owner is never duplicated.


def test_place_receipt_host_is_fresh_unique_and_explicitly_opted_in():
    import autopilot as ap
    saved = dict(hosts=["intel1", "intel2"], kit="/scratch/kit", started=1000)
    receipt = dict(goal="place", rc=0, started=1000, ended=1100, run_id="run1", physical_id="phys",
                   proof_id="eq-inputs", proof_owner="proof1", checkpoint_current=True)
    probe = dict(exists=True, config=True, physical_identity="phys", active_containers=["proof1"],
                 physical_starts=[dict(goal="place", started=1000, run_id="run1", physical_id="phys")],
                 physical_completions=[receipt], async_proof=dict(identity="eq-inputs", owner="proof1", done=False))
    assert ap.physical_receipt(dict(goal="place", started=1000), probe) is None
    assert P.physical(ap, saved, {"intel2": probe})["host"] == "intel2"
    with pytest.raises(ValueError, match="multiple live PLACE owners"):
        P.physical(ap, saved, {"intel1": probe, "intel2": probe})
    probe["active_containers"] = []
    assert P.physical(ap, saved, {"intel2": probe}) is None
    with pytest.raises(ValueError, match="route/signoff"):
        ap.physical_receipt(dict(goal="route"), probe, goals=("route",))
