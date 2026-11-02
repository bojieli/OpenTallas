// SPDX-License-Identifier: BSD-3-Clause
// Native OpenDB callback prototype. No Tcl command-return repair is used.
#include <tcl.h>
#include <odb/db.h>
#include <odb/dbBlockCallBackObj.h>
#include <cctype>
#include <map>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using namespace odb;
struct Pending { dbITerm* term; dbNet* net; };
struct Birth : dbBlockCallBackObj {
  dbBlock* block;
  std::map<std::string, dbNet*> rules;
  std::recursive_mutex mutex;
  unsigned long creates=0, swaps=0, bound=0;
  explicit Birth(dbBlock* b) : block(b) { rules = read_rules(); audit_all(); addOwner(b); }
  static void fail(const std::string& s) { throw std::runtime_error("OT_PG_BIRTH_"+s); }
  static std::string literal(std::string s) {
    if (!s.empty() && s.front()=='^') s.erase(0,1);
    if (!s.empty() && s.back()=='$') s.pop_back();
    if (s.empty() || !(std::isalpha((unsigned char)s[0]) || s[0]=='_')) fail("UNSUPPORTED_PIN");
    for (unsigned char c : s) if (!(std::isalnum(c) || c=='_')) fail("UNSUPPORTED_PIN");
    return s;
  }
  std::map<std::string, dbNet*> read_rules() {
    std::map<std::string, dbNet*> out;
    for (auto r : block->getGlobalConnects()) {
      if (r->getInstPattern()!=".*" || r->getRegion()!=nullptr) fail("UNSUPPORTED_RULE_CONTEXT");
      auto n=r->getNet();
      if (!n || (n->getSigType()!=dbSigType::POWER && n->getSigType()!=dbSigType::GROUND)) fail("RULE_ROLE");
      auto pin=literal(r->getPinPattern());
      auto [it, inserted]=out.emplace(pin,n);
      if (!inserted && it->second!=n) fail("AMBIGUOUS_DOMAIN "+pin);
    }
    if (out.empty()) fail("NO_RULES");
    return out;
  }
  void check_rules() { if (read_rules()!=rules) fail("RULES_CHANGED"); }
  dbNet* expected(dbMTerm* m) {
    auto it=rules.find(m->getName());
    if (it==rules.end()) fail("UNKNOWN_DOMAIN "+m->getName());
    if (it->second->getSigType()!=m->getSigType()) fail("PIN_ROLE "+m->getName());
    return it->second;
  }
  static bool pg(dbMTerm* m) { return m->getSigType()==dbSigType::POWER || m->getSigType()==dbSigType::GROUND; }
  void master_ok(dbMaster* m) {
    for (auto [pin, net]:rules) {
      auto p=m->findMTerm(pin.c_str());
      if (p && !pg(p)) fail("RULE_SIGNAL_PIN "+pin);
    }
    for (auto p:m->getMTerms()) if (pg(p)) expected(p);
  }
  void audit(dbInst* i) {
    master_ok(i->getMaster());
    for (auto m:i->getMaster()->getMTerms()) if (pg(m)) {
      auto t=i->findITerm(m->getConstName());
      if (!t || t->getMTerm()!=m || t->getNet()!=expected(m)) fail("AUDIT "+i->getName()+"/"+m->getName());
    }
  }
  void audit_all() { std::scoped_lock lock(mutex); check_rules(); for (auto i:block->getInsts()) audit(i); }
  void inDbInstCreate(dbInst* i) override {
    std::scoped_lock lock(mutex);
    check_rules(); master_ok(i->getMaster());
    std::vector<Pending> pending;
    for (auto m:i->getMaster()->getMTerms()) if (pg(m)) {
      auto t=i->findITerm(m->getConstName()); auto n=expected(m);
      if (!t || t->getMTerm()!=m) fail("MISSING_ITERM");
      if (t->getNet() && t->getNet()!=n) fail("WRONG_DOMAIN");
      if (!t->getNet()) pending.push_back({t,n});
    }
    if (!pending.empty() && i->isDoNotTouch()) fail("PROTECTED_UNBOUND");
    for (auto p:pending) { p.term->connect(p.net); ++bound; }
    audit(i); ++creates;
  }
  void inDbInstSwapMasterBefore(dbInst* i, dbMaster* m) override { std::scoped_lock lock(mutex); check_rules(); audit(i); master_ok(m); }
  void inDbInstSwapMasterAfter(dbInst* i) override { std::scoped_lock lock(mutex); check_rules(); audit(i); ++swaps; }
  void inDbITermPreConnect(dbITerm* t, dbNet* n) override {
    std::scoped_lock lock(mutex);
    if (pg(t->getMTerm())) { check_rules(); if (n!=expected(t->getMTerm())) fail("WRONG_DOMAIN"); }
  }
};
std::unique_ptr<Birth> guard;
int install(ClientData, Tcl_Interp* ip, int objc, Tcl_Obj* const objv[]) {
  try {
    if (objc!=3) { Tcl_WrongNumArgs(ip,1,objv,"database_id block_id"); return TCL_ERROR; }
    int d,b; if (Tcl_GetIntFromObj(ip,objv[1],&d)!=TCL_OK || Tcl_GetIntFromObj(ip,objv[2],&b)!=TCL_OK) return TCL_ERROR;
    if (d<=0 || b<=0 || guard) Birth::fail("INSTALL_CONTEXT");
    auto db=dbDatabase::getDatabase(d); auto chip=db ? db->getChip() : nullptr; auto block=chip ? chip->getBlock() : nullptr;
    if (!block || block->getId()!=(unsigned)b) Birth::fail("TOP_BLOCK_ID");
    guard=std::make_unique<Birth>(block);
    Tcl_SetObjResult(ip,Tcl_NewStringObj("NATIVE_CALLBACK_INSTALLED",-1)); return TCL_OK;
  } catch (const std::exception& e) { Tcl_SetObjResult(ip,Tcl_NewStringObj(e.what(),-1)); return TCL_ERROR; }
}
int audit(ClientData, Tcl_Interp* ip, int objc, Tcl_Obj* const objv[]) {
  try {
    if (objc!=1 || !guard) Birth::fail("NOT_INSTALLED");
    guard->audit_all();
    auto r=Tcl_NewDictObj();
    Tcl_DictObjPut(ip,r,Tcl_NewStringObj("creates",-1),Tcl_NewWideIntObj(guard->creates));
    Tcl_DictObjPut(ip,r,Tcl_NewStringObj("swaps",-1),Tcl_NewWideIntObj(guard->swaps));
    Tcl_DictObjPut(ip,r,Tcl_NewStringObj("bound",-1),Tcl_NewWideIntObj(guard->bound));
    Tcl_SetObjResult(ip,r);return TCL_OK;
  } catch (const std::exception& e) { Tcl_SetObjResult(ip,Tcl_NewStringObj(e.what(),-1));return TCL_ERROR; }
}
int uninstall(ClientData, Tcl_Interp* ip, int objc, Tcl_Obj* const objv[]) {
  if (objc!=1) { Tcl_WrongNumArgs(ip,1,objv,""); return TCL_ERROR; }
  guard.reset(); return TCL_OK;
}
int status(ClientData, Tcl_Interp* ip, int objc, Tcl_Obj* const objv[]) {
  if (objc!=1) { Tcl_WrongNumArgs(ip,1,objv,""); return TCL_ERROR; }
  auto r=Tcl_NewDictObj();
  auto put=[&](const char* k,Tcl_Obj* v) { Tcl_DictObjPut(ip,r,Tcl_NewStringObj(k,-1),v); };
  put("contract",Tcl_NewStringObj("native_pg_birth.flat_literal.v1",-1));
  bool active=guard && guard->hasOwner();
  put("active",Tcl_NewBooleanObj(active));
  if (active) {
    put("database_id",Tcl_NewWideIntObj(guard->block->getDataBase()->getId()));
    put("block_id",Tcl_NewWideIntObj(guard->block->getId()));
  }
  Tcl_SetObjResult(ip,r);return TCL_OK;
}
}
extern "C" int Nativepgbirth_Init(Tcl_Interp* ip) {
  // Public OpenDB C++ symbols are used; refuse a different executable ABI.
  if (Tcl_EvalEx(ip,"lindex [exec sha256sum -- [info nameofexecutable]] 0",-1,TCL_EVAL_GLOBAL)!=TCL_OK) return TCL_ERROR;
  if (std::string(Tcl_GetStringResult(ip))!="21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846") {
    Tcl_SetObjResult(ip,Tcl_NewStringObj("OT_PG_BIRTH_BINARY_ABI_REFUSED",-1)); return TCL_ERROR;
  }
  Tcl_CreateObjCommand(ip,"ot_native_pg_install",install,nullptr,nullptr);
  Tcl_CreateObjCommand(ip,"ot_native_pg_audit",audit,nullptr,nullptr);
  Tcl_CreateObjCommand(ip,"ot_native_pg_uninstall",uninstall,nullptr,nullptr);
  Tcl_CreateObjCommand(ip,"ot_native_pg_status",status,nullptr,nullptr);
  return Tcl_PkgProvide(ip,"nativepgbirth","0.2");
}
