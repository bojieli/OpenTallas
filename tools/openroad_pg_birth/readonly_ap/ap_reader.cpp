// SPDX-License-Identifier: BSD-3-Clause
// Read-only public OpenDB AP bucket adapter. No callbacks, writes, RC or PA.
#include <tcl.h>
#include <odb/db.h>
#include <stdexcept>
#include <string>
namespace {
using namespace odb;
void put(Tcl_Interp* ip,Tcl_Obj* d,const char* k,Tcl_Obj* v) {Tcl_DictObjPut(ip,d,Tcl_NewStringObj(k,-1),v);}
Tcl_Obj* str(const char* s) {return Tcl_NewStringObj(s,-1);}
Tcl_Obj* num(unsigned long long n) {return Tcl_NewWideIntObj(n);}
void append(Tcl_Interp* ip,Tcl_Obj* list,Tcl_Obj* v) {Tcl_ListObjAppendElement(ip,list,v);}
Tcl_Obj* point(Tcl_Interp* ip,dbAccessPoint* ap) {
  if (!ap) throw std::runtime_error("OT_AP_READER_NULL_AP");
  auto r=Tcl_NewDictObj();auto p=ap->getPoint();auto layer=ap->getLayer();auto mp=ap->getMPin();
  put(ip,r,"id",num(ap->getId())); put(ip,r,"mpin_id",num(mp ? mp->getId():0));
  put(ip,r,"x",Tcl_NewIntObj(p.x())); put(ip,r,"y",Tcl_NewIntObj(p.y()));
  put(ip,r,"layer",str(layer ? layer->getConstName():""));
  auto vias=Tcl_NewListObj(0,nullptr);
  for (const auto& cut : ap->getVias()) {
    auto bucket=Tcl_NewListObj(0,nullptr);
    for (auto via : cut) {
      if (!via) throw std::runtime_error("OT_AP_READER_NULL_VIA");
      auto v=Tcl_NewDictObj();put(ip,v,"id",num(via->getId()));put(ip,v,"type",str(via->getTypeName()));
      append(ip,bucket,v);
    }
    append(ip,vias,bucket);
  }
  put(ip,r,"via_buckets",vias);return r;
}
int read(ClientData,Tcl_Interp* ip,int objc,Tcl_Obj* const objv[]) {
  try {
    if (objc!=4) {Tcl_WrongNumArgs(ip,1,objv,"database_id block_id instance_name");return TCL_ERROR;}
    int d,b;if(Tcl_GetIntFromObj(ip,objv[1],&d)!=TCL_OK || Tcl_GetIntFromObj(ip,objv[2],&b)!=TCL_OK)return TCL_ERROR;
    if(d<=0 || b<=0)throw std::runtime_error("OT_AP_READER_CONTEXT");
    auto db=dbDatabase::getDatabase(d);auto chip=db ? db->getChip():nullptr;auto block=chip ? chip->getBlock():nullptr;
    if(!block || block->getId()!=(unsigned)b)throw std::runtime_error("OT_AP_READER_TOP_BLOCK");
    auto inst=block->findInst(Tcl_GetString(objv[3]));if(!inst)throw std::runtime_error("OT_AP_READER_INST_NOT_FOUND");
    auto r=Tcl_NewDictObj();auto idx=inst->getPinAccessIdx();
    put(ip,r,"instance",str(inst->getConstName()));put(ip,r,"master",str(inst->getMaster()->getConstName()));
    put(ip,r,"pin_access_idx",num(idx));auto pins=Tcl_NewListObj(0,nullptr);
    for(auto mt:inst->getMaster()->getMTerms())for(auto mp:mt->getMPins()) {
      auto pin=Tcl_NewDictObj();put(ip,pin,"mterm",str(mt->getConstName()));put(ip,pin,"mpin_id",num(mp->getId()));
      auto buckets=mp->getPinAccess();put(ip,pin,"bucket_count",num(buckets.size()));
      auto counts=Tcl_NewListObj(0,nullptr);for(const auto& bucket:buckets)append(ip,counts,num(bucket.size()));
      put(ip,pin,"bucket_sizes",counts);put(ip,pin,"index_in_range",Tcl_NewBooleanObj(idx<buckets.size()));
      auto selected=Tcl_NewListObj(0,nullptr);if(idx<buckets.size())for(auto ap:buckets[idx])append(ip,selected,point(ip,ap));
      put(ip,pin,"selected_points",selected);append(ip,pins,pin);
    }
    put(ip,r,"pins",pins);Tcl_SetObjResult(ip,r);return TCL_OK;
  }catch(const std::exception& e){Tcl_SetObjResult(ip,str(e.what()));return TCL_ERROR;}
}
}
extern "C" int Apreader_Init(Tcl_Interp* ip) {
  if(Tcl_EvalEx(ip,"lindex [exec sha256sum -- [info nameofexecutable]] 0",-1,TCL_EVAL_GLOBAL)!=TCL_OK)return TCL_ERROR;
  if(std::string(Tcl_GetStringResult(ip))!="21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846"){
    Tcl_SetObjResult(ip,str("OT_AP_READER_BINARY_ABI_REFUSED"));return TCL_ERROR;
  }
  Tcl_CreateObjCommand(ip,"ot_ap_read_instance",read,nullptr,nullptr);
  return Tcl_PkgProvide(ip,"apreader","0.1");
}
