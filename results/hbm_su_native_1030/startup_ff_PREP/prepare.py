from pathlib import Path
import re,json,hashlib
R=Path(__file__).resolve().parents[3];B=R/'physical/die_plan/hbm_arch_cores';O=R/'results/hbm_su_native_1030/startup_ff_PREP';O.mkdir(exist_ok=True);(O/'rtl').mkdir(exist_ok=True)
SUFFIX='__su_startup_ff1030';rows=[]
def inst(s,old,name):
 hits=[]
 for m in re.finditer(r'\b'+old+r'\b',s):
  pos=m.end()
  while s[pos].isspace():pos+=1
  if s[pos]=='#':
   pos+=1
   while s[pos].isspace():pos+=1
   assert s[pos]=='(';level=0
   while pos<len(s):
    c=s[pos];pos+=1
    if c=='(':level+=1
    if c==')':
     level-=1
     if level==0:break
  n=re.match(r'\s*(\w+)\s*\(',s[pos:])
  if n and n[1]==name:hits.append(m.span())
 assert len(hits)==1,(old,name,len(hits))
 a,b=hits[0];return s[:a]+old+SUFFIX+s[b:]
def make(old,edges=(),addition=None,folder='native_1030'):
 p=B/folder/(old+'.sv');s=p.read_text();orig=s;s=s.replace('module '+old,'module '+old+SUFFIX,1)
 for child,i in edges:s=inst(s,child,i)
 if addition:
  before,after=addition;assert s.count(before)==1;s=s.replace(before,after)
 (O/'rtl'/(old+SUFFIX+'.sv')).write_text(s)
 norm=s.replace(SUFFIX,'')
 if addition:norm=norm.replace(addition[1],addition[0])
 assert norm==orig
 rows.append(dict(original=old,specialized=old+SUFFIX,source=str(p.relative_to(R)),original_sha256=hashlib.sha256(orig.encode()).hexdigest(),specialized_sha256=hashlib.sha256(s.encode()).hexdigest(),only_changes='module/child names plus exactly corresponding unreset FF leaf replacements where declared',edges=list(edges),has_state_replacement=bool(addition)))
make('ot_hdc_delay',addition=("if (RESET != 0) begin : g_rst\n                always @(posedge clk or negedge rst_n)\n                    if (!rst_n) line <= {(W*D){1'b0}};", "if (W == 32 && D == 4 && RESET == 0) begin : g_startup_preserve\n                for (genvar k=0;k<W*D;k=k+1) begin : g_bit\n                    if (k % 32 == 30) begin : g_leaf\n                        ot_hbm_su_startup_ff1030 u_ff(.clk(clk),.d(k < W ? d[k % W] : line[k-W]),.q(line[k]));\n                    end else begin : g_plain\n                        always @(posedge clk) line[k] <= k < W ? d[k % W] : line[k-W];\n                    end\n                end\n            end else if (RESET != 0) begin : g_rst\n                always @(posedge clk or negedge rst_n)\n                    if (!rst_n) line <= {(W*D){1'b0}};"))
make('ot_hdc_w11_cut',addition=('always @(posedge clk) rd <= d;', 'for (genvar k=0;k<W;k=k+1) begin : g_startup_preserve\n            if (W==120 && k==71) begin : g_leaf\n                ot_hbm_su_startup_ff1030 u_ff(.clk(clk),.d(d[k]),.q(rd[k]));\n            end else begin : g_plain\n                always @(posedge clk) rd[k] <= d[k];\n            end\n        end'))
make('ot_hdc_fp32_add_lat',[('ot_hdc_w11_cut','u_ca')])
make('ot_hdc_fp32_add_lat4i',[('ot_hdc_fp32_add_lat','u')])
make('ot_hdc_qadd_lat',[('ot_hdc_fp32_add_lat4i','u')])
make('ot_hdc_v41x_exp',[('ot_hdc_delay','d_lo'),('ot_hdc_qadd_lat','a_r')],addition=('always @(posedge clk) {a_hi, a_lo} <= ln2_nk(nint[7:0]);', 'wire [63:0] startup_lut = ln2_nk(nint[7:0]);\n    always @(posedge clk) begin\n        a_hi <= startup_lut[63:32];\n        a_lo[31] <= startup_lut[31];\n        a_lo[29:0] <= startup_lut[29:0];\n    end\n    ot_hbm_su_startup_ff1030 u_startup_lo30(.clk(clk),.d(startup_lut[30]),.q(a_lo[30]));'))
make('ot_hbm_su_static_lane',[('ot_hdc_v41x_exp','u_exp')])
make('ot_hbm_su_static_lane_pinreg__static_id',[('ot_hbm_su_static_lane','u_lane')],folder='id_1030')
make('ot_hnx_su_exp__rst3__static_id',[('ot_hbm_su_static_lane_pinreg__static_id','m1')],folder='id_1030')
(O/'graph_identity.json').write_text(json.dumps(dict(status='SOURCE_PREP_EXACT_STATEBIT_LEAF_REPLACEMENT',no_logic_or_reset_or_cycle_changes=True,physical_adoption=False,rows=rows),indent=2)+'\n')
(O/'rtl/ot_hbm_su_startup_ff1030.sv').write_text('(* keep_hierarchy = \"yes\" *) module ot_hbm_su_startup_ff1030(input wire clk,d,output reg q); always @(posedge clk) q<=d; endmodule\n')
print('PREP',len(rows),'module copies; exactly6 original startup FFs replaced by identical unreset preserved-hierarchy FF leaves')
