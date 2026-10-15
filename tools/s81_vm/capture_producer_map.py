#!/usr/bin/env python3
"""Source-guarded bit join from real capture children to native VM CAP2 pins.

Positions are local actual LEF shapes, never inferred parent placements or route
proof. A changed RTL connection or a missing actual pin refuses the export.
"""
import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import die_port_bind as D

CAP = "rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_capture_c_cl.sv"
VM = "rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_cap.sv"
PROD = "physical/ref_tile/dsfd_capt_x8_dual/views/dsfd_capt_x8_dual/dsfd_capt_x8_dual.lef"
CONS = "physical/ref_tile/dsfd_vm_static_cap_leaf_1015_r7/views/dsfd_vm_static_cap_leaf/dsfd_vm_static_cap_leaf.lef"
CTL = "physical/ref_tile/dsfd_vm_static_cap_ctl_1015_r1/views/dsfd_vm_static_cap_ctl/dsfd_vm_static_cap_ctl.lef"


def lef_pins(path):
    text = path.read_text()
    out = {}
    for m in re.finditer(r"^  PIN (\S+)\n(.*?)^  END \1$", text, re.M | re.S):
        shapes = []
        layer = None
        for row in m[2].splitlines():
            lm = re.search(r"LAYER (\S+) ;", row)
            if lm:
                layer = lm[1]
            rm = re.search(r"RECT\s+([-.\d]+)\s+([-.\d]+)\s+([-.\d]+)\s+([-.\d]+)\s*;", row)
            if rm:
                vals = list(map(float, rm.groups()))
                shapes.append(dict(layer=layer, rect_um=vals))
        out[m[1]] = shapes
    return out


def generate(root):
    cap, vm = (root / CAP).read_text(), (root / VM).read_text()
    cm = next(m for m in D.parse_modules(D.preprocess(cap, {}), CAP) if m.name == "dsfd_sp_capture_c")
    mm = next(m for m in D.parse_modules(D.preprocess(vm, {}), VM) if m.name == "dsfd_vm_static_cap")
    env = cm.env()
    assert env["NT"] == 8 and cm.width("t_vm", env) == mm.width("f_capture", mm.env()) == 13376
    c = re.sub(r"\s+", "", cap)
    v = re.sub(r"\s+", "", vm)
    for expression in [".t_vm(t_vm[1664*g+:832])", ".t_vm(t_vm[1664*g+832+:832])",
                       "assign t_vm[13375:13312]=stw;", "stv[64*(NT/2-1)+:64]",
                       ".t_st(stv[64*g+:64])"]:
        assert re.sub(r"\s+", "", expression) in c, "capture connection changed: " + expression
    for expression in [".f_c(f_capture[832*g+:832])", ".st_live(f_capture[13312])",
                       ".st_drn(f_capture[13314])", ".st_flt(f_capture[13315])"]:
        assert expression in v, "VM connection changed: " + expression
    pp, cp, tp = [lef_pins(root / p) for p in (PROD, CONS, CTL)]
    rows = []
    status = {0: "st_live", 2: "st_drn", 3: "st_flt"}
    for bit in range(13376):
        if bit < 13312:
            lane, local = divmod(bit, 832)
            inst = f"capture.g_t[{lane//2}].u_x{lane%2}"
            port = f"t_vm[{local}]"
            target = f"vm.u_cap.lane[{lane}].u_l.f_c[{local}]"
            target_shapes = cp[f"f_c[{local}]"]
            target_clock = f"ck_cap_lane_s[{lane}]"
            source_clock = f"capture.ckv_x[{lane}]"
        else:
            local = bit - 13312
            inst, port = "capture.g_t[3].u_x0", f"t_st[{local}]"
            target = "vm.u_cap.u_ctl." + status[local] if local in status else None
            target_shapes = tp[status[local]] if local in status else []
            target_clock = "ck_cap_control_s" if local in status else None
            source_clock = "capture.ckv_x[6]"
        assert pp[port] and (target is None or target_shapes), (bit, port, target)
        rows.append(dict(bit=bit, source=inst+"."+port, target=target,
                         source_clock=source_clock, target_clock=target_clock,
                         producer_shapes_local_um=pp[port], consumer_shapes_local_um=target_shapes,
                         top_bus_join=f"capture.t_vm[{bit}] -> vm.f_capture[{bit}]",
                         unused_by_current_VM=(target is None)))
    paths = [CAP, VM, PROD, CONS, CTL]
    return dict(schema="opentallas.s81.capture-native-vm-bit-join.v1",
                config=dict(READ_PIPE=4, CAP_PIPE=2, WSCATTER_PIPE=1),
                status="SOURCE_AND_ACTUAL_LOCAL_PIN_JOIN_ONLY",
                source_sha256={p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},
                total_bits=len(rows), active_VM_inputs=sum(r["target"] is not None for r in rows),
                unused_status_bits=sum(r["unused_by_current_VM"] for r in rows),
                constraints=["Actual capture parent instance origins/orientations and all incident physical wires remain required.",
                             "No alias, source version, clock insertion, reach, timing or programme qualification inferred.",
                             "All13376 top bus bits have real capture child producers;61 status bits are explicitly unused by current VM RTL."], rows=rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    record = generate(args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(record, separators=(",", ":")) + "\n").encode()
    if args.out.suffix == ".gz":
        with gzip.GzipFile(filename=str(args.out), mode="wb", mtime=0) as f:
            f.write(data)
    else:
        args.out.write_bytes(data)
    print(json.dumps({k:record[k] for k in ("total_bits", "active_VM_inputs", "unused_status_bits", "status")}))


if __name__ == "__main__":
    main()
