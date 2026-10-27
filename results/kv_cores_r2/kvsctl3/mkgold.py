# gold for the KV-KVSCTL-3 retime LEC = OLD RTL + the DECLARED changes only:
#   (i) w_data/w_zero/w_one reset (ruling (c)), (ii) +1 landing regs on 305 dcfg bits + setup_ready (ruling (a)).
# gate = new RTL (adds the 0-cycle retimes: layer/layer_e 54, auth 80, cf2 IN_LAND 32).
import sys,os
src,new,out=sys.argv[1:4]
os.makedirs(out,exist_ok=True)
t=open(src+"/rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_nc32_face.sv").read()
a="  w_data<=wdn;w_zero<=data_q[31:0]==0;w_one<=data_q[31:0]==1;\n end\n"
assert t.count(a)==1
t=t.replace(a," end\n always @(posedge ck or negedge rn)if(!rn)begin w_data<=0;w_zero<=0;w_one<=0;end\n else begin w_data<=wdn;w_zero<=data_q[31:0]==0;w_one<=data_q[31:0]==1;end\n")
open(out+"/qkd_kv_ctl_nc32_face.sv","w").write(t)
l=open(new+"/results/kv_cores_r2/kvsctl3/rtl/qkd_kvs_ctl_nc32__leaf.sv").read()
assert l.count(", .IN_LAND(1)")==8
open(out+"/qkd_kvs_ctl_nc32__leaf.sv","w").write(l.replace(", .IN_LAND(1)",""))
print("ok")
