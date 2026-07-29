/*
 * app/static/js/admin.js
 * ------------------------
 * All JS for the protected /admin/dashboard page. Talks only to the
 * /admin/api/* endpoints, which require an authenticated admin
 * session (see app/utils/security.py, admin_login_required) - if the
 * session has expired, any of these fetch() calls will get a 401 and
 * the page reloads to the login screen.
 */

const API_BASE = '/admin/api/customers';

const statTotal = document.getElementById('stat-total');
const statToday = document.getElementById('stat-today');

const tableBody = document.getElementById('customer-table-body');
const paginationEl = document.getElementById('pagination');
const refreshBtn = document.getElementById('refresh-btn');
const searchInput = document.getElementById('search-input');
const filterSpecialty = document.getElementById('filter-specialty');
const filterService = document.getElementById('filter-service');
const logoutBtn = document.getElementById('logout-btn');

const editModalBackdrop = document.getElementById('edit-modal-backdrop');
const editModalClose = document.getElementById('edit-modal-close');
const editForm = document.getElementById('edit-form');
const editBanner = document.getElementById('edit-banner');

let currentPage = 1;
let currentSearch = '';
let searchDebounce = null;

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

function formatDate(isoString) {
  if (!isoString) return '';
  try {
    return new Date(isoString).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  } catch (err) {
    return isoString;
  }
}

async function handleAuthFailure(res) {
  if (res.status === 401) {
    window.location.href = '/admin/login';
    return true;
  }
  return false;
}

/* ---------- Stats ---------- */

async function loadStats() {
  try {
    const res = await fetch('/admin/api/stats');
    if (await handleAuthFailure(res)) return;
    const body = await res.json();
    if (!res.ok || !body.success) throw new Error('stats failed');

    statTotal.textContent = body.data.total_customers;
    statToday.textContent = body.data.today_registrations;

    const specialties = Object.keys(body.data.by_specialty || {}).sort();
    filterSpecialty.innerHTML = '<option value="">All specialties</option>' +
      specialties.map((s) => `<option>${escapeHtml(s)}</option>`).join('');
  } catch (err) {
    statTotal.textContent = '—';
    statToday.textContent = '—';
  }
}

/* ---------- Records table ---------- */

async function loadCustomers(page = 1) {
  currentPage = page;
  tableBody.innerHTML = '<tr><td colspan="9" class="empty-row">Loading…</td></tr>';

  const params = new URLSearchParams({ page: String(page), per_page: '15' });
  if (currentSearch) params.set('search', currentSearch);
  if (filterSpecialty.value) params.set('specialty', filterSpecialty.value);
  if (filterService.value) params.set('interested_service', filterService.value);

  try {
    const res = await fetch(`${API_BASE}?${params.toString()}`);
    if (await handleAuthFailure(res)) return;
    const body = await res.json();
    if (!res.ok || !body.success) throw new Error('list failed');

    renderTable(body.data.customers);
    renderPagination(body.data.page, body.data.total_pages, body.data.total);
  } catch (err) {
    tableBody.innerHTML = '<tr><td colspan="9" class="empty-row">Could not load customer records.</td></tr>';
    paginationEl.innerHTML = '';
  }
}

function renderTable(customers) {
  if (!customers.length) {
    tableBody.innerHTML = '<tr><td colspan="9" class="empty-row">No customers match yet.</td></tr>';
    return;
  }

  tableBody.innerHTML = customers.map((c) => `
    <tr data-id="${c.customer_id}">
      <td>${c.customer_id}</td>
      <td>${escapeHtml(c.customer_name)}</td>
      <td>${escapeHtml(c.business_name)}</td>
      <td>${escapeHtml(c.specialty || '—')}</td>
      <td>${escapeHtml(c.phone_number)}</td>
      <td>${escapeHtml(c.email)}</td>
      <td>${escapeHtml(c.interested_service || '—')}</td>
      <td>${formatDate(c.created_at)}</td>
      <td>
        <button class="delete-btn edit-btn" data-id="${c.customer_id}">Edit</button>
        &nbsp;·&nbsp;
        <button class="delete-btn" data-id="${c.customer_id}" data-action="delete">Remove</button>
      </td>
    </tr>
  `).join('');
}

function renderPagination(page, totalPages, total) {
  if (!total) {
    paginationEl.innerHTML = '';
    return;
  }
  paginationEl.innerHTML = `
    <button id="prev-page" ${page <= 1 ? 'disabled' : ''}>&larr; Prev</button>
    <span>Page ${page} of ${Math.max(totalPages, 1)} · ${total} total</span>
    <button id="next-page" ${page >= totalPages ? 'disabled' : ''}>Next &rarr;</button>
  `;
  const prevBtn = document.getElementById('prev-page');
  const nextBtn = document.getElementById('next-page');
  if (prevBtn) prevBtn.addEventListener('click', () => loadCustomers(page - 1));
  if (nextBtn) nextBtn.addEventListener('click', () => loadCustomers(page + 1));
}

tableBody.addEventListener('click', async (event) => {
  const editBtn = event.target.closest('.edit-btn');
  if (editBtn) {
    openEditModal(editBtn.dataset.id);
    return;
  }
  const deleteBtn = event.target.closest('[data-action="delete"]');
  if (deleteBtn) {
    if (confirm('Remove this customer record?')) await deleteCustomer(deleteBtn.dataset.id);
  }
});

async function deleteCustomer(customerId) {
  try {
    const res = await fetch(`${API_BASE}/${customerId}`, { method: 'DELETE' });
    if (await handleAuthFailure(res)) return;
    const body = await res.json();
    if (!res.ok || !body.success) throw new Error('delete failed');
    await Promise.all([loadCustomers(currentPage), loadStats()]);
  } catch (err) {
    alert('Could not remove that customer. Please try again.');
  }
}

/* ---------- Edit modal ---------- */

async function openEditModal(customerId) {
  editBanner.className = 'banner';
  editBanner.textContent = '';
  try {
    const res = await fetch(`${API_BASE}/${customerId}`);
    if (await handleAuthFailure(res)) return;
    const body = await res.json();
    if (!res.ok || !body.success) throw new Error('fetch failed');

    const c = body.data;
    document.getElementById('edit_customer_id').value = c.customer_id;
    document.getElementById('edit_customer_name').value = c.customer_name || '';
    document.getElementById('edit_business_name').value = c.business_name || '';
    document.getElementById('edit_phone_number').value = c.phone_number || '';
    document.getElementById('edit_email').value = c.email || '';
    document.getElementById('edit_practice_type').value = c.practice_type || '';
    document.getElementById('edit_specialty').value = c.specialty || '';
    document.getElementById('edit_pain_point').value = c.pain_point || '';
    document.getElementById('edit_interested_service').value = c.interested_service || '';
    document.getElementById('edit_additional_notes').value = c.additional_notes || '';

    editModalBackdrop.hidden = false;
  } catch (err) {
    alert('Could not load that customer record.');
  }
}

function closeEditModal() {
  editModalBackdrop.hidden = true;
}
editModalClose.addEventListener('click', closeEditModal);
editModalBackdrop.addEventListener('click', (event) => {
  if (event.target === editModalBackdrop) closeEditModal();
});

editForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const customerId = document.getElementById('edit_customer_id').value;

  const payload = {
    customer_name: document.getElementById('edit_customer_name').value.trim(),
    business_name: document.getElementById('edit_business_name').value.trim(),
    phone_number: document.getElementById('edit_phone_number').value.trim(),
    email: document.getElementById('edit_email').value.trim(),
    practice_type: document.getElementById('edit_practice_type').value.trim(),
    specialty: document.getElementById('edit_specialty').value.trim(),
    pain_point: document.getElementById('edit_pain_point').value.trim(),
    interested_service: document.getElementById('edit_interested_service').value.trim(),
    additional_notes: document.getElementById('edit_additional_notes').value.trim(),
  };

  try {
    const res = await fetch(`${API_BASE}/${customerId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (await handleAuthFailure(res)) return;
    const body = await res.json();

    if (res.ok && body.success) {
      closeEditModal();
      await Promise.all([loadCustomers(currentPage), loadStats()]);
    } else if (body.errors) {
      editBanner.className = 'banner show error';
      editBanner.textContent = 'Please check the highlighted fields.';
    } else {
      editBanner.className = 'banner show error';
      editBanner.textContent = body.message || 'Could not save changes.';
    }
  } catch (err) {
    editBanner.className = 'banner show error';
    editBanner.textContent = 'Network error. Please try again.';
  }
});

/* ---------- Toolbar / logout ---------- */

refreshBtn.addEventListener('click', () => loadCustomers(currentPage));
filterSpecialty.addEventListener('change', () => loadCustomers(1));
filterService.addEventListener('change', () => loadCustomers(1));
searchInput.addEventListener('input', () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    currentSearch = searchInput.value.trim();
    loadCustomers(1);
  }, 300);
});

logoutBtn.addEventListener('click', async () => {
  await fetch('/admin/logout', { method: 'POST' });
  window.location.href = '/admin/login';
});

loadStats();
loadCustomers(1);
