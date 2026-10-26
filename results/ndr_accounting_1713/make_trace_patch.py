from pathlib import Path
import difflib
r=Path(__file__).parent
old=(r/'source/pinned_graph2d.cpp').read_text();new=old.replace('#include <algorithm>','#include <algorithm>\n#include <atomic>',1)
new=new.replace('namespace grt {','''namespace grt {
namespace {
// Diagnostic only: selected old E5 failed edge. No clamping/accounting change.
std::atomic<uint64_t> ot_ndr_trace_sequence{0};
constexpr int ot_ndr_trace_x = 654;
constexpr int ot_ndr_trace_y = 528;
}  // namespace
''',1)
for method,member,op in [('updateEstUsageV','est_usage','EST'),('updateUsageV','usage','ACTUAL')]:
 expr=f'  v_edges_[x][y].{member}\n      += getCostNDRAware(net, x, y, usage, EdgeDirection::Vertical);'
 assert new.count(expr)==1,(method,new.count(expr))
 prediction='static_cast<double>(edge.usage) + ot_est_before + ot_delta' if op=='EST' else 'static_cast<double>(edge.usage) + ot_delta'
 repl='''  auto& edge = v_edges_[x][y];
  const double ot_est_before = edge.est_usage;
  const auto ot_ndr_before = edge.ndr_overflow;
  const bool ot_present_before
      = v_ndr_nets_[x][y].find(net) != v_ndr_nets_[x][y].end();
  const double ot_delta
      = getCostNDRAware(net, x, y, usage, EdgeDirection::Vertical);
  const double ot_next = PREDICT;
  if ((x == ot_ndr_trace_x && y == ot_ndr_trace_y)
      || !std::isfinite(ot_next) || ot_next < 0.0 || ot_next > 65535.0) {
    logger_->report(
        "OT_NDR_ACCOUNTING seq={} op=OP net_id={} net={} dir=V x={} y={} "
        "edge_cost={} requested={} delta={} usage_before={} "
        "est_before={} predicted={} ndr_before={} ndr_after={} "
        "present_before={} present_after={}",
        ot_ndr_trace_sequence.fetch_add(1),
        net->getDbNet()->getId(), net->getName(), x, y,
        static_cast<int>(net->getEdgeCost()), usage, ot_delta,
        edge.usage, ot_est_before, ot_next, ot_ndr_before,
        edge.ndr_overflow, ot_present_before,
        v_ndr_nets_[x][y].find(net) != v_ndr_nets_[x][y].end());
  }
  edge.MEMBER += ot_delta;'''.replace('PREDICT',prediction).replace('op=OP','op='+op).replace('edge.MEMBER','edge.'+member)
 new=new.replace(expr,repl,1)
expr='  foreachEdge([](Edge& edge) { edge.usage += edge.est_usage; });';assert new.count(expr)==1
new=new.replace(expr,'''  foreachEdge([this](Edge& edge) {
    const double ot_next = static_cast<double>(edge.usage) + edge.est_usage;
    if (!std::isfinite(ot_next) || ot_next < 0.0 || ot_next > 65535.0) {
      logger_->report(
          "OT_NDR_BAD_CONVERSION seq={} usage_before={} est_usage={} "
          "predicted={} ndr_overflow={}",
          ot_ndr_trace_sequence.fetch_add(1), edge.usage,
          edge.est_usage, ot_next, edge.ndr_overflow);
    }
    // Preserve native conversion/exit behavior: diagnostic, not a repair.
    edge.usage += edge.est_usage;
  });''',1)
(r/'trace_candidate.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/src/grt/src/fastroute/src/graph2d.cpp',tofile='b/src/grt/src/fastroute/src/graph2d.cpp')))
