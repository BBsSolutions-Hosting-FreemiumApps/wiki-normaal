/* Elohim YHWH Studiebijbel · Wiki (statisch voorbeeld). Werkt ook via file:// (geen fetch nodig). */
(function(){
'use strict';
var SBW=window.SBW={meta:null,books:{},ents:{},_wait:{}};
var app=document.getElementById('app'),panel=document.getElementById('panel'),pbody=document.getElementById('panelBody'),tip=document.getElementById('tip');
var TYPES={P:['persoon','Personen'],V:['volk','Volken en stammen'],S:['stad','Steden'],L:['land','Landen'],W:['water','Rivieren, meren en zeeën'],R:['regio','Bergen, woestijnen en regio’s'],O:['plaats','Overige plaatsen'],U:['onbepaald','Soort onzeker']};
var CERT={z:['zeker','Soort volgt uit de legendakleur of een koningsprofiel in de studiebijbel'],w:['waarschijnlijk','Soort volgt uit de zinnen in de tekst (bijv. “zoon van”, “het land”) of een naamlijst'],o:['onzeker','Weinig aanwijzingen; controleer de verzen']};
var CODES={'[E]':'Elohim spreekt','[EE]':'De Engel van Elohim spreekt','[Y]':'YHWH spreekt','[EY]':'De Engel van YHWH spreekt','[YW]':'Wetten door YHWH zelf uitgesproken en opgelegd','[YP]':'Wetten van YHWH, opgelegd aan de priesters','[YL]':'Wetten van YHWH, opgelegd aan de Levieten','[MW]':'Wetten door Mozes aan het volk doorgegeven','[§]':'Verbond','{§}':'Wet(ten)','[#]':'Commentaar','[C]':'Contradictie tussen verzen','[?]':'Open vraag','[##]':'Open vraag','[!]':'Opmerkelijkheid','[###]':'Opmerkelijkheid','[X]':'Correctie doorgevoerd','{#}':'Seizoensaanduiding','[=]':'Dubbele tekst, volledig gelijk','[-]':'Dubbele tekst, ongelijk','[‘=’]':'Dubbele tekst, gelijkgemaakt','[+]':'Dubbele tekst met extra aanvulling','[{=}]':'Evangeliën: volledig gelijke tekst','[{-}]':'Evangeliën: ongelijke tekst','[[2]]':'Tweedubbel vers','[[3]]':'Driedubbel vers','{1x}':'Komt 1x voor'};
var CODERX=/\[‘=’\]|\[\{[=\-]\}\]|\[\[[23]\]\]|\[(?:EE|EY|E|Y|YW|YP|YL|MW|§|#{1,3}|C|\?|!|X|=|-|\+)\]|\{[§#]\}|\{1x\}/g;
var colors=localStorage.getItem('sbw-kleur')!=='uit';

function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function load(src){
  if(SBW._wait[src]) return SBW._wait[src];
  return SBW._wait[src]=new Promise(function(res,rej){var s=document.createElement('script');s.src=src;s.onload=res;s.onerror=function(){rej(new Error('Kon '+src+' niet laden'));};document.head.appendChild(s);});
}
SBW.gotMeta=function(m){SBW.meta=m;};
SBW.gotBook=function(i,d){SBW.books[i]=d;};
SBW.gotEnts=function(d){for(var k in d) SBW.ents[k]=d[k];};
function book(i){return SBW.books[i]?Promise.resolve(SBW.books[i]):load('data/b/'+i+'.js').then(function(){return SBW.books[i];});}
function ent(id){var m=SBW.meta; if(SBW.ents[id]) return Promise.resolve(SBW.ents[id]); return load('data/e'+(id%m.nch)+'.js').then(function(){return SBW.ents[id];});}
function norm(s){return s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[-'’·ʼ`‘ ]/g,'').toLowerCase();}

/* ---------- verwijzingen ---------- */
var BOOKRX=null;
function refRx(){
  if(BOOKRX) return BOOKRX;
  var names=SBW.meta.books.map(function(b){return b[0];}).sort(function(a,b){return b.length-a.length;}).map(function(n){return n.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');});
  BOOKRX=new RegExp('('+names.join('|')+') (\\d+):(\\d+)','g'); return BOOKRX;
}
function findBlock(bn,c,v){
  var bi=-1,M=SBW.meta; M.books.forEach(function(b,i){if(b[0]===bn) bi=i;});
  if(bi<0) return null;
  var best=null;
  for(var i=0;i<M.blk.length;i++){var b=M.blk[i]; if(b[0]!==bi||b[1]!==c) continue;
    var m=/:(\d+)(?:-(\d+))?$/.exec(b[2]); if(!m) continue; var a=+m[1],z=m[2]?+m[2]:a;
    if(v>=a&&v<=z) return i; if(a<=v&&(best===null)) best=i;}
  return best!==null?best:(function(){for(var i=0;i<M.blk.length;i++){if(M.blk[i][0]===bi&&M.blk[i][1]===c) return i;}return null;})();
}
function blockHref(id){var b=SBW.meta.blk[id]; return '#/lees/'+b[0]+'/'+b[1]+'/'+id;}
function refHref(label){var m=/^(.*) (\d+):(\d+)/.exec(label); if(!m) return null; var id=findBlock(m[1],+m[2],+m[3]); return id===null?null:blockHref(id);}
function decorate(s){ // HTML-escaped tekst met codes en verwijzingen
  var h=esc(s);
  h=h.replace(CODERX,function(c){var t=CODES[c.replace('&amp;','&')]; return t?'<span class="code" data-tip="'+esc(t)+'">'+c+'</span>':c;});
  h=h.replace(refRx(),function(all,b,c,v){var href=refHref(b+' '+c+':'+v); return href?'<a class="ref" href="'+href+'">'+all+'</a>':all;});
  return h;
}

/* ---------- lezen ---------- */
function renderRead(bi,c,focus){
  var M=SBW.meta;
  if(bi===undefined||isNaN(bi)){bi=0;}
  if(!M.books[bi]||!M.books[bi][1].length){bi=M.books.findIndex(function(b){return b[1].length;});}
  var chs=M.books[bi][1]; if(!c||chs.indexOf(c)<0) c=chs[0];
  app.innerHTML='<p class="loading">Hoofdstuk wordt geladen…</p>';
  book(bi).then(function(B){
    var opts=M.books.map(function(b,i){return '<option value="'+i+'"'+(i===bi?' selected':'')+(b[1].length?'':' disabled')+'>'+esc(b[0])+'</option>';}).join('');
    var copts=chs.map(function(x){return '<option'+(x===c?' selected':'')+'>'+x+'</option>';}).join('');
    var h='<div class="bar"><select id="selB" aria-label="Boek">'+opts+'</select><select id="selC" aria-label="Hoofdstuk">'+copts+'</select>'+
      '<button id="kleur" class="'+(colors?'on':'')+'" title="Kleuren uit de studiebijbel aan of uit">Kleuren</button></div>';
    h+='<h1>'+esc(M.books[bi][0])+' '+c+'</h1>';
    var ids=B.ch[c]||[];
    h+='<div class="txt'+(colors?'':' plain')+'">';
    ids.forEach(function(id){
      var bl=B.bl[id];
      if(bl.h) h+='<div class="head">'+esc(bl.h)+'</div>';
      if(bl.s) h+='<div class="sub">'+decorate(bl.s)+'</div>';
      h+='<div class="blk" id="b'+id+'"><a class="lab" href="'+blockHref(id)+'">'+esc(bl.l)+'</a>'+(bl.m?'<span class="marks">'+decorate(bl.m)+'</span>':'');
      bl.x.forEach(function(line){
        if(!line){h+='<div class="gap"></div>';return;}
        var tabs=0; if(line.length&&typeof line[0][0]==='string'){var m=/^\t+/.exec(line[0][0]); if(m) tabs=Math.min(3,m[0].length);}
        h+='<p class="ln t'+tabs+'">';
        line.forEach(function(seg,si){
          var t=seg[0]; if(si===0) t=t.replace(/^\t+/,'');
          var st=M.sty[seg[1]]||'';
          if(seg.length>2) h+='<span class="x ent" tabindex="0" role="button" data-e="'+seg[2]+'" style="'+st+'">'+esc(t)+'</span>';
          else h+='<span class="x" style="'+st+'">'+decorate(t)+'</span>';
        });
        h+='</p>';
      });
      h+='</div>';
    });
    h+='</div>';
    var ci=chs.indexOf(c),prev=null,next=null;
    if(ci>0) prev=[bi,chs[ci-1]]; else for(var i=bi-1;i>=0;i--){if(M.books[i][1].length){prev=[i,M.books[i][1][M.books[i][1].length-1]];break;}}
    if(ci<chs.length-1) next=[bi,chs[ci+1]]; else for(var j=bi+1;j<M.books.length;j++){if(M.books[j][1].length){next=[j,M.books[j][1][0]];break;}}
    h+='<div class="pager">'+(prev?'<a href="#/lees/'+prev[0]+'/'+prev[1]+'">← '+esc(M.books[prev[0]][0])+' '+prev[1]+'</a>':'<span></span>')+(next?'<a href="#/lees/'+next[0]+'/'+next[1]+'">'+esc(M.books[next[0]][0])+' '+next[1]+' →</a>':'')+'</div>';
    h+='<p class="small">Let op: de studiebijbel is chronologisch geordend; verzen die elders in het bestand staan, worden hier onder hun eigen boek en hoofdstuk getoond.</p>';
    app.innerHTML=h;
    document.getElementById('selB').onchange=function(){location.hash='#/lees/'+this.value;};
    document.getElementById('selC').onchange=function(){location.hash='#/lees/'+bi+'/'+this.value;};
    document.getElementById('kleur').onclick=function(){colors=!colors;localStorage.setItem('sbw-kleur',colors?'aan':'uit');this.classList.toggle('on',colors);app.querySelector('.txt').classList.toggle('plain',!colors);};
    if(focus!==undefined){var el=document.getElementById('b'+focus); if(el){el.scrollIntoView({block:'start'}); window.scrollBy(0,-110); el.style.background='#fff3c4'; setTimeout(function(){el.style.background='';},2200);}}
    else window.scrollTo(0,0);
  }).catch(function(e){app.innerHTML='<p>'+esc(e.message)+'</p>';});
}

/* ---------- popup ---------- */
function factLine(f){
  var kind=f[0],t=f[1],r=f[2];
  var lbl={rel:'',kind:'',rel2:'',rol:'',heerser:'Als koning/vorst hier genoemd: ',dood:'',tijd:'',gen:'Generatiemarkering: '}[kind]||'';
  var txt=lbl+t; txt=txt.charAt(0).toUpperCase()+txt.slice(1);
  var href=refHref(r);
  return '<li>'+esc(txt)+(r?' — '+(href?'<a href="'+href+'">'+esc(r)+'</a>':esc(r)):'')+'</li>';
}
function openEnt(id){
  var M=SBW.meta,row=M.ents[id]; if(!row) return;
  panel.hidden=false; pbody.innerHTML='<p class="loading">Laden…</p>';
  ent(id).then(function(d){
    var T=TYPES[row[1]]||['?','?'],C=CERT[row[2]];
    var h='<h2 class="p-name">'+esc(d.n)+'</h2>';
    var extra=[]; d.f.forEach(function(f){if(f!==d.n) extra.push(f);});
    if(extra.length||d.a.length||d.h.length) h+='<div class="small">'+(extra.length?'Ook geschreven als: '+esc(extra.join(', '))+'. ':'')+(d.a.length?'Afwijkende naam [{‘…’}]: '+esc(d.a.join(', '))+'. ':'')+(d.h.length?'Hebreeuws: &lt;'+esc(d.h.join('&gt;, &lt;'))+'&gt;':'')+'</div>';
    h+='<div class="badges"><span class="badge">'+esc(T[0])+'</span><span class="badge b-'+C[0]+'" title="'+esc(C[1])+'">'+esc(C[0])+'</span><span class="badge">'+d.on+(d.on===1?' vers':' verzen')+'</span></div>';
    // wie of wat
    var who=[];
    if(d.ov) who.push(esc(d.ov));
    if(d.role.length) who.push(esc(cap(T[0]))+': '+esc(d.role.join('; '))+'.');
    else who.push(esc(cap(T[0]))+(row[1]==='U'?' (soort niet vast te stellen uit de tekst)':'')+'.');
    var first=d.q.length?d.q[0]:null;
    if(first) who.push('Eerst genoemd in <a href="'+blockHref(first[0])+'">'+esc(M.blk[first[0]][2])+'</a>.');
    h+='<p class="who">'+who.join(' ')+'</p>';
    if(d.kp&&d.kp.length){d.kp.forEach(function(k){ if(!k.info.length) return; h+='<div class="kp"><b>Koningsprofiel uit de studiebijbel</b><br>'+esc(k.h)+'<br>'+k.info.map(esc).join('<br>')+'</div>';});}
    var facts=d.facts.filter(function(f){return f[0]!=='heerser';}),rul=d.facts.filter(function(f){return f[0]==='heerser';});
    if(facts.length){h+='<h3>Wat de tekst over '+(row[1]==='P'?'deze persoon':'deze naam')+' zegt</h3><ul class="facts">'+facts.slice(0,14).map(factLine).join('')+'</ul>';}
    if(rul.length){h+='<h3>Koningen of vorsten van '+esc(d.n)+'</h3><ul class="facts">'+rul.slice(0,12).map(function(f){return factLine(['',f[1].replace(/ \(.*\)$/,''),f[2]]);}).join('')+'</ul>';}
    if(d.x.length){h+='<h3>Toelichting in de tekst [(…)]</h3><ul class="facts">'+d.x.map(function(x){var hr=refHref(x[1]);return '<li>'+esc(x[0])+' — '+(hr?'<a href="'+hr+'">'+esc(x[1])+'</a>':esc(x[1]))+'</li>';}).join('')+'</ul>';}
    if(d.q.length){h+='<h3>Belangrijke verzen</h3>'+d.q.map(function(q){return '<div class="q"><a class="lab" href="'+blockHref(q[0])+'">'+esc(M.blk[q[0]][2])+'</a>'+decorate(q[1])+'</div>';}).join('');}
    h+='<h3>Komt voor in</h3><div class="chips">'+d.bk.map(function(b){return '<span class="chip">'+esc(M.books[b[0]][0])+' · '+b[1]+'</span>';}).join('')+'</div>';
    var refs=d.o.map(function(b){return '<a href="'+blockHref(b)+'">'+esc(M.blk[b][2])+'</a>';});
    h+='<div class="refs" id="refs">'+refs.slice(0,40).join('')+(refs.length>40?' <button id="moreRefs">Alle '+refs.length+(d.on>refs.length?' (van '+d.on+')':'')+' tonen</button>':'')+'</div>';
    if(d.nt.length){h+='<h3>Aantekeningen (studynotes)</h3>'+d.nt.map(function(i){var n=M.notes[i],hr=n.r?refHref(n.r):null;return '<div class="note"><span class="small">['+n.n+']'+(n.r?' · '+(hr?'<a href="'+hr+'">'+esc(n.r)+'</a>':esc(n.r)):'')+'</span><br>'+decorate(n.t)+'</div>';}).join('')+(d.ntn>d.nt.length?'<p class="small">Nog '+(d.ntn-d.nt.length)+' aantekening(en) noemen deze naam.</p>':'');}
    h+='<h3>Waarop deze indeling berust</h3><p class="why">'+esc(C[1])+'.<br>'+d.why.map(esc).join('<br>')+(d.lst?'<br>Ook in de naamlijst van deze wiki als '+esc(T[0])+'.':'')+'</p>';
    h+='<p class="small">Alles hierboven komt letterlijk uit de Elohim YHWH Studiebijbel v9 en de studynotes; er is niets bijgeschreven. <a href="#/e/'+id+'">Vaste link</a></p>';
    pbody.innerHTML=h; pbody.scrollTop=0;
    var mr=document.getElementById('moreRefs'); if(mr) mr.onclick=function(){document.getElementById('refs').innerHTML=refs.join('');};
  });
}
function cap(s){return s.charAt(0).toUpperCase()+s.slice(1);}
document.getElementById('panelClose').onclick=function(){panel.hidden=true;};
document.addEventListener('keydown',function(e){if(e.key==='Escape') panel.hidden=true; if((e.key==='Enter'||e.key===' ')&&e.target.classList&&e.target.classList.contains('ent')){e.preventDefault();openEnt(+e.target.dataset.e);}});
document.addEventListener('click',function(e){
  var t=e.target.closest('[data-e]'); if(t){e.preventDefault(); openEnt(+t.dataset.e); return;}
  var c=e.target.closest('.code'); if(c){showTip(c); return;}
  var a=e.target.closest('a'); if(a&&a.getAttribute('href')&&a.getAttribute('href').indexOf('#/lees')===0&&window.innerWidth<720) panel.hidden=true;
});
function showTip(el){var r=el.getBoundingClientRect(); tip.textContent=el.dataset.tip; tip.hidden=false; tip.style.left=Math.min(r.left,window.innerWidth-260)+'px'; tip.style.top=(r.bottom+6)+'px'; clearTimeout(showTip.t); showTip.t=setTimeout(function(){tip.hidden=true;},2600);}
document.addEventListener('mouseover',function(e){var c=e.target.closest&&e.target.closest('.code'); if(c) showTip(c);});

/* ---------- wiki ---------- */
function renderWiki(type,q){
  var M=SBW.meta; type=type||'P'; q=q||'';
  var counts={}; M.ents.forEach(function(e){counts[e[1]]=(counts[e[1]]||0)+1;});
  var h='<h1>Wiki</h1><p class="lead">Namen uit de studiebijbel, automatisch verzameld uit de tekst en de legendakleuren. Tik op een naam voor de uitleg.</p>';
  h+='<div class="bar"><input type="search" id="q" placeholder="Zoek een naam, bijv. David, Hebron, Jordaan" value="'+esc(q)+'" style="flex:1;min-width:12rem"></div>';
  h+='<div class="tabs">'+['P','V','S','L','W','R','O','U'].map(function(t){return '<button data-t="'+t+'" class="'+(t===type&&!q?'on':'')+'">'+TYPES[t][1]+' ('+(counts[t]||0)+')</button>';}).join('')+'</div>';
  h+='<p class="small"><span class="dot d-z"></span>zeker · <span class="dot d-w"></span>waarschijnlijk · <span class="dot d-o"></span>onzeker (zie “Over”)</p><div class="list" id="list"></div>';
  app.innerHTML=h;
  var list=document.getElementById('list');
  function draw(){
    var qq=norm(document.getElementById('q').value.trim()),rows=[];
    M.ents.forEach(function(e,i){
      if(qq){var hit=norm(e[0]).indexOf(qq)===0||e[4].some(function(f){return norm(f).indexOf(qq)===0;}); if(!hit&&qq.length>2) hit=norm(e[0]).indexOf(qq)>=0; if(!hit) return;}
      else if(e[1]!==type) return;
      rows.push(i);
    });
    rows.sort(function(a,b){return M.ents[b][3]-M.ents[a][3]||M.ents[a][0].localeCompare(M.ents[b][0],'nl');});
    var lim=qq?300:1600;
    list.innerHTML=rows.slice(0,lim).map(function(i){var e=M.ents[i];return '<a href="#/e/'+i+'" data-e="'+i+'"><span class="dot d-'+e[2]+'"></span>'+esc(e[0])+' <span>'+(qq?TYPES[e[1]][0]+' · ':'')+e[3]+'x</span></a>';}).join('')+(rows.length>lim?'<p class="small">… en nog '+(rows.length-lim)+' namen. Gebruik het zoekveld.</p>':'')+(rows.length?'':'<p>Geen namen gevonden.</p>');
  }
  draw();
  document.getElementById('q').oninput=function(){draw(); app.querySelectorAll('.tabs button').forEach(function(b){b.classList.toggle('on',!this.value&&b.dataset.t===type);},this);};
  app.querySelectorAll('.tabs button').forEach(function(b){b.onclick=function(){location.hash='#/wiki/'+b.dataset.t;};});
}
function renderOver(){
  var S=SBW.meta.stats,ps=S.perSoortZekerheid;
  var rows=['P','V','S','L','W','R','O','U'].map(function(t){var n=TYPES[t][0],x=ps[n]||{};return '<tr><td>'+TYPES[t][1]+'</td><td>'+(S.soorten[n]||0)+'</td><td>'+(x.zeker||0)+' / '+(x.waarschijnlijk||0)+' / '+(x.onzeker||0)+'</td></tr>';}).join('');
  app.innerHTML='<section class="page"><h1>Over deze wiki</h1>'+
  '<p class="notice">Dit is een voorbeeld (preview). Het staat niet online en is nog niet gecontroleerd door de redactie.</p>'+
  '<p>Deze wiki is gemaakt uit de Elohim YHWH Studiebijbel 2026 (v9) van Jan Smit, de bijbehorende studynotes en de officiële legenda. U leest de tekst per boek en hoofdstuk; namen van personen, volken, steden, landen, rivieren, meren, zeeën en regio’s zijn aan te tikken.</p>'+
  '<h2>Wat staat er in een popup?</h2><ol><li>Wie of wat het is, en waarop dat berust (legendakleur, zinnen in de tekst of een naamlijst).</li><li>Wat de tekst zelf zegt: “zoon van”, “koning van”, “verwekte”, generatiemarkeringen en de koningsprofielen uit de studiebijbel.</li><li>De belangrijkste verzen, letterlijk geciteerd, met een link.</li><li>Alle plaatsen waar de naam voorkomt en de aantekeningen die de naam noemen.</li></ol>'+
  '<p>Er worden geen levensverhalen bijgeschreven. Staat er in de tekst niets over de rol of het doel van iemand, dan blijft de popup kort en verwijst naar de verzen.</p>'+
  '<h2>Tellingen</h2><table class="stat"><tr><td><b>Soort</b></td><td><b>Aantal</b></td><td><b>zeker / waarschijnlijk / onzeker</b></td></tr>'+rows+'<tr><td><b>Totaal</b></td><td><b>'+S.entiteiten+'</b></td><td></td></tr></table>'+
  '<p class="small">Tekstblokken (verzen of versgroepen): '+S.blokken+'. Aantekeningen: '+SBW.meta.notes.length+'.</p>'+
  '<h2>Zekerheid</h2><ol><li><b>zeker</b>: '+CERT.z[1]+'.</li><li><b>waarschijnlijk</b>: '+CERT.w[1]+'.</li><li><b>onzeker</b>: '+CERT.o[1]+'.</li></ol></section>';
}
function renderLegenda(){app.innerHTML=''; app.appendChild(document.getElementById('tpl-legenda').content.cloneNode(true));}

/* ---------- router ---------- */
function route(){
  var h=location.hash.replace(/^#\/?/,''),p=h.split('/');
  document.querySelectorAll('nav a').forEach(function(a){a.classList.toggle('on',a.dataset.nav===(p[0]==='e'?'wiki':(p[0]||'lees')));});
  tip.hidden=true; if(p[0]!=='e') panel.hidden=true;
  if(p[0]==='wiki') renderWiki(p[1]);
  else if(p[0]==='e'){ if(!app.querySelector('#list')) renderWiki(SBW.meta.ents[+p[1]]?SBW.meta.ents[+p[1]][1]:'P'); openEnt(+p[1]); }
  else if(p[0]==='legenda') renderLegenda();
  else if(p[0]==='over') renderOver();
  else renderRead(p[1]!==undefined?+p[1]:undefined,p[2]?+p[2]:undefined,p[3]!==undefined?+p[3]:undefined);
}
load('data/meta.js').then(function(){window.addEventListener('hashchange',route); route();}).catch(function(e){app.innerHTML='<p>'+esc(e.message)+'</p>';});
})();
