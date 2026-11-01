#!/usr/bin/env python3
"""Generate a literal native combinational command-relocation gate.

The old and candidate blocks are extracted byte-for-byte from the real calendar
module. This proves that local mechanism, not complete calendar scheduling or STA.
"""
import argparse
from pathlib import Path
import subprocess
import dv_lower as D


def cut(source, name):
    start=source.index('    wire [24:0]   ub =')
    body=source[start:source.index('    generate if',start)]
    return f'''module {name} #(parameter NU=4,UB=2,MUT=0,UFOLD=1,UVM_STRIDE=4096,
PIDX_STRIDE=128,UTAG_LSB=6,TABLE_USER_RELOC=0,BTAB_COMPACT=1)
(input [115:0] ic,input [1:0] ru,output [115:0] result,output bad);
wire [2:0] i_kind=ic[3:1];wire i_loc=ic[115:112]==14;
{body}
assign result=rc;assign bad=r_bad;
endmodule\n'''


def replace(word,lo,width,value):
    return (word & ~(((1<<width)-1)<<lo)) | (value<<lo)


def expected(command,user):
    kind=(command>>1)&7
    if command>>112==14:
        return command,0
    out,bad=command,0
    if kind==0:
        sub=(command>>4)&3
        if sub==0:
            bad=int(((command>>29)&3)!=0)
            out=replace(out,29,2,user)
        elif sub==1:
            base=(command>>6)&1023
            relocated=base+user*128
            out=replace(out,6,10,relocated&1023)
            bad=int(base>124 or relocated>=1024)
    elif kind==2:
        sb=(command>>15)&511
        if command & (1<<24):
            out=replace(out,26,24,((command>>26)&0xffffff)+user*4096)
        out=replace(out,51,2,user)
        offset=(0,272,344,416)[user] if sb<72 else 0
        out=replace(out,15,9,sb+offset)
        bad=int(sb>=272)
    elif kind==3:
        for lo in (11,36):
            address=(command>>lo)&0xffffff
            out=replace(out,lo,24,address+user*4096)
            bad |= int(address>=4096)
    return out,bad


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',type=Path,required=True)
    ap.add_argument('--before',required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    path='rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv'
    old=subprocess.check_output(['git','-C',str(a.repo),'show',f'{a.before}:{path}'],text=True)
    new=(a.repo/path).read_text()
    (a.out/'cuts.sv').write_text(cut(old,'original')+cut(new,'candidate'))
    commands=[D.cmd_root(dst,1,32,ss,fuse=1,rx=rx,eps=897988541,k=12)
              for dst in (0,7) for ss,rx in ((384,400),(4096,400),(384,4096))]
    commands += [D.cmd_stn(dst,1,0,8,sb,sdst,416,kc=2)
                 for dst in (0,5) for sb in (0,8,32,48,64,72,128,264,272,511) for sdst in (1,2)]
    commands += [(dst<<112)|(base<<6)|(1<<4)|1
                 for dst in (0,7,15) for base in (0,64,71,120,124,125,127,128,640,1023)]
    commands += [replace(c,112,4,14) for c in list(commands)]
    lines=[]
    for user in range(4):
        for command in commands:
            value,bad=expected(command,user)
            lines.append(f"drive(2'd{user},116'h{command:029x},116'h{value:029x},1'b{bad});")
    tb='''`timescale 1ns/1ps
module tb;
reg [115:0] ic=0;reg[1:0] ru=0;wire[115:0] old_rc,off_rc,new_rc,wrong_rc,drop_rc;wire old_bad,off_bad,new_bad,wrong_bad,drop_bad;
original base(ic,ru,old_rc,old_bad);
candidate #(.TABLE_USER_RELOC(0)) off_dut(ic,ru,off_rc,off_bad);
candidate #(.TABLE_USER_RELOC(1)) fixed_dut(ic,ru,new_rc,new_bad);
candidate #(.TABLE_USER_RELOC(1),.BTAB_COMPACT(0)) wrong(ic,ru,wrong_rc,wrong_bad);
candidate #(.TABLE_USER_RELOC(1),.MUT(12)) dropped(ic,ru,drop_rc,drop_bad);
integer n=0,checks=0,caught=0,rope_caught=0;
task drive(input[1:0]u,input[115:0]cmd,input[115:0]want,input bad);
begin ru=u;ic=cmd;#1;
if({off_bad,off_rc}!=={old_bad,old_rc})$fatal(1,"default changed");
if({new_bad,new_rc}!=={bad,want})$fatal(1,"native bank mismatch u%0d kind%0d got%h/%b want%h/%b",u,cmd[3:1],new_rc,new_bad,want,bad);
if({wrong_bad,wrong_rc}!=={bad,want})caught=caught+1;
if(cmd[115:112]!=14 && cmd[3:1]==0 && cmd[5:4]==1 && !bad && {drop_bad,drop_rc}!=={bad,want})rope_caught=rope_caught+1;
checks=checks+1;end endtask
initial begin
'''+ '\n'.join(lines)+'''
for(n=0;n<4096;n=n+1)begin ru=n%4;ic={$urandom,$urandom,$urandom,$urandom};#1;
if({off_bad,off_rc}!=={old_bad,old_rc})$fatal(1,"random default changed");end
if(caught==0)$fatal(1,"wrong compact bank not caught");
if(rope_caught==0)$fatal(1,"dropped ROPE bank not caught");
$display("PASS native command vectors=%0d random_default=4096 wrong_compact_caught=%0d dropped_rope_caught=%0d",checks,caught,rope_caught);$finish;
end
endmodule
'''
    (a.out/'tb.sv').write_text(tb)


if __name__=='__main__':main()
