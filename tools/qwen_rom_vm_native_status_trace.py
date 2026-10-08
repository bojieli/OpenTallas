#!/usr/bin/env python3
"""Current-source ME address/tag slice; no arithmetic or parent co-issue claim."""
import argparse,subprocess,re
import csv,json,hashlib
from pathlib import Path
from collections import Counter,defaultdict

def parse(path,ignore_enable=False):
 rows=list(csv.DictReader(path.open()));frames=[];lookup={};edges=[];rs=[];ws=[];mins=[];maxs=[];peakr=peakw=0
 for r in rows:
  cy=int(r['cycle']);en=int(r['me_clk_en'])
  if cy<4:continue
  if any(c in r['xre']+r['owe'] for c in 'xz'):raise ValueError('unknown valid')
  xm=int(r['xre'],16);wm=int(r['owe'],16)
  x=[];w=[]
  if xm:
   a=int(r['xaddr'],16);x=[(i,(a>>(24*i))&0xffffff) for i in range(2048) if xm>>i&1]
  if wm:
   a=int(r['oaddr'],16);mask=int(r['omask'],16);w=[(i,(a>>(24*i))&0xffffff,(mask>>(16*i))&65535) for i in range(48) if wm>>i&1 and (mask>>(16*i))&65535]
  # Full captured PRE-edge buses, canonical compression preserves every seat.
  key=(r['xre'],r['xaddr'] if xm else '',r['owe'],r['oaddr'] if wm else '',r['omask'] if wm else '')
  if key not in lookup: lookup[key]=len(frames);frames.append(dict(zip(['xre','xaddr','owe','oaddr','omask'],key)))
  edges.append(dict(cycle=cy,me_clk_en=en,frame=lookup[key]))
  if not(en or ignore_enable):continue
  if x:
   rs.append((cy,x));addrs=[a for i,a in x];mins.append(min(addrs));maxs.append(max(addrs));banks=defaultdict(set)
   for a in addrs:banks[(a>>15,(a>>4)&3)].add((a>>6)&511)
   peakr=max(peakr,max(map(len,banks.values())))
  if w:
   ws.append((cy,w));addrs=[16*a+l for i,a,m in w for l in range(16) if m>>l&1];mins.append(min(addrs));maxs.append(max(addrs));banks=defaultdict(set)
   for i,a,m in w:banks[(a>>11,a&3)].add((a>>2)&511)
   peakw=max(peakw,max(map(len,banks.values())))
 sig=lambda xs:hashlib.sha256(json.dumps([v for c,v in xs],separators=(',',':')).encode()).hexdigest()
 return dict(trace=dict(schema='opentallas.qwen-native-me-preedge-trace.v1',frames=frames,edges=edges),
   summary=dict(read_edges=len(rs),write_edges=len(ws),read_scalar_requests=sum(len(v) for c,v in rs),
     write_scalar_requests=sum(m.bit_count() for c,v in ws for i,a,m in v),read_first_cycle=rs[0][0],read_last_cycle=rs[-1][0],write_first_cycle=ws[0][0],write_last_cycle=ws[-1][0],
     min_scalar_address=min(mins),max_scalar_address=max(maxs),fits_177808_for_this_operation=max(maxs)<177808,
     maximum_same_group_bank_distinct_read_rows=peakr,maximum_same_group_bank_distinct_write_rows=peakw,
     read_order_signature=sig(rs),write_order_signature=sig(ws),read_write_coissue_cycles=len(set(c for c,v in rs)&set(c for c,v in ws)),native_parent_other_writer_families='not observed; excluded component, not zero-valued actual runtime traces'))

def generate(root,out):
    from pathlib import Path
    import hashlib,json,sys
    R=root;O=out;s=(R/'rtl/hdc/ot_qwen_w12_matvec.sv').read_text()
    parts=[]
    def cut(a,b):
     x=s[s.index(a):s.index(b,s.index(a))];parts.append(dict(start=a,end=b,sha256=hashlib.sha256(x.encode()).hexdigest()));return x
    text=cut('module ot_qwen_w12_matvec_part #(', '    //: KV ops: group g = q*S + c takes tile')
    text+=cut('    // Tag of the element issued this cycle', '    generate if (LANES && FAST_ISSUE')
    text+=cut('    // -- S1 (memories answer)', '    //: Memory read data is registered')
    text+=cut('    wire [TW-1:0] a_tag;', '    // -- lanes')
    post=cut('    wire raw_v =', '    //: A status bit:')
    a=post.index('        genvar si;');b=post.index('        assign res = scaled;',a)
    post=post[:a]+post[b:]
    text+='    wire [GI*W*32-1:0] raw_res; // unobserved datapath, deliberately undriven\n'+post
    text+=cut('    // -- results ', '    // -- argmax:')
    text+='    genvar lv;\n'
    tail=cut('    // -- argmax:', '\nendmodule')
    a=tail.index('    genvar e;');b=tail.index('    wire [CW-1:0] top =',a)
    text+=tail[:a]+tail[b:]
    text+='\nendmodule\n'
    text+=s[s.index('module ot_qwen_w12_kadd #'):]
    text=text.replace('module ot_qwen_w12_matvec_part #(', 'module native_me_address_slice #(')
    (O/'slice.sv').write_text(text)
    (O/'slice_manifest.json').write_text(json.dumps(dict(source='rtl/hdc/ot_qwen_w12_matvec.sv',source_sha256=hashlib.sha256(s.encode()).hexdigest(),slices=parts,excluded='Arithmetic and data returns, core scheduler and non-ME writers. W1 amax/rmax=0; argmax/MX valid/status retained, comparator datapath removed; this W1 has amax/rmax=0 and never consumes comparator output.',modified='Module name; remove post-scale arithmetic instances only. Undriven data outputs are never observed.',sha256=hashlib.sha256(text.encode()).hexdigest()),indent=2)+'\n')
    sys.path.insert(0,str(R/'tools'));from hdc_isa import decode
    raw=(R/'results/rtl/qwen_rom_finite_vm_schedule_20261005/inputs/L20_program.hex').read_text().splitlines();d=decode(int(raw[20],16))
    ports=['clk(clk)','rst_n(rst_n)','go(go)','i_gbase(0)','x_re(xre)','x_addr(xaddr)','o_we(owe)','o_addr(oaddr)','o_mask(omask)','idle(idle)','ready(ready)','progress(progress)','mx_we(mxwe)']
    for key,val in d.items():
     if key.startswith('me_') and key[3:] in ['nout','tiles','k','wsrc','wbase','ts','ks','js','xbase','xks','xjs','xcs','jsh','split','wcs','round','obase','ots','ojs','mmode','oen','amax','rmax','mbase']:
      ports.append('i_'+key[3:]+'(32\'d'+str(val)+')')
    bench='''module tb;
    parameter FAST=0,ACC=5,TREE=3,MUL=5,STALL=0;
    reg rawclk=0,rst_n=0,go=0,en=1;
    wire clk=rawclk & en;
    wire[6143:0] xre;wire[6144*24-1:0] xaddr;
    wire idle,ready,mxwe;wire[15:0] progress;wire[47:0] owe;wire[48*24-1:0] oaddr;wire[48*16-1:0] omask;
    native_me_address_slice #(.G(6144),.GT(6144),.W(16),.AW(24),.NW(18),.PART(2),.SMIN(7),.TCUT(7),.NX(2048),.GOUT(48),.XD(105),.ORD(7),.MEM_EXTRA(1),.INT8_WEIGHT(1),.INT8_SCALE_WCS_BASE(1),.FAST_ISSUE(FAST),.ACC_LAT(ACC),.TREE_LAT(TREE),.MUL_LAT(MUL)) dut(PORTS);
    integer n,fd;
    initial begin
     fd=$fopen("trace.csv","w");
     $fdisplay(fd,"cycle,me_clk_en,xre,xaddr,owe,oaddr,omask,idle,ready,progress,mxwe");
     #1;rst_n=1;#1;rst_n=0;#1;
     for(n=0;n<700;n=n+1) begin
      rawclk=0;en=!(STALL && n>8 && n%7==0);go=n==5;rst_n=n>=4;
      #5;
      $fdisplay(fd,"%0d,%0d,%h,%h,%h,%h,%h,%0d,%0d,%0d,%0d",n,en,xre[2047:0],xaddr[2048*24-1:0],owe,oaddr,omask,idle,ready,progress,mxwe);
      rawclk=1;#5;
     end
     $fclose(fd);$display("PASS captured700 PRE edges");$finish;
    end
    endmodule
    '''.replace('PORTS',','.join('.'+p for p in ports))
    (O/'bench.sv').write_text(bench)

def run(root,out):
    out.mkdir(parents=True,exist_ok=False)
    generate(root,out)
    profiles=dict(default=[],physical=['-Ptb.FAST=1','-Ptb.ACC=7','-Ptb.TREE=7','-Ptb.MUL=6'],physical_stalls=['-Ptb.FAST=1','-Ptb.ACC=7','-Ptb.TREE=7','-Ptb.MUL=6','-Ptb.STALL=1'])
    summaries={};traces={}
    sources=['rtl/hdc/ot_qwen_w12_matvec.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_sfu.sv','rtl/hdc/ot_qwen_w12_arith.sv','rtl/hdc/ot_qwen_me_array_w12.sv','results/rtl/qwen_rom_finite_vm_schedule_20261005/inputs/L20_program.hex','tools/hdc_isa.py','tools/qwen_rom_vm_native_status_trace.py']
    for key,flags in profiles.items():
        dest=out/key;dest.mkdir()
        build=subprocess.run(['iverilog','-g2012','-s','tb',*flags,'-o',str(dest/'sim'),str(out/'slice.sv'),str(out/'bench.sv'),*[str(root/p) for p in sources[1:4]]],capture_output=True,text=True)
        (dest/'build.log').write_text(build.stdout+build.stderr)
        if build.returncode:raise RuntimeError(build.stderr)
        sim=subprocess.run(['vvp',str(dest/'sim')],cwd=dest,capture_output=True,text=True)
        (dest/'sim.log').write_text(sim.stdout+sim.stderr)
        if sim.returncode:raise RuntimeError(sim.stdout+sim.stderr)
        result=parse(dest/'trace.csv');summaries[key]=result['summary'];traces[key]=result['trace']
        status=[{k:int(row[k]) for k in ['cycle','me_clk_en','idle','ready','progress','mxwe']} for row in csv.DictReader((dest/'trace.csv').open()) if int(row['cycle'])>=4]
        (dest/'drain_control.json').write_text(json.dumps(status,separators=(',',':'))+'\n')
        first_idle=next(row['cycle'] for row in status if row['cycle']>5 and row['idle']==1)
        result['summary']['native_first_idle_cycle']=first_idle
        result['summary']['native_final_progress']=status[-1]['progress']
        assert status[-1]['progress']==8 and first_idle>result['summary']['write_last_cycle']

        (dest/'trace.json').write_text(json.dumps(result['trace'],separators=(',',':'))+'\n')
    expected=summaries['default']
    assert expected['read_edges']==256 and expected['write_edges']==8 and expected['write_scalar_requests']==6144
    for summary in summaries.values():
        assert summary['read_order_signature']==expected['read_order_signature']
        assert summary['write_order_signature']==expected['write_order_signature']
    assert summaries['physical']['write_first_cycle']-expected['write_first_cycle']==55
    ignored=parse(out/'physical_stalls/trace.csv',ignore_enable=True)['summary']
    negative=ignored['read_order_signature']!=expected['read_order_signature'] and ignored['write_order_signature']!=expected['write_order_signature']
    assert negative
    # Candidate mapping: row retains upper bits, bank XOR-folds those into low bits.
    frames=traces['physical']['frames'];readsets=[];writesets=[]
    for f in frames:
        if int(f['xre'],16):
            a=int(f['xaddr'],16);readsets.append(set(((a>>(24*i))&0xffffff)//16 for i in range(2048)))
        if int(f['owe'],16):
            a=int(f['oaddr'],16);writesets.append(set((a>>(24*i))&0xffffff for i in range(48)))
    def peak(sets): return max(max(Counter((w^(w>>7))&127 for w in words).values()) for words in sets)
    bank_map_injective=len({(w>>7,(w^(w>>7))&127) for w in range(65536)})==65536
    lef=['physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.lef','physical/asap7_memory_macros_v2/ot_sram_2rw_512x64_m4_r2c2/ot_sram_2rw_512x64_m4_r2c2.lef']
    areas=[]
    for name in lef:
        size=re.search(r'SIZE ([0-9.]+) BY ([0-9.]+)',(root/name).read_text());areas.append(float(size[1])*float(size[2]))
    sources+=lef
    result=dict(schema='opentallas.qwen-native-me-control-trace.v1',pass_component=True,profiles=summaries,
        source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in sources},
        negative_ignore_me_clock_enable_rejected=negative,
        inherited_shape=dict(G=6144,SMIN=7,TCUT=7,NXC=2048,NPORT=48,XD=105,ORD=7,MEM_EXTRA=1),
        schedule_scope='One isolated L20 PC20 W1 operation. Source-current ME issue/address/tag/result-control statements. Input instruction is previously committed compiled program. Arithmetic and all non-ME writer families excluded.',
        clock_scope='Component edge sequence; physical_stalls uses directed external clock enables, not the production core admission controller',
        operation_extent_proved=True,whole_workload_extent_proved=False,parent_coissue_proved=False,full_VM_qualified=False,
        folded_bank_OPTION=dict(status='TRACE_SUBSET_MODEL_ONLY',word_address='scalar_address >>4',bank='(word ^ (word>>7)) &127',row='word>>7',inverse='word=(row<<7)|(bank^(row&127))',
            full_1M_scalar_range_injective=bank_map_injective,banks=128,rows_per_bank=512,payload_bits_per_word=512,SECDED_check_bits_per_word=64,
            per_bank_MACs=0,read_bytes_per_bank_cycle=64,write_bytes_per_bank_cycle=64,total_read_reply_bits_per_cycle=65536,
            data_macros=512,check_macros=128,full_payload_bytes=4194304,check_bytes=524288,macro_body_area_mm2=(512*areas[0]+128*areas[1])/1e6,
            observed_ME_read_words_per_bank_peak=peak(readsets),observed_ME_write_words_per_bank_peak=peak(writesets),
            command_controller_mux_fanout_area=None,protected_mutable_control_area=None,slot_fit=False,physical_clock_latency=None,composed_token_latency=None,
            ready_for_RTL=False,missing=['All-writer-family conflict and parent co-issue trace','Real finite captured request/response flow and publication','Same-cycle read-old semantics and source-priority conflicts','Sidecar codec/partial-write service latency','Timing, die tracks and clock/load/floorplan fit']),
        adoption=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(pass_component=True,maximum_old_bank_read_rows=64,maximum_old_bank_write_rows=48,option_read_peak=peak(readsets),option_write_peak=peak(writesets),full_VM_qualified=False)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();run(args.root,args.out)
