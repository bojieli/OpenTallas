#!/usr/bin/env python3
"""Expand the retired attention-half parents into real hard cells.

Elaboration uses the production half RTL and the closed Liberty interfaces. No
half timing model is invented. The small fpipe registers become padded existing
136-bit banks, with exactly one register edge per original stage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWS = {
    "ot_attn_bank_sn544": "physical/hbm_attn_tile_r/bank_v12/sn544_rec/view",
    "ot_attn_bank_sn136": "physical/hbm_attn_tile_r/bank_v12/sn136_rec/view",
    "ot_attn_bank_ew544": "physical/hbm_attn_tile_r/bank_v12/ew544_rec/view",
    "ot_attn_bank_ew136": "physical/hbm_attn_tile_r/bank/ot_attn_bank_ew136",
    "ot_attn_tile_m6h1q": "physical/hbm_attn_tile_r/quad_b_tc/04424cd9f_pka/view",
    "ot_attn_lo_root": "physical/ref_tile/hattn_lo_root/views/ot_attn_lo_root",
    "ot_attn_hi_merge": "physical/ref_tile/hattn_hi_merge/views/ot_attn_hi_merge",
    "ot_attn_ks_entry": "physical/ref_tile/hattn_ks_entry/views/ot_attn_ks_entry",
}
PARAMS = {
    "lo": dict(CG=1, ROWEW=1, NK=3, NC=1, NR=2, PMID=3, NFR=4,
               NLL=3, NXP=3, LDKR=16),
    "hi": dict(CG=1, ROWEW=1, PMID=2, NFC=2, NL=8, NLL=3, NI=6),
}


def module(text, name):
    match = re.search(r"\bmodule\s+" + re.escape(name) + r"\b.*?\bendmodule", text, re.S)
    if not match:
        raise ValueError(f"missing module {name}")
    return match.group()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(out):
    tile = (ROOT / "rtl/hdc/v41x/ot_hdc_v41x_attn_die_tile_b.sv").read_text()
    half = (ROOT / "rtl/hdc/v41x/ot_hdc_v41x_attn_die_half_b.sv").read_text()
    # Synthesis never parameterises the hardened quad.
    text = "`define OT_ATTN_QCG\n"
    text += module(tile, "ot_attn_bpipe") + "\n" + module(tile, "ot_attn_bpipe136") + "\n"
    text += """
module ot_attn_fpipe #(parameter W=1, parameter N=1)
 (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
  // Same bank semantics, one edge per stage. Spare bits are tied low.
  ot_attn_bpipe136 #(.W(W),.N(N)) u_hard (.clk(clk),.d(d),.q(q));
endmodule
"""
    text += module(half, "hfd_attn_half_lo") + "\n" + module(half, "hfd_attn_half_hi") + "\n"
    # Dead initial guards are not synthesis cells; params are pinned above.
    text = re.sub(r"initial if \([^;]*?\$fatal\([^;]*?;", "", text)
    (out / "native_source.sv").write_text(text)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--yosys", default="yosys")
    a = p.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    prepare(out)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    children = {}
    for name, directory in VIEWS.items():
        view = ROOT / directory
        lef = view / f"{name}.lef"
        lint = subprocess.run(["python3", str(ROOT / "tools/hier_contract/child_lint.py"),
                               str(lef), "--libs", str(view), "--json"],
                              capture_output=True, text=True, check=True)
        report = json.loads(lint.stdout)
        (out / f"{name}_child_lint.json").write_text(json.dumps(report, indent=1) + "\n")
        children[name] = dict(logical_module=name, view_lef=str(lef.relative_to(ROOT)),
                             view_lib={c: str((view / f"{name}_{c}.lib").relative_to(ROOT))
                                       for c in ["tt", "ff", "ss"]},
                             w_um=report["info"]["W"], h_um=report["info"]["H"],
                             pg_top=report["info"]["pg_layer"], closure_status="closed_leaf",
                             source_commit=source,
                             sha256={f.name: digest(f) for f in view.iterdir()
                                     if f.suffix in [".lef", ".lib"]})
    for half, params in PARAMS.items():
        top = f"hfd_attn_half_{half}"
        script = "\n".join(f'read_liberty -lib "{ROOT / d / (n + "_tt.lib")}"'
                           for n, d in VIEWS.items())
        script += f'\nread_verilog -sv "{out / "native_source.sv"}"\n'
        script += "chparam " + " ".join(f"-set {k} {v}" for k, v in params.items()) + f" {top}\n"
        script += f"hierarchy -check -top {top}\nproc\nflatten\nopt_clean\ncheck -assert\n"
        script += f'write_json "{out / (half + ".netlist.json")}"\n'
        script += f'write_verilog -noattr "{out / (half + ".v")}"\n'
        path = out / f"{half}.ys"
        path.write_text(script)
        with (out / f"{half}.elaboration.log").open("w") as log:
            subprocess.run([a.yosys, "-Q", "-s", str(path)], stdout=log, stderr=subprocess.STDOUT, check=True)
        netlist = json.loads((out / f"{half}.netlist.json").read_text())["modules"][top]
        cells = netlist["cells"]
        unknown = sorted({v["type"] for v in cells.values()} - set(VIEWS))
        if unknown:
            raise ValueError(f"soft cells remain: {unknown}")
        endpoints = {}
        for instance, cell in cells.items():
            for port, bits in cell["connections"].items():
                for i, bit in enumerate(bits):
                    endpoints.setdefault(str(bit), []).append(dict(instance=instance, port=port, lsb=i, width=1))
        boundary = []
        ports = {}
        for port, desc in netlist["ports"].items():
            ports[port] = dict(direction=desc["direction"], width=len(desc["bits"]),
                               role="clock" if port == "ck" else "data")
            for i, bit in enumerate(desc["bits"]):
                for ep in endpoints.get(str(bit), []):
                    boundary.append(dict(parent_port=port, parent_lsb=i, width=1,
                                         child_instance=ep["instance"], child_port=ep["port"], child_lsb=ep["lsb"]))
        component = dict(schema="opentallas.native_component.v1", component=f"attention_{half}",
                         logical_module=top, source_commit=source, params=params,
                         outline_um=[1778.52, 1263.6 if half == "lo" else 689.04],
                         boundary_ports=ports,
                         children=[dict(children[v["type"]], instance=k, xy_um=None, orientation="R0")
                                   for k, v in cells.items()],
                         connections=[dict(net=b, endpoints=e, kind="constant" if b in ["0", "1", "x"] else "signal")
                                      for b, e in endpoints.items()],
                         boundary_binding=boundary,
                         unresolved=["Physical placement and real pin-distance/cut verification pending.",
                                     "Die clock distribution must balance actual child ETM insertion.",
                                     "Padded fpipe bank replacement needs exact sequential equivalence gate."],
                         closed=False)
        (out / f"{half}.component.json").write_text(json.dumps(component, indent=1) + "\n")
        print(f"{half}: {len(cells)} real child instances; {len(boundary)} boundary bindings; no soft cells")


if __name__ == "__main__":
    main()
