"""Browser-side Posit Connect identity lookup for Streamlit."""

from __future__ import annotations

import streamlit as st


_IDENTITY_COMPONENT = st.components.v2.component(
    "rsc_identity",
    html="<span aria-hidden=\"true\"></span>",
    js="""
export default async function ({ setStateValue }) {
  const xsrfCookie = document.cookie
    .split('; ')
    .find((item) => item.startsWith('RSC-XSRF-legacy='));
  const xsrfToken = xsrfCookie ? xsrfCookie.slice('RSC-XSRF-legacy='.length) : '';
  try {
    const response = await fetch('/__api__/me', {
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json',
        ...(xsrfToken ? { 'X-RSC-XSRF': xsrfToken } : {}),
      },
      cache: 'no-store',
    });
    if (!response.ok) {
      setStateValue('ntid', '');
      return;
    }
    const payload = await response.json();
    const profile = payload?.profile || payload?.user || payload || {};
    setStateValue('ntid', String(profile?.username || payload?.username || '').trim());
  } catch {
    setStateValue('ntid', '');
  }
}
""",
)


def rsc_ntid() -> str:
    """Return the signed-in Posit Connect username from the browser session."""
    result = _IDENTITY_COMPONENT(key="rsc_identity", on_ntid_change=lambda: None)
    return str(getattr(result, "ntid", "") or "").strip()