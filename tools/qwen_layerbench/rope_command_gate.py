#!/usr/bin/env python3
"""Build a literal calendar-relocation -> actual native RP1 write-pin gate.

This does not replace CROM, execute arithmetic or qualify a full calendar.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from table_command_gate import cut


def native_module(text, name):
    match = re.search(r'^module\s+' + re.escape(name) + r'\b.*?\bendmodule\b', text, re.M | re.S)
    if not match:
        raise ValueError('missing native module: ' + name)
    return match.group(0) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    sources = [
        ('rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv', ['qfd_dv_s5_rst2']),
        ('rtl/qwen_dv/s5/s8/qfd_dv_s8_kept.sv', ['qfd_s8k_rp_wbit', 'qfd_s8k_rp_wgrp']),
        ('rtl/qwen_dv/s5/s8/qfd_dv_s8_rp1.sv', ['qfd_dv_s8_rp1']),
    ]
    parts, identity = [], {}
    for path, modules in sources:
        text = subprocess.check_output(['git', '-C', str(a.repo), 'show', 'HEAD:' + path], text=True)
        identity[path] = dict(file_sha256=hashlib.sha256(text.encode()).hexdigest(), modules={})
        for name in modules:
            body = native_module(text, name)
            parts.append(body)
            identity[path]['modules'][name] = hashlib.sha256(body.encode()).hexdigest()
    calendar = a.repo / 'rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv'
    parts.append(cut(calendar.read_text(), 'candidate'))
    (a.out / 'native.sv').write_text('`timescale 1ns/1fs\n' + '\n'.join(parts))
    (a.out / 'tb.sv').write_text('''`timescale 1ns/1fs
module tb;
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0;reg[115:0]ic=0;reg[1:0]ru=0;reg[1037:0]chd=0;
wire[115:0]fixed_cmd,old_cmd,cmd,ctl_cmd;
wire fixed_bad,old_bad;wire[1037:0]ctl_chd;
wire we,fault;wire[1:0]kind;wire[23:0]addr;wire[1023:0]data;
integer drop_base=0,corrupt_payload=0,corrupt_beat=0;
candidate #(.TABLE_USER_RELOC(1)) reloc(ic,ru,fixed_cmd,fixed_bad);
candidate #(.TABLE_USER_RELOC(0)) before_reloc(ic,ru,old_cmd,old_bad);
assign cmd=drop_base?old_cmd:fixed_cmd;
qfd_dv_s8_rp1 dut(.ck(ck),.rst_n(rst_n),.cmd_q(cmd),.chd_q(chd),
 .tw_we(1'b0),.tw_kind(2'd0),.tw_addr(24'd0),.tw_data(1024'd0),
 .ctl_cmd(ctl_cmd),.ctl_chd(ctl_chd),.vtw_we(we),.vtw_kind(kind),
 .vtw_addr(addr),.vtw_data(data),.fault(fault),.w519_cp(89'd0),.w518_cp(89'd0));
integer u,b,j,writes=0;reg[511:0]payload;reg[23:0]want_addr;
task set_id;
begin ic=116'd15;@(negedge ck);ic=0;@(negedge ck);end
endtask
task arm(input integer user_index);
begin ru=2'(user_index);ic=(116'd64<<6)|116'd17;#0.000001;
 if(fixed_bad)$fatal(1,"VALID_ROPE_REJECTED");
 @(negedge ck);ic=0;@(negedge ck);end
endtask
task beat(input integer user_index,input integer k);
begin
 payload=0;for(j=0;j<16;j=j+1)payload[32*j+:32]=32'h3f800000+32'(user_index*4096+k*16+j);
 chd=0;chd[519]=1;chd[518]=1;chd[514:512]=3'(k);chd[511:0]=payload;
 if(corrupt_payload && user_index==1 && k==3)chd[0]=~chd[0];
 if(corrupt_beat && user_index==1 && k==3)chd[512]=~chd[512];
 #0.000001;
 want_addr=24'd2048+24'((k&1)*1024+64+128*user_index+(k>>1));
 if(!we||kind!=1||addr!==want_addr||data!=={payload,payload}||fault)
  $fatal(1,"ROPE_NATIVE_MISMATCH user%0d beat%0d addr%0d want%0d fault%b",user_index,k,addr,want_addr,fault);
 writes=writes+1;@(negedge ck);chd=0;
end
endtask
initial begin
 drop_base=$test$plusargs("MUT_NO_RELOC");corrupt_payload=$test$plusargs("MUT_PAYLOAD");corrupt_beat=$test$plusargs("MUT_BEAT");
 repeat(4)@(negedge ck);rst_n=1;repeat(8)@(negedge ck);set_id;
 for(u=0;u<4;u=u+1)begin
  arm(u);for(b=0;b<8;b=b+1)beat(u,b);
  if(we||fault)$fatal(1,"ROPE_EXTRA_WRITE_OR_FAULT");
 end
 // A partially received epoch is cancelled by the actual native reset logic.
 arm(2);beat(2,0);beat(2,1);rst_n=0;#0.000001;
 if(we||fault)$fatal(1,"ROPE_RESET_NOT_FLUSHED");
 repeat(4)@(negedge ck);rst_n=1;repeat(8)@(negedge ck);set_id;
 arm(2);for(b=0;b<8;b=b+1)beat(2,b);
 if(we||fault)$fatal(1,"ROPE_RESET_REPLAY_FAILED");
 $display("ROPE_NATIVE_PASS users4 writes%0d rows4peruser bank2 warmreset1 period833ps",writes);$finish;
end
endmodule
''')
    (a.out / 'source.json').write_text(json.dumps(dict(native=identity,
        calendar_sha256=hashlib.sha256(calendar.read_bytes()).hexdigest(),
        scope='Literal relocation plus native RP1 write pins only; no CROM/arithmetic/calendar scheduling qualification'), indent=2) + '\n')


if __name__ == '__main__':
    main()
