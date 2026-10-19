# PVM whole-macro mirror successor, mapped budget

The current packet is results/arch/hbm_pvm_safe2_1019/mirror_geometry_mapped. Earlier mirror_geometry is retained historical model-only review evidence. All canonical failed s2 physical artifacts and macros remain immutable.

Same302.4square outline and43.2lattice origin, complete SRAM171.288x153.912 R180, all1585contacts onactualtracks. Actual clockcontact214.476/196.332 is32.898um from the one legal band. No data/calendar edge change; coherent fullcontact/PG/OBS/RC/Lib views and actual newmacro nativebehavior exact240/tight192 plus4mutants PASS expected.

ActualOpenDB measured stdcellmass9023.13918um2 AFTER standardtie-repair. Current oneband realcore[2.16,229.23,300.24,300.24] gives42.63% modeledfill; actualafterplacement cell/row census is stillrequired. Prior41.19% used Yosysarea10343 and is notactualplacedmass. The old gate41.3% was totalcorefill.

16 kept final-reset landing copies use the existing proven synthesistransform, retain2edge release and split391coarseloads max25. ActualASAP7 mappedOpenDB allnonclockfunctional/reset loads<=25. Standardrepair_tie_fanout split801HIGH+34LOW into835localties; every835sink/value binding is exactlyidentical. This proves fanout/source semantics; externalPG/via/DRC access remains open. Raw24x24nm macrocontacts require minimumarea patches.

No CTS/gate/adoption. TTsetup/FFhold, nativeclock references, registeredreach, actualoneband and criticallayoutreview remainrequired. Read design_review.json and mapped_census/record.json. No REVIEW.json or submit.

The hop model in hop_model/model.json uses the actual mapped macro fanin/fanout graph. The runtime macro_regions.tcl recomputes membership, creates nonoverlapping DEF fences inside the same legal row band, and fails on an unexpected macro-cone input. It does not rely on a stored cell-name list. Current internal cone8437cells/1322.79966um² occupies86.4..259.2 x230.04..247.32 at44.30%;546Wmacroconstantties occupy86.4..172.8 x229.23..229.77 at51.19%. Remaining cells use the same north band. No new power domain or row band is created.

The actual boundary graph has522registers on seven inputs: sum,ev,fold_a,fold_start,pub_slot,pub_start,tag_d. tag_d[14] is the ev_first control and its FF was renamed by synthesis; it is included by connectivity. These complete input ports useN86.4..259.2; other ports still use the fullNface. Four-track pin spacing(.192um) and8staggered IOflop rows support the source face demand. Allowing one1.08um FF footprint around its pin range, the worst modeled macro/FF endpoint is385.152um; constant316.44, other register pairs369.09. Route detours and actual timing remain unqualified.

The pre-DPL validator refuses unplaced cells, any functional cell outside the sole band, missing/wrong fences or macro orientation/origin, and an actual macro/FF or direct-net endpoint farther than405um. It runs before CTS. OpenDB EXCLUSIVE is the hard DEF FENCE enum, as documented in https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/odb/include/odb/dbTypes.h and checked against the pinned tool image. Roundtrip mechanism and unknown-input negative evidence accompany the model. These checks do not replace nativeTT/FF STA or macro externalPG/via/DRC signoff.
