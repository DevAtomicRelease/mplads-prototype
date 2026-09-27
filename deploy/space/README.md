---
title: MPLADS-GUARD demo
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# MPLADS-GUARD — read-only demo copy

SIH 2026 · PS 26102. Anomaly and inefficiency review signals for MPLADS works.

- **Review signals, not findings of fraud.** Every flag is a request to check evidence.
- **Read-only:** saving reviews and running maintenance tools are turned off here.
- The data bundle is downloaded at startup from a private dataset repo and every
  sealed release file is checked against its manifest before the server starts.

Space settings needed (Settings → Variables and secrets):

| Name | Kind | Value |
|---|---|---|
| `MPLADS_BUNDLE_REPO` | Variable | `your-username/mplads-demo-data` |
| `HF_TOKEN` | Secret | a read-only Hugging Face access token |
| `MPLADS_BUNDLE_SHA256` | Variable (optional) | contents of `mplads-demo-bundle.tar.gz.sha256` (first word) |
