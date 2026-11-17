"""Install the opt-in, cycle-neutral S81 VPW bank-end physical form.

The RTL XR stage still comes from s81_vp_xr_overlay and a fresh die bind.
This hook places the write port and its XR flops at the SRAM banks and
groups them on one existing standard tap, as required by the strip PD review.
"""
from pathlib import Path
import shutil


def install(kit):
    kit = Path(kit)
    gp = kit / "face_flops.tcl"
    cts = kit / "clock_taps.tcl"
    if not gp.is_file() or not cts.is_file():
        raise ValueError("VPW bank form needs both placement and clock hooks")
    gp_text, cts_text = gp.read_text(), cts.read_text()
    if "s81_vpw_bank.tcl" in gp_text or "vpw_bank_clock.tcl" in cts_text:
        raise ValueError("VPW bank form already installed")
    source = Path(__file__).with_suffix(".tcl")
    if not source.is_file():
        raise ValueError("VPW bank placement source missing")
    shutil.copyfile(source, kit / source.name)
    gp.write_text(gp_text + "\nuplevel #0 {source /work/s81_vpw_bank.tcl}\n")
    cts.write_text('if {![file exists /work/vpw_bank_clock.tcl]} {error "OT_VPW_BANK missing placement clock record"}\n'
                   'source /work/vpw_bank_clock.tcl\n' + cts_text)

