#!/usr/bin/env python3
"""Transfer one verified KIT_RTL closure without repeating its native producer."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import kit_rtl_closure as closure

NAME = "kit_rtl_prepared.json"
SCHEMA = "opentallas.kit_rtl_prepared.v1"
INSTALLED = ".kit_rtl_imported.json"
HEAD_SCRIPT = (
    b'#!/bin/bash\nset -euo pipefail\n: "${TYPE:?}" "${OUT:?}" "${PLAN:?}"\n'
    b'python3 -I tools/s81_head/head_wave_kit_rtl.py export --plan "$PLAN" --out "$OUT" --type "$TYPE"\n'
)
CONTROL = ("kit_rtl.json", "kit_rtl.f", "kit_rtl_sim.f",
           "kit_rtl.producer.json", "native_sink_censuses.json")


def configured(sp, seal):
    """The HEAD exporter currently has the explicit portable input contract."""
    kr = sp["kit_rtl"]
    if (not sp.get("private") or sp.get("die") != "s81_head" or sp.get("kind") != "type"
            or kr.get("mode") != "script" or kr.get("bind_out")
            or any(sp.get(k) for k in ("canonical_topology_prepare", "prov_views",
                                       "type_overlay", "gen_pins", "gen_tools_manifest_sha"))
            or not re.fullmatch(r"[0-9a-f]{64}", seal.get("manifest_hash") or "")
            or not re.fullmatch(r"[0-9a-f]{40}", sp.get("tools_sha") or "")):
        return None
    return {"die": sp["die"], "item": sp["item"], "source": seal["manifest_hash"],
            "runtime": sp["tools_sha"], "source_root": sp["src"]}


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
        tmp = Path(handle.name)
        json.dump(value, handle, sort_keys=True)
        handle.write("\n")
    try:
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def identity(inputs, launch, script, plan):
    launch, script, plan = map(Path, (launch, script, plan))
    if script.read_bytes() != HEAD_SCRIPT:
        raise ValueError("unsupported HEAD KIT_RTL script")
    packet = plan.parent
    prepared = read(packet / "wave_prepare.json")
    wrapper = prepared["published_wrappers"][inputs["item"]]
    module = wrapper["module"]
    if not re.fullmatch(r"[A-Za-z_]\w*", module, flags=re.ASCII):
        raise ValueError("invalid published wrapper name")
    actual = {"plan": closure.digest(plan),
              "sidecar": closure.digest(packet / "source_sidecar.json"),
              "wrapper": closure.digest(packet / "published" / (module + ".sv"))}
    if (inputs["item"] not in prepared["eligible_types"]
            or actual != {"plan": prepared["prepared_plan_sha256"],
                          "sidecar": prepared["sidecar_sha256"],
                          "wrapper": wrapper["sha256"]}):
        raise ValueError("prepared HEAD plan packet changed")
    for asset in prepared.get("native_sink_censuses", {}).values():
        exact = Path(asset["path"])
        if not exact.is_file() and "physical" in exact.parts:
            rel = Path(*exact.parts[exact.parts.index("physical"):])
            options = [launch / rel]
            if "physical" in packet.parts:
                options.insert(0, Path(*packet.parts[:packet.parts.index("physical")]) / rel)
            exact = next((p for p in options if p.is_file()), exact)
        if closure.digest(exact) != asset["sha256"]:
            raise ValueError("prepared HEAD native sink census changed")
    # Capture the same admitted worker's semantic settings. Resource settings
    # differ between the actual producer and the bounded transfer consumer.
    environment = {k: v for k, v in os.environ.items()
                   if k.startswith("OT_") and not k.startswith(("OT_HEAVY_", "OT_RUN_"))}
    environment_sha = hashlib.sha256(json.dumps(environment, sort_keys=True).encode()).hexdigest()
    return dict(inputs, **actual, ambient=environment_sha, packet=closure.digest(packet / "wave_prepare.json"),
                exporter=closure.digest(launch / "tools/s81_head/head_wave_kit_rtl.py"),
                generator=closure.digest(launch / "tools/die_plan/gen.py"),
                python=closure.digest(Path(sys.executable)))


def relative(name):
    path = Path(name)
    if not path.parts or path.is_absolute() or ".." in path.parts or str(path) != name or "\n" in name or "\r" in name:
        raise ValueError(f"invalid closure path {name!r}")
    return path


def regular(root, name):
    rel = relative(name)
    path = root / rel
    if not path.is_file() or path.resolve() != root.resolve() / rel:
        raise ValueError(f"closure file is missing or symlinked: {name}")
    return path


def publish(rtl, expected, runtime_directory=None):
    runtime_directory = runtime_directory or rtl
    meta = read(regular(rtl, "kit_rtl.json"))
    stage = meta["input_closure"]
    if (meta["schema"] != "opentallas.head_wave_kit_rtl.v1" or meta["plan_type"] != expected["item"]
            or meta["published_wrapper_sha256"] != expected["wrapper"]
            or stage["sealed"] is not True or stage["runtime_directory"] != str(runtime_directory)):
        raise ValueError("KIT_RTL output does not match the exact sealed HEAD stage")
    for name in ("kit_rtl.f", "kit_rtl_sim.f"):
        if name == "kit_rtl_sim.f" and not (rtl / name).exists():
            continue
        for line in regular(rtl, name).read_text().splitlines():
            if line.strip() and str(Path(line).relative_to(runtime_directory)) not in stage["files"]:
                raise ValueError(f"unsealed input in {name}: {line}")
    files = {name: record["sha256"] for name, record in stage["files"].items()}
    files.update({name: closure.digest(regular(rtl, name)) for name in CONTROL
                  if (rtl / name).exists()})
    if "native_sink_censuses.json" in files:
        censuses = read(regular(rtl, "native_sink_censuses.json"))
        for record in censuses.values():
            name = str(Path(record["path"]).relative_to(runtime_directory))
            if not relative(name).is_relative_to("assets"):
                raise ValueError("native sink census is outside the retained staged assets")
            files[name] = record["sha256"]
    return {"schema": SCHEMA, "identity": expected, "files": files,
            "bytes": sum(regular(rtl, name).stat().st_size for name in files)}


def checked(path, receipt, portable_from=None):
    if receipt.get("schema") != SCHEMA or not isinstance(receipt.get("files"), dict):
        raise ValueError("invalid KIT_RTL handoff receipt")
    total = 0
    for name, digest in receipt["files"].items():
        file = regular(path, name)
        total += file.stat().st_size
        data = file.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"prepared RTL differs from receipt: {name}")
        if (portable_from and file.suffix.lower() in {".sv", ".v", ".svh", ".vh"}
                and portable_from in data):
            raise ValueError(f"prepared RTL embeds the producer work directory: {name}")
    if total != receipt["bytes"]:
        raise ValueError("prepared RTL transfer length differs from receipt")


def restore(rtl, receipt, donor, host):
    receipt_id = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    if rtl.exists() or rtl.is_symlink():
        if not rtl.is_symlink() and (rtl / INSTALLED).is_file():
            prior = read(regular(rtl, INSTALLED))
            if prior["donor_receipt"] == receipt_id:
                checked(rtl, prior["installed"])
                return prior["installed"]
        raise ValueError("refusing to replace an existing KIT_RTL directory")
    if not donor.is_absolute() or donor.name != "rtl" or not re.fullmatch(r"/[A-Za-z0-9_./@+\-]+", str(donor)) or ".." in donor.parts:
        raise ValueError("unsafe KIT_RTL donor path")
    if host and not re.fullmatch(r"(?:epyc|intel)[0-9]+", host):
        raise ValueError("unsafe KIT_RTL donor host")
    for name in receipt["files"]:
        relative(name)
    with tempfile.TemporaryDirectory(prefix=".kit-rtl-incoming-", dir=rtl.parent) as path:
        incoming = Path(path)
        source = (f"{host}:" if host else "") + f"{donor}/"
        subprocess.run(["rsync", "-a", "--files-from=-", "-e",
                        "ssh -o BatchMode=yes -o ControlPath=none", source, str(incoming) + "/"],
                       input="".join(name + "\n" for name in receipt["files"]), text=True, check=True)
        checked(incoming, receipt, portable_from=(str(donor.parent) + "/").encode())
        (incoming / "closure" / "bind").mkdir(parents=True, exist_ok=True)
        closure.relocate(incoming, runtime_directory=rtl)
        installed = publish(incoming, receipt["identity"], runtime_directory=rtl)
        write(incoming / INSTALLED, {"donor_receipt": receipt_id, "installed": installed})
        if rtl.exists() or rtl.is_symlink():
            raise ValueError("KIT_RTL destination appeared while importing")
        incoming.rename(rtl)
    return installed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("identity", "publish", "restore", "check"))
    ap.add_argument("request")
    args = ap.parse_args()
    request = json.loads(args.request)
    rtl = Path(request["rtl"])
    if args.mode == "identity":
        result = identity(request["inputs"], request["launch"], request["script"], request["plan"])
    elif args.mode == "publish":
        result = publish(rtl, request["identity"])
    else:
        receipt = request["receipt"]
        effective = identity(request["inputs"], request["launch"], request["script"], request["plan"])
        if effective != receipt["identity"]:
            raise ValueError("prepared RTL effective input identity changed")
        if args.mode == "restore":
            result = restore(rtl, receipt, Path(request["donor"]), request["host"])
        else:
            checked(rtl, receipt)
            result = receipt
    print("KW_KIT_RTL_HANDOFF " + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
