#!/usr/bin/env python3
"""Image review receipts for a kit's pre-placement plan and physical recipe.

The scheduler writes a request before starting the kit. After looking at the
render, the reviewer records it on the coordination hub and commits the ledger:

  python3 -I plan_visual_review.py REQUEST --image HOST:/path/to/render.png \
      --verdict GOOD --reviewer LANE --finding 'Clear channels and aligned pins'

A BAD or missing receipt never admits a kit. Placement has its own review.
"""

import argparse
import fcntl
import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess
from datetime import datetime
from pathlib import Path

LEDGER = "lanes/PLAN-VISUAL-REVIEW.tsv"
HEADER = "time\tdie\ttype\tform_sha256\tverdict\timage\timage_sha256\treviewer\tfinding\n"
DIES = frozenset(("s81", "s81_head", "qwen_compute", "qwen_kvsys"))
SHA = re.compile(r"[0-9a-f]{64}\Z")
HOST = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*\Z")
PNG = b"\x89PNG\r\n\x1a\n"


def enabled(policy, die, item, kind):
    if die not in DIES or kind != "type":
        return False
    if policy is True:
        return True
    return isinstance(policy, list) and any(
        isinstance(pattern, str) and fnmatch.fnmatchcase(item, pattern) for pattern in policy
    )


def applies(spec):
    return (spec.get("die") in DIES and spec.get("kind", "type") == "type"
            and spec.get("launch_plan_review_required") is True)


def file_sha(path, host=None, image=False):
    """Read the designated producer, never a local file shadowing a remote path."""
    if not isinstance(path, str) or not path.startswith("/") or any(c in path for c in "\r\n\t"):
        raise ValueError("expected an absolute file path")
    if not host or host == "localhost":
        with open(path, "rb") as artifact:
            if image and artifact.read(len(PNG)) != PNG:
                raise ValueError("the review image must be a PNG")
            artifact.seek(0)
            digest = hashlib.sha256()
            for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
                digest.update(chunk)
            return digest.hexdigest()
    if not HOST.fullmatch(host):
        raise ValueError("invalid artifact host")
    if image:
        command = "python3 -I -c " + shlex.quote(
            "import hashlib,sys; f=open(sys.argv[1],'rb'); "
            "d=f.read(); assert d.startswith(b'\\x89PNG\\r\\n\\x1a\\n'); print(hashlib.sha256(d).hexdigest())"
        ) + " " + shlex.quote(path)
    else:
        command = "sha256sum -- " + shlex.quote(path)
    result = subprocess.run(
        ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "ControlPath=none", host, command],
        check=True, capture_output=True, text=True, timeout=45,
    )
    value = result.stdout.split(maxsplit=1)
    if not value or not SHA.fullmatch(value[0]):
        raise ValueError("invalid artifact digest")
    return value[0]


def request(spec, plan_sha="", producer=None, overlay_sha=None, floorplan_sha256=""):
    """Keep attempt directories, placement hosts, and route-only options out of the key."""
    source_manifest = str(spec.get("src_manifest_hash") or "")
    if spec.get("private") and not SHA.fullmatch(source_manifest):
        raise ValueError("private plan review requires an exact sealed or verified source manifest SHA-256")
    plan = spec["plan"]
    plan_sha = plan_sha or file_sha(plan, producer)
    overlay = spec.get("type_overlay")
    if overlay_sha is None:
        overlay_sha = file_sha(overlay, producer) if overlay else ""
    if not SHA.fullmatch(plan_sha) or (overlay and not SHA.fullmatch(overlay_sha)):
        raise ValueError("invalid plan or overlay digest")
    if overlay_sha and spec.get("type_overlay_sha") and overlay_sha != spec["type_overlay_sha"]:
        raise ValueError("type overlay bytes differ from spec")
    source = str(spec.get("src") or "").rstrip("/")

    def normalize(value):
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if isinstance(value, str) and source:
            return value.replace(source + "/", "<src>/")
        return value

    env = {key: value for key, value in (spec.get("gen_env") or {}).items()
           if key not in ("OT_FLOW_TAG", "OT_PLACE_MAX_FANOUT", "OT_GRT_TRANSITION_MODE")}
    recipe = normalize({
        "env": env, "gen_args": spec.get("gen_args") or [],
        "cland_pinslot": spec.get("cland_pinslot"), "piece_of": spec.get("piece_of"),
        "region_guide_geom": spec.get("region_guide_geom"), "leafslew_form": spec.get("leafslew_form"),
        "relay_bay_re": spec.get("relay_bay_re"), "canonical_topology_prepare": spec.get("canonical_topology_prepare"),
    })
    if spec.get("reviewed_station_prepare"):
        station = spec["reviewed_station_prepare"]
        if not SHA.fullmatch(station.get("sha256", "")):
            raise ValueError("invalid named station preparation digest")
        recipe["reviewed_station_prepare_sha256"] = station["sha256"]
        recipe["reviewed_station_tools"] = spec["tools_sha"]
        if spec.get("reviewed_station_stop"):
            recipe["reviewed_station_stop"] = spec["reviewed_station_stop"]
    if floorplan_sha256:
        if (spec.get("reviewed_station_stop") != "floorplan" or not spec.get("reviewed_station_prepare")
                or not SHA.fullmatch(floorplan_sha256)):
            raise ValueError("expected an exact reviewed station floorplan checkpoint")
        recipe["place_after_floorplan_sha256"] = floorplan_sha256
    form = {"plan_sha256": plan_sha, "overlay_sha256": overlay_sha, "recipe": recipe,
            "source": source_manifest or spec.get("src_sha") or ""}
    fingerprint = hashlib.sha256(json.dumps(form, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"die": spec["die"], "item": spec["item"], "plan": plan, "plan_sha256": plan_sha,
            "overlay": overlay, "overlay_sha256": overlay_sha, "gen_host": spec.get("gen_host"),
            "source_manifest_sha256": source_manifest, "form_sha256": fingerprint}


def verdict(text, candidate):
    """The last exact form receipt wins, including a later BAD review."""
    match = (candidate["die"], candidate["item"], candidate["form_sha256"])
    for line in reversed((text or "").splitlines()):
        fields = line.split("\t")
        if (len(fields) == 9 and tuple(fields[1:4]) == match
                and fields[4] in ("GOOD", "BAD") and fields[5]
                and SHA.fullmatch(fields[6]) and fields[7] and fields[8]):
            return fields[4]
    return None


def read_ledger(hub):
    """Use the committed hub copy rather than a possibly stale lane checkout."""
    if hub == "localhost":
        command = ["git", "-C", str(Path.home() / "coord"), "show", f"HEAD:{LEDGER}"]
    elif isinstance(hub, str) and HOST.fullmatch(hub):
        command = ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "ControlPath=none",
                   hub, f"git -C ~/coord show HEAD:{LEDGER}"]
    else:
        raise ValueError("invalid coordination hub")
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    if result.returncode == 0:
        return result.stdout
    if result.returncode == 128 and (f"path '{LEDGER}' does not exist in 'HEAD'" in result.stderr
                                     or f"path '{LEDGER}' exists on disk, but not in 'HEAD'" in result.stderr):
        return ""
    raise ValueError(f"cannot read committed {LEDGER} from {hub}")


def write_request(path, candidate):
    path = Path(path)
    content = json.dumps(candidate, indent=2) + "\n"
    try:
        if path.read_text() == content:
            return
    except OSError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(content)
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    parser.add_argument("--image", required=True)
    parser.add_argument("--verdict", choices=("GOOD", "BAD"), required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--finding", required=True)
    parser.add_argument("--coord", type=Path, default=Path.home() / "coord")
    args = parser.parse_args()
    try:
        candidate = json.loads(args.request.read_text())
        if candidate["die"] not in DIES or not SHA.fullmatch(candidate["form_sha256"]):
            raise ValueError("invalid plan review request")
        producer = candidate.get("gen_host")
        if file_sha(candidate["plan"], producer) != candidate["plan_sha256"]:
            raise ValueError("plan changed since the request was made")
        if candidate.get("overlay") and file_sha(candidate["overlay"], producer) != candidate["overlay_sha256"]:
            raise ValueError("type overlay changed since the request was made")
        host, path = args.image.split(":", 1) if not args.image.startswith("/") else ("", args.image)
        image_sha = file_sha(path, host, image=True)
        fields = (datetime.now().astimezone().isoformat(timespec="seconds"), candidate["die"],
                  candidate["item"], candidate["form_sha256"], args.verdict, args.image,
                  image_sha, args.reviewer, args.finding)
        if any(not value.strip() or any(c in value for c in "\r\n\t") for value in fields):
            raise ValueError("receipt fields must be single-line and nonempty")
        target = args.coord / LEDGER
        with target.open("a+") as ledger:
            fcntl.flock(ledger, fcntl.LOCK_EX)
            if ledger.tell() == 0:
                ledger.write(HEADER)
            ledger.write("\t".join(fields) + "\n")
        print(f"{args.verdict} {candidate['die']}/{candidate['item']} {candidate['form_sha256']}: {target}")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"plan-visual-review: {exc}\n")


if __name__ == "__main__":
    main()
