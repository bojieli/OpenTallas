#!/usr/bin/env python3
"""hd_serdes form A (sd9A) receiver unit model: the two KP4 decoder seam banks and their RX latency.

Form A is the source already on main: ot_s81hd_serdes_link(_ls) sets DNGB 12, RMRPC 32, DKREG 1, DOREG 1, so the
decoder word delay grows by DDX = 2 (ot_s81_kp4_dec).  This helper is the one place that prices it:

  area     per receiver, from the sd9A post-CTS bank census (BANK_CENSUS lines, sd9a_guard1 kit):
             DK  k_* seam (g_kreg)      323 FF   94.230540 um2   (320 data + 3 reset-sync)
             DO  chn -> out (g_oreg)    557 FF  166.314060 um2   (554 data + 3 reset-sync; the 5 r_one bits of the
                                                                  559 declared are unused and synthesize away)
             total                      880 FF  260.544600 um2
           This replaces the earlier 554 FF / ~161.55 um2 estimate, which counted the DO data bits only.
  latency  each seam register is one edge of the RECOVERED receive clock pma_rck: TWO RX edges of 833 ps per link
           traversal, relative to DKREG 0 / DOREG 0.  The price is per traversal of a receiver, never multiplied by
           the receiver count.  The forwarded transmit clock (pma_tck on tap clk_t8) is a different clock and is not
           priced here.

Nothing here claims a physical result: the census is a post-CTS cell count, not a routed sign-off.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "opentallas.head_serdes_sd9a_model.v1"
CLOCK_PS = 833
RX_CLOCK = "pma_rck"
TX_CLOCK = "pma_tck"            # forwarded on tap clk_t8; separate from RX_CLOCK, not priced by this model
PARAMS = {"DNGB": 12, "RMRPC": 32, "DKREG": 1, "DOREG": 1}
LINK_SOURCES = ("rtl/dsrom_sys/s81_head/ot_s81hd_serdes_link.sv", "rtl/dsrom_sys/s81_head/ot_s81hd_serdes_link_ls.sv")
# bank: (flops, flop area um2).  Reset rows are the per-bank ot_s81_kp4_rst synchronizer flops.
BANKS = {
    "DK": {"instance": "u_dec.g_kreg", "data_ff": 320, "reset_ff": 3, "data_um2": 93.355740, "reset_um2": 0.874800,
           "declared_bits": 320},
    "DO": {"instance": "u_dec.g_oreg", "data_ff": 554, "reset_ff": 3, "data_um2": 165.439260, "reset_um2": 0.874800,
           "declared_bits": 559, "unused_bits": 5},
}
SUPERSEDED = {"ff": 554, "um2": 161.55, "why": "DO data bits only; no DK bank, no reset flops"}
CENSUS_NAMES = {"kreg_all": ("DK", "all"), "kreg_data": ("DK", "data"), "oreg_all": ("DO", "all"),
                "oreg_data": ("DO", "data")}
TOL_UM2 = 1e-6


def ddx(params=PARAMS):
    """Extra decoder word-delay cycles, as ot_s81_kp4_dec computes DDX."""
    return (1 if params["DKREG"] else 0) + (1 if params["DOREG"] else 0)


def bank(name):
    b = BANKS[name]
    return {"ff": b["data_ff"] + b["reset_ff"], "um2": round(b["data_um2"] + b["reset_um2"], 6)}


def receiver():
    """Added flops and flop area of ONE receiver."""
    rows = {n: bank(n) for n in BANKS}
    return {"ff": sum(r["ff"] for r in rows.values()), "um2": round(sum(r["um2"] for r in rows.values()), 6),
            "banks": rows}


def area(receivers):
    """Added flops and flop area of `receivers` receivers (area scales with the count; latency does not)."""
    if receivers < 0:
        raise ValueError("receivers must be >= 0")
    r = receiver()
    return {"receivers": receivers, "ff": r["ff"] * receivers, "um2": round(r["um2"] * receivers, 6)}


def rx_latency(traversals=1, params=PARAMS):
    """RX latency added against DKREG 0 / DOREG 0, per link traversal: DDX recovered-clock edges each."""
    if traversals < 0:
        raise ValueError("traversals must be >= 0")
    edges = ddx(params) * traversals
    return {"clock": RX_CLOCK, "edges_per_traversal": ddx(params), "traversals": traversals, "edges": edges,
            "ps": edges * CLOCK_PS, "clock_ps": CLOCK_PS}


def source_params(root=ROOT):
    """The DNGB / RMRPC / DKREG / DOREG values each link wrapper actually instantiates."""
    out = {}
    for rel in LINK_SOURCES:
        text = (Path(root) / rel).read_text()
        m = re.search(r"ot_pdie_serdes\s*#\(([^;]*?)\)\s*u_link", text, re.S)
        if not m:
            raise ValueError(f"{rel}: no ot_pdie_serdes u_link instance")
        got = {k: int(v) for k, v in re.findall(r"\.(\w+)\((\d+)\)", m.group(1))}
        out[rel] = {k: got.get(k, 0) for k in PARAMS}
    return out


def check_source(root=ROOT):
    """Errors if a link wrapper is not form A (the model would then price the wrong hardware)."""
    return [f"{rel}: {k} is {got[k]}, form A needs {v}"
            for rel, got in source_params(root).items() for k, v in PARAMS.items() if got[k] != v]


def parse_census(text):
    """BANK_CENSUS lines -> {name: {ff, um2}}; a name seen twice or a line without both fields is an error."""
    out = {}
    for line in text.splitlines():
        if not line.startswith("BANK_CENSUS "):
            continue
        name = line.split()[1]
        ff = re.search(r"\bsequential_ff=(\d+)", line)
        um2 = re.search(r"\bff_area_um2=([0-9.]+)", line)
        if not ff or not um2 or name in out:
            raise ValueError(f"bad or repeated BANK_CENSUS line: {line[:120]}")
        out[name] = {"ff": int(ff.group(1)), "um2": float(um2.group(1))}
    return out


def check_census(text):
    """Errors if a measured bank census disagrees with the model (all four rows are required)."""
    got = parse_census(text)
    bad = []
    for name, (b, kind) in CENSUS_NAMES.items():
        want = bank(b) if kind == "all" else {"ff": BANKS[b]["data_ff"], "um2": BANKS[b]["data_um2"]}
        if name not in got:
            bad.append(f"{name}: missing from the census")
        elif got[name]["ff"] != want["ff"] or abs(got[name]["um2"] - want["um2"]) > TOL_UM2:
            bad.append(f"{name}: census {got[name]['ff']} FF / {got[name]['um2']:.6f} um2, "
                       f"model {want['ff']} FF / {want['um2']:.6f} um2")
    return bad


def model(receivers=12, traversals=1):
    return {"schema": SCHEMA, "form": "sd9A", "params": dict(PARAMS, DDX=ddx()), "receiver": receiver(),
            "area": area(receivers), "rx_latency": rx_latency(traversals),
            "tx_clock": {"clock": TX_CLOCK, "tap": "clk_t8", "priced_here": False},
            "superseded_estimate": SUPERSEDED, "qualification": "POST_CTS_CENSUS_NOT_PHYSICAL_SIGNOFF"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--receivers", type=int, default=12)
    ap.add_argument("--traversals", type=int, default=1)
    ap.add_argument("--census", help="bank census log (BANK_CENSUS lines) to check against the model")
    ap.add_argument("--no-source-check", action="store_true", help="do not read the link wrappers")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    bad = [] if a.no_source_check else check_source()
    if a.census:
        bad += check_census(Path(a.census).read_text())
    m = model(a.receivers, a.traversals)
    m["errors"] = bad
    text = json.dumps(m, indent=1, sort_keys=True) + "\n"
    if a.out:
        Path(a.out).write_text(text)
    else:
        sys.stdout.write(text)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
