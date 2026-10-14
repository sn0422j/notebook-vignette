(() => {
 const details=[...document.querySelectorAll('.code-cell details.code-details')];
 const toggle=document.getElementById('toggle-code');
 const sync=()=>{if(toggle)toggle.textContent=details.every(x=>x.open)?'コードを折りたたむ':'コードをすべて開く'};
 if(toggle)toggle.addEventListener('click',()=>{const open=!details.every(x=>x.open);details.forEach(x=>x.open=open);sync()});
 details.forEach(x=>x.addEventListener('toggle',sync));sync();
 document.querySelectorAll('.copy-button').forEach(button=>button.addEventListener('click',async event=>{
  event.preventDefault();event.stopPropagation();
  const pre=button.parentElement.querySelector('pre');if(!pre)return;
  try{
   if(!navigator.clipboard)throw new Error('clipboard unavailable');
   await navigator.clipboard.writeText(pre.textContent);button.textContent='コピー済み';
  }catch{
   const area=document.createElement('textarea');area.value=pre.textContent;
   area.style.cssText='position:fixed;opacity:0';document.body.appendChild(area);area.select();
   let copied=false;try{copied=document.execCommand('copy')}finally{area.remove()}
   if(copied){button.textContent='コピー済み'}else{
    const range=document.createRange();range.selectNodeContents(pre);
    const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);
    button.textContent='選択済み';
   }
  }
  setTimeout(()=>button.textContent='コピー',1800);
 }));
 if('IntersectionObserver' in window){
  const observer=new IntersectionObserver(entries=>{
   for(const entry of entries){if(entry.isIntersecting){
    document.querySelectorAll('nav a').forEach(a=>a.classList.toggle('active',decodeURIComponent(a.hash.slice(1))===entry.target.id));
   }}
  },{rootMargin:'-10% 0px -70% 0px'});
  document.querySelectorAll('[data-toc-heading]').forEach(x=>observer.observe(x));
 }
 let beforePrint=[];
 window.addEventListener('beforeprint',()=>{beforePrint=details.map(x=>x.open);details.forEach(x=>x.open=true)});
 window.addEventListener('afterprint',()=>{details.forEach((x,i)=>x.open=beforePrint[i]??x.open)});
})();
