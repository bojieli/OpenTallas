"""DIE-QC-63/KITS 11-02: AUTO-GEOM GRT probe excludes SDC clock-port nets (bus bits too) and has a wall limit."""
import re
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GC = (HERE / "geom_check.sh").read_text()
DECK = (HERE / "geom_grt.tcl").read_text()


def clock_ports(sdc_text):
    frag = GC[GC.index("CLKP=$("):GC.index('"$KIT/constraint.sdc")') + len('"$KIT/constraint.sdc")')]
    with tempfile.TemporaryDirectory() as d:
        Path(d, "constraint.sdc").write_text(sdc_text)
        out = subprocess.run(["bash", "-c", frag + '\necho "$CLKP"'], env={"KIT": d, "PATH": "/usr/bin:/bin"},
                             capture_output=True, text=True, check=True).stdout
    return out.split()


def test_sdc_clock_ports_parsed():
    sdc = ("create_clock -name clk -period 833.0000 [get_ports {clk clk_t1 clk_t2}]\n"
           "set_clock_uncertainty 25 [get_clocks clk]\n"
           "create_clock -name fclk_in_cmd_ei -period 833.0000 [get_ports fclk_in_cmd_ei]\n"
           "create_clock -name v -period 833\n")
    assert clock_ports(sdc) == ["clk", "clk_t1", "clk_t2", "fclk_in_cmd_ei"]
    assert clock_ports("") == []


def test_deck_marks_port_nets_and_bus_bits_special():
    assert "OT_GRT_CLOCK_PORTS" in DECK and "getBTerms" in DECK and "setSpecial" in DECK
    assert re.search(r"regsub \{\\\[\[0-9\]\+\\\]\$\}", DECK)          # NAME[i] bus bit -> NAME
    assert '"OT_GRT_CLOCK_PORTS=$CLKP"' in GC


def test_grt_wall_limit_default_on():
    assert "GWALL=$(J grt_wall_s 7200)" in GC
    assert 'stop -t 10 "ap-ageom-$ID-grt-$$"' in GC
    subprocess.run(["bash", "-n", str(HERE / "geom_check.sh")], check=True)
