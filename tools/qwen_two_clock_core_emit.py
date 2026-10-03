#!/usr/bin/env python3
"""Emit ot_hdc_core_vector_weight_2clk: the pinned Qwen ROM decode core with its matrix engine behind the
default-off two-clock wrapper ot_hdc_me_2clk (rtl/hdc/ot_hdc_me_2clk.sv).

The pinned source rtl/hdc/ot_hdc_core_vector_weight.sv is read, never edited (AGENTS.md: pinned files stay
byte-identical); the variant is a build product, like tools/qwen_rom_rt_core_emit_w12.py's core.  Every edit is
an exact anchor replacement that must match once, or the tool refuses:
  * the module is renamed and gains ME_CDC (default 0) and ME_CDC_DEPTH parameters;
  * ports: `fclk` (the 1.2 GHz streaming clock) and a fast-domain BF16 weight port f_wrom_* (the shared wrom port
    keeps serving the stream unit on the slow clock);
  * u_me becomes ot_hdc_me_2clk with the same parameters and connections plus fclk/f_wrom_*.
  * with ME_CDC != 0 only: an engine op that chases the stream unit's rows waits for that stream op to finish
    (the single-clock chase assumes the engine never overtakes a same-clock producer; at 1.2 vs 0.9 GHz it would).
With ME_CDC = 0 the wrapper instantiates ot_hdc_matvec on the core clock with the identical connections, so the
emitted core is the pinned core plus three unused ports.

    python3 tools/qwen_two_clock_core_emit.py --out DIR      (writes DIR/ot_hdc_core_vector_weight_2clk.sv + .json)
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINNED = ROOT / "rtl/hdc/ot_hdc_core_vector_weight.sv"
WRAPPER = ROOT / "rtl/hdc/ot_hdc_me_2clk.sv"
EDITS = [
    ("module ot_hdc_core_vector_weight #(\n",
     "module ot_hdc_core_vector_weight_2clk #(\n"
     "    // ME_CDC = 1: the matrix engine runs on fclk (1.2 GHz streaming domain) behind ot_ratio_cdc_fifo\n"
     "    // crossings (rtl/hdc/ot_hdc_me_2clk.sv); 0 (default) is the pinned core.\n"
     "    parameter integer ME_CDC = 0,\n"
     "    parameter integer ME_CDC_DEPTH = 4,\n"
     "    // ME_CDC_SAFE_CHASE = 1 (default): an engine op that chases stream-unit rows waits for the stream op to\n"
     "    // finish (rate-safe by construction).  0 keeps the single-clock row chase: measured exact at the gated\n"
     "    // shape only, NOT proven rate-safe -- diagnostic.\n"
     "    parameter integer ME_CDC_SAFE_CHASE = 1,\n"),
    ("    input  wire              clk,\n",
     "    input  wire              clk,\n"
     "    input  wire              fclk,            // ME_CDC: the engine's 1.2 GHz clock (3:4 with clk, one PLL)\n"),
    ("    output wire              wrom_re,\n",
     "    // ME_CDC with BF16 weights: the engine's weight ROM port on fclk\n"
     "    output wire              f_wrom_re,\n"
     "    output wire [AW-1:0]     f_wrom_addr,\n"
     "    input  wire [G*W*16-1:0] f_wrom_q,\n"
     "    output wire              wrom_re,\n"),
    ("    ot_hdc_matvec #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW),\n",
     "    ot_hdc_me_2clk #(.ME_CDC(ME_CDC), .CDC_DEPTH(ME_CDC_DEPTH), .W(W), .G(G), .IL(IL), .AW(AW), .NW(NW),\n"),
    ("        .clk(me_clk), .rst_n(rst_n), .go(me_go), .ready(me_ready), .idle(me_idle),\n",
     "        .fclk(fclk), .f_wrom_re(f_wrom_re), .f_wrom_addr(f_wrom_addr), .f_wrom_q(f_wrom_q),\n"
     "        .clk(me_clk), .rst_n(rst_n), .go(me_go), .ready(me_ready), .idle(me_idle),\n"),
]
EDITS.append((
    "    wire chased = ((d_unit == 2'd1) ? (d_chase_rows ? su_rows : su_progress) : me_progress) >= d_chase_n;\n",
    "    //: ME_CDC: an engine op that CHASES the stream unit's rows reads them at the engine's rate; the single-clock\n"
    "    //: chase relies on equal clocks (the engine never overtakes the producer).  At 1.2 GHz against a 0.9 GHz\n"
    "    //: producer it would, so with ME_CDC the engine op waits for the chased stream op to finish (su_idle: every\n"
    "    //: write in the vector memory).  The other direction (a stream op chasing engine results) stays a chase:\n"
    "    //: me_progress counts results already written through the crossing, so it can only run late.\n"
    "    wire chased = ((d_unit == 2'd1) ? ((ME_CDC != 0 && ME_CDC_SAFE_CHASE != 0) ? su_idle : ((d_chase_rows ? su_rows : su_progress) >= d_chase_n))\n"
    "                                    : (me_progress >= d_chase_n));\n"))
TAIL = ("endmodule\n",
        "    initial if (ME_CDC != 0 && (ME_STALL != 0 || ME_IDLE_GATE != 0 || W_HBM != 0 || KV_HBM != 0))\n"
        "        $error(\"ot_hdc_core_vector_weight_2clk: ME_CDC needs ME_STALL = ME_IDLE_GATE = W_HBM = KV_HBM = 0\");\n"
        "endmodule\n")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def emit() -> str:
    src = PINNED.read_text()
    for old, new in EDITS:
        if src.count(old) != 1:
            raise SystemExit(f"anchor not unique in {PINNED.name}: {old!r} x{src.count(old)}")
        src = src.replace(old, new, 1)
    if not src.endswith(TAIL[0]) or src.count("endmodule") != 1:
        raise SystemExit("unexpected module tail")
    return src[: -len(TAIL[0])] + TAIL[1]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    text = emit()
    dst = a.out / "ot_hdc_core_vector_weight_2clk.sv"
    dst.write_text(text)
    rec = dict(schema="opentallas.qwen_two_clock_core_emit.v1", output=str(dst), output_sha256=sha(text.encode()),
               pinned_source=str(PINNED.relative_to(ROOT)), pinned_sha256=sha(PINNED.read_bytes()),
               wrapper=str(WRAPPER.relative_to(ROOT)), wrapper_sha256=sha(WRAPPER.read_bytes()),
               tool_sha256=sha(Path(__file__).read_bytes()), edits=len(EDITS) + 1)
    (a.out / "ot_hdc_core_vector_weight_2clk.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(dst)


if __name__ == "__main__":
    main()
