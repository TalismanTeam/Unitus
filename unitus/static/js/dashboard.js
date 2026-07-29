// dashboard.js
// Connects the "In Progress / Suspended / Completed / Managed / All" tabs
// on dashboard.html to:
//
//   GET /auth/users/me/dashboard/projects?tab=<in_progress|suspended|completed|managed|all>
//
// (accounts.views.dashboard_projects_view, mounted at /auth/ in the root
// urls.py). Session-auth only, GET-only, so no CSRF header is needed here.
//
// Response shape (accounts.serialization.serialize_project_summary), one
// object per project:
//   { id, title, short_description, state, duration_days, created_at,
//     is_pm, role_title }
//
// role_title comes from the viewer's ProjectMember.project_role.role_title
// for that project, and is null when they have no membership row for it
// (e.g. a PM with no ProjectMember row) or the row's project_role is null.
//
// Clicking a project card navigates to its real detail page:
//   GET /projects/<id>/workspace/  (projects.views.project_workspace,
//   name="project_workspace", mounted at /projects/ in the root urls.py).
// That page is server-rendered Django (no JSON here) and itself enforces
// that only the PM sees edit/delete/status-change/transfer actions.

const DASHBOARD_PROJECTS_URL = "/auth/users/me/dashboard/projects";
const projectWorkspaceUrl = (id) => `/projects/${id}/workspace/`;

const TAB_HEADINGS = {
  in_progress: "In Progress Projects",
  suspended: "Suspended Projects",
  completed: "Completed / Terminated Projects",
  managed: "My Managed Projects",
  all: "All Projects",
};

document.addEventListener("DOMContentLoaded", () => {
  const tabButtons = document.querySelectorAll(".tab-btn[data-tab]");
  const heading = document.getElementById("tab-content-heading");
  const list = document.getElementById("project-list");
  const status = document.getElementById("project-list-status");

  if (!tabButtons.length || !list) return;

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      loadTab(btn.dataset.tab);
    });
  });

  const initiallyActive = document.querySelector(".tab-btn.active[data-tab]");
  loadTab(initiallyActive ? initiallyActive.dataset.tab : "in_progress");

  function setStatus(message, isError) {
    if (!status) return;
    if (!message) {
      status.style.display = "none";
      status.textContent = "";
      return;
    }
    status.style.display = "";
    status.textContent = message;
    status.style.color = isError ? "#b00020" : "";
  }

  function loadTab(tab) {
    if (heading) heading.textContent = TAB_HEADINGS[tab] || "Projects";
    setStatus("Loading…", false);
    list.innerHTML = "";

    fetch(`${DASHBOARD_PROJECTS_URL}?tab=${encodeURIComponent(tab)}`, {
      method: "GET",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(async (response) => {
        if (response.status === 401 || response.status === 403) {
          throw new Error("You need to be logged in to view your dashboard.");
        }
        if (!response.ok) {
          // View returns { detail: "..." } on bad_request (400)
          let detail = `Request failed (${response.status})`;
          try {
            const body = await response.json();
            if (body && body.detail) detail = body.detail;
          } catch (_) {
            /* non-JSON error body, keep default message */
          }
          throw new Error(detail);
        }
        return response.json();
      })
      .then((projects) => {
        setStatus(null);
        renderProjects(projects);
      })
      .catch((err) => {
        setStatus(err.message || "Something went wrong loading your projects.", true);
      });
  }

  function renderProjects(projects) {
    list.innerHTML = "";

    if (!Array.isArray(projects) || projects.length === 0) {
      const empty = document.createElement("li");
      empty.textContent = "No projects in this category yet.";
      list.appendChild(empty);
      return;
    }

    projects.forEach((project) => {
      const li = document.createElement("li");
      li.style.cursor = "pointer";
      li.title = "View project details";
      li.addEventListener("click", () => {
        window.location.href = projectWorkspaceUrl(project.id);
      });

      const title = document.createElement("strong");
      title.textContent = project.title;
      li.appendChild(title);

      let roleLabel;
      if (project.role_title) {
        roleLabel = project.is_pm
          ? `Project Manager · ${project.role_title}`
          : project.role_title;
      } else {
        roleLabel = project.is_pm ? "Project Manager" : "Member";
      }
      const meta = document.createElement("span");
      meta.textContent = ` — Role: ${roleLabel} — Status: ${project.state}`;
      li.appendChild(meta);

      if (project.short_description) {
        const desc = document.createElement("div");
        desc.textContent = project.short_description;
        desc.style.fontSize = "0.9em";
        desc.style.opacity = "0.8";
        li.appendChild(desc);
      }

      list.appendChild(li);
    });
  }
});
