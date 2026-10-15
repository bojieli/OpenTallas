// Read-only OpenSTA scene binding census. Build against the running ORFS image.
#include <tcl.h>
#include <exception>
#include <string>
#include "sta/MinMax.hh"
#include "sta/Scene.hh"
#include "sta/Sta.hh"
#include "sta/Network.hh"
#include "sta/Liberty.hh"
#include "sta/TimingArc.hh"
#include "sta/TimingRole.hh"
#include "sta/PortDirection.hh"

namespace {
void field(Tcl_Interp* ip, Tcl_Obj* d, const char* key, const std::string& value) {
  Tcl_DictObjPut(ip, d, Tcl_NewStringObj(key, -1), Tcl_NewStringObj(value.c_str(), -1));
}
int census(ClientData, Tcl_Interp* ip, int argc, Tcl_Obj* const argv[]) {
  if (argc != 3) {Tcl_WrongNumArgs(ip, 1, argv, "instance clock_pin"); return TCL_ERROR;}
  try {
    auto* sta = sta::Sta::sta();
    auto* scene = sta->cmdScene();
    if (!scene) throw std::runtime_error("missing actual active scene");
    auto* network = sta->network();
    auto* inst = network->findInstance(Tcl_GetString(argv[1]));
    if (!inst) throw std::runtime_error("missing actual instance");
    auto* base = network->libertyCell(inst);
    if (!base) throw std::runtime_error("missing actual instance Liberty cell");
    auto* result = Tcl_NewDictObj();
    field(ip, result, "scene", scene->name());
    for (const auto* mm : {sta::MinMax::min(), sta::MinMax::max()}) {
      auto* cell = base->sceneCell(scene, mm);
      if (!cell) throw std::runtime_error("missing actual scene-mapped cell");
      auto* library = cell->libertyLibrary();
      auto* clock = cell->findLibertyPort(Tcl_GetString(argv[2]));
      if (!clock || !clock->isClock() || !clock->direction()->isInput())
        throw std::runtime_error("missing actual input clock pin");
      if (!cell->isMemory()) throw std::runtime_error("actual scene cell has no memory semantics");
      auto* row = Tcl_NewDictObj();
      field(ip, row, "cell", cell->name());
      field(ip, row, "library", library->name());
      field(ip, row, "filename", library->filename());
      field(ip, row, "clock_pin", clock->name());
      // Check the same per-scene arc mapping used by delay calculation,
      // including any missing-arc fallback to the representative cell.
      auto* base_clock = base->findLibertyPort(Tcl_GetString(argv[2]));
      if (!base_clock || base_clock->scenePort(scene, mm) != clock)
        throw std::runtime_error("actual scene clock-port mapping mismatch");
      for (auto* set : base->timingArcSets()) {
        if (set->from() != base_clock) continue;
        for (auto* arc : set->arcs()) {
          auto* mapped = arc->sceneArc(scene->libertyIndex(mm));
          if (!mapped || !mapped->model() || !mapped->from() || !mapped->to()
              || mapped->from()->libertyCell() != cell
              || mapped->to()->libertyCell() != cell
              || mapped->role() != arc->role())
            throw std::runtime_error("actual scene arc mapping/source mismatch");
        }
      }
      auto* arcs = Tcl_NewListObj(0, nullptr);
      bool setup = false, hold = false, cq = false;
      for (auto* arc : cell->timingArcSets()) {
        if (arc->from() != clock) continue;
        const auto* role = arc->role();
        setup |= role == sta::TimingRole::setup();
        hold |= role == sta::TimingRole::hold();
        cq |= role == sta::TimingRole::regClkToQ();
        auto* a = Tcl_NewDictObj();
        field(ip, a, "from", arc->from()->name());
        field(ip, a, "to", arc->to()->name());
        field(ip, a, "role", role->to_string());
        Tcl_ListObjAppendElement(ip, arcs, a);
      }
      if (!setup || !hold || !cq) throw std::runtime_error("actual scene clock lacks setup/hold/clock-to-Q arcs");
      Tcl_DictObjPut(ip, row, Tcl_NewStringObj("arcs", -1), arcs);
      Tcl_DictObjPut(ip, result, Tcl_NewStringObj(mm == sta::MinMax::min() ? "min" : "max", -1), row);
    }
    Tcl_SetObjResult(ip, result);
    return TCL_OK;
  } catch (const std::exception& error) {
    Tcl_SetObjResult(ip, Tcl_NewStringObj(error.what(), -1));
    return TCL_ERROR;
  }
}
}
extern "C" int Otscenebinding_Init(Tcl_Interp* ip) {
  Tcl_CreateObjCommand(ip, "ot_sta_scene_binding", census, nullptr, nullptr);
  return Tcl_PkgProvide(ip, "ot_sta_scene_binding", "1.0");
}
