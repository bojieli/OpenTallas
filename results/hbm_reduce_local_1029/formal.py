from pathlib import Path
s=Path('ot_hgi_coll_reduce_static.sv').read_text()
s=s.replace('output wire fault,output reg [7:0] fault_cause','output wire [79:0] ctrl_obs,output wire fault,output reg [7:0] fault_cause')
s=s.replace('  ot_hgi_coll_reduce_static_state_lane u_state(', '  assign ctrl_obs[l*5+:5]={local_wb,local_tag};\n  ot_hgi_coll_reduce_static_state_lane u_state(')
Path('obs.sv').write_text(s)
Path('formal.sv').write_text("""module formal(input clk,rst_n,add_issue,add_read,input[3:0]read_tag,output eq);
wire[79:0]a,b;
ot_hgi_coll_reduce_static #(.LOCAL_CTRL(0))g(.clk_control(clk),.rst_n(rst_n),.add_issue(add_issue),.add_read(add_read),.read_tag(read_tag),.ctrl_obs(a));
ot_hgi_coll_reduce_static #(.LOCAL_CTRL(1))n(.clk_control(clk),.rst_n(rst_n),.add_issue(add_issue),.add_read(add_read),.read_tag(read_tag),.ctrl_obs(b));
assign eq=a==b;endmodule
""")
