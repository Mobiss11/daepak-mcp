# Changelog

## 2.0.5 — 2026-08-31

- MCP Registry readiness: `server.json` (io.github.mobiss11/daepak-mcp) and the
  `mcp-name` ownership marker in the package README/metadata. No code changes.

## 2.0.4

- README rewritten in English and brought up to date. The package page on PyPI was
  rendering the Russian one — PyPI is an international index, and the page is the first
  thing a developer sees.
- Documents what the agent gained since 2.0.3: streaming, conversation memory, image
  attachments, mentor mode, reconnecting to a running generation, cancelling one, and
  listing conversations.

## 2.0.3

- Repository, issues and changelog links added to the package metadata.
  (PyPI does not accept a re-upload of an existing version, even with changed
  metadata — hence the bump.)

## 2.0.2

- Server version is now read from package metadata instead of being hard-coded,
  so it can no longer drift from the published release.

## 2.0.1

- `certifi` added as a dependency. Without it every call fails with
  `CERTIFICATE_VERIFY_FAILED` on macOS, where Python builds do not read the
  system certificate store.

## 2.0.0

- The server now talks to the public `/v1` API and authenticates with a
  per-user key. The account is derived **from the key**; it can no longer be
  named in the request.
- The tool catalogue arrives filtered by the key's scopes, and each tool
  carries its price in credits.
