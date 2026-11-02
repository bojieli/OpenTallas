from pathlib import Path
import argparse,json,re,hashlib
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
records=[];sv=[]
for name,root in [('ot_qfd_ucie_x64_phy','nface_tall_g5_lclk_1020'),('ot_qfd_serdes_112g_x12_phy_s597','nface_tall_1017')]:
 d=a.source/'physical/qwen_missing_phy'/root/name
 abi=d/(name+'_bb.v');doc=d/(name+'.json');meta=json.loads(doc.read_text());fdi=meta['fdi'];fw=int(fdi['flit_bits']);lat=int(fdi['latency_fdi_cycles_one_way'])
 assert (fw,lat)==((1043,4) if 'ucie' in name else (597,223))
 text=abi.read_text().replace('`timescale 1ns/1ps','`timescale 1ns/1fs').replace('(* blackbox *)','')
 body=f'''
    // Explicit quiescent external service only. Missing peer data is never
    // replaced by a numeric token result or by TX loopback.
    integer bringup_only;
    initial begin
        bringup_only=0;
        if (!$value$plusargs("QC_PHY_BRINGUP_ONLY=%d",bringup_only) || bringup_only!=1)
            $fatal(1,"QC_PHY_PROVIDER_REQUIRED %m: explicit bringup-only mode or real external provider required");
        $display("QC_PHY_BRINGUP_ONLY %m FW={fw} LAT={lat} UP=16 peer=NATIVE_REQUIRED");
    end
    always @(posedge clk)
        if(rst_n && tx_v) $fatal(1,"QC_PHY_MISSION_PROVIDER_REQUIRED %m: quiescent model refuses mission TX");
    wire unused_link_v;
    wire [{fw-1}:0] unused_link_flit;
    ot_qkvd_ucie_x64_phy_model #(.FW({fw}),.LAT({lat}),.UP(16)) u_model (
        .clk(clk),.rst_n(rst_n),.tx_up(tx_up),.tx_v(tx_v),.tx_flit(tx_flit),
        .rx_v(rx_v),.rx_flit(rx_flit),.link_v(unused_link_v),.link_flit(unused_link_flit),
        .far_v(1'b0),.far_flit({fw}'d0));
'''
 if 'ucie' in name:
  assert fdi['clock_ghz']==1.0 and fdi['clock_output']['ghz']==1.0
  body+='    reg generated_lclk=0; always #0.5 generated_lclk=~generated_lclk; assign lclk=generated_lclk;\n'
 text=text.replace('endmodule',body+'endmodule')
 sv.append(text)
 records.append(dict(module=name,ABI=str(abi),ABI_sha256=hashlib.sha256(abi.read_bytes()).hexdigest(),metadata=str(doc),metadata_sha256=hashlib.sha256(doc.read_bytes()).hexdigest(),fdi=fdi,scope='Quiescent reset/clock/ROM bringup only; mission TX is rejected.'))
(a.out/'qc_phy_bringup.sv').write_text('\n'.join(sv))
model=a.source/'physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv'
(a.out/'registered_fdi_model.sv').write_bytes(model.read_bytes())
(a.out/'manifest.json').write_text(json.dumps(dict(scope='External licensed-PHY boundary service only; no die logic replacement or token verdict',qualified_model_source=str(model),qualified_model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),hardware_added_cycles=0,macro_records=records,native_required=['TP8 collective UCIe real peer service','three SerDes real peer/host services'],whole_programme_qualified=False),indent=2)+'\n')
(a.out/'tb_phy_bringup.sv').write_text('''`timescale 1ns/1fs
module tb_phy_bringup;
reg ck=0;always #0.4165 ck=~ck;reg rst_n=0,tx_v=0;wire lclk,uup,sup,uv,sv;wire[1042:0]ud;wire[596:0]sd;
ot_qfd_ucie_x64_phy u(.lclk(lclk),.clk(lclk),.rst_n(rst_n),.tx_up(uup),.tx_v(tx_v),.tx_flit(1043'd0),.rx_v(uv),.rx_flit(ud));
ot_qfd_serdes_112g_x12_phy_s597 s(.clk(lclk),.rst_n(rst_n),.tx_up(sup),.tx_v(1'b0),.tx_flit(597'd0),.rx_v(sv),.rx_flit(sd));
realtime last_u=0;integer edges=0;
always @(posedge lclk)begin
 if(last_u!=0 && $realtime-last_u!=1.0)$fatal(1,"PHY_CLOCK_MISMATCH");last_u=$realtime;edges=edges+1;
end
initial begin
 repeat(4)@(negedge ck);rst_n=1;repeat(80)@(negedge ck);
 if(!uup||!sup||uv||sv||ud!==0||sd!==0||edges<64)$fatal(1,"PHY_BRINGUP_MISMATCH");
 if($test$plusargs("MUT_TX"))begin tx_v=1;repeat(4)@(negedge ck);$fatal(1,"MISSION_GUARD_MISSED");end
 rst_n=0;#0.001;if(uup||sup||uv||sv)$fatal(1,"PHY_RESET_FLUSH_MISMATCH");
 $display("PHY_BRINGUP_PASS declaredPHY1000ps drivercore833ps registeredFDI resetUP16 missionGuard");$finish;
end
endmodule
''')
