#!/usr/bin/env python3
"""Emit ot_hdc_core_2clk: the pinned TP decode core (rtl/hdc/ot_hdc_core.sv, the scalar-stream-unit core of the
tools/hdc_program.py --tp images) with its matrix engine behind the default-off two-clock wrapper
rtl/hdc/ot_hdc_me_2clk.sv (claude/two-clock-rtl-20261003 @ 27d86cfe).  Used by the Qwen ROM system top's dies.

The pinned core is read, never edited (AGENTS.md); the variant is a build product, emitted with the same exact
anchor method as tools/qwen_two_clock_core_emit.py (which emits the vector-weight core of the TP1 gate):
  * the module is renamed ot_hdc_core_2clk and gains ME_CDC (default 0), ME_CDC_DEPTH, ME_CDC_SAFE_CHASE;
  * ports `fclk` (the 1.2 GHz streaming clock) and a fast-domain BF16 weight port f_wrom_* (the shared wrom port
    keeps serving the stream unit on the slow clock);
  * u_me becomes ot_hdc_me_2clk with the same connections plus fclk / f_wrom_* (its scale port, unused at BF16
    weights, is tied off) -- the wrapper ANDs every engine read enable with the engine clock enable (the
    read-enable clock-gating fix, 744ab23fd);
  * the safe ordering rule (ME_CDC_SAFE_CHASE = 1, default): an engine op that chases stream-unit rows waits for the
    stream op to finish, since a 1.2 GHz engine would overtake a 0.9 GHz producer.
Unlike the TP1 variant, KV_HBM = 1 is allowed with ME_CDC: the KV service resolves a KV op's readiness (kv_ok) in
the slow domain BEFORE the sequencer issues it into the command crossing, and the op's block is complete and
read-only for the whole op, so the engine's fast-clock KV reads see settled words (the system bench counts reads
of words written within two slow cycles; it must stay 0).  ME_STALL / ME_IDLE_GATE do not exist in this core.
With ME_CDC = 0 the wrapper instantiates ot_hdc_matvec on the core clock with identical connections, so the emitted
core is the pinned core plus unused ports.

    python3 tools/qwen_rom_sys_core2clk_emit.py --out DIR      (writes DIR/ot_hdc_core_2clk.sv + .json)
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINNED = ROOT / "rtl/hdc/ot_hdc_core.sv"
WRAPPER = ROOT / "rtl/hdc/ot_hdc_me_2clk.sv"
EDITS = [
    ("module ot_hdc_core #(\n",
     "module ot_hdc_core_2clk #(\n"
     "    // ME_CDC = 1: the matrix engine runs on fclk (1.2 GHz streaming domain) behind ot_ratio_cdc_fifo\n"
     "    // crossings (rtl/hdc/ot_hdc_me_2clk.sv); 0 (default) is the pinned core.\n"
     "    parameter integer ME_CDC = 0,\n"
     "    parameter integer ME_CDC_DEPTH = 4,\n"
     "    parameter integer ME_CDC_SAFE_CHASE = 1,\n"),
    ("    input  wire              clk,\n",
     "    input  wire              clk,\n"
     "    input  wire              fclk,            // ME_CDC: the engine's 1.2 GHz clock (3:4 with clk, one PLL)\n"),
    ("    output wire              wrom_re,\n",
     "    // ME_CDC: the engine's BF16 weight ROM port on fclk\n"
     "    output wire              f_wrom_re,\n"
     "    output wire [AW-1:0]     f_wrom_addr,\n"
     "    input  wire [G*W*16-1:0] f_wrom_q,\n"
     "    output wire              wrom_re,\n"),
    ("    ot_hdc_matvec #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW)) u_me (\n"
     "        .clk(clk), .rst_n(rst_n), .go(me_go), .ready(me_ready), .idle(me_idle),\n",
     "    ot_hdc_me_2clk #(.ME_CDC(ME_CDC), .CDC_DEPTH(ME_CDC_DEPTH), .W(W), .G(G), .IL(IL), .AW(AW), .NW(NW)) u_me (\n"
     "        .fclk(fclk), .f_wrom_re(f_wrom_re), .f_wrom_addr(f_wrom_addr), .f_wrom_q(f_wrom_q),\n"
     "        .scale_re(), .scale_gre(), .scale_addr(), .scale_q({(G*W*16){1'b0}}),\n"
     "        .clk(clk), .rst_n(rst_n), .go(me_go), .ready(me_ready), .idle(me_idle),\n"),
    ("    wire chased = ((d_unit == 2'd1) ? (d_chase_rows ? su_rows : su_progress) : me_progress) >= d_chase_n;\n",
     "    //: ME_CDC: an engine op that CHASES the stream unit's rows waits for the chased stream op to finish\n"
     "    //: (a 1.2 GHz engine would overtake a 0.9 GHz producer); a stream op chasing engine results stays a chase:\n"
     "    //: me_progress counts results already written through the crossing, so it can only run late.\n"
     "    wire chased = ((d_unit == 2'd1) ? ((ME_CDC != 0 && ME_CDC_SAFE_CHASE != 0) ? su_idle\n"
     "                                       : ((d_chase_rows ? su_rows : su_progress) >= d_chase_n))\n"
     "                                    : (me_progress >= d_chase_n));\n"),
]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def emit() -> str:
    src = PINNED.read_text()
    for old, new in EDITS:
        if src.count(old) != 1:
            raise SystemExit(f"anchor not unique in {PINNED.name}: {old!r} x{src.count(old)}")
        src = src.replace(old, new, 1)
    return src


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    text = emit()
    dst = a.out / "ot_hdc_core_2clk.sv"
    dst.write_text(text)
    rec = dict(schema="opentallas.qwen_rom_sys_core2clk_emit.v1", output=str(dst), output_sha256=sha(text.encode()),
               pinned_source=str(PINNED.relative_to(ROOT)), pinned_sha256=sha(PINNED.read_bytes()),
               wrapper=str(WRAPPER.relative_to(ROOT)), wrapper_sha256=sha(WRAPPER.read_bytes()),
               tool_sha256=sha(Path(__file__).read_bytes()), edits=len(EDITS))
    (a.out / "ot_hdc_core_2clk.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(dst)


if __name__ == "__main__":
    main()
