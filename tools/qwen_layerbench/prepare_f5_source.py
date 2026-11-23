#!/usr/bin/env python3
"""Prepare explicitly selected F5 source and ROM inputs in a fresh directory.

This stages RTL and exact masks for a private compile. Use the returned source
paths in the source-selection manifest before any physical source preparation.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil


ROOT = Path(__file__).resolve().parents[2]
HEAD = Path("rtl/qwen_dv/headprep37")
FACE = Path("rtl/qwen_split")
FQREG = Path("rtl/qwen_dv/headprep13/frontend_fqreg/qfd_dv_cmd_cal_mu_fqreg.sv")


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"expected one matching exact source fragment: {old}")
    return text.replace(old, new, 1)


def write(out, path, text):
    dest = out / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text)


def words(path):
    return [int(line, 16) for line in path.read_text().split()]


def copy(out, path):
    dest = out / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / path, dest)


def select_tt(frontend, media, out):
    desc = words(media / "dw.hex")
    if len(desc) != 8 or desc[0] >> 32 != 0x43414c52 or (desc[0] & 0xfffffc00) != 0x400:
        raise ValueError("CALR DW0 must select dual ages in bit 10")
    nent = desc[0] & 0x3ff
    if not 0 < nent <= 1023:
        raise ValueError("CALR descriptor does not address the native media")
    for addr in (1, 2, 3, 4):
        start, count = desc[addr] >> 16, desc[addr] & 1023
        if start % 4 or not count or start + count > nent:
            raise ValueError(f"CALR descriptor DW{addr} is outside the aligned ROM")
    for name in ("calendar_m0.viamap.hex", "calendar_m1.viamap.hex"):
        image = words(media / name)
        if len(image) != 256 or any(w >= (1 << 2128) for w in image):
            raise ValueError(f"CALR physical bank shape differs: {name}")

    src = (ROOT / HEAD / "qfd_dv_cmd_cal_mu_head37.sv").read_text()
    src = replace_once(src, "module qfd_dv_cmd_cal_mu_head37 #(", "module qfd_dv_cmd_cal_mu #(")
    for param in ("CALREG", "COLD_DELTA", "TABLE_NEXT"):
        src = replace_once(src, f"parameter integer {param} = 0", f"parameter integer {param} = 1")
    original = (frontend / FQREG).read_text()
    if "parameter integer CALREG = 1" not in original or "COLD_DELTA" in original:
        raise ValueError("expected the pristine selected HP13 FQREG frontend")
    write(out, FQREG, src)
    rom = HEAD / "qfd_dv_calendar_rom_dual_age.sv"
    copy(out, rom)
    recipe = "frontend_head37_1.ys"
    selected = (frontend / recipe).read_text()
    if "chparam -set HEAD_STAGE37 1" not in selected:
        raise ValueError("expected the explicit native HEAD37 constructor selection")
    selected = replace_once(selected, " " + str(FQREG) + " ", " " + str(FQREG) + " " + str(rom) + " ")
    write(out, recipe, selected)
    for name in ("dw.hex", "calendar_m0.viamap.hex", "calendar_m1.viamap.hex"):
        (out / "calr_media").mkdir(exist_ok=True)
        shutil.copyfile(media / name, out / "calr_media" / name)


def select_face(core, logical, segments, out):
    data = words(logical)
    if len(data) != 4096 or any(w >= (1 << 72) for w in data):
        raise ValueError("expected a complete 4096-by-72 C configuration ROM")
    if data[1024] >> 32 != 0x43414c52 or (data[1024] & 0xfffffc00) != 0x400:
        raise ValueError("C program replay requires its selected CALR DW0 marker")
    tape = data[1536:1825]
    if any(not w & (1 << 11) or w >= (1 << 32) or w >> 12 < 4 for w in tape):
        raise ValueError("shared F5 tape has an invalid start record")
    if any(w & (1 << 7) for w in tape[:-1]) or not tape[-1] & (1 << 7) or any(data[1825:2048]):
        raise ValueError("shared F5 tape must wrap once and stay inside the free address region")
    header = segments.read_text()
    if not re.search(r"\bNSTART\s*=\s*288\s*,", header):
        raise ValueError("expected the fixed F5 pair's 288 starts")
    lib = ROOT / "tools/qwen_split/sys_face_image.py"
    spec = importlib.util.spec_from_file_location("sys_face_image", lib)
    compiler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(compiler)
    source = core.read_text()
    source = replace_once(source, "    wire [71:0] rom_q;", """    wire [71:0] rom_q;
    wire [8:0] f5_tape_addr;
    wire f5_tape_enable;
    wire [11:0] selected_rom_addr = f5_tape_enable ? {3'b011,f5_tape_addr} : rom_a;
    wire selected_rom_ce = rom_ce || f5_tape_enable;""")
    if source.count(".ce_in(rom_ce), .addr_in(rom_a)") != 2:
        raise ValueError("C ROM simulation and synthesis port declarations differ")
    source = source.replace(".ce_in(rom_ce), .addr_in(rom_a)", ".ce_in(selected_rom_ce), .addr_in(selected_rom_addr)")
    source = replace_once(source, "    wire        rp_program_ready, rp_fault;", """    wire        rp_program_ready, rp_fault;
    // Boot and program issue keep priority and are decoded by the existing qualified strobes.
    assign f5_tape_enable = (st == S_IDLE) && boot_done && rp_program_ready && !rom_ce;""")
    source = replace_once(source, "qfd_sysface_cseq_single #(.CTL_PAD", "qfd_sysface_cseq_f5_shared #(.CTL_PAD")
    source = replace_once(source, ".epoch_go(fwd_epoch), .halt(input_source_copies[44]),",
        ".epoch_go(fwd_epoch), .halt(input_source_copies[44]),\n"
        "        .media_hold(!f5_tape_enable), .shared_tape_word(rom_qr[31:0]), .shared_tape_addr(f5_tape_addr),")
    write(out, FACE / "qfd_sys_face_lctx3_core.sv", source)
    for name in ("qfd_sysface_cseq_f5_shared.sv", "ot_qwen_d2d_ovl_seq_shared.sv",
                 "ot_qwen_d2d_list_play_f5_shared.sv"):
        copy(out, FACE / name)
    write(out, FACE / "qfd_sysface_f5_shared_calendar.svh", header)
    write(out, "c_media/sys_face_cfg.viamap.hex", compiler.viamap(dict(enumerate(data))))
    write(out, "c_media/host_auth_digest.txt", f"{compiler.image_digest(data[:1032]):016x}\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--tt-frontend", type=Path)
    p.add_argument("--calr-media", type=Path)
    p.add_argument("--c-core", type=Path)
    p.add_argument("--c-logical", type=Path)
    p.add_argument("--c-segments", type=Path)
    a = p.parse_args()
    tt = (a.tt_frontend, a.calr_media)
    face = (a.c_core, a.c_logical, a.c_segments)
    if (any(tt) and not all(tt)) or (any(face) and not all(face)) or not (all(tt) or all(face)):
        p.error("select all inputs for a TT frontend, a C face, or both")
    if all(tt) and all(face) and words(a.calr_media / "dw.hex") != words(a.c_logical)[1024:1032]:
        p.error("C boot descriptor differs from the selected TT descriptor")
    a.out.mkdir(parents=True, exist_ok=False)
    if all(tt):
        select_tt(*tt, a.out)
    if all(face):
        select_face(*face, a.out)
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    report = {"status": "PRIVATE_F5_SELECTED_SOURCE", "tt_dual_age": bool(all(tt)),
              "c_shared_mask": bool(all(face)),
              "output_sha256": {str(p.relative_to(a.out)): sha(p) for p in sorted(a.out.rglob("*")) if p.is_file()}}
    write(a.out, "receipt.json", json.dumps(report, indent=2)+"\n")


if __name__ == "__main__":
    main()
