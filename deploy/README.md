# Free, read-only demo deployment

Two zero-cost ways to show MPLADS-GUARD to others. Neither needs a credit card.

| | Hugging Face Space | Cloudflare quick tunnel |
|---|---|---|
| Runs on | Hugging Face's free CPU (2 vCPU, 16 GB) | Your own computer |
| Account | Free Hugging Face account (email only) | None |
| Link | Stable `https://<user>-<space>.hf.space` | New random `https://….trycloudflare.com` each time |
| Availability | Sleeps after ~48 h without visitors; first visit then takes 1–2 min | Only while your computer and the script are running |
| Data | Uploaded to a **private** Hugging Face dataset repo | Never leaves your computer |

**Both are read-only demo copies.** Any server reachable beyond this computer is
forced into read-only mode: no review saving, no maintenance tools, and a
"Demo copy · read-only" banner on every page. Use them for judges and reviewers,
not as a public website. The app shows real MP names next to "high priority"
flags; keep links private (a private Space, or share the tunnel link only with
the people who need it).

---

## Option A — Hugging Face Space (hosted, stable link)

### 1. Make the demo bundle (on your computer)

```powershell
cd mplads-prototype; npm run build; cd ..
.\.venv\Scripts\python.exe -B deploy\pack_release.py
```

This writes `deploy\build\mplads-demo-bundle.tar.gz` (about 55 MB) and a `.sha256`
file next to it. The packer refuses to run if the active release fails
verification or the built interface is older than its source, and it re-reads the
finished archive against the release manifest. The bundle contains the sealed
release (without the two large CSV downloads), the exact analysis code, and the
built interface — never the raw `Dataset/` files or your review notes.

### 2. Create a free Hugging Face account and a write token

1. Sign up at <https://huggingface.co/join> (email only).
2. Settings → Access Tokens → **Create new token**:
   - one **Write** token for uploading (keep it on your computer only);
   - one **Read** token for the Space to download the bundle.

### 3. Upload the bundle to a private dataset repo

```powershell
.\.venv\Scripts\python.exe -m pip install huggingface_hub
.\.venv\Scripts\hf.exe auth login        # paste the Write token
.\.venv\Scripts\hf.exe repos create mplads-demo-data --repo-type dataset --private
.\.venv\Scripts\hf.exe upload <your-username>/mplads-demo-data deploy\build\mplads-demo-bundle.tar.gz mplads-demo-bundle.tar.gz --repo-type dataset
```

(The same steps work in the browser: New → Dataset → Private → Files → Upload.)

### 4. Create the Space

1. New → **Space** → name it (e.g. `mplads-demo`) → SDK **Docker** → *Blank* →
   visibility **Private** → Create.
2. Upload the five files from `deploy\space\` to the Space's root
   (Files → Add file → Upload): `Dockerfile`, `README.md`, `start.py`,
   `requirements.txt`, `.gitattributes`.
3. Space → Settings → **Variables and secrets**:

   | Name | Type | Value |
   |---|---|---|
   | `MPLADS_BUNDLE_REPO` | Variable | `<your-username>/mplads-demo-data` |
   | `HF_TOKEN` | **Secret** | the **Read** token |
   | `MPLADS_BUNDLE_SHA256` | Variable (recommended) | first word of `deploy\build\mplads-demo-bundle.tar.gz.sha256` |

4. The Space builds and starts. Logs show `Bundle checksum matches`, then
   `MPLADS Six Source: … (read-only demo copy)`.
5. Share access: Space → Settings → add collaborators, or make the Space public
   only if you accept that anyone can open it.

### Updating the demo later

Rebuild or prepare a new release locally, run `pack_release.py` again, upload the
new bundle (same file name), update `MPLADS_BUNDLE_SHA256`, then **Restart** the Space.

---

## Option B — Cloudflare quick tunnel (from your computer, no account)

```powershell
winget install --id Cloudflare.cloudflared          # once
powershell -ExecutionPolicy Bypass -File deploy\tunnel.ps1
```

The script starts a separate read-only copy on port 8767 (your normal `START.cmd`
copy on 8766 is unaffected) and prints a `https://….trycloudflare.com` link. Close
the window or press Ctrl+C to stop sharing. Keep the computer awake during demos.

---

## What the hosted copy does and does not do

- Every sealed release file present is checked against the release manifest at
  startup, the analysis code must match the code recorded in the release, and any
  missing file must be one the packer declared omitted. Otherwise it will not start.
- Requests are accepted only for `localhost` and the configured public hostname
  (`SPACE_HOST` is set by Hugging Face automatically; tunnels use `*.trycloudflare.com`).
- Saving reviews and running maintenance jobs return 403 and are hidden in the UI.
- The two large CSV downloads (all works, all payments) show "not generated" in the
  demo; every screen, chart, query and the Excel workbook still work.
- There are no user log-ins. Privacy comes from a private Space or an unshared link.
