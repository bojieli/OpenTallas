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

# ROOTOWNED_1114: spill extraction runs under sudo -n tar in production; the spill tests put a fake tar first on PATH, which sudo would bypass
os.environ.setdefault("OT_SPILL_NO_SUDO", "1")

# FLOW-FLEET-R2 P1 11-22: spill_run asks the destination's ot-heavy-reconcile --gate before copying (admit first); the spill tests run their "ssh" locally, where that would
# read this host's live admission.  Off for the session; test_ot_run_ticket.py turns it on for its own cases.
os.environ.setdefault("OT_RUN_ADMIT_FIRST", "0")
os.environ.setdefault("OT_RUN_TICKETS", os.path.join(tempfile.gettempdir(), "ot-run-test-tickets.json"))

# SCOPE-ENV-1124 (COORD green-main): a suite run INSIDE an ot-run / ot-heavy job (merge gates, ot-run test jobs) inherits that job's scope
# markers.  The ot-heavy tests then ran their fake jobs as crit (OT_HEAVY_CPU=crit skips the load cap), as an admitted child
# (OT_HEAVY_PARENT_UNIT) or with the job's thread count, and 5 tests failed there while passing direct.  Drop the markers for the session;
# a test that needs one sets it itself.
for _k in ("OT_HEAVY_CPU", "OT_HEAVY_DIRECT", "OT_HEAVY_DISK_GB", "OT_HEAVY_MEM_GB", "OT_HEAVY_PARENT_UNIT", "OT_HEAVY_PRIO",
           "OT_HEAVY_SHORT_SLOTS", "OT_HEAVY_TAG", "OT_HEAVY_THREADS", "OT_HEAVY_UNIT", "OT_HEAVY_WAIT_SINCE", "OT_VL_JCAP_N",
           "OT_VL_JCAP_WHY", "OT_RUN_CRIT", "OT_TOOLSTALE_RT"):
    os.environ.pop(_k, None)

# FLEET-OPS 11-25: the delete guard keeps probe / private-kit dirs written in the last 12 h; the guard tests build fresh dirs and expect the other rules to decide (test_ot_delete_guard_probe.py sets its own)
os.environ.setdefault("OT_PROBE_HOLD_S", "0")
