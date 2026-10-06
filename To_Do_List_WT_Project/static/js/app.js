function openAdd(){document.getElementById("addModal").classList.add("show")}
function closeAdd(){document.getElementById("addModal").classList.remove("show")}
function openEdit(id){document.getElementById("edit-"+id).classList.add("show")}
function closeEdit(id){document.getElementById("edit-"+id).classList.remove("show")}
document.getElementById("menuBtn")?.addEventListener("click",()=>document.getElementById("sidebar")?.classList.toggle("open"));
document.addEventListener("click",e=>{if(e.target.classList.contains("modal"))e.target.classList.remove("show")});
setTimeout(()=>document.querySelectorAll(".flash").forEach(x=>x.remove()),4500);

if(window.Chart&&window.CHART_DATA){
  Chart.defaults.color="#8fa9a0";
  Chart.defaults.font.family="Inter";
  Chart.defaults.borderColor="rgba(255,255,255,.05)";
  const c1=document.getElementById("categoryChart");
  if(c1)new Chart(c1,{type:"doughnut",data:{labels:CHART_DATA.categories,datasets:[{data:CHART_DATA.categoryValues,backgroundColor:["#42e6a4","#72d8ff","#f5c86a","#9d8cff","#ff6f7f","#9ab9ad"],borderWidth:0,hoverOffset:7}]},options:{responsive:true,maintainAspectRatio:false,cutout:"68%",plugins:{legend:{position:"bottom",labels:{usePointStyle:true,boxWidth:8,padding:16}}}}});
  const c2=document.getElementById("priorityChart");
  if(c2)new Chart(c2,{type:"bar",data:{labels:CHART_DATA.priorities,datasets:[{data:CHART_DATA.priorityValues,backgroundColor:["#ff6f7f","#f5c86a","#72d8ff"],borderRadius:8}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false}},y:{beginAtZero:true,ticks:{precision:0}}}}});
}