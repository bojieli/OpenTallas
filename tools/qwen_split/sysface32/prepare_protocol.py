#!/usr/bin/env python3
"""Prepare production SYSFACE32 bare-core protocol and pin-copy equations.

The bare-core aliases are a functional test adapter, never physical copies.
The separate source equation receipt checks the ACTUAL captured wrapper FFs.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(repo, intermediate, original_wrapper, out, bounded=None, bounded_helpers=None):
    repo, intermediate, original_wrapper, out = map(Path, (repo, intermediate, original_wrapper, out))
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((intermediate / "INTERMEDIATE.json").read_text())
    wrapper = (intermediate / "qfd_sys_face_n32.sv").read_text()
    original = original_wrapper.read_text()
    assert digest(original_wrapper) == manifest["actual_pin_wrapper_sha256"]
    bench = (repo / "rtl/test/qwen_split/tb_qfd_sys_face.sv").read_text()
    instance = re.search(r"    qfd_sys_face #\(.*?\) u_dut \((.*?)\);", bench, re.S)
    assert instance, "Original bare protocol DUT instance changed"
    bindings = dict(re.findall(r"\.(\w+)\(([^()]*)\)", instance[1]))
    equations, aliases = [], []
    for i, row in enumerate(manifest["external_same_edge_boundary_copies"]):
        source = row["parent_raw_bit"]
        match = re.fullmatch(r"(\w+)(\[\d+\])?", source)
        assert match, source
        port, bit = match[1], match[2] or ""
        assert port in bindings, port
        alias = f"({bindings[port]})" + bit if bit else bindings[port]
        # SV indexing a parenthesized expression is not portable; these aliases
        # are named bench signal vectors in the actual pinned instance.
        if bit:
            assert re.fullmatch(r"\w+", bindings[port]), (port, bindings[port])
            alias = bindings[port] + bit
        aliases.append(f"    assign protocol_only_pin_aliases[{i}] = {alias};")
        actual = rf"always\s*@\(posedge\s+ck\)\s*pin_source_copies\[{i}\]\s*<=\s*{re.escape(source)}\s*;"
        assert len(re.findall(actual, wrapper)) == 1, (i, source)
        baseline = rf"always\s*@\(posedge\s+ck\)\s*{re.escape(port)}__ot_q\s*<=\s*{re.escape(port)}\s*;"
        assert len(re.findall(baseline, original)) == 1, port
        equations.append({"copy_bit": i, "record_copy_bit": row["record_copy"],
                          "raw_source_bit": source, "clock": "posedge ck",
                          "assignment": "nonblocking", "extra_edges": 0,
                          "equation": f"copy[{i}](t+1) = original_pin_q({source})(t+1) = raw({source})(t)",
                          "qualification": "Actual source capture equations; arbitrary initial copies may differ until first edge. Native physical clone retention remains separate."})
    width = len(equations)
    assert width == 35
    modified = instance[0].replace("qfd_sys_face #(", "qfd_sys_face_core_n32 #(", 1)
    if ".MU_HEAD(" not in modified:
        modified = modified.replace(".MU(MU)", ".MU(MU), .MU_HEAD(1)", 1)
    # The current production fixture declares MU_HEAD itself; preserve its
    # parameter connection and specialize the test profile rather than adding
    # a duplicate named parameter. Older fixtures have no such parameter.
    bench = re.sub(r"(parameter integer MU_HEAD\s*=\s*)0", r"\g<1>1", bench, count=1)
    modified = modified.replace("u_dut (", "u_dut (.pin_source_copies(protocol_only_pin_aliases), ", 1)
    bench = bench[:instance.start()] + f"    // FUNCTIONAL ADAPTER ONLY: these aliases are not physical producer copies.\n    wire [{width-1}:0] protocol_only_pin_aliases;\n" + "\n".join(aliases) + "\n" + modified + bench[instance.end():]
    bench = bench.replace("module tb_qfd_sys_face;", "module tb_qfd_sys_face;\n    initial if(MU!=1) $fatal(1,\"SYSFACE32 protocol proof requires production MU1\");", 1)
    # Actual captured pin wrappers are additional paired shadow DUTs. They see
    # identical raw inputs; neither uses the bare adapter's input aliases.
    decls = re.findall(r"^\s*(input|output)\s+(?:wire\s+|reg\s+)?(\[[^\]]+\])?\s*(\w+)\s*;", original, re.M)
    assert decls and set(name for _, _, name in decls) == set(bindings), "Captured wrapper / protocol port set mismatch"
    shadows, oldpins, newpins, comparisons = [], [], [], []
    output_bits = 0
    new_type = "qfd_sys_face_n32_bounded" if bounded else "qfd_sys_face_n32"
    new_boot = "u_shadow_new.n_4216" if bounded else "u_shadow_new.u_ot_pr_core.boot_done"
    new_ready = "u_shadow_new.n_4548" if bounded else "u_shadow_new.u_ot_pr_core.cal_ready"
    for direction, packed, name in decls:
        if direction == "input":
            oldpins.append(f".{name}({bindings[name]})")
            newpins.append(f".{name}({bindings[name]})")
        else:
            shadows.append(f"    wire {packed or ''} shadow_old_{name}, shadow_new_{name};")
            oldpins.append(f".{name}(shadow_old_{name})")
            newpins.append(f".{name}(shadow_new_{name})")
            comparisons.append(f'        if(shadow_old_{name} !== shadow_new_{name}) $fatal(1,"SYSFACE32_WRAPPER_MISMATCH port={name} cyc=%0d",cyc);')
            bounds = [int(x) for x in re.findall(r"\d+", packed)]
            output_bits += abs(bounds[0]-bounds[1])+1 if bounds else 1
    shadows += ["    qfd_sys_face_gold_wrap u_shadow_old(" + ",".join(oldpins) + ");",
                f"    {new_type} u_shadow_new(" + ",".join(newpins) + ");",
                "    integer wrapper_checks=0;",
                "    integer old_boot_cycle=-1,new_boot_cycle=-1,old_ready_cycle=-1,new_ready_cycle=-1;",
                "    always @(posedge ck) begin #0.02;",
                "      if(u_shadow_old.u_ot_pr_core.boot_done && old_boot_cycle<0) old_boot_cycle=cyc;",
                f"      if({new_boot} && new_boot_cycle<0) new_boot_cycle=cyc;",
                "      if(u_shadow_old.u_ot_pr_core.cal_ready && old_ready_cycle<0) old_ready_cycle=cyc;",
                f"      if({new_ready} && new_ready_cycle<0) new_ready_cycle=cyc;",
                "      if(MUT==0 && ep_cyc>=0) begin",
                f'        if(!u_shadow_old.u_ot_pr_core.boot_done || !{new_boot} || !u_shadow_old.u_ot_pr_core.cal_ready || !{new_ready}) $fatal(1,"SYSFACE32_WRAPPER_NOT_BOOTED_AT_EPOCH");',
                "        wrapper_checks=wrapper_checks+1;"] + comparisons + ["      end", "    end",
                '    final $display("SYSFACE32_WRAPPER_CHECKS %0d",wrapper_checks);',
                '    final $display("SYSFACE32_BOOT old=%0d new=%0d delta=%0d CAL_READY old=%0d new=%0d delta=%0d EPOCH=%0d",old_boot_cycle,new_boot_cycle,new_boot_cycle-old_boot_cycle,old_ready_cycle,new_ready_cycle,new_ready_cycle-old_ready_cycle,ep_cyc);']
    bench = bench.replace("endmodule", "\n".join(shadows)+"\nendmodule", 1)
    epoch_wait = "wait (u_dut.boot_done); repeat (4) @(negedge ck);"
    assert bench.count(epoch_wait) == 1
    bench = bench.replace(epoch_wait,
        f"wait (u_dut.boot_done && u_dut.cal_ready && u_shadow_old.u_ot_pr_core.boot_done && u_shadow_old.u_ot_pr_core.cal_ready && {new_boot} && {new_ready}); repeat (4) @(negedge ck);", 1)
    (out / "tb_qfd_sys_face_n32.sv").write_text(bench)
    oldcore = (repo / "rtl/qwen_split/qfd_sys_face.sv").read_text()
    oldcore = oldcore.replace("module qfd_sys_face #(", "module qfd_sys_face__ot_pr_core #(", 1)
    oldcore = re.sub(r"(parameter integer MU\s*=\s*)0", r"\g<1>1", oldcore, count=1)
    oldcore = re.sub(r"(parameter integer MU_HEAD\s*=\s*)0", r"\g<1>1", oldcore, count=1)
    (out / "protocol_gold_core.sv").write_text(oldcore)
    (out / "protocol_gold_wrapper.sv").write_text(original.replace("module qfd_sys_face (", "module qfd_sys_face_gold_wrap (", 1))
    bounded_receipt = None
    if bounded:
        assert bounded_helpers
        text = Path(bounded).read_text()
        assert "wire n_4216" in text or re.search(r"\bwire[^;]*\bn_4216\b", text)
        assert re.search(r"\bwire[^;]*\bn_4548\b", text)
        # Synthesis removes simulation initialization parameters from the ROM
        # instance. Restore ONLY its real functional model's content identity.
        pattern = r"ot_rom_4096x72_m8 (\\u_ot_pr_core\.u_rom\s+)\("
        assert len(re.findall(pattern, text)) == 1
        text = re.sub(pattern, r'ot_rom_4096x72_m8 #(.INSTANCE("sys_face_cfg")) \1(', text)
        (out / "protocol_bounded.sv").write_text(text)
        (out / "protocol_bounded_helpers.sv").write_text(Path(bounded_helpers).read_text())
        bounded_receipt = {"physical_source_sha256": digest(bounded),
                           "simulation_binding_sha256": digest(out / "protocol_bounded.sv"),
                           "helper_sha256": digest(bounded_helpers),
                           "change": "Only real ROM INSTANCE initialization parameter restored; +OT_ROM_DIR loads exact same compiled .viamap.hex. Same actual model, depth, data bits and read edge. No physical source edit.",
                           "boot_done_wire": "n_4216", "cal_ready_wire": "n_4548"}
    # Fixed wrappers only specialize the generic module parameter. They add no
    # registers and deliberately make no source-copy/fanout qualification.
    generic = (repo / "rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_sysface32.sv").read_text()
    port_start = generic.index(") (", generic.index("module ot_qwen_d2d_cal_sysface32")) + 3
    port_end = generic.index("\n);", port_start)
    ports = generic[port_start:port_end]
    names = re.findall(r"(?:input|output)\s+(?:wire|reg)\s*(?:\[[^\]]+\]\s*)?([^;\n]+)", ports)
    port_names = []
    for name in names:
        port_names.extend(x.strip() for x in name.rstrip(",").split(",") if x.strip())
    wrappers = []
    for ne in (16, 32, 64):
        aw = ne.bit_length()-1
        local = ports
        for key, value in (("AW", aw), ("NB", (ne+31)//32), ("G", ne//16)):
            local = re.sub(rf"\b{key}\b", str(value), local)
        wrappers.append(f"// Functional specialization only; independent source copies are the parent's responsibility.\nmodule qfd_syscal{ne}_n32 (" + local + ");\n" + f"ot_qwen_d2d_cal_sysface32 #(.NE({ne})) u_cal(" + ",".join(f".{name}({name})" for name in port_names) + ");\nendmodule\n")
    (out / "protocol_calendar_wrappers.sv").write_text("\n".join(wrappers))
    receipt = {"schema": "opentallas.sysface32.protocol_adapter.v1",
               "scope": "Production bare-core protocol plus actual wrapper source-capture equation provenance. No native clone retention or layout claim.",
               "extra_boot_reset_edges": manifest["added_boot_reset_edges"],
               "extra_production_edges": 0,
               "paired_actual_wrapper_output_bits": output_bits,
               "paired_actual_wrapper_output_ports": len(comparisons),
               "paired_wrapper_scope": "Actual captured original pin wrapper and actual successor wrapper with its 35 same-edge producer FFs. Identical raw protocol inputs; both boot_done required at epoch anchor, compare every output from the epoch anchor with no post-anchor mask. Bare core supplies healthy protocol checks separately.",
               "bounded_source": bounded_receipt,
               "epoch_anchor": "Wait bare core and BOTH actual wrappers boot_done AND cal_ready, then four quiet edges; epoch stimulus is relative to that anchor. Compare every output from the first epoch edge, with no post-anchor mask.",
               "actual_pin_wrapper_sha256": manifest["actual_pin_wrapper_sha256"],
               "successor_wrapper_sha256": digest(intermediate / "qfd_sys_face_n32.sv"),
               "successor_core_sha256": digest(intermediate / "qfd_sys_face_core_n32.sv"),
               "original_bench_sha256": digest(repo / "rtl/test/qwen_split/tb_qfd_sys_face.sv"),
               "prepared_bench_sha256": digest(out / "tb_qfd_sys_face_n32.sv"),
               "equations": equations, "PASS": True}
    (out / "PIN_COPY_EQUATIONS.json").write_text(json.dumps(receipt, indent=2)+"\n")
    return receipt


if __name__ == "__main__":
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--repo", required=True)
    p.add_argument("--intermediate", required=True)
    p.add_argument("--original-wrapper", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--bounded")
    p.add_argument("--bounded-helpers")
    a = p.parse_args()
    r = prepare(a.repo, a.intermediate, a.original_wrapper, a.out, a.bounded, a.bounded_helpers)
    print("SYSFACE32_PROTOCOL_PREP_PASS", len(r["equations"]), "actual same-edge source equations")
