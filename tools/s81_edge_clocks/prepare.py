#!/usr/bin/env python3
"""Prepare minimum actual edge-category clock/reset connection proof.
Normal fullshape capture and XIO benches retain their independent original
scoreboards, adapted only at the category pin interface. No VM core is built.
"""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'))
import die_port_bind as D

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--leaf-commit',default='de6ef76d6');ap.add_argument('--baseline',default='d066faae2');a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 vm=R/'rtl/dsrom_sys/s81_ph/vm';test=R/'rtl/dsrom_sys/s81_ph/test';hashes={}
 names=['dsfd_vm_static_cap.sv','dsfd_vm_static_wfc.sv','dsfd_vm_static_xio.sv','dsfd_vm_static_capl.sv','ot_s81_vm_x34.sv','ot_s81_vm_x43.sv']
 for n in names:
  data=(vm/n).read_bytes();(a.out/n).write_bytes(data);hashes[n]=hashlib.sha256(data).hexdigest()
 for n in ['dsfd_vm_static_cap_leaf.sv','dsfd_vm_static_capl_pipe.sv']:
  data=subprocess.check_output(['git','show',a.leaf_commit+':rtl/dsrom_sys/s81_ph/vm/'+n],cwd=R);(a.out/n).write_bytes(data);hashes[n]=hashlib.sha256(data).hexdigest()
 clockmap={};resetmap={};observers=[];robs=[];c=0;r=0
 def cat(prefix,module,ports,func,params=''):
  nonlocal c,r
  cons=[]
  for name,width,kind,path in ports:
   start=c if kind=='clock' else r;vec='clocks' if kind=='clock' else 'resets'
   cons.append(f'.{name}({vec}[{start}]' + ')' if width==1 else f'.{name}({vec}[{start} +: {width}])')
   for j in range(width):
    ix=start+j;target=path.format(g=j)
    if kind=='clock':observers.append((ix,target));clockmap[str(ix)]=dict(top_instance=prefix,category=name,bit=j,target=target)
    else:robs.append((ix,target));resetmap[str(ix)]=dict(top_instance=prefix,category=name,bit=j,target=target)
   if kind=='clock':c+=width
   else:r+=width
  cons+=func
  return module+params+' '+prefix+' ('+',\n'.join(cons)+');\n'
 capports=[('ck_control_s',1,'clock','cap.ck_control_s'),('ck_lane_s',16,'clock','cap.lane[{g}].u_l.ck'),('ck_x34_s',16,'clock','cap.lane[{g}].u_x.s_ck'),('ck_x34_t',16,'clock','cap.lane[{g}].u_x.t_ck'),('rst_control_s',1,'reset','cap.rst_control_s'),('rst_x34_s',16,'reset','cap.lane[{g}].u_x.s_rst_n'),('rss_x34_t',16,'reset','cap.lane[{g}].u_x.t_rst_n')]
 wports=[(n,1,'clock','wfc.'+p) for n,p in [('ck_control_s','ck_control_s'),('ck_control_t','ck_control_t'),('ck_x34_s','u_xi.s_ck'),('ck_x34_t','u_xi.t_ck'),('ck_x43_s','u_xo.s_ck'),('ck_x43_t','u_xo.t_ck')]]+[(n,1,'reset','wfc.'+p) for n,p in [('rst_control_s','rst_control_s'),('rss_control_t','rss_control_t'),('rst_x34_s','u_xi.s_rst_n'),('rss_x34_t','u_xi.t_rst_n'),('rst_x43_s','u_xo.s_rst_n'),('rss_x43_t','u_xo.t_rst_n')]]
 xports=[('ck_control_s',1,'clock','xio.ck_control_s'),('ck_control_t',1,'clock','xio.ck_control_t'),('ck_x43_s',2,'clock','xio.u_x{g}.s_ck'),('ck_x43_t',2,'clock','xio.u_x{g}.t_ck'),('rst_control_s',1,'reset','xio.rst_control_s'),('rss_control_t',1,'reset','xio.rss_control_t'),('rst_x43_s',2,'reset','xio.u_x{g}.s_rst_n'),('rss_x43_t',2,'reset','xio.u_x{g}.t_rst_n')]
 xports=[(n,w,k,p.replace('u_x{g}','u_xq') if w==1 else p) for n,w,k,p in xports]
 body=cat('cap','dsfd_vm_static_cap',capports,[".f_capture(13376'd0)"],params=' #(.CAP_PIPE(0))')
 body+=cat('wfc','dsfd_vm_static_wfc',wports,[".f_wfc(560'd0)",".e_v(4'd0)",".e_d(2048'd0)",".vm_fault(1'b0)"])
 body+=cat('xio','dsfd_vm_static_xio',xports,[".n_v(1'b0)",".n_d(84'd0)",".e_v(4'd0)",".e_d(2048'd0)",".f_collective(2204'd0)",".f_crq(15'd0)",".f_xgo(11'd0)",".qSWs(3'b011)"])
 # xio's two CDC instances are named u_xq/u_xg, not generated.
 observers=[(i,p.replace('u_x0','u_xq').replace('u_x1','u_xg')) for i,p in observers];robs=[(i,p.replace('u_x0','u_xq').replace('u_x1','u_xg')) for i,p in robs]
 for entry in list(clockmap.values())+list(resetmap.values()):entry['target']=entry['target'].replace('u_x0','u_xq').replace('u_x1','u_xg')
 assert (c,r)==(61,45),(c,r)
 tb='''`timescale 1ns/1ps
module tb_edge_clock_categories;
reg [60:0] clocks=0;reg [44:0] resets=0;integer counts[0:60];wire [44:0] observed_reset;integer i,j,bad=0;
'''+body
 for i,p in observers:tb+=f'always @(posedge {p}) counts[{i}]=counts[{i}]+1;\n'
 for i,p in robs:tb+=f'assign observed_reset[{i}]={p};\n'
 tb+='''initial begin
 for(i=0;i<61;i=i+1)counts[i]=0;
 #2;resets='1;#2;
 // One pulse per actual external category bit. Check all actual child pins.
 for(i=0;i<61;i=i+1)begin
  clocks[i]=1;#1;clocks[i]=0;#1;
  for(j=0;j<61;j=j+1)if(counts[j]!==((j<=i)?1:0))begin bad=bad+1;if(bad<5)$display("CLOCK_BIND_MISMATCH pulse%0d observed%0d count%0d",i,j,counts[j]);end
 end
 for(i=0;i<45;i=i+1)begin
  resets='1;resets[i]=0;#1;
  if(observed_reset!==resets)begin bad=bad+1;if(bad<5)$display("RESET_BIND_MISMATCH pin%0d",i);end
 end
 $display("EDGE_BIND_RESULT clocks61 resets45 bad%0d",bad);
 if(bad==0)$display("EDGE_BIND_PASS");else $display("EDGE_BIND_FAIL");$finish;
end
endmodule
''';(a.out/'tb_edge_clock_categories.sv').write_text(tb)
 # Pure renaming proof: module sequential/combinational body is unchanged.
 norm={}
 for n in names[:3]:
  current=(a.out/n).read_text();old=subprocess.check_output(['git','show',a.baseline+':rtl/dsrom_sys/s81_ph/vm/'+n],cwd=R,text=True)
  def body_norm(s,changed):
   s=D._lexical_mask(s);s=s[s.index(');',s.index('module '))+2:]
   if changed:
    s=re.sub(r'ck_(?:control|lane|x34|x43)_s(?:\[[^]]+\])?','ck',s)
    s=re.sub(r'ck_(?:control|x34|x43)_t(?:\[[^]]+\])?','cks',s)
    s=re.sub(r'rst_(?:control|x34|x43)_s(?:\[[^]]+\])?','rst',s)
    s=re.sub(r'rss_(?:control|x34|x43)_t(?:\[[^]]+\])?','rss',s)
    s=s.replace(', .PIPE(CAP_PIPE)','')
   return re.sub(r'\s+','',s)
  equal=body_norm(current,True)==body_norm(old,False);assert equal,n
  norm[n]=dict(body_equal_after_clock_reset_pin_rename=True,baseline=a.baseline,baseline_sha256=hashlib.sha256(old.encode()).hexdigest(),new_sha256=hashes[n],cap_pipe_default=0 if n.endswith('_cap.sv') else None)
 # Adapt independent original cap/XIO benches only at their DUT pin hookups.
 for n in ['tb_dsfd_vm_static_cap.sv','tb_dsfd_vm_static_xio.sv']:
  s=(test/n).read_text()
  if '_cap.' in n:s=s.replace('.ck(s_ck), .rst(rst), .cks(t_ck), .rss(rss)', '.ck_control_s(s_ck), .rst_control_s(rst), .ck_lane_s({16{s_ck}}), .ck_x34_s({16{s_ck}}), .rst_x34_s({16{rst}}), .ck_x34_t({16{t_ck}}), .rss_x34_t({16{rss}})')
  else:s=s.replace('.cks(cks),.rss(rss),.ck(ck),.rst(rst)', '.ck_control_t(cks),.rss_control_t(rss),.ck_control_s(ck),.rst_control_s(rst),.ck_x43_t({2{cks}}),.rss_x43_t({2{rss}}),.ck_x43_s({2{ck}}),.rst_x43_s({2{rst}})')
  (a.out/n).write_text(s)
 # Actual wiring mutant: collapse WFC incoming CDC stream root to control.
 orig=(a.out/'dsfd_vm_static_wfc.sv').read_text();needle='.t_ck(ck_x34_t)';assert orig.count(needle)==1
 (a.out/'dsfd_vm_static_wfc_mut.sv').write_text(orig.replace(needle,'.t_ck(ck_control_t)'))
 (a.out/'source_receipt.json').write_text(json.dumps(dict(schema='opentallas.s81.edge-category-clock-proof-input.v1',source_hashes=hashes,leaf_dependency=a.leaf_commit,normalized_body_proof=norm,clocks=clockmap,resets=resetmap,scope='Actual61clock/45rawresetconnectivity plus unchangedmodulebodyproof and independent fullshapeCAP_PIPE0/XIObenches. No phase/pin/CTS/physicalqualification; capture16rn leaves stillconsumeparent2edge release.'),indent=2)+'\n')
 print('PREPARE_PASS clocks61 resets45 normalized3modulebodies unchanged')
if __name__=='__main__':main()
