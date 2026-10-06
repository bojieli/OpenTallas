#!/usr/bin/env python3
"""Emit additive selected-source finite-VM binding. Original sources unchanged.
No build/inference; exact snapshot anchors and HEAD PC2 bytes are mandatory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from hdc_isa import decode

ROOT=Path(__file__).resolve().parents[1]
BOOK=ROOT/'results/rtl/qwen_hbm_activation_vm_realization_20261005'


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('selected-source binding anchor: '+old)
    return text.replace(old,new,1)


def emit(out):
    top_path=ROOT/'results/rtl/qwen_hbm_activation_vm_inventory_20261005/selected_source/ot_qwen_hbmacc_rt_die_w12.sv'
    core_path=BOOK/'inputs/ot_qwen_rom_core.sv'
    top=top_path.read_text();core=core_path.read_text()
    assert hashlib.sha256(top_path.read_bytes()).hexdigest()=='761799736039b1345140b7d2da2634829baf3adfe4be49477c04af3e815f4618'
    pins=json.loads((BOOK/'inputs/source_pins.json').read_text())
    assert hashlib.sha256(core_path.read_bytes()).hexdigest()==next(p['sha256'] for p in pins if p['path'].endswith('/ot_qwen_rom_core.sv'))
    words=[(BOOK/f'inputs/head-d{r}/program.hex').read_text().splitlines()[2] for r in range(4)]
    assert len(set(words))==1
    d=decode(int(words[0],16));assert d['unit']==2 and d['dst']==1 and d['d_base']==8192 and d['su_nin']==4096
    # Core's existing public result ports are qualified by ME enable. The
    # adapter must reserve/ACK their immutable raw payload while the clock is
    # held. Only the additive finite successor exposes raw held strobes.
    core=once(core,'module ot_qwen_rom_core #(','module ot_qwen_rom_core_finite_vm #(')
    core=once(core,'parameter integer W    = 16,','parameter integer FINITE_VM_RAW = 0,\n    parameter integer W    = 16,')
    core=once(core,'assign vw_me_we = me_o_we & {(G >> SMIN){me_en}};',
              'assign vw_me_we = me_o_we & {(G >> SMIN){FINITE_VM_RAW != 0 || me_en}};')
    core=once(core,'assign vw_mx_we = me_mx_we & me_en;',
              'assign vw_mx_we = me_mx_we & (FINITE_VM_RAW != 0 || me_en);')
    top=once(top,'module ot_qwen_hbmacc_rt_die_w12 #(', 'module ot_qwen_hbmacc_rt_die_w12_finite_vm #(')
    start=top.index('parameter integer ')
    top=top[:start]+'parameter integer FINITE_VM = 0,\n    parameter integer FINITE_HEAD_CACHE = 0,\n    '+top[start:]
    top=once(top,'ot_qwen_rom_core #(', 'ot_qwen_rom_core_finite_vm #(.FINITE_VM_RAW(FINITE_VM),')
    # Two source participants advance together; HBM arrivals/cmax/stats retain
    # their original master clock, while consumption uses qualified me_clk_en.
    top=once(top,'.clk(clk),.rst_n(rst_n),.start(core_start)', '.clk(vm_native_clk),.rst_n(rst_n),.start(core_start)')
    top=once(top,'.clk(clk),.rst_n(rst_n),.start(start | h_start)', '.clk(vm_native_clk),.rst_n(rst_n),.start(start | h_start)')
    top=once(top,'.me_mem_ok(hb_me_ok),.me_clk_en(me_clk_en)',
             '.me_mem_ok(hb_me_ok && (!FINITE_VM || vm_me_lease)),.me_clk_en(vm_original_me_en)')
    for name,off,size in [('va_q',0,2048),('vb_q',2048,2048),('vc_q',4096,2048),('vx_q',6144,65536)]:
        top=once(top,f'.{name}({name})', f'.{name}(FINITE_VM ? vm_read_q[{off} +: {size}] : {name})')
    top=once(top,'.vm_rq(s_vrq)', '.vm_rq(FINITE_VM ? vm_read_q[71680 +: 512] : s_vrq)')
    top=once(top,'.fault(s_fault),.coll_busy(coll_busy)', '.fault(vm_seq_fault),.coll_busy(coll_busy)')
    # Fingerprint actual immutable PC2 decoded control, not catalogue addresses
    # or a host-generated normalizer. Bound only with selected HEAD_CACHE mode.
    fields=['su_nout','su_nin','a_src','a_base','a_so','a_si','b_src','b_base','b_so','b_si',
            'c_src','c_base','c_so','c_si','ma','mb','ad','sfu','mc','md','dst','d_base','d_so','d_si','red','r_base','r_so','red_sq','imm1','imm2']
    # *_src are decoded a_src/b_src/c_src in this selected core.
    aliases={'red_sq':'redsq'}
    checks=' &&\n        '.join(f'core.{aliases.get(k,k)} == {d[k]}' for k in fields)
    glue='''
    // Default-off native bank binding; no new program/owner ABI.
    wire vm_native_tick,vm_me_lease,vm_drained,vm_fault;
    wire vm_seq_fault;
    assign s_fault = vm_seq_fault || (FINITE_VM && vm_fault);
    wire vm_native_clk,vm_original_me_en;
    wire vm_me_intent = hb_me_ok && ((ME_IDLE_GATE==0) || !core.me_idle || core.me_wake);
    assign me_clk_en = vm_original_me_en && (!FINITE_VM || vm_native_tick);
    generate if(FINITE_VM)begin:g_vm_clock
        ot_hdc_cg u_native_cg(.clk(clk),.en(!rst_n || vm_native_tick),.gclk(vm_native_clk));
    end else begin:g_original_clock
        assign vm_native_clk=clk;
    end endgenerate
    reg [2255:0] vm_ren;
    reg [54143:0] vm_raddr;
    wire [72191:0] vm_read_q;
    reg [1632:0] vm_wen;
    reg [39191:0] vm_waddr;
    reg [52255:0] vm_wdata;
    wire vm_actual_head_producer = FINITE_HEAD_CACHE && core.su_go &&
        CHECKS;
    always @*begin
        vm_ren=0;vm_raddr=0;vm_wen=0;vm_waddr=0;vm_wdata=0;
        for(integer k=0;k<64;k=k+1)begin
            vm_ren[k]=va_re[k];vm_raddr[k*24+:24]=va_addr[k*24+:24];
            vm_ren[64+k]=vb_re[k];vm_raddr[(64+k)*24+:24]=vb_addr[k*24+:24];
            vm_ren[128+k]=vc_re[k];vm_raddr[(128+k)*24+:24]=vc_addr[k*24+:24];
        end
        for(integer k=0;k<2048;k=k+1)begin
            vm_ren[192+k]=vx_re[k] && vm_me_intent;
            vm_raddr[(192+k)*24+:24]=vx_addr[k*24+:24];
        end
        for(integer k=0;k<16;k=k+1)begin
            vm_ren[2240+k]=s_vre;vm_raddr[(2240+k)*24+:24]=({16'b0,s_vraddr}<<4)+k;
        end
        for(integer g=0;g<96;g=g+1)for(integer k=0;k<16;k=k+1)begin
            vm_wen[g*16+k]=vw_me_we[g] && vw_me_mask[g*16+k] && vm_me_intent;
            vm_waddr[(g*16+k)*24+:24]=(vw_me_addr[g*24+:24]<<4)+k;
            vm_wdata[(g*16+k)*32+:32]=vw_me_data[(g*16+k)*32+:32];
        end
        for(integer k=0;k<16;k=k+1)begin
            vm_wen[1536+k]=vw_mx_we && vw_mx_mask[k] && vm_me_intent;
            vm_waddr[(1536+k)*24+:24]=(vw_mx_addr<<4)+k;
            vm_wdata[(1536+k)*32+:32]=vw_mx_data[k*32+:32];
        end
        for(integer k=0;k<64;k=k+1)begin
            vm_wen[1552+k]=vw_su_we[k];vm_waddr[(1552+k)*24+:24]=vw_su_addr[k*24+:24];
            vm_wdata[(1552+k)*32+:32]=vw_su_data[k*32+:32];
        end
        vm_wen[1616]=vw_rd_we;vm_waddr[1616*24+:24]=vw_rd_addr;vm_wdata[1616*32+:32]=vw_rd_data;
        for(integer k=0;k<16;k=k+1)begin
            vm_wen[1617+k]=s_vwe;vm_waddr[(1617+k)*24+:24]=(s_vwaddr<<4)+k;
            vm_wdata[(1617+k)*32+:32]=s_vwdata[k*32+:32];
        end
    end
    ot_qwen_finite_vm_adapter #(.ENABLE(FINITE_VM),.HEAD_CACHE(FINITE_HEAD_CACHE)) u_vm_provider(
        .clk(clk),.rst_n(rst_n),.source_me_wanted(vm_me_intent),
        .head_source_producer_go(vm_actual_head_producer),
        .read_en(vm_ren),.read_addr(vm_raddr),.read_q(vm_read_q),
        .write_en(vm_wen),.write_addr(vm_waddr),.write_data(vm_wdata),
        .native_tick(vm_native_tick),.native_me_lease(vm_me_lease),.drained(vm_drained),.fault(vm_fault),
        .native_epoch(),.physical_reads(),.physical_writes(),.physical_ACKs(),.held_edges(),
        .head_fill_reads(),.head_hit_edges());
    initial if(FINITE_VM && (G!=6144 || SMIN!=6 || SMAX!=11 || SW!=64 || XVM!=1))
        $fatal(1,"finite VM selected source geometry mismatch");
'''.replace('CHECKS',checks)
    top=once(top,'    localparam integer W=16, AW=24, PAW=12, DAW=6, FW=512;', glue+'\n    localparam integer W=16, AW=24, PAW=12, DAW=6, FW=512;')
    out.mkdir(parents=True,exist_ok=True)
    files={'ot_qwen_hbmacc_rt_die_w12_finite_vm.sv':top,'ot_qwen_rom_core_finite_vm.sv':core}
    for name,text in files.items():(out/name).write_text(text)
    book=dict(default_off=True,head_program_PC2_sha256=hashlib.sha256(words[0].encode()).hexdigest(),
              sources={str(top_path):hashlib.sha256(top_path.read_bytes()).hexdigest(),str(core_path):hashlib.sha256(core_path.read_bytes()).hexdigest()},
              emitted={name:hashlib.sha256(text.encode()).hexdigest() for name,text in files.items()},
              runtime_rule='Native callback/capture and collective peers must use immutable PRE-edge vm_native_tick and qualified me_clk_en; weights HBM controller remains original clock. Full-token enrollment refused without actual joint participant admission.',
              backend='full16 DS masked-visible-r2 + CAP1 checked SRAM sidecar/RMW/postverify',
              mutable_frame_protection_complete=False,
              remaining_integration=['W6 protection/held codec timing of remaining output/XVM/cache/control state before physical admission',
                'actual joint collective admission before full-token enrollment',
                'source-owned initial VM provisioning before native start'],
              adopted=False)
    (out/'binding.json').write_text(json.dumps(book,indent=2)+'\n')
    return book


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(emit(a.out)))
