// Gibbs literal CASE1/new-session recipe, same real parent and provider.
// +SFU_NEXT is scheduled by Lorentz AFTER first norm terminal; no norm gate
// replay. +CONTINUE_SFU permits same-process sequencing if no prior norm run.
static void run_native_sfu_next(Sim& s,const std::filesystem::path& dir){
 auto& d=s.dut;
 constexpr uint32_t SJ=0x9234abce,SG=10,ST=0x10002,SP=0xfffff;
 auto F=[](auto& p,bool foreign=false){put(p,0,32,SJ);put(p,32,4,SG);put(p,36,17,ST^(foreign?0x10000:0));put(p,53,20,SP);};
 auto O=[](const auto& p){return bits(p,0,32)==SJ&&bits(p,32,4)==SG&&bits(p,36,17)==ST&&bits(p,53,20)==SP;};
 auto field=[](const std::string& value,unsigned start,unsigned count){
  require(count<=32,"SFU retained field too wide");uint32_t n=0;
  for(unsigned k=0;k<count;++k){unsigned bit=start+k;unsigned nibble=std::stoul(value.substr(value.size()-1-bit/4,1),nullptr,16);n|=((nibble>>(bit%4))&1U)<<k;}return n;
 };
 auto case1=[](const std::filesystem::path& path){std::ifstream f(path);require(bool(f),"SFU retained vectors required");std::string value;
  for(unsigned i=0;i<2;++i)require(bool(f>>value),"missing SFU case1");
  require(value.size()==521&&value.find_first_not_of("0123456789abcdefABCDEF")==std::string::npos,"SFU2083/2081 shape mismatch");return value;};
 const auto req=case1(dir/"sfu_req.mem"),expected=case1(dir/"sfu_exp.mem");
 require(field(req,2048,3)==1&&field(req,2051,32)==0xc5000001&&field(expected,2048,1)==0&&field(expected,2049,32)==0xc5000001,"retained SFU case1 opcode/tag/error mismatch");
 unsigned changed=0;for(unsigned i=0;i<64;++i)changed+=field(req,i*32,32)!=field(expected,i*32,32);
 require(changed==64,"SFU continuation must exercise arithmetic, not identity opcode");
 // The previous norm run has already accepted actual completion and warm ACK.
 // Release the request, wait real CP_IDLE; no POR, force or clearing debt.
 s.neg();d.cp_reset_req=0;s.phase="SFU next actual reset release";
 s.wait([&]{return (d.db_rdy&1)&&(d.sfu_vm_bind_r&1);});
 require(!(d.norm_retained&1)&&!(d.sfu_retained&1)&&!(d.sfu_vm_retained&1),"prior native owner debt remains");
 const auto old_db=d.fixture_db_accepts,old_bind=d.fixture_bind_accepts,old_retire=d.fixture_retire_accepts,old_cpl=d.fixture_cpl_accepts;
 s.neg();d.cmd_we=1;put(d.cmd_addr,0,8,0);put(d.cmd_wdata,0,32,0);put(d.cmd_wdata,32,32,0x20000000);s.sm();s.neg();d.cmd_we=0;
 put(d.db_token,0,17,ST);put(d.db_pos,0,20,SP);put(d.db_job,0,32,SJ);put(d.db_generation,0,4,SG);
 d.db_v=1;s.phase="SFU distinct actual CP context";s.wait([&]{return d.fixture_db_accepts==old_db+1;});s.neg();d.db_v=0;
 F(d.sfu_vm_bind_frame);put(d.sfu_vm_bind_rank,0,7,41);put(d.sfu_vm_bind_base,0,32,64);put(d.sfu_vm_bind_span,0,32,64);
 d.sfu_vm_bind_v=1;s.phase="SFU actual root allocation";s.wait([&]{return d.fixture_bind_accepts==old_bind+1;});s.neg();d.sfu_vm_bind_v=0;
 require((d.sfu_vm_retained&1)&&O(d.sfu_vm_held_frame),"SFU actual native allocation absent");
 // Exclusive caller input allocation comes from authentic prepared HBM image.
 // This is not a shared-calendar grant; that stays fully inside real RTL.
 F(d.sfu_allocation_frame);d.sfu_allocation_valid=1;
 put(d.sfu_source_addr,0,32,0xa0000);put(d.sfu_source_base,0,32,0xa0000);put(d.sfu_source_limit,0,32,0xa0100);
 put(d.sfu_dest_addr,0,32,256);put(d.sfu_dest_base,0,32,256);put(d.sfu_dest_limit,0,32,512);
 put(d.sfu_fn,0,3,1);put(d.sfu_local_tag,0,32,0xc5000001);put(d.sfu_count,0,9,1);put(d.sfu_expert,0,9,41);
 // Foreign highTOKEN offer cannot acquire stage/calendar under correct root.
 F(d.sfu_enroll_frame,true);d.sfu_enroll_v=1;s.phase="SFU foreign full73 refusal";s.settle();
 for(unsigned i=0;i<7;++i){require(!(d.sfu_enroll_r&1),"foreign SFU ready");s.sm();s.healthy();require(d.fixture_sfu_enroll_accepts==0&&!(d.sfu_retained&1)&&(d.sfu_vm_retained&1)&&O(d.sfu_vm_held_frame)&&d.fixture_sfu_cp_requests==0,"foreign SFU accepted or root lost");}
 s.neg();F(d.sfu_enroll_frame);s.phase="SFU actual correct enrollment";s.wait([&]{return d.fixture_sfu_enroll_accepts==1;});s.neg();d.sfu_enroll_v=0;
 F(d.sfu_publication_owner);s.phase="SFU actual arithmetic/provider/publication";s.wait([&]{return (d.sfu_publication_v&1)!=0;});
 require(d.fixture_sfu_cp_requests==8&&d.fixture_sfu_cp_returns==8&&d.fixture_sfu_TXs==3&&d.fixture_sfu_ACKs==2,"SFU actual8CP/3TX/2ACK accounting incomplete");
 auto H=[&]{s.healthy();require((d.sfu_retained&1)&&(d.sfu_vm_retained&1)&&O(d.sfu_held_frame)&&O(d.sfu_vm_held_frame)&&!(d.cpl_v&1),"SFU held owner/debt changed");};
 F(d.sfu_vm_index_read_frame);put(d.sfu_vm_index_read_rank,0,7,41);put(d.sfu_vm_index_read_words,0,6,32);
 unsigned old_reads=d.fixture_read_accepts,old_rsps=d.fixture_rsp_accepts;
 for(unsigned row=0;row<2;++row){s.neg();put(d.sfu_vm_index_read_addr,0,32,64+32*row);put(d.sfu_vm_index_read_tag,0,8,row);d.sfu_vm_index_read_v=1;
  s.phase="SFU actual samebank64 readback";s.wait([&]{return d.fixture_read_accepts==old_reads+row+1;});s.neg();d.sfu_vm_index_read_v=0;
  s.wait([&]{return (d.sfu_vm_index_rsp_v&1)!=0;});Row actual{};for(unsigned k=0;k<32;++k)actual[k]=bits(d.sfu_vm_index_rsp_data,k*32,32);
  for(unsigned hold=0;hold<3;++hold){H();require((d.sfu_vm_index_rsp_v&1)&&O(d.sfu_vm_index_rsp_frame)&&bits(d.sfu_vm_index_rsp_tag,0,8)==row&&bits(d.sfu_vm_index_rsp_rank,0,7)==41,"SFU held readback metadata");
   for(unsigned k=0;k<32;++k)require(bits(d.sfu_vm_index_rsp_data,k*32,32)==actual[k],"SFU held readback payload changed");s.sm();}
  for(unsigned k=0;k<32;++k)require(actual[k]==field(expected,(row*32+k)*32,32),"SFU retained arithmetic golden mismatch lane="+std::to_string(row*32+k));
  s.neg();d.sfu_vm_index_rsp_r=1;s.wait([&]{return d.fixture_rsp_accepts==old_rsps+row+1;});s.neg();d.sfu_vm_index_rsp_r=0;
 }
 s.neg();d.cp_reset_req=1;s.phase="SFU held warm lease";
 for(unsigned i=0;i<7;++i){s.sm();H();require((d.sfu_publication_v&1)&&!(d.cp_reset_ack&1)&&!(d.sfu_warm_ack&1)&&!(d.sfu_vm_warm_ack&1),"SFU warm dropped held result");}
 s.neg();d.sfu_publication_r=1;s.phase="SFU real joint publication/reverse ACK";s.wait([&]{return !(d.sfu_retained&1);});s.neg();d.sfu_publication_r=0;
 require(d.fixture_sfu_releases==1,"SFU shared reverse ACK absent");
 F(d.sfu_vm_retire_frame);d.sfu_vm_retire_v=1;s.phase="SFU actual root retirement";s.wait([&]{return d.fixture_retire_accepts==old_retire+1;});s.neg();d.sfu_vm_retire_v=0;
 s.phase="SFU actual END context completion";s.wait([&]{return (d.cpl_v&1)!=0;});
 require(bits(d.cpl_data,37,4)==2&&bits(d.cpl_data,17,20)==SP&&bits(d.cpl_data,73,4)==SG&&bits(d.cpl_data,77,32)==SJ,"SFU context completion/status mismatch");
 s.neg();d.cpl_rdy=1;s.wait([&]{return d.fixture_cpl_accepts==old_cpl+1;});s.neg();d.cpl_rdy=0;
 s.phase="SFU joint warm acknowledgment";s.wait([&]{return (d.cp_reset_ack&1)&&(d.sfu_warm_ack&1)&&(d.sfu_vm_warm_ack&1);});
 // Only actual SFU stage numerics are qualified by this terminal. No selected-ID
 // RESULT kernel or installed formatter receipts exist in current parent.
 std::cout<<"PARENT_NATIVE_SFU_STAGE_PASS case=1 fn=1 changed_lanes=64 CP=8/8 TX=3 SRAM_ACK=2 samebank_golden=64 full73_refusal=1 warm_joint=1 cpl_context_status=2 token_qualified=0 formatter_execution_covered=0 all_levers_qualified=0 cycles="<<s.cycles<<"\n";
 std::cout<<"PARENT_FORMATTER_OPEN missing=installed_book_receipt,released96x512_score_ID_producer,selected_ID_sink_publication,source_reverse_receipt,native_result_to_SM_RESULT_program\n";
}
