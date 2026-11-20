#!/usr/bin/env python3
"""svc_h_gather_bench.py -- S81-SVC-H8W 11-20: every gather quarter of every service-slice port variant, at H.

    svc_h_gather_bench.py --h {8,16} --out DIR [--fv FILE] [--entry FILE] [--rsc FILE] [--pvso DIR] [--vectors N]

For each of the 15 port variants in the die's dsdv_svc_rs_fv.sv (13 dsdv_svc_rs_fv_<FM> + 2 dsdv_svc_rs_pvso_entry_fv_<FM>,
through the bind178 PORTFIX dsdv_svc_rs_pvso_entry for the entries) the bench drives N random words on EVERY gather
input face the variant carries (gi_d_<f>, GW = H*132+20 b) and a random 4-quarter word on the core's go_d, and checks
bit for bit, in iverilog:
  * the core dsdv_svc_rs_c sees gi_d[GW*q +: GW] == the word on face q for every face q in the variant, and 0 on the
    quarters the variant does not carry (FM off: no logic on them) -- "an H gather drives all quarters";
  * every go_d_<f> face port == the core's go_d[GW*q +: GW].
The core is a probe with dsdv_svc_rs_c's exact ANSI header (taken from --rsc under the same defines, H included): it
exposes gi_d and drives go_d from the bench.  A face whose port is narrower or wider than GW, or a wrapper that keeps the
H16 lane (the J3 r7 PORTFIX form: [2131:0] faces, 8,528-b core bus), fails here: the negative control (--fv / --entry of
the pre-fix files) must FAIL at H 8.  Exit 0 = PASS.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import svc_width_gate as SWG  # noqa: E402

FV = "physical/die_plan/s81/bind/source_modules/portfix178/dsdv_svc_rs_fv.sv"
ENTRY = "physical/die_plan/s81/bind/source_modules/portfix178/dsdv_svc_rs_pvso_entry.sv"
RSC = "rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs.sv"
PVSO = "rtl/dsrom_sys/s81_dv/pv_so"


def stub_rsc(rsc_text, defines):
    t = SWG.prep(rsc_text, defines)
    m = re.search(r"\bmodule\s+dsdv_svc_rs_c\b", t)
    par, pt, _ = SWG.header(t[m.end():])
    ports = SWG.ports(pt)
    pt = re.sub(r"\boutput\s+reg\b", "output wire", pt)
    L = [f"module dsdv_svc_rs_c #({par}) ({pt});"]
    for n, (d, _) in ports.items():
        if d == "output" and n not in ("go_d",):
            L.append(f"    assign {n} = '0;")
    L.append("    assign go_d = tb.go_pat[4*(H*132+20)-1:0];")
    L.append("endmodule")
    return "\n".join(L) + "\n"


def variants(fv_text, defines):
    t = SWG.prep(fv_text, defines)
    out = []
    for m in SWG.MOD.finditer(t):
        name = m.group(1)
        if not re.match(r"dsdv_svc_rs(_pvso_entry)?_fv_[0-9a-f]+$", name):
            continue
        par, pt, _ = SWG.header(m.group(2))
        ps = SWG.ports(pt)
        out.append(dict(name=name, entry="pvso_entry" in name, ports=ps, has_h=bool(re.search(r"\bH\s*=", par))))
    return out


def tb(vs, h, n):
    gw = h * 132 + 20
    L = ["`timescale 1ns/1ps", "module tb;", f"    localparam integer GW = {gw};",
         "    reg [4*GW-1:0] go_pat; integer errs = 0, checks = 0, v, k;"]
    for i, x in enumerate(vs):
        conns = []
        for p, (d, r) in x["ports"].items():
            w = SWG.width(r, {"H": str(h)}) if r else 1
            L.append(f"    {'reg' if d == 'input' else 'wire'} [{w - 1}:0] v{i}_{p};")
            conns.append(f".{p}(v{i}_{p})")
        L.append(f"    {x['name']} {'#(.H(' + str(h) + ')) ' if x['has_h'] else ''}d{i} ({', '.join(conns)});")
    L += ["    initial begin"]
    L.append(f"        for (v = 0; v < {n}; v = v + 1) begin")
    L.append("            for (k = 0; k < 4*GW; k = k + 32) go_pat[k +: 32] = $urandom;")
    for i, x in enumerate(vs):
        core = f"d{i}.u.u" if x["entry"] else f"d{i}.u"
        for p, (d, r) in x["ports"].items():
            if d == "input":
                w = SWG.width(r, {"H": str(h)}) if r else 1
                L.append(f"            for (k = 0; k < {w}; k = k + 32) v{i}_{p}[k +: 32] = $urandom;" if w > 1
                         else f"            v{i}_{p} = $urandom;")
        L.append("            #1;")
        for q, f in enumerate("nesw"):
            gi, go = f"gi_d_{f}", f"go_d_{f}"
            if gi in x["ports"]:
                L.append(f"            checks = checks + 1; if ({core}.gi_d[GW*{q} +: GW] !== v{i}_{gi}) begin errs = errs + 1; "
                         f"if (errs < 20) $display(\"FAIL {x['name']} gi quarter {q} ({f})\"); end")
            else:
                L.append(f"            checks = checks + 1; if ({core}.gi_d[GW*{q} +: GW] !== {{GW{{1'b0}}}}) begin errs = errs + 1; "
                         f"if (errs < 20) $display(\"FAIL {x['name']} gi quarter {q} ({f}) not zero\"); end")
            if go in x["ports"]:
                L.append(f"            checks = checks + 1; if (v{i}_{go} !== go_pat[GW*{q} +: GW]) begin errs = errs + 1; "
                         f"if (errs < 20) $display(\"FAIL {x['name']} go quarter {q} ({f})\"); end")
    L += ["        end",
          "        $display(\"GATHER_BENCH H=%0d GW=%0d variants=%0d checks=%0d errors=%0d %s\", "
          f"{h}, GW, {len(vs)}, checks, errs, errs ? \"FAIL\" : \"PASS\");",
          "        $finish;", "    end", "endmodule"]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--h", type=int, required=True, choices=(8, 16))
    ap.add_argument("--out", required=True)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--fv", default=FV)
    ap.add_argument("--entry", default=ENTRY)
    ap.add_argument("--rsc", default=RSC)
    ap.add_argument("--pvso", default=PVSO)
    ap.add_argument("--vectors", type=int, default=64)
    a = ap.parse_args(argv)
    root, out = Path(a.root), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    defines = ["OT_SVC_H8"] if a.h == 8 else []
    fv = (root / a.fv).read_text()
    vs = variants(fv, defines)
    if len(vs) != 15:
        raise SystemExit(f"expected 15 port variants, found {len(vs)}")
    (out / "stub_rsc.sv").write_text(stub_rsc((root / a.rsc).read_text(), defines))
    (out / "tb_gather.sv").write_text(tb(vs, a.h, a.vectors))
    # the bind178 PORTFIX dsdv_pv_so_program (TF parameter) is the one the PORTFIX entry selects, as in the as-built set
    pv = [str(root / ENTRY).replace("dsdv_svc_rs_pvso_entry.sv", "dsdv_pv_so_program.sv")] + \
        [str(root / a.pvso / f"dsdv_pv_{m}.sv") for m in ("so_program_h8", "half_join", "half_join_h8", "so_ingress",
                                                          "so_ingress_h8", "so_ingress_hden")]
    cmd = ["iverilog", "-g2012", "-o", str(out / "sim")] + [f"-D{d}" for d in defines] + \
          [str(out / "tb_gather.sv"), str(out / "stub_rsc.sv"), str(root / a.fv), str(root / a.entry)] + pv
    r = subprocess.run(cmd, capture_output=True, text=True)
    (out / "compile.log").write_text(r.stdout + r.stderr)
    if r.returncode:
        print("GATHER_BENCH COMPILE_FAIL\n" + (r.stdout + r.stderr)[-3000:])
        return 1
    s = subprocess.run(["vvp", "-n", str(out / "sim")], capture_output=True, text=True)
    (out / "sim.log").write_text(s.stdout + s.stderr)
    last = [ln for ln in s.stdout.splitlines() if ln.startswith("GATHER_BENCH")]
    print("\n".join(ln for ln in s.stdout.splitlines() if ln.startswith("FAIL"))[:2000])
    print(last[-1] if last else "GATHER_BENCH NO_RESULT")
    ok = bool(last) and last[-1].endswith("PASS")
    (out / "result.json").write_text(json.dumps(dict(h=a.h, fv=a.fv, entry=a.entry, verdict="PASS" if ok else "FAIL",
                                                     line=last[-1] if last else None), indent=1) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
