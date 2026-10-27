#!/usr/bin/env python3
"""kvspc_face_ports.wrapper accepts a cut whose hck is already tied to ck (common833 bind); fails on neither/both."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kvspc_face_ports as K


def mk(hck_bind):
    return ("module m (\n    input wire [0:0] ck,\n    input wire [0:0] hck,\n"
            "    input wire [3:0] pc__front_hbm_data,\n    input wire [3:0] pc__return_hbm_data,\n"
            "    input wire [260:0] pc__land_er,\n    input wire [0:0] rst_n\n);\n  leaf u (" + hck_bind +
            ", .pc__front_hbm_data(pc__front_hbm_data[3:0]), .pc__return_hbm_data(pc__return_hbm_data[3:0]),"
            " .pc__land_er(pc__land_er[260:0]));\nendmodule\n")


def run():
    for b in (".hck(hck[0])", ".hck(ck[0])"):
        out = K.wrapper(mk(b), "m")
        assert ".hck(ck[0])" in out and ".hck(hck[0])" not in out and "input wire [0:0] hck" not in out, b
    for bad in (".hck(x[0])", ".hck(hck[0]), .hck(ck[0])"):
        try:
            K.wrapper(mk(bad), "m")
        except AssertionError:
            continue
        raise SystemExit(f"FAIL: accepted {bad}")
    print("OK")


if __name__ == "__main__":
    run()
