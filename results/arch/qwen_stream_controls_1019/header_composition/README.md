# Actual header producer to native consumer

Final r4 component proof passes10,000edges and1,460,000orderedheader checks at each -80/0/+80ps writerphase at833.333ps functional period. Exact55eb5d887 upstream header source and oldgenericLPhelpers are copied byte-identically under rtl/test/qwen_dv/stream_controls/header_sources with source_manifest.json. Reference path uses actualW1088/D4/K2 chunkedwriter/readers and originalsw_q/se_q capture. Candidate146headerbits come from actualfivefieldreaders and146keptcaptureFF; they feed the native1195cd50b consumer, not repeatedscalar ties.

Actualcommand_q→SETIDsid_q update equation is present. All146copiedbits must seeboth0/1. All8kindvalues and independentPRNGdestinations are used. Each phase contains191SID-targeted table events and161broadcast events; targetedSIDmaskffff provesall16currentSIDs exercised. Sixreal faults fail: rawvalid28, wrongSID37, consumerreset1, oldSID37, header+1edge33 (also±80phases), capture-reset701. Logs are in r4/.

Producer state is independently measured GENERIC201FF (146asynccorecapture+55LPreadstate) in6d257d103; upstream_generic_census.json.gz preserves that scoped evidence. Native consumer is independently40956ASAP7cells/6459FF withdirect+transparentultimate24. Combinedparent native preservation/electrical remains unproved.

R1oldSIDfault was ineffective because its negedgesnapshot matched actualcurrentSID atconsumer capture; mut4 PASS escape and originalbench are retained in r1/. Correctedfault uses a realposedgepreviousSID. R2 proves correctedage/reset faults; R3 addsall8kinds/146bitdynamiccoverage; R4 additionally requires targeted/broadcast/allSID routing coverage. Production RTL did not change across these fixture refinements. No proof failures were overwritten.

Configuration and SUreturn copies,95consumerreset leaves and globalparentreset forests remain explicitlogicalmodels/open in this component. Original writer epochs/diagnostics are preserved; this proof adopts noepoch=0tie or physicalnoepochvariant. FullE/Wproduction, actualnativeclockphase, geometry/reach/PG/TTFF and physical parentadmission remain open. No gate or release qualification is implied.
