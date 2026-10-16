#!/usr/bin/env python3
"""OFF DEFAULT logical epoch proof. Physical/compiler epoch binding UNBOUND."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FILES=['dsfd_wfc_stg_cl.sv','ot_ratio_cdc_fifo.sv','ot_dsrom_mtp_link_pair.sv','ot_dsrom_mtp_skid.sv','ot_dsrom_mtp_rstsync.sv','ot_s81_fixed_issue.sv','ot_s81_fixed_mailbox.sv','dsfd_stage_seq_static_c.sv','dsfd_stage_seq_static_c8.sv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 paths=[a.source/f for f in FILES];pins={f:hashlib.sha256(p.read_bytes()).hexdigest()for f,p in zip(FILES,paths)}
 b=(a.source/'wfc_start_bench.sv').read_text()
 b=b.replace('#(.POSTED(1),.VM_LINK(1),.START_DELAY_S(1))','#(.POSTED(1),.VM_LINK(1),.START_DELAY_S(1),.EPOCH_START_ENABLE(1),.EPOCH_COMMON_RESET_CONTRACT(1),.FIRST_SLOT_S(148),.PERIOD_S(12),.SLOT_COUNT(1))')
 b=b.replace('integer tc=0,','integer mode=0,timing_errors=0,firstcmd=-1,firstkit=-1,firstfault=-1;\n integer tc=0,').replace('sp=0,','sp=3,')
 b=b.replace('if($value$plusargs("SP=%d",sp))begin end','if($value$plusargs("MODE=%d",mode))begin end')
 b=b.replace("if(tc==198+phase)vw=", "if(tc==200+phase)vw=")
 b=b.replace("if(tc==200+phase)cs={1'b1,META};", """if(tc==200+phase&&mode!=1&&mode!=2&&mode!=5)cs={1'b1,META};
  if(mode==2&&tc==240+phase)cs={1'b1,META};
  if(mode==5&&tc==202+phase)cs={1'b1,META};
  if(mode==3&&tc==230+phase)cs={1'b1,META^52'd1};""")
 b=b.replace('if(faultcase&&sc==expected_door)ready=0;','if(mode==4&&sc==expected_door+1)ready=0;')
 b=b.replace('if(sc!=door+1||ks[51:0]!==META)errors=errors+1;','if(sc!=163)timing_errors=timing_errors+1;if(ks[51:0]!==META)errors=errors+1;')
 b=b.replace('if(swd[51:0]!==META)errors=errors+1;',"if(swd[51:0]!==META && !(mode==3&&doors==2&&swd[51:0]===(META^52'd1)))errors=errors+1;")
 b=b.replace('kits=kits+1;if(kd[52:32]','firstkit=sc;kits=kits+1;if(kd[52:32]')
 b=b.replace('commands=commands+1;due=tc+3;','firstcmd=tc;commands=commands+1;due=tc+3;')
 b=b.replace('if(rn&&consumer.u_s.kv)', 'if(rn&&ft[0]&&firstfault<0)firstfault=tc;\n  if(rn&&consumer.u_s.kv)')
 begin=b.index('    if(!cal&&(');end=b.index('\n    $finish;',begin)
 b=b[:begin]+'''    $display("EPOCH_RESULT phase=%0d mode=%0d command_core=%0d kit_serial=%0d firstfault_core=%0d timing_errors=%0d",phase,mode,firstcmd,firstkit,firstfault,timing_errors);
    if(pulses!=1||commands!=1||kits!=1||timing_errors||launch!=163||capture!=192||firstcmd!=261||firstkit!=204||st[5])$fatal(1,"fixed epoch command/KIT schedule moved");
    if(mode==5&&door!=162)$fatal(1,"late metadata not exactly one serial edge after deadline");
    if(mode==0&&(errors||ft))$fatal(1,"normal epoch metadata/fault");
    if(mode!=0&&!ft[0])$fatal(1,"missing static epoch fault");
    if((mode==1||mode==2||mode==5)&&errors==0)$fatal(1,"late/missing metadata was hidden");
    if((mode==3||mode==4)&&errors)$fatal(1,"valid reserved metadata corrupt");
    if((mode==1||mode==2||mode==4||mode==5)&&firstfault>=firstcmd)$fatal(1,"fault missed logical consumer deadline");
''' +b[end:]
 bench=a.out/'tb_wfc_epoch.sv';bench.write_text(b);pins['bench']=hashlib.sha256(b.encode()).hexdigest()
 variants={'positive':paths[0].read_text(),'one_edge_early_slot':paths[0].read_text().replace('epoch_s == next_slot_s',"epoch_s + 32'd1 == next_slot_s"),'wrong_token':paths[0].read_text().replace('pending_meta <= t_swd[SP-1:0];',"pending_meta <= t_swd[SP-1:0] ^ ({{(SP-1){1'b0}},1'b1} << NW);")}
 rows=[]
 for name,src in variants.items():
  v=a.out/name;v.mkdir(exist_ok=True);rtl=v/paths[0].name;rtl.write_text(src)
  r=subprocess.run(['iverilog','-g2012','-s','tb_wfc_start','-o',str(v/'sim'),str(rtl),*map(str,paths[1:]),str(bench)],capture_output=True,text=True)
  (v/'build.log').write_text(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError('compile '+name)
  cases=[(phase,mode)for phase in range(8)for mode in range(5)]if name=='positive'else[(phase,0)for phase in range(8)]
  if name=='positive':cases.append((7,5))
  for phase,mode in cases:
   r=subprocess.run(['vvp',str(v/'sim'),f'+PHASE={phase}',f'+MODE={mode}'],capture_output=True,text=True)
   (v/f'p{phase}_m{mode}.log').write_text(r.stdout+r.stderr)
   m=re.search(r'START_RESULT (.*)',r.stdout);n=re.search(r'EPOCH_RESULT (.*)',r.stdout)
   rows.append(dict(variant=name,phase=phase,mode=mode,rc=r.returncode,start=m.group(1)if m else None,epoch=n.group(1)if n else None))
   if (name=='positive')!=(r.returncode==0):raise RuntimeError('unexpected '+str(rows[-1]))
 rec=dict(schema='opentallas.s81.offdefault-start-epoch.v1',source_sha256=pins,rows=rows,one_fixed_programme_start_phase=3,one_fixed_epoch=dict(FIRST_SLOT_S=148,PERIOD_S=12,SLOT_COUNT=1),production_admissible=False,common_physical_epoch_bound=False,actual_compiler_parameter_producer='UNBOUND',native_physical_image=None,scope='actual vmx_w +40generatedstationsemantics+actualc8PW36; declaredidealcommonreset only; no mappedSRAM in this gate')
 (a.out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print('EPOCH_GATE PASS',len(rows))
if __name__=='__main__':main()
