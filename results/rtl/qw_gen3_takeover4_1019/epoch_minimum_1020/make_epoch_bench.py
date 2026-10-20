from pathlib import Path
import json,re,math,hashlib
p=Path(__file__).resolve().parent; cone=json.loads((p/'lnk_native_tx_slot_reset_cone.json').read_text());dst=p/'epoch_src'
masters={}
for f in ['regenerated_masters.sv']:
 for m in re.finditer(r'^module\s+(\w+)\b.*?\bendmodule', (dst/f).read_text(), re.S|re.M):masters[m[1]]=m[0]
used=set();inst=[];nets=set();clocks=[]
for line in cone['exact_instances']:
 m=re.match(r'(\w+)\s+(\w+)\s+\(',line);master,name=m.groups();used.add(master)
 ports=dict(re.findall(r'\.(\w+)\((\w+)\)',line))
 for port,net in ports.items():
  if port in ['clk','ck','ckf']:
   ck='probe_ck_'+str(len(clocks));clocks.append((name+'/'+port,ck))
   line=line.replace('.'+port+'('+net+')','.'+port+'('+ck+')')
  else:nets.add(net)
 inst.append(line)
for pin,name in [('rly_lnk_native_tx_slot_0/ck_s','source_ck'),('rly_lnk_native_tx_slot_0/ck','receiver_ck')]:clocks.append((pin,name))
assert used <= set(masters) | {'qfd_rstsync','qfd_rstseq'}, used-set(masters)
(dst/'selected_masters.sv').write_text('`timescale 1ns/1ps\n'+'\n'.join(masters[m]for m in sorted(used)if m in masters)+'\n')
# qfd_rstsync/qfd_rstseq are taken directly from actual qfd_link_slots.sv; reset behavior is not reconstructed.
for corner in ['tt','ff']:
 arr={}
 for line in(p/f'probe_{corner}.tsv').read_text().splitlines():
  a=line.split();assert len(a)==4,a;arr[a[0]]=float(a[2])
 assert all(pin in arr and math.isfinite(arr[pin]) and abs(arr[pin])<1e8 for pin,_ in clocks)
 T=.833333; phi=arr['rly_lnk_native_tx_slot_0/ck']-arr['rly_lnk_native_tx_slot_0/ck_s']
 # The identical L is selected from BOTH corner phases, with 150/100 ps reservations.
 phis=[]
 for cc in ['tt','ff']:
  ar={a[0]:float(a[2]) for a in(l.split()for l in(p/f'probe_{cc}.tsv').read_text().splitlines())}
  phis.append(ar['rly_lnk_native_tx_slot_0/ck']-ar['rly_lnk_native_tx_slot_0/ck_s'])
 L=max(math.ceil((1.25*833.333+150-v)/833.333+1)for v in phis)
 assert all(1.25*833.333+150 <=(L-1)*833.333+v<=4.125*833.333-100 for v in phis)
 src=['`timescale 1ns/1ps','module tb;','real T=0.833333;']
 for pin,name in clocks:src.append(f'reg {name}=0; initial begin #{arr[pin]/1000.:.9f}; forever begin {name}=1; #(0.4166665); {name}=0; #(0.4166665); end end')
 src+=['reg n_rst_fwd=0;']
 src+=['wire '+n+';' for n in sorted(nets-{'n_rst_fwd'})]
 src+=inst
 src+=['integer se=-1,re=-1,G=-999,R0=-999,checks=0,errors=0,flts=0;','reg data_bit=0; integer K=0,mode=0,unused;','wire out_bit,fault;',f'localparam integer L={L};',
       "function automatic bit word_at(input integer e); word_at=(16'ha6c5 >> (e & 15)) & 1; endfunction",
       'always @(posedge source_ck) begin se=se+1; data_bit <= word_at(se); end',
       'always @(posedge receiver_ck) begin re=re+1; #0.002; if(mode==1 && R0 != -999 && re>R0+32) begin checks=checks+1; if(out_bit !== word_at(re-L)) errors=errors+1; if(fault) flts=flts+1; end end',
       'always @(posedge n_rst_d2d__fo1__r3__t78) G=se;',
       'always @(posedge n_rst_seq__t55) R0=re;',
       'ot_qfd_land8 #(.W(1),.ICG(0)) dut (.ck_s(source_ck),.en(n_rst_d2d__fo1__r3__t78),.i(data_bit),.ck(receiver_ck),.rs(n_rst_seq__t55),.k(K[3:0]),.o(out_bit),.fault(fault));',
       'initial begin unused=$value$plusargs("mode=%d",mode); unused=$value$plusargs("K=%d",K); #(500*T); n_rst_fwd=1; #(2300*T);',
       f' $display("EPOCH_TRACE {corner} G=%0d R0=%0d L=%0d K=%0d formula=%0d checks=%0d errors=%0d faults=%0d",G,R0,L,K,(L+G-R0-1)&15,checks,errors,flts);',
       'if(G == -999 || R0 == -999) $fatal(1,"MISSING_RAW_EPOCH");',
       'if(mode==1 && (K != ((L+G-R0-1)&15) || checks<100 || errors!=0 || flts!=0)) $fatal(1,"NATIVE_EPOCH_RTL_FAIL");',
       '$finish; end','endmodule']
 (dst/f'tb_{corner}.sv').write_text('\n'.join(src)+'\n')
print(json.dumps(dict(cells=len(inst),clock_pins=len(clocks),source='actualGEN6f78resetRTL+nativeD8RTL',L=L,qualified=False)))
