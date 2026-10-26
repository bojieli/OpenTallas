#!/usr/bin/env python3
"""Prepare a minimum actual-ENG-wrapper transport probe, not an arithmetic/token qualification."""
import argparse,copy,json,re,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import native_istations


def prepare(base,trial,plan,cfgsource,out):
    out.mkdir(parents=True,exist_ok=False)
    typ=json.loads(plan.read_text())['partition_types']['eng__t1']
    text=trial.read_text();module='s81p_eng__t1'
    (out/'rtl').mkdir()
    target=out/'rtl'/(module+'.sv');target.write_text(text)
    # Exactly the OUT emitter used by bind, applied to the actual emitted
    # engine parent (whose IN pads already came from the strict bind).
    actual=[]
    for entry in native_istations.source_entries(typ):
        name=entry['conn'][4:]
        matches=re.findall(r'ot_dp_ste?\s+#\(\.W\((\d+)\)\)\s+u_bout_'+re.escape(name)+r'\b',text)
        if len(matches)!=1:raise ValueError('actual source face width not unique: '+name)
        actual.append(dict(oname=name,width=int(matches[0])))
    b=SimpleNamespace(types={'eng__t1':typ},ab={'internal_stations_types':['eng__t1']},
        by_type={'eng__t1':['eng']},out_bus={'eng':actual})
    native_istations.materialize(b,'eng__t1',target)
    cand=target.read_text()
    def renamed(t,name):return re.sub(r'\bmodule\s+s81p_eng__t1\b','module '+name,t,count=1)
    (out/'base.sv').write_text(renamed(base.read_text(),'eng_base'))
    (out/'trial.sv').write_text(renamed(cand,'eng_trial'))
    # A concrete wrong implementation: FKS payload stays registered, but its
    # epoch bypasses the newly added receiver pad. The comparator must catch it.
    mut=re.sub(r'\.q\(\{unit_i1_eq,\s*unit_i1_q\}\)',
               '.q({mut_unused_epoch, unit_i1_q})',cand,count=1)
    if mut==cand:raise ValueError('actual FKS pad output not found')
    mut=mut.replace('    wire unit_i1_eq;','    wire unit_i1_eq;\n    wire mut_unused_epoch;\n    assign unit_i1_eq=unit_i1_eb;',1)
    (out/'mut.sv').write_text(renamed(mut,'eng_mut'))
    cfg=re.search(r'(?ms)^module dsdv_eng_cfg\b.*?^endmodule\b',cfgsource.read_text())
    if not cfg:raise ValueError('actual configuration control not found')
    (out/'cfg.sv').write_text('`timescale 1ps/1fs\n'+cfg.group(0)+'\n')
    (out/'arith_stubs.sv').write_text('''`timescale 1ps/1fs
module dsdv_eng_rr_e #(parameter integer RETURN_AGE=640,parameter[29:0]PCBASE=0,parameter integer XQ_MUT=0)(
input wire ck,rst_n,cfg_en,cfg_layer,input wire[1:0]cfg_rank,input wire[52:0]f_ks,
output wire[38:0]rco,input wire[263:0]pci,input wire[275:0]vi_s,output wire[275:0]vo_s,
input wire[275:0]vi_n,output wire[275:0]vo_n,output wire[3:0]st,output wire[67:0]hx_w,input wire[1151:0]hx_res);
assign rco=pci[38:0];assign vo_s=vi_s;assign vo_n=vi_n;assign st=0;assign hx_w=0;
endmodule
module dsdv_eng_rr_h0(input wire ck,input wire[67:0]in_w,output wire[575:0]out_res);assign out_res=0;endmodule
module dsdv_eng_rr_h1(input wire ck,input wire[67:0]in_w,output wire[575:0]out_res);assign out_res=0;endmodule
''')
    ports='''.clk(clk),.arst_n(arst_n),.unit_i0(pci),.unit_i1(fks),.xtier_i0(vis),.xtier_i1(vin),
.flt_o0({prefix}flt),.unit_o0({prefix}rco),.xtier_o0(),.xtier_o1(),.ft0_i(1369'd0),.ft0_o(),.ft1_i(1121'd0),.ft1_o()'''
    inst='\n'.join(f'eng_{kind} {name} ({ports.format(prefix=name+"_")});'for kind,name in [('base','b'),('trial','d'),('mut','m')])
    tb='''`timescale 1ps/1fs
module tb;
reg clk=0;always #416.5 clk=~clk;
reg arst_n=0;reg[264:0]pci=0;reg[53:0]fks=0;reg[276:0]vis=0,vin=0;
wire[1:0]b_flt,d_flt,m_flt;wire[39:0]b_rco,d_rco,m_rco;
INSTANCES
integer cyc=0,checks=0,stage_errors=0,coherence_errors=0,output_epoch_errors=0,mutant_epoch_errors=0,cfgfault_seen=0;
reg[263:0]hpci[0:2];reg[52:0]hfks[0:1];reg[275:0]hvis[0:1];
reg he_pci[0:2];reg he_fks[0:1];reg he_vis[0:1];reg[37:0]hrco[0:3];reg hv[0:3];reg hcf[0:2];
always @(negedge clk)begin
cyc=cyc+1;if(cyc==8)arst_n=1;
pci[263:0]={8'(cyc^8'h5a),{8{32'hac1d1234^cyc}}};pci[38:1]={6'(cyc^6'h2d),32'(32'ha51d6937^(cyc*32'h37a38df1))};pci[0]=(cyc%5)==1;pci[264]=(cyc%7)<3;
fks[51:0]={20'(cyc^20'hab739),32'(32'h91a53647^(cyc*32'h85632bad))};fks[52]=cyc>140 && (cyc%13)==2;fks[53]=(cyc%11)<5;
vis[275:0]={20'(cyc^20'ha5331),{8{32'h31ba7351^cyc}}};vis[3:1]=3;vis[0]=(cyc%4)<2;vis[276]=(cyc%9)<4;
vin[275:0]={20'(cyc^20'h57621),{8{32'hca6291b5^cyc}}};vin[3:1]=3;vin[0]=(cyc%6)<3;vin[276]=(cyc%3)==1;
end
always @(posedge clk)begin
#0.001;
for(integer i=2;i>0;i=i-1)begin hpci[i]=hpci[i-1];he_pci[i]=he_pci[i-1];hcf[i]=hcf[i-1];end
hpci[0]=b.u_u_e.pci;he_pci[0]=b.unit_i0_eq;hcf[0]=d.w_u_cfg_fault;
hfks[1]=hfks[0];hfks[0]=b.u_u_e.f_ks;he_fks[1]=he_fks[0];he_fks[0]=b.unit_i1_eq;
hvis[1]=hvis[0];hvis[0]=b.u_u_e.vi_s;he_vis[1]=he_vis[0];he_vis[0]=b.xtier_i0_eq;
for(integer i=3;i>0;i=i-1)begin hrco[i]=hrco[i-1];hv[i]=hv[i-1];end
hrco[0]=b_rco[37:0];hv[0]=b_flt[0];
if(d_flt[1]!==d_rco[39])output_epoch_errors=output_epoch_errors+1;
if(cyc>80)begin
 checks=checks+1;
 if(d.u_u_e.pci!==hpci[2] || d.unit_i0_eq!==he_pci[2] || d.u_u_e.f_ks!==hfks[1] || d.unit_i1_eq!==he_fks[1] || d.u_u_e.vi_s!==hvis[1] || d.xtier_i0_eq!==he_vis[1] || d.u_u_e.vi_n!==b.u_u_e.vi_n || d_rco[37:0]!==hrco[3] || d_rco[38]!==hcf[2])stage_errors=stage_errors+1;
 if(d_flt[0]!==hv[3])coherence_errors=coherence_errors+1;
 if(m.unit_i1_eq!==he_fks[1])mutant_epoch_errors=mutant_epoch_errors+1;
 if(d_rco[38])cfgfault_seen=cfgfault_seen+1;
end
if(cyc==400)begin
$display("ENGF_TRANSPORT checks=%0d errors=%0d cfgfault_seen=%0d verdict=%s",checks,stage_errors,cfgfault_seen,stage_errors==0?"PASS":"FAIL");
$display("ENGF_RCO_COHERENCE valid_data_mismatches=%0d output_epoch_mismatches=%0d verdict=%s",coherence_errors,output_epoch_errors,(coherence_errors==0 && output_epoch_errors==0)?"PASS":"FAIL");
$display("ENGF_EPOCH_MUTANT mismatches=%0d verdict=%s",mutant_epoch_errors,mutant_epoch_errors>0?"CAUGHT":"MISSED");
if(stage_errors!=0 || mutant_epoch_errors==0 || cfgfault_seen==0)$fatal(1,"transport probe failed");
$finish;
end
end
endmodule
'''.replace('INSTANCES',inst)
    (out/'tb.sv').write_text(tb)
    print(json.dumps(dict(scope='TRANSPORT_ONLY_ARITHMETIC_STUBS_REAL_PARENT_AND_CFG',out=str(out))))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('base','trial','plan','cfgsource','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prepare(a.base,a.trial,a.plan,a.cfgsource,a.out)


if __name__=='__main__':main()
