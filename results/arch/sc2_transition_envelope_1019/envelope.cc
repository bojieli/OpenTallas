// Read-only native NLDM extraction/calibration. No production flow hook.
#include <tcl.h>
#include <sstream>
#include <iomanip>
#include <stdexcept>
#include "sta/Sta.hh"
#include "sta/Network.hh"
#include "sta/Scene.hh"
#include "sta/Liberty.hh"
#include "sta/TimingArc.hh"
#include "sta/TimingRole.hh"
#include "sta/TableModel.hh"
#include "sta/MinMax.hh"
static void table(std::ostream &o,const sta::TableModel *m) {
 if (!m || m->order()!=2) throw std::runtime_error("only exact 2D NLDM supported");
 o << "{\"axis1_kind\":\"" << m->axis1()->variableString() << "\",\"axis2_kind\":\"" << m->axis2()->variableString() << "\",\"axis1\":[";
 for(size_t i=0;i<m->axis1()->size();++i) {if(i)o<<',';o<<m->axis1()->axisValue(i);}
 o<<"],\"axis2\":[";for(size_t j=0;j<m->axis2()->size();++j){if(j)o<<',';o<<m->axis2()->axisValue(j);}
 o<<"],\"values\":[";for(size_t i=0;i<m->axis1()->size();++i){if(i)o<<',';o<<'[';for(size_t j=0;j<m->axis2()->size();++j){if(j)o<<',';o<<m->value(i,j,0);}o<<']';}o<<"]}";
}
static int query(ClientData,Tcl_Interp *ip,int argc,Tcl_Obj *const argv[]) {
 try {
  if(argc!=7)throw std::runtime_error("instance role_bound axis1 axis2 from to required");
  auto *s=sta::Sta::sta();auto *n=s->cmdNetwork();auto *inst=n->findInstance(Tcl_GetString(argv[1]));
  if(!inst)throw std::runtime_error("missing actual instance");
  std::string bound=Tcl_GetString(argv[2]);if(bound!="min" && bound!="max")throw std::runtime_error("unsupported role bound");
  auto *mm=bound=="min"?sta::MinMax::min():sta::MinMax::max();
  auto *base=s->network()->libertyCell(inst);auto *cell=base->sceneCell(s->cmdScene(),mm);
  if(!cell)throw std::runtime_error("missing mapped cell");
  double x,y;if(Tcl_GetDoubleFromObj(ip,argv[3],&x)||Tcl_GetDoubleFromObj(ip,argv[4],&y))return TCL_ERROR;
  std::ostringstream o;o<<std::setprecision(12)<<'[';bool first=true;
  for(auto *set:base->timingArcSets()) {
   if(!set->from() || !set->to() || std::string(set->from()->name())!=Tcl_GetString(argv[5]) || std::string(set->to()->name())!=Tcl_GetString(argv[6]))continue;
   for(auto *original:set->arcs()) {
   auto *a=original->sceneArc(s->cmdScene()->libertyIndex(mm));
   if(!a || !a->model())throw std::runtime_error("missing actual mapped arc");
   const sta::TableModel *m=nullptr;const sta::TableModel *sl=nullptr;
   if(auto *g=dynamic_cast<const sta::GateTableModel*>(a->model())){m=g->delayModel();sl=g->slewModel();}
   else if(auto *c=dynamic_cast<const sta::CheckTableModel*>(a->model()))m=c->checkModel();
   else continue;
   if(!first)o<<',';first=false;
   o<<"{\"cell\":\""<<cell->name()<<"\",\"library\":\""<<cell->libertyLibrary()->name()<<"\",\"from\":\""<<a->from()->name()<<"\",\"to\":\""<<a->to()->name()<<"\",\"role\":\""<<a->role()->to_string()<<"\",\"rf\":"<<m->rfIndex()<<",\"query\":["<<x<<','<<y<<"],\"value\":"<<m->findValue(x,y,0)<<",\"table\":";table(o,m);
   if(sl){o<<",\"transition_raw\":"<<sl->findValue(x,y,0)<<",\"transition_table\":";table(o,sl);}
   o<<'}';
  }}
  o<<']';Tcl_SetObjResult(ip,Tcl_NewStringObj(o.str().c_str(),-1));return TCL_OK;
 }catch(const std::exception&e){Tcl_SetObjResult(ip,Tcl_NewStringObj(e.what(),-1));return TCL_ERROR;}
}
extern "C" int Otenvelope_Init(Tcl_Interp *ip){Tcl_CreateObjCommand(ip,"ot_envelope_query",query,nullptr,nullptr);return TCL_OK;}
