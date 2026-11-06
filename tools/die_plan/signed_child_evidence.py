"""Stage relocatable signed-child evidence without altering physical view inputs."""
import copy
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_same(path, data):
    path = Path(path)
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f"refusing to replace different child evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def stage_signed_child_evidence(view, master, macros, absolute_paths=False):
    """Copy the sealed local proof pack; retain its original tag and exact proof bytes.

    Only metadata paths are relocated. Library/LEF/RTL/SDC inputs are never written.
    absolute_paths supports already-pinned consumers predating relative pointers.
    The same-flow ETM qualification policy remains in signoff.py.
    """
    view, macros = Path(view), Path(macros)
    names = ("provenance.json", "PROVENANCE.json", "signoff.json", "lec.json")
    original = {name: (view / name).read_bytes() for name in names}
    prov = json.loads(original["provenance.json"])
    record = json.loads(original["PROVENANCE.json"])
    signoff = json.loads(original["signoff.json"])
    lec = json.loads(original["lec.json"])
    if prov.get("views_status") != "signoff" or signoff.get("verdict") != "SIGNED":
        raise ValueError("child evidence is not a complete SIGNED view")
    if record.get("kind") != "resign" or record.get("verdict") != "SIGNED" or not record.get("flow_tag"):
        raise ValueError("child evidence has no completed tagged re-sign record")
    if lec.get("verdict") != "EQUIVALENT":
        raise ValueError("child routed LEC is not EQUIVALENT")
    export = prov.get("export") or {}
    if export.get("signoff_sha256") != sha(view / "signoff.json"):
        raise ValueError("child signoff hash differs from signed view export")
    files = export.get("files_sha256") or prov.get("files_sha256") or {}
    for corner in ("tt", "ff"):
        name = f"{master}_{corner}.lib"
        hashes = [value for key, value in files.items() if Path(key).name == name]
        if len(hashes) != 1 or hashes[0] != sha(view / name):
            raise ValueError(f"{name}: library differs from signed view export")
        if not (macros / name).is_file() or sha(macros / name) != hashes[0]:
            raise ValueError(f"{name}: consumed library differs from signed child")
    relocated = copy.deepcopy(prov)
    for key, suffix in (("signoff", "signoff/signoff.json"), ("lec", "lec/lec.json")):
        relative = f"{master}/{suffix}"
        relocated["export"][key] = str((macros / relative).resolve()) if absolute_paths else relative
    relocated["portable_evidence"] = dict(
        schema="opentallas.signed_child_evidence.v1",
        source_files_sha256={name: hashlib.sha256(data).hexdigest() for name, data in original.items()},
        note="Paths relocated only; original proofs and source metadata retained byte-for-byte")
    relocated_record = copy.deepcopy(record)
    relocated_record["lec"] = "lec/lec.json"
    relocated_record["resign_signoff"] = "signoff/signoff.json"
    payload = {
        f"{master}.provenance.json": json.dumps(relocated, indent=1).encode() + b"\n",
        f"{master}/PROVENANCE.json": json.dumps(relocated_record, indent=1).encode() + b"\n",
        f"{master}/signoff/signoff.json": original["signoff.json"],
        f"{master}/lec/lec.json": original["lec.json"],
        f"{master}/source.provenance.json": original["provenance.json"],
        f"{master}/source.PROVENANCE.json": original["PROVENANCE.json"],
    }
    for name, data in payload.items():
        _write_same(macros / name, data)
    return dict(master=master, flow_tag=record["flow_tag"], files=sorted(payload))
