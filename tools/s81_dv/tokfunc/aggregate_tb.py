#!/usr/bin/env python3
"""Generate instrumentation for the one actual local-ri_e aggregate cone.

Every named die root has an explicit component-only period/phase. Forwarded
clocks remain driven by the actual cone. This is not a physical phase receipt.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--local-cone',type=Path,required=True)
    p.add_argument('--inventory',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    P=json.loads((a.local_cone/'cut/slice_ports.json').read_text())['ports']
    inv=json.loads(a.inventory.read_text());frames=[n for n in inv['selected_instances'] if n.startswith('u_f_')]
    assert len(frames)==6
    s='dut.u_s_0N.u_sl';xs=s+'.u_xg.u_s';cap=s+'.u_cap'
    v=['`timescale 1ns/1ps','module tb_s0N_aggregate;',
       'reg tick=0;always #0.5 tick=~tick;reg rst_n=1;integer cyc=-1,T=5000,mut=0;',
       'integer bad=0,nraw=0,nctl=0,ngather=0,nis=0,ncfg=0,ngw=0,ntable=0,nmw=0,ncap=0;',
       'reg[95:0]seen=0,previous_table=0;reg[1103:0]packet[0:255];integer at[0:255];integer nev=0,ep=0;',
       'reg[1103:0]drive=0;reg[531:0]source_q[0:79];string dir;integer fd,rc,i,j,k,t;reg[1103:0]word;',
       'integer cfgs[0:5],gos[0:5],rets[0:5];real release_t;']
    roots={}
    for name,port in P.items():
        if port['dir']=='input' and port.get('kind')=='clock':
            sources=port.get('clock_from') or [port['net']]
            assert len(sources)==1,('ambiguous forwarded clock boundary',name,sources)
            roots.setdefault(sources[0],f'root_{len(roots)}')
    for source,root in roots.items():
        v.append(f'reg {root}=0;always #0.5 {root}=~{root}; // actual root {source}, explicit component phase0 period1ns')
    conns=[]
    for name,port in P.items():
        width=port['width'];lo=port['lo'];rng=f'[{lo+width-1}:{lo}]' if width>1 or lo else ''
        if port['dir']=='input':
            if port.get('kind')=='clock':
                sources=port.get('clock_from') or [port['net']]
                v.append(f'wire {rng} {name}={{{width}{{{roots[sources[0]]}}}}};')
            elif port['net']=='rst_n':v.append(f'wire {rng} {name}=rst_n;')
            elif name in [f'i__w_xrW_0N_l{k}_lnd' for k in range(4)]:
                lane=int(re.fullmatch(r'i__w_xrW_0N_l([0-3])_lnd',name)[1]);v.append(f'wire {rng} {name}=drive[{276*lane}+:276];')
            else:v.append(f'reg {rng} {name}=0;')
        else:v.append(f'wire {rng} {name};')
        conns.append(f'.{name}({name})')
    v.append('s0N_aggregate dut('+','.join(conns)+');')
    faults=[]
    for name,port in P.items():
        if port['dir']=='output' and 'fault' in port['net']:
            for hi,lo in port['bits']:
                faults.append(f'(|{name}[{hi}:{lo}])' if port['width']>1 or port['lo'] else f'(|{name})')
    v += ['initial begin',
          'if(!$value$plusargs("DIR=%s",dir))$fatal(1,"NO_REPLAY_DIR");',
          'void\'($value$plusargs("T=%d",T));void\'($value$plusargs("MUT=%d",mut));',
          'for(i=0;i<6;i=i+1)begin cfgs[i]=0;gos[i]=0;rets[i]=0;end',
          'for(i=0;i<80;i=i+1)source_q[i]=0;',
          'fd=$fopen({dir,"/ri_e_packets.txt"},"r");if(!fd)$fatal(1,"NO_PACKETS");',
          'while(!$feof(fd))begin rc=$fscanf(fd,"%d %h\\n",t,word);if(rc==2)begin',
          'at[nev]=t;packet[nev]=word;nev++;if(word[3:1]==1)source_q[word[20:13]]=word[21+:532];end end',
          '$fclose(fd);if(nev!=86)$fatal(1,"BAD_PACKET_COUNT");',
          '#0.1 rst_n=0;repeat(64)@(negedge tick);rst_n=1;release_t=$realtime;',
          '$display("AGG_COMPONENT_EPOCH release_t=%0.3f no_global_epoch=1",release_t);',
          '#(T+1);',
          f'if(ep!=nev||nraw!=80||nctl!=6||ngather!=80||nis!=5||ncfg!=1||ngw!=1||ntable!=80||seen!=96\'h0000ffffffffffffffffffff||{xs}.tqv[0]!=96\'h0000ffffffffffffffffffff||ncap!=24)bad++;',
          'for(i=0;i<6;i=i+1)if(cfgs[i]!=1||gos[i]!=1||rets[i]!=12)bad++;',
          '$display("AGG_COUNTS raw=%0d ctl=%0d gather=%0d is=%0d cfg=%0d windows=%0d table=%0d macro=%0d cap=%0d bad=%0d mut=%0d",nraw,nctl,ngather,nis,ncfg,ngw,ntable,nmw,ncap,bad,mut);',
          'for(i=0;i<6;i=i+1)$display("AGG_FRAME_COUNTS frame=%0d cfg=%0d go=%0d ret=%0d",i,cfgs[i],gos[i],rets[i]);',
          'if(bad)$fatal(1,"AGGREGATE_SOURCE_FAIL");$display("AGGREGATE_SOURCE_COUNTS_PASS");$finish;end',
          'always@(posedge tick)if(rst_n)cyc<=cyc+1;',
          'always@(negedge tick)begin drive=0;if(rst_n&&ep<nev&&at[ep]==cyc+1)begin',
          'drive=packet[ep];if(mut==1&&drive[3:1]==1&&drive[20:13]==0)drive=0;ep++;end end',
          f'always@(posedge {s}.ck_C)if(rst_n)begin',
          f'if({s}.ri_e[0])begin if({s}.ri_e[3:1]==1)nraw++;else nctl++;$display("AGG_RAW t=%0.3f data=%0276h",$realtime,{s}.ri_e);end',
          f'if({s}.is_v)begin nis++;$display("AGG_IS t=%0.3f data=%040h",$realtime,{s}.is_d);end',
          f'if({s}.cfg_v)begin ncfg++;$display("AGG_CFG t=%0.3f data=%040h",$realtime,{s}.cfg_d);end',
          f'if({xs}.o_gw[0])begin ngw++;$display("AGG_WINDOW t=%0.3f off=%0d par=%b fam=%b",$realtime,{xs}.off,{xs}.o_gwp[0],{xs}.o_gwf[0]);end',
          'for(j=0;j<3;j=j+1)begin',
          f'if({xs}.g_v[j])begin k={xs}.g_idx[7*j+:7];ngather++;',
          f'if(k>=80||seen[k]||{xs}.g_fam[j])bad++;else begin seen[k]=1;if({xs}.g_d[1024*j+:532]!==source_q[k])bad++;end',
          f'$display("AGG_GATHER t=%0.3f source=%0d idx=%0d fam=%b data=%0133h",$realtime,j,k,{xs}.g_fam[j],{xs}.g_d[1024*j+:532]);end',
          f'for(k=0;k<8;k=k+1)if({xs}.mw_e[j][k])begin nmw++;$display("AGG_MACRO_WRITE t=%0.3f source=%0d bank=%0d address=%0d mask=%064h data=%064h",$realtime,j,k,{xs}.mw_a[j][k],{xs}.mw_m[j][k],{xs}.mw_d[j][k]);end end',
          f'for(j=0;j<96;j=j+1)if({xs}.tqv[0][j]&&!previous_table[j])begin ntable++;$display("AGG_TABLE_WRITE t=%0.3f idx=%0d",$realtime,j);end',
          f'if((previous_table&~{xs}.tqv[0])!=0)begin bad++;$display("AGG_TABLE_DROP t=%0.3f old=%h new=%h",$realtime,previous_table,{xs}.tqv[0]);end previous_table={xs}.tqv[0];',
          f'if({s}.fault||{xs}.fault||dut.u_s_0N.fault)begin bad++;$display("AGG_SOURCE_FAULT t=%0.3f slice=%b xs=%b endpoint=%b",$realtime,{s}.fault,{xs}.fault,dut.u_s_0N.fault);end',
          f'if({s}.xw_v)$display("AGG_XS_WORD t=%0.3f cfg=%b go=%b data=%0276h",$realtime,{s}.xw_d[551],{s}.xw_d[550],{s}.xw_d);end']
    if faults:v.append(f'always@(posedge tick)if(rst_n&&({"|".join(faults)}))begin bad++;$display("AGG_LANDING_FAULT t=%0.3f",$realtime);end')
    for fno,frame in enumerate(frames):
        f='dut.'+frame
        v += [f'always@(posedge {f}.u_cf.cr)if(rst_n)begin',
              f'if({f}.u_cf.cc[1])cfgs[{fno}]++;if({f}.u_cf.cc[0])gos[{fno}]++;',
              f'if(|{f}.u_cf.cc[1:0])$display("AGG_FRAME_CC t=%0.3f frame={frame} cc=%h xk=%b lk=%h",$realtime,{f}.u_cf.cc,{f}.xk,{f}.lk);end',
              f'always@(posedge {f}.u_cf.cr_s)if(rst_n)begin',
              f'if({f}.ret[1])begin rets[{fno}]++;$display("AGG_FRAME_RET t=%0.3f frame={frame} word=%018h",$realtime,{f}.ret);end',
              f'if({f}.ret[69])begin bad++;$display("AGG_FRAME_FAULT t=%0.3f frame={frame}",$realtime);end end']
        landing='dut.ld_r_'+frame[2:]
        assert ('ld_r_'+frame[2:]) in inv['related_transport_instances']
        v += [f'always@(posedge {landing}.ck_f)if(rst_n&&{landing}.i[1])$display("AGG_RETURN_FLIGHT_IN t=%0.3f frame={frame} data=%018h",$realtime,{landing}.i);',
              f'always@(posedge {landing}.ck)if(rst_n&&{landing}.o[1])$display("AGG_RETURN_LANDED t=%0.3f frame={frame} data=%018h",$realtime,{landing}.o);']
    v += [f'always@(posedge {cap}.ck_rt)if(rst_n)begin',
          f'if({cap}.u_rt.cfg_v)$display("AGG_CAP_CFG_LANDED t=%0.3f data=%040h",$realtime,{cap}.u_rt.cfg_d);',
          f'if({cap}.u_rt.w_v)$display("AGG_CAP_RT t=%0.3f face=W tag=%08h data=%08h err=%b fault=%b",$realtime,{cap}.u_rt.w_t,{cap}.u_rt.w_d,{cap}.u_rt.w_e,{cap}.u_rt.w_f);',
          f'if({cap}.u_rt.e_v)$display("AGG_CAP_RT t=%0.3f face=E tag=%08h data=%08h err=%b fault=%b",$realtime,{cap}.u_rt.e_t,{cap}.u_rt.e_d,{cap}.u_rt.e_e,{cap}.u_rt.e_f);end']
    for face,clk,n in [('s','ck_rs',6),('n','ck_rn',4)]:
        v += [f'always@(posedge {cap}.{clk})if(rst_n)begin',
              f'for(integer p=0;p<{n};p=p+1)if({cap}.cw_{face}_v[p])begin ncap++;',
              f'$display("AGG_CAP t=%0.3f face={face.upper()} port=%0d address=%0d data=%08h",$realtime,p,{cap}.cw_{face}_a[12*p+:12],{cap}.cw_{face}_d[32*p+:32]);end end']
    v+=['endmodule']
    path=a.out/'tb_s0N_aggregate.sv';path.write_text('\n'.join(v)+'\n')
    (a.out/'bench.json').write_text(json.dumps(dict(schema='opentallas.s81.aggregate_bench_source.v1',
        bench_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),frames=frames,
        named_root_clocks={source:dict(signal=signal,period_ns=1,phase_ns=0) for source,signal in roots.items()},
        physical_phase_qualified=False,global_epoch_bound=False,local_pin='u_s_0N.ri_e',
        required_checks=['80 raw XQ acceptance','6 CTL','80 distinct gather/data matches','80 actual table writes/no drops',
            'actual macro write trace','one window, five is_v, one cfg_v','each six actual frame cfg/go/12returns',
            '24 actual CAP scalar writes; postrun fixture value comparison','all source faults and extra/late counts']),indent=1)+'\n')


if __name__=='__main__':main()
