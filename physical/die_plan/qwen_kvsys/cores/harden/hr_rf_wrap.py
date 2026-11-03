#!/usr/bin/env python3
"""DIE-KV-64/RF-C 11-03 (RE-FORM batch RF-KV1): HR core face wrapper, applied by gen_core_kit_kv.py from the recipe
key rf_wrap = {"resets": [port, ...], "fwft_reads": [{"rd": P, "rdata": P, "rempty": P, "rst": P}, ...]}.

The kit top file (face-recut <mod>.v) is kept bit for bit except that its module is renamed <mod>__rf_core; a new
module <mod> with the identical port list wraps it:
  * reset relay (registered reset face): each listed active-low reset port drives exactly one relay flop
    (async assert, synchronous release one ck edge later); the relay Q is the core's reset.  Reset release +1 edge.
  * registered FWFT read face: rdata / rempty come straight from flops (rdata = a private port bank whose hold
    input is the internal hold bank, so the port flop Q loads only the port) (one-entry prefetch stage: the inner FIFO is
    popped when the stage is empty or the face pops it; FWFT semantics kept, throughput 1/cycle, +1 read latency).
All other ports pass through unchanged.
"""
import json
import re


def ports(text, mod):
    m = re.search(r"^module\s+" + re.escape(mod) + r"\s*\((.*?)\);", text, re.S | re.M)
    if not m:
        raise SystemExit(f"rf_wrap: module {mod} not found")
    order = [p.strip() for p in m.group(1).split(",")]
    body = text[m.end():text.index("endmodule", m.end())]
    decl = {}
    for d, rng, n in re.findall(r"^\s*(input|output)\s+(?:wire\s+|reg\s+)?(\[[^\]]+\])?\s*([A-Za-z_][\w$]*)\s*;", body, re.M):
        decl[n] = (d, rng or "")
    miss = [p for p in order if p not in decl]
    if miss:
        raise SystemExit(f"rf_wrap: no declaration for ports {miss[:5]}")
    return order, decl, m.start()


def width(rng):
    if not rng:
        return 1
    a, b = [int(x) for x in rng.strip("[]").split(":")]
    return abs(a - b) + 1


def transform(text, mod, spec):
    order, decl, at = ports(text, mod)
    clk = "ck" if "ck" in decl else None
    if not clk:
        raise SystemExit("rf_wrap: core clock port ck not found")
    ck = "ck[0]" if decl["ck"][1] else "ck"
    inner = mod + "__rf_core"
    head = text[:at]
    head = re.sub(r"\(\*\s*top\s*=\s*1\s*\*\)\s*\n", "", head)
    head = head.replace(f'hdlname = "{mod}"', f'hdlname = "{inner}"')
    body = re.sub(r"^module\s+" + re.escape(mod) + r"\b", "module " + inner, text[at:], count=1, flags=re.M)
    # a kept inner PORT wire survives flatten as its own net behind a buffer = an extra load on the face net
    # (face_guard 'shared'); the port flops keep their own (* keep *) on the reg cells
    body, nk = re.subn(r"^[ \t]*\(\*\s*keep\s*=\s*32'd1\s*\*\)[ \t]*\n(?=[ \t]*(?:input|output)\b)", "", body,
                       flags=re.M)
    new = head + body
    conn = {p: p for p in order}
    lines, rep = [], dict(resets=[], fwft_reads=[], added_flops=0)
    for r in spec.get("resets", []):
        if r not in decl or decl[r][0] != "input" or width(decl[r][1]) != 1:
            raise SystemExit(f"rf_wrap: reset {r} is not a 1-bit input")
        q = f"rf_rst_q__{r}"
        lines += [f"  (* keep = 1 *) reg {q};",
                  f"  always @(posedge {ck} or negedge {r}[0]) if (!{r}[0]) {q} <= 1'b0; else {q} <= 1'b1;"]
        conn[r] = "{" + q + "}"
        rep["resets"].append(dict(port=r, relay=q, release_added_edges=1)); rep["added_flops"] += 1
    for g in spec.get("fwft_reads", []):
        rd, rdat, remp, rst = g["rd"], g["rdata"], g["rempty"], g["rst"]
        for p, d in ((rd, "input"), (rdat, "output"), (remp, "output"), (rst, "input")):
            if decl.get(p, ("",))[0] != d:
                raise SystemExit(f"rf_wrap: {p} is not an {d}")
        w = width(decl[rdat][1]); rr = conn[rst]
        rr1 = rr.strip("{}") if rr != rst else f"{rst}[0]"
        b = rdat
        lines += [f"  wire [{w-1}:0] rf_i_{b};", f"  wire rf_ie_{b};", f"  wire rf_ird_{b};",
                  f"  reg rf_ov_{b};", f"  (* keep = 1 *) reg [{w-1}:0] rf_od_{b};", f"  (* keep = 1 *) reg [{w-1}:0] rf_oh_{b};",
                  f"  wire rf_ld_{b} = !rf_ie_{b} && (!rf_ov_{b} || {rd}[0]);",
                  f"  assign rf_ird_{b} = rf_ld_{b};",
                  f"  always @(posedge {ck} or negedge {rr1}) if (!{rr1}) rf_ov_{b} <= 1'b0;",
                  f"    else if (rf_ld_{b}) rf_ov_{b} <= 1'b1; else if ({rd}[0]) rf_ov_{b} <= 1'b0;",
                  f"  always @(posedge {ck}) rf_oh_{b} <= rf_ld_{b} ? rf_i_{b} : rf_oh_{b};",
                  f"  always @(posedge {ck}) rf_od_{b} <= rf_ld_{b} ? rf_i_{b} : rf_oh_{b};   // private port bank",
                  # private rempty port flop (= !rf_ov), next state from rf_ov, so its Q loads only the port
                  f"  reg rf_pe_{b};",
                  f"  always @(posedge {ck} or negedge {rr1}) if (!{rr1}) rf_pe_{b} <= 1'b1;",
                  f"    else rf_pe_{b} <= rf_ld_{b} ? 1'b0 : ({rd}[0] ? 1'b1 : !rf_ov_{b});",
                  f"  assign {rdat} = rf_od_{b};", f"  assign {remp} = {{rf_pe_{b}}};"]
        conn[rd] = "{rf_ird_" + b + "}"; conn[rdat] = "rf_i_" + b; conn[remp] = "rf_ie_" + b
        rep["fwft_reads"].append(dict(rd=rd, rdata=rdat, rempty=remp, rst=rst, width=w, read_added_cycles=1,
                                      throughput="1/cycle", rd_face="combinational (stage load enable)"))
        rep["added_flops"] += 2 * w + 2
    hdr = [f"// GENERATED hr_rf_wrap.py (RF-KV1 RE-FORM, DIE-KV-64/RF-C 11-03): {mod} = {inner} + registered reset/read faces",
           "(* top = 1 *)", f"module {mod}({', '.join(order)});"]
    hdr += [f"  {decl[p][0]} {decl[p][1]+' ' if decl[p][1] else ''}{p};" for p in order]
    inst = [f"  {inner} u_rf_core (" + ",\n    ".join(f".{p}({conn[p]})" for p in order) + ");", "endmodule", ""]
    rep["inner_port_keeps_dropped"] = nk
    return new.rstrip() + "\n\n" + "\n".join(hdr + lines + inst), rep


def write_report(kd, rep, spec):
    (kd / "hr_rf_wrap.json").write_text(json.dumps(dict(schema="opentallas.kit_hr_rf_wrap.v1", spec=spec, **rep,
        note="RF-KV1 RE-FORM: reset release +1 edge per relayed reset; FWFT read data +1 cycle; other ports unchanged"),
        indent=1) + "\n")
