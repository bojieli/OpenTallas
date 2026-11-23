"""ADMISSION-SPILL-1122 (FAM-S81-COL-H10-R4 21:54): a private chain stages its admission bundle on its gen host; spilled off that host the bootstrap
fetched from "hub", which did not hold it ("admission tool transfer failed after 3 attempts").  The bootstrap now tries every source host,
taking the first that holds BUNDLE.json; kit_wave lists the kit / gen host before the hub."""
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import autopilot as AP  # noqa: E402
import kit_wave as KW  # noqa: E402


def setup(tmp_path):
    lane = tmp_path / "scr" / "claude" / "lane"
    dest = lane / "admission_tools" / "abc"
    mirror = tmp_path / "gen_host_copy"                # what the gen host holds at the same path
    (mirror / "die_plan").mkdir(parents=True)
    (mirror / "BUNDLE.json").write_text(json.dumps({"sha256": "abc123"}))
    (mirror / "signoff_chain.py").write_text("import sys\nprint('CHAIN', ' '.join(sys.argv[1:]))\n")
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    # fake ssh: host 'genhost' serves the mirror at the dest path; every other host has nothing there
    (bin_ / "ssh").write_text(f"""#!/bin/bash
for a; do :; done; cmd="$a"; host="${{@: -2:1}}"
echo "$host" >> {tmp_path}/ssh.log
d={dest}; m={mirror}
if [ "$host" = genhost ]; then cmd="${{cmd//"$d"/"$m"}}"; exec bash -c "$cmd"; fi
exit 1
""")
    (bin_ / "ssh").chmod(0o755)
    script = AP.ADMISSION_BOOTSTRAP.replace('"/"+"srv/opentallas-scratch"', repr(str(tmp_path / "scr")))
    return dest, bin_, script


def boot(tmp_path, dest, bin_, script, meta):
    meta = dict(meta, dir=str(dest), sha256="abc123")
    enc = base64.b64encode(json.dumps(meta).encode()).decode()
    env = dict(os.environ, PATH=f"{bin_}:{os.environ['PATH']}")
    return subprocess.run([sys.executable, "-c", script, enc, "a", "b"], capture_output=True, text=True, env=env, cwd=tmp_path)


def test_fetches_from_the_host_that_holds_the_bundle(tmp_path):
    dest, bin_, script = setup(tmp_path)
    r = boot(tmp_path, dest, bin_, script, {"source_host": "hub", "source_hosts": ["genhost", "hub"]})
    assert "ADMISSION_TOOLS READY abc123" in r.stdout and "CHAIN" in r.stdout, r.stdout + r.stderr
    assert (dest / "BUNDLE.json").is_file()


def test_hub_only_still_fails_closed(tmp_path):
    dest, bin_, script = setup(tmp_path)
    r = boot(tmp_path, dest, bin_, script, {"source_host": "hub"})
    assert r.returncode == 3 and "transfer failed after 3 attempts (sources hub)" in r.stdout, r.stdout + r.stderr


def test_kit_wave_lists_kit_and_gen_host_before_hub(monkeypatch):
    monkeypatch.delenv("AP_ADMISSION_HUB", raising=False)
    assert KW.admission_sources("epyc7", "epyc7", "intel2") == ["epyc7", "intel2", "hub"]
    assert KW.admission_sources(None, "localhost") == ["hub"]
