// SOURCE PROPOSAL ONLY; not compiled, registered, shipped or advertised as v1.
#pragma once
#include <cstdint>
#include <regex>
#include <vector>
#include <utility>
#include "odb/db.h"
#include "odb/dbBlockCallBackObj.h"
namespace odb {
class NativePgBirthGuard : public dbBlockCallBackObj {
 public:
  enum class Context { Unsupported, Placement };
  // Construct AFTER import and source-owned rule installation. No repairs here.
  explicit NativePgBirthGuard(dbBlock* block);
  void inDbInstCreateBegin(dbInst* inst) override;
  void inDbInstCreateEnd(dbInst* inst) override;
  void inDbInstDoNotTouchBefore(dbInst* inst) override;
  void inDbITermPostConnect(dbITerm*) override;
  void inDbITermPostDisconnect(dbITerm*, dbNet*) override;
  void inDbPostMoveInst(dbInst*) override;
  void inDbInstSwapMasterBefore(dbInst*, dbMaster*) override;
  void inDbInstSwapMasterAfter(dbInst*) override;
  // Must be called by native pre-mutation sites listed in MUTATION_SURFACE.md.
  void refuseRuleDomainOrMasterMutation();
  // Native command scope, NOT a Tcl stage string. Requires additional audited
  // CTS/RSZ caller entry integration; absent integration keeps Unsupported.
  void enterPlacementScope();
  void leavePlacementScope();
  uint64_t beforeFullPlacementEstimate();
  void afterFullPlacementEstimate(uint64_t generation);
  void beforeIncrementalEstimate(); // refuses dirty until closure witness exists
  void beforeTimingOrQualifiedWrite(); // read-only; never binds
  void refuseRoutedOrSpefAnalysis();
 private:
  struct Rule {
    dbRegion* region;
    dbNet* net;
    std::regex instances;
    std::regex pins;
  };
  [[noreturn]] void fail(const char* reason);
  std::vector<std::pair<dbITerm*, dbNet*>> resolve(dbInst* inst);
  void audit(dbInst* inst);
  void auditAll();
  void changed();
  dbBlock* block_;
  std::vector<Rule> rules_;
  std::vector<dbInst*> pending_;
  Context context_ = Context::Unsupported;
  uint64_t generation_ = 0;
  uint64_t estimated_generation_ = UINT64_MAX;
  bool poisoned_ = false;
};
} // namespace odb
