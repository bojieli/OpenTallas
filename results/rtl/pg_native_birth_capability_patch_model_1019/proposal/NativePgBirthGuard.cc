// SOURCE PROPOSAL ONLY. Native lifecycle/EST/mutation integration incomplete.
#include "NativePgBirthGuard.hh"
#include <stdexcept>
#include <set>
namespace odb {
[[noreturn]] void NativePgBirthGuard::fail(const char* reason)
{
  poisoned_ = true;
  throw std::runtime_error(reason); // Caller must terminate run, not recover.
}
NativePgBirthGuard::NativePgBirthGuard(dbBlock* block) : block_(block)
{
  for (auto* rule : block_->getGlobalConnects()) {
    auto* net = rule->getNet();
    if (!net) fail("PG_RULE_NULL_NET");
    rules_.push_back({rule->getRegion(), net,
                     std::regex(rule->getInstPattern()),
                     std::regex(rule->getPinPattern())});
  }
  if (rules_.empty()) fail("PG_NATIVE_RULES_ABSENT");
  auditAll(); // entry census only, no historical birth assertion
  addOwner(block_);
}
std::vector<std::pair<dbITerm*, dbNet*>>
NativePgBirthGuard::resolve(dbInst* inst)
{
  if (poisoned_) fail("PG_RUN_POISONED");
  std::vector<std::pair<dbITerm*, dbNet*>> targets;
  for (auto* master_term : inst->getMaster()->getMTerms()) {
    auto role = master_term->getSigType();
    if (role != dbSigType::POWER && role != dbSigType::GROUND) continue;
    auto* term = inst->getITerm(master_term);
    if (!term) fail("PG_MISSING_ITERM");
    std::set<dbNet*> nets;
    for (const auto& rule : rules_) {
      if (rule.region && rule.region != inst->getRegion()) continue;
      if (!std::regex_match(inst->getConstName(), rule.instances)) continue;
      if (!std::regex_match(master_term->getConstName(), rule.pins)) continue;
      if (rule.net->getSigType() != role) fail("PG_NATIVE_RULE_ROLE_MISMATCH");
      nets.insert(rule.net);
    }
    if (nets.size() != 1) fail("PG_DOMAIN_MISSING_OR_AMBIGUOUS");
    targets.emplace_back(term, *nets.begin());
  }
  return targets;
}
void NativePgBirthGuard::audit(dbInst* inst)
{
  for (auto [term, net] : resolve(inst))
    if (term->getNet() != net) fail("PG_BINDING_MISMATCH");
}
void NativePgBirthGuard::auditAll()
{
  for (auto* inst : block_->getInsts()) audit(inst);
}
void NativePgBirthGuard::changed() { ++generation_; }
void NativePgBirthGuard::inDbInstCreateBegin(dbInst* inst)
{
  if (context_ != Context::Placement || poisoned_) fail("PG_BIRTH_UNSUPPORTED_CONTEXT");
  pending_.push_back(inst);
  changed();
}
void NativePgBirthGuard::inDbInstCreateEnd(dbInst* inst)
{
  if (pending_.empty() || pending_.back() != inst) fail("PG_CREATE_ORDER");
  const auto targets = resolve(inst); // resolve WHOLE instance before mutation
  for (auto [term, net] : targets) {
    if (term->getNet() == net) continue;
    if (term->getNet()) fail("PG_BIRTH_WRONG_EXISTING_NET");
    if (inst->isDoNotTouch() || net->isDoNotTouch()) fail("PG_PROTECTED_UNBOUND");
  }
  for (auto [term, net] : targets) {
    if (term->getNet() == net) continue;
    term->connect(net);
    if (net->isSpecial()) term->setSpecial();
  }
  audit(inst);
  pending_.pop_back();
}
void NativePgBirthGuard::inDbInstDoNotTouchBefore(dbInst* inst)
{
  if (!pending_.empty()) fail("PG_PROTECT_DURING_BIRTH");
  audit(inst); // never repair here
}
void NativePgBirthGuard::inDbITermPostConnect(dbITerm*) { changed(); }
void NativePgBirthGuard::inDbITermPostDisconnect(dbITerm*, dbNet*) { changed(); }
void NativePgBirthGuard::inDbPostMoveInst(dbInst*) { changed(); }
void NativePgBirthGuard::inDbInstSwapMasterBefore(dbInst*, dbMaster*)
{
  fail("PG_MASTER_SWAP_UNSUPPORTED"); // no reentrant analysis window
}
void NativePgBirthGuard::inDbInstSwapMasterAfter(dbInst* inst)
{
  changed(); audit(inst); // changed role/term mapping refuses; no late repair
}
void NativePgBirthGuard::refuseRuleDomainOrMasterMutation()
{
  fail("PG_RULE_DOMAIN_MASTER_MUTATION_UNSUPPORTED");
}
void NativePgBirthGuard::enterPlacementScope()
{
  if (context_ != Context::Unsupported || poisoned_) fail("PG_SCOPE_NESTING");
  auditAll(); context_ = Context::Placement;
}
void NativePgBirthGuard::leavePlacementScope()
{
  if (!pending_.empty()) fail("PG_SCOPE_PENDING_BIRTH");
  auditAll(); context_ = Context::Unsupported;
}
uint64_t NativePgBirthGuard::beforeFullPlacementEstimate()
{
  if (context_ != Context::Placement || !pending_.empty()) fail("PG_EST_UNSUPPORTED_CONTEXT");
  auditAll(); return generation_;
}
void NativePgBirthGuard::afterFullPlacementEstimate(uint64_t generation)
{
  if (generation != generation_ || !pending_.empty()) fail("PG_MUTATED_DURING_ESTIMATE");
  estimated_generation_ = generation;
}
void NativePgBirthGuard::beforeIncrementalEstimate()
{
  if (!pending_.empty() || context_ != Context::Placement) fail("PG_INCR_CONTEXT");
  // O(1) only AFTER all native invalidation hooks are integrated.
  // Do not scan the whole block on each per-net ensureWireParasitic call.
  if (poisoned_) fail("PG_RUN_POISONED");
  if (generation_ != estimated_generation_) fail("PG_INCR_DIRTY_CLOSURE_UNPROVED");
  // No success notification: incremental never certifies an uncovered birth.
}
void NativePgBirthGuard::beforeTimingOrQualifiedWrite()
{
  if (!pending_.empty()) fail("PG_ANALYSIS_DURING_BIRTH");
  auditAll();
  if (generation_ != estimated_generation_) fail("PG_ANALYSIS_RC_DIRTY");
}
void NativePgBirthGuard::refuseRoutedOrSpefAnalysis()
{
  fail("PG_ROUTED_SPEF_CAPABILITY_UNSUPPORTED");
}
} // namespace odb
