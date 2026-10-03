const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const money=n=>'$ '+n.toLocaleString('es-CO');
const BEBIDAS={t:'Bebida',max:1,o:[['Coca Cola 400ml',4000],['Coca Cola sin azúcar 400ml',4000],['Ginger 400ml',4000],['Agua Brisa 600ml',4000],['Hit de mango 400ml',4000],['Hit de mora 400ml',4000],['Coronita 210ml',5000],['Tres Cordilleras',8000],['Coca Cola 1.5 Lt',8000],['Sprite 1.5 Lt',8000]]};
const TERIYAKI={t:'Teriyaki',max:3,o:[['Salsa teriyaki extra',1000],['Mayonesa de sushi',1000],['Jengibre',0],['Wasabi',0]]};
const SALSAS={t:'Salsas',max:2,o:[['BBQ',1000],['Ajo',1000],['Piña',1000],['Picante',0]]};
// Datos de ejemplo: luego se reemplazan por la respuesta de la API REST
const MENU=[
 {c:'Hamburguesas',e:/*aca va el logo de la hamburguesa*/'',h:20,p:[['Hamburguesa clásica',16900,'Carne, queso, lechuga y tomate.',[SALSAS,BEBIDAS]],['Hamburguesa doble',22900,'Doble carne y queso cheddar.',[SALSAS,BEBIDAS]]]},
 {c:'Pizza 27cm (6 porciones)',e:'',h:30,p:[['Pizza pepperoni',24900,'Queso mozzarella y pepperoni.',[BEBIDAS]],['Pizza hawaiana',24900,'Jamón y piña.',[BEBIDAS]]]},
 {c:'Alitas',e:'',h:10,p:[['Alitas x8',21900,'Ocho alitas con salsa a elección.',[SALSAS,BEBIDAS]]]},
 {c:'Costillas BBQ',e:'',h:0,p:[['Costillas BBQ',32900,'Media tira con salsa BBQ.',[BEBIDAS]]]},
 {c:'Salchipapa',e:'',h:40,p:[['Salchipapa clásica',14900,'Papa, salchicha y salsas.',[SALSAS,BEBIDAS]]]},
 {c:'Perro caliente',e:'',h:35,p:[['Perro americano',12900,'Salchicha, queso y papa ripio.',[SALSAS,BEBIDAS]]]},
 {c:'Lasaña',e:'',h:25,p:[['Lasagna de carne',18900,'Lasaña gratinada con carne y pan.',[BEBIDAS]]]},
 {c:'Sushi makis especiales',e:'',h:200,p:[['Crispy Philadelphia',27900,'Diez makis rellenos de salmón, queso crema, aguacate y mayonesa picante, envueltos en tempura y panko, servidos con salsa teriyaki y mayonesa de sushi.',[BEBIDAS,TERIYAKI]]]},
 {c:'Sushi nori makis',e:'',h:210,p:[['California roll',22900,'Diez makis de kanikama y aguacate.',[BEBIDAS,TERIYAKI]]]},
 {c:'Sushi combos',e:'',h:190,p:[['Combo x30',69900,'Treinta piezas surtidas.',[BEBIDAS,TERIYAKI]]]},
 {c:'Cervezas',e:'',h:45,p:[['Cerveza Club Colombia',6000,'Botella 330ml.',[]],['Cerveza Corona',9000,'Botella 355ml.',[]]]},
 {c:'Jugos Hit',e:'',h:130,p:[['Jugo Hit de mango',4000,'Caja 400ml.',[]],['Jugo Hit de mora',4000,'Caja 400ml.',[]]]},
];
let orders=[],draft=null,seq=13,filter='all',cat=0,cur=null,curOpts=[],curQty=1,openId=null;

function go(v){$$('.view').forEach(x=>x.classList.toggle('on',x.id==='v-'+v));
  $$('nav button').forEach(b=>b.classList.toggle('on',b.dataset.go===(v==='detail'?'orders':v)));}
const total=o=>o.lines.reduce((s,l)=>s+l.unit*l.qty,0);
const count=o=>o.lines.reduce((s,l)=>s+l.qty,0);
const mins=o=>Math.max(0,Math.floor((Date.now()-o.t)/60000));
const hhmm=d=>d.toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit',hour12:false});

/* ---------- Pedidos ---------- */
function renderOrders(){
  const pend=orders.filter(o=>!o.paid).length, paid=orders.length-pend;
  const F=[['all','Todo'],['pend','Pendiente',pend],['paid','Pagado',paid]];
  $('#chips').innerHTML=F.map(f=>`<button class="chip ${filter===f[0]?'on':''}" data-f="${f[0]}">${f[1]}${f[2]?`<i>${f[2]}</i>`:''}</button>`).join('');
  const L=orders.filter(o=>filter==='all'||(filter==='pend')!==o.paid).slice().reverse();
  $('#orderList').innerHTML=L.length?L.map(o=>`<button class="order ${o.paid?'paid':''}" data-id="${o.id}">
    <div class="row"><b>#${o.id} · En el local</b><span>${money(total(o))}</span></div>
    <div class="row"><span><span class="tag">PDV</span> <span class="tag ${o.paid?'g':'w'}">${o.paid?'Pagado':'No pagado'}</span></span>
    <small style="color:var(--mut)">${hhmm(new Date(o.t))} · ${mins(o)} min</small></div>
    <small style="color:var(--mut)">${count(o)} producto(s)</small></button>`).join('')
    :'<div class="empty">No hay pedidos todavía.<br>Toca «Nuevo pedido» para crear el primero.</div>';
}
$('#chips').onclick=e=>{const b=e.target.closest('[data-f]');if(b){filter=b.dataset.f;renderOrders();}};
$('#orderList').onclick=e=>{const b=e.target.closest('[data-id]');if(b){openId=+b.dataset.id;renderDetail(orders.find(o=>o.id===openId),true);go('detail');}};
$('#newOrder').onclick=()=>{draft={id:seq,t:Date.now(),lines:[],paid:false};cat=0;$('#q').value='';renderMenu();go('menu');};

/* ---------- Menú ---------- */
function renderMenu(){
  $('#cats').innerHTML=MENU.map((m,i)=>`<button class="${i===cat?'on':''}" data-i="${i}">${m.c} ${m.e}</button>`).join('');
  const q=$('#q').value.trim().toLowerCase();
  let items,title;
  if(q){items=MENU.flatMap((m,i)=>m.p.map(p=>({p,m}))).filter(x=>x.p[0].toLowerCase().includes(q));title='Resultados de la búsqueda';}
  else{items=MENU[cat].p.map(p=>({p,m:MENU[cat]}));title=MENU[cat].c;}
  $('#ctitle').textContent=title;
  $('#grid').innerHTML=items.length?items.map(x=>`<button class="prod" data-n="${x.p[0]}">
    <div class="ph" style="background:linear-gradient(135deg,hsl(${x.m.h} 55% 38%),hsl(${x.m.h+30} 60% 22%))"><span>${x.m.e}</span>${x.p[0]}</div>
    <p>${money(x.p[1])}</p></button>`).join(''):'<p style="color:var(--mut)">Sin resultados. Prueba con otra palabra.</p>';
  const n=draft?count(draft):0;
  $('#cartSum').textContent=n?`${n} producto(s) · ${money(total(draft))}`:'Aún no hay productos';
}
$('#cats').onclick=e=>{const b=e.target.closest('[data-i]');if(b){cat=+b.dataset.i;$('#q').value='';renderMenu();}};
$('#q').oninput=renderMenu;
$('#grid').onclick=e=>{const b=e.target.closest('[data-n]');if(!b)return;
  const p=MENU.flatMap(m=>m.p).find(p=>p[0]===b.dataset.n);openProduct(p);};
$('#free').onclick=()=>{const n=prompt('Nombre del producto libre');if(!n)return;const v=parseInt(prompt('Precio (COP)'),10);
  if(v>0){draft.lines.push({name:n.toUpperCase(),qty:1,unit:v,opts:[]});renderMenu();}};
$('#toOrder').onclick=()=>{if(!draft||!draft.lines.length){alert('Agrega al menos un producto.');return;}renderDetail(draft,false);go('detail');};

/* ---------- Producto (personalización) ---------- */
function openProduct(p){cur=p;curOpts=p[3].map(()=>[]);curQty=1;
  $('#mTitle').textContent=p[0].toUpperCase();
  const m=MENU.find(m=>m.p.includes(p));
  $('#mBody').innerHTML=`<div class="pinfo"><div><p>${p[2]}</p><b style="font-size:20px">${money(p[1])}</b></div>
   <div class="ph" style="background:linear-gradient(135deg,hsl(${m.h} 55% 38%),hsl(${m.h+30} 60% 22%))"><span style="position:static;font-size:44px;margin:auto">${m.e}</span></div></div>`+
   p[3].map((g,gi)=>`<div class="grp"><h4>${g.t}</h4><small>Selecciona hasta ${g.max} opción(es)</small>
   <div class="opts">${g.o.map((o,oi)=>`<button class="opt" data-g="${gi}" data-o="${oi}"><span class="bx"></span><span>${o[0]}<em>${o[1]?'+ '+money(o[1]):'Gratis'}</em></span></button>`).join('')}</div></div>`).join('');
  syncModal();$('#modal').classList.add('on');}
function unit(){return cur[1]+cur[3].reduce((s,g,gi)=>s+curOpts[gi].reduce((a,oi)=>a+g.o[oi][1],0),0);}
function syncModal(){
  $$('#mBody .opt').forEach(b=>{const gi=+b.dataset.g,oi=+b.dataset.o,sel=curOpts[gi].includes(oi);
    b.classList.toggle('on',sel);b.classList.toggle('off',!sel&&curOpts[gi].length>=cur[3][gi].max&&cur[3][gi].max>1);});
  $('#mQty').textContent=curQty;$('#mAdd').textContent='Agregar '+money(unit()*curQty);}
$('#mBody').onclick=e=>{const b=e.target.closest('.opt');if(!b)return;const gi=+b.dataset.g,oi=+b.dataset.o,a=curOpts[gi],max=cur[3][gi].max;
  if(a.includes(oi))a.splice(a.indexOf(oi),1);
  else if(max===1)curOpts[gi]=[oi];
  else if(a.length<max)a.push(oi);
  syncModal();};
$('#mMinus').onclick=()=>{if(curQty>1){curQty--;syncModal();}};
$('#mPlus').onclick=()=>{curQty++;syncModal();};
$('#mClose').onclick=()=>$('#modal').classList.remove('on');
$('#modal').onclick=e=>{if(e.target.id==='modal')$('#modal').classList.remove('on');};
document.addEventListener('keydown',e=>{if(e.key==='Escape')$('#modal').classList.remove('on');});
$('#mAdd').onclick=()=>{
  const names=cur[3].flatMap((g,gi)=>curOpts[gi].map(oi=>g.o[oi][0]));
  draft.lines.push({name:cur[0].toUpperCase(),qty:curQty,unit:unit(),opts:names});
  $('#modal').classList.remove('on');renderMenu();};

/* ---------- Detalle del pedido ---------- */
function renderDetail(o,saved){
  $('#dh').className='dh'+(o.paid?' paid':'');
  $('#dh').innerHTML=`<span>#${o.id} · En el local · ${o.paid?'Pagado':'Pendiente'}</span><button id="dx" aria-label="Cerrar">✕</button>`;
  $('#dx').onclick=()=>{saved?(renderOrders(),go('orders')):go('menu');};
  $('#items').innerHTML=o.lines.length?o.lines.map((l,i)=>`<div class="line"><div>${l.qty} ${l.name}${l.opts.length?`<small>${l.opts.join(', ')}</small>`:''}</div>
    <div style="display:flex;align-items:center">${money(l.unit*l.qty).slice(2)}<button data-rm="${i}" aria-label="Quitar ${l.name}">✕</button></div></div>`).join('')
    :'<div class="empty">El pedido está vacío. Vuelve al menú para agregar productos.</div>';
  $('#subLbl').textContent=`Subtotal productos (${count(o)})`;$('#sub').textContent=total(o).toLocaleString('es-CO');
  $('#total').textContent=money(total(o));
  $('#paidTag').textContent=o.paid?'Pagado':'No pagado';$('#paidTag').className='tag '+(o.paid?'g':'w');
  $('#accept').textContent=saved?'Guardar':'Aceptar';
  $('#items').onclick=e=>{const b=e.target.closest('[data-rm]');if(b){o.lines.splice(+b.dataset.rm,1);renderDetail(o,saved);}};
  $('#pay').onclick=()=>{o.paid=!o.paid;renderDetail(o,saved);};
  $('#cancel').onclick=()=>{if(!confirm('¿Cancelar este pedido?'))return;
    if(saved)orders=orders.filter(x=>x!==o);draft=null;renderOrders();go('orders');};
  $('#accept').onclick=()=>{if(!o.lines.length){alert('Agrega al menos un producto.');return;}
    if(!saved){orders.push(o);seq++;draft=null;}renderOrders();go('orders');};
}

/* ---------- Navegación inferior ---------- */
$$('nav button').forEach(b=>b.onclick=()=>{const t=b.dataset.go;
  if(t==='orders'){renderOrders();go('orders');}
  else if(t==='menu'){if(!draft)draft={id:seq,t:Date.now(),lines:[],paid:false};renderMenu();go('menu');}
  else alert('Esta sección se conectará más adelante.');});
renderOrders();setInterval(()=>{if($('#v-orders').classList.contains('on'))renderOrders();},60000);
