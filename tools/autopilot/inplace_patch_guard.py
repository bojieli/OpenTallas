"""Guard for in-place kit / src patch tools (WF-1 11-14): never rewrite a sha-pinned scheduler snapshot.

The 14:51 reg_fanout patch matched run_kit*.sh and rewrote 21 attempt_*/future_lec/run_kit_template.sh copies, whose sha the
lec_tools stage pins ("runner template differs from pinned scheduler snapshot", 16 items).  Every in-place patch tool filters its
candidates through is_patchable()."""
import re

PINNED_PARTS = ("/future_lec/", "/.future_lec-")
PINNED_NAMES = re.compile(r"^(?:run_kit_template\.sh|TOOL\.json|kit_resume\.py|future_kit_lec\.py)(?:\..*)?$")
SKIP_SUFFIX = re.compile(r"\.(?:bak[^/]*|wf1new|orig|new|tmp)$")


def is_patchable(path):
    """False for a sha-pinned snapshot file (anything under future_lec/, the pinned template / tool names) and for backup artefacts"""
    p = str(path).replace("\\", "/")
    base = p.rsplit("/", 1)[-1]
    if any(part in p + "/" for part in PINNED_PARTS):
        return False
    if PINNED_NAMES.match(base) or SKIP_SUFFIX.search(base) or ".bak-" in base:
        return False
    return True


def filter_patchable(paths):
    return [p for p in paths if is_patchable(p)]
