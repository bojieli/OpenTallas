#!/usr/bin/env python3
"""ELEM-HBM/SM 10-24: flat hardened-view kits of the HNX-SM4P halves hnx_rp3lp3h_n / hnx_rp3lp3h_s on the B2r2 pins.

    python3 gen_sm_kit.py --half n|s --out KITROOT [--util U] [--tag T] [any gen_core_kit_hbm.py option]

= ../gen_core_kit_hbm.py (CP1-R10 gates: sdc_lint at generation + pre-synth, face_guard post-synth, SS/FF/TT corners with
the face-flop CK spread) with two substitutions:
  * recipe = the hnx-sm4p half-kit spec (physical/hbm_next/sm4/hnx_rp3lp3h_<h>_spec.json @ SRC): its source list,
    defines and top.  The spec is a 'cluster' kit whose hard children (xs3n, smh_bdc/tct/tcl, smh_tr_group_*) are NOT
    closed views under the 833 ps SS/FF policy (xs3n FAIL spread 154/134 ps; bdc/tct/tcl SS setup -47.5/-17.9/-29.7 ps;
    tr_group WARN), so the half is hardened FLAT from the same RTL (children synthesised in place).
  * every RTL file is read with `git show SRC:<path>` (never the checked-out tree), so the kit is exactly the
    hnx-sm4p RTL that the lockstep + MUT 1-4 bench proves equal to hnx_rp3lp3x_flat.
Pins: views_b2r2.json (B2r2 plan pin tables = the hnx-sm4p kit pins snapped +0.012 um to the plan M4/M5 tracks).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import gen_core_kit_hbm as G  # noqa: E402

SRC = "4d6f5439dcee43b97baffaa731aae826fdcb6a66"   # origin/claude/hnx-sm4p-1020 (HNX-SM4P half kits + bench)
VIEWS = {"n": "hnx_rp3lp3h_n@1938f3904f84", "s": "hnx_rp3lp3h_s@33365650555c"}


def git_show(path):
    r = subprocess.run(["git", "-C", str(G.REPO), "show", f"{SRC}:{path}"], capture_output=True)
    if r.returncode:
        raise SystemExit(f"{path} missing at {SRC}")
    return r.stdout


def fetch(f, commit, dst):
    data = git_show(f)
    if dst.exists() and dst.read_bytes() != data:
        raise SystemExit(f"rtl name clash {dst.name}")
    dst.write_bytes(data)


def main():
    argv = sys.argv[1:]
    h = argv[argv.index("--half") + 1]
    i = argv.index("--half")
    argv = argv[:i] + argv[i + 2:]
    extra = {}                                   # --set VAR=VALUE: ORFS variable override (variants), recorded in freeze
    while "--set" in argv:
        j = argv.index("--set")
        k, v = argv[j + 1].split("=", 1)
        extra[k] = v
        argv = argv[:j] + argv[j + 2:]
    mod = f"hnx_rp3lp3h_{h}"
    spec = json.loads(git_show(f"physical/hbm_next/sm4/{mod}_spec.json"))
    assert spec["top"] == mod and not spec["macros"], spec["top"]
    rec = dict(files=spec["sources"], top=mod, params={}, defines=spec["defines"], source_commit=SRC, macros=[],
               util=0.5, src_spec=f"physical/hbm_next/sm4/{mod}_spec.json@{SRC}")
    G.fetch = fetch
    G.load_recipes = lambda: {mod: rec}
    sys.argv = [sys.argv[0], "--views", str(HERE.parent / "views_b2r2.json"), "--view", VIEWS[h],
                "--recipe-key", mod] + argv
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        G.main()
    out = json.loads(buf.getvalue().strip().splitlines()[-1])
    kd = Path(out["kit"])
    if extra:
        cfg = (kd / "config.mk").read_text().splitlines()
        for k, v in extra.items():
            hit = [n for n, ln in enumerate(cfg) if ln.startswith(f"export {k} = ")]
            if hit:
                cfg[hit[0]] = f"export {k} = {v}"
            else:
                cfg.append(f"export {k} = {v}")
        (kd / "config.mk").write_text("\n".join(cfg) + "\n")
    fz = json.loads((kd / "freeze.json").read_text())
    fz.update(src_commit=SRC, src_spec=rec["src_spec"], orfs_overrides=extra, flow="flat (children synthesised in place)")
    fz["kit_hash"] = G.kit_hash(kd)
    (kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
    out["kit_hash"] = fz["kit_hash"]
    print(json.dumps(out))


if __name__ == "__main__":
    main()
