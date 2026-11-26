const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const money = n => '$ ' + Number(n || 0).toLocaleString('es-CO');

let MENU = [];
let ADMIN_MENU = [];
let ADMIN_GRUPOS = [];
let adminTab = 'cats';
let orders = [], draft = null, seq = 13, filter = 'all', cat = 0, cur = null, curOpts = [], curQty = 1, openId = null;

const AREAS_LABEL = {
  PARRILLA: 'Parrilla',
  SOPAS_ENTRADAS: 'Sopas y Entradas',
  BEBIDAS: 'Bebidas'
};

/* ---------- Mapa de imágenes reales (frontend/imagenes/) ---------- */
const PRODUCT_IMAGES = {
  'ajiaco normal (22 onz)': 'ajiaco.jpeg',
  'ajiaco pequeño (15 onz)': 'ajiacoPequeño.jpeg',
  'chicharrones': 'chicharrones.jpeg',
  'chorizo': 'chorizo.jpeg',
  'churrasco': 'churrasco.jpeg',
  'frijolada': 'frijolada.jpeg',
  'insaciable': 'insaciable.jpeg',
  'longaniza': 'longaniza.jpeg',
  'mazamorra normal (22 onz)': 'mazamorra.jpeg',
  'mazamorra pequeña (15 onz)': 'mazamorraPequeña.jpeg',
  'medio plato mixta 3 carnes': 'Medio plato mixta 3 carnes.jpeg',
  //'mixta 2 carnes': 'Mixta 1-2.jpeg',
  //'mixta 3 carnes': 'Mixta 1-2.jpeg',
  'mondongo normal (22 onz)': 'mondongo.jpeg',
  'mondongo pequeño (15 onz)': 'mondongoPequeño.jpeg',
  'parrillada': 'parrillada.jpeg',
  'patacones': 'patacones.jpeg',
  'pechuga': 'pechuga de pollo.jpeg',
  'pechuga de pollo': 'pechuga de pollo.jpeg',
  'punta de anca': 'punta de anca.jpeg',
  'rellena': 'rellena.jpeg',
  'solo costilla': 'solo costilla.jpeg'
};

function obtenerImagenProducto(nombre) {
  const clave = (nombre || '').trim().toLowerCase();
  const archivo = PRODUCT_IMAGES[clave];
  return archivo ? encodeURI(`/imagenes/${archivo}`) : null;
}

function renderPhProducto(p, m, contenidoHtml = '') {
  const imgUrl = obtenerImagenProducto(p.nombre);
  if (imgUrl) {
    return `<div class="ph has-img" style="background-image:linear-gradient(to top,rgba(0,0,0,.78) 0%,rgba(0,0,0,.15) 55%,rgba(0,0,0,.1) 100%),url('${imgUrl}')">${contenidoHtml}</div>`;
  }
  return `<div class="ph" style="background:linear-gradient(135deg,hsl(${m.hue} 55% 38%),hsl(${m.hue + 30} 60% 22%))">${contenidoHtml}</div>`;
}

/* ---------- Cliente API con token JWT ---------- */
const ROLES_LABEL = {
  ADMINISTRADOR: 'Administrador',
  MESERO: 'Mesero',
  CAJERA: 'Cajera',
  ENCARGADO_AREA: 'Encargado de área',
  PATINADOR: 'Patinador'
};

const ROL_PERMISOS = {
  ADMINISTRADOR: {
    inicio: 'orders',
    nav: ['orders', 'sales', 'menu', 'users', 'reports', 'more'],
    vistas: ['orders', 'sales', 'menu', 'detail', 'admin-menu', 'users', 'kds', 'reports', 'more']
  },
  MESERO: {
    inicio: 'orders',
    nav: ['orders', 'menu'],
    vistas: ['orders', 'menu', 'detail']
  },
  CAJERA: {
    inicio: 'sales',
    nav: ['sales', 'reports'],
    vistas: ['sales', 'reports']
  },
  ENCARGADO_AREA: {
    inicio: 'kds',
    nav: ['kds'],
    vistas: ['kds']
  },
  PATINADOR: {
    inicio: 'kds',
    nav: ['kds'],
    vistas: ['kds']
  }
};

function getUsuarioActual() {
  try {
    return JSON.parse(localStorage.getItem('pdv_usuario') || 'null');
  } catch {
    return null;
  }
}

function aplicarPermisosRol() {
  const u = getUsuarioActual();
  const rol = u?.rol;
  const conf = ROL_PERMISOS[rol] || { inicio: 'orders', nav: [], vistas: [] };

  const btnKds = $('#btnOpenKds');
  if (btnKds) {
    btnKds.style.display = ['ADMINISTRADOR', 'ENCARGADO_AREA', 'PATINADOR'].includes(rol) ? '' : 'none';
  }

  const btnAdmin = $('#openAdminMenu');
  if (btnAdmin) {
    btnAdmin.style.display = rol === 'ADMINISTRADOR' ? '' : 'none';
  }

  $$('nav button[data-go]').forEach(b => {
    b.style.display = conf.nav.includes(b.dataset.go) ? '' : 'none';
  });
}

function mostrarLogin(mensaje = '') {
  localStorage.removeItem('pdv_token');
  localStorage.removeItem('pdv_usuario');
  $$('.view').forEach(x => x.classList.toggle('on', x.id === 'v-login'));
  const nav = $('nav');
  if (nav) nav.style.display = 'none';
  const err = $('#loginErr');
  if (err) {
    err.textContent = mensaje;
    err.style.display = mensaje ? 'block' : 'none';
  }
}

async function asegurarToken() {
  const token = localStorage.getItem('pdv_token');
  if (!token) {
    mostrarLogin();
    throw new Error('No hay sesión activa');
  }
  return token;
}

async function api(url, options = {}) {
  const token = await asegurarToken();
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...(options.headers || {})
    }
  });

  if (res.status === 401) {
    mostrarLogin('Tu sesión expiró. Inicia sesión de nuevo.');
    throw new Error('Sesión expirada o no autorizada');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const e = new Error(err.detail || 'Error en la petición');
    e.status = res.status;
    throw e;
  }
  return res.status === 204 ? null : res.json();
}

async function cargarMenu() {
  try {
    MENU = await api('/api/menu');
    if (cat >= MENU.length) cat = 0;
    renderMenu();
  } catch (e) {
    console.error('Error cargando menú:', e);
    $('#ctitle').textContent = 'Error al cargar el menú';
    $('#grid').innerHTML = `<p style="color:var(--bad)">${e.message}</p>`;
  }
}

/* ---------- Navegación ---------- */
function go(v) {
  const u = getUsuarioActual();
  if (v !== 'login' && u) {
    const conf = ROL_PERMISOS[u.rol];
    if (conf && !conf.vistas.includes(v)) {
      v = conf.inicio;
    }
  }
  $$('.view').forEach(x => x.classList.toggle('on', x.id === 'v-' + v));
  const navKey = v === 'detail' ? 'orders' : (v === 'admin-menu' ? 'menu' : v);
  $$('nav button[data-go]').forEach(b => b.classList.toggle('on', b.dataset.go === navKey));
}

const total = o => o.lines.reduce((s, l) => s + l.unit * l.qty, 0);
const count = o => o.lines.reduce((s, l) => s + l.qty, 0);
const mins = o => Math.max(0, Math.floor((Date.now() - o.t) / 60000));
const hhmm = d => d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', hour12: false });

/* ---------- Pedidos ---------- */
function renderOrders() {
  const pend = orders.filter(o => !o.paid).length, paid = orders.length - pend;
  const F = [['all', 'Todo'], ['pend', 'Pendiente', pend], ['paid', 'Pagado', paid]];
  $('#chips').innerHTML = F.map(f => `<button class="chip ${filter === f[0] ? 'on' : ''}" data-f="${f[0]}">${f[1]}${f[2] ? `<i>${f[2]}</i>` : ''}</button>`).join('');
  const L = orders.filter(o => filter === 'all' || (filter === 'pend') !== o.paid).slice().reverse();
  $('#orderList').innerHTML = L.length ? L.map(o => `<button class="order ${o.paid ? 'paid' : ''}" data-id="${o.id}">
    <div class="row"><b>#${o.id} · En el local</b><span>${money(total(o))}</span></div>
    <div class="row"><span><span class="tag">PDV</span> <span class="tag ${o.paid ? 'g' : 'w'}">${o.paid ? 'Pagado' : 'No pagado'}</span></span>
    <small style="color:var(--mut)">${hhmm(new Date(o.t))} · ${mins(o)} min</small></div>
    <small style="color:var(--mut)">${count(o)} producto(s)</small>
  </button>`).join('')
    : '<div class="empty">No hay pedidos todavía.<br>Toca «Nuevo pedido» para crear el primero.</div>';
}

$('#chips').onclick = e => { const b = e.target.closest('[data-f]'); if (b) { filter = b.dataset.f; renderOrders(); } };
$('#orderList').onclick = e => { const b = e.target.closest('[data-id]'); if (b) { openId = +b.dataset.id; renderDetail(orders.find(o => o.id === openId), true); go('detail'); } };
$('#newOrder').onclick = () => { draft = { id: seq, t: Date.now(), lines: [], paid: false }; cat = 0; $('#q').value = ''; renderMenu(); go('menu'); };

/* ---------- Menú (conectado a /api/menu) ---------- */
function renderMenu() {
  aplicarPermisosRol();
  if (!MENU.length) {
    $('#cats').innerHTML = '';
    $('#ctitle').textContent = 'Cargando menú...';
    $('#grid').innerHTML = '';
    return;
  }

  $('#cats').innerHTML = MENU.map((m, i) => `<button class="${i === cat ? 'on' : ''}" data-i="${i}">${m.nombre} ${m.emoji || ''}</button>`).join('');
  const q = $('#q').value.trim().toLowerCase();
  let items, title;

  if (q) {
    items = MENU.flatMap(m => m.productos.map(p => ({ p, m }))).filter(x => x.p.nombre.toLowerCase().includes(q));
    title = 'Resultados de la búsqueda';
  } else {
    const actual = MENU[cat];
    items = actual.productos.map(p => ({ p, m: actual }));
    title = actual.nombre;
  }

  $('#ctitle').textContent = title;
  $('#grid').innerHTML = items.length ? items.map(x => `<button class="prod" data-id="${x.p.id}">
    ${renderPhProducto(x.p, x.m, `<span>${obtenerImagenProducto(x.p.nombre) ? '' : (x.m.emoji || '')}</span>${x.p.nombre}`)}
    <p>${money(x.p.precio)}</p></button>`).join('')
    : '<p style="color:var(--mut)">Sin resultados. Prueba con otra palabra.</p>';

  const n = draft ? count(draft) : 0;
  $('#cartSum').textContent = n ? `${n} producto(s) · ${money(total(draft))}` : 'Aún no hay productos';
}

$('#cats').onclick = e => { const b = e.target.closest('[data-i]'); if (b) { cat = +b.dataset.i; $('#q').value = ''; renderMenu(); } };
$('#q').oninput = renderMenu;
$('#grid').onclick = e => {
  const b = e.target.closest('[data-id]');
  if (!b) return;
  const prodId = +b.dataset.id;
  const p = MENU.flatMap(m => m.productos).find(p => p.id === prodId);
  if (p) openProduct(p);
};
$('#free').onclick = () => {
  const n = prompt('Nombre del producto libre');
  if (!n) return;
  const v = parseInt(prompt('Precio (COP)'), 10);
  if (v > 0) {
    if (!draft) draft = { id: seq, t: Date.now(), lines: [], paid: false };
    draft.lines.push({ producto_id: null, name: n.toUpperCase(), qty: 1, unit: v, opts: [], opcion_ids: [] });
    renderMenu();
  }
};
$('#toOrder').onclick = () => { if (!draft || !draft.lines.length) { alert('Agrega al menos un producto.'); return; } renderDetail(draft, false); go('detail'); };

/* ---------- Producto (personalización desde JSON de API) ---------- */
function openProduct(p) {
  cur = p;
  curOpts = (p.grupos || []).map(() => []);
  curQty = 1;
  $('#mTitle').textContent = p.nombre.toUpperCase();
  const m = MENU.find(m => m.productos.some(prod => prod.id === p.id)) || { hue: 20, emoji: '' };
  const tieneImg = Boolean(obtenerImagenProducto(p.nombre));

  $('#mBody').innerHTML = `<div class="pinfo"><div><p>${p.descripcion || ''}</p><b style="font-size:20px">${money(p.precio)}</b></div>
    ${renderPhProducto(p, m, tieneImg ? '' : `<span style="position:static;font-size:44px;margin:auto">${m.emoji || ''}</span>`)}</div>` +
    (p.grupos || []).map((g, gi) => `<div class="grp"><h4>${g.titulo}</h4><small>Selecciona hasta ${g.max_opciones} opción(es)</small>
      <div class="opts">${g.opciones.map((o, oi) => `<button class="opt" data-g="${gi}" data-o="${oi}"><span class="bx"></span><span>${o.nombre}<em>${o.precio ? '+ ' + money(o.precio) : 'Gratis'}</em></span></button>`).join('')}</div>
    </div>`).join('');

  syncModal();
  $('#modal').classList.add('on');
}

function unit() {
  const grupos = cur.grupos || [];
  return cur.precio + grupos.reduce((s, g, gi) => s + curOpts[gi].reduce((a, oi) => a + g.opciones[oi].precio, 0), 0);
}

function syncModal() {
  const grupos = cur.grupos || [];
  $$('#mBody .opt').forEach(b => {
    const gi = +b.dataset.g, oi = +b.dataset.o, sel = curOpts[gi].includes(oi);
    b.classList.toggle('on', sel);
    b.classList.toggle('off', !sel && curOpts[gi].length >= grupos[gi].max_opciones && grupos[gi].max_opciones > 1);
  });
  $('#mQty').textContent = curQty;
  $('#mAdd').textContent = 'Agregar ' + money(unit() * curQty);
}

$('#mBody').onclick = e => {
  const b = e.target.closest('.opt');
  if (!b) return;
  const gi = +b.dataset.g, oi = +b.dataset.o, a = curOpts[gi], max = cur.grupos[gi].max_opciones;
  if (a.includes(oi)) a.splice(a.indexOf(oi), 1);
  else if (max === 1) curOpts[gi] = [oi];
  else if (a.length < max) a.push(oi);
  syncModal();
};
$('#mMinus').onclick = () => { if (curQty > 1) { curQty--; syncModal(); } };
$('#mPlus').onclick = () => { curQty++; syncModal(); };
$('#mClose').onclick = () => $('#modal').classList.remove('on');
$('#modal').onclick = e => { if (e.target.id === 'modal') $('#modal').classList.remove('on'); };
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    $('#modal').classList.remove('on');
    $('#adminModal').classList.remove('on');
  }
});

$('#mAdd').onclick = () => {
  if (!draft) draft = { id: seq, t: Date.now(), lines: [], paid: false };
  const grupos = cur.grupos || [];
  const elegidas = grupos.flatMap((g, gi) => curOpts[gi].map(oi => g.opciones[oi]));
  draft.lines.push({
    producto_id: cur.id,
    name: cur.nombre.toUpperCase(),
    qty: curQty,
    unit: unit(),
    opts: elegidas.map(o => o.nombre),
    opcion_ids: elegidas.map(o => o.id)
  });
  $('#modal').classList.remove('on');
  renderMenu();
};

/* ---------- GESTIÓN DE MENÚ (Administración) ---------- */
async function cargarAdminMenu() {
  try {
    const incluir = $('#chkInactivos').checked;
    const [menuData, gruposData] = await Promise.all([
      api(`/api/menu?incluir_inactivos=${incluir}`),
      api(`/api/menu/grupos?incluir_inactivos=${incluir}`)
    ]);
    ADMIN_MENU = menuData;
    ADMIN_GRUPOS = gruposData;
    actualizarFiltroCategoriasAdmin();
    renderAdminView();
  } catch (e) {
    $('#adminContent').innerHTML = `<div class="empty" style="color:var(--bad)">Error: ${e.message}</div>`;
  }
}

function actualizarFiltroCategoriasAdmin() {
  const sel = $('#adminCatFilter');
  const valorPrevio = sel.value;
  sel.innerHTML = '<option value="all">Todas las categorías</option>' +
    ADMIN_MENU.map(c => `<option value="${c.id}">${c.nombre}${c.activo ? '' : ' (Inactiva)'}</option>`).join('');
  if ([...sel.options].some(o => o.value === valorPrevio)) {
    sel.value = valorPrevio;
  }
}

function renderAdminView() {
  const btnNew = $('#btnAdminNew');
  const prodFilters = $('#adminProdFilters');

  if (adminTab === 'cats') {
    btnNew.style.display = '';
    btnNew.textContent = '+ Nueva Categoría';
    prodFilters.style.display = 'none';
    renderAdminCategorias();
  } else if (adminTab === 'prods') {
    btnNew.style.display = '';
    btnNew.textContent = '+ Nuevo Producto';
    prodFilters.style.display = 'flex';
    renderAdminProductos();
  } else {
    btnNew.style.display = '';
    btnNew.textContent = '+ Nuevo Grupo';
    prodFilters.style.display = 'none';
    renderAdminGrupos();
  }
}

/* --- 1. CATEGORÍAS --- */
function renderAdminCategorias() {
  if (!ADMIN_MENU.length) {
    $('#adminContent').innerHTML = '<div class="empty">No hay categorías registradas.</div>';
    return;
  }

  $('#adminContent').innerHTML = ADMIN_MENU.map(c => {
    const activosCount = (c.productos || []).filter(p => p.activo).length;
    const totalProds = (c.productos || []).length;
    return `
      <div class="admin-card ${c.activo ? '' : 'inactive'}">
        <div class="row">
          <div>
            <span class="swatch" style="background:hsl(${c.hue} 60% 42%)"></span>
            <b>${c.emoji ? c.emoji + ' ' : ''}${c.nombre}</b>
          </div>
          <span class="tag ${c.activo ? 'g' : 'w'}">${c.activo ? 'Activa' : 'Inactiva'}</span>
        </div>
        <div class="row" style="font-size:13px;color:var(--mut)">
          <span>Área: <b>${AREAS_LABEL[c.area] || c.area}</b></span>
          <span>Posición: ${c.posicion} · Productos: ${activosCount}/${totalProds}</span>
        </div>
        <div class="admin-actions">
          <button class="btn ghost sm" data-edit-cat="${c.id}">Editar</button>
          ${c.activo
            ? `<button class="btn bad sm" data-del-cat="${c.id}">Desactivar</button>`
            : `<button class="btn ok sm" data-act-cat="${c.id}">Reactivar</button>`
          }
        </div>
      </div>
    `;
  }).join('');
}

function abrirModalCategoria(catObj = null) {
  const esEdicion = Boolean(catObj);
  $('#amTitle').textContent = esEdicion ? `Editar categoría: ${catObj.nombre}` : 'Nueva categoría';

  $('#amForm').innerHTML = `
    <div class="field">
      <label for="catNombre">Nombre *</label>
      <input id="catNombre" required maxlength="80" value="${esEdicion ? catObj.nombre : ''}" placeholder="Ej. Postres">
    </div>
    <div class="field">
      <label for="catArea">Área de preparación *</label>
      <select id="catArea" required>
        <option value="PARRILLA" ${catObj?.area === 'PARRILLA' ? 'selected' : ''}>Parrilla</option>
        <option value="SOPAS_ENTRADAS" ${catObj?.area === 'SOPAS_ENTRADAS' ? 'selected' : ''}>Sopas y Entradas</option>
        <option value="BEBIDAS" ${catObj?.area === 'BEBIDAS' ? 'selected' : ''}>Bebidas</option>
      </select>
    </div>
    <div class="row">
      <div class="field" style="flex:1">
        <label for="catEmoji">Emoji (opcional)</label>
        <input id="catEmoji" maxlength="8" value="${esEdicion ? (catObj.emoji || '') : ''}" placeholder="Ej. 🥩">
      </div>
      <div class="field" style="flex:1">
        <label for="catPosicion">Posición (orden)</label>
        <input id="catPosicion" type="number" min="0" value="${esEdicion ? catObj.posicion : ADMIN_MENU.length}">
      </div>
    </div>
    <div class="field">
      <label for="catHue">Color de tarjeta (Tono HSL: <span id="hueVal">${esEdicion ? catObj.hue : 25}</span>°)</label>
      <input id="catHue" type="range" min="0" max="360" value="${esEdicion ? catObj.hue : 25}">
      <div id="huePreview" style="height:28px;border-radius:6px;background:linear-gradient(135deg,hsl(${esEdicion ? catObj.hue : 25} 55% 38%),hsl(${(esEdicion ? catObj.hue : 25) + 30} 60% 22%))"></div>
    </div>
    <div class="row" style="margin-top:6px">
      <button type="button" class="btn ghost" id="amCancel" style="flex:1">Cancelar</button>
      <button type="submit" class="btn ok" style="flex:1">${esEdicion ? 'Guardar cambios' : 'Crear categoría'}</button>
    </div>
  `;

  $('#catHue').oninput = e => {
    const h = +e.target.value;
    $('#hueVal').textContent = h;
    $('#huePreview').style.background = `linear-gradient(135deg,hsl(${h} 55% 38%),hsl(${h + 30} 60% 22%))`;
  };
  $('#amCancel').onclick = () => $('#adminModal').classList.remove('on');

  $('#amForm').onsubmit = async e => {
    e.preventDefault();
    const payload = {
      nombre: $('#catNombre').value.trim(),
      area: $('#catArea').value,
      emoji: $('#catEmoji').value.trim(),
      hue: parseInt($('#catHue').value, 10) || 0,
      posicion: parseInt($('#catPosicion').value, 10) || 0
    };

    try {
      if (esEdicion) {
        await api(`/api/menu/categorias/${catObj.id}`, { method: 'PUT', body: JSON.stringify(payload) });
      } else {
        await api('/api/menu/categorias', { method: 'POST', body: JSON.stringify(payload) });
      }
      $('#adminModal').classList.remove('on');
      await Promise.all([cargarAdminMenu(), cargarMenu()]);
    } catch (err) {
      alert(err.message);
    }
  };

  $('#adminModal').classList.add('on');
}

async function desactivarCategoria(id) {
  try {
    await api(`/api/menu/categorias/${id}`, { method: 'DELETE' });
    await Promise.all([cargarAdminMenu(), cargarMenu()]);
  } catch (err) {
    if (err.status === 409) {
      const confirmarCascada = confirm(
        'Esta categoría tiene productos activos.\n¿Deseas desactivar la categoría junto con todos sus productos?'
      );
      if (!confirmarCascada) return;
      try {
        await api(`/api/menu/categorias/${id}?cascade=true`, { method: 'DELETE' });
        await Promise.all([cargarAdminMenu(), cargarMenu()]);
      } catch (err2) {
        alert(err2.message);
      }
    } else {
      alert(err.message);
    }
  }
}

async function reactivarCategoria(id) {
  try {
    await api(`/api/menu/categorias/${id}`, { method: 'PUT', body: JSON.stringify({ activo: true }) });
    await Promise.all([cargarAdminMenu(), cargarMenu()]);
  } catch (err) {
    alert(err.message);
  }
}

/* --- 2. PRODUCTOS --- */
function renderAdminProductos() {
  const catFilter = $('#adminCatFilter').value;
  const search = $('#adminProdSearch').value.trim().toLowerCase();

  let productos = ADMIN_MENU.flatMap(c =>
    (c.productos || []).map(p => ({ ...p, categoriaNombre: c.nombre, categoriaActiva: c.activo, categoriaHue: c.hue }))
  );

  if (catFilter !== 'all') {
    productos = productos.filter(p => p.categoria_id === +catFilter);
  }
  if (search) {
    productos = productos.filter(p =>
      p.nombre.toLowerCase().includes(search) || (p.descripcion || '').toLowerCase().includes(search)
    );
  }

  if (!productos.length) {
    $('#adminContent').innerHTML = '<div class="empty">No se encontraron productos con ese filtro.</div>';
    return;
  }

  $('#adminContent').innerHTML = productos.map(p => {
    const gruposTags = (p.grupos || []).map(g => `<span class="tag">${g.titulo}</span>`).join(' ');
    return `
      <div class="admin-card ${p.activo && p.categoriaActiva ? '' : 'inactive'}">
        <div class="row">
          <b>${p.nombre}</b>
          <span style="font-weight:700;color:var(--pri)">${money(p.precio)}</span>
        </div>
        <div class="row" style="font-size:13px;color:var(--mut)">
          <span>
            <span class="swatch" style="background:hsl(${p.categoriaHue} 60% 42%)"></span>
            ${p.categoriaNombre}${p.categoriaActiva ? '' : ' (Cat. inactiva)'}
          </span>
          <span class="tag ${p.activo ? 'g' : 'w'}">${p.activo ? 'Activo' : 'Inactivo'}</span>
        </div>
        ${p.descripcion ? `<small style="color:var(--mut)">${p.descripcion}</small>` : ''}
        ${gruposTags ? `<div style="display:flex;gap:4px;flex-wrap:wrap">${gruposTags}</div>` : ''}
        <div class="admin-actions">
          <button class="btn ghost sm" data-edit-prod="${p.id}">Editar</button>
          ${p.activo
            ? `<button class="btn bad sm" data-del-prod="${p.id}">Desactivar</button>`
            : `<button class="btn ok sm" data-act-prod="${p.id}">Reactivar</button>`
          }
        </div>
      </div>
    `;
  }).join('');
}

function abrirModalProducto(prodObj = null) {
  const esEdicion = Boolean(prodObj);
  const categoriasActivas = ADMIN_MENU.filter(c => c.activo);

  if (!categoriasActivas.length) {
    alert('Debes tener al menos una categoría activa para crear o editar productos.');
    return;
  }

  const catSeleccionadaId = esEdicion
    ? prodObj.categoria_id
    : ($('#adminCatFilter').value !== 'all' ? +$('#adminCatFilter').value : categoriasActivas[0].id);

  const gruposAsignadosIds = new Set((prodObj?.grupos || []).map(g => g.id));
  const gruposActivos = ADMIN_GRUPOS.filter(g => g.activo);

  $('#amTitle').textContent = esEdicion ? `Editar producto: ${prodObj.nombre}` : 'Nuevo producto';

  $('#amForm').innerHTML = `
    <div class="field">
      <label for="prodCat">Categoría *</label>
      <select id="prodCat" required>
        ${categoriasActivas.map(c => `<option value="${c.id}" ${c.id === catSeleccionadaId ? 'selected' : ''}>${c.nombre} (${AREAS_LABEL[c.area] || c.area})</option>`).join('')}
      </select>
    </div>
    <div class="field">
      <label for="prodNombre">Nombre del producto *</label>
      <input id="prodNombre" required maxlength="120" value="${esEdicion ? prodObj.nombre : ''}" placeholder="Ej. Lomo fino 300gr">
    </div>
    <div class="row">
      <div class="field" style="flex:1">
        <label for="prodPrecio">Precio (COP) *</label>
        <input id="prodPrecio" type="number" required min="0" step="100" value="${esEdicion ? prodObj.precio : ''}" placeholder="Ej. 45000">
      </div>
      <div class="field" style="flex:1">
        <label for="prodPosicion">Posición (orden)</label>
        <input id="prodPosicion" type="number" min="0" value="${esEdicion ? prodObj.posicion : 0}">
      </div>
    </div>
    <div class="field">
      <label for="prodDesc">Descripción</label>
      <textarea id="prodDesc" rows="2" maxlength="500" placeholder="Ingredientes o acompañamientos...">${esEdicion ? (prodObj.descripcion || '') : ''}</textarea>
    </div>
    <div class="field">
      <label>Grupos de opciones / modificadores</label>
      <div style="display:grid;gap:6px;padding:8px;border:1px solid var(--line);border-radius:8px;background:var(--bg)">
        ${gruposActivos.length
          ? gruposActivos.map(g => `
            <label style="display:flex;align-items:center;gap:8px;color:var(--tx);font-weight:400;cursor:pointer">
              <input type="checkbox" name="prodGrupo" value="${g.id}" ${gruposAsignadosIds.has(g.id) ? 'checked' : ''}>
              <span><b>${g.titulo}</b> <small style="color:var(--mut)">(máx. ${g.max_opciones} · ${g.opciones.length} opciones)</small></span>
            </label>
          `).join('')
          : '<small style="color:var(--mut)">No hay grupos de opciones activos.</small>'
        }
      </div>
    </div>
    <div class="row" style="margin-top:6px">
      <button type="button" class="btn ghost" id="amCancel" style="flex:1">Cancelar</button>
      <button type="submit" class="btn ok" style="flex:1">${esEdicion ? 'Guardar cambios' : 'Crear producto'}</button>
    </div>
  `;

  $('#amCancel').onclick = () => $('#adminModal').classList.remove('on');

  $('#amForm').onsubmit = async e => {
    e.preventDefault();
    const categoriaId = parseInt($('#prodCat').value, 10);
    const grupoIds = [...$('#amForm').querySelectorAll('input[name="prodGrupo"]:checked')].map(cb => +cb.value);

    const payload = {
      categoria_id: categoriaId,
      nombre: $('#prodNombre').value.trim(),
      precio: parseInt($('#prodPrecio').value, 10) || 0,
      descripcion: $('#prodDesc').value.trim(),
      posicion: parseInt($('#prodPosicion').value, 10) || 0,
      grupo_ids: grupoIds
    };

    try {
      if (esEdicion) {
        await api(`/api/menu/productos/${prodObj.id}`, { method: 'PUT', body: JSON.stringify(payload) });
      } else {
        await api(`/api/menu/categorias/${categoriaId}/productos`, { method: 'POST', body: JSON.stringify(payload) });
      }
      $('#adminModal').classList.remove('on');
      await Promise.all([cargarAdminMenu(), cargarMenu()]);
    } catch (err) {
      alert(err.message);
    }
  };

  $('#adminModal').classList.add('on');
}

async function desactivarProducto(id) {
  if (!confirm('¿Desactivar este producto del menú?')) return;
  try {
    await api(`/api/menu/productos/${id}`, { method: 'DELETE' });
    await Promise.all([cargarAdminMenu(), cargarMenu()]);
  } catch (err) {
    alert(err.message);
  }
}

async function reactivarProducto(id) {
  try {
    await api(`/api/menu/productos/${id}`, { method: 'PUT', body: JSON.stringify({ activo: true }) });
    await Promise.all([cargarAdminMenu(), cargarMenu()]);
  } catch (err) {
    alert(err.message);
  }
}

/* --- 3. GRUPOS DE OPCIONES Y OPCIONES --- */
function renderAdminGrupos() {
  if (!ADMIN_GRUPOS.length) {
    $('#adminContent').innerHTML = '<div class="empty">No hay grupos de opciones registrados.</div>';
    return;
  }

  $('#adminContent').innerHTML = ADMIN_GRUPOS.map(g => {
    const opcionesHtml = (g.opciones || []).map(o => `
      <div class="row" style="padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);opacity:${o.activo ? '1' : '.55'}">
        <span style="font-size:13px">
          ${o.nombre} <small style="color:var(--mut)">(${o.precio ? '+ ' + money(o.precio) : 'Gratis'})</small>
          ${o.activo ? '' : '<span class="tag w" style="margin-left:4px">Inactiva</span>'}
        </span>
        <span style="display:flex;gap:4px">
          <button class="btn ghost sm" data-edit-opt="${o.id}" data-grupo-id="${g.id}" style="padding:3px 7px;font-size:12px">✎</button>
          ${o.activo
            ? `<button class="btn bad sm" data-del-opt="${o.id}" style="padding:3px 7px;font-size:12px">✕</button>`
            : `<button class="btn ok sm" data-act-opt="${o.id}" style="padding:3px 7px;font-size:12px">↺</button>`
          }
        </span>
      </div>
    `).join('');

    return `
      <div class="admin-card ${g.activo ? '' : 'inactive'}">
        <div class="row">
          <b>${g.titulo}</b>
          <span class="tag ${g.activo ? 'g' : 'w'}">${g.activo ? 'Activo' : 'Inactivo'}</span>
        </div>
        <small style="color:var(--mut)">Máximo seleccionable: <b>${g.max_opciones}</b> opción(es)</small>
        <div style="display:grid;gap:6px;margin-top:4px">
          ${opcionesHtml || '<small style="color:var(--mut)">Sin opciones todavía.</small>'}
        </div>
        <div class="admin-actions">
          ${g.activo ? `<button class="btn sm" data-add-opt="${g.id}">+ Opción</button>` : ''}
          <button class="btn ghost sm" data-edit-grp="${g.id}">Editar grupo</button>
          ${g.activo
            ? `<button class="btn bad sm" data-del-grp="${g.id}">Desactivar</button>`
            : `<button class="btn ok sm" data-act-grp="${g.id}">Reactivar</button>`
          }
        </div>
      </div>
    `;
  }).join('');
}

function abrirModalGrupo(grpObj = null) {
  const esEdicion = Boolean(grpObj);
  $('#amTitle').textContent = esEdicion ? `Editar grupo: ${grpObj.titulo}` : 'Nuevo grupo de opciones';

  $('#amForm').innerHTML = `
    <div class="field">
      <label for="grpTitulo">Título del grupo *</label>
      <input id="grpTitulo" required maxlength="80" value="${esEdicion ? grpObj.titulo : ''}" placeholder="Ej. Término de carne">
    </div>
    <div class="field">
      <label for="grpMax">Máximo de opciones permitidas (1 a 20) *</label>
      <input id="grpMax" type="number" required min="1" max="20" value="${esEdicion ? grpObj.max_opciones : 1}">
    </div>
    <div class="row" style="margin-top:6px">
      <button type="button" class="btn ghost" id="amCancel" style="flex:1">Cancelar</button>
      <button type="submit" class="btn ok" style="flex:1">${esEdicion ? 'Guardar cambios' : 'Crear grupo'}</button>
    </div>
  `;

  $('#amCancel').onclick = () => $('#adminModal').classList.remove('on');

  $('#amForm').onsubmit = async e => {
    e.preventDefault();
    const payload = {
      titulo: $('#grpTitulo').value.trim(),
      max_opciones: parseInt($('#grpMax').value, 10) || 1
    };

    try {
      if (esEdicion) {
        await api(`/api/menu/grupos/${grpObj.id}`, { method: 'PUT', body: JSON.stringify(payload) });
      } else {
        await api('/api/menu/grupos', { method: 'POST', body: JSON.stringify(payload) });
      }
      $('#adminModal').classList.remove('on');
      await Promise.all([cargarAdminMenu(), cargarMenu()]);
    } catch (err) {
      alert(err.message);
    }
  };

  $('#adminModal').classList.add('on');
}

async function desactivarGrupo(id) {
  try {
    await api(`/api/menu/grupos/${id}`, { method: 'DELETE' });
    await Promise.all([cargarAdminMenu(), cargarMenu()]);
  } catch (err) {
    if (err.status === 409) {
      const ok = confirm('Este grupo está asignado a productos activos.\n¿Deseas desvincularlo de esos productos y desactivarlo?');
      if (!ok) return;
      try {
        await api(`/api/menu/grupos/${id}?desvincular=true`, { method: 'DELETE' });
        await Promise.all([cargarAdminMenu(), cargarMenu()]);
      } catch (err2) {
        alert(err2.message);
      }
    } else {
      alert(err.message);
    }
  }
}

async function reactivarGrupo(id) {
  try {
    await api(`/api/menu/grupos/${id}`, { method: 'PUT', body: JSON.stringify({ activo: true }) });
    await Promise.all([cargarAdminMenu(), cargarMenu()]);
  } catch (err) {
    alert(err.message);
  }
}

function abrirModalOpcion(grupoId, optObj = null) {
  const esEdicion = Boolean(optObj);
  const grupo = ADMIN_GRUPOS.find(g => g.id === grupoId);
  $('#amTitle').textContent = esEdicion ? `Editar opción (${grupo?.titulo || ''})` : `Nueva opción en ${grupo?.titulo || ''}`;

  $('#amForm').innerHTML = `
    <div class="field">
      <label for="optNombre">Nombre de la opción *</label>
      <input id="optNombre" required maxlength="120" value="${esEdicion ? optObj.nombre : ''}" placeholder="Ej. Término medio">
    </div>
    <div class="row">
      <div class="field" style="flex:1">
        <label for="optPrecio">Precio adicional (0 = Gratis)</label>
        <input id="optPrecio" type="number" required min="0" step="100" value="${esEdicion ? optObj.precio : 0}">
      </div>
      <div class="field" style="flex:1">
        <label for="optPosicion">Posición</label>
        <input id="optPosicion" type="number" min="0" value="${esEdicion ? optObj.posicion : (grupo?.opciones?.length || 0)}">
      </div>
    </div>
    <div class="row" style="margin-top:6px">
      <button type="button" class="btn ghost" id="amCancel" style="flex:1">Cancelar</button>
      <button type="submit" class="btn ok" style="flex:1">${esEdicion ? 'Guardar cambios' : 'Agregar opción'}</button>
    </div>
  `;

  $('#amCancel').onclick = () => $('#adminModal').classList.remove('on');

  $('#amForm').onsubmit = async e => {
    e.preventDefault();
    const payload = {
      nombre: $('#optNombre').value.trim(),
      precio: parseInt($('#optPrecio').value, 10) || 0,
      posicion: parseInt($('#optPosicion').value, 10) || 0
    };

    try {
      if (esEdicion) {
        await api(`/api/menu/opciones/${optObj.id}`, { method: 'PUT', body: JSON.stringify(payload) });
      } else {
        await api(`/api/menu/grupos/${grupoId}/opciones`, { method: 'POST', body: JSON.stringify(payload) });
      }
      $('#adminModal').classList.remove('on');
      await Promise.all([cargarAdminMenu(), cargarMenu()]);
    } catch (err) {
      alert(err.message);
    }
  };

  $('#adminModal').classList.add('on');
}

async function desactivarOpcion(id) {
  if (!confirm('¿Desactivar esta opción?')) return;
  try {
    await api(`/api/menu/opciones/${id}`, { method: 'DELETE' });
    await Promise.all([cargarAdminMenu(), cargarMenu()]);
  } catch (err) {
    alert(err.message);
  }
}

async function reactivarOpcion(id) {
  try {
    await api(`/api/menu/opciones/${id}`, { method: 'PUT', body: JSON.stringify({ activo: true }) });
    await Promise.all([cargarAdminMenu(), cargarMenu()]);
  } catch (err) {
    alert(err.message);
  }
}

/* ---------- Eventos de Administración ---------- */
$('#openAdminMenu').onclick = () => {
  adminTab = 'cats';
  $$('[data-admin-tab]').forEach(b => b.classList.toggle('on', b.dataset.adminTab === 'cats'));
  cargarAdminMenu();
  go('admin-menu');
};
$('#backToMenu').onclick = () => {
  cargarMenu();
  go('menu');
};
$('#btnAdminNew').onclick = () => {
  if (adminTab === 'cats') abrirModalCategoria(null);
  else if (adminTab === 'prods') abrirModalProducto(null);
  else abrirModalGrupo(null);
};
$('#chkInactivos').onchange = cargarAdminMenu;
$('#adminCatFilter').onchange = renderAdminProductos;
$('#adminProdSearch').oninput = renderAdminProductos;
$('#amClose').onclick = () => $('#adminModal').classList.remove('on');
$('#adminModal').onclick = e => { if (e.target.id === 'adminModal') $('#adminModal').classList.remove('on'); };

$$('[data-admin-tab]').forEach(b => b.onclick = () => {
  adminTab = b.dataset.adminTab;
  $$('[data-admin-tab]').forEach(x => x.classList.toggle('on', x === b));
  renderAdminView();
});

$('#adminContent').onclick = e => {
  // Categorías
  const editCat = e.target.closest('[data-edit-cat]');
  if (editCat) {
    const c = ADMIN_MENU.find(x => x.id === +editCat.dataset.editCat);
    if (c) abrirModalCategoria(c);
    return;
  }
  const delCat = e.target.closest('[data-del-cat]');
  if (delCat) return desactivarCategoria(+delCat.dataset.delCat);
  const actCat = e.target.closest('[data-act-cat]');
  if (actCat) return reactivarCategoria(+actCat.dataset.actCat);

  // Productos
  const editProd = e.target.closest('[data-edit-prod]');
  if (editProd) {
    const p = ADMIN_MENU.flatMap(c => c.productos || []).find(x => x.id === +editProd.dataset.editProd);
    if (p) abrirModalProducto(p);
    return;
  }
  const delProd = e.target.closest('[data-del-prod]');
  if (delProd) return desactivarProducto(+delProd.dataset.delProd);
  const actProd = e.target.closest('[data-act-prod]');
  if (actProd) return reactivarProducto(+actProd.dataset.actProd);

  // Grupos
  const addOpt = e.target.closest('[data-add-opt]');
  if (addOpt) return abrirModalOpcion(+addOpt.dataset.addOpt, null);
  const editGrp = e.target.closest('[data-edit-grp]');
  if (editGrp) {
    const g = ADMIN_GRUPOS.find(x => x.id === +editGrp.dataset.editGrp);
    if (g) abrirModalGrupo(g);
    return;
  }
  const delGrp = e.target.closest('[data-del-grp]');
  if (delGrp) return desactivarGrupo(+delGrp.dataset.delGrp);
  const actGrp = e.target.closest('[data-act-grp]');
  if (actGrp) return reactivarGrupo(+actGrp.dataset.actGrp);

  // Opciones individuales
  const editOpt = e.target.closest('[data-edit-opt]');
  if (editOpt) {
    const grpId = +editOpt.dataset.grupoId;
    const g = ADMIN_GRUPOS.find(x => x.id === grpId);
    const o = g?.opciones?.find(x => x.id === +editOpt.dataset.editOpt);
    if (o) abrirModalOpcion(grpId, o);
    return;
  }
  const delOpt = e.target.closest('[data-del-opt]');
  if (delOpt) return desactivarOpcion(+delOpt.dataset.delOpt);
  const actOpt = e.target.closest('[data-act-opt]');
  if (actOpt) return reactivarOpcion(+actOpt.dataset.actOpt);
};

/* ---------- Detalle del pedido ---------- */
function renderDetail(o, saved) {
  $('#dh').className = 'dh' + (o.paid ? ' paid' : '');
  $('#dh').innerHTML = `<span>#${o.id} · En el local · ${o.paid ? 'Pagado' : 'Pendiente'}</span><button id="dx" aria-label="Cerrar">✕</button>`;
  $('#dx').onclick = () => { saved ? (renderOrders(), go('orders')) : go('menu'); };
  $('#items').innerHTML = o.lines.length ? o.lines.map((l, i) => `<div class="line"><div>${l.qty} ${l.name}${l.opts.length ? `<small>${l.opts.join(', ')}</small>` : ''}</div>
    <div style="display:flex;align-items:center">${money(l.unit * l.qty).slice(2)}<button data-rm="${i}" aria-label="Quitar ${l.name}">✕</button></div></div>`).join('')
    : '<div class="empty">El pedido está vacío. Vuelve al menú para agregar productos.</div>';
  $('#subLbl').textContent = `Subtotal productos (${count(o)})`;
  $('#sub').textContent = total(o).toLocaleString('es-CO');
  $('#total').textContent = money(total(o));
  $('#paidTag').textContent = o.paid ? 'Pagado' : 'No pagado';
  $('#paidTag').className = 'tag ' + (o.paid ? 'g' : 'w');
  $('#accept').textContent = saved ? 'Guardar' : 'Aceptar';

  $('#items').onclick = e => { const b = e.target.closest('[data-rm]'); if (b) { o.lines.splice(+b.dataset.rm, 1); renderDetail(o, saved); } };
  $('#pay').onclick = () => { o.paid = !o.paid; renderDetail(o, saved); };
  $('#cancel').onclick = () => {
    if (!confirm('¿Cancelar este pedido?')) return;
    if (saved) orders = orders.filter(x => x !== o);
    draft = null; renderOrders(); go('orders');
  };
  $('#accept').onclick = () => {
    if (!o.lines.length) { alert('Agrega al menos un producto.'); return; }
    if (!saved) { orders.push(o); seq++; draft = null; }
    renderOrders(); go('orders');
  };
}

/* ---------- GESTIÓN DE USUARIOS (Administración) ---------- */
let ADMIN_USERS = [];

async function cargarUsuarios() {
  try {
    ADMIN_USERS = await api('/api/usuarios');
    renderUsuarios();
  } catch (e) {
    $('#usersList').innerHTML = `<div class="empty" style="color:var(--bad)">Error: ${e.message}</div>`;
  }
}

function renderUsuarios() {
  if (!ADMIN_USERS.length) {
    $('#usersList').innerHTML = '<div class="empty">No hay usuarios registrados.</div>';
    return;
  }

  $('#usersList').innerHTML = ADMIN_USERS.map(u => `
    <div class="admin-card ${u.activo ? '' : 'inactive'}">
      <div class="row">
        <div>
          <b>${u.nombre}</b>
          <small style="color:var(--mut);display:block">@${u.usuario}</small>
        </div>
        <span class="tag ${u.activo ? 'g' : 'w'}">${u.activo ? 'Activo' : 'Inactivo'}</span>
      </div>
      <div class="row" style="font-size:13px;color:var(--mut)">
        <span>Rol: <b>${ROLES_LABEL[u.rol] || u.rol}</b></span>
        <span>${u.area ? `Área: <b>${AREAS_LABEL[u.area] || u.area}</b>` : ''}</span>
      </div>
      <div class="admin-actions">
        <button class="btn ghost sm" data-edit-user="${u.id}">Editar</button>
        ${u.activo
          ? `<button class="btn bad sm" data-toggle-user="${u.id}" data-next="false">Desactivar</button>`
          : `<button class="btn ok sm" data-toggle-user="${u.id}" data-next="true">Reactivar</button>`
        }
      </div>
    </div>
  `).join('');
}

function abrirModalUsuario(userObj = null) {
  const esEdicion = Boolean(userObj);
  $('#amTitle').textContent = esEdicion ? `Editar usuario: ${userObj.nombre}` : 'Nuevo usuario';

  $('#amForm').innerHTML = `
    <div class="field">
      <label for="usrNombre">Nombre completo *</label>
      <input id="usrNombre" required maxlength="120" value="${esEdicion ? userObj.nombre : ''}" placeholder="Ej. Carlos Pérez">
    </div>
    <div class="field">
      <label for="usrLogin">Usuario (login) *</label>
      <input id="usrLogin" required minlength="3" maxlength="60" value="${esEdicion ? userObj.usuario : ''}" ${esEdicion ? 'disabled' : ''} placeholder="Ej. mesero3">
    </div>
    <div class="field">
      <label for="usrPass">${esEdicion ? 'Nueva contraseña (dejar vacío para mantener)' : 'Contraseña *'}</label>
      <input id="usrPass" type="password" ${esEdicion ? '' : 'required'} minlength="4" maxlength="100" placeholder="Mínimo 4 caracteres">
    </div>
    <div class="field">
      <label for="usrRol">Rol *</label>
      <select id="usrRol" required>
        <option value="MESERO" ${userObj?.rol === 'MESERO' ? 'selected' : ''}>Mesero</option>
        <option value="CAJERA" ${userObj?.rol === 'CAJERA' ? 'selected' : ''}>Cajera</option>
        <option value="ENCARGADO_AREA" ${userObj?.rol === 'ENCARGADO_AREA' ? 'selected' : ''}>Encargado de área</option>
        <option value="PATINADOR" ${userObj?.rol === 'PATINADOR' ? 'selected' : ''}>Patinador</option>
        <option value="ADMINISTRADOR" ${userObj?.rol === 'ADMINISTRADOR' ? 'selected' : ''}>Administrador</option>
      </select>
    </div>
    <div class="field" id="usrAreaWrap" style="display:${userObj?.rol === 'ENCARGADO_AREA' ? 'block' : 'none'}">
      <label for="usrArea">Área asignada *</label>
      <select id="usrArea">
        <option value="PARRILLA" ${userObj?.area === 'PARRILLA' ? 'selected' : ''}>Parrilla</option>
        <option value="SOPAS_ENTRADAS" ${userObj?.area === 'SOPAS_ENTRADAS' ? 'selected' : ''}>Sopas y Entradas</option>
        <option value="BEBIDAS" ${userObj?.area === 'BEBIDAS' ? 'selected' : ''}>Bebidas</option>
      </select>
    </div>
    <div class="row" style="margin-top:6px">
      <button type="button" class="btn ghost" id="amCancel" style="flex:1">Cancelar</button>
      <button type="submit" class="btn ok" style="flex:1">${esEdicion ? 'Guardar cambios' : 'Crear usuario'}</button>
    </div>
  `;

  $('#usrRol').onchange = e => {
    $('#usrAreaWrap').style.display = e.target.value === 'ENCARGADO_AREA' ? 'block' : 'none';
  };
  $('#amCancel').onclick = () => $('#adminModal').classList.remove('on');

  $('#amForm').onsubmit = async e => {
    e.preventDefault();
    const rol = $('#usrRol').value;
    const area = rol === 'ENCARGADO_AREA' ? $('#usrArea').value : null;
    const pass = $('#usrPass').value;

    try {
      if (esEdicion) {
        const payload = { nombre: $('#usrNombre').value.trim(), rol, area };
        if (pass) payload.contrasena = pass;
        await api(`/api/usuarios/${userObj.id}`, { method: 'PUT', body: JSON.stringify(payload) });
      } else {
        const payload = {
          nombre: $('#usrNombre').value.trim(),
          usuario: $('#usrLogin').value.trim(),
          contrasena: pass,
          rol,
          area,
          activo: true
        };
        await api('/api/usuarios', { method: 'POST', body: JSON.stringify(payload) });
      }
      $('#adminModal').classList.remove('on');
      await cargarUsuarios();
    } catch (err) {
      alert(err.message);
    }
  };

  $('#adminModal').classList.add('on');
}

$('#btnNewUser').onclick = () => abrirModalUsuario(null);
$('#usersList').onclick = async e => {
  const editBtn = e.target.closest('[data-edit-user]');
  if (editBtn) {
    const u = ADMIN_USERS.find(x => x.id === +editBtn.dataset.editUser);
    if (u) abrirModalUsuario(u);
    return;
  }
  const toggleBtn = e.target.closest('[data-toggle-user]');
  if (toggleBtn) {
    const id = +toggleBtn.dataset.toggleUser;
    const activo = toggleBtn.dataset.next === 'true';
    if (!activo && !confirm('¿Desactivar este usuario? No podrá iniciar sesión.')) return;
    try {
      await api(`/api/usuarios/${id}`, { method: 'PUT', body: JSON.stringify({ activo }) });
      await cargarUsuarios();
    } catch (err) {
      alert(err.message);
    }
  }
};
/* ---------- CUENTAS, CAJA, RECIBOS Y REPORTES ---------- */
let CUENTAS_API = [];

async function cargarCuentas() {
  const u = getUsuarioActual();
  if (!u || !['CAJERA', 'ADMINISTRADOR'].includes(u.rol)) return;
  const estado = $('#cajaEstadoFilter')?.value ?? 'ABIERTA';
  const qs = estado ? `?estado=${encodeURIComponent(estado)}` : '';
  try {
    CUENTAS_API = await api(`/api/cuentas${qs}`);
    renderCuentas();
  } catch (e) {
    $('#cuentasList').innerHTML = `<div class="empty" style="color:var(--bad)">Error: ${e.message}</div>`;
  }
}

function renderCuentas() {
  if (!CUENTAS_API.length) {
    $('#cuentasList').innerHTML = '<div class="empty">No hay cuentas en este filtro.</div>';
    return;
  }

  $('#cuentasList').innerHTML = CUENTAS_API.map(c => {
    const monto = c.total_cobrado ?? c.total ?? 0;
    const esAbierta = c.estado === 'ABIERTA';
    return `
      <div class="order ${esAbierta ? '' : 'paid'}">
        <div class="row">
          <b>Cuenta #${c.id} · Mesa ${c.mesa_numero}</b>
          <span>${money(monto)}</span>
        </div>
        <div class="row">
          <span>
            <span class="tag ${esAbierta ? 'w' : 'g'}">${c.estado}</span>
            ${c.enviada_caja_en ? '<span class="tag">En caja</span>' : ''}
          </span>
          <small style="color:var(--mut)">${c.pago?.numero_recibo || ''}</small>
        </div>
        <div class="row" style="margin-top:6px;gap:6px;flex-wrap:wrap">
          ${esAbierta ? `<button class="btn ok sm" data-cobrar-cuenta="${c.id}" data-total="${c.total}">Cobrar</button>` : ''}
          ${!esAbierta ? `<button class="btn ghost sm" data-recibo-cuenta="${c.id}">Ver recibo</button>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

$('#cajaEstadoFilter').onchange = () => cargarCuentas();
$('#btnRefreshCuentas').onclick = () => cargarCuentas();

$('#cuentasList').onclick = async e => {
  const btnCobrar = e.target.closest('[data-cobrar-cuenta]');
  if (btnCobrar) {
    const cuentaId = +btnCobrar.dataset.cobrarCuenta;
    const totalCuenta = +btnCobrar.dataset.total;
    $('#amTitle').textContent = `Cobrar Cuenta #${cuentaId} (Total: ${money(totalCuenta)})`;
    $('#amForm').innerHTML = `
      <div class="field">
        <label for="pagoMetodo">Método de pago</label>
        <select id="pagoMetodo">
          <option value="EFECTIVO">Efectivo</option>
          <option value="TARJETA">Tarjeta</option>
          <option value="TRANSFERENCIA">Transferencia</option>
        </select>
      </div>
      <div class="field">
        <label for="pagoValor">Valor recibido (COP)</label>
        <input id="pagoValor" type="number" min="${totalCuenta}" step="100" value="${totalCuenta}" required>
      </div>
      <div class="row" style="margin-top:6px">
        <button type="button" class="btn ghost" id="amCancel" style="flex:1">Cancelar</button>
        <button type="submit" class="btn ok" style="flex:1">Registrar pago</button>
      </div>
    `;
    $('#amCancel').onclick = () => $('#adminModal').classList.remove('on');
    $('#amForm').onsubmit = async ev => {
      ev.preventDefault();
      try {
        const rec = await api(`/api/cuentas/${cuentaId}/pagar`, {
          method: 'POST',
          body: JSON.stringify({
            metodo: $('#pagoMetodo').value,
            valor: parseInt($('#pagoValor').value, 10)
          })
        });
        $('#adminModal').classList.remove('on');
        alert(`Pago registrado · Recibo ${rec.numero_recibo} · Cambio: ${money(rec.cambio)}`);
        await Promise.all([cargarCuentas(), cargarMesas()]);
      } catch (err) {
        alert(err.message);
      }
    };
    $('#adminModal').classList.add('on');
    return;
  }

  const btnRecibo = e.target.closest('[data-recibo-cuenta]');
  if (btnRecibo) {
    const cuentaId = +btnRecibo.dataset.reciboCuenta;
    try {
      const r = await api(`/api/cuentas/${cuentaId}/recibo`);
      const detalleLineas = (r.lineas || []).map(l => `${l.cantidad}x ${l.nombre} (${money(l.subtotal)})`).join('\n');
      alert(
        `Recibo: ${r.numero_recibo}\nMesa: ${r.mesa_numero}\nMétodo: ${r.metodo}\n` +
        `Total: ${money(r.total)} · Recibido: ${money(r.valor)} · Cambio: ${money(r.cambio)}\n\n${detalleLineas}`
      );
    } catch (err) {
      alert(err.message);
    }
  }
};

function inicializarFechasReporte() {
  const hoy = new Date().toISOString().slice(0, 10);
  if ($('#repDesde') && !$('#repDesde').value) $('#repDesde').value = hoy;
  if ($('#repHasta') && !$('#repHasta').value) $('#repHasta').value = hoy;
}

async function cargarReportes() {
  inicializarFechasReporte();
  const desde = $('#repDesde')?.value;
  const hasta = $('#repHasta')?.value;
  const params = new URLSearchParams();
  if (desde) params.set('desde', desde);
  if (hasta) params.set('hasta', hasta);
  const qs = params.toString() ? `?${params.toString()}` : '';

  try {
    const [ventas, prodData] = await Promise.all([
      api(`/api/reportes/ventas${qs}`),
      api(`/api/reportes/productos${qs}&limite=10`)
    ]);

    const metodosHtml = (ventas.por_metodo || [])
      .map(m => `<div>${m.metodo}: <b>${money(m.total)}</b> (${m.cuentas})</div>`)
      .join('');
    const topHtml = (prodData.productos || [])
      .map(p => `<div>${p.cantidad}x ${p.producto} — <b>${money(p.total)}</b></div>`)
      .join('');

    $('#reportesResumen').innerHTML = `
      <div class="order paid">
        <div class="row"><b>Ventas totales</b><span>${money(ventas.total_ventas)}</span></div>
        <small style="color:var(--mut)">Cuentas pagadas: ${ventas.cuentas_pagadas} · Ticket promedio: ${money(ventas.ticket_promedio)}</small>
      </div>
      <div class="order">
        <b>Por método de pago</b>
        <div style="font-size:13px;display:grid;gap:4px">${metodosHtml || 'Sin ventas'}</div>
      </div>
      <div class="order">
        <b>Top productos vendidos</b>
        <div style="font-size:13px;display:grid;gap:4px">${topHtml || 'Sin productos'}</div>
      </div>
    `;
  } catch (e) {
    $('#reportesResumen').innerHTML = `<div class="empty" style="color:var(--bad)">Error: ${e.message}</div>`;
  }
}

$('#btnRunReportes').onclick = () => cargarReportes();

/* ---------- Navegación inferior ---------- */
$$('nav button[data-go]').forEach(b => b.onclick = () => {
  const t = b.dataset.go;
  if (t === 'orders') { renderOrders(); go('orders'); }
  else if (t === 'menu') { if (!draft) draft = { id: seq, t: Date.now(), lines: [], paid: false }; renderMenu(); go('menu'); }
  else if (t === 'users') { cargarUsuarios(); go('users'); }
  else if (t === 'sales') { cargarCuentas(); go('sales'); }
  else if (t === 'reports') { cargarReportes(); go('reports'); }
  else alert('Esta sección se conectará en el siguiente paso.');
});

/* ---------- MESAS, PEDIDOS REALES, KDS Y SSE ---------- */
let MESAS = [];
let PEDIDOS_API = [];
let COMANDAS_API = [];
let kdsEstadoFiltro = '';
let sseSource = null;

async function cargarMesas() {
  try {
    MESAS = await api('/api/mesas');
    const selDraft = $('#draftMesa');
    if (selDraft) {
      selDraft.innerHTML = MESAS.map(m =>
        `<option value="${m.numero}">Mesa ${m.numero}${m.cuenta_abierta ? ` (${money(m.total_actual)})` : ''}</option>`
      ).join('');
    }
    const selFilter = $('#orderMesaFilter');
    if (selFilter) {
      const actual = selFilter.value;
      selFilter.innerHTML = '<option value="">Todas las mesas</option>' + MESAS.map(m =>
        `<option value="${m.numero}">Mesa ${m.numero}</option>`
      ).join('');
      selFilter.value = actual;
    }
  } catch (e) {
    console.warn('No se pudieron cargar mesas:', e.message);
  }
}

async function cargarPedidosAPI() {
  const u = getUsuarioActual();
  if (!u || !['MESERO', 'ADMINISTRADOR'].includes(u.rol)) return;
  const mesa = $('#orderMesaFilter')?.value;
  const qs = mesa ? `?mesa=${encodeURIComponent(mesa)}` : '';
  try {
    PEDIDOS_API = await api(`/api/pedidos${qs}`);
    renderPedidosAPI();
  } catch (e) {
    $('#orderList').innerHTML = `<div class="empty" style="color:var(--bad)">Error: ${e.message}</div>`;
  }
}

function renderPedidosAPI() {
  const u = getUsuarioActual();
  if (!u || !['MESERO', 'ADMINISTRADOR'].includes(u.rol)) {
    $('#orderList').innerHTML = '<div class="empty">Usa el Tablero KDS para ver y gestionar comandas.</div>';
    
    return;
  }

  const pend = PEDIDOS_API.filter(p => !['PAGADO', 'CANCELADO'].includes(p.estado)).length;
  const pag = PEDIDOS_API.filter(p => p.estado === 'PAGADO').length;
  const can = PEDIDOS_API.filter(p => p.estado === 'CANCELADO').length;
  const F = [
    ['all', 'Todo', PEDIDOS_API.length],
    ['pend', 'Activos', pend],
    ['paid', 'Pagados', pag],
    ['cancel', 'Cancelados', can]
  ];
  $('#chips').innerHTML = F.map(f =>
    `<button class="chip ${filter === f[0] ? 'on' : ''}" data-f="${f[0]}">${f[1]}${f[2] ? `<i>${f[2]}</i>` : ''}</button>`
  ).join('');

  const lista = PEDIDOS_API.filter(p => {
    if (filter === 'pend') return !['PAGADO', 'CANCELADO'].includes(p.estado);
    if (filter === 'paid') return p.estado === 'PAGADO';
    if (filter === 'cancel') return p.estado === 'CANCELADO';
    return true;
  });

  $('#orderList').innerHTML = lista.length ? lista.map(p => {
    const esPagado = p.estado === 'PAGADO';
    const esCancelado = p.estado === 'CANCELADO';
    const itemsCount = (p.lineas || []).reduce((s, l) => s + l.cantidad, 0);
    return `
    
      <div class="order ${esPagado ? 'paid' : ''}" style="${esCancelado ? 'opacity:.65;border-left-color:var(--bad)' : ''}">
        <div class="row">
          <b>Pedido #${p.id} · Mesa ${p.mesa_numero}</b>
          <span>${money(p.total)}</span>
        </div>
        <div class="row">
          <span>
            <span class="tag">${p.confirmado ? 'Confirmado' : 'Borrador'}</span>
            <span class="tag ${esPagado ? 'g' : 'w'}">${p.estado}</span>
          </span>
          <small style="color:var(--mut)">${itemsCount} ítem(s) · ${p.mesero?.nombre || ''}</small>
        </div>
        <div class="row" style="margin-top:4px;gap:6px;flex-wrap:wrap">
          ${!p.confirmado && !esCancelado
            ? `<button class="btn ok sm" data-confirmar-pedido="${p.id}">Enviar a cocina</button>`
            : ''
          }
          ${p.confirmado && !esPagado && !esCancelado
            ? `<button class="btn ghost sm" data-enviar-caja="${p.cuenta_id}" data-mesa="${p.mesa_numero}">Enviar a caja</button>`
            : ''
          }
          ${!esPagado && !esCancelado
            ? `<button class="btn bad sm" data-cancelar-pedido="${p.id}">Cancelar</button>`
            : ''
          }
        </div>
        <div class="row" style="margin-top:4px;gap:6px;flex-wrap:wrap">
          ${!p.confirmado && !esCancelado
            ? `<button class="btn ok sm" data-confirmar-pedido="${p.id}">Enviar a cocina</button>`
            : ''
          }
          ${!esPagado && !esCancelado
            ? `<button class="btn bad sm" data-cancelar-pedido="${p.id}">Cancelar</button>`
            : ''
          }
        </div>
      </div>
    `;
  }).join('') : '<div class="empty">No hay pedidos para mostrar.</div>';
}

$('#orderMesaFilter').onchange = () => cargarPedidosAPI();

$('#orderList').onclick = async e => {
  const btnCaja = e.target.closest('[data-enviar-caja]');
if (btnCaja) {
  const cuentaId = +btnCaja.dataset.enviarCaja;
  const mesaNum = btnCaja.dataset.mesa;
  try {
    await api(`/api/cuentas/${cuentaId}/enviar-caja`, { method: 'POST' });
    alert(`Cuenta de la Mesa ${mesaNum} enviada a caja.`);
    await Promise.all([cargarPedidosAPI(), cargarMesas(), cargarCuentas()]);
  } catch (err) {
    alert(err.message);
  }
  return;
}
  const btnConf = e.target.closest('[data-confirmar-pedido]');
  if (btnConf) {
    try {
      await api(`/api/pedidos/${+btnConf.dataset.confirmarPedido}/confirmar`, { method: 'POST' });
      await Promise.all([cargarPedidosAPI(), cargarMesas()]);
    } catch (err) {
      alert(err.message);
    }
    return;
  }
  
  const btnCanc = e.target.closest('[data-cancelar-pedido]');
  if (btnCanc) {
    const id = +btnCanc.dataset.cancelarPedido;
    const motivo = prompt('Motivo de cancelación (opcional):') ?? '';
    try {
      await api(`/api/pedidos/${id}?motivo=${encodeURIComponent(motivo.trim())}`, { method: 'DELETE' });
      await Promise.all([cargarPedidosAPI(), cargarMesas()]);
    } catch (err) {
      alert(err.message);
    }
  }
};

$('#toOrder').onclick = async () => {
  if (!draft || !draft.lines.length) {
    alert('Agrega al menos un producto.');
    return;
  }
  const mesaNumero = +($('#draftMesa')?.value || 1);
  const lineasPayload = draft.lines.map(l => l.libre
    ? {
        nombre: l.name,
        precio_unitario: l.unit,
        cantidad: l.qty,
        observacion: l.obs || '',
        area: l.area || 'PARRILLA'
      }
    : {
        producto_id: l.producto_id,
        cantidad: l.qty,
        opcion_ids: l.opcion_ids || [],
        observacion: l.obs || ''
      }
  );

  try {
    await api('/api/pedidos', {
      method: 'POST',
      body: JSON.stringify({ mesa_numero: mesaNumero, lineas: lineasPayload })
    });
    draft = null;
    await Promise.all([cargarPedidosAPI(), cargarMesas()]);
    go('orders');
  } catch (err) {
    alert(err.message);
  }
};

async function cargarComandas() {
  const u = getUsuarioActual();
  if (!u || !['ADMINISTRADOR', 'ENCARGADO_AREA', 'PATINADOR'].includes(u.rol)) return;
  const qs = kdsEstadoFiltro ? `?estado=${encodeURIComponent(kdsEstadoFiltro)}` : '';
  try {
    COMANDAS_API = await api(`/api/comandas${qs}`);
    renderComandas();
  } catch (e) {
    $('#kdsList').innerHTML = `<div class="empty" style="color:var(--bad)">Error: ${e.message}</div>`;
  }
}

function renderComandas() {
  const u = getUsuarioActual();
  if (!COMANDAS_API.length) {
    $('#kdsList').innerHTML = '<div class="empty">No hay comandas en este estado.</div>';
    return;
  }

  $('#kdsList').innerHTML = COMANDAS_API.map(c => {
    let accionHtml = '';
    if (['ENCARGADO_AREA', 'ADMINISTRADOR'].includes(u?.rol)) {
      if (c.estado === 'PENDIENTE') {
        accionHtml = `<button class="btn sm" data-kds-estado="${c.id}" data-next="EN_PREPARACION">Iniciar preparación</button>`;
      } else if (c.estado === 'EN_PREPARACION') {
        accionHtml = `<button class="btn ok sm" data-kds-estado="${c.id}" data-next="LISTO">Marcar LISTO</button>`;
      }
    }
    if (['PATINADOR', 'ADMINISTRADOR'].includes(u?.rol) && c.estado === 'LISTO') {
      accionHtml += `<button class="btn ok sm" data-kds-entregar="${c.id}">Entregar a mesa</button>`;
    }
    if (['ENCARGADO_AREA', 'ADMINISTRADOR'].includes(u?.rol)) {
  accionHtml += `
    <button class="btn ghost sm" data-kds-imprimir="${c.id}">Reimprimir</button>
    <button class="btn ghost sm" data-kds-ticket="${c.id}">Ticket</button>
  `;
}

    return `
      <div class="order">
        <div class="row">
          <b>Comanda #${String(c.id).padStart(6, '0')} · Mesa ${c.mesa_numero}</b>
          <span class="tag">${AREAS_LABEL[c.area] || c.area}</span>
        </div>
        <div class="row">
          <span class="tag w">${c.estado}</span>
          <small style="color:var(--mut)">Pedido #${c.pedido_id}</small>
        </div>
        <div style="font-size:13px;display:grid;gap:4px;margin-top:4px">
          ${(c.lineas || []).map(l => `
            <div>
              <b>${l.cantidad}x ${l.nombre}</b>
              ${l.opciones?.length ? `<small style="color:var(--mut);display:block">Opción: ${l.opciones.join(', ')}</small>` : ''}
              ${l.observacion ? `<small style="color:var(--warn);display:block">Obs: ${l.observacion}</small>` : ''}
            </div>
          `).join('')}
        </div>
        ${accionHtml ? `<div class="row" style="margin-top:6px;gap:6px;flex-wrap:wrap">${accionHtml}</div>` : ''}
      </div>
    `;
  }).join('');
}

$('#kdsEstadoChips').onclick = e => {
  const b = e.target.closest('[data-kds-estado]');
  if (!b) return;
  kdsEstadoFiltro = b.dataset.kdsEstado;
  $$('#kdsEstadoChips .chip').forEach(x => x.classList.toggle('on', x === b));
  cargarComandas();
};

$('#btnRefreshKds').onclick = () => cargarComandas();
$('#btnOpenKds').onclick = () => { cargarComandas(); go('kds'); };

$('#kdsList').onclick = async e => {
  const btnImp = e.target.closest('[data-kds-imprimir]');
if (btnImp) {
  const id = +btnImp.dataset.kdsImprimir;
  try {
    const res = await api(`/api/comandas/${id}/imprimir`, { method: 'POST' });
    alert(`Comanda #${String(id).padStart(6, '0')} enviada a impresión${res.archivo_impresion ? ` (${res.archivo_impresion})` : ''}.`);
    await cargarComandas();
  } catch (err) {
    alert(err.message);
  }
  return;
}

const btnTkt = e.target.closest('[data-kds-ticket]');
if (btnTkt) {
  const id = +btnTkt.dataset.kdsTicket;
  try {
    const resp = await fetch(`/api/comandas/${id}/ticket`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    });
    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}));
      throw new Error(errData.detail || 'Ticket no disponible');
    }
    const texto = await resp.text();
    const blob = new Blob([texto], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `comanda-${String(id).padStart(6, '0')}.txt`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  } catch (err) {
    alert(err.message);
  }
}
  const btnEst = e.target.closest('[data-kds-estado]');
  if (btnEst) {
    try {
      await api(`/api/comandas/${+btnEst.dataset.kdsEstado}/estado`, {
        method: 'PUT',
        body: JSON.stringify({ estado: btnEst.dataset.next })
      });
      await cargarComandas();
    } catch (err) {
      alert(err.message);
    }
    return;
  }
  const btnEnt = e.target.closest('[data-kds-entregar]');
  if (btnEnt) {
    try {
      await api(`/api/comandas/${+btnEnt.dataset.kdsEntregar}/entregar`, { method: 'POST' });
      await cargarComandas();
    } catch (err) {
      alert(err.message);
    }
  }
};

async function conectarSSE() {
  cerrarSSE();
  const token = getToken();
  if (!token) return;
  try {
    const res = await api('/api/auth/eventos-token', { method: 'POST' });
    const url = `/api/eventos?token=${encodeURIComponent(res.token)}`;
    const es = new EventSource(url);
    sseSource = es;

    es.onopen = () => {
      const st = $('#sseStatus');
      if (st) { st.textContent = 'SSE: en vivo'; st.className = 'tag g'; }
    };
    es.onerror = () => {
      const st = $('#sseStatus');
      if (st) { st.textContent = 'SSE: reconectando...'; st.className = 'tag w'; }
    };

    const refrescarTodo = () => {
      cargarMesas();
      cargarPedidosAPI();
      cargarComandas();
    };
    ['pedido_creado', 'pedido_confirmado', 'pedido_cancelado', 'comanda_creada', 'comanda_estado', 'comanda_entregada', 'cuenta_enviada_caja', 'cuenta_pagada', 'mesa_actualizada']
      .forEach(ev => es.addEventListener(ev, refrescarTodo));
  } catch (e) {
    console.warn('SSE no iniciado:', e.message);
  }
}

function cerrarSSE() {
  if (sseSource) {
    sseSource.close();
    sseSource = null;
  }
}

/* ---------- Inicialización ---------- */
/* ---------- Login, rol y arranque ---------- */
async function iniciarSesionApp() {
  const nav = $('nav');
  if (nav) nav.style.display = '';
  aplicarPermisosRol();
  const u = getUsuarioActual();
  const vistaInicio = ROL_PERMISOS[u?.rol]?.inicio || 'orders';

  await cargarMesas();
  if (vistaInicio === 'orders') await cargarPedidosAPI();
  if (vistaInicio === 'kds') await cargarComandas();
  if (vistaInicio === 'sales') await cargarCuentas();
  if (u?.rol === 'ADMINISTRADOR' || u?.rol === 'MESERO') {
    await cargarMenu();
  }
  conectarSSE();
  go(vistaInicio);
}

const loginForm = $('#loginForm');
if (loginForm) {
  loginForm.onsubmit = async e => {
    e.preventDefault();
    const usuario = $('#loginUser').value.trim();
    const contrasena = $('#loginPass').value;
    const err = $('#loginErr');
    if (err) err.style.display = 'none';

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ usuario, contrasena })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || 'Credenciales inválidas');
      }

      localStorage.setItem('pdv_token', data.access_token);

      let perfil = data.usuario || null;
      if (!perfil) {
        const meRes = await fetch('/api/auth/me', {
          headers: { 'Authorization': `Bearer ${data.access_token}` }
        });
        if (meRes.ok) perfil = await meRes.json();
      }
      if (perfil) {
        localStorage.setItem('pdv_usuario', JSON.stringify(perfil));
      }

      $('#loginPass').value = '';
      await iniciarSesionApp();
    } catch (ex) {
      if (err) {
        err.textContent = ex.message;
        err.style.display = 'block';
      }
    }
  };
}

const btnLogout = $('#btnLogout');
if (btnLogout) {
  btnLogout.onclick = () => {
    mostrarLogin();
  };
}

(async function initAuth() {
  const token = localStorage.getItem('pdv_token');
  if (!token) {
    mostrarLogin();
    return;
  }
  try {
    if (!getUsuarioActual()) {
      const meRes = await fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!meRes.ok) throw new Error('Token inválido');
      localStorage.setItem('pdv_usuario', JSON.stringify(await meRes.json()));
    }
    await iniciarSesionApp();
  } catch {
    mostrarLogin();
  }
})();

setInterval(() => { if ($('#v-orders').classList.contains('on')) renderOrders(); }, 60000);