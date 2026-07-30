/*
 * Unitas - Main UI Controller
 * -----------------------------------------------------------
 * Handles UI interactions (Tabs, Modals, Form Submissions) for all modules.
 * Uses conditional checks to prevent null reference errors across different HTML files.
 */

document.addEventListener("DOMContentLoaded", () => {

  // ==========================================
  // 1. PROFILE MODULE (userprofile.html view page + profile_edit.html)
  // ==========================================
  const viewPage = document.getElementById('viewName');         // userprofile.html only
  const editPage = document.getElementById('editProfileForm');  // profile_edit.html only

  if (viewPage || editPage) {

    // ---- CSRF / fetch helper (shared by both pages) ------------------------
    function getCookie(name) {
      const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
      return match ? decodeURIComponent(match[2]) : null;
    }
    const CSRF_TOKEN = getCookie('csrftoken');

    async function apiFetch(url, options = {}) {
      const headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
      if (options.method && options.method !== 'GET') {
        headers['X-CSRFToken'] = CSRF_TOKEN;
      }
      const res = await fetch(url, Object.assign({}, options, { headers }));
      let data = null;
      try {
        data = await res.json();
      } catch (e) {
        // 204 No Content etc. has no body
      }
      if (!res.ok) {
        const detail = (data && data.detail) || `Request failed (${res.status})`;
        throw new Error(detail);
      }
      return data;
    }

    // =====================================================================
    // VIEW PAGE — userprofile.html (read-only view + Report modal)
    // =====================================================================
    if (viewPage) {
      console.log("[Unitas] Profile view module initialized.");

      // PROFILE_ID is set inline in userprofile.html: null on /profile/
      // (your own profile), or a user id on /profile/<id>/ (someone
      // else's — read-only + Report button instead of Edit).
      const isOwnProfile = typeof PROFILE_ID !== 'undefined' && PROFILE_ID === null;
      const profileUrl = isOwnProfile ? '/users/me' : `/users/${PROFILE_ID}`;

      function populateHeader(data) {
        const name = [data.first_name, data.last_name].filter(Boolean).join(' ') || data.username;
        document.getElementById('viewName').textContent = name;
        // username is always present (serialize_me and serialize_public_profile
        // both include it unconditionally — it's not gated by privacy settings).
        document.getElementById('viewUsername').textContent = data.username ? `@${data.username}` : '';
        document.getElementById('viewBio').textContent = data.about_me || 'User biography goes here...';
        document.getElementById('viewLocation').textContent = data.location
          ? `📍 ${data.location}`
          : '📍 Location not set';

        // Each of these is only present in the API response when either it's
        // your own profile (serialize_me) or the profile owner's privacy
        // settings allow it (serialize_public_profile gates it to null
        // otherwise) — so a null/undefined value means "don't show this
        // row" rather than an error.
        const GENDER_LABELS = { MALE: 'Male', FEMALE: 'Female', OTHER: 'Other', NOT_SPECIFIED: 'Not Specified' };
        function setOptionalRow(elementId, value, formatter) {
          const el = document.getElementById(elementId);
          if (value === null || value === undefined || value === '') {
            el.style.display = 'none';
            el.textContent = '';
          } else {
            el.style.display = '';
            el.textContent = formatter(value);
          }
        }
        setOptionalRow('viewGender', data.gender, (v) => `Gender: ${GENDER_LABELS[v] || v}`);
        setOptionalRow('viewBirthYear', data.birth_year, (v) => `Birth Year: ${v}`);
        setOptionalRow('viewPhone', data.phone_number, (v) => `📞 ${v}`);
        setOptionalRow('viewEmail', data.email, (v) => `✉️ ${v}`);
        setOptionalRow('viewEducation', data.education_background, (v) => `🎓 ${v}`);

        const statusEl = document.getElementById('viewStatus');
        statusEl.textContent = data.is_open_to_work ? '🟢 Open to Work' : '⚪ Not Available';

        // No work-preferences model exists yet (endpoint returns 501), so this
        // stays static until that's built.
        document.getElementById('viewWorkType').textContent = 'Preference: Not set';

        const avatarEl = document.getElementById('userAvatar');
        avatarEl.textContent = data.avatar && data.avatar.icon_name ? data.avatar.icon_name : '👤';

        const rating = isOwnProfile ? data.average_rating : data.avg_rating;
        document.getElementById('avgRatingText').textContent = rating != null ? `${rating} / 5` : '- / 5';
      }

      function applyModeVisibility() {
        const editBtn = document.getElementById('editProfileBtn');
        const reportBtn = document.getElementById('reportUserBtn');
        const startChatBtn = document.getElementById('startChatBtn');
        const editJobAdsBtn = document.getElementById('editJobAdsBtn');
        if (isOwnProfile) {
          reportBtn.style.display = 'none';     // can't report yourself; backend blocks it too
          if (startChatBtn) startChatBtn.style.display = 'none';  // element isn't rendered at all on own profile, but guard just in case
          if (editJobAdsBtn) editJobAdsBtn.style.display = '';    // only the profile owner can hide/show their own job ads
        } else {
          editBtn.style.display = 'none'; // no PATCH endpoint for anyone but yourself
          // editJobAdsBtn stays hidden (its default) on someone else's profile
        }
      }

      // ---- Job Ads (ProjectMember rows the profile belongs to) -----------
      let currentJobAds = []; // last-loaded list, reused by the Edit modal

      function renderJobAds(jobAds) {
        currentJobAds = jobAds || [];
        const container = document.getElementById('jobAdsList');
        if (!jobAds || jobAds.length === 0) {
          container.innerHTML = '<p style="color: var(--muted); font-size: 14px; margin: 0;">No job ads to show.</p>';
          return;
        }
        container.innerHTML = '';
        jobAds.forEach((ad) => {
          const row = document.createElement('div');
          row.style.cssText =
            'display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border);';
          row.innerHTML = `
            <span>${ad.role_title || 'Role'} <span style="color:var(--muted);font-size:12px;">— ${ad.project_title}</span></span>
            <span style="font-size:12px;color:var(--muted);">${ad.project_state}</span>`;
          container.appendChild(row);
        });
      }

      // ---- Job Ads Edit modal (own profile only) --------------------------
      function renderJobAdsEditList() {
        const container = document.getElementById('jobAdsEditList');
        if (!container) return;
        if (currentJobAds.length === 0) {
          container.innerHTML = '<p style="color: var(--muted); font-size: 14px;">No job ads yet.</p>';
          return;
        }
        container.innerHTML = '';
        currentJobAds.forEach((ad) => {
          const row = document.createElement('label');
          row.style.cssText =
            'display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 0;border-bottom:1px solid var(--border);cursor:pointer;';
          row.innerHTML = `
            <span>${ad.role_title || 'Role'} <span style="color:var(--muted);font-size:12px;">— ${ad.project_title}</span></span>
            <input type="checkbox" data-membership-id="${ad.membership_id}" ${ad.visible_on_profile ? 'checked' : ''} style="width:auto;">`;
          container.appendChild(row);
        });

        container.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
          cb.addEventListener('change', async () => {
            const id = cb.dataset.membershipId;
            try {
              await apiFetch(`/users/me/memberships/${id}/visibility`, {
                method: 'PATCH',
                body: JSON.stringify({ visible_on_profile: cb.checked }),
              });
              const ad = currentJobAds.find((a) => String(a.membership_id) === id);
              if (ad) ad.visible_on_profile = cb.checked;
            } catch (e) {
              alert(e.message);
              cb.checked = !cb.checked; // revert on failure
            }
          });
        });
      }

      window.openJobAdsModal = function () {
        renderJobAdsEditList();
        document.getElementById('jobAdsModal').style.display = 'flex';
      };

      // ---- Skills (view + remove only; adding lives on the edit page) ------
      function renderSkills(skills) {
        const container = document.getElementById('skillsList');
        if (!skills || skills.length === 0) {
          container.innerHTML = '<p style="color: var(--muted); font-size: 14px; margin: 0;">No skills added yet.</p>';
          return;
        }
        container.innerHTML = '';
        skills.forEach((s) => {
          const row = document.createElement('div');
          row.style.cssText =
            'display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border);';
          row.innerHTML = `
            <span>${s.skill_name} <span style="color:var(--muted);font-size:12px;">(${s.category_name})</span></span>
            <span style="display:flex;align-items:center;gap:8px;">
              <span style="font-size:13px;color:var(--accent);">${s.mastery_level}</span>
              ${isOwnProfile ? `<button data-skill-id="${s.id}" class="removeSkillBtn" style="background:transparent;border:1px solid #ef4444;color:#ef4444;padding:2px 8px;font-size:12px;">Remove</button>` : ''}
            </span>`;
          container.appendChild(row);
        });

        if (isOwnProfile) {
          container.querySelectorAll('.removeSkillBtn').forEach((btn) => {
            btn.addEventListener('click', async () => {
              try {
                await apiFetch(`/users/me/skills/${btn.dataset.skillId}`, { method: 'DELETE' });
                loadProfile();
              } catch (e) {
                alert(e.message);
              }
            });
          });
        }
      }

async function loadHonors(userId) {
  const container = document.getElementById('honorsList');
  if (!container) return;
  
  console.log("[Unitas Debug] Fetching badges for userId:", userId);
  
  try {
  
    const data = await apiFetch(`/users/${userId}/badges/`);
    console.log("[Unitas Debug] Badges API response received:", data);
    
    renderHonors(data);
  } catch (e) {
    container.innerHTML = '<p style="color: var(--muted); font-size: 13px; margin: 0;">Could not load honors.</p>';
    console.error("[Unitas Debug] Error in loadHonors:", e);
  }
}

function renderHonors(data) {
  const container = document.getElementById('honorsList');
  
  
  let badges = [];
  if (Array.isArray(data)) {
    badges = data;
  } else if (data && Array.isArray(data.badges)) {
    badges = data.badges;
  } else if (data && data.results && Array.isArray(data.results)) {
    badges = data.results; 
  }

  if (!badges || badges.length === 0) {
    container.innerHTML = '<p style="color: var(--muted); font-size: 14px; margin: 0;">No honors unlocked yet.</p>';
    return;
  }
  
  container.innerHTML = '';
  badges.forEach((b) => {
    const chip = document.createElement('span');
    chip.style.cssText =
      'display:inline-flex; align-items:center; gap:6px; background:rgba(16,185,129,0.12); ' +
      'color:#10b981; border:1px solid #10b981; padding:6px 14px; border-radius:20px; ' +
      'font-size:13px; font-weight:600; margin:0 8px 8px 0;';
    
    // 
    const tagName = b.tag_name || (b.tag && b.tag.name) || (b.name) || 'Honor';
    
    chip.textContent = `🏅 ${tagName}`;
    container.appendChild(chip);
  });
}

      // ---- Report modal (other users' profiles only) --------------------------
      async function handleReportSubmit(event) {
        event.preventDefault();
        const reason = document.querySelector('input[name="reportReason"]:checked').value;
        const description = document.getElementById('reportDescription').value;

        // Radio values are INACTIVITY / INSULTING / FAKE_PROJECT / OTHER,
        // matching moderation.models.Report.Reason exactly.
        try {
          await apiFetch(`/users/${PROFILE_ID}/report`, {
            method: 'POST',
            body: JSON.stringify({ reason, description }),
          });
          alert('Report submitted successfully.');
          closeReportModal();
        } catch (e) {
          alert(e.message);
        }
      }

      async function loadProfile() {
        try {
          const data = await apiFetch(profileUrl);
          populateHeader(data);
          renderSkills(data.skills);
          renderJobAds(data.job_ads);
          loadHonors(data.id);
        } catch (e) {
          document.getElementById('viewName').textContent = 'Unable to load profile';
          console.error(e);
        }
      }

      // ---- Invite to Project modal (other users' profiles only) ----------
      // Button/modal only exist in the DOM when profile_id is set (i.e.
      // never on your own profile — see the {% if profile_id %} block in
      // userprofile.html), so this whole block is a no-op on isOwnProfile.
      const inviteBtn = document.getElementById('inviteToProjectBtn');
      if (inviteBtn) {
        const inviteForm = document.getElementById('inviteForm');
        const loadingMsg = document.getElementById('inviteLoadingMsg');
        const emptyMsg = document.getElementById('inviteEmptyMsg');
        const closeOnlyBtn = document.getElementById('inviteCloseOnlyBtn');
        const projectSelect = document.getElementById('inviteProjectSelect');
        const roleSelect = document.getElementById('inviteRoleSelect');
        const submitBtn = document.getElementById('inviteSubmitBtn');
        const errorEl = document.getElementById('inviteError');
        let myRecruitingProjects = [];

        function populateRoleSelect(projectId) {
          const project = myRecruitingProjects.find((p) => p.id === Number(projectId));
          roleSelect.innerHTML = '';
          (project ? project.roles : []).forEach((r) => {
            const opt = document.createElement('option');
            opt.value = r.id;
            opt.textContent = r.role_title;
            roleSelect.appendChild(opt);
          });
        }

        async function loadMyRecruitingProjects() {
          loadingMsg.style.display = '';
          emptyMsg.style.display = 'none';
          inviteForm.style.display = 'none';
          closeOnlyBtn.style.display = 'none';
          errorEl.style.display = 'none';

          try {
            // Only projects where the viewer is PM AND currently RECRUITING
            // are returned — enforced server-side by /projects/mine/recruiting/.
            const data = await apiFetch('/projects/mine/recruiting/');
            myRecruitingProjects = data.projects || [];

            loadingMsg.style.display = 'none';

            if (myRecruitingProjects.length === 0) {
              emptyMsg.style.display = '';
              closeOnlyBtn.style.display = '';
              return;
            }

            projectSelect.innerHTML = '';
            myRecruitingProjects.forEach((p) => {
              const opt = document.createElement('option');
              opt.value = p.id;
              opt.textContent = p.title;
              projectSelect.appendChild(opt);
            });
            populateRoleSelect(projectSelect.value);

            inviteForm.style.display = '';
          } catch (e) {
            loadingMsg.style.display = 'none';
            emptyMsg.textContent = 'Could not load your projects. Please try again.';
            emptyMsg.style.display = '';
            closeOnlyBtn.style.display = '';
            console.error(e);
          }
        }

        projectSelect.addEventListener('change', () => populateRoleSelect(projectSelect.value));
        inviteBtn.addEventListener('click', loadMyRecruitingProjects);

        inviteForm.addEventListener('submit', async (event) => {
          event.preventDefault();
          errorEl.style.display = 'none';
          submitBtn.disabled = true;
          try {
            await apiFetch('/collaboration/tickets', {
              method: 'POST',
              body: JSON.stringify({
                type: 'invitation',
                project_id: Number(projectSelect.value),
                project_role_id: Number(roleSelect.value),
                receiver_id: PROFILE_ID,
                message_text: document.getElementById('inviteMessage').value || null,
              }),
            });
            closeInviteModal();
            alert('Invitation sent.');
            inviteForm.reset();
          } catch (e) {
            errorEl.textContent = e.message;
            errorEl.style.display = '';
          } finally {
            submitBtn.disabled = false;
          }
        });
      }

      applyModeVisibility();
      loadProfile();
      if (!isOwnProfile) {
        document.getElementById('reportForm').addEventListener('submit', handleReportSubmit);
      }
    }

    // =====================================================================
    // EDIT PAGE — profile_edit.html (always your own profile)
    // =====================================================================
    if (editPage) {
      console.log("[Unitas] Profile edit module initialized.");

      // ---- Skill catalog (categories + search) ------------------------------
      let skillSearchResults = []; // last search results for the selected category/query

      async function loadSkillCategories() {
        const select = document.getElementById('skillCategorySelect');
        try {
          const categories = await apiFetch('/skills/categories/');
          categories.forEach((c) => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.category_name;
            opt.style.background = 'var(--surface)';
            select.appendChild(opt);
          });
        } catch (e) {
          console.error('Could not load skill categories', e);
        }
      }

      let searchDebounceTimer = null;
      function scheduleSkillSearch() {
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(searchSkills, 250);
      }

      async function searchSkills() {
        const categoryId = document.getElementById('skillCategorySelect').value;
        const query = document.getElementById('skillNameInput').value.trim();
        if (!categoryId) return;

        const params = new URLSearchParams({ category: categoryId });
        if (query) params.set('q', query);

        try {
          skillSearchResults = await apiFetch(`/skills/?${params.toString()}`);
          const datalist = document.getElementById('skillNameOptions');
          datalist.innerHTML = '';
          skillSearchResults.forEach((s) => {
            const opt = document.createElement('option');
            opt.value = s.name;
            datalist.appendChild(opt);
          });
        } catch (e) {
          console.error('Skill search failed', e);
        }
      }

      async function handleAddSkill() {
        const categoryId = document.getElementById('skillCategorySelect').value;
        const nameInput = document.getElementById('skillNameInput');
        const levelSelect = document.getElementById('skillLevelSelect');
        const skillName = nameInput.value.trim();
        // levelSelect.value is now the enum value (BEGINNER/INTERMEDIATE/...)
        // set via the option `value` attributes, matching skills.choices.MasteryLevel.
        const masteryLevel = levelSelect.value;

        if (!categoryId) {
          alert('Pick a category first.');
          return;
        }
        if (!skillName || !masteryLevel) {
          alert('Enter a skill name and pick a proficiency level.');
          return;
        }

        try {
          // Match against the catalog first (case-insensitive) so we reuse an
          // existing Skill row instead of creating a duplicate.
          const existing = skillSearchResults.find(
            (s) => s.name.toLowerCase() === skillName.toLowerCase() && String(s.category) === String(categoryId)
          );

          let skillId;
          if (existing) {
            skillId = existing.id;
          } else {
            const created = await apiFetch('/skills/custom/', {
              method: 'POST',
              body: JSON.stringify({ category: categoryId, name: skillName }),
            });
            skillId = created.id;
          }

          await apiFetch('/users/me/skills', {
            method: 'POST',
            body: JSON.stringify({ skill: skillId, mastery_level: masteryLevel }),
          });

          nameInput.value = '';
          levelSelect.selectedIndex = 0;
          alert('Skill added.');
        } catch (e) {
          alert(e.message);
        }
      }

      // ---- Avatar ------------------------------------------------------------
      let currentAvatarId = null;
      let selectedAvatarId = null;

      async function loadAvatarOptions() {
        const container = document.getElementById('avatarOptions');
        try {
          const avatars = await apiFetch('/users/me/avatar-options');
          container.innerHTML = '';
          avatars.forEach((a) => {
            const opt = document.createElement('span');
            opt.className = 'avatar-option' + (a.id === currentAvatarId ? ' selected' : '');
            opt.textContent = a.icon_name || '👤';
            opt.dataset.avatarId = a.id;
            opt.addEventListener('click', () => {
              selectedAvatarId = a.id;
              container.querySelectorAll('.avatar-option').forEach((el) => el.classList.remove('selected'));
              opt.classList.add('selected');
            });
            container.appendChild(opt);
          });
        } catch (e) {
          container.innerHTML = '<span style="color:#ef4444;font-size:13px;">Could not load avatar options.</span>';
        }
      }

      // ---- Prefill form from the logged-in user's own data --------------------
      function prefillEditForm(data) {
        document.getElementById('usernameInput').value = data.username || '';
        document.getElementById('firstNameInput').value = data.first_name || '';
        document.getElementById('lastNameInput').value = data.last_name || '';
        document.getElementById('bioInput').value = data.about_me || '';
        document.getElementById('locationInput').value = data.location || '';
        document.getElementById('genderInput').value = data.gender || 'NOT_SPECIFIED';
        document.getElementById('birthYearInput').value = data.birth_year || '';
        document.getElementById('phoneNumberInput').value = data.phone_number || '';
        document.getElementById('educationInput').value = data.education_background || '';
        document.getElementById('openToWorkCheckbox').checked = !!data.is_open_to_work;
        currentAvatarId = data.avatar ? data.avatar.id : null;
        selectedAvatarId = currentAvatarId;
      }

      function prefillPrivacyForm(privacy) {
        document.getElementById('showGenderCheckbox').checked = !!(privacy && privacy.show_gender);
        document.getElementById('showBirthYearCheckbox').checked = !!(privacy && privacy.show_birth_year);
        document.getElementById('showPhoneCheckbox').checked = !!(privacy && privacy.show_phone);
        document.getElementById('showEmailCheckbox').checked = !!(privacy && privacy.show_email);
        document.getElementById('showLocationCheckbox').checked = !!(privacy && privacy.show_location);
        document.getElementById('showEducationCheckbox').checked = !!(privacy && privacy.show_education_background);
      }

      async function loadOwnProfile() {
        try {
          const data = await apiFetch('/users/me');
          prefillEditForm(data);
          // serialize_me already embeds privacy_settings, so this doesn't
          // need a second round trip to /users/me/privacy-settings.
          prefillPrivacyForm(data.privacy_settings);
        } catch (e) {
          console.error('Could not load profile for editing', e);
        }
      }

      // Mirrors the server-side checks in accounts.views.me_view so the
      // person gets instant feedback instead of a round trip for something
      // we can already tell is wrong.
      const PHONE_RE = /^\+?[0-9]{7,15}$/;
      const USERNAME_RE = /^[A-Za-z0-9_.-]{3,50}$/;

      function validateEditForm() {
        const usernameEl = document.getElementById('usernameInput');
        const usernameError = document.getElementById('usernameError');
        const birthYearEl = document.getElementById('birthYearInput');
        const birthYearError = document.getElementById('birthYearError');
        const phoneEl = document.getElementById('phoneNumberInput');
        const phoneError = document.getElementById('phoneNumberError');
        let valid = true;

        usernameError.style.display = 'none';
        birthYearError.style.display = 'none';
        phoneError.style.display = 'none';

        const usernameRaw = usernameEl.value.trim();
        if (!usernameRaw) {
          usernameError.textContent = 'Username is required.';
          usernameError.style.display = '';
          valid = false;
        } else if (!USERNAME_RE.test(usernameRaw)) {
          usernameError.textContent =
            'Username must be 3-50 characters: letters, numbers, underscores, periods, or hyphens only.';
          usernameError.style.display = '';
          valid = false;
        }

        const birthYearRaw = birthYearEl.value.trim();
        if (birthYearRaw) {
          const year = Number(birthYearRaw);
          const currentYear = new Date().getFullYear();
          if (!Number.isInteger(year) || year < 1900 || year > currentYear) {
            birthYearError.textContent = `Enter a birth year between 1900 and ${currentYear}.`;
            birthYearError.style.display = '';
            valid = false;
          }
        }

        const phoneRaw = phoneEl.value.trim();
        if (phoneRaw && !PHONE_RE.test(phoneRaw)) {
          phoneError.textContent = "Enter 7-15 digits, optionally starting with '+'.";
          phoneError.style.display = '';
          valid = false;
        }

        return valid;
      }

      async function handleProfileSave(event) {
        event.preventDefault();
        const statusEl = document.getElementById('editProfileStatus');

        if (!validateEditForm()) {
          statusEl.textContent = 'Please fix the highlighted fields.';
          statusEl.style.color = '#ef4444';
          return;
        }

        statusEl.textContent = 'Saving...';
        statusEl.style.color = 'var(--muted)';

        const birthYearRaw = document.getElementById('birthYearInput').value.trim();
        const phoneRaw = document.getElementById('phoneNumberInput').value.trim();

        const body = {
          username: document.getElementById('usernameInput').value.trim(),
          first_name: document.getElementById('firstNameInput').value,
          last_name: document.getElementById('lastNameInput').value,
          about_me: document.getElementById('bioInput').value,
          location: document.getElementById('locationInput').value,
          gender: document.getElementById('genderInput').value,
          phone_number: phoneRaw || null,
          education_background: document.getElementById('educationInput').value,
        };
        // birth_year is required (non-nullable) on the model, so only send
        // it when the field actually has a value — leaving it out of the
        // PATCH body keeps whatever's already saved instead of trying (and
        // failing at the DB level) to null it out.
        if (birthYearRaw) {
          body.birth_year = Number(birthYearRaw);
        }

        const privacyBody = {
          show_gender: document.getElementById('showGenderCheckbox').checked,
          show_birth_year: document.getElementById('showBirthYearCheckbox').checked,
          show_phone: document.getElementById('showPhoneCheckbox').checked,
          show_email: document.getElementById('showEmailCheckbox').checked,
          show_location: document.getElementById('showLocationCheckbox').checked,
          show_education_background: document.getElementById('showEducationCheckbox').checked,
        };

        try {
          await apiFetch('/users/me', { method: 'PATCH', body: JSON.stringify(body) });

          await apiFetch('/users/me/privacy-settings', {
            method: 'PATCH',
            body: JSON.stringify(privacyBody),
          });

          const openToWork = document.getElementById('openToWorkCheckbox').checked;
          await apiFetch('/users/me/open-to-work', {
            method: 'PATCH',
            body: JSON.stringify({ is_open_to_work: openToWork }),
          });

          if (selectedAvatarId !== currentAvatarId) {
            await apiFetch('/users/me/avatar', {
              method: 'PATCH',
              body: JSON.stringify({ avatar_icon: selectedAvatarId }),
            });
          }

          statusEl.textContent = 'Saved. Returning to your profile...';
          statusEl.style.color = '#22c55e';

          // Give the "Saved." message a beat to be seen, then go back to the
          // profile page. PROFILE_REDIRECT_URL is set inline in profile_edit.html.
          setTimeout(() => {
            window.location.href =
              typeof PROFILE_REDIRECT_URL !== 'undefined' ? PROFILE_REDIRECT_URL : '/profile/';
          }, 600);
        } catch (e) {
          statusEl.textContent = e.message;
          statusEl.style.color = '#ef4444';
        }
      }

      // ---- Change password ---------------------------------------------------
      async function handlePasswordChange(event) {
        event.preventDefault();

        const oldPasswordEl = document.getElementById('oldPasswordInput');
        const newPasswordEl = document.getElementById('newPasswordInput');
        const confirmPasswordEl = document.getElementById('confirmPasswordInput');
        const passwordError = document.getElementById('passwordError');
        const statusEl = document.getElementById('changePasswordStatus');

        passwordError.style.display = 'none';
        statusEl.textContent = '';

        const oldPassword = oldPasswordEl.value;
        const newPassword = newPasswordEl.value;
        const confirmPassword = confirmPasswordEl.value;

        if (!oldPassword || !newPassword || !confirmPassword) {
          passwordError.textContent = 'Fill in all three password fields.';
          passwordError.style.display = '';
          return;
        }
        if (newPassword !== confirmPassword) {
          passwordError.textContent = 'New password and repeat password do not match.';
          passwordError.style.display = '';
          return;
        }
        if (newPassword === oldPassword) {
          passwordError.textContent = 'New password must be different from the old password.';
          passwordError.style.display = '';
          return;
        }

        statusEl.textContent = 'Saving...';
        statusEl.style.color = 'var(--muted)';

        try {
          await apiFetch('/users/me/password', {
            method: 'PATCH',
            body: JSON.stringify({
              old_password: oldPassword,
              new_password: newPassword,
              confirm_password: confirmPassword,
            }),
          });
          statusEl.textContent = 'Password updated.';
          statusEl.style.color = '#22c55e';
          oldPasswordEl.value = '';
          newPasswordEl.value = '';
          confirmPasswordEl.value = '';
        } catch (e) {
          statusEl.textContent = e.message;
          statusEl.style.color = '#ef4444';
        }
      }

      // ---- Skill picker wiring --------------------------------------------
      function setupSkillPicker() {
        const categorySelect = document.getElementById('skillCategorySelect');
        const nameInput = document.getElementById('skillNameInput');

        categorySelect.addEventListener('change', () => {
          nameInput.disabled = !categorySelect.value;
          nameInput.value = '';
          skillSearchResults = [];
          document.getElementById('skillNameOptions').innerHTML = '';
          if (categorySelect.value) searchSkills();
        });

        nameInput.addEventListener('input', scheduleSkillSearch);
      }

      loadOwnProfile();
      loadAvatarOptions();
      loadSkillCategories();
      setupSkillPicker();
      document.getElementById('addSkillBtn').addEventListener('click', handleAddSkill);
      document.getElementById('editProfileForm').addEventListener('submit', handleProfileSave);
      document.getElementById('changePasswordForm').addEventListener('submit', handlePasswordChange);
    }
  }

// ==========================================
  // 2. CHAT MODULE (WebSockets & Read Receipts) ------> moved to chat.js
  // ==========================================
 
  // ==========================================
  // 3. TICKET MANAGEMENT MODULE
  // ==========================================
  const ticketsList = document.getElementById('ticketsList');
  if (ticketsList) {
    console.log("[Unitas] Tickets module initialized.");

    // Handle Ticket Tabs Switching
    const ticketTabs = document.querySelectorAll('.ticket-tab');
    ticketTabs.forEach(tab => {
      tab.addEventListener('click', function() {
        ticketTabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        // TODO: Filter tickets list based on selected tab
      });
    });
  }

  // ==========================================
  // 4. SEARCH & DISCOVERY MODULE              --------> moved to search.js
  // ==========================================
 

  // ==========================================
  // 5. NOTIFICATIONS MODULE
  // ==========================================
  const notificationsList = document.getElementById('notificationsList');
  if (notificationsList) {
    console.log("[Unitas] Notifications module initialized.");

    // Handle Notification Tabs Switching
    const notifTabs = document.querySelectorAll('.notification-tab');
    notifTabs.forEach(tab => {
      tab.addEventListener('click', function() {
        notifTabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        // TODO: Filter notifications (All/Unread/Read)
      });
    });
  }

  // ==========================================
  // 6. MATCHMAKING & RECOMMENDATIONS MODULE
  // ==========================================
  const recommendationsList = document.getElementById('recommendationsList');
  if (recommendationsList) {
    console.log("[Unitas] Matchmaking module initialized.");

    // Handle Match Tabs Switching
    const matchTabs = document.querySelectorAll('.match-tab');
    matchTabs.forEach(tab => {
      tab.addEventListener('click', function() {
        matchTabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        // TODO: Fetch new recommendations based on tab
      });
    });

    // Handle Preferences Form Submission
    const preferencesForm = document.getElementById('preferencesForm');
    if (preferencesForm) {
      preferencesForm.addEventListener('submit', (e) => {
        e.preventDefault();
        alert('Recommendation preferences saved!');
      });
    }
  }

  // ==========================================
  // 7. PROJECT WORKSPACE MODULE (project_workspace.html)
  // ==========================================
  // These four modals are rendered conditionally (is_pm / is_member), so
  // detect the module by whichever of them actually exists on the page.
  const deleteProjectModal = document.getElementById('deleteProjectModal');
  const removeMemberModal = document.getElementById('removeMemberModal');
  const deleteRoleModal = document.getElementById('deleteRoleModal');
  const resignModal = document.getElementById('resignModal');

  if (deleteProjectModal || removeMemberModal || deleteRoleModal || resignModal) {
    console.log("[Unitas] Project workspace module initialized.");

    // Generic open/close — reused by every modal's Cancel button and by the
    // "click outside to close" handler registered further down this file.
    window.openModal = function (modalId) {
      const modal = document.getElementById(modalId);
      if (modal) modal.classList.add('visible');
    };
    window.closeModal = function (modalId) {
      const modal = document.getElementById(modalId);
      if (modal) modal.classList.remove('visible');
    };

    // Remove Member modal is one shared markup block reused for every row;
    // point its <form> at the right URL and fill in the member's name
    // before showing it.
    window.openRemoveMemberModal = function (button) {
      const form = document.getElementById('removeMemberForm');
      const nameEl = document.getElementById('removeMemberName');
      if (form) form.action = button.dataset.removeMemberUrl;
      if (nameEl) nameEl.textContent = button.dataset.memberName;
      openModal('removeMemberModal');
    };

    // Same idea for Delete Role.
    window.openDeleteRoleModal = function (button) {
      const form = document.getElementById('deleteRoleForm');
      const nameEl = document.getElementById('deleteRoleName');
      if (form) form.action = button.dataset.deleteRoleUrl;
      if (nameEl) nameEl.textContent = button.dataset.roleTitle;
      openModal('deleteRoleModal');
    };

    // Delete Project and Resign each have their own fixed-action <form>
    // already in the markup, so their buttons just call openModal directly
    // via inline onclick — nothing else to wire up here.
  }

  // ==========================================
  // GLOBAL MODAL HANDLERS (Optional Helper)
  // ==========================================
  // Closes any open modal when clicking outside the modal content
  const overlays = document.querySelectorAll('.modal-overlay');
  overlays.forEach(overlay => {
    overlay.addEventListener('click', function(e) {
      if (e.target === this) {
        this.style.display = 'none';
      }
    });
  });

});
