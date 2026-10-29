#!/usr/bin/env python3
"""DIE-HBM-20-EPA: build core-level PROBE kits (synth+floorplan+place only) for the hfd_ep_static tx/rx split from the
ep_my kit (HBM-CORES-KITS-18).  Diagnostic only: master-plan slice / island infra stubbed (clock nets are excluded by
the AUTO-GEOM GRT probe); pins on the M4/M5 track grid (0.024 + 0.048 n)."""
import os, re, shutil, sys, json
SRC = "/srv/opentallas-scratch2/claude/hbm-cores-kits-18/ep/ep_my"
ROOT = "/srv/opentallas-scratch2/claude/die-hbm-20/epA"
SR_W, SR_H = 171.288, 77.784

def g(v):  # snap to the M4/M5 track grid
    return round(0.024 + 0.048 * round((v - 0.024) / 0.048), 3)

def bits(name, w):
    return [name] if w == 1 else [f"{name}[{i}]" for i in range(w)]

def face_pins(face, names, W, H, start, pitch):
    out = []
    for k, n in enumerate(names):
        c = g(start + k * pitch)
        if face == "S": out.append((n, "M5", c, 0.096))
        elif face == "N": out.append((n, "M5", c, round(H - 0.096, 3)))
        elif face == "W": out.append((n, "M4", 0.096, c))
        elif face == "E": out.append((n, "M4", round(W - 0.096, 3), c))
    return out

def write_io(path, pins, clkxy):
    with open(path, "w") as f:
        f.write("# DIE-HBM-20-EPA probe pins\n")
        for n, l, x, y in pins:
            sz = "{0.0240 0.1920}" if l == "M5" else "{0.1920 0.0240}"
            f.write(f"place_pin -pin_name {{{n}}} -layer {l} -location {{{x:.4f} {y:.4f}}} -pin_size {sz}\n")
        f.write(f"place_pin -pin_name {{clk}} -layer M5 -location {{{g(clkxy[0]):.4f} {clkxy[1]:.4f}}} -pin_size {{0.048 0.48}}\n")

def mk(name, top, W, H, pins, clkxy, macros, ins, outs, density="0.5"):
    K = f"{ROOT}/{name}"
    if os.path.exists(K): shutil.rmtree(K)
    shutil.copytree(SRC, K, ignore=shutil.ignore_patterns("run", "lec", "__pycache__", "face_shell_work", "*.log", "placed.csv"))
    os.makedirs(f"{K}/rtl", exist_ok=True)
    for fn in os.listdir(f"{K}/rtl"): os.remove(f"{K}/rtl/{fn}")
    for fn in ["ot_hep_gbx.sv", "hfd_ep_static_split.sv", "ot_hep_rx_store.sv", "ot_hbm_face_reg.sv"]:
        shutil.copy(f"{ROOT}/eq/rtl/{fn}", f"{K}/rtl/{fn}")
    cfg = open(f"{K}/config.mk").read()
    cfg = re.sub(r"(?m)^export DESIGN_NICKNAME = .*$", f"export DESIGN_NICKNAME = hbc_{top}", cfg)
    cfg = re.sub(r"(?m)^export DESIGN_NAME = .*$", f"export DESIGN_NAME = {top}", cfg)
    cfg = re.sub(r"(?m)^export VERILOG_FILES = .*$", "export VERILOG_FILES = /work/rtl/ot_hep_gbx.sv /work/rtl/hfd_ep_static_split.sv /work/rtl/ot_hep_rx_store.sv /work/rtl/ot_hbm_face_reg.sv", cfg)
    cfg = re.sub(r"(?m)^export DIE_AREA = .*$", f"export DIE_AREA = 0 0 {W} {H}", cfg)
    cfg = re.sub(r"(?m)^export CORE_AREA = .*$", f"export CORE_AREA = 4.32 4.32 {round(W-4.32,3)} {round(H-4.32,3)}", cfg)
    cfg = re.sub(r"(?m)^export PLACE_DENSITY = .*$", f"export PLACE_DENSITY = {density}", cfg)
    cfg = re.sub(r"(?m)^override export OT_HOLD_MM = 1$", "override export OT_HOLD_MM = 0", cfg)
    cfg = "# DIE-HBM-20-EPA PROBE (from ep_my kit; synth+floorplan+place only)\n" + cfg
    open(f"{K}/config.mk", "w").write(cfg)
    write_io(f"{K}/io.tcl", pins, clkxy)
    with open(f"{K}/macro_placement.tcl", "w") as f:
        f.write("foreach {inst master x y orient} {\n")
        for inst, x, y, o in macros: f.write(f"  {{{inst}}} ot_sram_1r1w_64x512_m1_r2c2 {x} {y} {o}\n")
        f.write("} {\n  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact\n}\n")
    open(f"{K}/master_slice.tcl", "w").write('# DIE-HBM-20-EPA probe: master-plan slice / island infra stubbed\nputs "OT_MASTER_SLICE probe-stub"\n')
    sdc = open(f"{K}/constraint.sdc").read()
    sdc = re.sub(r"set non_clk_in \[get_ports \{[^}]*\}\]", "set non_clk_in [get_ports {%s}]" % " ".join(ins), sdc)
    sdc = re.sub(r"\[get_ports \{rx_block_ready fault_cause[^}]*\}\]", "[get_ports {%s}]" % " ".join(outs), sdc)
    open(f"{K}/constraint.sdc", "w").write(sdc)
    json.dump(dict(top=top, outline=[W, H], macros=macros, npins=len(pins) + 1), open(f"{K}/probe.json", "w"), indent=1)
    return K

ROWS = [(25.836, "1", "1"), (112.236, "1", "0"), (207.42, "0", "0"), (293.82, "0", "1")]
def mac(x, o, ys=None):
    ys = ys or [r[0] for r in ROWS]
    return [(f"u_fcore.u_rxb.g_block\\[{b}\\].u_block.g_mem\\[{m}\\].u_mem.u_sram", x, y, o) for (y0, b, m), y in zip(ROWS, ys)]

RX_IN = "rst_n tx_cal_fault rx_arm_bank rx_arm_v rx_block_words rx_release_bank rx_release_v rx_slot_bank rx_slot_index rx_slot_v sd_rx sd_st".split()
RX_OUT = "rx_block_ready fault_cause fault phy_up rx_pin_v rx_pin_flit".split()
ctl_s = ["fault", "phy_up", "rst_n", "rx_arm_bank", "rx_arm_v", "rx_pin_v", "rx_release_bank", "rx_release_v", "rx_slot_bank",
         "rx_slot_v", "sd_st[0]", "sd_st[1]", "tx_cal_fault"] + bits("rx_slot_index", 6) + bits("rx_block_words", 7)
stat_n = bits("rx_block_ready", 2) + bits("fault_cause", 11)

which = sys.argv[1:] or ["tx", "rx1", "rx2"]
if "tx" in which:
    # TX: pure logic; sd_tx 512 on S (M5, 0.192 pitch -> 98 um), tx_frame 612 + tx_v on W (M4, 0.192 -> 118 um)
    W, H = 112.32, 133.92
    p = face_pins("S", bits("sd_tx", 512), W, H, 7.0, 0.192)
    p += face_pins("W", ["tx_v"] + bits("tx_frame", 612), W, H, 6.0, 0.192)
    p += face_pins("N", ["rst_n", "tx_cal_fault"], W, H, 50.0, 4.32)
    print(mk("tx", "hfd_ep_static_tx", W, H, p, (W / 2, H / 2), [], ["rst_n", "tx_v", "tx_frame"], ["sd_tx", "tx_cal_fault"], "0.3"))
if "rx1" in which:
    # RX1: same slot 241.92x397.44 + same SRAM column (MY x 35.316) as ep_my; E face sd_rx/rx_pin_flit as the plan pins file
    W, H = 241.92, 397.44
    p = face_pins("E", bits("rx_pin_flit", 612), W, H, 8.808, 0.336)
    p += face_pins("E", bits("sd_rx", 512), W, H, 215.784, 0.336)
    p += face_pins("S", ctl_s, W, H, 12.984, 8.64)
    p += face_pins("N", stat_n, W, H, 17.304, 17.28)
    print(mk("rx1", "hfd_ep_static_rx", W, H, p, (120.984, 198.72), mac(35.316, "MY"), RX_IN, RX_OUT))
if "rx2" in which:
    # RX2: 285.12x397.44, SRAM column MY at x 12.96 (main SRAM pin side E -> 92-um logic strip), sd_rx on S under the strip
    W, H = 285.12, 397.44
    p = face_pins("E", bits("rx_pin_flit", 612), W, H, 8.808, 0.336)
    p += face_pins("S", bits("sd_rx", 512), W, H, 185.0, 0.192)
    p += face_pins("S", ctl_s, W, H, 12.984, 6.48)
    p += face_pins("N", stat_n, W, H, 190.0, 6.48)
    print(mk("rx2", "hfd_ep_static_rx", W, H, p, (234.0, 198.72), mac(12.96, "MY"), RX_IN, RX_OUT))
if "tx2" in which:
    # TX2 (after tx AUTO-GEOM fill/empty FAIL on 112.32x133.92): 99.36 square, sd_tx 512 on S, tx_v + tx_frame[0..499]
    # on W, tx_frame[500..611] on N (0.192 pitch = 5.2 pins/um <= 6), fill ~0.17 at 1,401 um2
    W, H = 99.36, 99.36
    tf = bits("tx_frame", 612)
    p = face_pins("S", bits("sd_tx", 512), W, H, 0.6, 0.192)
    p += face_pins("W", ["tx_v"] + tf[:500], W, H, 1.0, 0.192)
    p += face_pins("N", tf[500:], W, H, 30.0, 0.192)
    p += face_pins("E", ["rst_n", "tx_cal_fault"], W, H, 40.0, 4.32)
    print(mk("tx2", "hfd_ep_static_tx", W, H, p, (W / 2, H / 2), [], ["rst_n", "tx_v", "tx_frame"], ["sd_tx", "tx_cal_fault"], "0.2"))
if "tx3" in which:
    # TX3 (tx2 fill 0.1365 < 0.15): 95.04 square, 0.192 pitch on all four faces (<= 490 pins/face)
    W, H = 95.04, 95.04
    tf = bits("tx_frame", 612); sd = bits("sd_tx", 512)
    p = face_pins("S", sd[:480], W, H, 1.0, 0.192)
    p += face_pins("E", sd[480:], W, H, 1.0, 0.192)
    p += face_pins("W", ["tx_v"] + tf[:480], W, H, 1.0, 0.192)
    p += face_pins("N", tf[480:], W, H, 1.0, 0.192)
    p += face_pins("E", ["rst_n", "tx_cal_fault"], W, H, 60.0, 4.32)
    print(mk("tx3", "hfd_ep_static_tx", W, H, p, (W / 2, H / 2), [], ["rst_n", "tx_v", "tx_frame"], ["sd_tx", "tx_cal_fault"], "0.2"))
if "rx3" in which:
    # RX3 (after rx1 GRT 33 / rx2 fill+col_v): 263.52 wide -> macro share 50.9 % (fill INFO band), SRAM column MY at x 12.96,
    # E logic strip ~70.6 um; sd_rx on S (0.192) under the strip, rx_pin_flit E, status pins N over the strip
    W, H = 263.52, 397.44
    p = face_pins("E", bits("rx_pin_flit", 612), W, H, 8.808, 0.336)
    p += face_pins("S", bits("sd_rx", 512), W, H, 160.0, 0.192)
    p += face_pins("S", ctl_s, W, H, 12.984, 5.4)
    p += face_pins("N", stat_n, W, H, 192.0, 4.32)
    print(mk("rx3", "hfd_ep_static_rx", W, H, p, (224.0, 198.72), mac(12.96, "MY"), RX_IN, RX_OUT))
