from pathlib import Path
import re,hashlib,argparse
ap=argparse.ArgumentParser(description='Generate optional TKM internal delivery pipeline from exact approved reset source')
ap.add_argument('--source',type=Path)
ap.add_argument('--out',type=Path)
a=ap.parse_args()
r=Path(__file__).resolve().parents[3]
base=a.source or r/'rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192/ot_hgi_coll_tkm_tp192_root_core__ctlrst.sv'
s=base.read_text();assert hashlib.sha256(base.read_bytes()).hexdigest()=='2214efc605dac6ac80efbb29fe03a38486a272fde801af7e27ad1f48d27c62ff'
flag='OT_TKM_DEL_PIPE1'
def conditional(old,new):
 return '`ifdef '+flag+'\n'+new+'\n`else\n'+old+'\n`endif'
# Keep ingress_end and the external capture/validation calendar unchanged.
for n in [60220,60225,60226,60227,60228]:
 pat=rf'(?m)^    else _{n}_ <= (.+);$';m=re.search(pat,s);assert m,n
 old=m.group(0);new=f"    else _{n}_ <= ({m.group(1)}) + (_60268_[2] ? 32'd1 : 32'd0);"
 s=s[:m.start()]+conditional(old,new)+s[m.end():]
pat=r'(?m)^  assign \\u\.issue1\s*= .+;$';m=re.search(pat,s);assert m
old=m.group(0);new="  assign \\u.issue1  = \\u.busy  && (_60260_ >= 32'd10) && (_60260_ <= (_60224_ + 32'd1));"
s=s[:m.start()]+conditional(old,new)+s[m.end():]
# Exact old slot payload/reset masking stays; only its next-state equations change.
slot_regs=[]
for k in range(8):
 pat=rf'(?m)^  assign \{{ \\u\.slot\[{k}\]\[343\].+ = (_\d+_)m;$'
 # _m is named _60277_m (base without trailing underscore).
 lines=[l for l in s.splitlines() if l.startswith(f'  assign {{ \\u.slot[{k}][343]')]
 assert len(lines)==1,(k,len(lines));m=re.search(r'= (_\d+)_m;$',lines[0]);assert m,lines[0][-100:]
 slot_regs.append(m.group(1))
for k,reg in enumerate(slot_regs):
 pat=rf'(?m)^  assign {reg}_d = .+;$';m=re.search(pat,s);assert m,reg
 old=m.group(0);hold=slot_regs[k+1]+'_m' if k<7 else reg+'_m'
 new=f'  assign {reg}_d = ot_del_cap_q ? ot_del_slot_{k} : {hold};'
 s=s[:m.start()]+conditional(old,new)+s[m.end():]
extra=r'''
`ifdef OT_TKM_DEL_PIPE1
  // One internal delivery edge after the existing external face capture.
  // Accepted start remains unchanged; post-ingress calendars carry one extra edge.
  reg ot_del_cap_q;
  (* keep *) reg [2179:0] ot_del_flit_q;
  (* keep *) reg [3:0] ot_del_valid_q, ot_del_slot_q, ot_del_expected_q;
  reg [7:0] ot_del_rk_q[0:3], ot_del_pr_q[0:3];
  reg [7:0] ot_del_gbpf_q;
  always @(posedge clk, negedge rst_n)
    if (!rst_n) ot_del_cap_q <= 1'b0;
    else if (_18340_) ot_del_cap_q <= 1'b0;
    else ot_del_cap_q <= \u.capture ;
  always @(posedge clk) begin
    if (_60268_[0]) ot_del_gbpf_q <= _60234_ * _60236_[7:0];
    if (\u.capture ) begin
      ot_del_flit_q <= del_flit;
      ot_del_valid_q <= del_valid;
      ot_del_slot_q <= del_slot;
      ot_del_expected_q <= {\u.expected[3] ,\u.expected[2] ,\u.expected[1] ,\u.expected[0] };
      for (integer l=0;l<4;l=l+1) begin
        ot_del_rk_q[l] <= del_flit[545*l+528+:8] - _60234_;
        ot_del_pr_q[l] <= del_flit[545*l+528+:8] * _60236_[7:0];
      end
    end
  end
  function automatic [85:0] ot_del_decode(input [31:0] vv,input [31:0] id,input [7:0] rk,input [7:0] f8,input h,input [1:0] si,input ok);
    reg [31:0] norm,ordered;
    begin
      norm=(vv==32'h80000000)?32'd0:vv;
      ordered=norm[31]?~norm:(norm|32'h80000000);
      ot_del_decode={1'b0,1'b1,ordered,~id,~rk,~{f8,h,si},(vv==32'h80000000)};
      if(vv==32'hffffffff || !ok)ot_del_decode=86'd0;
    end
  endfunction
'''
# Raw string above uses doubled backslash for Python visibility; SV escaped identifier needs one.
extra=extra.replace('\\\\','\\')
for k in range(8):
 l=k//2;h=k%2
 extra+=f'  wire [343:0] ot_del_slot_{k};\n'
 for q in range(4):
  elem=4*h+q;vlo=545*l+32*elem;ilo=545*l+256+32*elem
  extra+=f"  assign ot_del_slot_{k}[{q*86}+:86] = ot_del_decode(ot_del_flit_q[{vlo}+:32],ot_del_flit_q[{ilo}+:32],ot_del_rk_q[{l}],(ot_del_flit_q[{545*l+512}+:8]+ot_del_gbpf_q-ot_del_pr_q[{l}]),1'b{h},2'd{q},ot_del_expected_q[{l}]);\n"
extra+='`endif\n'
i=s.index('\nendmodule');s=s[:i]+extra+s[i:]
out=a.out or base.with_name('ot_hgi_coll_tkm_tp192_root_core__delpipe1.sv');out.write_text(s)
print('slots',slot_regs,'sha',hashlib.sha256(out.read_bytes()).hexdigest(),'bytes',len(s))
