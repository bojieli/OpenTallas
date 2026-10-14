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
if sys.argv[2] in ('strict','strict_argmax','strict_fault','power'):
 ref=u1.replace(' u1 (',' u0 (')
 ref=re.sub(r'(\w+)_1\b',r'\1_0',ref)
 ref=ref.replace('.AUD(U1_AUD)', '.AUD(U1_AUD)')
 s=re.sub(r'    ot_qfd_tt_ctlm_i #\([^\n]*\) u0 \(.*?\);',lambda _:ref,s,flags=re.S)
sp=u1.replace('ot_qfd_tt_ctlm_i #','ot_qfd_tt_ctlm_split #',1).replace('.clk(clk)','.ck_head(clk), .ck_tree(clk)')
s=s.replace(u1,sp)
if sys.argv[2] in ('strict','strict_argmax','strict_fault'):
 s=s.replace('if (TXN == 0 && (out_mismatch || pq_mismatch))', 'if (out_mismatch || pq_mismatch)')
s=s.replace('u1.u_ctrl_me','u1.u_head.u_ctrl_me').replace('u1.prog_q','u1.u_head.prog_q')
if sys.argv[2] in ('strict','strict_argmax','strict_fault','power'):
 monitor = """
    integer station_checks=0, enable_checks=0;
    always @(negedge clk) if(rst_n) begin
        enable_checks=enable_checks+1;
        if(u1.u_head.me_clk_en !== u1.u_tree.local_en) $fatal(1,"native pre-edge enable mismatch");
        station_checks=station_checks+1;
        if({u1.u_head.c_me_ready,u1.u_head.c_me_idle,u1.u_head.c_me_wrom_re,u1.u_head.c_me_wrom_addr,u1.u_head.c_me_am_idx,u1.u_head.c_me_am_val,u1.u_head.c_me_am_any,u1.u_head.c_me_progress,u1.u_head.c_me_fault} !==
           {u1.u_tree.u_shadow.c_me_ready,u1.u_tree.u_shadow.c_me_idle,u1.u_tree.u_shadow.c_me_wrom_re,u1.u_tree.u_shadow.c_me_wrom_addr,u1.u_tree.u_shadow.c_me_am_idx,u1.u_tree.u_shadow.c_me_am_val,u1.u_tree.u_shadow.c_me_am_any,u1.u_tree.u_shadow.c_me_progress,u1.u_tree.u_shadow.c_me_fault}) $fatal(1,"native return station epoch mismatch");
    end
    final $display("NATIVE_STATION_PROOF enable_checks=%0d station_checks=%0d",enable_checks,station_checks);
"""
 s=s.rsplit('endmodule',1)[0]+monitor+'endmodule\n'
if sys.argv[2]=='strict_fault':
 s=re.sub(r"\.fab_fault\(\(TXN != 0\) \? 1'b0 : \w+\)", '.fab_fault(fab_fault)',s)
 s=s.replace('up_fault = 0; tr_fault = 0; p_fault = 0; fab_fault = 0;', 'up_fault = 0; tr_fault = 0; p_fault = 0; fab_fault = (i % TW) == 50;')
 monitor="""
    integer fault_checks=0;
    always @(negedge clk) if(rst_n && c_fault_0 != 0) fault_checks=fault_checks+1;
    final begin
        $display("FAULT_PROOF active_fault_checks=%0d",fault_checks);
        if(fault_checks==0) $fatal(1,"fault proof vacuous");
    end
"""
 s=s.rsplit('endmodule',1)[0]+monitor+'endmodule\n'
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
 strict_fault) CV="-GNCYC=60000 -GPCOV=1 -GCOVMASK=0 -GMINEV=0 -GTXN=1 -GDBGTX=0" ;;
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
 PASS*) echo "PASS tt_ctlm_split $MODE $RLINE"; grep -E '^(TXN (events|STREAMS)|CLOCK_ACTIVITY|NATIVE_STATION_PROOF|FAULT_PROOF)' "$OUT/run.log"; exit 0 ;;
 *) head -12 "$OUT/run.log"; echo "FAIL tt_ctlm_split $MODE ${MUT:-} $RLINE"; exit 1 ;;
esac
