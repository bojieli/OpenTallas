#!/usr/bin/env python3
"""Default-off h9 r0 p2 relay-depth proposal; every changed interface needs a fresh native calendar."""
import argparse
import json
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from frame_colrelay_depth import instances


def transform(text):
    matches=list(re.finditer(r'(^module col_h9_l4_lp_r0 #\(.*?^endmodule)',text,re.M|re.S))
    if len(matches)!=1:raise ValueError('need exactly one col_h9_l4_lp_r0')
    m=matches[0];block=m[1]
    if 'COLRELAY_H9P2' in block:raise ValueError('already transformed')
    block=block.replace('parameter integer MUT = 0,','parameter integer MUT = 0,\n    parameter integer COLRELAY_H9P2 = 0,',1)
    if 'parameter integer COLRELAY_H9P2' not in block:raise ValueError('missing parameter anchor')
    ins=instances(block);lines=block.splitlines();tails=[];ledger=[]
    specs=[('u_lpl_6_w','q',283),('u_lpl_7_w','q',266),('u_lpl_8_w','q',15),('u_y_so_1_0','o',2)]+[(f'u_y_xo{i}_1','o',276) for i in range(4)]
    for inst,pin,width in specs:
        if inst not in ins:raise ValueError('missing '+inst)
        row,mod,c=ins[inst];orig=c[pin];stem='h9p2_'+inst[2:];raw=stem+'_raw';out=stem+'_extra'
        if not re.fullmatch(r'\w+|\{[^{}]+\}',orig):raise ValueError('unsupported output '+inst)
        anchor=f'.{pin}({orig})'
        if lines[row].count(anchor)!=1:raise ValueError('ambiguous output '+inst)
        lines[row]=lines[row].replace(anchor,f'.{pin}({raw})',1)
        tails.extend([f'    wire [{width-1}:0] {raw};',f'    wire [{width-1}:0] {out};',f'    generate if (COLRELAY_H9P2) begin : g_{stem}'])
        if mod=='ot_pl_seam_w_plr':
            rsreg=re.search(r'\.RSREG\((\d+)\)',lines[row])
            if not rsreg:raise ValueError('missing RSREG '+inst)
            # Repeat the writer's per-chunk asynchronous clear and original reset-release control.
            tails.append(f'    ot_pl_seam_w_plr #(.W({width}), .CHUNK_BITS(24), .RSREG({rsreg[1]})) u_lpl_{stem}_extra (.ck({c["ck"]}), .rsi({c["rsi"]}), .rse({c["rse"]}), .ir({raw}), .q({out}));')
        else:
            if 'ck' not in c or 'rs' not in c:raise ValueError('missing clock/reset '+inst)
            tails.append(f'    ot_s81_rly #(.W({width}), .RSREG(1)) u_y_{stem}_extra (.ck({c["ck"]}), .rs({c["rs"]}), .i({raw}), .o({out}));')
        tails.extend([f'    end else begin : g_{stem}_off',f"    assign {out} = {{{width}{{1'b0}}}};",'    end endgenerate',f'    assign {orig} = COLRELAY_H9P2 ? {out} : {raw};'])
        ledger.append(dict(group=inst,width=width,added_cycles=1,added_data_ff=width,reset_basis='original per-chunk writer clear' if mod=='ot_pl_seam_w_plr' else 'original source reset leaf'))
    lines.insert(len(lines)-1,'\n'.join(tails));output=text[:m.start()]+'\n'.join(lines)+text[m.end():]
    return output,dict(schema='opentallas.s81.colrelay_h9p2.v1',default='COLRELAY_H9P2=0 retains original data/control/clock/reset cycle behavior',select='contents.u_r0.params.COLRELAY_H9P2=1 only on measured h9r0p2 cohort',groups=ledger,added_data_ff=sum(x['added_data_ff'] for x in ledger),xo_coherence='all four276b chunks delayed onecycle including geometricallyunneededxo1',status='SOURCE_PROPOSAL_NOT_ADOPTED: nativeinterface/calendar/fullshape/throughput gates pending')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--from',dest='src',required=True);ap.add_argument('--out',required=True);ap.add_argument('--report',required=True);a=ap.parse_args()
    out,r=transform(Path(a.src).read_text());Path(a.out).write_text(out);Path(a.report).write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
