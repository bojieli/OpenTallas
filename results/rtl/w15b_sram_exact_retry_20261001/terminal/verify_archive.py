"""Verify the immutable terminal archive without executing the simulator."""
import hashlib
import json
import pathlib
import tarfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


root = pathlib.Path(__file__).resolve().parent
manifest = json.loads((root / "manifest.json").read_text())
binding = json.loads((root.parent / "binding.json").read_text())
campaign = json.loads((root.parent / "campaign.json").read_text())
archive = root / "measured_artifacts.tar.gz"
assert digest(archive.read_bytes()) == manifest["archive_sha256"]
with tarfile.open(archive, "r:gz") as bundle:
    assert set(bundle.getnames()) == set(manifest["files"])
    contents = {}
    for name, pin in manifest["files"].items():
        data = bundle.extractfile(name).read()
        assert len(data) == pin["size_bytes"] and digest(data) == pin["sha256"], name
        contents[name] = data
assert manifest["source_commit"] == binding["source_commit"] == campaign["git"]["head"]
binary_hash = digest(contents["binary/Vtb_w15b_v41_tp4"])
assert binary_hash == manifest["binary_sha256"]
for config, record in binding["configs"].items():
    assert record["binary_sha256"] == binary_hash
    sources = json.loads((root.parent / config / "binary_sources.json").read_text())
    assert sources["gen"] == campaign["configs"][config]["parameters"]
    assert digest((root.parent / config / "binary_sources.json").read_bytes()) == record["binary_sources_sha256"]
    for name, pin in sources["pins"].items():
        assert digest(contents["source/" + name]) == pin == campaign["source_sha256"][name]
    rows = [row for row in manifest["runs"] if row["config"] == config]
    assert len(rows) == len(record["runs"]) == 40
    assert {row["run"] for row in rows} == {row["run"] for row in record["runs"]}
    for row in rows:
        original = next(item for item in record["runs"] if item["run"] == row["run"])
        assert digest(contents[row["vm_file"]]) == row["vm_sha256"] == original["vm_sha256"]
        log = root.parent / config / "logs" / row["run"] / "log.txt"
        assert digest(log.read_bytes()) == row["log_sha256"] == original["log_sha256"]
for name, pin in campaign["source_sha256"].items():
    assert digest(contents["source/" + name]) == pin
for config in campaign["configs"].values():
    fixture = config["fixture"]
    prefix = "fixtures/" + fixture + "/"
    data = contents[prefix + "manifest.json"]
    assert digest(data) == config["fixture_manifest_sha256"]
    for name, pin in json.loads(data)["images_sha256"].items():
        assert digest(contents[prefix + name]) == pin
for name, pin in manifest["wrapper_files"].items():
    assert digest((root / name).read_bytes()) == pin
assert manifest["terminal_rc"] == int((root / "campaign_retry.rc").read_text()) == 0
assert manifest["run_count"] == len(manifest["runs"]) == 80
print("TERMINAL_ARCHIVE_PASS: binary, 33 source pins, fixtures, 80 VM/log bindings, rc 0")
