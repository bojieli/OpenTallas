#!/usr/bin/env python3
"""qwen-vm-fallback 2026-10-14: the XHI measurement knob for the per-layer token vehicle (idempotent source patch).

  python3 tools/qwen_tp8/vm_xhi_knob.py <tree root>

Patches <root>/rtl/qwen_sys/baseline_ar_stream4/ot_qwen_rom_rt_die_w12_stream4_tagged_ar.sv (parameter XHI, default 0 =
unchanged: XHI 1 returns every ME x-read element as {x[31:16], 16'h0}, i.e. what the VM's half-plane transport XHP = 1
delivers) and <root>/tools/exactness/qwen_rom_fulltoken.py (env QROM_XHI=1 -> -GXHI=1).  A run of the vehicle with
QROM_XHI=1 that is exact against the golden proves at TOKEN level that no consumer of the VM x read needs the low 16
bits; equal stage cycles prove it costs 0 cycles.  QROM_XHI=2 is the negative control (bit 16 dropped too: must FAIL).  Used on the frozen vehicle source (68dd9fcf7) and on main."""
import sys
from pathlib import Path
root = Path(sys.argv[1])
die = root / "rtl/qwen_sys/baseline_ar_stream4/ot_qwen_rom_rt_die_w12_stream4_tagged_ar.sv"
s = die.read_text()
if "parameter integer XHI" not in s:
    a = "    parameter integer XVM = 0,\n"
    assert s.count(a) == 1
    s = s.replace(a, a + "    parameter integer XHI = 0,   // qwen-vm-fallback 1014: 1 = x reads return {x[31:16], 16'h0} (VM XHP 1)\n")
    b = "if (vx_re[vi]) begin a = vx_addr[vi*24 +: 24]; rq[vi*32 +: 32] = (a < VM_ELEMS) ? vm[a] : 32'd0; end"
    assert s.count(b) == 1
    s = s.replace(b, "if (vx_re[vi]) begin a = vx_addr[vi*24 +: 24]; rq[vi*32 +: 32] = ((a < VM_ELEMS) ? vm[a] : 32'd0) & ((XHI == 2) ? 32'hFFFE0000 : (XHI != 0) ? 32'hFFFF0000 : 32'hFFFFFFFF); end")
    die.write_text(s)
ft = root / "tools/exactness/qwen_rom_fulltoken.py"
t = ft.read_text()
if "QROM_XHI" not in t:
    a = 'if os.environ.get("QROM_BD"):\n'
    assert t.count(a) == 1
    t = t.replace(a, '# qwen-vm-fallback 1014: QROM_XHI=1 = the VM half-plane x transport (x reads keep bits 31:16 only), a measurement knob\n'
                     'if os.environ.get("QROM_XHI") in ("1", "2"):\n    DIE = DIE + ["-GXHI=" + os.environ["QROM_XHI"]]\n' + a)
    ft.write_text(t)
print("patched", die, ft)
