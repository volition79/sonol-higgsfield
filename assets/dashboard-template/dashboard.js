const fallback = window.SONOL_HIGGSFIELD_STATE || {};
const token = new URLSearchParams(location.search).get("token");
let current = fallback;

const esc = value => String(value ?? "—").replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
const badge = value => { const v=String(value||"UNKNOWN"); const cls=/PASSED|APPROVED|LOCKED|COMPLETE|GENERATED/.test(v)?"good":/FAILED|REVISION|HOLD|CONFLICT|BREACH/.test(v)?"bad":"warn"; return `<span class="state ${cls}">${esc(v)}</span>`; };
const toast = message => { const el=document.querySelector("#toast"); el.textContent=message; el.classList.add("show"); setTimeout(()=>el.classList.remove("show"),2800); };

async function action(payload){
  if(!token){toast("대시보드 서버의 token URL로 열어야 승인할 수 있습니다.");return;}
  try{
    const response=await fetch("/api/action",{method:"POST",headers:{"Content-Type":"application/json","X-Sonol-Token":token},body:JSON.stringify(payload)});
    const data=await response.json(); if(!response.ok) throw new Error(data.error||"action failed"); current=data.state; render(); toast("상태가 기록되었습니다.");
  }catch(error){toast(error.message);}
}

function approvalItems(s){
  const items=[];
  if(s.project?.requirements_lock?.status!=="LOCKED") items.push(`<div class="approval"><div><strong>요구사항 잠금</strong><small>모든 필드가 CONFIRMED일 때만 승인됩니다.</small></div><button onclick='action({action:"lock_requirements"})'>LOCK</button></div>`);
  if(s.project?.cost_approval?.status!=="APPROVED") items.push(`<div class="approval"><div><strong>프로젝트 크레딧 상한</strong><small>라이브 견적 없이 실행할 위험을 포함한 총 사용 한도입니다.</small><input id="budget-ceiling" type="number" min="0" step="0.1" placeholder="credits"></div><button class="money" onclick='approveBudget()'>APPROVE</button></div>`);
  for(const asset of s.assets||[]) if(asset.status==="USER_REVIEW") items.push(`<div class="approval"><div><strong>${esc(asset.id)} / ${esc(asset.label)}</strong><small>ASSET v${esc(asset.version)}</small></div><div class="actions"><button onclick='action({action:"asset_transition",id:${JSON.stringify(asset.id)},version:${Number(asset.version)},target:"USER_APPROVED"})'>APPROVE</button><button class="secondary" onclick='action({action:"asset_transition",id:${JSON.stringify(asset.id)},version:${Number(asset.version)},target:"REVISION_REQUESTED"})'>REVISE</button></div></div>`);
  for(const shot of s.shots||[]) if(shot.approval_status==="USER_REVIEW") items.push(`<div class="approval"><div><strong>${esc(shot.id)} / ${esc(shot.title)}</strong><small>SHOT BOARD v${esc(shot.generation?.version)}</small></div><div class="actions"><button onclick='action({action:"shot_transition",id:${JSON.stringify(shot.id)},version:${Number(shot.generation?.version)},target:"USER_APPROVED"})'>APPROVE</button><button class="secondary" onclick='action({action:"shot_transition",id:${JSON.stringify(shot.id)},version:${Number(shot.generation?.version)},target:"REVISION_REQUESTED"})'>REVISE</button></div></div>`);
  return items;
}

function approveBudget(){const input=document.querySelector("#budget-ceiling");const value=Number(input?.value);if(!Number.isFinite(value)||value<0){toast("유효한 크레딧 상한을 입력하세요.");return;}action({action:"approve_budget",max_credits:value});}

function render(){
  const s=current, summary=s.summary||{}, project=s.project?.project||{};
  document.querySelector("#project-id").textContent=project.id||"PROJECT_001"; document.querySelector("#project-name").textContent=project.name||"Untitled production";
  document.querySelector("#project-meta").textContent=[project.target_platform,project.duration_seconds&&`${project.duration_seconds}s`,project.aspect_ratio,project.resolution,project.language].filter(Boolean).join(" / ")||"요구사항을 준비하는 중입니다.";
  const progress=Number(summary.progress_percent||0); document.querySelector("#progress-value").textContent=`${progress}%`; document.querySelector("#progress-bar").style.width=`${progress}%`; document.querySelector("#generated-at").textContent=s.generated_at||"—";
  document.querySelector("#metric-grid").innerHTML=[[summary.total_shots,"TOTAL SHOTS"],[summary.validated_grammar_shots,"GRAMMAR READY"],[summary.generated_shots,"GENERATED"],[summary.qc_passed_shots,"QC PASSED"],[summary.locked_assets,"LOCKED ASSETS"]].map(([v,l])=>`<div class="metric"><span>${esc(v||0)}</span><small>${l}</small></div>`).join("");
  const approvals=approvalItems(s); document.querySelector("#approval-count").textContent=`${approvals.length} PENDING`; document.querySelector("#approval-queue").innerHTML=approvals.join("")||'<div class="empty">대기 중인 승인이 없습니다.</div>';
  document.querySelector("#blockers").innerHTML=(summary.blockers||[]).map(x=>`<div class="notice">${esc(x)}</div>`).join("")||'<div class="empty">활성 인터록이 없습니다.</div>';
  document.querySelector("#shots-table").innerHTML=(s.shots||[]).map(x=>{const q=Object.values(x.qc||{});const qp=q.filter(v=>v==="PASSED"||v==="NOT_APPLICABLE").length;return `<tr><td><b>${esc(x.id)}</b><br>${esc(x.title)}</td><td>${badge(x.approval_status)}</td><td>${badge(x.shot_grammar?.status)}</td><td>${badge(x.generation?.status)}</td><td>${esc(x.generation?.model)}</td><td>${qp}/${q.length}</td><td>v${esc(x.generation?.version)}</td></tr>`}).join("")||'<tr><td colspan="7">아직 계획된 샷이 없습니다.</td></tr>';
  document.querySelector("#grammar-grid").innerHTML=(s.shots||[]).map(x=>{const g=x.shot_grammar||{};const core=[g.shot_size,g.angle,g.lens_family,g.movement].filter(Boolean).join(" · ");return `<div class="grammar-card"><div><span class="id">${esc(x.id)}</span>${badge(g.status)}</div><h3>${esc(g.dramatic_beat||"촬영 의도 미정")}</h3><p>${esc(core||"기법 미선택")}</p><small>${esc(g.why||"추천 → 선택 → 공급자 컴파일이 필요합니다.")}</small><footer>${esc(g.provider_binding?.provider||"NO PROVIDER")} / ${esc(g.provider_binding?.support_level||"UNVERIFIED")}</footer></div>`}).join("")||'<div class="empty">등록된 샷 문법이 없습니다.</div>';
  document.querySelector("#asset-count").textContent=`${(s.assets||[]).length} ASSETS`; document.querySelector("#assets-grid").innerHTML=(s.assets||[]).map(x=>`<div class="asset"><span class="id">${esc(x.id)} / v${esc(x.version)}</span><h3>${esc(x.label)}</h3>${badge(x.status)} ${x.contains_korean_text?badge(`OCR ${x.ocr_status}`):""}</div>`).join("")||'<div class="empty">등록된 자산이 없습니다.</div>';
  const ref=s.costs?.reference_estimates||{}, actual=s.costs?.actual||{}; document.querySelector("#cost-panel").innerHTML=`<div class="cost-row"><span>REFERENCE ONLY</span><b>${ref.total_estimated_credits==null?esc(ref.status||"NOT COMPUTED"):esc(ref.total_estimated_credits)}</b></div><div class="cost-row"><span>ESTIMATE COVERAGE</span><b>${esc(ref.covered_shots||0)}/${esc(ref.total_shots||0)}</b></div><div class="cost-row"><span>ACTUAL</span><b>${esc(actual.credits||0)}</b></div><div class="cost-row"><span>RECONCILIATION</span><b>${actual.reconciliation_required?"REQUIRED":"CLEAR"}</b></div><div class="cost-row"><span>CEILING STATUS</span><b>${actual.ceiling_breach?"BREACH":"WITHIN LIMIT"}</b></div><div class="cost-row"><span>APPROVED CEILING</span><b>${esc(s.project?.cost_approval?.max_credits)}</b></div>`;
  document.querySelector("#history").innerHTML=(s.history||[]).slice().reverse().slice(0,100).map(e=>`<div class="event"><time>${esc(e.timestamp)}</time><div><b>${esc(e.event)}</b><br>${esc(e.entity_id)} / ${esc(e.actor)}</div></div>`).join("")||'<div class="empty">변경 이력이 없습니다.</div>';
}

async function refresh(){try{const response=await fetch("/api/state",{cache:"no-store"});if(response.ok){current=await response.json();document.querySelector("#sync-state").textContent="SERVER SYNC";}}catch(_){document.querySelector("#sync-state").textContent="STATIC SNAPSHOT";}render();}
refresh(); setInterval(refresh,10000);
