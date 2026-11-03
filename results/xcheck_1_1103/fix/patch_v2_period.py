"""XCHECK-1 one-off: carry the hbm_phy_gen.py 833-ps controller clock into the write-once v2 / v2_ew HBM PHY copies
(tools/mem_compiler/build_aligned_v2.py cannot rebuild on main: missing ot_rom_4096x266_m8_skew250 v1 sheet).
Only min_period (lib + json timing), controller_clock_mhz and the json views sha256 change; pins/LEF/bb untouched."""
import hashlib, json, re, sys
from pathlib import Path
R = Path(sys.argv[1])
DIRS = ["physical/asap7_memory_macros_v2/" + d for d in ("ot_hbm3e_phy", "ot_hbm3e_phy_v41x", "ot_hbm3e_phy_v41x_aw30",
        "ot_hbm3e_phy_v41x_aw30_e8p5", "ot_hbm3e_phy_v41x_aw30_e8p5_k")] + ["physical/asap7_memory_macros_v2_ew/ot_hbm3e_phy"]
for d in DIRS:
    D = R / d; n = D.name
    for lib in sorted(D.glob("*.lib")):
        s = lib.read_text(); t = re.sub(r"min_period : (900|1000)\.000", "min_period : 833.000", s)
        assert t != s, lib; lib.write_text(t)
    j = D / f"{n}.json"; sh = json.loads(j.read_text())
    for c in sh.get("timing", {}).values():
        if isinstance(c, dict) and c.get("min_period_ps") in (900.0, 1000.0): c["min_period_ps"] = 833.0
    cc = (sh.get("interface") or {}).get("controller_clock_mhz")
    if isinstance(cc, dict):
        cc["value"] = 1200.0; cc["note"] = "the die clock (1.2 GHz); min_period 833 ps (XCHECK-1 11-03)"
    v = sh.get("views")
    if isinstance(v, dict):
        for f in list(v):
            if (D / f).exists(): v[f] = hashlib.sha256((D / f).read_bytes()).hexdigest()
    j.write_text(json.dumps(sh, indent=2) + "\n")
    print(d, "ok")
