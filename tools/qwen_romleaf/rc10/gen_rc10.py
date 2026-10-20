"""A0 rc10 (QW-CB16A0-2 10-20): REGROOT 9 = LANDED inter-root crossings instead of CTS hold buffering.

rc9 CTS hold repair inserted 34,239 hold cells (NK rc9 4_1_cts.odb classified by endpoint / startpoint:
rung 0 u_tx 4,458 EP / s2_x 1,485 SP (hub ck + ck_dw/de -> ck_tx), mq_wrom 2,284 EP from the ROM group roots gs/gn
3,787 SP, leaf -> outland 1,339, x delay-line shift chain 968 EP / 1,599 SP, ports 3,205 (input hold, unchanged)).
REGROOT 9 replaces the three inter-root seams by 4-slot rings (ot_qw_lw on the source root, ot_qw_lr on the
destination root, K = 2) with set_multicycle_path -setup 2 / -hold 3 ring -> read, and the x delay by a ring.
Same outline / pins / macros / pin and reset landing as the parent kit; fences extended to the new cells (the per-leaf
weight rings u_qlw2w/e stay unfenced between the operand strip and the leaf: 4,096 slots per side would overfill dw/de).
Base kits: NK rc9 (rc8 floorplan) -> rc10, NK rc9b (rc8b: IREG boxed at the E tap pins) -> rc10b; NL rc8 / rc8b ->
rc10 / rc10b.
"""
import json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
SDC = "tools/qwen_romleaf/rc10/land_mcp.sdc"
W_BITS = r"([0-9]|[1-9][0-9]|[1-9][0-9][0-9]|10[01][0-9]|102[0-3])"      # s2_w west half = bits 0..1023

def add(line, branch):
    m = re.search(r" regex \{(.*)\} boxes ", line)
    assert m, line[:80]
    return line[:m.start(1)] + "(" + branch + "|" + m.group(1) + ")" + line[m.end(1):]

def make(kind, variant, base):
    old = f"qfd_tile_{kind}_romleaf_{base}{variant}"
    new = f"qfd_tile_{kind}_romleaf_rc10{variant}"
    src = ROOT / "physical/ref_tile" / old
    spec = json.loads((src / "spec.json").read_text().replace(old, new))
    spec["params"] = dict(spec.get("params", {}), REGROOT_MODE=9)
    if "rtl/physical/ot_qw_land4.sv" not in spec["sources"]:
        spec["sources"].insert(0, "rtl/physical/ot_qw_land4.sv")
    spec["sdc_extra"] = [SDC]
    spec["io_tcl"] = f"tools/qwen_romleaf/rc10/{new}_pins.tcl"
    spec["pin_hook_before_flops"] = [f"tools/qwen_romleaf/rc10/{new}_regions.tcl"]
    rdir = "rc9" if base == "rc9" else "rc8"
    text = (ROOT / f"tools/qwen_romleaf/{rdir}/{old}_regions.tcl").read_text().replace(old, new)
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.search(r"name tx([0-7]) type EXCLUSIVE", line)
        if m:
            g = m.group(1)
            lines[i] = add(line, rf"g_sl\[{g}\]\.g_hd\.(g_tx9\.(u_qlr2[cwe]\.|g_r\[1\]\.u_tx/)|g_out9\.u_qlw3\.)")
        for side, col in (("rsw", "sw"), ("rnw", "nw"), ("rse", "se"), ("rne", "ne")):
            if f"name {side} type EXCLUSIVE" in line:
                lines[i] = add(lines[i], rf"g_col_land\.u_qlw1{col}\.")
        if "name dw type EXCLUSIVE" in line:
            lines[i] = add(line, rf"g_col_land\.u_qlr1[sn]w\.|u_me\.s2_w\[{W_BITS}\]")
        if "name de type EXCLUSIVE" in line:
            lines[i] = add(line, r"g_col_land\.u_qlr1[sn]e\.|u_me\.s2_w\[")
    text = "\n".join(lines) + "\n"
    text = text.replace(f"# {new}:", f"# {new}: REGROOT 9 landed-crossing fences added by tools/qwen_romleaf/rc10/gen_rc10.py; base", 1)
    spec["structural_change"] = ("REGROOT 9: the three inter-root seams (ROM group roots -> ck_dw/de operand, rung 0 hub ck + ck_dw/de -> "
        "ck_tx[g], leaf result/fault return ck_tx[g] -> ck) are LANDED 4-slot rings (K=2, MCP setup 2 / hold 3) instead of "
        "~34k CTS hold buffers; x delay line -> ring (item 5). Priced: +2 memory cycles (RX; x/KV follow) and +4 leaf "
        "cycles (XTD): t_out +6 edges vs REGROOT 8. Same outline/pins/macros/reset landing.")
    job = spec["job"]
    job.update(owner="Claude:QW-CB16A0-2", branch="claude/qw-a0-rc10-1020", tag="rc10" + variant, purpose=spec["structural_change"])
    xp = job.setdefault("extra_paths", [])
    for p in ("rtl/physical/ot_qw_land4.sv", "rtl/test/tb_qwen_a0_rr9.sv", SDC):
        if p not in xp:
            xp.append(p)
    out = ROOT / "tools/ref_tile/specs_qw_a0_rc10_1020"; out.mkdir(exist_ok=True)
    (out / f"{new}.json").write_text(json.dumps(spec, indent=1) + "\n")
    (HERE / f"{new}_regions.tcl").write_text(text)
    (HERE / f"{new}_pins.tcl").write_text((ROOT / f"tools/qwen_romleaf/{rdir}/{old}_pins.tcl").read_text().replace(old, new))
    return new

if __name__ == "__main__":
    for kind, base in (("nk", "rc9"), ("nl", "rc8")):
        for variant in ("", "b"):
            print(make(kind, variant, base))
