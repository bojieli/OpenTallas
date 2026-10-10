#!/bin/bash
# sys-takeover 2026-10-09 (review of qwen-system C03, ot_qwen_tp_seq_w12_fs): full-shape collective-tag bench
# (rtl/test/qwen_system/tb_qwen_tp_seq_tag.sv: 38 stages x positions {5, 261, 517, 8191}, records / done / VM writes
# equal to the base instance; here with the Qwen layer's two all-reduce segments a stage) plus collision mutants of the full-shape tag, which must FAIL:
#   stage   -- the stage field dropped (the original stage alias)
#   pos8    -- position cut to 8 bits (the original 256 wrap; 5 vs 261)
#   seg     -- the segment field dropped (records of one stage collide)
#   seq_tag_bench.sh pos|stage|pos8|seg OUT
set -u
m=$1; o=$2; mkdir -p "$o"
F=rtl/rom/ot_qwen_tp_seq_w12_fs.sv
python3 - "$m" "$o" <<'PY'
import sys, pathlib
m, o = sys.argv[1], pathlib.Path(sys.argv[2])
t = pathlib.Path("rtl/rom/ot_qwen_tp_seq_w12_fs.sv").read_text()
a = "assign c_tag = TAGW'({gen_t, stg_t, pos_t, tok_t, tag_b[2:0]});"
assert t.count(a) == 1
b = {"pos": a, "stage": "assign c_tag = TAGW'({gen_t, 6'd0, pos_t, tok_t, tag_b[2:0]});",
     "pos8": "assign c_tag = TAGW'({gen_t, stg_t, 5'd0, pos_t[7:0], tok_t, tag_b[2:0]});",
     "seg": "assign c_tag = TAGW'({gen_t, stg_t, pos_t, tok_t, 3'd0});"}[m]
(o / "fs.sv").write_text(t.replace(a, b))
# the Qwen layer stage has TWO all-reduce segments (attention o_proj, MLP down) before END: the bench's stage program
# gets two AR segments, so a dropped segment field collides inside one stage
tb = pathlib.Path("rtl/test/qwen_system/tb_qwen_tp_seq_tag.sv").read_text()
for x, y in (("desc_q <= (daddr == 0) ? 64'h0000_0000_0000_0805 : 64'd0;  // kind 1, vw 1, nw 2",
              "desc_q <= (daddr == 0) ? 64'h0000_0000_0000_0805 : (daddr == 1) ? 64'h0000_0000_0000_0815 : 64'd0;  // 2 AR segments"),
             ("(fs_coll == 0 && n == 2 * dones && writes == 2 * dones && !fault)",
              "(fs_coll == 0 && n == 4 * dones && writes == 4 * dones && !fault)")):
    assert tb.count(x) == 1, x
    tb = tb.replace(x, y)
(o / "tb.sv").write_text(tb)
PY
iverilog -g2012 -s tb_qwen_tp_seq_tag -o "$o/sim" "$o/fs.sv" rtl/rom/ot_qwen_tp_seq_w12.sv "$o/tb.sv" > "$o/build.log" 2>&1 || { cat "$o/build.log" | head; echo SEQTAG_BENCH_ERROR; exit 2; }
vvp -n "$o/sim" > "$o/run.log" 2>&1; grep TAG_RESULT "$o/run.log"
ok=$(grep -c "TAG_RESULT pass=1 " "$o/run.log")
if [[ $m == pos ]]; then [[ $ok == 1 ]] && { echo SEQTAG_PASS; exit 0; }; echo SEQTAG_FAIL; exit 1; fi
[[ $ok == 0 ]] && { echo SEQTAG_NEG_DETECTED; exit 1; }; echo SEQTAG_NEG_MISSED; exit 0
