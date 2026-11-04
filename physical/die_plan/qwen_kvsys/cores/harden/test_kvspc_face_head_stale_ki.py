#!/usr/bin/env python3
"""kvspc_face_ports.wrapper on a chain head whose raw cut already carries the pins-file slices pc__ki_15 / pc__ki_31 beside
the full bus: one declaration of each, so yosys-slang (LEC gold) elaborates the wrapper (DIE-KV-65/LEC 11-03)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kvspc_face_ports as K


def mk(stale="", ki_body=".pc__ki(pc__ki[32:0])"):
    return ("module m (\n    input wire [0:0] ck,\n    input wire [3:0] pc__front_hbm_data,\n"
            "    input wire [3:0] pc__return_hbm_data,\n    input wire [32:0] pc__ki,\n" + stale +
            "    input wire [260:0] pc__land_er,\n    input wire [0:0] rst_n\n);\n  leaf u (.hck(ck[0]), "
            ".pc__front_hbm_data(pc__front_hbm_data[3:0]), .pc__return_hbm_data(pc__return_hbm_data[3:0]), "
            ".pc__land_er(pc__land_er[260:0]), " + ki_body + ");\nendmodule\n")


STALE = "    input wire [20:15] pc__ki_15,\n    input wire [32:31] pc__ki_31,\n"


@pytest.mark.parametrize("stale", ["", STALE])
def test_one_declaration_of_each_slice(stale):
    out = K.wrapper(mk(stale), "m", head=True)
    assert out.count("input wire [20:15] pc__ki_15,") == 1
    assert out.count("input wire [32:31] pc__ki_31,") == 1
    assert ".pc__ki({pc__ki_31[32:31], 10'd0, pc__ki_15[20:15], 14'd0, pc__ki[0:0]})" in out


def test_live_slice_is_not_discarded():
    with pytest.raises(AssertionError):
        K.wrapper(mk(STALE, ".pc__ki(pc__ki[32:0]), .x(pc__ki_15[15])"), "m", head=True)


def test_repeated_port_fails_closed():
    with pytest.raises(AssertionError, match="repeated wrapper ports"):
        K.wrapper(mk("    input wire [1:0] other,\n    input wire [1:0] other,\n"), "m", head=True)
