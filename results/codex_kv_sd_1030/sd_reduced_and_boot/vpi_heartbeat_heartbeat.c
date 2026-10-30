#include <vpi_user.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static vpiHandle ch;
static int faults=0;
static int number(vpiHandle h){s_vpi_value v;v.format=vpiIntVal;vpi_get_value(h,&v);return v.value.integer;}
static void bit(const char*n){vpiHandle h=vpi_handle_by_name((char*)n,NULL);s_vpi_value v;v.format=vpiBinStrVal;if(h){vpi_get_value(h,&v);vpi_printf(" %s=%s",n,v.value.str);}}
static PLI_INT32 changed(p_cb_data cb) {
 int n=number(cb->obj);
 if(n%100==0) {s_vpi_time t;t.type=vpiSimTime;vpi_get_time(NULL,&t);vpi_printf("HEARTBEAT cycle=%d ticks=%u:%u",n,t.high,t.low);
 bit("tb.die.hub_C.cland_start");bit("tb.die.rs_hub_C");bit("tb.die.rraw_hub_C");bit("tb.die.pst_sys_SW");bit("tb.ready");bit("tb.fault");vpi_printf("\n");fflush(stdout);}
 return 0;
}
static PLI_INT32 faulted(p_cb_data cb){
 s_vpi_value v;v.format=vpiScalarVal;vpi_get_value(cb->obj,&v);
 if(v.value.scalar==vpi1 && faults++<20){vpi_printf("CA_FAULT cycle=%d %s\n",number(ch),cb->user_data);fflush(stdout);}
 return 0;
}
static void scan(vpiHandle scope){
 vpiHandle it=vpi_iterate(vpiModule,scope),h;
 while(it && (h=vpi_scan(it))){
  if(!strcmp(vpi_get_str(vpiDefName,h),"ot_dp_clk_landing_cas")){
   const char*p=vpi_get_str(vpiFullName,h);char*name=malloc(strlen(p)+8);sprintf(name,"%s.fault",p);
   vpiHandle f=vpi_handle_by_name(name,NULL);
   if(f){s_cb_data c={0};c.reason=cbValueChange;c.cb_rtn=faulted;c.obj=f;c.user_data=name;vpi_register_cb(&c);}
  }
  scan(h);
 }
}
static PLI_INT32 start(p_cb_data unused) {
 ch=vpi_handle_by_name("tb.cycle",NULL);
 if(!ch){vpi_printf("HEARTBEAT no cycle handle\n");return 0;}
 s_cb_data c={0};c.reason=cbValueChange;c.cb_rtn=changed;c.obj=ch;vpi_register_cb(&c);
 scan(NULL);vpi_printf("HEARTBEAT attached read-only timing/control/fault probes\n");fflush(stdout);return 0;
}
static void reg(void) {s_cb_data c={0};c.reason=cbStartOfSimulation;c.cb_rtn=start;vpi_register_cb(&c);}
void (*vlog_startup_routines[])(void)={reg,0};
