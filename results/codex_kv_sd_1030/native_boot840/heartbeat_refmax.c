#include <vpi_user.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <inttypes.h>
static vpiHandle ch;
static int faults=0,initialised=0;
static unsigned initseed=1;
static int number(vpiHandle h){s_vpi_value v;v.format=vpiIntVal;vpi_get_value(h,&v);return v.value.integer;}
static void bit(const char*n){vpiHandle h=vpi_handle_by_name((char*)n,NULL);s_vpi_value v;v.format=vpiBinStrVal;if(h){vpi_get_value(h,&v);vpi_printf(" %s=%s",n,v.value.str);}}
static PLI_INT32 changed(p_cb_data cb) {
 int n=number(cb->obj);
 if(n%100==0) {s_vpi_time t;t.type=vpiSimTime;vpi_get_time(NULL,&t);vpi_printf("HEARTBEAT cycle=%d ticks=%u:%u",n,t.high,t.low);
 bit("tb.die.hub_C.cland_start");bit("tb.die.rs_hub_C");bit("tb.die.rraw_hub_C");bit("tb.die.pst_sys_SW");bit("tb.ready");bit("tb.fault");vpi_printf("\n");fflush(stdout);}
 return 0;
}

static void pc_snapshot(void){
 const char*prefix="tb.die.pc_WS_6.u_cland_i_vport_Q_N_vqN";
 const char*names[]={"t_rst_n","rst_n","ready","fault","seen","armed","arm_cnt","tmo","tmo_cnt","trip","u_ring.tc","u_ring.rp","u_ring.r_v","u_ring.r_lap_ok","u_ring.r_glo_ok","u_ring.r_ghi_ok",NULL};
 char p[512];
 bit("tb.die.hg_WS_6.cland_start");bit("tb.die.pc_WS_6.cland_start");
 for(int i=0;names[i];i++){snprintf(p,sizeof p,"%s.%s",prefix,names[i]);bit(p);}
}
static PLI_INT32 pc_transition(p_cb_data cb){
 s_vpi_time t={0};t.type=vpiSimTime;vpi_get_time(NULL,&t);
 vpi_printf("PC_TRANSITION cycle=%d ticks=%u:%u",number(ch),t.high,t.low);bit(cb->user_data);pc_snapshot();vpi_printf("\n");fflush(stdout);return 0;
}
static PLI_INT32 faulted(p_cb_data cb){
 s_vpi_value v;v.format=vpiScalarVal;vpi_get_value(cb->obj,&v);
 if(v.value.scalar==vpi1 && faults++<20){vpi_printf("CA_FAULT cycle=%d %s",number(ch),cb->user_data);pc_snapshot();vpi_printf("\n");fflush(stdout);}
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
  if(!strcmp(vpi_get_str(vpiDefName,h),"ot_meso_ring")){
   const char*p=vpi_get_str(vpiFullName,h);char*name=malloc(strlen(p)+5);sprintf(name,"%s.tc",p);
   vpiHandle tc=vpi_handle_by_name(name,NULL);
   if(tc){unsigned phase=initseed;for(const char*q=p;*q;q++)phase=(phase*16777619u)^(unsigned char)*q;
    unsigned bits=vpi_get(vpiSize,tc);phase&=((1u<<bits)-1u);s_vpi_value v;v.format=vpiIntVal;v.value.integer=phase;
    vpi_put_value(tc,&v,NULL,vpiNoDelay);vpi_printf("LEGAL_FREE_TC_POWERUP %s=%u width=%u\n",name,phase,bits);initialised++;}
  }
  scan(h);
 }
}
static PLI_INT32 finish(p_cb_data unused) {
 vpiHandle die=vpi_handle_by_name("tb.die",NULL),it=vpi_iterate(vpiModule,die),h;
 while(it&&(h=vpi_scan(it))){char n[512];snprintf(n,sizeof n,"%s",vpi_get_str(vpiFullName,h));if(!strncmp(vpi_get_str(vpiDefName,h),"kv3_",4)){
  char a[512];vpi_printf("FINAL_PART %s",n);snprintf(a,sizeof a,"%s.cland_up_ready",n);bit(a);snprintf(a,sizeof a,"%s.cland_up_fault",n);bit(a);snprintf(a,sizeof a,"%s.cland_start",n);bit(a);vpi_printf("\n");}}
 vpi_printf("POWERUP_MODEL seed=%u free_writer_counters=%d no_reinitialisation_on_warm=1\n",initseed,initialised);fflush(stdout);return 0;
}

static vpiHandle refh;
static int refval=0;
static PLI_INT32 refedge(p_cb_data unused){
 refval=!refval;s_vpi_value v;v.format=vpiIntVal;v.value.integer=refval;vpi_put_value(refh,&v,NULL,vpiForceFlag);
 static s_vpi_time delay={vpiSimTime,0,5000000,0};s_cb_data c={0};c.reason=cbAfterDelay;c.cb_rtn=refedge;c.time=&delay;vpi_register_cb(&c);return 0;
}
static PLI_INT32 exact_event(p_cb_data cb){
 s_vpi_time t={0};t.type=vpiSimTime;vpi_get_time(NULL,&t);
 uint64_t ticks=((uint64_t)t.high<<32)|t.low;
 vpi_printf("CAUSAL_EVENT ticks_fs=%" PRIu64 " cycle=%d",ticks,number(ch));bit(cb->user_data);vpi_printf("\n");fflush(stdout);return 0;
}
static PLI_INT32 start(p_cb_data unused) {
 const char*env=getenv("OT_BOOT_INIT_SEED");if(env)initseed=(unsigned)strtoul(env,NULL,0);
 ch=vpi_handle_by_name("tb.cycle",NULL);
 if(!ch){vpi_printf("HEARTBEAT no cycle handle\n");return 0;}
 s_cb_data c={0};c.reason=cbValueChange;c.cb_rtn=changed;c.obj=ch;vpi_register_cb(&c);
 s_cb_data end={0};end.reason=cbEndOfSimulation;end.cb_rtn=finish;vpi_register_cb(&end);
 
 const char*pn[]={"tb.die.hg_WS_6.cland_start","tb.die.pc_WS_6.cland_start","tb.die.pc_WS_6.u_cland_i_vport_Q_N_vqN.u_ring.t_rst_n","tb.die.pc_WS_6.u_cland_i_vport_Q_N_vqN.u_ring.r_rst_n",NULL};
 for(int i=0;pn[i];i++){vpiHandle h=vpi_handle_by_name((char*)pn[i],NULL);if(h){s_cb_data c={0};c.reason=cbValueChange;c.cb_rtn=pc_transition;c.obj=h;c.user_data=(char*)pn[i];vpi_register_cb(&c);}else vpi_printf("MISSING_PC_PROBE %s\n",pn[i]);}

 const char*first=getenv("OT_REF_FIRST_RISE_PS");
 if(first){
  double fps=strtod(first,NULL);if(fps<=0 || fps>=10000){vpi_printf("INVALID_REF_INPUT_PHASE\n");vpi_control(vpiFinish,1);return 0;}
  refh=vpi_handle_by_name("tb.refclk",NULL);if(!refh){vpi_printf("MISSING_REF_INPUT\n");vpi_control(vpiFinish,1);return 0;}
  s_vpi_value v;v.format=vpiIntVal;v.value.integer=0;vpi_put_value(refh,&v,NULL,vpiForceFlag);
  static s_vpi_time td;td.type=vpiSimTime;td.high=0;td.low=(unsigned)(fps*1000+.5);
  s_cb_data z={0};z.reason=cbAfterDelay;z.cb_rtn=refedge;z.time=&td;vpi_register_cb(&z);
  vpi_printf("REF_INPUT_DRIVER first_rise_ps=%.3f period_ps=10000 duty_ps=5000 native_PLL_8edge_law_unchanged=1\n",fps);
 }
 const char*en[]={"tb.rst","tb.mission_start","tb.die.hub_C.w_pll_locked","tb.die.hub_C.rst_root_n","tb.ready","tb.fault","tb.mission_all","tb.complete_ready",NULL};
 for(int i=0;en[i];i++){vpiHandle h=vpi_handle_by_name((char*)en[i],NULL);if(!h){vpi_printf("MISSING_CAUSAL_EVENT %s\n",en[i]);vpi_control(vpiFinish,1);return 0;}s_cb_data z={0};z.reason=cbValueChange;z.cb_rtn=exact_event;z.obj=h;z.user_data=(char*)en[i];vpi_register_cb(&z);}
scan(NULL);vpi_printf("HEARTBEAT legal binary free-counter powerup, then read-only timing/control/fault probes\n");fflush(stdout);return 0;
}
static void reg(void) {s_cb_data c={0};c.reason=cbStartOfSimulation;c.cb_rtn=start;vpi_register_cb(&c);}
void (*vlog_startup_routines[])(void)={reg,0};
