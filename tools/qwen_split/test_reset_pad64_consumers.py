"""PAD62 must remain a 64-edge shift cell in generated RTL and calendars."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from gen_relay_rtl import main as generate
from reset_calendar_audit import audit, finalize_model
net='''module die;
wire root;
wire delayed;
qfd_rst_rep_p62 pad (.clk(ck), .d(root), .q0(delayed), .q1());
qfd_landh0_n1 land (.en(delayed), .rs(delayed));
endmodule
'''
lanes=dict(lanes=[dict(bid='x',landing='land',E=2,E_sta=2,n=1,K=0)])
row=audit(net,lanes,{'root':7})[0]
assert (row['G'],row['R0'])==(72,71),row
model=dict(insts=[SimpleNamespace(name='pad',master='qfd_rst_rep_p62')],
 buses=[('root','reset',1,[('external','reset'),('pad','d')]),
 ('delayed','reset',1,[('pad','q0'),('land','en'),('land','rs')])],
 fwd_lanes=dict(lanes=[dict(bid='x',landing='land',E=2,E_sta=2,n=1,K=0)]))
finalize_model(model,{'external.reset':7})
r=model['fwd_lanes']['lanes'][0]
assert (r['G_reset_tree'],r['R0_reset_tree'])==(72,71),r
with TemporaryDirectory() as td:
 p=Path(td);(p/'die.v').write_text(net.replace('qfd_landh0_n1 land (.en(delayed), .rs(delayed));',''))
 generate(p/'die.v',p/'relay.sv')
 rtl=(p/'relay.sv').read_text()
 assert 'ot_qwen_rst_rep #(.PAD(62))' in rtl,rtl
 assert 'output wire q1' in rtl,rtl
print('PAD64_CONSUMERS PASS: actual netlist + model calendars both count64, RTL keeps PAD62/q1')
