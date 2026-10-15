"use strict";
const STORE_KEY = "edupredict_academic_workspace_v1";
const $ = (id) => document.getElementById(id);
const fmt = (n, places = 2) => Number(n).toFixed(places);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const point = (percent) => percent >= 90 ? 10 : percent >= 80 ? 9 : percent >= 70 ? 8 : percent >= 60 ? 7 : percent >= 50 ? 6 : percent >= 40 ? 5 : 0;
const scorePct = (m) => m.max > 0 ? 100 * m.score / m.max : 0;
const uid = () => typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + "-" + String(Math.random()).slice(2);
const blank = () => ({ marks: [], attendance: [], assignments: [], goal: 9 });
function load() {
  try {
    const data = JSON.parse(localStorage.getItem(STORE_KEY) || "null");
    if (!data || typeof data !== "object") return blank();
    return {
      marks: Array.isArray(data.marks) ? data.marks.filter(m => Number.isFinite(+m.score) && Number.isFinite(+m.max) && +m.max > 0 && +m.score >= 0 && +m.score <= +m.max && +m.credits > 0 && +m.semester >= 1) : [],
      attendance: Array.isArray(data.attendance) ? data.attendance.filter(a => +a.total > 0 && +a.present >= 0 && +a.present <= +a.total) : [],
      assignments: Array.isArray(data.assignments) ? data.assignments.filter(a => !!a && typeof a.title === "string") : [],
      goal: Number.isFinite(+data.goal) && +data.goal >= 0 && +data.goal <= 10 ? +data.goal : 9
    };
  } catch (_error) { return blank(); }
}
let state = load();
function save() {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); }
  catch (_error) { notify("Storage is unavailable. Records may not remain after refresh."); }
  render();
}
let toastTimer;
function notify(message) {
  const toast = $("toast"); toast.textContent = message; toast.classList.add("show");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => toast.classList.remove("show"), 3100);
}
function weightedGpa(records) {
  const credits = records.reduce((sum, row) => sum + Number(row.credits), 0);
  return credits ? records.reduce((sum, row) => sum + Number(row.credits) * point(scorePct(row)), 0) / credits : null;
}
function latestSemester() {
  return state.marks.length ? Math.max(...state.marks.map(m => Number(m.semester))) : null;
}
function selectedMarks(semester) {
  return state.marks.filter(m => Number(m.semester) === semester);
}
function totalAttendance() {
  const attended = state.attendance.reduce((sum, a) => sum + Number(a.present), 0);
  const total = state.attendance.reduce((sum, a) => sum + Number(a.total), 0);
  return total ? 100 * attended / total : null;
}
function metric(id, value) { $(id).textContent = value; }
function progress(label, percent, trailing) {
  return `<div class="chart-row"><div class="chart-label"><span>${esc(label)}</span><strong>${esc(trailing)}</strong></div><div class="progress"><i style="width:${Math.max(0, Math.min(100, percent))}%"></i></div></div>`;
}
function insight(title, body) { return `<div class="insight"><b>${esc(title)}</b><div>${esc(body)}</div></div>`; }
function setPage(page) {
  for (const section of document.querySelectorAll("[data-screen]")) {
    section.classList.toggle("hidden", section.dataset.screen !== page);
  }
  for (const button of document.querySelectorAll("[data-page]")) {
    const current = button.dataset.page === page;
    button.classList.toggle("active", current);
    if (current) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  }
  try { history.replaceState(null, "", "/academic#" + page); } catch (_) {}
  window.scrollTo({top: 0, behavior: "smooth"});
}
document.querySelectorAll("[data-page]").forEach(btn => btn.addEventListener("click", () => setPage(btn.dataset.page)));
document.querySelectorAll("[data-jump]").forEach(btn => btn.addEventListener("click", () => setPage(btn.dataset.jump)));
function renderOverview() {
  const latest = latestSemester(), cgpa = weightedGpa(state.marks), sgpa = latest === null ? null : weightedGpa(selectedMarks(latest)), attendance = totalAttendance();
  metric("overview-cgpa", cgpa === null ? "—" : fmt(cgpa));
  metric("overview-sgpa", sgpa === null ? "—" : fmt(sgpa));
  metric("semester-label", latest === null ? "No marks entered yet" : "Semester " + latest);
  metric("overview-attendance", attendance === null ? "—" : fmt(attendance, 1) + "%");
  const done = state.assignments.filter(a => a.done).length;
  metric("overview-assignments", done + "/" + state.assignments.length);
  $("overview-subjects").innerHTML = latest === null ? "" : selectedMarks(latest)
    .sort((a,b) => String(a.subject).localeCompare(String(b.subject)))
    .map(m => progress(m.subject, scorePct(m), fmt(scorePct(m), 1) + "% · " + point(scorePct(m)) + " GP")).join("");
  const guidance = [];
  if (!state.marks.length) guidance.push(insight("Start with marks", "Enter a subject, marks and credits to see estimated SGPA and CGPA."));
  else {
    const low = state.marks.filter(m => scorePct(m) < 50).slice(0, 2);
    if (low.length) guidance.push(insight("Consider subject support", low.map(m => m.subject).join(", ") + " may benefit from more revision and faculty feedback."));
    if (sgpa !== null) guidance.push(insight("Most recent SGPA", "Semester " + latest + " currently estimates " + fmt(sgpa) + "/10 using the illustrative grade conversion."));
  }
  if (attendance === null) guidance.push(insight("Log attendance", "Track attended and total classes to see your current attendance percentage."));
  else if (attendance < 75) guidance.push(insight("Review attendance", "Recorded attendance is " + fmt(attendance, 1) + "%. Check your institution's own required threshold."));
  const pending = state.assignments.filter(a => !a.done).length;
  if (pending) guidance.push(insight("Coursework reminder", pending + " assignment" + (pending > 1 ? "s" : "") + " still pending."));
  if (!guidance.length) guidance.push(insight("You're up to date", "Your records are organized. Keep updating new marks and assignments."));
  $("overview-insights").innerHTML = guidance.join("");
}
function renderMarks() {
  metric("record-count", state.marks.length + " RECORDS");
  const rows = state.marks.slice().sort((a,b) => Number(b.semester) - Number(a.semester) || String(a.subject).localeCompare(String(b.subject)));
  $("marks-table").innerHTML = rows.map(m => `<tr><td>${esc(m.subject)}</td><td>${Number(m.semester)}</td><td>${Number(m.score)} / ${Number(m.max)}</td><td>${fmt(scorePct(m),1)}%</td><td>${point(scorePct(m))}</td><td>${Number(m.credits)}</td><td><button type="button" class="delete-btn" data-remove-mark="${esc(m.id)}" aria-label="Delete ${esc(m.subject)}">Remove</button></td></tr>`).join("");
  $("marks-empty").classList.toggle("hidden", rows.length !== 0);
}
function renderGrades() {
  const all = state.marks;
  metric("grade-cgpa", weightedGpa(all) === null ? "—" : fmt(weightedGpa(all)));
  metric("grade-credits", String(all.reduce((sum,m) => sum + Number(m.credits), 0)));
  const semesters = [...new Set(all.map(m => Number(m.semester)))].sort((a,b) => a-b);
  const select = $("focus-semester"), previous = select.value;
  select.innerHTML = '<option value="all">Latest</option>' + semesters.map(v => `<option value="${v}">Semester ${v}</option>`).join("");
  select.value = semesters.includes(Number(previous)) && previous !== "all" ? previous : "all";
  const focused = select.value === "all" ? latestSemester() : Number(select.value);
  const gp = focused === null ? null : weightedGpa(selectedMarks(focused));
  metric("grade-sgpa", gp === null ? "—" : fmt(gp));
  $("semester-chart").innerHTML = semesters.map(s => {
    const value = weightedGpa(selectedMarks(s)) ?? 0;
    return `<div class="semester-row"><span>Semester ${s}</span><div class="progress"><i style="width:${value*10}%"></i></div><strong>${fmt(value)}</strong></div>`;
  }).join("");
}
function renderAttendance() {
  const pct = totalAttendance();
  metric("attendance-total-value", pct === null ? "—" : fmt(pct, 1) + "%");
  $("attendance-progress").style.width = (pct ?? 0) + "%";
  $("attendance-table").innerHTML = state.attendance.slice().sort((a,b) => String(a.subject).localeCompare(String(b.subject))).map(a => `<tr><td>${esc(a.subject)}</td><td>${Number(a.present)}</td><td>${Number(a.total)}</td><td>${fmt(100*Number(a.present)/Number(a.total), 1)}%</td><td><button type="button" class="delete-btn" data-remove-attendance="${esc(a.id)}">Remove</button></td></tr>`).join("");
  $("attendance-empty").classList.toggle("hidden", state.attendance.length > 0);
}
function renderAssignments() {
  const done = state.assignments.filter(a => a.done).length;
  metric("assignment-progress", done + " / " + state.assignments.length + " COMPLETE");
  const today = new Date().toISOString().slice(0,10);
  const list = state.assignments.slice().sort((a,b) => Number(a.done)-Number(b.done) || String(a.due).localeCompare(String(b.due)));
  $("assignment-list").innerHTML = list.map(a => `<div class="task ${a.done?'done':''} ${String(a.due) < today && !a.done ? 'overdue' : ''}"><input type="checkbox" data-check-assignment="${esc(a.id)}" ${a.done?'checked':''} aria-label="Completed: ${esc(a.title)}"><div class="task-body"><strong>${esc(a.title)}</strong><small>${esc(a.subject)} · <span class="due">Due ${esc(a.due)}</span></small></div><button class="task-remove" data-remove-assignment="${esc(a.id)}" type="button">Remove</button></div>`).join("");
  $("assignment-empty").classList.toggle("hidden", list.length > 0);
}
function renderGoals() {
  $("goal-target").value = Number(state.goal);
  const latest = latestSemester(), sgpa = latest === null ? null : weightedGpa(selectedMarks(latest));
  $("goal-summary").innerHTML = '<span>YOUR SGPA TARGET</span><strong>' + fmt(state.goal,1) + ' / 10</strong><p>' + (sgpa === null ? 'Enter subject marks to compare your target.' : 'Latest SGPA: ' + fmt(sgpa) + ' · Gap: ' + fmt(Math.max(0, state.goal - sgpa)) + ' points.') + '</p>';
  const notes=[];
  if (sgpa === null) notes.push(insight("Get started", "Enter semester subject marks and credits to calculate your estimated academic performance."));
  else if (sgpa >= state.goal) notes.push(insight("Target reached", "Your entered results meet this estimated SGPA goal. Keep building on your progress."));
  else {
    notes.push(insight("Focus on your target", "Your target is " + fmt(state.goal - sgpa) + " points above the most recent estimated SGPA."));
    const weak = selectedMarks(latest).slice().sort((a,b) => scorePct(a) - scorePct(b)).slice(0,2);
    if(weak.length)notes.push(insight("Revision priorities", "Review " + weak.map(m=>m.subject).join(" and ") + " and discuss improvement opportunities with your faculty."));
  }
  $("goal-advice").innerHTML = notes.join("");
}
function render() {
  renderOverview(); renderMarks(); renderGrades(); renderAttendance(); renderAssignments(); renderGoals();
}
$("marks-form").addEventListener("submit", event => {
  event.preventDefault();
  const subject=$("subject-name").value.trim(), semester=Number($("subject-semester").value), credits=Number($("subject-credits").value), score=Number($("subject-score").value), max=Number($("subject-max").value);
  if (!subject || !Number.isInteger(semester) || semester<1 || semester>12 || !Number.isInteger(credits) || credits<1 || credits>12 || !Number.isFinite(score) || score<0 || !Number.isFinite(max) || max<=0 || max>1000 || score>max) return notify("Please enter valid marks, credits and semester.");
  const previous = state.marks.find(m => Number(m.semester)===semester && String(m.subject).toLowerCase()===subject.toLowerCase());
  if (previous) Object.assign(previous,{subject,semester,credits,score,max});
  else state.marks.push({id:uid(),subject,semester,credits,score,max});
  $("subject-name").value=""; save();notify("Subject result saved.");
});
$("marks-table").addEventListener("click", event => {
  const id=event.target.closest("[data-remove-mark]")?.dataset.removeMark;
  if(id){state.marks=state.marks.filter(m=>m.id!==id);save();notify("Subject removed.");}
});
$("attendance-form").addEventListener("submit", event => {
  event.preventDefault();
  const subject=$("attendance-subject").value.trim(),present=Number($("attendance-present").value),total=Number($("attendance-total").value);
  if (!subject || !Number.isInteger(present) || !Number.isInteger(total) || present<0 || total<1 || present>total || total>10000) return notify("Enter a valid attendance count.");
  const existing=state.attendance.find(a=>String(a.subject).toLowerCase()===subject.toLowerCase());
  if(existing)Object.assign(existing,{subject,present,total});else state.attendance.push({id:uid(),subject,present,total});
  $("attendance-subject").value="";save();notify("Attendance saved.");
});
$("attendance-table").addEventListener("click", event => {
  const id=event.target.closest("[data-remove-attendance]")?.dataset.removeAttendance;
  if(id){state.attendance=state.attendance.filter(a=>a.id!==id);save();notify("Attendance removed.");}
});
$("assignment-form").addEventListener("submit",event=>{
  event.preventDefault();
  const title=$("assignment-title").value.trim(),subject=$("assignment-subject").value.trim(),due=$("assignment-due").value;
  if(!title||!subject||!/\d{4}-\d{2}-\d{2}/.test(due))return notify("Enter a title, subject and due date.");
  state.assignments.push({id:uid(),title,subject,due,done:false});$("assignment-title").value="";save();notify("Assignment added.");
});
$("assignment-list").addEventListener("click",event=>{
  const id=event.target.closest("[data-remove-assignment]")?.dataset.removeAssignment;
  if(id){state.assignments=state.assignments.filter(a=>a.id!==id);save();notify("Assignment removed.");}
});
$("assignment-list").addEventListener("change",event=>{
  const id=event.target.dataset.checkAssignment;
  if(id){const item=state.assignments.find(a=>a.id===id);if(item){item.done=event.target.checked;save();}}
});
$("goal-form").addEventListener("submit",event=>{
  event.preventDefault();const v=Number($("goal-target").value);
  if(!Number.isFinite(v)||v<0||v>10)return notify("Enter a target between 0 and 10.");
  state.goal=v;save();notify("Academic target saved.");
});
$("focus-semester").addEventListener("change",renderGrades);
$("demo-button").addEventListener("click",()=>{
  if((state.marks.length||state.assignments.length||state.attendance.length)&&!window.confirm("Replace your browser's current academic records with demo data?"))return;
  state={
    marks:[
      {subject:"Data Structures",semester:4,score:82,max:100,credits:4},
      {subject:"Database Systems",semester:4,score:91,max:100,credits:3},
      {subject:"Web Technology",semester:4,score:76,max:100,credits:3},
      {subject:"Design & Analysis of Algorithms",semester:5,score:86,max:100,credits:4},
      {subject:"Machine Learning",semester:5,score:93,max:100,credits:4},
      {subject:"Operating Systems",semester:5,score:71,max:100,credits:3}
    ].map(m=>({id:uid(),...m})),
    attendance:[{id:uid(),subject:"Machine Learning",present:37,total:44},{id:uid(),subject:"Operating Systems",present:29,total:42}],
    assignments:[{id:uid(),title:"ML Model Presentation",subject:"Machine Learning",due:"2026-10-24",done:false},{id:uid(),title:"DAA Lab",subject:"Algorithms",due:"2026-10-17",done:true}],
    goal:9
  };save();notify("Demo data loaded.");
});
$("export-button").addEventListener("click",()=>{
  const lines=[["subject","semester","score","maximum","credits","percentage","grade_point"].join(",")];
  const quote=(val)=>'"'+String(val).replace(/"/g,'""')+'"';
  for (const m of state.marks)lines.push([quote(m.subject),m.semester,m.score,m.max,m.credits,fmt(scorePct(m),1),point(scorePct(m))].join(","));
  const file=new Blob([lines.join("\r\n")+"\r\n"],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(file),a=document.createElement("a");a.href=url;a.download="edupredict_subject_marks.csv";document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  notify("Marks CSV downloaded.");
});
const hash=location.hash.replace("#","");
setPage(["overview","marks","grades","attendance","assignments","goals"].includes(hash)?hash:"overview");
render();
