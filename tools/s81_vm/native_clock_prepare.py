#!/usr/bin/env python3
"""Build an independent-pin connectivity witness for the actual full VM hierarchy.
Every external root is pulsed alone; observers are the actual leaf clock pins.
No clock generation, gate, CTS or physical phase delivery is inferred by this test.
"""
import argparse, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import die_port_bind as D

def prepare(out, read_pipeline=4, cap_pipeline=2):
    clocks={}; resets={}
    def add(table,port,paths):
        assert port not in table
        table[port]=paths if isinstance(paths,list) else [paths]
    mem='dut.u_core.u_mem'; ws='dut.u_core.u_ws'
    rsched = '.rs_l16.u_rs' if read_pipeline >= 4 else '.rs_l14.u_rs'
    for cat,child,cp,rp in [('core','', 'cks','rss'),('rsched',rsched,'ck','rst_n'),('seq','.u_seq','ck','rst'),('landing','.u_land','ck','rst_n')]:
        add(clocks,'ck_'+cat+'_t','dut.u_core'+child+'.'+cp)
        add(resets,'rss_'+cat+'_t','dut.u_core'+child+'.'+rp)
    for cat,child in [('return','u_return')]:
        add(clocks,'ck_mem_'+cat+'_t',[f'{mem}.slice[{s}].{child}.ck' for s in range(4)])
        add(resets,'rss_mem_'+cat+'_t',[f'{mem}.slice[{s}].{child}.rst_n' for s in range(4)])
    fsrpaths=[f'{mem}.slice[{s}].u_slice.u_r.b{b}.leaf' for s in range(4) for b in range(4)]
    add(clocks,'ck_mem_fsr_t',[p+'.ck' for p in fsrpaths]);add(resets,'rss_mem_fsr_t',[p+'.rst_n' for p in fsrpaths])
    if read_pipeline:
        for cat,count in [('data',64),('valid',8)]:
            read_branch = 'l13' if read_pipeline == 1 else 'l14'
            paths=[f'dut.u_core.bounded_read.{read_branch}.u_read.{"d" if cat=="data" else "v"}{b}.leaf' for b in range(count)]
            add(clocks,'ck_read_'+cat+'_t',[p+'.ck' for p in paths]);add(resets,'rss_read_'+cat+'_t',[p+'.rst_n' for p in paths])
    for cat,child,width in [('bank','bank',32),('wcapture','write_group',32),('wscatter','write_group',4)]:
        paths=[]
        for s in range(4):
            for b in range(width):
                tail=f'bank[{b}].u_bank' if cat=='bank' else (f'write_group[{b//8}].capture[{b%8}].u_capture' if cat=='wcapture' else f'write_group[{b}].u_w')
                paths.append(f'{mem}.slice[{s}].u_slice.{tail}')
        add(clocks,'ck_mem_'+cat+'_t',[p+'.ck' for p in paths]);add(resets,'rss_mem_'+cat+'_t',[p+'.rst_n' for p in paths])
    hops=[f'{mem}.slice[{s}].u_slice.'+(f'bridge[{b}].u_hop' if b<4 else f'quarter[{b-4}].u_hop') for s in range(4) for b in range(12)]
    for direction in ['req','rsp']:add(clocks,'ck_mem_relay_'+direction+'_t',[p+'.ck_'+direction for p in hops])
    add(resets,'rss_mem_relay_t',[p+'.rst_n' for p in hops])
    wpaths={'control':[ws+'.u_control'],'header':[ws+'.u_header'],'payload':[f'{ws}.w0_payload[{s}].u_payload' for s in range(4)],'dispatch':[f'{ws}.slice[{s}].quarter[{z}].u_d' for s in range(4) for z in range(4)],'stage':[f'{ws}.slice[{s}].bank[{b}].u_w' for s in range(4) for b in range(32)]}
    for cat,paths in wpaths.items():
        add(clocks,'ck_write_'+cat+'_t',[p+('.ck_control' if cat=='control' else '.ck') for p in paths]);add(resets,'rss_write_'+cat+'_t',[p+'.rst_n' for p in paths])
    for domain,cp,rp in [('s','s_ck','s_rst_n'),('t','t_ck','t_rst_n')]:
        add(clocks,'ck_landing_x34_'+domain,['dut.'+p+'.'+cp for p in ['u_xsel','u_xcol','u_xsw']]);add(resets,('rst' if domain=='s' else 'rss')+'_landing_x34_'+domain,['dut.'+p+'.'+rp for p in ['u_xsel','u_xcol','u_xsw']])
    add(clocks,'ck_cap_control_s','dut.u_cap.u_ctl.ck');add(resets,'rst_cap_control_s','dut.u_cap.u_ctl.rst_n')
    add(clocks,'ck_cap_lane_s',[f'dut.u_cap.lane[{g}].u_l.ck' for g in range(16)])
    for dom,cp,rp in [('s','s_ck','s_rst_n'),('t','t_ck','t_rst_n')]:
        add(clocks,'ck_cap_x34_'+dom,[f'dut.u_cap.lane[{g}].u_x.{cp}' for g in range(16)]);add(resets,('rst' if dom=='s' else 'rss')+'_cap_x34_'+dom,[f'dut.u_cap.lane[{g}].u_x.{rp}' for g in range(16)])
    for unit in ['wfc','xio']:
        for dom in ['s','t']:
            add(clocks,f'ck_{unit}_control_{dom}',f'dut.u_{unit}.ck_control_{dom}');add(resets,f'{"rst" if dom=="s" else "rss"}_{unit}_control_{dom}',f'dut.u_{unit}.{ "rst" if dom=="s" else "rss"}_control_{dom}')
        cdc={'x34':['u_xi'],'x43':['u_xo']} if unit=='wfc' else {'x43':['u_xq','u_xg']}
        for kind,paths in cdc.items():
            for dom,cp,rp in [('s','s_ck','s_rst_n'),('t','t_ck','t_rst_n')]:
                add(clocks,f'ck_{unit}_{kind}_{dom}',[f'dut.u_{unit}.{p}.{cp}' for p in paths]);add(resets,f'{"rst" if dom=="s" else "rss"}_{unit}_{kind}_{dom}',[f'dut.u_{unit}.{p}.{rp}' for p in paths])
    text=(ROOT/'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm_static.sv').read_text()
    mod=next(m for m in D.parse_modules(D.preprocess(text,{'DSFD_SP_VM_MIX4':''}),'dsfd_sp_vm_static.sv') if m.name=='dsfd_sp_vm');env=mod.env();cons=[];obs=[];robs=[];c=0;r=0;mapping={}
    for table,vec in [(clocks,'clocks'),(resets,'resets')]:
        for port,paths in table.items():
            assert mod.width(port,env)==len(paths),(port,mod.width(port,env),len(paths))
            start=c if vec=='clocks' else r
            cons.append(f'.{port}({vec}[{start}])' if len(paths)==1 else f'.{port}({vec}[{start} +: {len(paths)}])')
            for i,p in enumerate(paths):(obs if vec=='clocks' else robs).append((start+i,p))
            mapping[port]={'kind':vec,'start':start,'width':len(paths),'leaf_pins':paths}
            if vec=='clocks':c+=len(paths)
            else:r+=len(paths)
    assert (c,r)==(609+72*bool(read_pipeline),545+72*bool(read_pipeline)),(c,r)
    inactive_read = set() if read_pipeline else {'ck_read_data_t','ck_read_valid_t','rss_read_data_t','rss_read_valid_t'}
    actual_clock_reset = {n for n in mod.ports if n.startswith(('ck_', 'rss_', 'rst_'))}
    assert set(mapping) | inactive_read == actual_clock_reset, (sorted(actual_clock_reset-set(mapping)-inactive_read), sorted(set(mapping)-actual_clock_reset))
    for port,(direction,_) in mod.ports.items():
        if direction=='input' and port not in mapping:
            width=mod.width(port,env);cons.append(f'.{port}({width}\'d0)')
    tb='`timescale 1ns/1ps\nmodule tb_vm_native_clock_pins;\n'
    tb+=f'reg [{c-1}:0] clocks=0;reg [{r-1}:0] resets=0;wire [{r-1}:0] observed_reset;integer counts[0:{c-1}];integer i,j,bad=0;\n'
    tb+=f'dsfd_sp_vm #(.READ_PIPE({read_pipeline}), .CAP_PIPE({cap_pipeline})) dut ('+',\n'.join(cons)+');\n'
    for i,p in obs:tb+=f'always @(posedge {p}) counts[{i}]=counts[{i}]+1;\n'
    for i,p in robs:tb+=f'assign observed_reset[{i}]={p};\n'
    tb+=f'''initial begin
for(i=0;i<{c};i=i+1)counts[i]=0;
#2;resets='1;#2;
for(i=0;i<{c};i=i+1)begin
 clocks[i]=1;#1;clocks[i]=0;#1;
 for(j=0;j<{c};j=j+1)if(counts[j]!==((j<=i)?1:0))begin bad=bad+1;if(bad<5)$display("CLOCK_BIND_MISMATCH pulse%0d observed%0d",i,j);end
end
for(i=0;i<{r};i=i+1)begin resets='1;resets[i]=0;#1;if(observed_reset!==resets)begin bad=bad+1;if(bad<5)$display("RESET_BIND_MISMATCH pin%0d",i);end end
$display("VM_NATIVE_PIN_RESULT clocks{c} resets{r} bad%0d",bad);
if(bad==0)$display("VM_NATIVE_PIN_PASS");else $display("VM_NATIVE_PIN_FAIL");$finish;
end
endmodule
'''
    out.mkdir(parents=True,exist_ok=False);(out/'tb_vm_native_clock_pins.sv').write_text(tb)
    (out/'mapping.json').write_text(json.dumps({'source_sha256':hashlib.sha256(text.encode()).hexdigest(),'read_pipeline':read_pipeline,'cap_pipeline':cap_pipeline,'clocks':c,'raw_reset_pins':r,'legacy_only_clock_categories':['ck_core_t'] if read_pipeline else [],'scope':'Independent raw root connectivity only; no CTS, sink-count, related-clock timing, or reset-function qualification. ck_core_t has no native-read sequential sink.','cap_rn_distribution':'16synchronous lane rn pins remain driven by existing cap-control rq2; physicalreset delivery unqualified','categories':mapping},indent=2)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--read-pipe',type=int,choices=[0,1,2,4],default=4);ap.add_argument('--cap-pipe',type=int,choices=[0,1,2],default=2);a=ap.parse_args();prepare(a.out,a.read_pipe,a.cap_pipe)
