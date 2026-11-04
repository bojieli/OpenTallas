#!/usr/bin/env python3
"""Prepare actual cached native ROOT with AMAX prearm and lease controls.

No job is launched; all native k79/FDN/RP/CTL/calendar bodies are unchanged.
Only fixture scalar-chain input/TOK observation and runtime cfg.amnb vary.
"""
import argparse,hashlib,json,shutil
from pathlib import Path


def one(s,a,b):
    if s.count(a)!=1:raise ValueError('exact cached fixture anchor differs: '+a[:80])
    return s.replace(a,b)


def prepare(base,out):
    out.mkdir(parents=True,exist_ok=False);d=out/'src';d.mkdir();sources=[];native={}
    for name in (base/'source.f').read_text().splitlines():
        src=base/'src'/Path(name).name;p=d/src.name;s=src.read_text()
        if src.name=='native_root_component.sv':
            s=one(s,'input wire red_we,input wire[23:0]red_addr,input wire[31:0]red_data,',
                  'input wire red_we,input wire[23:0]red_addr,input wire[31:0]red_data,input wire[47:0]am_chain,\n output wire tok_v,tok_own,output wire[23:0]tok_idx,output wire[31:0]tok_val,output wire[1:0]tok_user,')
            s=one(s,' wire tok_v,tok_own;wire[23:0]tok_idx;wire[31:0]tok_val;wire[1:0]tok_user;','')
            s=one(s,".sc_cfg(sc_cfg),.dn_i(48'd0)",'.sc_cfg(sc_cfg),.dn_i(am_chain)')
        elif src.name=='tb_native_root.sv':
            s=one(s,' wire[100:0]cfg;', ' reg[47:0]am_chain=0;wire tok_v,tok_own;wire[23:0]tok_idx;wire[31:0]tok_val;wire[1:0]tok_user;\n integer legacy=0,tokens=0,token_count=0;reg[31:0]am_values[0:5];\n wire[100:0]cfg;')
            s=one(s,'.sc_cfg(cfg),.sc_busy(busy)', '.am_chain(am_chain),.tok_v(tok_v),.tok_own(tok_own),.tok_idx(tok_idx),.tok_val(tok_val),.tok_user(tok_user),\n .sc_cfg(cfg),.sc_busy(busy)')
            s=one(s,"(116'(rx)<<36)|(116'h358637bd<<60)|(116'd12<<92);", "(116'(rx)<<36)|(116'h358637bd<<60)|(116'd12<<92)|(116'(legacy?0:6)<<97);")
            s=one(s,'  if(cfg[100])begin', '  if(tok_v)begin\n   if(legacy||tok_user!==2\'(active)||tok_idx!==24\'d101||tok_val!==32\'h40800000||!tok_own)$fatal(1,"PREARM_TOKEN_PAYLOAD user%0d idx%0d val%h own%b",tok_user,tok_idx,tok_val,tok_own);\n   tokens=tokens+1;token_count=token_count+1;$display("PREARM_AMAX_TOKEN user%0d idx%0d value%h",tok_user,tok_idx,tok_val);\n  end\n  if(cfg[100])begin')
            s=one(s,'  late=$test$plusargs("LATE_CFG");', '  legacy=$test$plusargs("LEGACY_AMNB0");\n  am_values[0]=32\'h3f800000;am_values[1]=32\'h40800000;am_values[2]=32\'h40000000;am_values[3]=32\'h40800000;am_values[4]=32\'h40400000;am_values[5]=0;\n  late=$test$plusargs("LATE_CFG");')
            s=one(s,'   repeat(32)@(negedge ck);if(busy||seen!=1)$fatal(1,"NATIVE_ROOT_LEASE_DRAIN");', '''   repeat(32)@(negedge ck);if(busy||seen!=1)$fatal(1,"NATIVE_ROOT_LEASE_DRAIN");
   // No intervening cfg: the residual ROOT cfg must already arm HEAD AMAX.
   token_count=0;
   for(j=0;j<6;j=j+1)begin
    am_chain=(48'd1<<47)|(48'd3<<44)|(48'(u)<<32)|48'((j==1)?103:(j==3)?101:100+j);@(negedge ck);
    am_chain=(48'd1<<47)|(48'd4<<44)|(48'(u)<<32)|48'(am_values[j]);
    if($test$plusargs("MUT_AMAX_USER")&&u==1&&j==2)am_chain=am_chain^(48'd1<<32);
    @(negedge ck);am_chain=0;repeat(8)@(negedge ck);
    if(j<5&&token_count)$fatal(1,"PREARM_EARLY_TOKEN count%0d",j+1);
   end
   repeat(32)@(negedge ck);
   if(token_count!=(legacy?0:1))$fatal(1,"PREARM_TOKEN_COUNT user%0d got%0d legacy%0d",u,token_count,legacy);''')
            s=one(s,'  $display("NATIVE_ROOT_FOUR_CASES_PASS outputs%0d",outputs);$finish;', '  if(tokens!=(legacy?0:4))$fatal(1,"PREARM_ALL_TOKEN_COUNT");\n  $display("NATIVE_ROOT_FOUR_CASES_PASS outputs%0d",outputs);\n  $display("NATIVE_PREARM_ROOT_PASS amnb%0d rstd%0d tokens%0d",legacy?0:6,outputs,tokens);$finish;')
        else:native[src.name]=hashlib.sha256(src.read_bytes()).hexdigest()
        p.write_text(s);sources.append(p)
    for name in ('defines.f','psum.hex','rstd.hex'):shutil.copy2(base/name,out/name)
    shutil.copy2(Path(__file__).with_name('run_root_prearm_gate.sh'),out/'run_gate.sh')
    (out/'source.f').write_text(''.join(str(p.relative_to(out))+'\n'for p in sources))
    report=dict(status='PREP_ONLY_NOT_LAUNCHED',unchanged_native_sources=native,source_files=len(sources),source_bytes=sum(p.stat().st_size for p in sources),
                cases='baselineamnb0 and prearm6, four native RSTD + six tagged AMAX candidates/user, lower-index tie',controls=['COLLECT_CFG','LATE_CFG','MUT_AMAX_USER'],
                boundary='actual native scalar,FDN,RP,CTL,calendar; external PSUM and scalar-chain AMI/AMV; no full HEAD transport or token')
    (out/'preparation.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'packet.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(out))+'\n'for p in sorted(out.rglob('*'))if p.is_file()))
    return report

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--base',type=Path,required=True);a.add_argument('--out',type=Path,required=True);v=a.parse_args();r=prepare(v.base,v.out)
    print(json.dumps({k:r[k]for k in ('status','source_files','source_bytes')}))
