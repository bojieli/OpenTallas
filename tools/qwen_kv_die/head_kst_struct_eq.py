#!/usr/bin/env python3
"""KV-KT-E0 2026-11-18: KT_ST 0 is the source head, cell for cell and wire for wire.

    head_kst_struct_eq.py OUTDIR [yosys]

For each generated head ot_qkh_head_native_r4*_kst and its source head: yosys (leaves as black boxes: lane, K-tree,
front, stin, stk, score, nb, feed-through stages) hierarchy + proc + flatten + opt_clean, then the two netlists are compared
as connectivity: the same cells (name, type, parameters) and, for every cell input bit and every module output bit, the
same driver (cell output bit, module input bit or constant).  At KT_ST 0 the station leaves are wires, so nothing is left
of them.  Control: KT_ST 2 must differ (the stations are cells).  Light job (seconds); run on a build host.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S = "rtl/qwen_sys/split_20261014"
SRC = [f"{S}/ot_qkh_head_native_r4_s.sv", f"{S}/ot_qkh_head_native_r4_s_lk.sv", f"{S}/ot_qkh_head_native_r4_kst.sv", f"{S}/ot_qkh_head_kst.sv"]
LIB = [f"{S}/ot_qkh_head_native_r4.sv", f"{S}/ot_qkh_head_native_r3.sv", f"{S}/ot_qkh_head_native.sv", "rtl/hdc/nearhbm/ot_qkh_subtiles.sv",
       "rtl/hdc/nearhbm/ot_qkh_ktree_lk.sv", "rtl/hdc/nearhbm/ot_qwen_nearhbm_head_hs.sv", f"{S}/qkh_head_gather_stage.sv", f"{S}/qkh_head_stages.sv"]
PAIRS = [("ot_qkh_head_native_r4_s_lk", "ot_qkh_head_native_r4_s_lk_kst"), ("ot_qkh_head_native_r4_ft_s_lk", "ot_qkh_head_native_r4_ft_s_lk_kst"),
         ("ot_qkh_head_native_r4_s", "ot_qkh_head_native_r4_s_kst"), ("ot_qkh_head_native_r4_ft_s", "ot_qkh_head_native_r4_ft_s_kst")]


def netlist(yosys, top, out, kt=None):
    js = out / f"{top}{'' if kt is None else '_kt%d' % kt}.json"
    chp = "" if kt is None else f"chparam -set KT_ST {kt} {top}\n"
    ys = (f"read_verilog -sv {' '.join(SRC)}\nread_verilog -sv -lib {' '.join(LIB)}\n{chp}hierarchy -check -top {top}\n"
          f"proc\nflatten\nopt_clean -purge\nwrite_json {js}\n")
    r = subprocess.run([yosys, "-q", "-p", ys.replace("\n", "; ")], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"yosys {top}: {r.stdout[-400:]} {r.stderr[-400:]}")
    d = json.loads(js.read_text())["modules"]
    return next(v for k, v in d.items() if k.lstrip("\\").startswith(top))


def canon(m):
    """{sink: driver} over cell inputs and module outputs + {cell: (type, parameters)}"""
    drv = {}
    for pn, p in m["ports"].items():
        if p["direction"] == "input":
            for i, b in enumerate(p["bits"]):
                drv[b] = f"in:{pn}[{i}]"
    for cn, c in m["cells"].items():
        for pn, bits in c["connections"].items():
            if c["port_directions"][pn] == "output":
                for i, b in enumerate(bits):
                    drv[b] = f"cell:{cn}.{pn}[{i}]"
    d = lambda b: b if isinstance(b, str) else drv.get(b, f"undriven:{b}")
    sinks = {}
    for pn, p in m["ports"].items():
        if p["direction"] == "output":
            for i, b in enumerate(p["bits"]):
                sinks[f"out:{pn}[{i}]"] = d(b)
    for cn, c in m["cells"].items():
        for pn, bits in c["connections"].items():
            if c["port_directions"][pn] != "output":
                for i, b in enumerate(bits):
                    sinks[f"cell:{cn}.{pn}[{i}]"] = d(b)
    return sinks, {cn: (c["type"], json.dumps(c.get("parameters", {}), sort_keys=True)) for cn, c in m["cells"].items()}


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    yosys = sys.argv[2] if len(sys.argv) > 2 else "yosys"
    bad = 0
    lines = []
    for src, kst in PAIRS:
        a = canon(netlist(yosys, src, out))
        b = canon(netlist(yosys, kst, out, 0))
        c = canon(netlist(yosys, kst, out, 2))
        same = a == b
        differs = a != c and len(c[1]) == len(a[1]) + 32
        und = sum(1 for v in a[0].values() if v.startswith("undriven")) + sum(1 for v in b[0].values() if v.startswith("undriven"))
        ok = same and differs and und == 0
        bad += not ok
        lines.append(f"{'PASS' if ok else 'FAIL'} {kst} KT_ST 0 == {src}: {len(a[1])} cells, {len(a[0])} sink bits identical drivers "
                     f"({'equal' if same else 'DIFFERENT'}); KT_ST 2: {len(c[1])} cells ({'+32 station leaves' if differs else 'UNEXPECTED'}); undriven {und}")
    lines.append(("PASS" if not bad else "FAIL") + f" head_kst_struct_eq: {len(PAIRS) - bad}/{len(PAIRS)} heads")
    (out / "result.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
