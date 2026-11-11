#!/usr/bin/env python3
"""S81 J3 leaf follow (DIE-S81-85 11-10, KW43-111): the J3 leaf RTL in a kit follows the wave source, nothing else.

Class: dsdv_slice c1x_C t1/t3-t10, lepe_mu_C, lepe_nh_mus_C, lepw_mu_C, lepw_mus_C ... failed LEC KEEP FAIL (32 kept
bits u_xg.u_s.u_ctl.g_hq[*].h[5,15..17,21,31..33] + 806 differ) because bind.py kit-rtl closes leaf RTL in the frozen
as-built base (codex-wave-bind-1106/src_28fc7), whose ot_s81sl_xs4.sv (f90b02c9) still holds the stream-head payload
under the rh/rx reset-hold enables.  Those bits load constants (r1_blk0[3]=0, r1_blk*[15:13]=0, r1_blk1[3]=1) with no
reset, so Yosys folds the flops to TIELO/TIEHI while the gold keeps them X until the first enabled load; no reset window
proves the constant.  The fix is already in the wave source (S81-TYPES-7-LEC J3, xs4 355a0bfc + rstopt_xo e94e3162:
payload loads every edge), it just never reached the kit.

This step rewrites only the kit_rtl.f / kit_rtl_sim.f / kit_rtl.json["files"] entries of the J3 leaf files named in
FOLLOW whose path lies outside the wave source (cwd) and whose bytes differ from the wave source file at the same
repo-relative path, provided the wave file defines every module of the old one (else FAIL closed).  A kit whose closure
has none of these files, or already has the wave bytes, is left byte-identical (no files are rewritten).
Usage (cwd = wave source checkout): j3_leaf_follow.py KIT_RTL_OUT
"""
import hashlib
import json
import re
import sys
from pathlib import Path

FOLLOW = ("rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs4.sv", "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstopt_xo.sv")
MOD = re.compile(r"^\s*module\s+(?:automatic\s+|static\s+)?([A-Za-z_]\w*)", re.M)


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def mods(p):
    t = re.sub(r"/\*.*?\*/", "", Path(p).read_text(errors="replace"), flags=re.S)
    return set(MOD.findall(re.sub(r"//[^\n]*", "", t)))


def follow(path, src):
    """-> new path or None (keep).  Raises SystemExit on a J3 leaf that differs and cannot follow."""
    rp = Path(path).resolve()
    if rp == src or src in rp.parents:
        return None
    for rel in FOLLOW:
        if str(rp).endswith("/" + rel):
            now = src / rel
            if not now.is_file() or md5(rp) == md5(now):
                return None
            miss = mods(rp) - mods(now)
            if miss:
                sys.exit(f"S81_J3_LEAF_FOLLOW FAIL {rel}: wave file {now} lacks module(s) {sorted(miss)} of {rp}")
            return str(now)
    return None


def main():
    out = Path(sys.argv[1])
    src = Path.cwd().resolve()
    rows = {}
    for name in ("kit_rtl.f", "kit_rtl_sim.f"):
        f = out / name
        if not f.is_file():
            continue
        lines = f.read_text().splitlines(keepends=True)
        new = []
        for ln in lines:
            s = ln.strip()
            n = follow(s, src) if s and not s.startswith(("+", "-")) else None
            if n:
                rows[s] = n
                ln = ln.replace(s, n)
            new.append(ln)
        if new != lines:
            f.write_text("".join(new))
    if not rows:
        print("S81_J3_LEAF_FOLLOW none (kit unchanged)")
        return
    j = out / "kit_rtl.json"
    r = json.loads(j.read_text())
    r["files"] = [rows.get(x, x) for x in r.get("files", [])]
    r["s81_j3_leaf_follow"] = dict(
        rule="DIE-S81-85 11-10 KW43-111: J3 leaf RTL follows the wave source (frozen as-built base had pre-fix xs4/rstopt_xo)",
        src=str(src), followed=[dict(was=k, now=v, was_md5=md5(k), now_md5=md5(v)) for k, v in sorted(rows.items())])
    j.write_text(json.dumps(r, indent=1))
    print("S81_J3_LEAF_FOLLOW followed", len(rows), " ".join(f"{Path(k).name} {md5(k)[:8]}->{md5(v)[:8]}" for k, v in sorted(rows.items())))


if __name__ == "__main__":
    main()
