#!/usr/bin/env bash
set -u
OUT=$1; MODE=${2:-strict}; MUT=${3:-}
R=$(cd "$(dirname "$0")/../.." && pwd); cd "$R" || exit 2
mkdir -p "$OUT"
python3 - "$OUT/tb.sv" "$MODE" <<'PY'
import re,sys
from pathlib import Path
s=Path('rtl/test/tb_qfd_tt_ctlm_i_psram.sv').read_text()
u1=re.search(r'    ot_qfd_tt_ctlm_i #\([^\n]*\) u1 \(.*?\);',s,re.S).group()
if sys.argv[2] in ('strict','strict_argmax','power'):
 ref=u1.replace(' u1 (',' u0 (')
 ref=re.sub(r'(\w+)_1\b',r'\1_0',ref)
 ref=ref.replace('.AUD(U1_AUD)', '.AUD(U1_AUD)')
 s=re.sub(r'    ot_qfd_tt_ctlm_i #\([^\n]*\) u0 \(.*?\);',lambda _:ref,s,flags=re.S)
sp=u1.replace('ot_qfd_tt_ctlm_i #','ot_qfd_tt_ctlm_split #',1).replace('.clk(clk)','.ck_head(clk), .ck_tree(clk)')
s=s.replace(u1,sp)
if sys.argv[2] in ('strict','strict_argmax'):
 s=s.replace('if (TXN == 0 && (out_mismatch || pq_mismatch))', 'if (out_mismatch || pq_mismatch)')
s=s.replace('u1.u_ctrl_me','u1.u_head.u_ctrl_me').replace('u1.prog_q','u1.u_head.prog_q')
if sys.argv[2]=='power':
 monitor='''
    integer p_edges0=0,p_edges1=0,p_idle0=0,p_idle1=0,p_idleclk0=0,p_idleclk1=0,p_cycles=0;
    always @(posedge clk) if(rst_n) begin
        p_cycles=p_cycles+1;
        if(me_clk_en_0) p_edges0=p_edges0+1;
        if(u1.u_tree.local_en) p_edges1=p_edges1+1;
        if(u0.u_ctrl_me.me_idle && !u0.u_ctrl_me.me_go && !u0.u_ctrl_me.me_wake) begin
            p_idle0=p_idle0+1;if(me_clk_en_0) p_idleclk0=p_idleclk0+1;end
        if(u1.u_head.u_ctrl_me.me_idle && !u1.u_head.u_ctrl_me.me_go && !u1.u_head.u_ctrl_me.me_wake) begin
            p_idle1=p_idle1+1;if(u1.u_tree.local_en) p_idleclk1=p_idleclk1+1;end
    end
    final $display("CLOCK_ACTIVITY cycles=%0d native_clock_edges=%0d split_clock_edges=%0d native_idle_cycles=%0d split_idle_cycles=%0d native_idle_clock_edges=%0d split_idle_clock_edges=%0d",p_cycles,p_edges0,p_edges1,p_idle0,p_idle1,p_idleclk0,p_idleclk1);
'''
 s=s.rsplit('endmodule',1)[0]+monitor+'endmodule\n'
Path(sys.argv[1]).write_text(s)
PY
L=$(sed -n 's/^L="\(.*\)"/\1/p' rtl/test/run_tt_ctlm_i_lockstep.sh | sed 's#rtl/test/tb_qfd_tt_ctlm_i_psram.sv##')
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
D=""; [ "$MUT" = mut ] && D="-DOT_TT_SPLIT_MUT"
case "$MODE" in
 strict) CV="-GNCYC=60000 -GPCOV=1 -GCOVMASK=16254821 -GMINEV=3 -GTXN=1 -GDBGTX=0" ;;
 argmax|strict_argmax) CV="-GNCYC=20000 -GCOVMASK=2 -GMINEV=5 -GTXN=1" ;;
 *) CV="-GNCYC=60000 -GPCOV=1 -GCOVMASK=16254821 -GMINEV=3 -GTXN=1" ;;
esac
"$V" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -CFLAGS -O1 --x-assign fast --x-initial fast \
 +define+OT_ICUT_NONFATAL --top-module tb_qfd_tt_ctlm_i_psram $CV -GMINRD=200 -GSEED=1 -GU1_HQ2=1 -GU1_RRG=1 -GU1_PCUT=1 \
 -GMOK=1 -GPFMASK=1 -GU1_AUD=33975 -GU1_MEREG=3 -GTBG=3072 $D --Mdir "$OUT/obj" "$OUT/tb.sv" \
 rtl/physical/ot_qfd_tt_ctlm_split.sv $L > "$OUT/build.log" 2>&1 || { grep -m5 '%Error' "$OUT/build.log"; echo "FAIL tt_ctlm_split build"; exit 1; }
"$OUT/obj/Vtb_qfd_tt_ctlm_i_psram" > "$OUT/run.log" 2>&1
RLINE=$(grep -E '^(PASS|FAIL) tt_ctlm_i_psram' "$OUT/run.log" | tail -1)
case "$RLINE" in
 PASS*) echo "PASS tt_ctlm_split $MODE $RLINE"; grep -E '^(TXN (events|STREAMS)|CLOCK_ACTIVITY)' "$OUT/run.log"; exit 0 ;;
 *) head -12 "$OUT/run.log"; echo "FAIL tt_ctlm_split $MODE ${MUT:-} $RLINE"; exit 1 ;;
esac
