"""Independent admitted PLACE client lifecycle for kit-wave physical handoff.

The worker may stop after a physical receipt; this separately launched systemd
service retains the real ot-run client, its admission, and its proof owner.
This module never terminates a service or infers a physical result from a log.
"""
import hashlib
import json
import re
import time
from pathlib import Path


def _save(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=1) + "\n")
    temp.replace(path)


def start(AP, directory, argv, kit, hosts):
    """Start once, or resume the same immutable client descriptor.

    Call before destructive preparation on worker restart. A saved descriptor
    is authority to resume, never permission to regenerate or relaunch its kit.
    """
    directory = Path(directory)
    descriptor = dict(argv=list(argv), kit=str(kit), hosts=sorted(set(hosts)))
    fingerprint = hashlib.sha256(json.dumps(descriptor, sort_keys=True).encode()).hexdigest()
    path = directory / "place_service.json"
    if path.exists():
        saved = json.loads(path.read_text())
        if saved.get("fingerprint") != fingerprint:
            raise ValueError("existing PLACE service has different inputs; preserve original owner")
        return saved
    directory.mkdir(parents=True, exist_ok=True)
    unit = "kw-place-" + hashlib.sha256(str(directory.resolve()).encode()).hexdigest()[:24]
    saved = dict(descriptor, schema="opentallas.place_service.v1", fingerprint=fingerprint,
                 unit=unit, started=time.time(), logfile=str(directory / "place_service.log"),
                 launch="prepared")
    # Persist before launching. A crash across this boundary must not launch a
    # second client; recovery inspects the named unit and its real log.
    _save(path, saved)
    if AP.launch_unit(unit, Path(saved["logfile"]), argv):
        saved["launch"] = "launched"
    else:
        saved["launch"] = "uncertain"
    _save(path, saved)
    return saved


def status(AP, saved):
    """Real client completion only. A lost client does not authorize a retry."""
    active = AP.unit_active(saved["unit"])
    path = Path(saved["logfile"])
    log = path.read_text(errors="replace") if path.exists() else ""
    # AP.launch_unit prints this only after the actual client exits. RAN is
    # retained for terminal evidence and never synthesized from admission.
    exits = re.findall(r"(?m)^AP_RC=(-?\d+)\s*$", log)
    ran = re.findall(r"(?m)^ot-run: RAN on ([^\s:]+)(?: \(unit [^)\n]+\))?:", log)
    if active:
        state, rc = "running", None
    elif exits:
        state, rc = "complete", int(exits[-1])
    else:
        state, rc = "lost", None
    return dict(state=state, rc=rc, ran_on=ran[-1] if ran else None,
                logfile=str(path), unit=saved["unit"], preserve_owner=True)
