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

/* ---------- Cliente API con token JWT ---------- */
async function asegurarToken() {
  let token = localStorage.getItem('pdv_token');
  if (token) return token;

  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ usuario: 'admin', contrasena: 'admin123' })
  });
  if (!res.ok) throw new Error('No se pudo autenticar con el servidor');
  const data = await res.json();
  token = data.access_token;
  localStorage.setItem('pdv_token', token);
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
    localStorage.removeItem('pdv_token');
    const nuevoToken = await asegurarToken();
    const retry = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${nuevoToken}`,
        ...(options.headers || {})
      }
    });
    if (!retry.ok) {
      const err = await retry.json().catch(() => ({ detail: retry.statusText }));
      const e = new Error(err.detail || 'Error en la petición');
      e.status = retry.status;
      throw e;
    }
    return retry.status === 204 ? null : retry.json();
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
  $$('.view').forEach(x => x.classList.toggle('on', x.id === 'v-' + v));
  const navKey = v === 'detail' ? 'orders' : (v === 'admin-menu' ? 'menu' : v);
  $$('nav button').forEach(b => b.classList.toggle('on', b.dataset.go === navKey));
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
    <div class="ph" style="background:linear-gradient(135deg,hsl(${x.m.hue} 55% 38%),hsl(${x.m.hue + 30} 60% 22%))"><span>${x.m.emoji || ''}</span>${x.p.nombre}</div>
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

  $('#mBody').innerHTML = `<div class="pinfo"><div><p>${p.descripcion || ''}</p><b style="font-size:20px">${money(p.precio)}</b></div>
    <div class="ph" style="background:linear-gradient(135deg,hsl(${m.hue} 55% 38%),hsl(${m.hue + 30} 60% 22%))"><span style="position:static;font-size:44px;margin:auto">${m.emoji || ''}</span></div></div>` +
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

/* ---------- Navegación inferior ---------- */
$$('nav button').forEach(b => b.onclick = () => {
  const t = b.dataset.go;
  if (t === 'orders') { renderOrders(); go('orders'); }
  else if (t === 'menu') { if (!draft) draft = { id: seq, t: Date.now(), lines: [], paid: false }; renderMenu(); go('menu'); }
  else alert('Esta sección se conectará más adelante.');
});

/* ---------- Inicialización ---------- */
renderOrders();
cargarMenu();
setInterval(() => { if ($('#v-orders').classList.contains('on')) renderOrders(); }, 60000);