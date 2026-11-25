"""DIECLASS_1125 (OWNER 11-25 00:0x): a kit stage killed by OOM is retried, never left CRASH infra-stopped: ot-heavy-exit's own
EARLYOOM / MEMCG-OOM report is memory evidence."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import autopilot as ap


def test_ot_heavy_exit_oom_report_is_infra_oom():
    for tag in ("EARLYOOM on epyc11 at 2026-11-25T08:01:02: earlyoom SIGTERM pid 12 openroad VmRSS 40.1 GiB",
                "MEMCG-OOM on epyc9 at 2026-11-25T08:01:02+0000: 1 process(es) of unit oth-u-1-2 killed at its cap 48 GB"):
        text = f"ot-heavy: {tag}\not-run: RAN on epyc11 (unit oth-u-1-2): exit 137\nAP_RC=137\n"
        cl = ap.parse_client_log(text)
        assert cl.get("oom_report", "").startswith("ot-heavy: ")
        kind = ap.classify({}, cl)[1]
        assert kind == "infra-oom" and kind in ap.INFRA_KINDS, (tag, kind)


def test_bare_outside_stop_unchanged():
    cl = ap.parse_client_log("ot-run: RAN on epyc11: exit 143\nAP_RC=143\n")
    assert "oom_report" not in cl
    assert ap.classify({}, cl)[1] == "infra-stopped"
