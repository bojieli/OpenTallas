#!/usr/bin/env python3
"""Native VM bank master kits (H-SM 2026-10-16 06:xx) for the v16 die ABI (main a9a005496 + 04fad9220).

The v16 die binds hfd_vms_bank_native_q0 (SW, RG5/WG2), _q1 (SE and NE, RG4/WG2) and _q2 (NW, RG5/WG3); the strap
masters (RG5/WG1, RG4/WG1, RG6/WG3) are no longer instantiated.  The native masters wrap the same body
(ot_vms_bank_static_strap) as the strap6 kits, so every strap4..strap6 structural fix carries over.

Pin grant (derived, proposal for H-DIE; 270 x 270 slot unchanged):
  * N, S, W faces: the v4 strap grant of the same quadrant (vm_strap_grants_2210.json), unchanged.
  * E face: the strap q2 E layout (M4 at 0.144-um bit pitch, already granted for q2/q3) minus the retired rq5/rr5 group.
    It carries rq1/rr1, wq1/wq_done1 (the new SM-writer group for q0/q1; write group 1 for q2), xq2/xq2_done and eg,
    identical for all three native masters.
Kit settings = the strap6 kits of the same quadrant (strap5 write-tree RTL, OT_IOF_FOLLOW_AND=1, abutted 3-SRAM stack,
spine clock, pin flops in RTL); q0 adds EG_WIDE=1 (strap6 q0 egress fix).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/ref_tile"))
import ref_tile as RT  # noqa: E402

SRC_GRANT = "results/arch/hbm_die_v15/vm_strap_grants_2210.json"
GRANT = "results/arch/hbm_die_v16/vm_native_bank_grants_0600.json"
SHAPES = {0: (5, 2, "SW"), 1: (4, 2, "SE"), 2: (5, 3, "NW")}   # native_q1 also serves NE (sid port)


def stem(name):
    return name.split("[")[0]


def native_ports(q):
    t = (ROOT / f"rtl/hbm_accel/generic/vm/static/physical/hfd_vms_bank_native_q{q}.sv").read_text().split(");")[0]
    return {m[4]: (int(m[3]) + 1 if m[3] else 1)
            for m in re.finditer(r"(input|output)\s+wire\s*(\[(\d+):0\])?\s*(\w+)", t)}


def make_grant():
    g = json.loads((ROOT / SRC_GRANT).read_text())
    by = {s["cell"]: s for s in g["slots"]}
    e_face = [json.loads(json.dumps(p)) for p in by["hfd_vms_bank_strap_q2"]["pins"]
              if p["face"] == "E" and stem(p["name"]) not in ("rq5", "rr5")]
    slots = []
    for q, (rg, wg, quad) in SHAPES.items():
        s = json.loads(json.dumps(by[f"hfd_vms_bank_strap_q{q}"]))
        s["pins"] = [p for p in s["pins"] if p["face"] != "E"] + json.loads(json.dumps(e_face))
        s["cell"] = f"hfd_vms_bank_native_q{q}"
        s["name"] = f"vmb_{quad}_native_master"
        s["source"] = f"rtl/hbm_accel/generic/vm/static/physical/hfd_vms_bank_native_q{q}.sv"
        ports = native_ports(q)
        have = {stem(p["name"]): len(p["bit_centres_um"]) for p in s["pins"]}
        assert have == ports, (q, sorted(set(have.items()) ^ set(ports.items())))
        for f in "NSEW":
            c = sorted(x for p in s["pins"] if p["face"] == f for x in p["bit_centres_um"])
            assert all(b - a >= 0.096 - 1e-9 for a, b in zip(c, c[1:])), (q, f)
            assert len(c) * 0.096 <= g["rules"]["face_cap"] * s["outline"]["w"] + 1e-9 or f != "E", (q, f, len(c))
        s["native_shape"] = {"RG": rg, "WG": wg, "quadrants": [quad] + (["NE"] if q == 1 else [])}
        slots.append(s)
    out = {k: g[k] for k in g if k != "slots"}
    out.update(version="native-0600", slots=slots, derived_from=[SRC_GRANT, "E face = strap q2 E minus rq5/rr5"],
               owner="Claude H-SM", proposal_for="H-DIE (v16 VM slice parents)", production_binding_adopted=False)
    (ROOT / GRANT).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / GRANT).write_text(json.dumps(out, indent=1) + "\n")
    return out


def make():
    grant = make_grant()
    for slot in grant["slots"]:
        q = int(slot["cell"][-1])
        rg, wg, quad = SHAPES[q]
        name = f"vm_native_q{q}_ref"
        kd = ROOT / "physical/ref_tile" / name
        hd_rel = f"physical/hbm_vm_native_1016/q{q}"
        hd = ROOT / hd_rel
        hd.mkdir(parents=True, exist_ok=True)
        s = json.loads((ROOT / f"physical/ref_tile/vm_strap_q{q}_ref/spec.json").read_text())
        s.pop("reroute_reason", None)
        s.update(name=name, top=slot["cell"],
                 sources=[slot["source"], "rtl/hbm_accel/generic/vm/static/ot_vms_bank_static_strap.sv",
                          "rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv",
                          "physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v"],
                 contract={"file": GRANT, "slot": slot["name"]}, pins={f: [] for f in "NSEW"}, pin_ranges={},
                 io_tcl=f"{hd_rel}/io.tcl")
        s["orfs_vars"] = {"POST_IO_PLACEMENT_TCL": f"{hd_rel}/post_iop.tcl", "OT_IOF_FOLLOW_AND": "1"}
        expected = []
        for p in slot["pins"]:
            st = stem(p["name"])
            s["pins"][p["face"]].append(st)
            s["pin_ranges"][st] = p["span_um"]
            m = re.search(r"\[(\d+):(\d+)\]", p["name"])
            n = int(m[1]) + 1 if m else 1
            for bit in range(n):
                expected.append((f"{st}[{bit}]" if m else st, p["face"], p["layer"], round(p["bit_centres_um"][bit], 9)))
        # io.tcl / post_iop.tcl: same exact-pin construction + readback audit as the strap kits
        old_io = (ROOT / f"physical/hbm_vm_strap_1015/q{q}/io.tcl").read_text().split("\n")
        head = [l for l in old_io[:3]]
        tail = old_io[old_io.index("}") + 1:]
        io = head + ["set vm_expected {", *[" {%s %s %s %.9f}" % row for row in expected], "}"] + tail
        (hd / "io.tcl").write_text("\n".join(io).rstrip("\n") + "\n")
        post = (ROOT / f"physical/hbm_vm_strap_1015/q{q}/post_iop.tcl").read_text()
        (hd / "post_iop.tcl").write_text(post.replace(f"physical/hbm_vm_strap_1015/q{q}/io.tcl", f"{hd_rel}/io.tcl"))
        tb = "rtl/hbm_accel/generic/vm/static"
        comp = (f"cd {tb} && iverilog -g2012 -s tb_hbm_vm_native_abi -Ptb_hbm_vm_native_abi.SID={q} "
                f"-Ptb_hbm_vm_native_abi.RG={rg} -Ptb_hbm_vm_native_abi.WG={wg} -Ptb_hbm_vm_native_abi.MUT=%d "
                "-o {RUN}/m%d.vvp ot_vms_ce_counter_pipe.sv ot_vms_bank_static_strap.sv ot_vms_bank_native_physical.sv "
                "physical/hfd_vms_bank_native_q0.sv physical/hfd_vms_bank_native_q1.sv physical/hfd_vms_bank_native_q2.sv "
                "../../../../../physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v "
                "native_abi_1016/tb_hbm_vm_native_abi.sv && vvp {RUN}/m%d.vvp")
        sc = (f"Native v16 ABI master for {'/'.join(slot['native_shape']['quadrants'])} (RG{rg}/WG{wg}; die netlist main "
              "04fad9220 binds hfd_vms_bank_native_q*, strap masters retired). Same body as strap6: strap5 write tree "
              "(payload zeroed at its own pin capture, lv_rep removed), SECDED flip on the D edge, OT_IOF_FOLLOW_AND=1 "
              "(pin -> AND2 -> DFF captures anchored; strap5 q2/q3 view capture 493.3 ps / 818 pins without it)"
              + (", EG_WIDE=1 (strap5 q0 TT -114.94: 21/22 violators packet/COLL leaf -> egress pin clones)" if q == 0 else "")
              + ". Pins: v4 strap grant N/S/W + E face = strap q2 E (0.144 um) minus rq5/rr5 "
              f"({GRANT}).")
        s["job"].update(tag="nat1", purpose=sc, structural_change=sc,
                        extra_paths=["rtl/hbm_accel/generic/vm/static", hd_rel, GRANT,
                                     "physical/common_flow/assigned_pin_exact.tcl"],
                        record_to=f"results/rtl/ref_tile/{name}", views_to=f"physical/ref_tile/{name}/views",
                        branch="claude/hbm-sm-attention-1015",
                        benches=[{"name": "native_abi_8_banks", "cmd": comp % (0, 0, 0), "expect": "pass",
                                  "threads": 1, "peak_ram_gb": 4, "min_count_regex": r"VM_NATIVE_ABI PASS RG=\d+ WG=\d+ banks=8 SRAMs=24 wide_writes=(\d+)"},
                                 {"name": "bank_identity_mutant", "cmd": comp % (3, 3, 3), "expect": "fail",
                                  "fail_regex": r"FATAL: .*bank fault", "threads": 1, "peak_ram_gb": 4}])
        s["structural_change"] = sc
        kd.mkdir(parents=True, exist_ok=True)
        (kd / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
        print(json.dumps(RT.gen(str(kd / "spec.json"))))


if __name__ == "__main__":
    make()
