#!/usr/bin/env python3
"""kit_preflight._guarded (QC-A0-KITS-3 10-28): the once-per-body block state gives the same answer as the original
per-instance replay of every begin/end token before the position, and a large flat (mapped) body stays linear."""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_preflight as P  # noqa: E402


def _replay(text, pos):
    stack = []
    for m in P._BLOCK.finditer(text, 0, pos):
        if m.group(1) == 'begin':
            stack.append(P._cond_before(text, m.start()))
        elif stack:
            stack.pop()
    return any(stack)


BODY = """
  generate if (W > 4) begin : g_big
    sub_a u_a (.x(x));
    for (i = 0; i < 2; i = i + 1) begin : g_loop
      sub_b u_b (.x(x));
    end
  end else begin : g_small
    sub_c u_c (.x(x));
  end endgenerate
  always @(posedge clk) begin q <= d; end
  case (m) 1: begin sub_d u_d (.x(x)); end default: ; endcase
  sub_e u_e (.x(x));
"""


def test_guarded_matches_replay_at_every_offset():
    for pos in range(len(BODY) + 1):
        assert P._guarded(BODY, pos) == _replay(BODY, pos), pos
    assert P._guarded(BODY, BODY.index("sub_a")) and P._guarded(BODY, BODY.index("sub_c"))
    assert not P._guarded(BODY, BODY.index("sub_e"))


def test_flat_mapped_body_is_linear():
    body = "".join(f"  BUFx2_ASAP7_75t_R u{i} (.A(n{i}), .Y(n{i + 1}));\n" for i in range(60000))
    t0 = time.time()
    hits = [m.start(2) for m in P._INST.finditer(body)]
    assert len(hits) == 60000
    assert not any(P._guarded(body, h) for h in hits)
    assert time.time() - t0 < 30
