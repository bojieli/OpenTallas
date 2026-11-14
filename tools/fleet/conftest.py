"""HERMETIC_CONF_1114 (ADMIT-TUNE-1): the ot-heavy / ot-heavy-reconcile / ot-run tests must not read the host's live /etc/ot-heavy.conf
(retuned fleet-wide 11-14: SIMPLE_ADMIT, floors, load gate off) -- 8 test files failed on the hub.  ot-heavy and ot-heavy-reconcile read
$OT_HEAVY_CONF when set; point it at an empty file for the whole pytest session (tests that need a conf set their own env / temp file)."""
import os
import tempfile

_f = tempfile.NamedTemporaryFile("w", prefix="ot-heavy-test-", suffix=".conf", delete=False)
_f.close()
os.environ["OT_HEAVY_CONF"] = _f.name

# GATEOFF_1114: ot-run production default for OT_RUN_LOAD_GATE_FACTOR is now 0 (gate off fleet-wide); the load-gate tests exercise the 1.25 rule
os.environ.setdefault("OT_RUN_LOAD_GATE_FACTOR", "1.25")
