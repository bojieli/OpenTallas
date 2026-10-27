"""Read literal, source-pinned custom IO assignments without evaluating Tcl.

Only the port-to-face map can justify a slot_change. Coordinate, layer, pitch,
ordering and file-name changes alone do not establish a different pin face.
Unsupported/dynamic Tcl and missing inputs provide no evidence of a change.
"""
from __future__ import annotations

import hashlib
import math
import re
import shlex
from pathlib import PurePosixPath


NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
PLACE = re.compile(
    r"place_pin\s+-pin_name\s+\{(?P<pin>[A-Za-z_][A-Za-z_0-9]*(?:\[\d+\])?)\}"
    r"\s+-layer\s+(?P<layer>M\d+)\s+-location\s+\{\s*(?P<x>" + NUMBER + r")\s+(?P<y>" + NUMBER + r")\s*\}"
    r"(?:\s+-pin_size\s+\{\s*" + NUMBER + r"\s+" + NUMBER + r"\s*\})?"   # spread_face_pins.py writes the pin size
    # (RESUB-2 2026-10-19) -force_to_die_boundary is optional: the face is proven by the literal location
    # (<= 0.5 um from exactly one face), not by the flag (tools/qwen_split/qfd_d2d_n_face_pins.py omits it)
    r"(?:\s+-force_to_die_boundary)?\s*;?\s*"
)


def outline(geometry):
    """Only known, finite positive physical widths/heights prove an outline."""
    try:
        geometry = geometry or {}
        values = [geometry.get(key) for key in ("FW", "FH")]
        if not all(isinstance(v, str) and re.fullmatch(NUMBER, v) for v in values):
            return None
        result = list(map(float, values))
        return result if all(math.isfinite(v) and v > 0 for v in result) else None
    except (ValueError, TypeError):
        return None


def regions(value):
    """Canonical port->face map for generated literal --pin-region rules.

    Grouping and along-face ranges are placement details, not a different face.
    Arbitrary regex/Tcl/shell constructions are not verified geometry evidence.
    """
    try:
        if not isinstance(value, str) or not value.startswith("(") or not value.endswith(")"):
            return {"status": "error", "error": "pin regions are not a literal array"}
        tokens = shlex.split(value[1:-1])
        if len(tokens) % 2:
            return {"status": "error", "error": "pin-region options are incomplete"}
        faces = {}
        for flag, rule in zip(tokens[::2], tokens[1::2]):
            if flag != "--pin-region" or not rule.startswith("^("):
                return {"status": "error", "error": "unsupported pin-region option or pattern"}
            parts = rule[2:].split(")(\\[|$)=")
            if len(parts) != 2:
                return {"status": "error", "error": "pin-region pattern is not a literal port group"}
            names = parts[0].split("|")
            if not all(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", n) for n in names):
                return {"status": "error", "error": "pin-region port group is not literal"}
            side_range = parts[1].split(":")
            face = {"left": "W", "right": "E", "top": "N", "bottom": "S"}.get(side_range[0])
            if face is None or len(side_range) > 2:
                return {"status": "error", "error": "pin-region face is invalid"}
            if len(side_range) == 2 and not re.fullmatch(NUMBER + "-" + NUMBER, side_range[1]):
                return {"status": "error", "error": "pin-region coordinate range is not literal"}
            for name in names:
                if name in faces and faces[name] != face:
                    return {"status": "error", "error": "pin-region port has conflicting faces"}
                faces[name] = face
        return {"status": "verified", "faces": faces}
    except ValueError as error:
        return {"status": "error", "error": f"invalid pin-region evidence: {error}"}


def read(kit_text, commit, show):
    """Return absent, verified, or error; `show` reads only the named Git object.

    Deliberately support the generated literal place_pin format, not Tcl programs.
    A valid file is complete as written: every non-comment statement must parse,
    each pin appears once, and each location identifies one unambiguous boundary.
    """
    if "IO_CONSTRAINTS" not in kit_text:
        return {"status": "absent"}
    result = {"status": "error", "commit": commit}

    def fail(message):
        return dict(result, error=message)

    try:
        extra = re.findall(r"^EXTRA=\((.*)\)\s*$", kit_text, re.M)
        if len(extra) != 1 or re.search(r"^EXTRA\+=", kit_text, re.M):
            return fail("custom IO requires one literal EXTRA array")
        tokens = shlex.split(extra[0])
        assignments = [t for t in tokens if t.startswith("IO_CONSTRAINTS=")]
        if len(assignments) != 1:
            return fail("custom IO requires one IO_CONSTRAINTS source")
        index = tokens.index(assignments[0])
        if index == 0 or tokens[index - 1] != "--orfs-var":
            return fail("IO_CONSTRAINTS is not an ORFS variable assignment")
        source = assignments[0].split("=", 1)[1]
        if source.startswith("/src/"):
            source = source[5:]
        path = PurePosixPath(source)
        if (not source or path.is_absolute() or ".." in path.parts
                or re.search(r"[^A-Za-z_0-9./-]", source)):
            return fail("custom IO source is not a literal repository path")
        result["source"] = source
        text = show(commit, source)
        if text is None:
            return fail("custom IO source is missing from the pinned commit")
        result["sha256"] = hashlib.sha256(text.encode()).hexdigest()
        outline = {}
        for key in ("FW", "FH"):
            matches = re.findall(r"^" + key + r"=(" + NUMBER + r")\s*$", kit_text, re.M)
            if len(matches) != 1:
                return fail("custom IO requires a literal FW/FH outline")
            outline[key] = float(matches[0])
        width, height = outline["FW"], outline["FH"]
        if not all(math.isfinite(v) and v > 0 for v in (width, height)):
            return fail("custom IO outline is invalid")
        faces = {}
        for number, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if line.endswith("\\"):
                return fail(f"unsupported custom IO continuation on line {number}")
            if not line or line.startswith("#"):
                continue
            match = PLACE.fullmatch(line)
            if match is None:
                return fail(f"unsupported custom IO statement on line {number}")
            pin = match["pin"]
            if pin in faces:
                return fail(f"duplicate custom IO pin {pin}")
            x, y = float(match["x"]), float(match["y"])
            if not (math.isfinite(x) and math.isfinite(y) and 0 <= x <= width and 0 <= y <= height):
                return fail(f"custom IO pin {pin} lies outside its outline")
            distances = sorted(((x, "W"), (width - x, "E"), (y, "S"), (height - y, "N")))
            # Generated die pins are on a face or inset by 0.144 um. A location
            # farther than 0.5 um, or exactly between two faces, is not proof.
            if distances[0][0] > .5 or abs(distances[0][0] - distances[1][0]) < 1e-8:
                return fail(f"custom IO pin {pin} has no unambiguous boundary face")
            faces[pin] = distances[0][1]
        if not faces:
            return fail("custom IO source has no literal pins")
        return dict(result, status="verified", faces=faces, pins=len(faces), outline=[width, height])
    except (ValueError, TypeError, IndexError) as error:
        return fail(f"invalid custom IO evidence: {error}")


def compare(new, old):
    """A face change requires two complete maps for the exact same set of pins."""
    new = new or {"status": "absent"}
    old = old or {"status": "absent"}
    evidence = {"new": {k: v for k, v in new.items() if k != "faces"},
                "old": {k: v for k, v in old.items() if k != "faces"}}
    if new["status"] == old["status"] == "absent":
        return dict(evidence, status="absent")
    if new["status"] != "verified" or old["status"] != "verified":
        return dict(evidence, status="unverified", error="both source-pinned custom IO maps must be readable")
    nf, of = new["faces"], old["faces"]
    if nf.keys() != of.keys() and "pin_regions" in (new.get("source"), old.get("source")):
        # (RESUB-2 2026-10-19) a per-bit custom map against a per-port pin-region map: compare per PORT when every
        # bit of each port sits on one face and both maps name exactly the same ports (two custom maps still need
        # the exact same pin set)
        nf, of = port_faces(nf), port_faces(of)
        if nf is None or of is None or nf.keys() != of.keys():
            return dict(evidence, status="unverified", error="custom IO pin sets differ; no complete face comparison")
        evidence["level"] = "port"
    elif nf.keys() != of.keys():
        return dict(evidence, status="unverified", error="custom IO pin sets differ; no complete face comparison")
    changed = {p: [of[p], face] for p, face in nf.items() if face != of[p]}
    return dict(evidence, status="changed" if changed else "same", changed_pins=len(changed),
                examples=dict(list(sorted(changed.items()))[:8]))


def port_faces(faces):
    """{pin or pin[bit]: face} -> {port: face}; None when the bits of one port sit on different faces."""
    out = {}
    for pin, face in faces.items():
        port = re.sub(r"\[\d+\]$", "", pin)
        if out.setdefault(port, face) != face:
            return None
    return out


def regions_as_map(regions):
    """a verified, non-empty pin-region map as a compare() operand (per-port faces); absent otherwise."""
    if (regions or {}).get("status") == "verified" and regions.get("faces"):
        return {"status": "verified", "source": "pin_regions", "faces": dict(regions["faces"]),
                "pins": len(regions["faces"])}
    return {"status": "absent"}
