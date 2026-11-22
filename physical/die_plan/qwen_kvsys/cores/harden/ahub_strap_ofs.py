#!/usr/bin/env python3
"""KV-AHUB-RH1 11-21 (COORD ruling on the D27d3 hub_C AP_OFS mismatch): qkd_ahub with the die table AP_OFS / FR_OFS as
strap input pins instead of elaborated constants, 0 added cycles.

The KV plan moves the hub_C u_ahub offsets (D27d3: AP_OFS 64'hffe3ffe2ffe1ffe1, FR_OFS -7) whenever the landed ap / hs /
fr relay depths change, and every move made the signed hc_qkd_ahub view stale (swap_ahub_boundary refused it).  The core
is therefore hardened ONCE with
    strap_ofs_ap[31:0]  AP_OFS_s = sext16(strap_ofs_ap[8 s +: 8])   (stack s = 0..3, two's complement)
    strap_ofs_fr[7:0]   FR_OFS   = sext(strap_ofs_fr)
tied at the hub_C parent (TIEHI/TIELO next to the pin, OWNER 10-25 option B ID-strap rules: quasi-static, no pin
register, set_false_path -from [get_ports {strap_*}] in the core SDC).  Same prior art as qkd_ahub_static_dw_bo
(KV-ATTN4 10-20) but WITHOUT its capture flops (KV-KITS-8 10-28 COORD: no strap-capture register without timed fan-in):
the strap drives the same calendar adders the constant fed, so every timed register, edge and cycle is unchanged.

Every substitution is listed below and the reverse substitution must restore the source module text byte-for-byte
(same collapse check as ahub_clock7.apply); the new modules are APPENDED (qkd_ahub_static_io_st,
qkd_ahub_static_dw_ck7_st), so the canonical / ck7 text stays byte-identical in the file.

usage:
  ahub_strap_ofs.py rtl WRAP_IN DW_IN OUT_DIR             transformed qkd_ahub.sv + qkd_ahub_static_dw.sv
  ahub_strap_ofs.py kit SRC_KIT DST_KIT [--face N --x0 UM] derive a strap kit from a qkd_ahub kit (rtl, pins, io.tcl,
                                                          SDC, sdc_lint.json, straps.json, core.json, freeze.json)
  ahub_strap_ofs.py encode AP_OFS FR_OFS                  -> strap_ofs_ap / strap_ofs_fr literals (fails if not 8-bit)
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

STRAPS = {"strap_ofs_ap": 32, "strap_ofs_fr": 8}

AP_EXPR = ("{{8{strap_ofs_ap[31]}}, strap_ofs_ap[31:24], {8{strap_ofs_ap[23]}}, strap_ofs_ap[23:16],\n"
           "                          {8{strap_ofs_ap[15]}}, strap_ofs_ap[15:8],  {8{strap_ofs_ap[7]}},  strap_ofs_ap[7:0]}")

IO_SUBS = [
    ("module qkd_ahub_static_io #(\n    parameter [63:0] AP_OFS = {4{16'd2}},\n    parameter integer FR_OFS = 0,\n",
     "module qkd_ahub_static_io_st #(\n"),
    ("    input  wire [15:0]   hs_cal_r,            // cal[175:160]: R\n",
     "    input  wire [15:0]   hs_cal_r,            // cal[175:160]: R\n"
     "    // KV-AHUB-RH1 11-21: die offsets as ID-strap pins (tied at the hub_C parent, quasi-static, no pin register)\n"
     "    input  wire [31:0]   strap_ofs_ap,        // AP_OFS_s = sext16(strap_ofs_ap[8 s +: 8])\n"
     "    input  wire [7:0]    strap_ofs_fr,        // FR_OFS = sext(strap_ofs_fr)\n"),
    ("    reg  [111:0] cal_q;  reg [15:0] cal_r_q;\n",
     "    wire [63:0] AP_OFS = " + AP_EXPR + ";\n"
     "    wire signed [18:0] FR_OFS = {{11{strap_ofs_fr[7]}}, strap_ofs_fr};\n"
     "    reg  [111:0] cal_q;  reg [15:0] cal_r_q;\n"),
]

DW_SUBS = [
    ("module qkd_ahub_static_dw_ck7 #(\n    parameter [63:0] AP_OFS = {4{16'd2}},\n    parameter integer FR_OFS = 0,\n",
     "module qkd_ahub_static_dw_ck7_st #(\n"),
    ("    input  wire [15:0]   hs_cal_r,\n",
     "    input  wire [15:0]   hs_cal_r,\n"
     "    input  wire [31:0]   strap_ofs_ap,        // KV-AHUB-RH1: AP_OFS_s = sext16(strap_ofs_ap[8 s +: 8]) (ID strap)\n"
     "    input  wire [7:0]    strap_ofs_fr,        // KV-AHUB-RH1: FR_OFS = sext(strap_ofs_fr) (ID strap)\n"),
    ("    qkd_ahub_static_io #(.AP_OFS(AP_OFS), .FR_OFS(FR_OFS), .WF_RLY(WF_RLY), .MUT(MUT)) u_io (\n",
     "    qkd_ahub_static_io_st #(.WF_RLY(WF_RLY), .MUT(MUT)) u_io (\n"
     "        .strap_ofs_ap(strap_ofs_ap), .strap_ofs_fr(strap_ofs_fr),\n"),
]

LEAF_RE = re.compile(r"qkd_ahub_static_dw_ck7 #\(\.AP_OFS\((64'h[0-9a-fA-F_]+)\), \.FR_OFS\((-?\d+)\), "
                     r"\.Z_IN_STRIDE\((\d+)\)\) u_leaf \(\n")


def module(src, name):
    m = re.findall(r"^module %s\b.*?^endmodule\b" % re.escape(name), src, re.M | re.S)
    if len(m) != 1:
        raise ValueError(f"exactly one module {name} required, found {len(m)}")
    return m[0]


def apply(orig, subs):
    out = orig
    for old, new in subs:
        if out.count(old) != 1:
            raise ValueError(f"substitution anchor not unique/absent: {old[:70]!r}")
        out = out.replace(old, new, 1)
    back = out
    for old, new in reversed(subs):
        if back.count(new) != 1:
            raise ValueError(f"reverse anchor not unique: {new[:70]!r}")
        back = back.replace(new, old, 1)
    if back != orig:
        raise ValueError("the strap transformation changed a non-offset token")
    return out


def encode(ap, fr):
    """AP_OFS (int or 64'h literal) / FR_OFS (int) -> (strap_ofs_ap int, strap_ofs_fr int); every 16-bit AP slice must be
    the sign extension of its low byte and FR_OFS must fit 8-bit two's complement (else the strap core cannot carry it)."""
    if isinstance(ap, str):
        m = re.fullmatch(r"64'h([0-9a-fA-F_]+)", ap.strip())
        if not m:
            raise ValueError(f"AP_OFS literal {ap!r}: expected 64'h<hex>")
        ap = int(m.group(1).replace("_", ""), 16)
    fr = int(fr)
    sap = 0
    for s in range(4):
        v = (ap >> (16 * s)) & 0xFFFF
        sv = v - 0x10000 if v & 0x8000 else v
        if not -128 <= sv <= 127:
            raise ValueError(f"AP_OFS stack {s} = {sv} does not fit the 8-bit strap")
        sap |= (sv & 0xFF) << (8 * s)
    if not -128 <= fr <= 127:
        raise ValueError(f"FR_OFS {fr} does not fit the 8-bit strap")
    return sap, fr & 0xFF


def decode(sap, sfr):
    ap = 0
    for s in range(4):
        b = (sap >> (8 * s)) & 0xFF
        ap |= ((b | 0xFF00) if b & 0x80 else b) << (16 * s)
    return ap, (sfr - 256 if sfr & 0x80 else sfr)


def rtl(wrap, dw):
    """-> (new wrapper text, new dw text, leaf params {AP_OFS, FR_OFS, Z_IN_STRIDE})"""
    io_st = apply(module(dw, "qkd_ahub_static_io"), IO_SUBS)
    dw_st = apply(module(dw, "qkd_ahub_static_dw_ck7"), DW_SUBS)
    m = list(LEAF_RE.finditer(wrap))
    if len(m) != 1:
        raise ValueError(f"wrapper: expected one parameterised qkd_ahub_static_dw_ck7 u_leaf, got {len(m)}")
    m = m[0]
    params = dict(AP_OFS=m.group(1), FR_OFS=int(m.group(2)), Z_IN_STRIDE=int(m.group(3)))
    encode(params["AP_OFS"], params["FR_OFS"])
    port = "    input wire [15:0] hs_cal_r,\n"
    if wrap.count(port) != 1 or "strap_ofs" in wrap:
        raise ValueError("wrapper: unexpected hs_cal_r port declaration or strap already present")
    w = wrap.replace(port, port + "    input wire [31:0] strap_ofs_ap,\n    input wire [7:0] strap_ofs_fr,\n", 1)
    w = w.replace(m.group(0), f"qkd_ahub_static_dw_ck7_st #(.Z_IN_STRIDE({params['Z_IN_STRIDE']})) u_leaf (\n"
                  "        .strap_ofs_ap(strap_ofs_ap[31:0]), .strap_ofs_fr(strap_ofs_fr[7:0]),\n", 1)
    w = w.replace("// (+ added / strap pins, see <module>_core.json).  Do not edit.\n",
                  "// (+ added / strap pins, see <module>_core.json).  Do not edit.\n"
                  "// KV-AHUB-RH1 11-21 (ahub_strap_ofs.py): AP_OFS / FR_OFS = ID-strap inputs strap_ofs_ap[31:0] / strap_ofs_fr[7:0]\n"
                  f"// (tied at the hub_C parent; this view was derived from the AP_OFS {params['AP_OFS']} / FR_OFS {params['FR_OFS']} build).\n", 1)
    d = (dw + "\n// KV-AHUB-RH1 11-21 (ahub_strap_ofs.py): AP_OFS / FR_OFS as ID-strap input pins, 0 added cycles, no capture register.\n"
         + io_st + "\n\n" + dw_st + "\n")
    return w, d, params


def strap_pins(face, x0, pitch, w, h):
    """40 strap pins on free M5 (N/S) tracks: x = x0 + pitch * i (x0 on the M5 0.024 + 0.048 k grid)."""
    if face not in ("N", "S"):
        raise ValueError("strap pins go on the N or S face (M5)")
    if abs(((x0 - 0.024) / 0.048) - round((x0 - 0.024) / 0.048)) > 1e-6 or abs(pitch / 0.048 - round(pitch / 0.048)) > 1e-6:
        raise ValueError("x0 / pitch off the M5 track grid")
    y = 0.0 if face == "S" else h
    out, i = [], 0
    for bus, n in STRAPS.items():
        for b in range(n):
            x = round(x0 + pitch * i, 4)
            if x > w - 1.0:
                raise ValueError("strap pins run off the face")
            out.append(dict(bus=bus, bit=b, layer="M5", x=x, y=y, face=face))
            i += 1
    return out


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def kit(src, dst, face="N", x0=420.024, pitch=1.248):
    src, dst = Path(src), Path(dst)
    if dst.exists():
        raise SystemExit(f"{dst} exists")
    skip = {"run", "lec", "signoff", "views", "physical_completion", "probe", "__pycache__", "work"}
    shutil.copytree(src, dst, ignore=lambda d, names: [n for n in names if (Path(d) == src and (n in skip or n.startswith("lec_")
                    or n.endswith(".log") or n.startswith("prd_") or n.startswith("PRD"))) or ".previous." in n])
    w, d, params = rtl((src / "rtl/qkd_ahub.sv").read_text(), (src / "rtl/qkd_ahub_static_dw.sv").read_text())
    (dst / "rtl/qkd_ahub.sv").write_text(w)
    (dst / "rtl/qkd_ahub_static_dw.sv").write_text(d)
    cj = json.loads((src / "core.json").read_text())
    W, H = 604.8, 440.64
    pins = json.loads((src / "pins.json").read_text())
    used = {(p["face"], p["layer"], round(p["x"] if p["face"] in "NS" else p["y"], 3)) for p in pins}
    new = strap_pins(face, x0, pitch, W, H)
    for p in new:
        for dx in (-0.048, 0.0, 0.048):
            if (p["face"], "M5", round(p["x"] + dx, 3)) in used:
                raise SystemExit(f"strap pin {p} collides with an existing pin track")
    (dst / "pins.json").write_text(json.dumps(pins + new))
    io = (src / "io.tcl").read_text().rstrip("\n") + "\n# KV-AHUB-RH1 11-21: 40 ID-strap pins (strap_ofs_ap[31:0], strap_ofs_fr[7:0]), tied at the hub_C parent\n"
    yc = 0.096 if face == "S" else H - 0.096
    io += "".join(f"place_pin -pin_name {{{p['bus']}[{p['bit']}]}} -layer M5 -location {{{p['x']:.4f} {yc:.4f}}} "
                  "-pin_size {0.0240 0.1920}\n" for p in new)
    io = io.replace("(631 pins, core frame um)", f"({len(pins) + len(new)} pins, core frame um)", 1)
    (dst / "io.tcl").write_text(io)
    sdc = (src / "constraint.sdc").read_text()
    if "set_false_path" in sdc:
        raise SystemExit("source SDC already has a false path")
    sdc = sdc.rstrip("\n") + ("\n# ID straps (OWNER 10-25 option B): tied at the parent, quasi-static (KV-AHUB-RH1 strap_ofs)\n"
                              "set_false_path -from [get_ports {strap_ofs_ap strap_ofs_fr}]\n")
    (dst / "constraint.sdc").write_text(sdc)
    sl = json.loads((src / "sdc_lint.json").read_text())
    sl["inputs"] = sl["inputs"] + list(STRAPS)
    for s in STRAPS:
        sl.setdefault("io_floor_ps", {})[s] = sl["io_floor_ps"]["hs_start"]
    sl["straps"] = list(STRAPS)
    (dst / "sdc_lint.json").write_text(json.dumps(sl, indent=1) + "\n")
    (dst / "straps.json").write_text(json.dumps(dict(
        schema="opentallas.straps.v1", straps=sorted(STRAPS), source="KV-AHUB-RH1 ahub_strap_ofs.py (COORD 11-21 hub_C AP_OFS ruling)",
        rule="OWNER 10-25 option B ID straps (METHODOLOGY R7) + OWNER 12.15a count straps (strap_ca_*)"), indent=1) + "\n")
    for s, n in STRAPS.items():
        cj["port_decl"][s] = ["input", n - 1, 0]
        cj["boundary_role"][s] = "strap"
        for b in range(n):
            cj["pin_class"][f"{s}[{b}]"] = "strap"
    cj["classes"]["strap"] = sum(STRAPS.values())
    cj["pin_bits"] = cj.get("pin_bits", 0) + sum(STRAPS.values())
    cj["report"]["straps"] = [dict(pin=s, port=s, width=n, kind="id_strap",
                                   was=f"qkd_ahub_static_dw parameter {'AP_OFS (4 x 16b -> 4 x 8b two-complement)' if s.endswith('ap') else 'FR_OFS'}")
                              for s, n in STRAPS.items()]
    cj["report"]["pins"] = len(pins) + len(new)
    cj["source_note"] = (cj.get("source_note", "") + " | KV-AHUB-RH1 11-21: AP_OFS/FR_OFS -> strap_ofs_ap[31:0]/strap_ofs_fr[7:0] ID-strap "
                         f"inputs (ahub_strap_ofs.py; built from the {params['AP_OFS']}/{params['FR_OFS']} source; any 8-bit table)")
    cj["strap_ofs"] = dict(straps=STRAPS, cycles_added=0, capture_registers=0, source_params=params,
                           rule="OWNER 10-25 option B (ID straps, tied at parent) + COORD 11-21 hub_C AP_OFS ruling")
    (dst / "core.json").write_text(json.dumps(cj, indent=1) + "\n")
    fz = json.loads((src / "freeze.json").read_text())
    fz["pins"] = len(pins) + len(new)
    fz["added_pins"] = len(new)
    fz["straps"] = sorted(STRAPS)
    fz["core_json_sha256"] = sha(dst / "core.json")
    (dst / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
    pa = json.loads((src / "pins_added.json").read_text())
    pa["straps"] = [dict(pin=p["bus"], bit=p["bit"], face=p["face"], x=p["x"], y=p["y"], layer="M5") for p in new]
    (dst / "pins_added.json").write_text(json.dumps(pa, indent=1) + "\n")
    rec = dict(src=str(src), dst=str(dst), params=params, pins_added=len(new), face=face, x0=x0, pitch=pitch,
               files={f: sha(dst / f) for f in ("rtl/qkd_ahub.sv", "rtl/qkd_ahub_static_dw.sv", "pins.json", "io.tcl",
                                               "constraint.sdc", "core.json", "straps.json", "sdc_lint.json")})
    (dst / "strap_ofs.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("rtl"); r.add_argument("wrap"); r.add_argument("dw"); r.add_argument("out")
    k = sp.add_parser("kit"); k.add_argument("src"); k.add_argument("dst")
    k.add_argument("--face", default="N"); k.add_argument("--x0", type=float, default=420.024)
    k.add_argument("--pitch", type=float, default=1.248)
    e = sp.add_parser("encode"); e.add_argument("ap"); e.add_argument("fr", type=int)
    a = ap.parse_args(argv)
    if a.cmd == "rtl":
        w, d, p = rtl(Path(a.wrap).read_text(), Path(a.dw).read_text())
        o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
        (o / "qkd_ahub.sv").write_text(w); (o / "qkd_ahub_static_dw.sv").write_text(d)
        print(json.dumps(p))
    elif a.cmd == "kit":
        kit(a.src, a.dst, a.face, a.x0, a.pitch)
    else:
        s, f = encode(a.ap, a.fr)
        print(f"strap_ofs_ap 32'h{s:08x} strap_ofs_fr 8'h{f:02x}")


if __name__ == "__main__":
    main()
