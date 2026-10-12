#!/usr/bin/env python3
"""HIER station hub extraction (el1011-hbm-no3, owner TWO-LEVEL HIERARCHY rule 10-11 ~21:00).

The station's own glue (phase FSM, S2, ACK / receipt / permission banks, release, fclk, status) becomes its own small hard
element ot_hbm_w2_stn_hub_no<NO>; the 5 hardened slice tiles and the hub are placed directly by the die.  The hub is the
SAME RTL as the bit-exact HIER station (station_rb_static.sv HIER=1, OT_STN_HARD): yosys elaborates the station with the
slices as their liberty cells, `expose -evert` turns every slice connection into a hub port and removes the slices, then
the pure feed-throughs that the die wires directly (station data pins <-> slice din/dout, clk_sm -> slice clk, slice PG)
are dropped.  Composition hub + 5 slices == station netlist-for-netlist, so the station gate (w2_station_rb_gate.py --hier)
is the element's bit-exact bench.  Seam ports are renamed sl<k>_<port> (k 0-3 = slice8, 4 = slice5).
Usage: python3 tools/hbm_w2_station_hub_extract.py --no 3   (runs yosys in the ORFS image; writes physical/.../hub/)
"""
import argparse, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STN = "physical/hbm_w2_rb_station_20261006"
VIEWS = {2: ("6fc328026p7_slice8_no2", "6fc328026p7_slice5_no2"), 3: ("6fc328026p7_slice8_no3", "6fc328026p7_slice5_no3")}
DROP_STATION = ["in_data", "in_owner", "in_frame", "out_data", "out_owner", "out_frame"]
DROP_SLICE = ["clk", "din", "dout", "VDD", "VSS"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no", type=int, choices=(2, 3), required=True)
    ap.add_argument("--image", default=os.environ.get("OPENTALLAS_ORFS_IMAGE", "openroad/orfs:asap7lock"))
    a = ap.parse_args()
    v8, v5 = VIEWS[a.no]
    out = ROOT / STN / "hub"
    out.mkdir(exist_ok=True)
    name = f"ot_hbm_w2_stn_hub_no{a.no}"
    inst = [f"held.hier_payload.sl[{k}].u_sl" for k in range(4)] + ["held.hier_payload.u_sl4"]
    drops = [f"w:{p}" for p in DROP_STATION] + [f"w:{i}.{p}".replace("[", "\\[").replace("]", "\\]") for i in inst for p in DROP_SLICE]
    ys = f"""read_verilog -sv -DOT_STN_HARD /src/{STN}/bank_veto_static.sv /src/rtl/common/ot_fwd_link_stage.sv /src/{STN}/station_rb_static.sv /src/{STN}/slice_static.sv
delete ot_hbm_w2_stn_slice8 ot_hbm_w2_stn_slice5
read_liberty -lib /src/{STN}/views_hier/{v8}/ot_hbm_w2_stn_slice8/ot_hbm_w2_stn_slice8_tt.lib
read_liberty -lib /src/{STN}/views_hier/{v5}/ot_hbm_w2_stn_slice5/ot_hbm_w2_stn_slice5_tt.lib
hierarchy -top ot_hbm_native_frame_station_rb -chparam ENABLE 1 -chparam NO {a.no} -chparam REL_REG 1 -chparam SAFE 1 -chparam GRANT_SEAT 1 -chparam HIER 1
proc; flatten; opt_clean
select -assert-count 5 t:ot_hbm_w2_stn_slice8 t:ot_hbm_w2_stn_slice5
expose -evert t:ot_hbm_w2_stn_slice8 t:ot_hbm_w2_stn_slice5
delete -port {' '.join(drops)}
opt_clean -purge
check -assert
rename ot_hbm_native_frame_station_rb {name}
tee -o /w/{name}.ports.txt select -list x:*
write_verilog -noattr /w/{name}.v
"""
    (out / f"{name}.ys").write_text(ys)
    subprocess.run(["docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}", "-v", f"{ROOT}:/src:ro", "-v", f"{out}:/w", "--entrypoint", "yosys", a.image,
                    "-q", "-s", f"/w/{name}.ys"], check=True)
    v = (out / f"{name}.v").read_text()
    for k, i in enumerate(inst):
        v = re.sub(re.escape("\\" + i + ".") + r"(\w+) ", lambda m: f"sl{k}_{m.group(1)} ", v)
    assert "u_sl" not in v.split(f"module {name}")[1].split(");")[0], "unrenamed slice seam port"
    (out / f"{name}.v").write_text(v)
    ports = re.findall(r"^  (input|output|inout)\s+(\[\d+:\d+\]\s+)?(\S+)\s*;", v.split(f"module {name}")[1].split("endmodule")[0], re.M)
    nb = sum(int(re.match(r"\[(\d+):(\d+)\]", w).group(1)) - int(re.match(r"\[(\d+):(\d+)\]", w).group(2)) + 1 if w else 1 for _, w, _ in ports)
    print(f"wrote {out / (name + '.v')}: {len(ports)} ports / {nb} bits: " + " ".join(sorted(p for _, _, p in ports)))


if __name__ == "__main__":
    main()
