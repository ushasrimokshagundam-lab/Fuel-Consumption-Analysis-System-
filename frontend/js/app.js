// Frontend for the Fuel Consumption Analysis System - talks to the Flask REST API.
const $=s=>document.querySelector(s),inr=n=>n==null?"–":"₹"+Math.round(n).toLocaleString("en-IN"),f1=n=>n==null?"–":(+n).toFixed(1),f2=n=>n==null?"–":(+n).toFixed(2);
const api=async(u,o)=>{const r=await fetch(u,o),j=await r.json().catch(()=>({}));if(!r.ok)throw new Error(j.error||r.statusText);return j};
const send=(u,m,b)=>api(u,{method:m,headers:{"Content-Type":"application/json"},body:b?JSON.stringify(b):undefined});
const col=["#5aa9e6","#f0b44c","#7fc8a9","#b39ddb","#f08a8a","#8fb8de"];
const N={full_tank:"Full-tank",approximate:"Approx.",baseline:"Baseline",invalid:"Invalid"},C={full_tank:"t-full",approximate:"t-approx",baseline:"t-base",invalid:"t-bad"};
const tag=s=>`<span class="tag ${C[s]}">${N[s]}</span>`;
const mlabel=m=>new Date(m+"-01").toLocaleString("en",{month:"short",year:"2-digit"});
let V=[],R=[],charts=[];

function mk(id,cfg){const css=getComputedStyle(document.documentElement);Chart.defaults.color=css.getPropertyValue("--mut");Chart.defaults.borderColor=css.getPropertyValue("--line");
 cfg.options=Object.assign({responsive:true,maintainAspectRatio:false},cfg.options||{});charts.push(new Chart($(id),cfg))}

async function render(){
 const inc=$("#incApprox").checked?1:0;
 try{let dash,rep;[V,R,dash,rep]=await Promise.all([api("/api/vehicles"),api("/api/records"),api("/api/dashboard?include_approx="+inc),api("/api/reports?include_approx="+inc)]);
  drawDash(dash);drawVeh();drawRec();drawRep(rep);await drawHist()}
 catch(e){alert("Backend error: "+e.message)}}

function drawDash(d){const k=d.kpis;
 $("#kpis").innerHTML=[["Fleet avg mileage",f1(k.fleet_mileage)+" km/L"],["Total fuel spend",inr(k.total_spend)],["Avg cost per km","₹"+f2(k.cost_per_km)],["Most efficient",k.best_vehicle?k.best_vehicle+" · "+f1(k.best_mileage):"–"],["Records",k.records+" ("+k.invalid+" invalid)"]].map(x=>`<div class="card kpi"><span>${x[0]}</span><b>${x[1]}</b></div>`).join("");
 charts.forEach(c=>c.destroy());charts=[];const codes=Object.keys(d.monthly_cost),lab=d.months.map(mlabel);
 mk("#c1",{type:"bar",data:{labels:d.by_vehicle.map(x=>x.code),datasets:[{data:d.by_vehicle.map(x=>x.mileage),backgroundColor:col}]},options:{plugins:{legend:{display:false}}}});
 mk("#c2",{type:"line",data:{labels:lab,datasets:codes.map((c,i)=>({label:c,borderColor:col[i%6],backgroundColor:col[i%6],tension:.3,spanGaps:true,data:d.monthly_mileage[c]}))},options:{scales:{y:{type:"logarithmic"}}}});
 mk("#c3",{type:"bar",data:{labels:lab,datasets:codes.map((c,i)=>({label:c,backgroundColor:col[i%6],data:d.monthly_cost[c]}))},options:{scales:{x:{stacked:true},y:{stacked:true}}}});
 mk("#c4",{type:"bar",data:{labels:d.by_vehicle.map(x=>x.code),datasets:[{data:d.by_vehicle.map(x=>x.cpk),backgroundColor:col.slice().reverse()}]},options:{indexAxis:"y",plugins:{legend:{display:false}}}})}

function drawVeh(){
 $("#vt").innerHTML="<tr><th>ID</th><th>Code</th><th>Type</th><th>Fuel</th><th>Records</th><th></th></tr>"+V.map(v=>`<tr><td>${v.vehicle_id}</td><td><b>${v.vehicle_code}</b></td><td>${v.vehicle_type}</td><td>${v.fuel_type}</td><td>${v.record_count}</td><td><button class="btn s" data-dv="${v.vehicle_id}">Delete</button></td></tr>`).join("")}

function drawRec(){
 const cv=$("#rv").value,cf=$("#rfil").value,opts=V.map(v=>`<option value="${v.vehicle_id}">${v.vehicle_code}</option>`).join("");
 $("#rv").innerHTML=opts;$("#rv").value=V.some(v=>v.vehicle_id==cv)?cv:(V[0]?V[0].vehicle_id:"");
 $("#rfil").innerHTML='<option value="0">All vehicles</option>'+opts;$("#rfil").value=cf||"0";
 const fil=+$("#rfil").value;
 $("#rt").innerHTML="<tr><th>Date</th><th>Vehicle</th><th>Odometer</th><th>Litres</th><th>Cost</th><th>Tank</th><th>Distance</th><th>km/L</th><th>₹/km</th><th>Method</th><th></th></tr>"+R.filter(r=>!fil||r.vehicle_id==fil).map(r=>`<tr><td>${r.fill_date}</td><td>${r.vehicle_code}</td><td>${r.odometer_km}</td><td>${r.litres}</td><td>${r.total_cost}</td><td>${r.full_tank_flag?"Full":"Partial"}</td><td>${r.distance_km??"–"}</td><td>${f1(r.mileage_kmpl)}</td><td>${f2(r.cost_per_km)}</td><td>${tag(r.status)}</td><td><button class="btn s" data-dr="${r.record_id}">✕</button></td></tr>`).join("")}

function drawRep(p){
 $("#r1").innerHTML="<tr><th>Rank</th><th>Vehicle</th><th>Fuel</th><th>Full-tank km/L</th><th>₹/km</th><th>Distance</th><th>Approx. km/L</th><th>Intervals (full / approx)</th></tr>"+p.mileage.map(x=>`<tr><td>${x.rank||"–"}</td><td><b>${x.vehicle_code}</b></td><td>${x.fuel_type}</td><td>${f2(x.mileage_kmpl)}</td><td>${f2(x.cost_per_km)}</td><td>${x.distance_km} km</td><td>${f2(x.approx_mileage_kmpl)} <span class="tag t-approx">est.</span></td><td>${x.intervals} / ${x.approx_intervals}</td></tr>`).join("");
 const e=p.expenses;
 $("#r2").innerHTML="<tr><th>Month</th>"+e.codes.map(c=>`<th>${c}</th>`).join("")+"<th>Total</th><th>Litres</th></tr>"+e.rows.map(r=>`<tr><td>${mlabel(r.month)}</td>`+e.codes.map(c=>`<td>${inr(r.costs[c])}</td>`).join("")+`<td><b>${inr(r.total_cost)}</b></td><td>${f1(r.total_litres)} L</td></tr>`).join("");
 $("#r3").innerHTML=p.invalid.length?"<tr><th>Record</th><th>Date</th><th>Vehicle</th><th>Odometer</th><th>Litres</th><th>Cost</th><th>Reason excluded</th></tr>"+p.invalid.map(r=>`<tr><td>#${r.record_id}</td><td>${r.fill_date}</td><td>${r.vehicle_code}</td><td>${r.odometer_km}</td><td>${r.litres}</td><td>${r.total_cost}</td><td><span class="tag t-bad">${r.reason}</span></td></tr>`).join(""):"<tr><td>No invalid readings 🎉</td></tr>"}

async function drawHist(){
 const pa=$("#pa");if(!V.length){pa.innerHTML="<p>No vehicles yet.</p>";return}
 const hv=$("#hv"),pv=hv.value;hv.innerHTML=V.map(v=>`<option value="${v.vehicle_id}">${v.vehicle_code} · ${v.vehicle_type}</option>`).join("");hv.value=V.some(v=>v.vehicle_id==pv)?pv:V[0].vehicle_id;
 const rs=R.filter(r=>r.vehicle_id==hv.value).sort((a,b)=>a.fill_date.localeCompare(b.fill_date)||a.record_id-b.record_id);
 const hr=$("#hr"),pr=hr.value;hr.innerHTML='<option value="0">Full history (all records)</option>'+rs.map(r=>`<option value="${r.record_id}">${r.fill_date} · ${r.odometer_km} km · ${r.litres} L</option>`).join("");hr.value=rs.some(r=>r.record_id==pr)?pr:"0";
 const h=await api(`/api/history/${hv.value}?record_id=${hr.value}`),v=h.vehicle,s=h.summary;
 const kv=a=>'<div class="kv">'+a.map(k=>`<div><span>${k[0]}</span><b>${k[1]}</b></div>`).join("")+'</div>';
 let o=`<h2>${h.selected?"Fuel record details":"Vehicle history report"} – ${v.vehicle_code}</h2><p class="sub">${v.vehicle_type} · ${v.fuel_type} · Generated ${new Date().toLocaleDateString("en-IN")}</p>`;
 if(h.selected&&h.records[0]){const r=h.records[0];o+=kv([["Date",r.fill_date],["Odometer",r.odometer_km+" km"],["Litres",r.litres],["Total cost","₹"+r.total_cost],["Price per litre",r.litres>0?"₹"+f2(r.total_cost/r.litres):"–"],["Tank",r.full_tank_flag?"Full":"Partial"],["Distance",r.distance_km==null?"–":r.distance_km+" km"],["Mileage",r.mileage_kmpl==null?"–":f1(r.mileage_kmpl)+" km/L"],["Cost per km",r.cost_per_km==null?"–":"₹"+f2(r.cost_per_km)],["Method",N[r.status]]]);if(r.reason)o+=`<p><span class="tag t-bad">${r.reason}</span></p>`}
 else if(s)o+=kv([["Fill-ups",s.fills],["Total litres",f1(s.litres)+" L"],["Total spend",inr(s.spend)],["Odometer span",s.span==null?"–":s.span+" km"],["Avg mileage (full-tank)",f2(s.mileage)+" km/L"],["Cost per km",s.cpk?"₹"+f2(s.cpk):"–"],["Invalid readings",s.invalid]]);
 o+='<div class="scroll"><table><tr><th>Date</th><th>Odometer</th><th>Litres</th><th>Cost</th><th>Tank</th><th>Distance</th><th>km/L</th><th>₹/km</th><th>Method</th></tr>'+h.records.map(r=>`<tr><td>${r.fill_date}</td><td>${r.odometer_km}</td><td>${r.litres}</td><td>${r.total_cost}</td><td>${r.full_tank_flag?"Full":"Partial"}</td><td>${r.distance_km??"–"}</td><td>${f1(r.mileage_kmpl)}</td><td>${f2(r.cost_per_km)}</td><td>${tag(r.status)}</td></tr>`).join("")+'</table></div>';
 if(!h.selected)o+='<p class="sub" style="margin-top:10px;font-size:13px">Full-tank mileage uses distance between consecutive full fills ÷ litres in that interval. Approximate values are estimates from partial fills.</p>';
 pa.innerHTML=o}

document.querySelectorAll("aside button[data-v]").forEach(b=>b.onclick=()=>{document.querySelectorAll("aside button,section").forEach(e=>e.classList.remove("on"));b.classList.add("on");$("#"+b.dataset.v).classList.add("on");render()});
$("#incApprox").onchange=render;$("#rfil").onchange=drawRec;
$("#hv").onchange=()=>{$("#hr").innerHTML="";drawHist()};$("#hr").onchange=drawHist;$("#pb").onclick=()=>window.print();
$("#vf").onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target);try{await send("/api/vehicles","POST",{vehicle_code:f.get("code"),vehicle_type:f.get("type"),fuel_type:f.get("fuel")});e.target.reset();render()}catch(x){alert(x.message)}};
$("#rf").onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target);try{await send("/api/records","POST",{vehicle_id:+f.get("v"),fill_date:f.get("d"),odometer_km:+f.get("o"),litres:+f.get("l"),total_cost:+f.get("c"),full_tank_flag:+f.get("f")});render()}catch(x){alert(x.message)}};
$("#reset").onclick=async()=>{if(confirm("Replace all data with the sample data?")){await send("/api/reset-sample","POST");render()}};
document.addEventListener("click",async e=>{const d=e.target.dataset;try{if(d.dr){await send("/api/records/"+d.dr,"DELETE");render()}if(d.dv&&confirm("Delete this vehicle and all its records?")){await send("/api/vehicles/"+d.dv,"DELETE");render()}}catch(x){alert(x.message)}});
render();
