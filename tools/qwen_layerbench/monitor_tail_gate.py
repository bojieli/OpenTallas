"""Generate the isolated native C0/J0 monitor-tail component gate."""
import argparse,json,subprocess,sys
from pathlib import Path
import programme_store as P
import monitor_tail as M

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--reference',type=Path);ap.add_argument('--programme',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--rom-model',type=Path,required=True);ap.add_argument('--namespace-tool',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[2]
    manifest=a.programme/'rank0/lowered/mu_table_input.json';m=json.loads(manifest.read_text());images=P.logical_images(m);tail=M.tails(m)
    subprocess.run([sys.executable,str(Path(M.__file__)), '--manifest',str(manifest),'--images',str(a.programme/'rank0/masks'),'--out',str(a.out/'masks'),'--emit-masks'],check=True)
    sys.path.insert(0,str(a.namespace_tool.parent));import table_roms as T
    cases={f'tb_monitor.{name}.u_ld.m{k}':f'table_s{s}_m{k}.viamap.hex' for s in (0,1) for name in (f'c{s}',f'o{s}',f'r{s}') for k in range(4)}
    (a.out/'rom.v').write_text(T.namespace(a.rom_model,cases))
    for fn,mod in [('qfd_dv_table_rom_loader.sv','qfd_dv_table_rom_loader'),('qfd_dv_slice_tload.sv','qfd_dv_slice_tload')]:
        source=root/'rtl/qwen_dv'/fn
        (a.out/fn).write_text(source.read_text())
        original=(a.reference/fn).read_text() if a.reference else subprocess.check_output(['git','show',f'HEAD:rtl/qwen_dv/{fn}'],cwd=root,text=True)
        # The unchanged helper definitions are shared with the candidate source.
        original=original.split('endmodule',1)[0]+'endmodule\n'
        original=original.replace('qfd_dv_slice_tload','reference_tload').replace('qfd_dv_table_rom_loader','reference_loader')
        (a.out/('ref_'+fn)).write_text(original)
    counts=[]
    for sid in (0,1):
        lines=[]
        for stage in (1,36):
            for u in range(4):
                words=[images[sid][r] for r in P.read_rows(stage,u)]+tail[sid][2*u:2*u+2]
                valid=[]
                for w in words:
                    if not(w>>1024)&1:continue
                    w=P.relocate_word(w,u,btab_compact=True)
                    valid.append((w&((1<<1024)-1))|((w>>1027)<<1024)|(((w>>1025)&3)<<1048))
                lines+= [f'{w:0263x}' for w in valid]
                counts.append(len(valid))
        (a.out/f'e{sid}.hex').write_text('\n'.join(lines)+'\n')
    n=[counts[0],counts[8]];assert counts==[n[0]]*8+[n[1]]*8
    sv='''`timescale 1ns/1fs
module tb_monitor;
reg ck=0;always #0.4165 ck=~ck;reg rst_n=0;reg[8:0]req=0;reg sw=0;
wire[5:0]we,busy,done,fault;wire[1:0]kind[0:5];wire[23:0]addr[0:5];wire[1023:0]data[0:5];
integer cyc=0,origin=0,caseno=0,st,u,j,checks=0;integer cnt[0:1],firstw[0:1],lastw[0:1],lastbusy[0:3],donedate[0:3];
reg[1049:0]e0[0:N0*8-1],e1[0:N1*8-1];
INSTANCES
initial begin
 $readmemh("E0",e0);$readmemh("E1",e1);
 #0.001;
 if($test$plusargs("MUT_OFF"))begin o0.u_ld.m0.arr[0][0]=~o0.u_ld.m0.arr[0][0];end
 if($test$plusargs("MUT_TAIL"))begin c0.u_ld.m0.arr[477][0]=~c0.u_ld.m0.arr[477][0];end
 if($test$plusargs("MUT_PIDX"))begin c0.u_ld.m3.arr[477][1832]=~c0.u_ld.m3.arr[477][1832];end
 if($test$plusargs("MUT_PAYLOAD"))begin c0.u_ld.m0.arr[0][0]=~c0.u_ld.m0.arr[0][0];end
 repeat(24)@(negedge ck);rst_n=1;repeat(16)@(negedge ck);
 for(st=0;st<2;st=st+1)for(u=0;u<4;u=u+1)begin
  cnt[0]=0;cnt[1]=0;firstw[0]=-1;firstw[1]=-1;lastw[0]=-1;lastw[1]=-1;
  for(j=0;j<4;j=j+1)begin lastbusy[j]=-1;donedate[j]=-1;end
  req={1'b1,(st==0?6'd1:6'd36),2'(u)};if($test$plusargs("MUT_USER"))req[1:0]=2'(u+1);
  origin=cyc+1;@(negedge ck);req=0;repeat(110)@(negedge ck);
  if(cnt[0]!=N0||cnt[1]!=N1||fault!=0)$fatal(1,"COVERAGE %0d/%0d fault%b",cnt[0],cnt[1],fault);
  if(firstw[0]!=5||firstw[1]!=5||lastw[0]!=94||lastw[1]!=94)$fatal(1,"DATES first%0d/%0d last%0d/%0d",firstw[0],firstw[1],lastw[0],lastw[1]);
  for(j=0;j<2;j=j+1)if(lastbusy[j]!=lastbusy[j+2]+2||donedate[j]!=donedate[j+2]+2)$fatal(1,"BUSY_DONE_DATE");
  $display("MONITOR_CASE stage%0d user%0d writes%0d/%0d VMfirst5 last94 busyLast%0d/%0d done%0d/%0d",st==0?1:36,u,cnt[0],cnt[1],lastbusy[0],lastbusy[2],donedate[0],donedate[2]);caseno=caseno+1;
 end
 // A real simultaneous stream/loader write must suppress both and fault.
 req={1'b1,6'd1,2'd0};@(negedge ck);req=0;wait(we[0]);@(negedge ck);sw=1;@(negedge ck);sw=0;repeat(110)@(negedge ck);
 if(!fault[0]||!fault[1])$fatal(1,"COLLISION_NOT_FAULTED");
 $display("MONITOR_TAIL_PASS checks%0d stage1and36 users4 nativeC0J0WE34 period833ps collision",checks);$finish;
end
always @(posedge ck)begin
 cyc=cyc+1;
 if(rst_n)begin
  for(integer k=0;k<4;k=k+1)if(caseno<8)begin if(busy[k])lastbusy[k]=cyc-origin;if(done[k])donedate[k]=cyc-origin;end
  for(integer s=0;s<2;s=s+1)begin
   if({we[2+s],busy[2+s],done[2+s],fault[2+s]}!=={we[4+s],busy[4+s],done[4+s],fault[4+s]})$fatal(1,"DEFAULT_CONTROL_LOCKSTEP");
   if(we[2+s]&&{kind[2+s],addr[2+s],data[2+s]}!=={kind[4+s],addr[4+s],data[4+s]})$fatal(1,"DEFAULT_PAYLOAD_LOCKSTEP");
   if(caseno<8&&we[s])begin
    if(cnt[s]==0)firstw[s]=cyc-origin;
    lastw[s]=cyc-origin;
    if((s==0&&{kind[s],addr[s],data[s]}!==e0[caseno*N0+cnt[s]])||(s==1&&{kind[s],addr[s],data[s]}!==e1[caseno*N1+cnt[s]]))$fatal(1,"PAYLOAD s%0d case%0d index%0d",s,caseno,cnt[s]);
    cnt[s]=cnt[s]+1;checks=checks+1;
   end
   if(sw&&c0.l_we&&we[0])$fatal(1,"COLLISION_NOT_SUPPRESSED");
  end
 end
end
endmodule
'''
    instances=[]
    for sid in (0,1):
        for name,typ,idx,param in [(f'c{sid}','qfd_dv_slice_tload',sid,',.MONITOR_TAIL(1)'),(f'o{sid}','qfd_dv_slice_tload',2+sid,',.MONITOR_TAIL(0)'),(f'r{sid}','reference_tload',4+sid,'')]:
            instances.append(f'{typ} #(.SLICE(0),.CAPTURE_STAGE(0),.LOCAL_JOIN(0){param}) {name}(.ck(ck),.rst_n(rst_n),.treq(req),.s_we(sw),.s_kind(2\'d1),.s_addr(24\'d0),.s_data(1024\'d0),.tw_we(we[{idx}]),.tw_kind(kind[{idx}]),.tw_addr(addr[{idx}]),.tw_data(data[{idx}]),.busy(busy[{idx}]),.done(done[{idx}]),.fault(fault[{idx}]));')
    for key,val in {'INSTANCES':'\n'.join(instances),'N0':str(n[0]),'N1':str(n[1]),'E0':str(a.out/'e0.hex'),'E1':str(a.out/'e1.hex')}.items():sv=sv.replace(key,val)
    (a.out/'tb.sv').write_text(sv)
    (a.out/'scope.json').write_text(json.dumps(dict(source='current C0/J0 inline body',positive_writes=sum(n)*8,VM_first=5,VM_last=94,not_qualified=['real CALR TREQ producer','global earliest ANY PROG','SU execution of monitor copies','RP1 write timing','physical re-sign']),indent=2)+'\n')

if __name__=='__main__':main()
