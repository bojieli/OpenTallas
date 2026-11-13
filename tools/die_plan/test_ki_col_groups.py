import sys,importlib.util,json,re
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import kit_istations as K
TXT='''module bound(input wire clk,rst_n,input wire a1,a0,b1,b0);
 cfg u_u_s0 (.st({a1, a0}));
 cfg u_u_s3 (.st({b1, b0}));
 reg [1:0] cst_st_s0; always @(posedge clk or negedge rst_n) if(!rst_n)cst_st_s0<=2'b00; else cst_st_s0 <= {a1,a0};
 reg [1:0] cst_st_s1; always @(posedge clk or negedge rst_n) if(!rst_n)cst_st_s1<=2'b00; else cst_st_s1 <= cst_st_s0;
 reg [1:0] cst_s3_t2_s0; always @(posedge clk or negedge rst_n) if(!rst_n)cst_s3_t2_s0<=2'b00; else cst_s3_t2_s0 <= {b1,b0};
 core u_u_t0 (.c0(cst_st_s1));
 core u_u_t2 (.c0(cst_s3_t2_s0));
endmodule'''
def entry(s,t,n,explicit=True):
 a=f'u_r0.u_s{s}.st';b=f'u_r0.u_t{t}'+('.c0'if explicit else'')
 return dict(conn='core:'+a+'|core:'+b,launch=a,capture=b,regs_um=[[10+j*20,20+j*20]for j in range(n)])
def test_actual_concat_source_expression():
 assert K._col_chain(TXT,'u_r0.u_s0.st','u_r0.u_t0.c0')==['cst_st_s0','cst_st_s1']
 assert K._col_chain(TXT,'u_r0.u_s3.st','u_r0.u_t2.c0')==['cst_s3_t2_s0']
def test_distinct_depths_and_duplicate_capture_coalesce():
 es=[entry(0,0,2,False),entry(0,0,2),entry(3,2,1)];tcl=[];rep=[]
 assert K.col_st_stations(dict(internal_stations=es),TXT,tcl,rep)==es
 assert len(tcl)==3
 rows=rep[0]['col_st_groups'];assert [(r['stages'],r['entries'])for r in rows]==[(2,2),(1,1)]
 assert rows[1]['regs']==['cst_s3_t2_s0']
def test_no_global_t0_chain_substituted_for_t2():
 txt=TXT.replace('core u_u_t2 (.c0(cst_s3_t2_s0));','core u_u_t2 (.c0(unmaterialized));')
 assert K._col_chain(txt,'u_r0.u_s3.st','u_r0.u_t2.c0')==[]
 rep=[];tcl=[];K.col_st_stations(dict(internal_stations=[entry(3,2,1)]),txt,tcl,rep)
 assert tcl==[] and rep[0]['col_st']['bound_stages']==0
def test_unequal_same_group_is_rejected():
 with pytest.raises(SystemExit,match='entries disagree'):
  K.col_st_stations(dict(internal_stations=[entry(0,0,2),entry(0,0,1)]),TXT,[],[])
def test_old_single_chain_receipt_shape_is_preserved():
 rep=[];K.col_st_stations(dict(internal_stations=[entry(0,0,2)]),TXT,[],rep)
 assert rep[0]['col_st']['stages']==2 and 'col_st_groups'not in rep[0]
def test_actual_mismatch_reports_actual_depth():
 txt=TXT.replace('.c0(cst_st_s1)','.c0(cst_st_s0)')
 rep=[];K.col_st_stations(dict(internal_stations=[entry(0,0,2)]),txt,[],rep)
 assert rep[0]['col_st']['bound_stages']==1
 assert rep[0]['col_st']['regs']==['cst_st_s0']
def test_alias_and_cycle():
 txt=TXT.replace('.c0(cst_st_s1)','.c0(alias)')+'\nassign alias = cst_st_s1;\n'
 assert K._col_chain(txt,'u_r0.u_s0.st','u_r0.u_t0')==['cst_st_s0','cst_st_s1']
 txt=txt.replace('assign alias = cst_st_s1','assign alias = alias')
 assert K._col_chain(txt,'u_r0.u_s0.st','u_r0.u_t0')==[]
def test_reset_pad_suffix_cannot_replace_actual_source():
 txt=TXT.replace('cfg u_u_s0', 'reset lpr_c_u_s0 (.st(unrelated));\n cfg u_u_s0')
 assert K._col_chain(txt,'u_r0.u_s0.st','u_r0.u_t0.c0')==['cst_st_s0','cst_st_s1']
