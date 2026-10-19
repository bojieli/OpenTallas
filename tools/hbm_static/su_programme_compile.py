#!/usr/bin/env python3
"""Losslessly lower whole-SU command images to physical SRAM config transactions."""
import argparse, hashlib, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def lower(source, out, extra=None, extra_bits=0, line_bits=9688, param_prefix="PROGRAMME", index_pack=1):
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
    cols=(bits+255)//256; groups=(cols+15)//16; ib=(len(rows)+128*index_pack-1)//(128*index_pack)
    assert index_pack in (1,2,4,8,16) and (index_pack==1 or cols==1)
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
        for e in range(0,len(rows),index_pack):
            word=sum(indices[c][e+k]<<(16*(c%16+cols*k))
                     for k in range(min(index_pack,len(rows)-e))
                     for c in range(g*16,min(cols,(g+1)*16)))
            index_row=e//index_pack
            config.append((g*ib+index_row//128,index_row%128,word))
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
           columns=cols,index_groups=groups,index_banks=ib,index_pack=index_pack,dictionary_banks=db,
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
    dbstr="{"+','.join("32'd"+str(x) for x in reversed(db))+"}"
    (out/'programme_params.svh').write_text(
        f'localparam integer {param_prefix}_BITS={bits}, {param_prefix}_COLS={cols}, {param_prefix}_WRITES={len(config)}, {param_prefix}_MACROS={base}, {param_prefix}_INDEX_PACK={index_pack};\n'
        f'localparam [32*{param_prefix}_COLS-1:0] {param_prefix}_DICT_BANKS={dbstr};\n')
    (out/'tb.sv').write_text(TB.replace('@BITS@',str(bits)).replace('@EDGES@',str(len(rows)))
        .replace('@WRITES@',str(len(config))).replace('@DB@',dbstr).replace('@DICT@',str(groups*ib)).replace('@MACROS@',str(base)).replace('@PACK@',str(index_pack)))
    return m

TB='''`timescale 1ns/1ps
module tb;
localparam integer B=@BITS@, N=@EDGES@, W=@WRITES@;
localparam [32*((B+255)/256)-1:0] DB=@DB@;
logic clk=0; always #5 clk=~clk;
logic rst_n=0,cfg_we=0,start=0;
logic [15:0] cfg_bank=0; logic [6:0] cfg_row=0; logic[255:0] cfg_data=0;
wire busy,valid,done,fault; wire[15:0] edge_index; wire[B-1:0] command;
reg[279:0] config_words[0:W-1]; reg[B-1:0] expected_words[0:N-1];
string dir; integer data_mut,addr_mut,phase_mut;
ot_hbm_su_programme #(.LINE_BITS(B),.COLS((B+255)/256),.EDGES(N),.INDEX_PACK(@PACK@),.DICT_BANKS(DB),.MACROS(@MACROS@)) dut(
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

def lower_partitioned(source, out, parts=4, line_bits=9688, start_depth=2, uniform=True, mut_pc_slice=None):
    """H-SU 2026-10-16 (opt-in, --partition): split the whole-SU line into PARTS per-quarter producers (line bits
    [k*SB,(k+1)*SB), SB = line_bits/PARTS), each lowered exactly as lower() lowers a whole line, so each producer holds
    only its own columns' dictionaries and its own edge-index table and sits beside its consumer.  Only start/length
    cross the die, as an equal-age registered tree of START_DEPTH edges inside ot_hbm_su_programme_part; the compiler
    issues start START_DEPTH edges earlier, so every command bit reaches its consumer on the same edge as from the
    monolithic producer (fixed-cycle stream, no queue/credit).  uniform=True gives every producer the element-wise max
    dictionary capacity (one physical master for all PARTS).  The default lower() path is untouched."""
    assert line_bits%parts==0 and start_depth>=1
    sb=line_bits//parts
    out.mkdir(parents=True,exist_ok=True)
    rows=[int(t,16) for t in source.read_text().split()]
    assert rows and all(0<=r<1<<line_bits for r in rows)
    ms=[]
    for k in range(parts):
        d=out/f'slice{k}'; d.mkdir(parents=True,exist_ok=True)
        (d/'source.mem').write_text(''.join(f'{(r>>(k*sb))&((1<<sb)-1):0{(sb+3)//4}x}\n' for r in rows))
        ms.append(lower(d/'source.mem',d,line_bits=sb,param_prefix=f'PSLICE{k}'))
    cols=ms[0]['columns']; ib=ms[0]['index_banks']; groups=ms[0]['index_groups']
    assert all(m['columns']==cols and m['index_banks']==ib and m['index_groups']==groups for m in ms)
    cap=[max(m['dictionary_banks'][c] for m in ms) for c in range(cols)] if uniform else None
    # global host config stream: slice k banks [base_k, base_k + macros_k); each slice's own bank numbering inside.
    smac=[(groups*ib+sum(cap)) if uniform else m['total_macros'] for m in ms]
    base=[sum(smac[:k]) for k in range(parts)]
    def slice_dict_base(m):  # first bank of each dictionary column inside the slice
        db=cap if uniform else m['dictionary_banks']; return [groups*ib+sum(db[:c]) for c in range(cols)]
    lines=[]; lines_mut=[]
    for k,m in enumerate(ms):
        d=out/f'slice{k}'
        own=[(int(l[:4],16),int(l[4:6],16),l[6:]) for l in (d/'config.mem').read_text().split()]
        if uniform:  # remap the slice's own dictionary bank ids onto the uniform capacity layout
            odb=m['dictionary_banks']; ob=[groups*ib+sum(odb[:c]) for c in range(cols)]; nb=slice_dict_base(m)
            def remap(b):
                if b<groups*ib: return b
                c=max(i for i in range(cols) if ob[i]<=b); return nb[c]+(b-ob[c])
            own=[(remap(b),r,w) for b,r,w in own]
        for b,r,w in own: lines.append(f'{base[k]+b:04x}{r:02x}{w}\n')
        if mut_pc_slice==k:  # MUT: this slice's index table rotated by one edge == its PC offset by one
            idx=[(b,r,w) for b,r,w in own if b<groups*ib]; rest=[(b,r,w) for b,r,w in own if b>=groups*ib]
            words=[w for b,r,w in sorted(idx)]; words=words[1:]+words[:1]
            idx=[(b,r,words[i]) for i,(b,r,_) in enumerate(sorted(idx))]
            own=idx+rest
        for b,r,w in own: lines_mut.append(f'{base[k]+b:04x}{r:02x}{w}\n')
    assert base[-1]+smac[-1]<=65536
    (out/'config.mem').write_text(''.join(lines))
    if mut_pc_slice is not None: (out/'config_mut_pc.mem').write_text(''.join(lines_mut))
    (out/'expected.mem').write_text(''.join(f'{r:0{(line_bits+3)//4}x}\n' for r in rows))
    pk=out/'part_params.svh'
    sdb=[(cap if uniform else m['dictionary_banks']) for m in ms]
    flat=[x for k in range(parts) for x in sdb[k]]
    pk.write_text(f'localparam integer PART_N={parts}, PART_SB={sb}, PART_COLS={cols}, PART_EDGES={len(rows)}, '
                  f'PART_WRITES={len(lines)}, PART_MACROS={sum(smac)}, PART_DEPTH={start_depth}, PART_FIRST_DICT={groups*ib};\n'
                  f'localparam [32*PART_N-1:0] PART_SMACROS={{'+','.join("32'd"+str(x) for x in reversed(smac))+'};\n'
                  f'localparam [32*PART_N*PART_COLS-1:0] PART_DICT_BANKS={{'+','.join("32'd"+str(x) for x in reversed(flat))+'};\n')
    man=dict(schema='opentallas.hbm.su_programme.partitioned.v1', qualified=False, source=str(source),
             source_sha256=sha(source), edges=len(rows), line_bits=line_bits, parts=parts, slice_bits=sb,
             start_depth=start_depth, uniform_capacity=uniform, columns_per_slice=cols, index_banks_per_slice=ib,
             slice_macros=smac, slice_bank_base=base, total_macros=sum(smac),
             slice_dictionary_banks_exact=[m['dictionary_banks'] for m in ms],
             slice_dictionary_banks_used=sdb, slice_dictionary_entries=[m['dictionary_entries'] for m in ms],
             slice_macros_exact=[m['total_macros'] for m in ms], config_transactions=len(lines),
             startup_consumer_edges=4+start_depth, start_issue_advance_edges=start_depth,
             crossing_bits_per_slice='start 1 + length 16 (registered, equal age); config bus host-time only',
             mut_pc_slice=mut_pc_slice)
    (out/'part_manifest.json').write_text(json.dumps(man,indent=2)+'\n')
    return man

def lower_columns(source, out, line_bits=2422, leaf_caps=(3,13), col_bits=32, mut_pc_col=None, mut_tpl_col=None):
    """HBM-SU r5 2026-10-17 (opt-in, --columns): one quarter's command line (line_bits) lowered for the per-column
    cluster ot_hbm_su_programme_pslice_c5: column c (bits [256c, 256c+256)) is its own producer (lower() with
    line_bits 256, index_pack 16: 16 edges of 16-bit dictionary indices per index row), config bank = col_bits*c +
    local bank (local 0..IB-1 index, IB.. dictionary).  The leaf master is the smallest of leaf_caps that holds the
    column's dictionary.  Also lowers the same quarter for the r4 reference (lower(), unpacked) into out/ref."""
    out.mkdir(parents=True,exist_ok=True)
    rows=[int(t,16) for t in source.read_text().split()]
    assert rows and all(0<=r<1<<line_bits for r in rows)
    ref=lower(source,out/'ref',line_bits=line_bits,param_prefix='REF')
    cols=(line_bits+255)//256; lines=[]; lines_mut=[]; per=[]
    for c in range(cols):
        d=out/f'col{c}'; d.mkdir(parents=True,exist_ok=True)
        (d/'source.mem').write_text(''.join(f'{(r>>(256*c))&((1<<256)-1):064x}\n' for r in rows))
        m=lower(d/'source.mem',d,line_bits=256,param_prefix=f'COL{c}',index_pack=16)
        db=m['dictionary_banks'][0]; ib=m['index_banks']
        leaf=min(x for x in leaf_caps if x>=db)
        assert ib+leaf<col_bits-1, 'local bank id 31 is the reject code'
        own=[(int(l[:4],16),int(l[4:6],16),l[6:]) for l in (d/'config.mem').read_text().split()]
        for b,r,w in own: lines.append(f'{col_bits*c+b:04x}{r:02x}{w}\n')
        mo=own
        if mut_pc_col==c:  # MUT: this column's packed index table one edge late == its PC offset by one
            e=[int(w,16) for b,r,w in sorted(x for x in own if x[0]<ib)]
            vals=[(e[i//16]>>(16*(i%16)))&0xffff for i in range(len(e)*16)][:len(rows)]
            vals=vals[1:]+vals[:1]; vals+= [0]*(len(e)*16-len(vals))
            words=[sum(vals[16*j+k]<<(16*k) for k in range(16)) for j in range(len(e))]
            idx=sorted(x for x in own if x[0]<ib)
            mo=[(b,r,f'{words[i]:064x}') for i,(b,r,_) in enumerate(idx)]+[x for x in own if x[0]>=ib]
        if mut_tpl_col==c:  # MUT: first dictionary word of this column flipped in bit 0
            mo=[(b,r,(f'{int(w,16)^1:064x}' if (b==ib and r==0) else w)) for b,r,w in mo]
        for b,r,w in mo: lines_mut.append(f'{col_bits*c+b:04x}{r:02x}{w}\n')
        per.append(dict(column=c,index_banks=ib,dictionary_banks=db,leaf_dictionary_banks=leaf,
                        leaf='ot_hbm_su_programme_pgcol_s' if leaf==leaf_caps[0] else 'ot_hbm_su_programme_pgcol_l',
                        dictionary_entries=m['dictionary_entries'][0],writes=len(own)))
    (out/'config.mem').write_text(''.join(lines))
    (out/'config_mut.mem').write_text(''.join(lines_mut))
    (out/'expected.mem').write_text(''.join(f'{r:0{(line_bits+3)//4}x}\n' for r in rows))
    cap=[p['dictionary_banks'] for p in per]
    (out/'cols_params.svh').write_text(
        f'localparam integer CL_SB={line_bits}, CL_NC={cols}, CL_EDGES={len(rows)}, CL_WRITES={len(lines)};\n'
        f'localparam [32*CL_NC-1:0] CL_CAP={{'+','.join("32'd"+str(x) for x in reversed(cap))+'};\n')
    man=dict(schema='opentallas.hbm.su_programme.columns.v1',qualified=False,source=str(source),source_sha256=sha(source),
             edges=len(rows),line_bits=line_bits,columns=per,config_transactions=len(lines),
             cluster_macros=sum(p['index_banks']+p['leaf_dictionary_banks'] for p in per),
             reference_macros=ref['total_macros'],bank_numbering=f'{col_bits} x column + local bank',
             mut_pc_col=mut_pc_col,mut_tpl_col=mut_tpl_col)
    (out/'cols_manifest.json').write_text(json.dumps(man,indent=2)+'\n')
    return man

def lower_root5(source, out, parts=4, line_bits=9688, part_banks=320, col_bits=32, mut_q=None, start_depth=2):
    """HBM-RTL5 2026-10-18 (opt-in, --root5): whole-SU line lowered for ot_hbm_su_programme_root_h5 + PARTS per-column
    clusters ot_hbm_su_programme_pslice_c5 (pgp_<q>): quarter k = lower_columns() of line bits [k*SB,(k+1)*SB) in
    out/q<k>, host config bank = part_banks*k + col_bits*column + local.  Also lowers the r4 reference (root_h 4 x 98 +
    pslice_q4, lower_partitioned) into out/ref4 so the whole-programme bench can run both on one host stimulus.
    mut_q: quarter whose column 3 index (PC offset) and column 2 dictionary word are mutated in config_mut.mem."""
    assert line_bits%parts==0
    sb=line_bits//parts; cols=(sb+255)//256
    assert col_bits*cols<=part_banks and part_banks*parts<65536
    out.mkdir(parents=True,exist_ok=True)
    rows=[int(t,16) for t in source.read_text().split()]
    lines=[]; lines_mut=[]; caps=[]; per=[]
    for k in range(parts):
        d=out/f'q{k}'; d.mkdir(parents=True,exist_ok=True)
        (d/'source.mem').write_text(''.join(f'{(r>>(k*sb))&((1<<sb)-1):0{(sb+3)//4}x}\n' for r in rows))
        m=lower_columns(d/'source.mem',d,line_bits=sb,col_bits=col_bits,
                        mut_pc_col=3 if mut_q==k else None,mut_tpl_col=2 if mut_q==k else None)
        caps.append([c['dictionary_banks'] for c in m['columns']]); per.append(m)
        for src,dst in (('config.mem',lines),('config_mut.mem',lines_mut)):
            for l in (d/src).read_text().split():
                dst.append(f'{part_banks*k+int(l[:4],16):04x}{l[4:]}\n')
    # one cluster leaf layout for every quarter (one pgp_<q> master): leaf choice per column must agree
    leaves=[[c['leaf'] for c in m['columns']] for m in per]
    assert all(l==leaves[0] for l in leaves), f'quarter leaf layouts differ: {leaves}'
    cap=[max(c[i] for c in caps) for i in range(cols)]
    (out/'config.mem').write_text(''.join(lines)); (out/'config_mut.mem').write_text(''.join(lines_mut))
    (out/'expected.mem').write_text(''.join(f'{r:0{(line_bits+3)//4}x}\n' for r in rows))
    ref=lower_partitioned(source,out/'ref4',parts,line_bits,start_depth)
    (out/'root5_params.svh').write_text(
        f'localparam integer R5_PARTS={parts}, R5_SB={sb}, R5_NC={cols}, R5_EDGES={len(rows)}, R5_WRITES={len(lines)}, '
        f'R5_PART_BANKS={part_banks};\n'
        f'localparam [32*R5_NC-1:0] R5_CAP={{'+','.join("32'd"+str(x) for x in reversed(cap))+'};\n')
    man=dict(schema='opentallas.hbm.su_programme.root5.v1',qualified=False,source=str(source),source_sha256=sha(source),
             edges=len(rows),line_bits=line_bits,parts=parts,slice_bits=sb,columns=cols,part_banks=part_banks,
             bank_numbering=f'{part_banks} x part + {col_bits} x column + local bank',leaves=leaves[0],
             dictionary_caps_per_quarter=caps,config_transactions=len(lines),
             reference=dict(parts=ref['parts'],slice_macros=ref['slice_macros'],config_transactions=ref['config_transactions']),
             mut_q=mut_q)
    (out/'root5_manifest.json').write_text(json.dumps(man,indent=2)+'\n')
    return man

def main():
    p=argparse.ArgumentParser(); p.add_argument('source',type=Path); p.add_argument('out',type=Path)
    p.add_argument('--extra-mem',type=Path); p.add_argument('--extra-bits',type=int,default=0)
    p.add_argument('--line-bits',type=int,default=9688)
    p.add_argument('--param-prefix',default='PROGRAMME')
    p.add_argument('--index-pack',type=int,default=1)
    p.add_argument('--partition',type=int,default=0,help='opt-in: N per-quarter producers (ot_hbm_su_programme_part)')
    p.add_argument('--start-depth',type=int,default=2); p.add_argument('--exact-capacity',action='store_true')
    p.add_argument('--mut-pc-slice',type=int)
    p.add_argument('--columns',action='store_true',help='opt-in: per-column cluster lowering of one quarter line')
    p.add_argument('--mut-pc-col',type=int); p.add_argument('--mut-tpl-col',type=int)
    p.add_argument('--root5',action='store_true',help='opt-in: root_h5 + 4 per-column clusters (whole SU line)')
    p.add_argument('--mut-q',type=int)
    a=p.parse_args()
    if a.root5:
        print(json.dumps(lower_root5(a.source,a.out,line_bits=a.line_bits,mut_q=a.mut_q,start_depth=a.start_depth),indent=2)); return
    if a.columns:
        print(json.dumps(lower_columns(a.source,a.out,a.line_bits,mut_pc_col=a.mut_pc_col,mut_tpl_col=a.mut_tpl_col),
                         indent=2)); return
    if a.partition:
        print(json.dumps(lower_partitioned(a.source,a.out,a.partition,a.line_bits,a.start_depth,not a.exact_capacity,
                                           a.mut_pc_slice),indent=2)); return
    print(json.dumps(lower(a.source,a.out,a.extra_mem,a.extra_bits,a.line_bits,a.param_prefix,a.index_pack),indent=2))
if __name__=='__main__': main()
