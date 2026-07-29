/*
 * Unitas - Shared API helper
 * -----------------------------------------------------------
 * Reusable fetch() wrapper for talking to the Django backend.
 * Reads the CSRF token from the `csrftoken` cookie (Django's default
 * session-auth + CSRF setup) and attaches it to every non-GET request,
 * as the backend has @csrf_exempt disabled everywhere.
 *
 * Any new section being connected to its backend should reuse this
 * instead of re-implementing CSRF handling.
 */

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return decodeURIComponent(parts.pop().split(';').shift());
  return null;
}

/**
 * apiFetch(url, { method, body })
 * - Defaults to GET.
 * - JSON-encodes `body` and sets Content-Type automatically when present.
 * - Attaches X-CSRFToken for any method other than GET/HEAD/OPTIONS/TRACE.
 * - Always sends credentials so the Django session cookie is included.
 *
 * Returns { ok, status, data } — never throws on a non-2xx HTTP status,
 * so callers can read the backend's real error body (e.g. {'error': '...'})
 * without a try/catch just for that. Network failures still reject.
 */
async function apiFetch(url, { method = 'GET', body } = {}) {
  const headers = {};
  const safeMethod = ['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method.toUpperCase());

  if (!safeMethod) {
    headers['X-CSRFToken'] = getCookie('csrftoken');
  }

  let requestBody;
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    requestBody = JSON.stringify(body);
  }

  const response = await fetch(url, {
    method,
    headers,
    body: requestBody,
    credentials: 'same-origin',
  });

  let data = null;
  try {
    data = await response.json();
  } catch (e) {
    // No JSON body (e.g. 204) — leave data as null.
  }

  return { ok: response.ok, status: response.status, data };
}
