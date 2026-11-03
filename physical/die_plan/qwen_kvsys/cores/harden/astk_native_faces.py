#!/usr/bin/env python3
"""DIE-KV-61 11-02: face recut of the NATIVE ASTK strap master (plan_c kv3_astk = the kv_core_rtl.py wrapper of the
bind7 leaf kv3_astk__leaf), the same delta the 0828 ASTK kit carried (core.json actual_bind7_native_recut c6b9852b,
command_cycles_added 0, external_fault_b_cycles_added 1; face_guard PASS 1688/1688):

  * ctl qkd_astk_ctl_s_g0 PORT_REGS(1): the core qo port is driven by the exclusive qo_face register bank (same edge
    and reset as qo, kept hierarchy); the internal {T, start} nets keep feeding the four zones -> no shared qo nets;
  * qkd_astk_fault_join PORT_REGS(1): the incoming fault b lands in a register (+1 external-fault edge, +2 FF);
  * the plan tc pins that kv_core_rtl.py recorded as stale_in (no kv41 leaf bit: unconnected input ports of the
    wrapper) are declared dead (kit dead_inputs.json + receipt); face_guard independently requires no load/no driver.

Command / token cycles: 0.  The --astk-face-ports form (astk_face_ports.py) applies only to the old kv3_astk_* corner
extractions (tc outputs, qkd_astk_ctl_s instance) and refuses this one.
"""
import hashlib
import json
import re
from pathlib import Path

LEAF = "kv3_astk__leaf"
QO = "u_strip_u_strip_u_ctl__qo"
QO_W = 572
FACE = "astk_qo_face"
STRAP = "strap_corner"
ZN_DECL = "    (* keep *) reg [3:0]   zc_q;\n"
ZN_CAP = "always @(posedge ck) begin zc_q <= zc; "
ZN_USE = "wire [1:0]  S = zc_q[1:0], L = zc_q[3:2];"
CTL_DECL = "    (* keep *) reg [1:0]   st_q;\n"
CTL_CAP = "        st_q <= st; aq_q[20:1]"
CTL_USE = "wire [13:0]  base_s = {5'd0, st_q, 7'd0};"


def _concat_bits(s):
    """'{nA, nB, ...}' (MSB first) -> [LSB ... MSB] net names"""
    items = [x.strip() for x in s.strip()[1:-1].split(",")]
    return items[::-1]


def leaf_transform(text):
    if FACE in text:
        raise ValueError("ASTK native faces already applied")
    if f"module {LEAF} (" not in text:
        raise ValueError(f"expected module {LEAF}")
    fj = re.findall(r"qkd_astk_fault_join (\w+) \(", text)
    if len(fj) != 1:
        raise ValueError(f"expected one plain qkd_astk_fault_join instance, found {fj}")
    text = text.replace(f"qkd_astk_fault_join {fj[0]} (", f"qkd_astk_fault_join #(.PORT_REGS(1)) {fj[0]} (", 1)
    ctl = re.findall(r"qkd_astk_ctl_s_g0 #\(([^()]*(?:\([^()]*\)[^()]*)*)\) (\w+) \(", text)
    if len(ctl) != 1 or "PORT_REGS" in ctl[0][0]:
        raise ValueError(f"expected one qkd_astk_ctl_s_g0 instance without PORT_REGS, found {len(ctl)}")
    params, inst = ctl[0]
    head = f"qkd_astk_ctl_s_g0 #({params}) {inst} ("
    i = text.index(head)
    line = text[i:text.index("\n", i)]
    m = re.search(r"\.qo\((\{[^}]*\})\)", line)
    if not m:
        raise ValueError("ctl instance has no .qo({...}) connection")
    qo_nets = _concat_bits(m.group(1))
    if len(qo_nets) != QO_W:
        raise ValueError(f"ctl .qo has {len(qo_nets)} bits, want {QO_W}")
    text = text.replace(head, f"qkd_astk_ctl_s_g0 #({params}, .PORT_REGS(1)) {inst} (.qo_face({FACE}), ", 1)
    for b in range(QO_W):
        pat = rf"assign {QO}\[{b}\] = (\w+);"
        hits = re.findall(pat, text)
        if len(hits) != 1 or hits[0] != qo_nets[b]:
            raise ValueError(f"{QO}[{b}]: expected one alias of ctl qo bit {qo_nets[b]}, found {hits}")
        text = re.sub(pat, f"assign {QO}[{b}] = {FACE}[{b}];", text, count=1)
    marker = "    wire n0;\n"
    if text.count(marker) != 1:
        raise ValueError("expected the generated leaf local declarations")
    text = text.replace(marker, f"    // DIE-KV-61 ASTK native faces: exclusive qo launch bank (ctl PORT_REGS).\n"
                                f"    wire [{QO_W - 1}:0] {FACE};\n" + marker, 1)
    return text


def _module_span(text, mod):
    hits = [m.start() for m in re.finditer(rf"\bmodule {mod}\s*[#(]", text)]
    if len(hits) != 1:
        raise ValueError(f"expected exactly one module {mod}, found {len(hits)}")
    return hits[0], text.index("endmodule", hits[0])


def _sub_once(text, mod, old, new):
    i, j = _module_span(text, mod)
    body = text[i:j]
    if body.count(old) != 1:
        raise ValueError(f"{mod}: expected one '{old.strip()}', found {body.count(old)}")
    return text[:i] + body.replace(old, new, 1) + text[j:]


def strap_direct(leaf_text, leaves_text, ctl_text):
    """-> (leaves_text, ctl_text, zones): the strap-only capture registers dropped (see the module doc).  Fail-closed:
    every qkd_astk_zn instance of the leaf has zc = {2 constants, strap_corner[1:0]} and the one ctl instance st =
    strap_corner[1:0]."""
    sb = rf"{STRAP}\[1\], {STRAP}\[0\]"
    zn = re.findall(r"\bqkd_astk_zn (\w+) \((.*)", leaf_text)
    if not zn:
        raise ValueError("strap direct: no qkd_astk_zn instance in the leaf")
    for inst, line in zn:
        if not re.search(rf"\.zc\(\{{1'b[01], 1'b[01], {sb}\}}\)", line):
            raise ValueError(f"strap direct: zone {inst} zc is not {{const, const, {STRAP}[1:0]}}")
    ctl = re.findall(r"\bqkd_astk_ctl_s_g0 #\(.*?\) (\w+) \((.*)", leaf_text)
    if len(ctl) != 1 or not re.search(rf"\.st\(\{{{sb}\}}\)", ctl[0][1]):
        raise ValueError(f"strap direct: expected one ctl instance with st = {STRAP}[1:0]")
    m = "qkd_astk_zn"
    leaves_text = _sub_once(leaves_text, m, ZN_DECL, "    (* keep *) reg [3:2]   zc_q;   // zc[1:0] = ID strap: read from the port\n")
    leaves_text = _sub_once(leaves_text, m, ZN_CAP, "always @(posedge ck) begin zc_q[3:2] <= zc[3:2]; ")
    leaves_text = _sub_once(leaves_text, m, ZN_USE, "wire [1:0]  S = zc[1:0], L = zc_q[3:2];")
    m = "qkd_astk_ctl_s_g0"
    ctl_text = _sub_once(ctl_text, m, CTL_DECL, "    // st = ID strap (quasi-static): read from the port, no capture register\n")
    ctl_text = _sub_once(ctl_text, m, CTL_CAP, "        aq_q[20:1]")
    ctl_text = _sub_once(ctl_text, m, CTL_USE, "wire [13:0]  base_s = {5'd0, st, 7'd0};")
    for t, mm, bad in ((leaves_text, "qkd_astk_zn", "zc_q[1"), (ctl_text, "qkd_astk_ctl_s_g0", "st_q")):
        i, j = _module_span(t, mm)
        if bad in t[i:j]:
            raise ValueError(f"strap direct: {mm} still reads {bad}")
    return leaves_text, ctl_text, [i for i, _ in zn]


def dead_bits(wrapper_text, cj):
    """stale_in pin bits of (non clock/reset) buses that are input ports of the wrapper and are referenced nowhere but
    their declaration"""
    bits = []
    for name, cls in sorted(cj.get("pin_class", {}).items()):
        m = re.fullmatch(r"(\w+)\[(\d+)\]", name)
        if cls != "stale_in" or not m:
            continue
        bus = m.group(1)
        if re.search(r"(^|_)(ck|clk|rst_n)$", bus):   # clock / reset controls keep their own face_guard handling
            continue
        decl = re.findall(rf"^\s*input wire \[(\d+):(\d+)\] {bus},?\s*$", wrapper_text, re.M)
        if len(decl) != 1 or not int(decl[0][1]) <= int(m.group(2)) <= int(decl[0][0]):
            continue
        if len(re.findall(rf"\b{bus}\b", wrapper_text)) != 1:
            continue
        bits.append(name)
    return bits


def apply_kit(kd, mod, cj, src_core_json=None):
    kd = Path(kd)
    if mod != "kv3_astk":
        raise SystemExit("--astk-native-faces only applies to the native strap master kv3_astk")
    leaves = [p for p in sorted((kd / "rtl").glob("*__leaf.sv")) if f"module {LEAF} (" in p.read_text()]
    if len(leaves) != 1:
        raise SystemExit(f"--astk-native-faces: expected one {LEAF} source in the kit rtl, found {len(leaves)}")
    leaf = leaves[0]
    before = hashlib.sha256(leaf.read_bytes()).hexdigest()
    leaf.write_text(leaf_transform(leaf.read_text()))
    lv, cf = kd / "rtl" / "qkd_astk_leaves.sv", kd / "rtl" / "qkd_astk_ctl_s_g0.sv"
    if not (lv.is_file() and cf.is_file()):
        raise SystemExit("--astk-native-faces: kit rtl lacks qkd_astk_leaves.sv / qkd_astk_ctl_s_g0.sv (strap direct)")
    sha_lv, sha_cf = (hashlib.sha256(p.read_bytes()).hexdigest() for p in (lv, cf))
    lvt, cft, zones = strap_direct(leaf.read_text(), lv.read_text(), cf.read_text())
    lv.write_text(lvt)
    cf.write_text(cft)
    wrapper = kd / "rtl" / f"{mod}.sv"
    wt = wrapper.read_text()
    bits = dead_bits(wt, cj)
    method = ("kv_core_rtl.py recorded these plan pins as stale_in (no kv41 leaf bit); each bus is an input port of the "
              "generated wrapper referenced only by its declaration (no cell connection, no alias). Mapped face_guard "
              "independently requires no load and no driver.")
    receipt = dict(verdict="PASS", module=mod, bits=bits, wrapper_sha256=hashlib.sha256(wt.encode()).hexdigest(),
                   core_json=str(src_core_json) if src_core_json else None, method=method)
    if bits:
        (kd / "astk_native_dead_inputs_proof.json").write_text(json.dumps(receipt, indent=1) + "\n")
        (kd / "dead_inputs.json").write_text(json.dumps(dict(schema="opentallas.kit_dead_inputs.v1", bits=bits,
            proof=dict(verdict="PASS", method=method, receipt="astk_native_dead_inputs_proof.json")), indent=1) + "\n")
    (kd / "astk_native_face_delta.json").write_text(json.dumps(dict(
        transform="physical/die_plan/qwen_kvsys/cores/harden/astk_native_faces.py", leaf=leaf.name,
        leaf_sha256_before=before, leaf_sha256_after=hashlib.sha256(leaf.read_bytes()).hexdigest(),
        qo_face_bits=QO_W, fault_b_landing="PORT_REGS(1): +1 external-fault edge, +2 FF", dead_inputs=len(bits),
        command_cycles=0, nominal_token_cycles=0, local_fault_cycles=0, external_fault_cycles=1,
        strap_direct=dict(strap=STRAP, zones=zones, ctl="st", dropped_flops=2 * len(zones) + 2,
                          rule="COORD 2026-10-28 06:26 (KV-KITS-7 strap-capture class): no strap-capture register without timed fan-in",
                          leaves_sha256_before=sha_lv, ctl_sha256_before=sha_cf,
                          leaves_sha256_after=hashlib.sha256(lv.read_bytes()).hexdigest(),
                          ctl_sha256_after=hashlib.sha256(cf.read_bytes()).hexdigest()),
        same_as="0828 kit core.json actual_bind7_native_recut c6b9852b (command_cycles_added 0, external_fault_b_cycles_added 1)"),
        indent=1) + "\n")
    return bits
