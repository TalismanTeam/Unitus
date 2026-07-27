/*
 * Unitas - Project Storage Layer (temporary front-end mock)
 * -----------------------------------------------------------
 * This file simulates the Django backend using localStorage so the
 * frontend behaves like a complete, connected site during development.
 *
 * WHEN THE DJANGO BACKEND IS READY:
 * Replace the body of each function below with a `fetch()` call to the
 * matching API endpoint. Every page that uses this file (project_create.html,
 * projects.html, project_advertisements.html, project_detail.html) calls
 * ONLY these functions — so the rest of the code does not need to change,
 * only this file does.
 */

const STORAGE_KEY = 'unitus_projects';

const STATUS_LABELS = {
  recruiting: 'Recruiting',
  in_progress: 'In Progress',
  suspended: 'Suspended',
  terminated: 'Terminated / Completed'
};

const TERMINATION_REASON_LABELS = {
  success: 'Successful completion',
  internal_issues: 'Internal team issues',
  team_failure: 'Team failure',
  owner_withdrawal: 'Owner withdrawal',
  other: 'Other'
};

// ---- Core read/write ----

function getProjects() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    console.error('Failed to read projects from storage:', e);
    return [];
  }
}

function saveProjects(projects) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(projects));
}

function getProject(projectId) {
  const id = Number(projectId);
  return getProjects().find(p => p.id === id) || null;
}

// ---- Project management (PM domain) ----

// PM-001: Create Project
// Expects: { title, shortDescription, fullDescription, duration, ownerRole, roles: [...] }
function addProject(data) {
  const projects = getProjects();
  const nextId = projects.length ? Math.max(...projects.map(p => p.id)) + 1 : 1;

  const project = {
    id: nextId,
    title: data.title,
    shortDescription: data.shortDescription,
    fullDescription: data.fullDescription,
    duration: data.duration,
    ownerRole: data.ownerRole || null, // null = PM has no technical role
    owner: 'You', // placeholder until auth/session is wired to Django
    status: 'recruiting',
    terminationReason: null,
    roles: data.roles.map((r, index) => ({
      id: index + 1,
      title: r.title,
      capacity: Number(r.capacity) || 1,
      filled: 0, // no members system yet — every role starts unfilled
      skill: r.skill,
      skillLevel: r.skillLevel,
      description: r.description
    }))
  };

  projects.push(project);
  saveProjects(projects);
  return project;
}

// PM-003: Edit Project
function updateProject(projectId, data) {
  const projects = getProjects();
  const index = projects.findIndex(p => p.id === Number(projectId));
  if (index === -1) return null;

  projects[index] = {
    ...projects[index],
    title: data.title,
    shortDescription: data.shortDescription,
    fullDescription: data.fullDescription,
    duration: data.duration,
    ownerRole: data.ownerRole || null,
    roles: data.roles.map((r, i) => ({
      id: i + 1,
      title: r.title,
      capacity: Number(r.capacity) || 1,
      filled: projects[index].roles[i] ? projects[index].roles[i].filled : 0,
      skill: r.skill,
      skillLevel: r.skillLevel,
      description: r.description
    }))
  };

  saveProjects(projects);
  return projects[index];
}

// PM-004/PM-005: Change Status (Recruiting / In Progress / Suspended / Terminated)
function updateProjectStatus(projectId, status, terminationReason) {
  const projects = getProjects();
  const index = projects.findIndex(p => p.id === Number(projectId));
  if (index === -1) return null;

  projects[index].status = status;
  projects[index].terminationReason = status === 'terminated' ? terminationReason : null;

  saveProjects(projects);
  return projects[index];
}

// ---- Advertisement management (AM domain) ----
// Ads are NOT stored separately — per the spec, they are auto-generated
// from every role that still has open capacity (filled < capacity), and
// disappear automatically once a role is full.

function getAllOpenAds() {
  const ads = [];
  getProjects().forEach(project => {
    if (project.status !== 'recruiting') return; // only recruiting projects advertise
    project.roles.forEach(role => {
      if (role.filled < role.capacity) {
        ads.push({
          projectId: project.id,
          roleId: role.id,
          role: role.title,
          projectShortDescription: project.shortDescription,
          roleDescription: role.description,
          status: 'Open'
        });
      }
    });
  });
  return ads;
}

// ---- Seed data (only runs once, so the pages aren't empty on first load) ----

function seedProjectsIfEmpty() {
  if (getProjects().length > 0) return;

  addProject({
    title: 'Online Marketplace Platform',
    shortDescription: 'A marketplace connecting local sellers with buyers.',
    fullDescription: 'Full-featured e-commerce platform including seller dashboards, order tracking, and payments.',
    duration: '3 months',
    ownerRole: null,
    roles: [
      { title: 'Front-end Developer', capacity: 2, skill: 'React', skillLevel: 'Intermediate', description: 'Build the storefront and seller dashboard UI.' },
      { title: 'Backend Developer', capacity: 1, skill: 'Django', skillLevel: 'Advanced', description: 'Design the API and payment integration.' }
    ]
  });

  addProject({
    title: 'Fitness Tracking App',
    shortDescription: 'Mobile-first app for tracking workouts and nutrition.',
    fullDescription: 'An app that lets users log workouts, track nutrition, and share progress with friends.',
    duration: '2 months',
    ownerRole: 'Backend Developer',
    roles: [
      { title: 'UI/UX Designer', capacity: 1, skill: 'Figma', skillLevel: 'Advanced', description: 'Design the mobile app screens and flows.' }
    ]
  });
}