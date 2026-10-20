"""Complete REGROOT8 operand clock-mass fences; no RTL or cycle changes."""
import json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[3]
HERE=pathlib.Path(__file__).resolve().parent

def make(kind,variant):
    old=f"qfd_tile_{kind}_romleaf_rc8{variant}"
    new=f"qfd_tile_{kind}_romleaf_rc9{variant}"
    src=ROOT/"physical/ref_tile"/old
    spec=json.loads((src/"spec.json").read_text().replace(old,new))
    spec["io_tcl"]=f"tools/qwen_romleaf/rc9/{new}_pins.tcl"
    spec["pin_hook_before_flops"]=[f"tools/qwen_romleaf/rc9/{new}_regions.tcl"]
    text=(ROOT/f"tools/qwen_romleaf/rc8/{old}_regions.tcl").read_text().replace(old,new)
    # Yosys aliases s2_w into rung0 di after REGROOT8 raw-capture. These remain on ck_dw/de,
    # whereas u_tx registers are on ck_tx. Claim the source registers before hub catch-all.
    sels={"dw":r"(16[0-9]|17[0-5]|19[2-9]|20[0-7]|22[4-9]|23[0-9]|25[6-9]|26[0-9]|27[01])",
          "de":r"(28[89]|29[0-9]|30[0-3]|32[0-9]|33[0-5]|35[2-9]|36[0-7]|38[4-9]|39[0-9])"}
    lines=text.splitlines()
    for i,line in enumerate(lines):
        for side,sel in sels.items():
            if f"name {side} type EXCLUSIVE" in line:
                marker=" regex {("
                assert marker in line
                branch=r"g_hd\.g_tx\.g_r\[0\]\.di\["+sel+r"\]|"
                lines[i]=line.replace(marker,marker+branch,1)
    text="\n".join(lines)+"\n"
    spec["structural_change"]="REGROOT8 complete operand clock mass fencing: raw-capture s2_w aliases g_r[0].di routed with mq_wrom and csel on ck_dw/de. Zero data/reset cycles, same outline/pins/macros/RTL."
    spec["job"].update(owner="Codex:QW-A0-RC4",branch="codex/qw-gates-collect-1020",tag="rc9"+variant,purpose=spec["structural_change"])
    out=ROOT/"tools/ref_tile/specs_qw_a0_rc9_1020";out.mkdir(exist_ok=True)
    (out/f"{new}.json").write_text(json.dumps(spec,indent=1)+"\n")
    (HERE/f"{new}_regions.tcl").write_text(text)
    (HERE/f"{new}_pins.tcl").write_text((ROOT/f"tools/qwen_romleaf/rc8/{old}_pins.tcl").read_text().replace(old,new))
    return new
if __name__=="__main__":
    for kind in ("nk","nl"):
        for variant in ("","b"):print(make(kind,variant))
