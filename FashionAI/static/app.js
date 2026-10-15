
const form=document.getElementById('searchForm');
const grid=document.getElementById('grid');
const status=document.getElementById('status');
const btn=document.getElementById('submit');
document.getElementById('image').addEventListener('change',e=>{document.getElementById('filename').textContent=e.target.files[0]?.name||'No file selected'});
document.querySelectorAll('[data-preset]').forEach(el=>el.addEventListener('click',e=>{e.preventDefault();document.getElementById('description').value=el.dataset.preset;form.requestSubmit()}));
function draw(items){grid.replaceChildren();for(const p of items){
 const card=document.createElement('article');card.className='product';
 const img=document.createElement('img');img.src=p.image;img.alt='Illustration of '+p.name;img.loading='lazy';
 const body=document.createElement('div');body.className='details';
 const category=document.createElement('div');category.className='category';category.textContent=p.category;
 const title=document.createElement('h3');title.textContent=p.name;
 const sub=document.createElement('p');sub.textContent=p.color+' · '+p.gender+' · '+p.style;
 const match=document.createElement('div');match.className='match';match.textContent=p.score===undefined?'DISCOVER THIS STYLE':'Similarity score: '+p.score;
 body.append(category,title,sub,match);card.append(img,body);grid.append(card);
}}
fetch('/api/products').then(r=>r.json()).then(items=>draw(items)).catch(()=>{status.textContent='Unable to load collection'});
form.addEventListener('submit',async e=>{e.preventDefault();btn.disabled=true;status.textContent='Searching the collection…';
try{const r=await fetch('/api/recommend',{method:'POST',body:new FormData(form)});const data=await r.json();if(!r.ok)throw Error(data.error||'Unable to search');draw(data.results);status.textContent=data.count+' style recommendations';}
catch(err){status.textContent=err.message;}finally{btn.disabled=false;}});
