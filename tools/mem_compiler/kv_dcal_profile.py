#!/usr/bin/env python3
"""Generate the content of the single 64x32 KV calibration-profile ROM.

Addresses 0..35 are the 36 20-bit START offsets, 36..43 the scalar schedule
constants in SCALARS order, and 44..63 reserved zero. The macro implements a
single synchronous read; this tool changes only its via layer, never its views.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import rom_gen

NAME = "ot_rom_64x32_m2"
SCALARS = ("PERIOD", "TX_SEG1", "RX_SEG1", "TX_SEG2", "RX_SEG2", "ADM_OFS", "ADM_LEN", "FIRST_OFS")
ROOT = Path(__file__).resolve().parents[2]
MACRO = ROOT / "physical/asap7_memory_macros_v2" / NAME / f"{NAME}.json"


def compile_shape(out: Path) -> dict:
    """Use the existing compiler and v2 track-alignment rules for this shape."""
    import build_aligned_v2 as aligned
    spec = rom_gen.RomSpec(NAME, 64, 32, 2)
    v1 = rom_gen.compile_macro(spec)
    with aligned.patched(rom_gen, macro_outline=aligned.aligned_outline,
                         write_lef=aligned.aligned_write_lef,
                         GENERATOR_VERSION=f"{rom_gen.GENERATOR_VERSION}+{aligned.ALIGN_VERSION}"):
        sheet = rom_gen.compile_macro(spec, out)
    aligned.finish(out, NAME, v1, (v1["area"]["macro_width_um"], v1["area"]["macro_height_um"]),
                   {"kind":"rom", "spec":sheet["spec"]})
    return json.loads((out / NAME / f"{NAME}.json").read_text())


def pack_profile(profile: dict) -> list[int]:
    """Fail on truncation: all scalars fit 32 bits, every START fits 20 bits."""
    expected = {"START", *SCALARS}
    if set(profile) != expected:
        raise ValueError(f"profile keys differ: missing {sorted(expected-set(profile))}, extra {sorted(set(profile)-expected)}")
    starts = profile["START"]
    if not isinstance(starts, list) or len(starts) != 36:
        raise ValueError("START must contain exactly 36 offsets")
    words = []
    for name, value, width in [(f"START[{i}]", v, 20) for i, v in enumerate(starts)] + [(k, profile[k], 32) for k in SCALARS]:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < (1 << width):
            raise ValueError(f"{name} must be an unsigned {width}-bit integer, got {value!r}")
        words.append(value)
    if starts[0] != 0 or any(b-a < 2 for a,b in zip(starts, starts[1:])):
        raise ValueError("START must begin at zero and leave at least two clocks between used layers")
    if profile["PERIOD"] - starts[-1] < 2:
        raise ValueError("PERIOD must leave two clocks after the last layer")
    if profile["ADM_OFS"] < 68 or profile["ADM_LEN"] == 0:
        raise ValueError("admission must follow the 66-word init stream with a two-clock lead")
    if profile["FIRST_OFS"] < profile["ADM_OFS"] + profile["ADM_LEN"] + 2:
        raise ValueError("first token must follow admission with a two-clock lead")
    return words + [0] * (64-len(words))


def extract_sv(text: str) -> dict:
    """Read generated literal localparams only; expressions and X/Z fail closed."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    def value(name):
        matches = re.findall(r"\blocalparam\b[^;]*?\b"+re.escape(name)+r"\s*=\s*([^;]+);", text)
        if len(matches) != 1:
            raise ValueError(f"expected one literal localparam {name}, found {len(matches)}")
        raw = matches[0].strip().replace("_", "")
        m = re.fullmatch(r"(?:(\d+)'([hdb])([0-9a-f]+)|(\d+))", raw, re.I)
        if not m: raise ValueError(f"{name} is not a known unsigned literal: {raw}")
        if m.group(4): return int(m.group(4), 10)
        n = int(m.group(3), {"h":16,"d":10,"b":2}[m.group(2).lower()])
        if n >= 1 << int(m.group(1)): raise ValueError(f"{name} overflows its declared literal width")
        return n
    packed = value("D2D_CAL_START")
    if packed >= 1 << 720: raise ValueError("START exceeds 36 x 20 bits")
    profile = {"START": [(packed >> (20*i)) & ((1<<20)-1) for i in range(36)]}
    aliases = {"PERIOD":"D2D_TOKEN_PERIOD", "FIRST_OFS":"D2D_FIRST_TOKEN",
               "ADM_OFS":"D2D_ADM_OFS", "ADM_LEN":"D2D_ADM_LEN"}
    for k in SCALARS: profile[k] = value(aliases.get(k, "D2D_CAL_K_"+k))
    pack_profile(profile)
    return profile


def personalise(profile: dict, out: Path, instance: str = "kv_dcal", macro: Path = MACRO) -> dict:
    """Write image, via map and rom_gen-compatible manifest with no absolute paths."""
    if not instance or instance[0].isdigit() or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in instance):
        raise ValueError("instance must be a non-empty Verilog identifier")
    spec = rom_gen.spec_from_sheet(macro)
    if spec != rom_gen.RomSpec(NAME, 64, 32, 2):
        raise ValueError("profile requires the generated 64x32 m2 macro")
    words = pack_profile(profile)
    out.mkdir(parents=True, exist_ok=True)
    image = out / f"{instance}.hex"
    image.write_text("".join(f"{w:08x}\n" for w in words))
    rec = rom_gen.personalise_instance(spec, words, instance + "_r0_c0", out)
    manifest = {"schema": "opentallas.rom-personalisation.v1", "macro": NAME,
                "ecc": "none", "image": image.name,
                "image_sha256": rom_gen.asap7.sha256_file(image), "data_bits": 32,
                "tile_data_bits": 32, "instances": [rec],
                "content_signature": rom_gen.die_signature([rec]),
                "viamap_set_sha256": hashlib.sha256(rec["viamap_sha256"].encode()).hexdigest(),
                "profile_schema": "opentallas.kv-dcal-profile.v1",
                "word_addresses": {"START": [0, 35], **{k: 36+i for i, k in enumerate(SCALARS)}, "RESERVED_ZERO": [44, 63]}}
    profile_file = out / f"{instance}.profile.json"
    profile_file.write_text(json.dumps(profile, indent=2, sort_keys=True)+"\n")
    manifest["profile"] = profile_file.name
    manifest["profile_sha256"] = rom_gen.asap7.sha256_file(profile_file)
    target = out / f"{instance}.personalisation.json"
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    check = rom_gen.verify_personalisation(target, image, macro)
    if check["verdict"] != "PASS":
        raise ValueError(f"ROM content verification failed: {check}")
    return {"manifest": target.name, "image": image.name, "viamap": rec["viamap"],
            "check": check, "manifest_sha256": rom_gen.asap7.sha256_file(target)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("profile", type=Path, nargs="?", help="JSON with START[36] and the eight scalar keys")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--compile-shape", action="store_true", help="compile the content-independent aligned64x32m2 views under --out")
    ap.add_argument("--sv", action="store_true", help="extract generated literal localparams from the input SystemVerilog")
    ap.add_argument("--instance", default="kv_dcal")
    ap.add_argument("--macro", type=Path, default=MACRO)
    a = ap.parse_args()
    if a.compile_shape:
        sheet = compile_shape(a.out)
        print(json.dumps({"spec":sheet["spec"], "area":sheet["area"], "timing":sheet["timing"]}, indent=2))
        return 0
    if a.profile is None:
        ap.error("profile is required unless --compile-shape is selected")
    profile = extract_sv(a.profile.read_text()) if a.sv else json.loads(a.profile.read_text())
    print(json.dumps(personalise(profile, a.out, a.instance, a.macro), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
