"""Install the opt-in exact site and tap checks for existing DLY lockup latches."""
from pathlib import Path
import re
import shutil


def install(kd, row, type_name, spread, lockup):
    records = row["dly_latch_sites"]
    if not records or not (spread and lockup):
        raise ValueError(f"type {type_name}: dly_latch_sites needs a nonempty DLY spread and lockup")
    width, height = row["outline_um"]
    seen = set()
    lines = []
    for entry in records:
        fields = [entry[k] for k in ("latch", "master", "launch", "capture", "launch_tap", "capture_tap")]
        latch = fields[0]
        if not all(isinstance(v, str) and re.fullmatch(r"[^\s]+", v) for v in fields):
            raise ValueError(f"type {type_name}: invalid DLY latch branch identity {fields!r}")
        if not latch.startswith("u_bound.u_fl_") or latch in seen:
            raise ValueError(f"type {type_name}: invalid or duplicate DLY latch {latch!r}")
        x, y = entry["origin_um"]
        if not (0 <= x < width and 0 <= y < height
                and abs(x * 1000 - round(x * 1000)) < 1e-6 and abs(y * 1000 - round(y * 1000)) < 1e-6):
            raise ValueError(f"type {type_name}: DLY latch {latch!r} outside outline or off the database grid")
        seen.add(latch)
        lines.append("\t".join([*fields, f"{x:.3f}", f"{y:.3f}"]))

    phase = kd / "pre_cts.tcl"
    marker = "source /work/clock_taps.tcl\n"
    prior = phase.read_text()
    if prior.count(marker) != 1:
        raise ValueError(f"type {type_name}: missing unique clock tap phase hook for DLY latch sites")
    shutil.copyfile(Path(__file__).with_suffix(".tcl"), kd / "dly_latch_sites.tcl")
    (kd / "dly_latch_sites.tsv").write_text("\n".join(lines) + "\n")
    commands = "source /work/dly_latch_sites.tcl\not_dly_site::run {} /work/dly_latch_sites.tsv\n"
    phase.write_text(prior.replace(marker, marker + commands.format("phase"), 1))
    with (kd / "face_flops_release.tcl").open("a") as hook:
        hook.write(commands.format("place"))
