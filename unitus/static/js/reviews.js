/*
 * Unitas - Reviews module (project_workspace.html only)
 * -----------------------------------------------------------
 * Powers the "Leave a Review" modal for successfully terminated
 * projects. Depends on apiFetch() from api.js - load api.js first.
 */

document.addEventListener('DOMContentLoaded', () => {
  const openBtn = document.getElementById('openReviewModalBtn');
  if (!openBtn) return; // not on a page with the review flow

  const dataEl = document.getElementById('reviewable-members-data');
  const projectIdEl = document.getElementById('reviewProjectId');
  const members = dataEl ? JSON.parse(dataEl.textContent) : [];
  const projectId = projectIdEl ? projectIdEl.value : null;

  const overlay = document.getElementById('reviewModalOverlay');
  const listEl = document.getElementById('reviewMembersList');
  const emptyEl = document.getElementById('reviewAllDoneMessage');

  let tagsCache = null;

  async function loadTags() {
    if (tagsCache) return tagsCache;
    const { ok, data } = await apiFetch('/reviews/tags');
    tagsCache = ok && data ? data.tags : [];
    return tagsCache;
  }

  function starMarkup(memberId) {
    let html = '<div class="star-rating" data-member-id="' + memberId + '">';
    for (let i = 1; i <= 5; i++) {
      html += '<span class="star" data-value="' + i + '">&#9733;</span>';
    }
    html += '</div>';
    return html;
  }

  function tagChipsGroupMarkup(tags, memberId) {
    const positive = tags.filter(t => t.tag_type === 'POSITIVE');
    const negative = tags.filter(t => t.tag_type === 'NEGATIVE');

    const chip = (tag) => (
      '<span class="tag-chip ' + tag.tag_type.toLowerCase() + '" ' +
      'data-tag-id="' + tag.id + '" data-member-id="' + memberId + '">' +
      tag.name + '</span>'
    );

    return `
      <div class="tag-section">
        <span class="tag-section-label positive">Positive</span>
        <div class="tag-chip-group" data-member-id="${memberId}">
          ${positive.map(chip).join('')}
        </div>
      </div>
      <div class="tag-section">
        <span class="tag-section-label negative">Negative</span>
        <div class="tag-chip-group" data-member-id="${memberId}">
          ${negative.map(chip).join('')}
        </div>
      </div>
    `;
  }

  async function renderMembers() {
    const tags = await loadTags();
    const pending = members.filter(m => !m.already_reviewed);

    if (pending.length === 0) {
      listEl.innerHTML = '';
      emptyEl.style.display = 'block';
      return;
    }
    emptyEl.style.display = 'none';

    
    listEl.innerHTML = pending.map(m => `
      <div class="review-member-card" id="review-card-${m.user_id}">
        <div class="review-member-header">
          <strong>${m.username}</strong>
          <span class="hint">${m.role_title}</span>
        </div>
        ${starMarkup(m.user_id)}
        ${tagChipsGroupMarkup(tags, m.user_id)}
        <button type="button" class="secondary-btn submit-review-btn" data-member-id="${m.user_id}">
          Submit Review
        </button>
        <div class="review-submit-status" id="review-status-${m.user_id}"></div>
      </div>
    `).join('');

    wireCardEvents();
  }

  function wireCardEvents() {
    listEl.querySelectorAll('.star-rating').forEach(group => {
      group.addEventListener('click', (e) => {
        if (!e.target.classList.contains('star')) return;
        const value = Number(e.target.dataset.value);
        group.dataset.selected = value;
        group.querySelectorAll('.star').forEach(star => {
          star.classList.toggle('filled', Number(star.dataset.value) <= value);
        });
      });
    });

    listEl.querySelectorAll('.tag-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        chip.classList.toggle('selected');
      });
    });

    listEl.querySelectorAll('.submit-review-btn').forEach(btn => {
      btn.addEventListener('click', () => handleSubmit(Number(btn.dataset.memberId)));
    });
  }

  async function handleSubmit(memberId) {
    const statusEl = document.getElementById('review-status-' + memberId);
    const starGroup = listEl.querySelector('.star-rating[data-member-id="' + memberId + '"]');
    const rating = starGroup ? Number(starGroup.dataset.selected || 0) : 0;

    if (!rating) {
      statusEl.textContent = 'Please select a star rating.';
      statusEl.style.color = '#ef4444';
      return;
    }

    const selectedTags = Array.from(
      listEl.querySelectorAll('.tag-chip.selected[data-member-id="' + memberId + '"]')
    ).map(chip => Number(chip.dataset.tagId));

    statusEl.textContent = 'Submitting...';
    statusEl.style.color = 'var(--muted)';

    const { ok, data } = await apiFetch('/reviews', {
      method: 'POST',
      body: {
        project_id: projectId,
        reviewee_id: memberId,
        rating: rating,
        tag_ids: selectedTags,
      },
    });

    if (!ok) {
      statusEl.textContent = (data && data.error) || 'Something went wrong.';
      statusEl.style.color = '#ef4444';
      return;
    }

    const member = members.find(m => m.user_id === memberId);
    if (member) member.already_reviewed = true;

    const card = document.getElementById('review-card-' + memberId);
    if (card) {
      card.classList.add('is-done');
      card.querySelector('.submit-review-btn').disabled = true;
      statusEl.textContent = 'Review submitted. Thank you!';
      statusEl.style.color = '#10b981';
    }

    if (members.every(m => m.already_reviewed)) {
      setTimeout(renderMembers, 800);
    }
  }

  openBtn.addEventListener('click', () => {
    overlay.classList.add('visible');
    renderMembers();
  });

  overlay.querySelector('.close-review-modal').addEventListener('click', () => {
    overlay.classList.remove('visible');
  });
});