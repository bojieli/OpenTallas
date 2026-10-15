#!/usr/bin/env python3
"""Losslessly lower whole-SU command images to physical SRAM config transactions."""
import argparse, hashlib, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def lower(source, out, extra=None, extra_bits=0, line_bits=9688, param_prefix="PROGRAMME"):
    assert 0<line_bits<=65536
    assert extra or extra_bits==0
    assert re.fullmatch(r"[A-Z][A-Z0-9_]*",param_prefix)
    out.mkdir(parents=True,exist_ok=True)
    rows=[int(s,16) for s in source.read_text().split()]
    bits=line_bits
    assert rows and all(0<=r<1<<bits for r in rows)
    if extra:
        xs=[int(s,16) for s in extra.read_text().split()]
        assert len(xs)==len(rows) and extra_bits>0 and all(0<=x<1<<extra_bits for x in xs)
        rows=[r|(x<<bits) for r,x in zip(rows,xs)]; bits+=extra_bits
    assert len(rows)<=65535
    cols=(bits+255)//256; groups=(cols+15)//16; ib=(len(rows)+127)//128
    dictionaries=[]; indices=[]
    for c in range(cols):
        d={}; ix=[]
        for r in rows:
            w=(r>>(c*256))&((1<<256)-1)
            if w not in d: d[w]=len(d)
            ix.append(d[w])
        assert len(d)<=65536
        dictionaries.append(list(d)); indices.append(ix)
    db=[(len(d)+127)//128 for d in dictionaries]
    config=[]
    for g in range(groups):
        for e in range(len(rows)):
            word=sum(indices[c][e]<<(16*(c%16)) for c in range(g*16,min(cols,(g+1)*16)))
            config.append((g*ib+e//128,e%128,word))
    base=groups*ib
    for d,n in zip(dictionaries,db):
        for i,w in enumerate(d): config.append((base+i//128,i%128,w))
        base+=n
    assert base<=65536, 'configuration bank ID exceeds physical host port'
    with (out/'config.mem').open('w') as f:
        for b,r,w in config: f.write(f'{b:04x}{r:02x}{w:064x}\n')
    (out/'expected.mem').write_text(''.join(f'{r:0{(bits+3)//4}x}\n' for r in rows))
    m=dict(schema='opentallas.hbm.su_programme.sram.v1', qualified=False,
           scope='standalone programme producer; whole SU integration and physical closure unproven',
           source=str(source),source_sha256=sha(source),edges=len(rows),line_bits=bits,
           columns=cols,index_groups=groups,index_banks=ib,dictionary_banks=db,
           dictionary_entries=list(map(len,dictionaries)),total_macros=base,
           allocated_bits=base*32768,uncompressed_bits=len(rows)*bits,
           config_transactions=len(config),startup_present_edges=3,startup_consumer_edges=4,
           command_interval_edges=1,first_dictionary_bank=groups*ib,
           extra_source=str(extra) if extra else None,extra_sha256=sha(extra) if extra else None,
           memory_model='physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v')
    pins=['tools/hbm_static/su_top_compile.py', 'tools/hbm_static/su_arith_compile.py',
          'tools/hbm_static/su_programme_compile.py',
          'rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme.sv',
          'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
    m['clock_roots']={'controller':'clk', 'macros':base,
        'index_groups':[{'first_macro':g*ib,'count':ib} for g in range(groups)],
        'dictionary_columns':[{'first_macro':groups*ib+sum(db[:c]),'count':db[c]} for c in range(cols)]}
    m['source_pins']={p:sha(ROOT/p) for p in pins}
    (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    dbstr="'{"+','.join(map(str,db))+"}"
    (out/'programme_params.svh').write_text(
        f'localparam integer {param_prefix}_BITS={bits}, {param_prefix}_COLS={cols}, {param_prefix}_WRITES={len(config)}, {param_prefix}_MACROS={base};\n'
        f'localparam integer {param_prefix}_DICT_BANKS[0:{param_prefix}_COLS-1]={dbstr};\n')
    (out/'tb.sv').write_text(TB.replace('@BITS@',str(bits)).replace('@EDGES@',str(len(rows)))
        .replace('@WRITES@',str(len(config))).replace('@DB@',dbstr).replace('@DICT@',str(groups*ib)).replace('@MACROS@',str(base)))
    return m

TB='''`timescale 1ns/1ps
module tb;
localparam integer B=@BITS@, N=@EDGES@, W=@WRITES@;
logic clk=0; always #5 clk=~clk;
logic rst_n=0,cfg_we=0,start=0;
logic [15:0] cfg_bank=0; logic [6:0] cfg_row=0; logic[255:0] cfg_data=0;
wire busy,valid,done,fault; wire[15:0] edge_index; wire[B-1:0] command;
reg[279:0] config_words[0:W-1]; reg[B-1:0] expected_words[0:N-1];
string dir; integer data_mut,addr_mut,phase_mut;
ot_hbm_su_programme #(.LINE_BITS(B),.EDGES(N),.DICT_BANKS(@DB@),.MACROS(@MACROS@)) dut(
 .clk(clk),.clk_macro({@MACROS@{clk}}),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),
 .start(start),.length(16'(N)),.busy(busy),.valid(valid),.done(done),.fault(fault),
 .edge_index(edge_index),.command(command));
task automatic tick; @(posedge clk); #1; endtask
task automatic execute;
 @(negedge clk); start=1; tick(); @(negedge clk); start=0;
 // Three startup edges after start; third presents line zero.
 for(integer k=0;k<2;k=k+1) begin tick(); if(valid) $fatal(1,"SU_PROGRAMME FAIL early"); end
 for(integer e=0;e<N;e=e+1) begin
   tick();
   if(!valid || edge_index!=e || command!==expected_words[(e+phase_mut)%N] || fault || done!=(e==N-1))
     $fatal(1,"SU_PROGRAMME FAIL edge=%0d index=%0d valid=%b done=%b fault=%b",e,edge_index,valid,done,fault);
 end
 tick(); if(valid || busy || done || command!='0) $fatal(1,"SU_PROGRAMME FAIL tail");
endtask
initial begin
 if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR required");
 data_mut=$test$plusargs("MUT_DATA"); addr_mut=$test$plusargs("MUT_ADDR"); phase_mut=$test$plusargs("MUT_PHASE");
 $readmemh({dir,"/config.mem"},config_words); $readmemh({dir,"/expected.mem"},expected_words);
 tick(); @(negedge clk); rst_n=1;
 for(integer i=0;i<W;i=i+1) begin
   cfg_we=1; cfg_bank=config_words[i][279:264]; cfg_row=config_words[i][262:256]; cfg_data=config_words[i][255:0];
   if(data_mut && cfg_bank==@DICT@ && cfg_row==0) cfg_data=cfg_data^256'b1;
   if(addr_mut && cfg_bank==0 && cfg_row==0) cfg_data=cfg_data^256'b1;
   tick(); @(negedge clk);
 end
 cfg_we=0; execute(); execute();
 $display("SU_PROGRAMME PASS edges=%0d restart=1",N); $finish;
end
endmodule
'''

def main():
    p=argparse.ArgumentParser(); p.add_argument('source',type=Path); p.add_argument('out',type=Path)
    p.add_argument('--extra-mem',type=Path); p.add_argument('--extra-bits',type=int,default=0)
    p.add_argument('--line-bits',type=int,default=9688)
    p.add_argument('--param-prefix',default='PROGRAMME')
    a=p.parse_args(); print(json.dumps(lower(a.source,a.out,a.extra_mem,a.extra_bits,a.line_bits,a.param_prefix),indent=2))
if __name__=='__main__': main()
