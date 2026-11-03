"""DIE-KV-64/RF-E 11-03 RE-FORM RF-KV1 of ot_nhb_zh (AHUB hard child; two strikes: native151 TT -22.83 / FF -13.47 /
slew 1202, then ECO A1 on the same placement-buffer nets).

Failure cause ([CHECKED] zh_native151_model signoff/tt/sta.log + RCX probe of DIE-KV-63/ahub): each of the 16 read
ports g_z[gz].g_b[gb].g_f[gf] takes a registered 6-bit node address (ot_nhb_dup_a6 u_a) and reads 16 b out of 64
entries of zm (64:1 mux, zv-masked).  Every address bit therefore drives the full mux tree (up to 512 loads), which
the tool buffers into fanout-64 placement-buffer chains (place*/fanout*, slew 330-404 ps vs 320; 3 x ~100 ps on the
worst TT path g_z[0].g_b[0].g_f[1].u_a/q[1] -> za_r[17]).

Form (0 cycles, exact): the read address is captured PRE-DECODED.  Each port's kept register module ot_nhb_rf1_pd
holds onehot(d[5:3]) and onehot(d[2:0]) (2 x 8 FF) from the same D the old u_a captured; entry a of the port is
selected by hi[a/8] & lo[a%8] (one AND2 per entry, each pre-decode bit drives 8 AND2), and the 16-b read is an
AND-OR over the 64 entries, so no select net fans out > 16.  hi/lo == onehot(old a) on every edge (no reset, like
u_a), so rd and the za_r / zb_r captures are unchanged.
Added flops: 16 ports x (16 - 6) = +160 FF (PG XCHECK-1: 160 / 0.0229 mm2 = 7.0k bits/mm2 in the ZH outline,
0.6k bits/mm2 over the AHUB slot 604.8 x 440.64 that carries it).
"""
import hashlib
import json
import re
from pathlib import Path

MOD = "ot_nhb_zh"
OLD = """                (* keep_hierarchy *) ot_nhb_dup_a6 u_a (.clk(clk), .d({zg_p, pzz[4:0]}), .q(a));
                wire [6:0]  ix = {a[5], a[4:0], gb[0]};
                wire [15:0] rd = zv[ix] ? zm[32*ix + 16*gf +: 16] : 16'd0;
"""
NEW = """                // RF-KV1 (DIE-KV-64/RF-E 11-03, zh_rf1.py): pre-decoded registered read address, <= 16 loads per bit
                wire [7:0] ahi, alo;
                (* keep_hierarchy *) ot_nhb_rf1_pd u_a (.clk(clk), .d({zg_p, pzz[4:0]}), .hi(ahi), .lo(alo));
                wire [15:0] rd = rf1_rd(ahi, alo, zv, zm, gb, gf);
"""
FUNC = """    // RF-KV1: 16-b read of port (gb, gf): OR over the 64 entries {a, gb} of (hi[a/8] & lo[a%8] & zv) & zm
    function automatic [15:0] rf1_rd(input [7:0] hi, input [7:0] lo, input [127:0] v, input [32*128-1:0] m,
                                     input integer b, input integer f);
        integer e;
        begin
            rf1_rd = 16'd0;
            for (e = 0; e < 64; e = e + 1)
                rf1_rd = rf1_rd | ({16{hi[e / 8] & lo[e % 8] & v[2*e + b]}} & m[32*(2*e + b) + 16*f +: 16]);
        end
    endfunction
"""
MODS = """
(* keep_hierarchy *) module ot_nhb_rf1_pd (input wire clk, input wire [5:0] d, output reg [7:0] hi, output reg [7:0] lo);
    always @(posedge clk) begin hi <= 8'd1 << d[5:3]; lo <= 8'd1 << d[2:0]; end
endmodule
"""


ZY_OLD_DECL = "    reg [ZW*32-1:0] zy_r;\n"
ZY_OLD_REG = "    always @(posedge clk) zy_r <= zy;\n"
ZY_OLD_USE = "if (zw_oh[z_][e_]) zm[32*e_ +: 32] <= zy_r[32*z_ +: 32];"
ZY_NEW_USE = "if (zw_oh[z_][e_]) zm[32*e_ +: 32] <= zy_rr[e_ / ZY_SPAN][32*z_ +: 32];"
ZY_MOD = """
(* keep_hierarchy *) module ot_nhb_rf1_zy (input wire clk, input wire [127:0] d, output reg [127:0] q);
    always @(posedge clk) q <= d;
endmodule
"""


def transform_zy(text, reps=8):
    """RF-KV1b: the adder result register zy_r (128 b, each bit -> the zm write mux of all 128 entries) becomes
    `reps` kept identical replicas, replica k feeding entries [k*128/reps, (k+1)*128/reps): <= 128/reps write loads
    per bit, 0 cycles, exact (every replica captures the same zy on the same edge, no reset, like zy_r)."""
    if 128 % reps or reps < 2:
        raise ValueError("zh_rf1: zy replicas must divide 128")
    for s in (ZY_OLD_DECL, ZY_OLD_REG, ZY_OLD_USE):
        if text.count(s) != 1:
            raise ValueError(f"zh_rf1: zy_r form not as expected: {s.strip()}")
    if len(re.findall(r"\bzy_r\b", text)) != 3:
        raise ValueError("zh_rf1: zy_r has uses beyond the zm write")
    new_decl = (f"    // RF-KV1b (DIE-KV-64/RF-E 11-03): {reps} kept zy_r replicas, <= {128 // reps} zm write loads per bit\n"
                f"    localparam integer ZY_REPS = {reps}, ZY_SPAN = 128 / ZY_REPS;\n"
                "    wire [ZW*32-1:0] zy_rr [0:ZY_REPS-1];\n")
    new_reg = ("    genvar zyk;\n    generate for (zyk = 0; zyk < ZY_REPS; zyk = zyk + 1) begin : g_zy\n"
               "        (* keep_hierarchy *) ot_nhb_rf1_zy u_zy (.clk(clk), .d(zy), .q(zy_rr[zyk]));\n"
               "    end endgenerate\n")
    text = text.replace(ZY_OLD_DECL, new_decl, 1).replace(ZY_OLD_REG, new_reg, 1).replace(ZY_OLD_USE, ZY_NEW_USE, 1)
    return text + ZY_MOD


def transform(text):
    """-> rewritten ot_nhb_tiles.sv text; fail-closed on any unexpected shape"""
    if len(re.findall(rf"^module {MOD}\b", text, re.M)) != 1:
        raise ValueError(f"zh_rf1: expected one module {MOD}")
    if "rf1_" in text:
        raise ValueError("zh_rf1: already applied")
    if text.count(OLD) != 1:
        raise ValueError("zh_rf1: ZH read port (u_a / ix / rd) not in the expected form")
    anchor = "    localparam integer ZW = 4, ADD_LAT = 7;\n"
    start = text.index(f"module {MOD}")
    if text.count(anchor) != 1 or text.index(anchor) < start:
        raise ValueError("zh_rf1: ZH localparam anchor missing")
    for decl in ("reg [32*128-1:0] zm;", "reg [127:0]      zv;"):
        if decl not in text:
            raise ValueError(f"zh_rf1: {decl} not found")
    text = text.replace(anchor, anchor + FUNC, 1).replace(OLD, NEW, 1)
    return text + MODS


def apply_kit(kd, mod, zy_reps=0):
    kd = Path(kd)
    if mod != MOD:
        raise SystemExit(f"--zh-rf1 only applies to {MOD}")
    srcs = [p for p in sorted((kd / "rtl").glob("*.sv")) if re.search(rf"^module {MOD}\b", p.read_text(), re.M)]
    if len(srcs) != 1:
        raise SystemExit(f"--zh-rf1: expected one {MOD} source in the kit rtl, found {len(srcs)}")
    p = srcs[0]
    before = hashlib.sha256(p.read_bytes()).hexdigest()
    try:
        t = transform(p.read_text())
        if zy_reps:
            t = transform_zy(t, zy_reps)
        p.write_text(t)
    except ValueError as e:
        raise SystemExit(str(e))
    delta = dict(transform="physical/die_plan/qwen_kvsys/cores/harden/zh_rf1.py", file=p.name,
                 sha256_before=before, sha256_after=hashlib.sha256(p.read_bytes()).hexdigest(),
                 command_cycles=0, nominal_token_cycles=0,
                 added_ff=16 * (16 - 6) + (128 * (zy_reps - 1) if zy_reps else 0), max_select_loads=16,
                 zy_replicas=zy_reps or 1,
                 form="pre-decoded registered ZH read address (RF-KV1)"
                      + (f" + {zy_reps} zy_r write replicas (RF-KV1b)" if zy_reps else ""))
    (kd / "zh_rf1_delta.json").write_text(json.dumps(delta, indent=1) + "\n")
    return delta


# ---- derive: the RE-FORM kit from the exact native ZH kit (same pins / io.tcl / outline / PG / SDC) --------------------
# The native ZH kit's pin geometry is the retained ref_tile LEF contract (offset 0.012, q6_pin_geometry_prepare.py), which
# gen_core_kit_kv.py's symmetric-track pin gate does not take; so the RE-FORM keeps that generated kit byte-for-byte
# except: the transformed RTL, the DRV form OT_MAXWIRE_UM (repeater pitch, tools/die_plan/grt_maxwire.tcl), the KV core
# recipe GRT hold target OT_HOLD_FF_MARGIN, and a fresh freeze/PROVENANCE stamp (kit_hash, source_commit).
SKIP_DIRS = {"run", "signoff", "lec", "lec_async.runs", "views", "physical_completion", "__pycache__", "reset_contract"}
SKIP_FILES = {"1_synth_odb.v", "pin_audit.json", "status", "status.grt_est0104", "lec_async.done", "lec_async.identity",
              "lec_async.lock", "lec_async.owner", "lec_async.pid", "lec_async.rc", "lec_async.ready",
              "lec_async.source_identity", "face_guard_synth_model.json", "face_guard_odb.json", "face_guard.json",
              "synth_area_model.json", "rtl_lint.json", "selrange.json"}
# sdc_lint.json is NOT an output: gen_core_kit_kv.py writes it as the sdc_lint gate context (run_kit_kv.sh reads it)


def derive(src, out, repo, maxwire_um=60, hold_ff_margin=10, zy_reps=0, io_hold_pad_margin=None):
    import re as _re
    import shutil
    import sys
    src, out, repo = Path(src), Path(out), Path(repo)
    sys.path.insert(0, str(repo / "tools/die_plan"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import lec as LEC
    import gen_core_kit_kv as GEN
    fz = json.loads((src / "freeze.json").read_text())
    if fz.get("module") != MOD or fz.get("outline_um") != [151.2, 151.2]:
        raise SystemExit("zh_rf1 derive: source kit is not the 151.2 native ZH kit")
    kd = out / fz["type"]
    if kd.exists():
        raise SystemExit(f"zh_rf1 derive: {kd} exists")
    kd.mkdir(parents=True)
    for p in sorted(src.iterdir()):
        if p.is_dir():
            if p.name not in SKIP_DIRS:
                shutil.copytree(p, kd / p.name)
        elif p.name not in SKIP_FILES and not p.name.endswith(".log") and not p.name.startswith("cont."):
            shutil.copy2(p, kd / p.name)
    delta = apply_kit(kd, MOD, zy_reps)
    cfg = (kd / "config.mk").read_text()
    cfg, n = _re.subn(r"^export OT_HOLD_FF_MARGIN = .*$", f"export OT_HOLD_FF_MARGIN = {hold_ff_margin:g}", cfg, flags=_re.M)
    if n != 1 or "OT_MAXWIRE_UM" in cfg or "OT_IO_HOLD_PAD" in cfg:
        raise SystemExit("zh_rf1 derive: config.mk OT_HOLD_FF_MARGIN / OT_MAXWIRE_UM / OT_IO_HOLD_PAD not in the expected form")
    cfg += f"export OT_MAXWIRE_UM = {maxwire_um:g}\n"
    if io_hold_pad_margin is not None:
        # IO-HOLD-PAD (tools/orfs_hold_mm.tcl, COORD 10-27 (d), METHODOLOGY 12.8): the kit's input-port -> face-register
        # hold contract padded per bit with HB4 in the GRT step (KV kits repair FF hold first at GRT).  RF-E zh rfA2:
        # in-flow GRT hold +10.0 ps -> routed sign-off FF -15.73 ps on 70 input-face endpoints (sid_q / zs_we_q).
        cfg += ("export OT_IO_HOLD_PAD = 1\nexport OT_IO_HOLD_PAD_STAGE = grt\n"
                f"export OT_IO_HOLD_PAD_MARGIN_PS = {io_hold_pad_margin:g}\n")
        delta["io_hold_pad_margin_ps"] = io_hold_pad_margin
    (kd / "config.mk").write_text(cfg)
    shutil.copyfile(repo / "tools/die_plan/grt_maxwire.tcl", kd / "grt_maxwire.tcl")
    prov = LEC._repo_provenance(repo)
    fz.update(source_commit=prov.get("commit"), rf1=dict(delta, derived_from=str(src), derived_from_kit_hash=fz.get("kit_hash"),
              maxwire_um=maxwire_um, hold_ff_margin_ps=hold_ff_margin))
    fz["kit_hash"] = GEN.kit_hash(kd)
    (kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
    LEC.write_kit_provenance(kd, repo, provenance=prov)
    return kd


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="derive the RF-KV1 ZH kit from the native ZH kit")
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[5]))
    ap.add_argument("--maxwire-um", type=float, default=60)
    ap.add_argument("--hold-ff-margin", type=float, default=10)
    ap.add_argument("--zy-reps", type=int, default=0, help="RF-KV1b: kept zy_r write replicas (0 = RF-KV1 only)")
    ap.add_argument("--io-hold-pad-margin", type=float, default=None, help="enable IO-HOLD-PAD at GRT with this margin")
    a = ap.parse_args()
    print(derive(a.src, a.out, a.repo, a.maxwire_um, a.hold_ff_margin, a.zy_reps, a.io_hold_pad_margin))
