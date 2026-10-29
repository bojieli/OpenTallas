"""Stage the build's DCAL ROM at its literal runtime path before starting a sim."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def stage(build, runtime, viamap=None):
    build, runtime = map(Path, (build, runtime))
    source_files = [Path(p) for p in (build / "vl.f").read_text().splitlines() if p.endswith((".sv", ".v"))]
    matches = []
    for p in source_files:
        text = p.read_text()
        if re.search(r"\bmodule\s+qkd_d2d_cal_seq_pin_bc4\b", text):
            m = re.search(r'parameter\s+VIAMAP\s*=\s*"([^"]+)"', text)
            if not m:
                raise ValueError("DCAL source has no literal VIAMAP")
            matches.append((p, m.group(1)))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one DCAL source, found {len(matches)}")
    source, name = matches[0]
    rel = Path(name)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("DCAL VIAMAP must be a safe relative runtime path")
    viamap = Path(viamap) if viamap else runtime / rel
    if not viamap.is_file():
        raise ValueError(f"missing functional DCAL ROM {viamap}; set KV_DCAL_VIAMAP to the selected bind image")
    data = viamap.read_bytes()
    lines = data.decode().splitlines()
    if len(lines) != 32 or any(not re.fullmatch(r"[0-9a-fA-F]{16}", s.strip()) for s in lines):
        raise ValueError("DCAL ROM must contain 32 physical rows of 64 bits")
    if not any(int(s, 16) for s in lines):
        raise ValueError("DCAL profile ROM is all zero")
    dest = runtime / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.read_bytes() != data:
        raise ValueError("runtime ROM already exists with different content")
    dest.write_bytes(data)
    receipt = dict(source=str(source), viamap=str(viamap.resolve()), runtime_path=name,
                   sha256=hashlib.sha256(data).hexdigest(), rows=len(lines))
    (runtime / "runtime_rom.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--build", required=True)
    p.add_argument("--runtime", required=True)
    p.add_argument("--viamap")
    a = p.parse_args()
    print(json.dumps(stage(a.build, a.runtime, a.viamap)))
