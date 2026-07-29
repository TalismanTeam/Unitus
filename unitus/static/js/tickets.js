/*
 * Unitas - Ticket Management (collaboration app)
 * -----------------------------------------------------------
 * Wires templates/ticketManagement.html to the real endpoints in
 * collaboration/views.py:
 *
 *   GET  /collaboration/tickets?type=&status=   list (own tickets)
 *   GET  /collaboration/tickets/history         full history (any status)
 *   GET  /collaboration/tickets/<id>            single ticket
 *   DELETE /collaboration/tickets/<id>          cancel (sender only, pending only)
 *   PATCH  /collaboration/tickets/<id>/respond  {action: 'approve'|'reject'}
 *
 * Depends on static/js/api.js (apiFetch) being loaded first.
 */

document.addEventListener('DOMContentLoaded', () => {
  const ticketsList = document.getElementById('ticketsList');
  if (!ticketsList) return; // not on this page

  const API_BASE = '/collaboration/tickets';

  const TYPE_LABELS = {
    COLLAB_REQUEST: 'Application',
    INVITATION: 'Invitation',
    RESIGNATION: 'Resignation',
  };

  const STATUS_LABELS = {
    PENDING_FEEDBACK: 'Pending',
    WAITING_FOR_US: 'Pending',
    CLOSED_ACCEPTED: 'Accepted',
    CLOSED_REJECTED: 'Rejected',
    CANCELLED: 'Cancelled',
  };

  const ticketTabs = document.querySelectorAll('.ticket-tab');
  const typeFilter = document.getElementById('typeFilter');

  const reviewModal = document.getElementById('reviewApplicationModal');
  const reviewSenderName = document.getElementById('reviewSenderName');
  const reviewTicketType = document.getElementById('reviewTicketType');
  const reviewProjectRole = document.getElementById('reviewProjectRole');
  const reviewMessageText = document.getElementById('reviewMessageText');
  const reviewAcceptBtn = document.getElementById('reviewAcceptBtn');
  const reviewRejectBtn = document.getElementById('reviewRejectBtn');

  const withdrawModal = document.getElementById('withdrawModal');
  const withdrawConfirmBtn = document.getElementById('withdrawConfirmBtn');

  let currentTab = 'received';
  let activeTicketId = null;

  function userLabel(user) {
    const name = `${user.first_name || ''} ${user.last_name || ''}`.trim();
    return name || user.username;
  }

  function formatDate(iso) {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  }

  async function fetchTicketsForTab(tab, type) {
    if (tab === 'history') {
      const { ok, data } = await apiFetch(`${API_BASE}/history`);
      if (!ok) return { ok, data, tickets: [] };
      let tickets = data.tickets.filter(t => t.status === 'CLOSED_REJECTED' || t.status === 'CANCELLED');
      if (type) tickets = tickets.filter(t => t.ticket_type === type);
      return { ok, data, tickets };
    }

    const statusParam = {
      received: 'pending_our_response',
      sent: 'pending_their_response',
      approved: 'closed',
    }[tab];

    const params = new URLSearchParams({ status: statusParam });
    if (type) params.set('type', type);

    const { ok, data } = await apiFetch(`${API_BASE}?${params.toString()}`);
    if (!ok) return { ok, data, tickets: [] };

    let tickets = data.tickets;
    if (tab === 'approved') {
      tickets = tickets.filter(t => t.status === 'CLOSED_ACCEPTED');
    }
    return { ok, data, tickets };
  }

  function renderTickets(tickets) {
    if (!tickets.length) {
      ticketsList.style.display = 'flex';
      ticketsList.style.alignItems = 'center';
      ticketsList.style.justifyContent = 'center';
      ticketsList.innerHTML = '<p style="color: var(--muted); font-size: 15px; margin: 0;">No tickets found in this section.</p>';
      return;
    }

    ticketsList.style.display = 'block';
    ticketsList.innerHTML = '';

    tickets.forEach(ticket => {
      const otherParty = ticket.direction === 'sent' ? ticket.receiver : ticket.sender;
      const card = document.createElement('div');
      card.style.cssText = 'background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; padding: 15px; margin-bottom: 12px;';

      let actionsHtml = '';
      if (currentTab === 'received' && ticket.status === 'PENDING_FEEDBACK') {
        actionsHtml = `<button class="review-btn" data-ticket-id="${ticket.id}" style="margin-top: 10px; padding: 8px 14px; font-size: 13px;">Review</button>`;
      } else if (currentTab === 'sent' && ticket.status === 'PENDING_FEEDBACK') {
        actionsHtml = `<button class="withdraw-btn" data-ticket-id="${ticket.id}" style="margin-top: 10px; padding: 8px 14px; font-size: 13px; background: transparent; color: #ef4444; border: 1px solid #ef4444;">Withdraw</button>`;
      }

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: start; gap: 10px; flex-wrap: wrap;">
          <div>
            <p style="margin: 0 0 4px 0; color: var(--text); font-weight: bold;">
              ${TYPE_LABELS[ticket.ticket_type] || ticket.ticket_type} — ${ticket.project ? ticket.project.title : 'Unknown project'}
            </p>
            <p style="margin: 0; color: var(--muted); font-size: 13px;">
              ${ticket.direction === 'sent' ? 'To' : 'From'}: ${userLabel(otherParty)}
              ${ticket.project_role ? ' · Role: ' + ticket.project_role.role_title : ''}
            </p>
          </div>
          <span style="font-size: 12px; color: var(--muted);">${STATUS_LABELS[ticket.status] || ticket.status} · ${formatDate(ticket.created_at)}</span>
        </div>
        ${ticket.message_text ? `<p style="margin: 10px 0 0 0; color: var(--text); font-size: 14px;">${escapeHtml(ticket.message_text)}</p>` : ''}
        ${actionsHtml}
      `;

      ticketsList.appendChild(card);
    });

    ticketsList.querySelectorAll('.review-btn').forEach(btn => {
      btn.addEventListener('click', () => openReviewModal(Number(btn.dataset.ticketId)));
    });
    ticketsList.querySelectorAll('.withdraw-btn').forEach(btn => {
      btn.addEventListener('click', () => openWithdrawModal(Number(btn.dataset.ticketId)));
    });
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  async function loadTickets() {
    const type = typeFilter && typeFilter.value ? typeFilter.value : '';
    const { ok, data, tickets } = await fetchTicketsForTab(currentTab, type);
    if (!ok) {
      ticketsList.style.display = 'flex';
      ticketsList.innerHTML = `<p style="color: #ef4444; font-size: 14px; margin: 0;">${(data && data.error) || 'Failed to load tickets.'}</p>`;
      return;
    }
    renderTickets(tickets);
  }

  // ---- Tabs ----
  ticketTabs.forEach(tab => {
    tab.addEventListener('click', function () {
      ticketTabs.forEach(t => t.classList.remove('active'));
      this.classList.add('active');
      currentTab = this.dataset.tab || 'received';
      loadTickets();
    });
  });

  // ---- Type filter ----
  if (typeFilter) {
    typeFilter.addEventListener('change', loadTickets);
  }

  // ---- Review (respond) modal ----
  function openReviewModal(ticketId) {
    activeTicketId = ticketId;
    apiFetch(`${API_BASE}/${ticketId}`).then(({ ok, data }) => {
      if (!ok) {
        alert((data && data.error) || 'Could not load ticket.');
        return;
      }
      reviewSenderName.textContent = userLabel(data.sender);
      reviewTicketType.textContent = TYPE_LABELS[data.ticket_type] || data.ticket_type;
      reviewProjectRole.textContent = `${data.project ? data.project.title : 'Unknown'}${data.project_role ? ' — ' + data.project_role.role_title : ''}`;
      reviewMessageText.textContent = data.message_text || 'No message provided.';
      openModal('reviewApplicationModal');
    });
  }

  async function respondToTicket(action) {
    if (!activeTicketId) return;
    const { ok, data } = await apiFetch(`${API_BASE}/${activeTicketId}/respond`, {
      method: 'PATCH',
      body: { action },
    });
    if (!ok) {
      alert((data && data.error) || 'Could not submit response.');
      return;
    }
    closeModal('reviewApplicationModal');
    activeTicketId = null;
    loadTickets();
  }

  if (reviewAcceptBtn) reviewAcceptBtn.addEventListener('click', () => respondToTicket('approve'));
  if (reviewRejectBtn) reviewRejectBtn.addEventListener('click', () => respondToTicket('reject'));

  // ---- Withdraw (cancel) modal ----
  function openWithdrawModal(ticketId) {
    activeTicketId = ticketId;
    openModal('withdrawModal');
  }

  async function withdrawTicket() {
    if (!activeTicketId) return;
    const { ok, data } = await apiFetch(`${API_BASE}/${activeTicketId}`, { method: 'DELETE' });
    if (!ok) {
      alert((data && data.error) || 'Could not withdraw ticket.');
      return;
    }
    closeModal('withdrawModal');
    activeTicketId = null;
    loadTickets();
  }

  if (withdrawConfirmBtn) withdrawConfirmBtn.addEventListener('click', withdrawTicket);

  // ---- Initial load ----
  loadTickets();
});
