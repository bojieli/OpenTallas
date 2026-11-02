"""Private two-peer macro-boundary diagnostic, never a hierarchy/model selector."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'inputs'
OUT = ROOT / 'generated'
OUT.mkdir(exist_ok=True)
names = ['ot_qfd_ucie_x64_phy', 'ot_qfd_serdes_112g_x12_phy_s597']
records = []
wrappers = []
clock_join = json.loads((SRC/'current_clock_join.json').read_text())
vehicle = (SRC/'qc_vehicle.py').read_text()
assert (clock_join['partitions'],clock_join['types'],clock_join['crossing_bits']) == (377,119,790393)
assert clock_join['top_port_count'] == 639
assert "conn[n] = 'ck_serdes' if a.phy_bringup_only and n == 'clk_serdes' else 'ck'" in vehicle
assert 'reg ck = 0; always begin #0.416 ck = ~ck; #0.417 ck = ~ck; end' in vehicle
assert {r['connections']['clk'] for r in clock_join['serdes_instances'].values()} == {
    'clk_region_coll_n','clk_region_coll_s','clk_region_c_W5_bf_01'}
for variant in ('phy_serdes','phy_serdes_b'):
    text = (SRC/f'ot_qfd_serdes_112g_x12_phy_s597__{variant}.sv').read_text()
    core = re.search(r'ot_qfd_serdes_112g_x12_phy_s597\s+u_core\s*\((.*?)\n\s*\);',text,re.S)
    assert re.search(r'\.clk\(clk\)',core.group(1))
for name, fw, lat, period in [(names[0],1043,4,1000), (names[1],597,223,833)]:
    abi = (SRC / (name + '_bb.v')).read_text()
    meta = json.loads((SRC / (name + '.json')).read_text())
    assert (meta['fdi']['flit_bits'], meta['fdi']['latency_fdi_cycles_one_way']) == (fw,lat)
    # Assert exact declared core-facing port inventory before changing the BB
    # into an explicitly private service wrapper. far/link are internal TB nets.
    actual = {p:(d,int(hi)+1 if hi else 1) for d,hi,p in re.findall(
        r'(input|output)\s+wire\s*(?:\[(\d+):0\]\s*)?(\w+)', abi)}
    expected = dict(clk=('input',1),rst_n=('input',1),tx_up=('output',1),
                    tx_v=('input',1),tx_flit=('input',fw),rx_v=('output',1),rx_flit=('output',fw))
    if name == names[0]: expected['lclk']=('output',1)
    assert actual == expected, (name,actual)
    consumer = SRC / ('qfd_qc_coll_ucie_part.sv' if name == names[0]
                      else 'ot_qfd_serdes_112g_x12_phy_s597__phy_serdes.sv')
    instance_name = 'u_io_ucie' if name == names[0] else 'u_core'
    call = re.search(r'\b'+name+r'\s+'+instance_name+r'\s*\((.*?)\n\s*\);', consumer.read_text(), re.S)
    assert call, (name,'selected native instance missing')
    connections = dict(re.findall(r'\.(\w+)\(([^()]*)\)',call.group(1)))
    assert set(connections) == set(expected), (name,'native pin inventory differs')
    assert connections['tx_flit'].endswith(f'[{fw-1}:0]')
    if name == names[0]:
        assert connections['clk'] == connections['lclk']+'[0]'
    body = f'''
    // Private peer nets, connected only by tb_pair; no constant far endpoint.
    wire far_v, link_v;
    wire [{fw-1}:0] far_flit, link_flit;
'''
    transport = 'ot_qkvd_ucie_x64_phy_model' if name == names[0] else name + '_model'
    instance = f'''    {transport} #(.FW({fw}),.LAT({lat}),.UP(16)) u_transport (
        .clk(clk),.rst_n(rst_n),.tx_up(tx_up),.tx_v(tx_v),.tx_flit(tx_flit),
        .rx_v(rx_v),.rx_flit(rx_flit),.link_v(link_v),.link_flit(link_flit),
        .far_v(far_v),.far_flit(far_flit));
'''
    if name == names[0]:
        body += '''`ifdef STALE_UCIE
    ot_qfd_ucie_x64_phy_model #(.FW(1043),.LAT(4),.UP(16)) u_transport (
        .lclk(lclk),.clk(clk),.rst_n(rst_n),.tx_up(tx_up),.tx_v(tx_v),.tx_flit(tx_flit),
        .rx_v(rx_v),.rx_flit(rx_flit),.link_v(link_v),.link_flit(link_flit),
        .far_v(far_v),.far_flit(far_flit));
`else
    reg generated_lclk=0;
    always #0.5 generated_lclk=~generated_lclk;
    assign lclk=generated_lclk;
''' + instance + '`endif\n'
    else:
        body += instance
    wrappers.append(abi.replace('`timescale 1ns/1ps','`timescale 1ns/1fs')
                    .replace('(* blackbox *)','').replace('endmodule',body+'endmodule'))
    records.append(dict(module=name,ports=expected,native_connections=connections,FW=fw,LAT=lat,driven_period_ps=period,
                        metadata_clock_ghz=meta['fdi']['clock_ghz']))

sources = [(SRC/'ot_qkvd_ucie_x64_phy_model.sv').read_text(),
           (SRC/(names[1]+'_model.sv')).read_text(),
           '`ifdef STALE_UCIE\n'+(SRC/(names[0]+'_model.sv')).read_text()+'\n`endif\n']
(OUT/'private_models.sv').write_text('\n'.join(t.replace('`timescale 1ns/1ps','`timescale 1ns/1fs') for t in sources+wrappers))

bench = r'''`timescale 1ns/1fs
module tb_pair;
localparam FW=__FW__, LAT=__LAT__, UP=16;
reg mission_clk=0;
always #0.4165 mission_clk=~mission_clk;
reg rst_n=0;
reg tv0=0,tv1=0;
reg [FW-1:0] td0=0,td1=0;
wire up0,up1,rv0,rv1;
wire [FW-1:0] rd0,rd1;
__CLOCK__
__MACRO__ u0 (.clk(clk),.rst_n(rst_n),.tx_up(up0),.tx_v(tv0),.tx_flit(td0),.rx_v(rv0),.rx_flit(rd0)__LCLK0__);
__MACRO__ u1 (.clk(clk),.rst_n(rst_n),.tx_up(up1),.tx_v(tv1),.tx_flit(td1),.rx_v(rv1),.rx_flit(rd1)__LCLK1__);
integer corrupt=0;
initial corrupt=$test$plusargs("MUT_PAYLOAD");
assign u0.far_v=u1.link_v;
assign u0.far_flit=u1.link_flit ^ ((corrupt && u1.link_v) ? {{(FW-1){1'b0}},1'b1} : {FW{1'b0}});
assign u1.far_v=u0.link_v;
assign u1.far_flit=u0.link_flit;
reg [FW:0] history0[0:LAT-1], history1[0:LAT-1];
reg [FW:0] last_tx0=0,last_tx1=0;
integer edges=0,accepted0=0,accepted1=0,delivered0=0,delivered1=0,resets=0;
integer drive=0,k;
realtime last_edge=0,last_mission=0;
function automatic [FW-1:0] payload(input integer n,input integer peer);
 integer b;
 begin
  for(b=0;b<FW;b=b+1) payload[b]=((n*17+b*13+peer*67)>>(b%5))&1;
  payload[n%FW]=~payload[n%FW];
 end
endfunction
always @(posedge mission_clk) begin
 if(last_mission!=0 && $rtoi(($realtime-last_mission)*1000+0.5)!=833) $fatal(1,"MISSION_PERIOD");
 last_mission=$realtime;
end
always @(posedge clk or negedge rst_n) begin
 if(!rst_n)begin
  edges=0; last_tx0=0;last_tx1=0;
  for(k=0;k<LAT;k=k+1)begin history0[k]=0;history1[k]=0;end
  #0.000001;
  if({up0,up1,rv0,rv1,u0.link_v,u1.link_v}!==0 || rd0!==0 || rd1!==0 || u0.link_flit!==0 || u1.link_flit!==0)
   $fatal(1,"ASYNC_RESET_FLUSH");
 end else begin
  if(last_edge!=0 && $rtoi(($realtime-last_edge)*1000+0.5)!=__PERIOD_PS__) $fatal(1,"PHY_PERIOD");
  edges=edges+1;
  for(k=LAT-1;k>0;k=k-1)begin history0[k]=history0[k-1];history1[k]=history1[k-1];end
  history0[0]={tv0,td0};history1[0]={tv1,td1};
  last_tx0={tv0,td0};last_tx1={tv1,td1};
  if(tv0)accepted0=accepted0+1;
  if(tv1)accepted1=accepted1+1;
  #0.000001;
  if({rv0,rd0}!==history1[LAT-1] || {rv1,rd1}!==history0[LAT-1])
   $fatal(1,"PEER_PAYLOAD_OR_LATENCY cycle=%0d LAT=%0d",edges,LAT);
  if(up0!==(edges>UP) || up1!==(edges>UP)) $fatal(1,"TX_UP_EDGE");
  if({u0.link_v,u0.link_flit}!==last_tx0 || {u1.link_v,u1.link_flit}!==last_tx1) $fatal(1,"TX_CAPTURE");
  if(rv0)delivered0=delivered0+1;
  if(rv1)delivered1=delivered1+1;
 end
 last_edge=$realtime;
end
always @(negedge clk) begin
 if(rst_n)begin
  drive=drive+1;
  // Bursts, gaps and independent direction payloads, all 1043/597 bits checked.
  tv0=(drive%7!=0);tv1=(drive%5<3);
  td0=payload(drive,0);td1=payload(drive,1);
  #0.000001;
  if({u0.link_v,u0.link_flit}!==last_tx0 || {u1.link_v,u1.link_flit}!==last_tx1)
   $fatal(1,"UNREGISTERED_TX_BETWEEN_EDGES");
 end
end
initial begin
 #0.000001; // explicit initial reset event even in two-state simulators
 rst_n=1;#0.000001;rst_n=0;
 repeat(4)@(negedge clk);#0.01;rst_n=1;
 repeat(LAT+70)@(negedge clk);
 #0.1;rst_n=0;resets=resets+1; // asynchronous mid-traffic flush on both peers
 repeat(4)@(negedge clk);#0.01;rst_n=1;
 repeat(LAT+300)@(negedge clk);
 #0.1;rst_n=0;resets=resets+1;
 #0.000002; // let async NBA flush and its assertion complete before $finish
 if(accepted0<250 || accepted1<180 || delivered0<150 || delivered1<200 || resets!=2)
  $fatal(1,"INSUFFICIENT_ACTIVE_COVERAGE");
 $display("PHY_PAIR_PASS FW=%0d LAT=%0d period_ps=__PERIOD_PS__ mission_ps=833 accepted=%0d/%0d delivered=%0d/%0d async_resets=%0d",FW,LAT,accepted0,accepted1,delivered0,delivered1,resets);
 $finish;
end
initial begin #100000;$fatal(1,"BOUNDED_DIAGNOSTIC_TIMEOUT");end
endmodule
'''
for rec in records:
    ucie = rec['module']==names[0]
    text=bench
    values=dict(FW=rec['FW'],LAT=rec['LAT'],MACRO=rec['module'],
                CLOCK='wire lclk0,lclk1;wire clk=lclk0;' if ucie else 'wire clk=mission_clk;',
                LCLK0=',.lclk(lclk0)' if ucie else '',LCLK1=',.lclk(lclk1)' if ucie else '',
                PERIOD_NS='1.0' if ucie else '0.833',PERIOD_PS=rec['driven_period_ps'])
    for key,value in values.items():text=text.replace('__'+key+'__',str(value))
    (OUT/('tb_'+('ucie' if ucie else 'serdes')+'.sv')).write_text(text)

manifest=dict(scope='PRIVATE_TWO_PEER_BOUNDARY_DIAGNOSTIC_ONLY',source_commit='bd55b15b452761be8ceefeae7b97abdf4a915bd4',
              current_bind='epyc2:/srv/opentallas-scratch2/claude/codex-qc62-collect-1101/bind_complete4',
              current_bind_receipt='82190c1ff',paired_plan_event='f79c1e228',
              canonical_plan_sha256='913be9b7f5ee612824f323d3d476999a36e2f224f1c3139f163d1b6558cdaab7',
              current_bind_parts=377,current_bind_types=119,current_top_ports=639,
              current_top_sha256=clock_join['top_sha256'],
              serdes_clock_scope='833ps diagnostic condition following frozen qc_vehicle clock mapping; complete current vehicle/physical clock contract unqualified',
              models=records,hardware_added_cycles=0,physical_qualification_eligible=False,
              full_hierarchy_qualified=False,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SRC.iterdir()) if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
