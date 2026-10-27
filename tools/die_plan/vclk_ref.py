"""vclk_ref: which IO virtual-clock reference the kit's FF sign-off will use -- ONE decision shared by signoff.py
(--ff-vclk auto) and the in-flow FF-only GRT hold repair (vclk_measured_hold.tcl), so the flow repairs FF hold in the
frame it is signed off in.

S81-ECO-2 10-27 (CHECKED qbank_S / sstn_base566 c18): the FF GRT hold repair bound the vclk to the fixed plan FF
insertion (OT_VCLK_FF 202.5 ps) while sign-off ('rebind', ruling 9.7 / 5e + COORD REBIND 10-27) timed FF hold against
the routed pin-register mean (189.74 / 190.97 ps).  12.8 / 11.5 ps more input-hold demand at sign-off than repaired ->
FF -6.19 / -6.32 ps (repair had left +5..+7 ps).  Async removal arcs WERE repaired (RSZ-0046 listed rn/RESETN; hold
buffers on rs): not a removal-coverage gap.

  bound-ff  the kit carries a typed hard-core latency contract (core.json clock_contract kind hard_core_latency):
            FF hold is timed against the declared FF insertion (no rebind inside a core, ROOT-MERGE2)
  rebind    die-plan kit with a per-corner insertion binding (sdc_lint.json insertion_ff_ps): every corner is timed
            against that corner's measured pin-register mean, band-checked vs the bound +- tol
  sdc       neither: the single SDC vclk

CLI (run inside the kit's docker, kit = /work):  python3 -I vclk_ref.py KITDIR  ->  "<ref> <ff_bound> <tol>" in SDC
time units (ff_bound / tol '-' when absent).  Fails closed (rc 2) when a declared boundary context points at a missing
core.json (the reference would otherwise silently fall back to 'rebind').
"""
import json
import sys
from pathlib import Path


class RefError(Exception):
    pass


def hard_core_latency_contract(kit):
    """the kit's typed hard-core clock contract (boundary_guard_context.json -> core.json clock_contract), or None.
    Only kind 'hard_core_latency' is recognised (COORD 10-24)."""
    if not kit:
        return None
    manifest = Path(kit) / "boundary_guard_context.json"
    if not manifest.is_file():
        return None
    ctx = json.loads(manifest.read_text())
    source = Path(ctx.get("source_core_json", ""))
    if not source.is_absolute():
        source = manifest.parent / source
    if not source.is_file():
        return None
    cc = json.loads(source.read_text()).get("clock_contract")
    if not isinstance(cc, dict) or cc.get("kind") != "hard_core_latency":
        return None
    return cc


def declared_ref(kit):
    """FLOW-MCMM-GRT 10-27: the kit runner's explicit sign-off FF frame, declared once in config.mk
    (`export OT_FF_VCLK_REF = bound-ff | rebind`, = the runner's signoff.py --ff-vclk flag), or None (derived)."""
    cfg = Path(kit) / "config.mk"
    if not cfg.is_file():
        return None
    val = None
    for line in cfg.read_text(errors="replace").splitlines():
        parts = line.split("#", 1)[0].split()
        if len(parts) >= 3 and parts[-3:-1] == ["OT_FF_VCLK_REF", "="] and parts[0] in ("export", "override"):
            val = parts[-1]
    if val is not None and val not in ("bound-ff", "rebind"):
        raise RefError(f"config.mk OT_FF_VCLK_REF {val!r} (bound-ff | rebind)")
    return val


def ff_reference(kit):
    """-> dict(ref, ff_bound, tol) with ff_bound / tol in SDC time units (None when absent)."""
    kd = Path(kit)
    manifest = kd / "boundary_guard_context.json"
    if manifest.is_file():
        src = json.loads(manifest.read_text()).get("source_core_json", "")
        p = Path(src)
        if not p.is_absolute():
            p = kd / p
        if not src or not p.is_file():
            raise RefError(f"boundary_guard_context.json names core json {src!r}, not found from {kd}")
    lint = kd / "sdc_lint.json"
    lctx = json.loads(lint.read_text()) if lint.is_file() else {}
    unit = float(lctx.get("time_unit_ps") or 1.0)
    ff = lctx.get("insertion_ff_ps")
    tol = lctx.get("insertion_tol_ps")
    ffu = None if ff is None else float(ff) / unit
    tolu = None if tol is None else float(tol) / unit
    declared = declared_ref(kd)
    if declared == "bound-ff" and ffu is None:
        raise RefError("config.mk OT_FF_VCLK_REF bound-ff without sdc_lint insertion_ff_ps")
    if declared == "bound-ff" or (declared is None and hard_core_latency_contract(kd)):
        return dict(ref="bound-ff", ff_bound=ffu, tol=tolu)
    if ff is not None:
        return dict(ref="rebind", ff_bound=ffu, tol=tolu if tolu is not None else 40.0 / unit)
    return dict(ref="sdc", ff_bound=None, tol=None)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: vclk_ref.py KITDIR", file=sys.stderr)
        return 2
    try:
        r = ff_reference(argv[0])
    except (RefError, ValueError, OSError) as e:
        print(f"VCLK_REF ERROR {e}", file=sys.stderr)
        return 2
    f = lambda v: "-" if v is None else f"{v:.6f}"
    print(f"{r['ref']} {f(r['ff_bound'])} {f(r['tol'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
