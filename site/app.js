const OFFICIAL = 'https://mptmd.sede.gob.es/pagina?id=Extranjeria-cita-previa-extranjeria';
const pathParts = location.pathname.split('/').filter(Boolean);
const repo = pathParts[0] || '';
const owner = location.hostname.endsWith('.github.io') ? location.hostname.split('.')[0] : '';
const repository = owner && repo ? `${owner}/${repo}` : '';
const storageKey = 'cita-clara-vault-v1';
let directory;
let vaultKey;
let records=[];
const $=id=>document.getElementById(id);
function procedureFor(raw){let s=String(raw||'').trim();if(!s)return null;if(/^cita previa para tramitar cartas? de invitaci[oó]n\s*:/i.test(s))return 'Cartas de Invitación';if(/^solicitud(?:es)? de asilo y refugio|^solicitud de asilo/i.test(s))return 'POLICÍA-SOLICITUD DE ASILO';if(/expedici[oó]n de tie|toma de huellas/i.test(s))return 'POLICÍA-TOMA DE HUELLAS (EXPEDICIÓN DE TARJETA) INICIAL, RENOVACIÓN, DUPLICADO Y LEY 14/2013';if(/pr[oó]rrogas? de estancia/i.test(s))return 'POLICÍA-PRÓRROGA DE ESTANCIA';if(/https?:\/\/|www\.|\S+@|\d{7,}|^horario|^lunes/i.test(s))return null;return s}
async function derive(pass,salt){const material=await crypto.subtle.importKey('raw',new TextEncoder().encode(pass),'PBKDF2',false,['deriveKey']);return crypto.subtle.deriveKey({name:'PBKDF2',salt,iterations:250000,hash:'SHA-256'},material,{name:'AES-GCM',length:256},false,['encrypt','decrypt'])}
const b64=b=>btoa(String.fromCharCode(...new Uint8Array(b)));const un64=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function saveVault(nextRecords=records){const existing=JSON.parse(localStorage.getItem(storageKey)||'{}');const iv=crypto.getRandomValues(new Uint8Array(12));const encrypted=await crypto.subtle.encrypt({name:'AES-GCM',iv},vaultKey,new TextEncoder().encode(JSON.stringify(nextRecords)));localStorage.setItem(storageKey,JSON.stringify({salt:existing.salt||window.ccSalt,iv:b64(iv),data:b64(encrypted)}))}
function openIssue(r){if(!repository){return ''}const clean={province:r.province,city:r.city,office:r.officeId==='*'?'Cualquier oficina':r.office,office_id:r.officeId,procedure:r.procedure,from:r.from,to:r.to,frequency_minutes:10};const body=`Solicitud de prueba Cita Clara. No incluyas datos personales.\n\n<!-- CITA-CLARA-REQUEST -->\n${JSON.stringify(clean,null,2)}\n<!-- FIN CITA-CLARA-REQUEST -->`;const title=`Búsqueda: ${r.city} · ${r.procedure}`;return `https://github.com/${repository}/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}&labels=busqueda-cita`}
function render(){
  const root=$('history');
  if(!records.length){root.innerHTML='<p class="muted">No hay solicitudes guardadas.</p>';return}
  root.innerHTML=records.map(r=>{
    const name=r.clientName||r.client||'Sin referencia';
    const maskedDocument=r.documentNumber?'••••'+r.documentNumber.slice(-4):'';
    const documentLabel={passport:'Pasaporte',identity:'Documento de identidad'}[r.documentType]||r.documentType;
    const details=[documentLabel,maskedDocument,r.phone,r.email].filter(Boolean).join(' · ');
    const url=openIssue(r);
    return `<div class="history-item"><strong>${esc(name)} · ${esc(r.procedure)}</strong><small>${esc(r.city)}, ${esc(r.province)} · ${esc(r.office)}</small>${details?`<small>Datos privados: ${esc(details)}</small>`:''}<small>${esc(r.from||'Sin fecha inicial')} → ${esc(r.to||'Sin fecha límite')}</small><span class="state">Guardada cifrada en este navegador</span><p>${url?`<a href="${esc(url)}" target="_blank" rel="noopener">Preparar criterios de búsqueda en GitHub ↗</a>`:'La publicación en GitHub requiere abrir el sitio desde GitHub Pages.'}</p><button class="secondary small" type="button" data-delete="${esc(r.id)}">Eliminar del historial local</button></div>`
  }).join('')
}
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function fillProvinces(){directory.provinces.forEach(p=>$('province').add(new Option(p.name,p.name)))}
function fillCities(){const p=directory?.provinces.find(x=>x.name===$('province').value);$('city').innerHTML='<option value="">Selecciona una localidad</option>';[...new Set((p?.offices||[]).map(o=>o.city))].sort((a,b)=>a.localeCompare(b,'es')).forEach(x=>$('city').add(new Option(x,x)));if(p&&p.offices.length){$('city').add(new Option('Cualquier localidad','*'),1);$('city').value='*';}$('city').disabled=!p;$('office').innerHTML='<option value="">Selecciona una oficina</option>';$('office').disabled=true;$('procedure').innerHTML='<option value="">Selecciona un trámite</option>';$('procedure').disabled=true;if(p)fillOffices()}
function fillOffices(){const p=directory.provinces.find(x=>x.name===$('province').value);const offices=(p?.offices||[]).filter(o=>$('city').value==='*'||o.city===$('city').value);$('office').innerHTML='<option value="">Selecciona una oficina</option>';if(offices.length)$('office').add(new Option(`Cualquier oficina (${offices.length})`,'*'));offices.forEach(o=>$('office').add(new Option(o.name,o.id)));$('office').disabled=!offices.length;if(offices.length)$('office').value='*';fillProcedures()}
function selectedOffices(){const p=directory.provinces.find(x=>x.name===$('province').value);const offices=(p?.offices||[]).filter(o=>$('city').value==='*'||o.city===$('city').value);return $('office').value==='*'?offices:offices.filter(o=>o.id===$('office').value)}
function fillProcedures(){const set=new Set(selectedOffices().flatMap(o=>o.procedures.map(procedureFor).filter(Boolean)));$('procedure').innerHTML='<option value="">Selecciona un trámite</option>';[...set].sort((a,b)=>a.localeCompare(b,'es')).forEach(s=>$('procedure').add(new Option(s,s)));$('procedure').disabled=!set.size}
async function setup(){const raw=localStorage.getItem(storageKey);const pass=$('passphrase').value;if(pass.length<10){alert('Usa una clave de al menos 10 caracteres.');return}try{if(raw){const v=JSON.parse(raw);window.ccSalt=v.salt;vaultKey=await derive(pass,un64(v.salt));records=JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({name:'AES-GCM',iv:un64(v.iv)},vaultKey,un64(v.data))))}else{window.ccSalt=b64(crypto.getRandomValues(new Uint8Array(16)));vaultKey=await derive(pass,un64(window.ccSalt));records=[];await saveVault()}$('welcome').hidden=true;$('workspace').hidden=false;render()}catch{alert('No se pudo abrir el espacio. Comprueba la clave. Los datos cifrados no se han modificado.')}}
$('unlock').addEventListener('click',setup);$('passphrase').addEventListener('keydown',e=>{if(e.key==='Enter')setup()});$('lock').addEventListener('click',()=>{vaultKey=null;records=[];$('history').replaceChildren();$('result').replaceChildren();$('result').hidden=true;$('request-form').reset();fillCities();$('workspace').hidden=true;$('welcome').hidden=false;$('passphrase').value=''});
$('province').addEventListener('change',fillCities);$('city').addEventListener('change',fillOffices);$('office').addEventListener('change',fillProcedures);
$('request-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const result=$('result');
  const submit=e.currentTarget.querySelector('button[type="submit"]');
  const showError=message=>{result.hidden=false;result.textContent=message};
  if(!vaultKey){showError('Abre el espacio local antes de guardar.');return}
  const from=$('from').value,to=$('to').value;
  if(from&&to&&from>to){showError('La fecha final debe ser igual o posterior a la fecha inicial.');return}
  const office=$('office').value;
  const p=directory?.provinces.find(x=>x.name===$('province').value);
  const offices=(p?.offices||[]).filter(o=>$('city').value==='*'||o.city===$('city').value);
  const selected=office==='*'?offices:offices.filter(o=>o.id===office);
  if(!selected.length||!$('procedure').value){showError('Selecciona una provincia, localidad, oficina y trámite disponibles.');return}
  const clientName=$('client-name')?.value.trim()||'';
  const documentType=$('document-type')?.value||'';
  const documentNumber=$('document-number')?.value.trim()||'';
  const phone=$('client-phone')?.value.trim()||'';
  const email=$('client-email')?.value.trim()||'';
  const consent=$('client-consent');
  if(consent&&(!consent.checked||!clientName||!documentType||!documentNumber||!phone)){
    showError('Completa los datos obligatorios y confirma la autorización del cliente.');return
  }
  const r={id:crypto.randomUUID(),client:$('client').value.trim(),clientName,documentType,documentNumber,phone,email,consentAt:consent?new Date().toISOString():null,province:$('province').value,city:$('city').value==='*'?'Cualquier localidad':$('city').value,office:office==='*'?`Cualquier oficina (${offices.length})`:selected[0].name,officeId:office,procedure:$('procedure').value,from,to,created:new Date().toISOString(),issue:''};
  submit.disabled=true;$('lock').disabled=true;
  try{
    const nextRecords=[r,...records];
    await saveVault(nextRecords);
    records=nextRecords;render();result.hidden=false;
    result.textContent='Solicitud guardada y cifrada en este navegador. La búsqueda no se ha iniciado. Para preparar la prueba, abre el enlace del historial y publica solo los criterios de búsqueda en GitHub. Se requiere una integración del trámite verificada.';
    $('request-form').reset();fillCities()
  }catch{
    showError('No se pudo guardar la solicitud en este navegador. Los campos se conservan para que puedas volver a intentarlo.')
  }finally{submit.disabled=false;$('lock').disabled=false}
});
$('history').addEventListener('click',async e=>{
  const button=e.target.closest('button[data-delete]');
  if(!button||!vaultKey)return;
  const nextRecords=records.filter(r=>r.id!==button.dataset.delete);
  button.disabled=true;$('lock').disabled=true;
  try{await saveVault(nextRecords);records=nextRecords;render()}
  catch{$('result').hidden=false;$('result').textContent='No se pudo eliminar la solicitud. Vuelve a intentarlo.';button.disabled=false}
  finally{$('lock').disabled=false}
});
try{directory=await(await fetch('./oficinas-extranjeria.json')).json();$('directory-date').textContent=directory.retrieved_at;fillProvinces()}catch{$('directory-date').textContent='no disponible';}
