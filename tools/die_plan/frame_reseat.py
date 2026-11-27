"""Opt-in placement of the existing H9 r1 FRAME data-path repeaters."""
import hashlib
import json
from pathlib import Path
import re
import shutil


TYPES = frozenset({
    "col_h9_r1__t1__cl49d7a23e__pv2f96c04f",
    "col_h9_r1__t1__cl49d7a23e__pva2370bfd",
    "col_h9_r1__t1__clf32cde8d__pv48cfde67",
})
BITS = 1166
PRE = "PRE_RESIZE_TCL"
DETAIL = "PRE_DETAIL_PLACE_TCL"
NAME = r"[A-Za-z0-9_./$\[\]-]+"
PRODUCER = re.compile(r"u_bound\.u_u_lpl_(5|10|11|12|13)_w\.[A-Za-z0-9_./$\[\]-]+")
STATION = "u_bound.u_ist_frame_int_o0_"
BOUT = "u_bound.u_bout_frame_int_o0"


def station_digest(banks, cell_size):
    canonical = json.dumps([banks, cell_size], separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def scoped_rows(tn, t):
    spec = t["frame_data_reseat"]
    if tn not in TYPES or set(spec) != {"station_sha256", "version", "paths"} or spec["version"] != 1:
        raise ValueError(f"{tn}: unsupported FRAME data reseat scope or version")
    from kit_istations import exact_banks

    station, = (row for row in t["internal_stations"] if row["conn"] == "bus:frame_int_o0")
    if len(station["regs_um"]) != 3:
        raise ValueError(f"{tn}: FRAME data reseat requires three existing station ranks")
    exact = exact_banks(station, BITS + 1)
    if exact is None:
        raise ValueError(f"{tn}: FRAME data reseat requires exact station banks")
    banks, cell_size, face = exact
    if face or station_digest(banks, cell_size) != spec["station_sha256"]:
        raise ValueError(f"{tn}: FRAME station seats differ from the reviewed source")

    paths = {}
    for bit, hop, src, dst, parity in spec["paths"]:
        if type(bit) is not int or not 0 <= bit < BITS or type(hop) is not int or not 0 <= hop < 4:
            raise ValueError(f"{tn}: invalid FRAME bit/hop {bit}/{hop}")
        if type(parity) is not int or parity != 1 or any(not re.fullmatch(NAME, name) for name in (src, dst)):
            raise ValueError(f"{tn}: invalid FRAME endpoint or polarity at {bit}/{hop}")
        station_prefix = STATION + str(hop)
        prefix = station_prefix if hop < 3 else BOUT
        if not re.fullmatch(rf"{re.escape(prefix)}[./]q\[{bit}\]\$[A-Za-z0-9_$]+", dst):
            raise ValueError(f"{tn}: unexpected FRAME capture {dst}")
        if hop == 0 and not PRODUCER.fullmatch(src):
            raise ValueError(f"{tn}: unexpected FRAME producer {src}")
        if (bit, hop) in paths:
            raise ValueError(f"{tn}: duplicate FRAME bit/hop {bit}/{hop}")
        paths[bit, hop] = (src, dst, parity)
    if len(paths) != BITS * 4:
        raise ValueError(f"{tn}: incomplete FRAME path inventory")
    producers = {paths[bit, 0][0] for bit in range(BITS)}
    if len(producers) != BITS:
        raise ValueError(f"{tn}: FRAME data bits share a producer")
    for bit in range(BITS):
        for hop in range(1, 4):
            if paths[bit, hop][0] != paths[bit, hop - 1][1]:
                raise ValueError(f"{tn}: discontinuous FRAME station chain at {bit}/{hop}")
    return banks, cell_size, paths


def _chain(config, kd, var, name, body):
    pat = re.compile(rf"\s*(?:override\s+)?export\s+{var}\s*=(.*)")
    lines = [i for i, line in enumerate(config) if pat.fullmatch(line)]
    if len(lines) > 1:
        raise ValueError(f"duplicate {var} while chaining FRAME reseat")
    override = ""
    if lines:
        i, = lines
        if config[i].lstrip().startswith("override "):
            override = "override "
        old = re.fullmatch(r"\s*/work/([a-zA-Z0-9_]+\.tcl)\s*", pat.fullmatch(config[i])[1])
        if not old or old[1].startswith("frame_data_reseat_") or not (kd / old[1]).is_file():
            raise ValueError(f"cannot chain FRAME reseat to {config[i]}")
        prior = f"source /work/{old[1]}\n"
    else:
        i = len(config)
        prior = ""
    name = f"frame_data_reseat_{name}.tcl"
    config[i:i + 1] = [f"{override}export {var} = /work/{name}"]
    return name, body + prior


def install(kd, tn, t):
    if "frame_data_reseat" not in t:
        return
    banks, cell_size, paths = scoped_rows(tn, t)
    kd = Path(kd)
    config = kd / "config.mk"
    lines = config.read_text().splitlines()
    run = "source /work/frame_data_reseat.tcl\nsource /work/frame_data_reseat_data.tcl\n"
    before = _chain(lines, kd, PRE, "pre", run + "::ot_frame_reseat::run resize\n")
    detail = _chain(lines, kd, DETAIL, "detail", run + "::ot_frame_reseat::run detail\n")
    data = ["set ::ot_frame_reseat::paths {"]
    for (bit, hop), (src, dst, parity) in sorted(paths.items()):
        site = " ".join(f"{float(v):.9g}" for v in banks[hop][bit]) if hop < 3 else ""
        data.append(f"  {{{bit} {hop} {{{src}}} {{{dst}}} {parity} {{{site}}}}}")
    data.append("}")
    data.append("set ::ot_frame_reseat::reserved {")
    for bank in banks:
        for x, y in bank:
            data.append(f"  {{{x:.9g} {y:.9g} {x + cell_size[0]:.9g} {y + cell_size[1]:.9g}}}")
    clock = t.get("clock", {})
    for rect in [*(r["rect_um"] for r in clock.get("reserved_sites_um", [])), *clock.get("die_islands_um", [])]:
        if len(rect) != 4:
            raise ValueError(f"{tn}: malformed FRAME reservation")
        data.append("  {" + " ".join(f"{float(n):.9g}" for n in rect) + "}")
    data.append("}\n")
    shutil.copyfile(Path(__file__).with_name("frame_data_reseat.tcl"), kd / "frame_data_reseat.tcl")
    (kd / "frame_data_reseat_data.tcl").write_text("\n".join(data))
    for name, body in (before, detail):
        (kd / name).write_text(body)
    config.write_text("\n".join(lines) + "\n")
