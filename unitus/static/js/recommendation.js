/*
 * Unitas - Recommendation pages
 * -----------------------------------------------------------
 * Wires two pages to the real recommendation engine (recommendation app)
 * and to the collaboration app's ticket system:
 *
 *   templates/recommendation/recommended_projects.html
 *     GET /recommendations/ads/                 -> list of suggested job ads
 *     POST /collaboration/tickets                -> "Send Request" (application)
 *
 *   templates/recommendation/find_candidates.html
 *     GET /recommendations/candidates/<ad_id>/   -> list of suggested users
 *     POST /collaboration/tickets                -> "Send Invitation"
 *
 * Depends on static/js/api.js (apiFetch) being loaded first.
 */

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str == null ? '' : str;
  return div.innerHTML;
}

function scorePercent(score) {
  return Math.round((score || 0) * 100) + '%';
}

function userDisplayName(user) {
  const name = `${user.first_name || ''} ${user.last_name || ''}`.trim();
  return name || user.username;
}

function userInitial(user) {
  return (user.username || '?').charAt(0).toUpperCase();
}

/* ---------------------------------------------------------------------
 * Recommended Projects page
 * ------------------------------------------------------------------- */

function initRecommendedProjectsPage() {
  const list = document.getElementById('recommendedProjectsList');
  if (!list) return;

  const statusEl = document.getElementById('recommendationsStatus');
  const modal = document.getElementById('sendRequestModal');
  const targetLabel = document.getElementById('sendRequestTarget');
  const messageInput = document.getElementById('sendRequestMessage');
  const errorEl = document.getElementById('sendRequestError');
  const confirmBtn = document.getElementById('sendRequestConfirmBtn');

  let activeRec = null;

  async function loadRecommendations() {
    list.innerHTML = '<p class="hint">Loading recommendations…</p>';
    const { ok, data } = await apiFetch('/recommendations/ads/');

    if (!ok) {
      list.innerHTML = `<p style="color: #ef4444;">${escapeHtml((data && data.detail) || 'Could not load recommendations.')}</p>`;
      return;
    }

    if (!data.length) {
      list.innerHTML = '<p class="hint">No recommendations found yet — add skills to your profile for better matches.</p>';
      return;
    }

    if (statusEl) statusEl.textContent = `${data.length} project${data.length === 1 ? '' : 's'} matched to your profile.`;

    list.innerHTML = '';
    data.forEach(rec => {
      const card = document.createElement('div');
      card.className = 'rec-card';
      card.innerHTML = `
        <div class="rec-card-header">
          <div>
            <h4 style="margin: 0;">${escapeHtml(rec.role_title)}</h4>
            <p class="hint" style="margin: 4px 0 0;">${escapeHtml(rec.project_title)}</p>
          </div>
          <span class="match-score-badge">${scorePercent(rec.match_score)} match</span>
        </div>
        <p style="font-size: 14px; margin: 8px 0 14px;">${escapeHtml(rec.project_description)}</p>
        <div class="project-actions">
          <a href="/projects/jobads/${rec.ad_id}/" class="secondary-btn" style="text-decoration: none; padding: 8px 14px; border-radius: 6px; font-size: 13px;">View Advertisement</a>
          <button type="button" class="send-request-btn" data-ad-id="${rec.ad_id}">Send Request</button>
        </div>
      `;
      card.querySelector('.send-request-btn').addEventListener('click', () => openSendRequestModal(rec));
      list.appendChild(card);
    });
  }

  function openSendRequestModal(rec) {
    activeRec = rec;
    targetLabel.textContent = `${rec.role_title} — ${rec.project_title}`;
    messageInput.value = '';
    errorEl.style.display = 'none';
    openModal('sendRequestModal');
  }

  async function sendRequest() {
    if (!activeRec) return;
    errorEl.style.display = 'none';

    const { ok, data } = await apiFetch('/collaboration/tickets', {
      method: 'POST',
      body: {
        type: 'application',
        project_id: activeRec.project_id,
        project_role_id: activeRec.project_role_id,
        message_text: messageInput.value.trim() || undefined,
      },
    });

    if (!ok) {
      errorEl.textContent = (data && data.error) || 'Could not send the request.';
      errorEl.style.display = 'block';
      return;
    }

    closeModal('sendRequestModal');
    activeRec = null;
    if (statusEl) statusEl.textContent = 'Request sent! You can track it from the Tickets page.';
  }

  if (confirmBtn) confirmBtn.addEventListener('click', sendRequest);

  loadRecommendations();
}

/* ---------------------------------------------------------------------
 * Find Candidates page (PM tool)
 * ------------------------------------------------------------------- */

function initFindCandidatesPage() {
  const dataEl = document.getElementById('pmProjectsData');
  const list = document.getElementById('candidatesList');
  if (!dataEl || !list) return;

  const pmProjects = JSON.parse(dataEl.textContent || '[]');
  const projectSelect = document.getElementById('projectSelect');
  const roleSelect = document.getElementById('roleSelect');
  const findBtn = document.getElementById('findCandidatesBtn');
  const statusEl = document.getElementById('candidatesStatus');

  const modal = document.getElementById('sendInviteModal');
  const targetLabel = document.getElementById('sendInviteTarget');
  const messageInput = document.getElementById('sendInviteMessage');
  const errorEl = document.getElementById('sendInviteError');
  const confirmBtn = document.getElementById('sendInviteConfirmBtn');

  let activeInvite = null;

  function populateProjectSelect() {
    if (!projectSelect) return;
    projectSelect.innerHTML = pmProjects.map(
      p => `<option value="${p.project_id}">${escapeHtml(p.project_title)}</option>`
    ).join('');

    const requestedAdId = new URLSearchParams(window.location.search).get('ad_id');
    if (requestedAdId) {
      const owningProject = pmProjects.find(p => p.roles.some(r => String(r.ad_id) === requestedAdId));
      if (owningProject) projectSelect.value = String(owningProject.project_id);
    }

    populateRoleSelect();

    if (requestedAdId && roleSelect && Array.from(roleSelect.options).some(o => o.value === requestedAdId)) {
      roleSelect.value = requestedAdId;
      findCandidates();
    }
  }

  function populateRoleSelect() {
    if (!roleSelect) return;
    const project = pmProjects.find(p => String(p.project_id) === projectSelect.value);
    const roles = project ? project.roles : [];
    roleSelect.innerHTML = roles.map(
      r => `<option value="${r.ad_id}">${escapeHtml(r.role_title)}</option>`
    ).join('');
  }

  if (projectSelect) projectSelect.addEventListener('change', populateRoleSelect);

  async function findCandidates() {
    if (!roleSelect || !roleSelect.value) return;
    const adId = roleSelect.value;
    const project = pmProjects.find(p => String(p.project_id) === projectSelect.value);

    list.innerHTML = '<p class="hint">Searching for matching candidates…</p>';
    statusEl.textContent = '';

    const { ok, data } = await apiFetch(`/recommendations/candidates/${adId}/`);

    if (!ok) {
      list.innerHTML = `<p style="color: #ef4444;">${escapeHtml((data && data.detail) || 'Could not load candidates.')}</p>`;
      return;
    }

    if (!data.length) {
      list.innerHTML = '<p class="hint">No matching open-to-work candidates found for this role yet.</p>';
      return;
    }

    statusEl.textContent = `${data.length} candidate${data.length === 1 ? '' : 's'} found.`;

    list.innerHTML = '';
    data.forEach(rec => {
      const card = document.createElement('div');
      card.className = 'candidate-card';
      card.innerHTML = `
        <a class="candidate-identity" href="/profile/${rec.user_id}/">
          <div class="candidate-avatar">${escapeHtml((rec.full_name || rec.username || '?').trim().charAt(0).toUpperCase())}</div>
          <div>
            <div class="candidate-name">${escapeHtml(rec.full_name && rec.full_name.trim() ? rec.full_name : rec.username)}</div>
            <div class="candidate-username">@${escapeHtml(rec.username)}</div>
          </div>
        </a>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span class="match-score-badge">${scorePercent(rec.match_score)} match</span>
          <button type="button" class="send-invite-btn" data-user-id="${rec.user_id}">Send Invitation</button>
        </div>
      `;
      card.querySelector('.send-invite-btn').addEventListener('click', () => openSendInviteModal(rec, project, adId));
      list.appendChild(card);
    });
  }

  function openSendInviteModal(rec, project, adId) {
    const roleTitle = (project && project.roles.find(r => String(r.ad_id) === String(adId)) || {}).role_title || '';
    activeInvite = {
      receiver_id: rec.user_id,
      project_id: project ? project.project_id : null,
      project_role_id: project ? (project.roles.find(r => String(r.ad_id) === String(adId)) || {}).role_id : null,
    };
    targetLabel.textContent = `${rec.full_name && rec.full_name.trim() ? rec.full_name : rec.username} — ${roleTitle}`;
    messageInput.value = '';
    errorEl.style.display = 'none';
    openModal('sendInviteModal');
  }

  async function sendInvite() {
    if (!activeInvite) return;
    errorEl.style.display = 'none';

    const { ok, data } = await apiFetch('/collaboration/tickets', {
      method: 'POST',
      body: {
        type: 'invitation',
        project_id: activeInvite.project_id,
        project_role_id: activeInvite.project_role_id,
        receiver_id: activeInvite.receiver_id,
        message_text: messageInput.value.trim() || undefined,
      },
    });

    if (!ok) {
      errorEl.textContent = (data && data.error) || 'Could not send the invitation.';
      errorEl.style.display = 'block';
      return;
    }

    closeModal('sendInviteModal');
    activeInvite = null;
    statusEl.textContent = 'Invitation sent! You can track it from the Tickets page.';
  }

  if (confirmBtn) confirmBtn.addEventListener('click', sendInvite);
  if (findBtn) findBtn.addEventListener('click', findCandidates);

  populateProjectSelect();
}

document.addEventListener('DOMContentLoaded', () => {
  initRecommendedProjectsPage();
  initFindCandidatesPage();
});
