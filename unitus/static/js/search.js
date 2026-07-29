/*
 * Unitus - Search & Discovery Module
 * Two independent search sections (Job Ads, Users), each with its own
 * filters, results grid, and pagination. Pure fetch()-based, no libraries.
 */

document.addEventListener('DOMContentLoaded', () => {
    const root = document.getElementById('searchPageRoot');
    if (!root) return;

    console.log('[Unitus] Search module initialized.');
    loadFilterCatalog().then((catalog) => {
        new SearchModule('ads', {
            endpoint: '/search/ads/',
            catalog,
            buildParams: buildAdsParams,
            renderCard: renderAdCard,
            requiresAuth: false,
        });

        new SearchModule('users', {
            endpoint: '/search/users/',
            catalog,
            buildParams: buildUsersParams,
            renderCard: renderUserCard,
            requiresAuth: true,
        });
    });
});

// ---------------------------------------------------------------------
// Filter catalog (skills / categories / mastery levels) — shared by both modules
// ---------------------------------------------------------------------

async function loadFilterCatalog() {
    try {
        const res = await fetch('/search/filters/');
        return await res.json();
    } catch (e) {
        console.error('[Unitus] Failed to load filter catalog', e);
        return { categories: [], mastery_levels: [] };
    }
}

// ---------------------------------------------------------------------
// Param builders (module-specific query strings)
// ---------------------------------------------------------------------

function buildAdsParams(state) {
    const params = new URLSearchParams();
    if (state.q) params.set('q', state.q);
    if (state.skill) params.set('skill', state.skill);
    else if (state.category) params.set('category', state.category);
    if (state.min_level) params.set('min_level', state.min_level);
    if (state.duration_min) params.set('duration_min', state.duration_min);
    if (state.duration_max) params.set('duration_max', state.duration_max);
    params.set('sort', state.sort || 'newest');
    params.set('page', state.page || 1);
    return params;
}

function buildUsersParams(state) {
    const params = new URLSearchParams();
    if (state.q) params.set('q', state.q);
    if (state.skill) params.set('skill', state.skill);
    else if (state.category) params.set('category', state.category);
    if (state.level) params.set('level', state.level);
    if (state.location) params.set('location', state.location);
    if (state.open_to_work) params.set('open_to_work', '1');
    params.set('sort', state.sort || 'name_asc');
    params.set('page', state.page || 1);
    return params;
}

// ---------------------------------------------------------------------
// Card renderers
// ---------------------------------------------------------------------

function renderAdCard(ad) {
    const card = document.createElement('div');
    card.className = 'result-card ad-card';

    const skillTags = ad.required_skills
        .map((s) => `<span class="skill-tag">${escapeHtml(s.skill_name)} · ${escapeHtml(s.min_required_level)}</span>`)
        .join('');

    card.innerHTML = `
        <div class="card-top">
            <h4>${escapeHtml(ad.role_title)}</h4>
            <span class="posted-time">${escapeHtml(ad.posted)}</span>
        </div>
        <p class="project-name">${escapeHtml(ad.project_title)}</p>
        <p class="short-desc">${escapeHtml(ad.project_short_description)}</p>
        <p class="role-desc">${escapeHtml(ad.role_description)}</p>
        <div class="skill-tags">${skillTags}</div>
        <div class="card-footer">
            <span class="duration">⏱ ${ad.duration_days} days</span>
            <button class="apply-btn" disabled title="Coming soon">Send Request</button>
        </div>
    `;
    // TODO: once the collaboration app's "create ticket" endpoint is
    // confirmed, wire the button above instead of leaving it disabled.
    return card;
}

function renderUserCard(user) {
    const card = document.createElement('div');
    card.className = 'result-card user-card';

    const initial = (user.username || '?').charAt(0).toUpperCase();
    const openBadge = user.is_open_to_work ? '<span class="badge-open">Open to Work</span>' : '';
    const location = user.location ? `<p class="user-location">📍 ${escapeHtml(user.location)}</p>` : '';
    const skillTags = user.skills
        .map((s) => `<span class="skill-tag">${escapeHtml(s.skill_name)} · ${escapeHtml(s.mastery_level)}</span>`)
        .join('');

    card.innerHTML = `
        <div class="user-avatar">${escapeHtml(user.avatar_icon_name ? user.avatar_icon_name.charAt(0) : initial)}</div>
        <div class="user-info">
            <div class="user-name-row">
                <strong>${escapeHtml(user.username)}</strong>
                ${openBadge}
            </div>
            <p class="user-fullname">${escapeHtml(user.first_name)} ${escapeHtml(user.last_name)}</p>
            ${location}
            <div class="skill-tags">${skillTags}</div>
            <a class="view-profile-btn" href="/profile/${user.id}/">View Profile</a>
        </div>
    `;
    // NOTE: assumes the public profile route is /profile/<id>/ — adjust
    // the href above if your actual route differs.
    return card;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str ?? '';
    return div.innerHTML;
}

// ---------------------------------------------------------------------
// Generic controller shared by both search sections
// ---------------------------------------------------------------------

class SearchModule {
    constructor(prefix, options) {
        this.prefix = prefix; // 'ads' | 'users'
        this.endpoint = options.endpoint;
        this.buildParams = options.buildParams;
        this.renderCard = options.renderCard;
        this.requiresAuth = options.requiresAuth;
        this.catalog = options.catalog;

        this.state = { page: 1 };
        this.debounceTimer = null;

        this._cacheDom();
        this._populateFilterOptions();
        this._bindEvents();
        this.search();
    }

    _el(id) {
        return document.getElementById(`${this.prefix}${id}`);
    }

    _cacheDom() {
        this.input = this._el('SearchInput');
        this.filterToggleBtn = this._el('FilterToggleBtn');
        this.filterPanel = this._el('FilterPanel');
        this.skillSelect = this._el('SkillSelect');
        this.categoryChips = this._el('CategoryChips');
        this.applyBtn = this._el('ApplyBtn');
        this.clearBtn = this._el('ClearBtn');
        this.sortSelect = this._el('SortSelect');
        this.resultsGrid = this._el('ResultsGrid');
        this.pagination = this._el('Pagination');

        // Optional, module-specific fields (may not exist for both modules)
        this.levelSelect = this._el('LevelSelect');
        this.durationMin = this._el('DurationMin');
        this.durationMax = this._el('DurationMax');
        this.locationInput = this._el('LocationInput');
        this.openToWorkCheckbox = this._el('OpenToWorkCheckbox');
    }

    _populateFilterOptions() {
        if (this.skillSelect) {
            this.skillSelect.innerHTML = '<option value="">Any skill</option>';
            this.catalog.categories.forEach((cat) => {
                const group = document.createElement('optgroup');
                group.label = cat.name;
                cat.skills.forEach((skill) => {
                    const opt = document.createElement('option');
                    opt.value = skill.id;
                    opt.textContent = skill.name;
                    group.appendChild(opt);
                });
                this.skillSelect.appendChild(group);
            });
        }

        if (this.levelSelect) {
            this.catalog.mastery_levels.forEach((lvl) => {
                const opt = document.createElement('option');
                opt.value = lvl.value;
                opt.textContent = lvl.label;
                this.levelSelect.appendChild(opt);
            });
        }

        if (this.categoryChips) {
            this.catalog.categories.forEach((cat) => {
                const chip = document.createElement('span');
                chip.className = 'chip';
                chip.textContent = cat.name;
                chip.dataset.categoryId = cat.id;
                chip.addEventListener('click', () => this._onCategoryChipClick(chip, cat.id));
                this.categoryChips.appendChild(chip);
            });
        }
    }

    _bindEvents() {
        if (this.input) {
            this.input.addEventListener('input', () => {
                clearTimeout(this.debounceTimer);
                this.debounceTimer = setTimeout(() => {
                    this.state.q = this.input.value.trim();
                    this.state.page = 1;
                    this.search();
                }, 300);
            });
        }

        if (this.filterToggleBtn && this.filterPanel) {
            this.filterToggleBtn.addEventListener('click', () => {
                this.filterPanel.classList.toggle('open');
                this.filterToggleBtn.classList.toggle('active');
            });
        }

        if (this.applyBtn) {
            this.applyBtn.addEventListener('click', () => {
                this.state.skill = this.skillSelect ? this.skillSelect.value : '';
                this.state.level = this.levelSelect ? this.levelSelect.value : '';
                this.state.min_level = this.levelSelect ? this.levelSelect.value : '';
                this.state.duration_min = this.durationMin ? this.durationMin.value : '';
                this.state.duration_max = this.durationMax ? this.durationMax.value : '';
                this.state.location = this.locationInput ? this.locationInput.value.trim() : '';
                this.state.open_to_work = this.openToWorkCheckbox ? this.openToWorkCheckbox.checked : false;
                this.state.sort = this.sortSelect ? this.sortSelect.value : '';
                this.state.category = null; // an explicit skill pick overrides a category chip
                this._clearActiveChip();
                this.state.page = 1;
                this.search();
            });
        }

        if (this.clearBtn) {
            this.clearBtn.addEventListener('click', () => {
                this.state = { page: 1 };
                if (this.input) this.input.value = '';
                if (this.skillSelect) this.skillSelect.value = '';
                if (this.levelSelect) this.levelSelect.value = '';
                if (this.durationMin) this.durationMin.value = '';
                if (this.durationMax) this.durationMax.value = '';
                if (this.locationInput) this.locationInput.value = '';
                if (this.openToWorkCheckbox) this.openToWorkCheckbox.checked = false;
                this._clearActiveChip();
                this.search();
            });
        }

        if (this.sortSelect) {
            this.sortSelect.addEventListener('change', () => {
                this.state.sort = this.sortSelect.value;
                this.search();
            });
        }
    }

    _clearActiveChip() {
        if (!this.categoryChips) return;
        this.categoryChips.querySelectorAll('.chip.active').forEach((c) => c.classList.remove('active'));
    }

    _onCategoryChipClick(chip, categoryId) {
        const wasActive = chip.classList.contains('active');
        this._clearActiveChip();

        if (wasActive) {
            this.state.category = null;
        } else {
            chip.classList.add('active');
            this.state.category = categoryId;
            if (this.skillSelect) this.skillSelect.value = ''; // category is a coarser filter than a specific skill
        }
        this.state.page = 1;
        this.search();
    }

    async search() {
        if (this.requiresAuth === false) {
            // ads search is public, nothing to check
        }

        this.resultsGrid.innerHTML = '<div class="loading-state">Loading...</div>';

        try {
            const params = this.buildParams(this.state);
            const res = await fetch(`${this.endpoint}?${params.toString()}`);

            if (res.status === 401) {
                this.resultsGrid.innerHTML = `
                    <div class="login-prompt">
                        Please <a href="/login/">log in</a> to search for users.
                    </div>`;
                this.pagination.innerHTML = '';
                return;
            }

            if (!res.ok) throw new Error(`Request failed (${res.status})`);

            const data = await res.json();
            this._renderResults(data);
        } catch (e) {
            console.error(`[Unitus] ${this.prefix} search failed`, e);
            this.resultsGrid.innerHTML = '<div class="error-state">Something went wrong. Please try again.</div>';
            this.pagination.innerHTML = '';
        }
    }

    _renderResults(data) {
        this.resultsGrid.innerHTML = '';

        if (data.results.length === 0) {
            this.resultsGrid.innerHTML = '<div class="empty-state">No results found. Try adjusting your search or filters.</div>';
            this.pagination.innerHTML = '';
            return;
        }

        data.results.forEach((item) => this.resultsGrid.appendChild(this.renderCard(item)));
        this._renderPagination(data.pagination);
    }

    _renderPagination(pagination) {
        this.pagination.innerHTML = '';
        if (pagination.num_pages <= 1) return;

        const prevBtn = document.createElement('button');
        prevBtn.textContent = '← Prev';
        prevBtn.disabled = !pagination.has_previous;
        prevBtn.addEventListener('click', () => {
            this.state.page = pagination.page - 1;
            this.search();
        });

        const info = document.createElement('span');
        info.className = 'pagination-info';
        info.textContent = `Page ${pagination.page} of ${pagination.num_pages} (${pagination.total_count} results)`;

        const nextBtn = document.createElement('button');
        nextBtn.textContent = 'Next →';
        nextBtn.disabled = !pagination.has_next;
        nextBtn.addEventListener('click', () => {
            this.state.page = pagination.page + 1;
            this.search();
        });

        this.pagination.append(prevBtn, info, nextBtn);
    }
}