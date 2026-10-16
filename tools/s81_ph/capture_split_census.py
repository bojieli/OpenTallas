#!/usr/bin/env python3
"""Source-extracted blackbox census of the proposed capture parent wiring.

This checks the parent graph only, not child functionality or physical closure.
Actual child bodies are verified by the independent full-shape comparison.
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "rtl/dsrom_sys/s81_ph/ctrl_c/"
GROUPS = {
    "rtl/dsrom_sys/s81_ph/ot_s81ph_cap_tile.sv": ["dsfd_capt_ctl"],
    BASE + "dsfd_capt_split.sv": ["dsfd_capt_x8_data", "dsfd_capt_g2_dualho", "dsfd_capt_status_dual",
                               "dsfd_capt_rly_31_EW", "dsfd_capt_rly_36_WE", "dsfd_capt_rly_64_EW", "dsfd_capt_rly_12_SN"],
    BASE + "dsfd_capt_cd.sv": ["dsfd_capt_cd"],
    "rtl/dsrom_sys/s81_glue/dsfd_rly_masters.sv": ["dsfd_rly_68_EW", "dsfd_rly_2_WE", "dsfd_rly_63_WE", "dsfd_rly_2_EW"],
}
PARENT = BASE + "dsfd_sp_capture_split_candidate.sv"


def census():
    headers = []
    for path, names in GROUPS.items():
        text = (ROOT / path).read_text()
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        text = re.sub(r"//[^\n]*", "", text)
        for name in names:
            match = re.search(r"\bmodule\s+" + name + r"\b.*?;", text, re.S)
            if not match:
                raise ValueError("missing actual source header: " + name)
            headers.append(match[0] + "\nendmodule\n")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "headers.sv").write_text("`define CAPT_KB 99\n" + "\n".join(headers))
        (tmp / "net.ys").write_text(
            f"read_verilog -sv -lib {tmp}/headers.sv\nread_verilog -sv {ROOT/PARENT}\n"
            "hierarchy -check -top dsfd_sp_capture_split_candidate\nproc; flatten; opt_clean\n"
            f"write_json {tmp}/net.json\n")
        subprocess.run(["yosys", "-Q", "-q", str(tmp / "net.ys")], check=True, capture_output=True)
        module = json.loads((tmp / "net.json").read_text())["modules"]["dsfd_sp_capture_split_candidate"]
    types = Counter(c["type"] for c in module["cells"].values())
    sinks, outputs, ties = set(), {}, []
    for n, c in module["cells"].items():
        for p, bits in c["connections"].items():
            if c["port_directions"][p] == "input":
                for i, b in enumerate(bits):
                    if isinstance(b, str):
                        ties.append(f"{n}/{p}[{i}]={b}")
                    else:
                        sinks.add(b)
            else:
                outputs.update({f"{n}/{p}[{i}]": b for i, b in enumerate(bits)})
    for p, v in module["ports"].items():
        if v["direction"] == "output":
            sinks.update(v["bits"])
    unused = [pin for pin, bit in outputs.items() if bit not in sinks]
    logic = {m: n for m, n in types.items() if m.startswith("$")}
    if logic or ties or unused:
        raise ValueError(f"parent has logic={logic}, ties={ties[:5]}, unloaded outputs={unused[:5]}")
    return dict(schema="opentallas.s81.capture_split_census.v1", adopted=False, physical_qualified=False,
                counts=dict(children=sum(types.values()), masters=len(types), parent_logic_cells=0,
                            tied_child_input_bits=0, unloaded_child_output_bits=0,
                            clock_entry_bits=sum(len(v["bits"]) for p, v in module["ports"].items() if p.startswith("ck"))),
                cell_types=dict(types),
                source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [*GROUPS, PARENT]},
                consumer_proof=dict(retained_status="Original g_t[3].u_x0/t_st[63:0] = new u_status/t_st[63:0], consumed by t_vm[13375:13312] and u_cd/f_st[13:0]",
                                    removed_status="Other 15 x8 t_st[63:0] have no consumers in original source; 896 f_sn bits were constants, one duplicate input64 fed the unused g_t[3].u_x1 status cone",
                                    overflow="Every x8 t_ho remains connected; g2 captures OR(ho_half[1:0]) on the same original hoq edge",
                                    relay_padding="Only unused outputs removed: W_kb 4x23, E_kb 4x27, status4, done3. Actual99-bit constants,64-bit status,12-bit completion all preserved"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = census()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print("CAPTURE_SPLIT_CENSUS PASS", json.dumps(out["counts"]))
