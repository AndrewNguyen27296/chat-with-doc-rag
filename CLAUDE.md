# Pillar 3 - Chat with Docs RAG

Cited, hallucination-free answers over company documents: every answer carries
the source file and page, with an expandable excerpt drawer.

Read `README.md` for the product vision and `V1_NOTES.md` for build notes.

## The portfolio this belongs to

Three Streamlit products, built as proof-of-work to win freelance B2B data/AI
engagements in Sweden, the Nordics and Europe. Each has one 60-second "wow
moment" it exists to deliver. They are sold through three tiers: advisory audits
(~$500/day), turnkey builds ($1,000-$4,000), and managed retainers
($250-$600/month).

| Pillar | What it is | Code | Repo | Live URL |
| :--- | :--- | :--- | :--- | :--- |
| 1. Data Pipeline Dashboard | Freight ops briefing from messy multi-schema CSVs | V1 | yes | **live** |
| 2. Invoice & Vision Parser | Zero-manual-entry AP with an arithmetic audit | V1 | yes | **live** |
| 3. Chat with Docs RAG | Cited, hallucination-free answers over company docs | V1 | not yet | not yet |

Pillar 1 is live at https://freight-operations-intelligence-gr6t94nmogzgzh3cgy2plf.streamlit.app/.
Pillar 2 is live at https://invoice-vision-parser-uezswbeps38zrocbeej9hf.streamlit.app/.

## The plan, in order

The bottleneck is not building. All three are built. The bottleneck is that a
prospect cannot reach them, so work top-down and resist polishing.

**Phase A - ship what exists.** git init, push to GitHub, deploy to Streamlit
Community Cloud, smoke-test the live URL cold. Done for Pillars 1 and 2;
Pillar 3 still needs it.

**Phase B - turn demos into conversations.** A 60-second screen recording per
pillar. A one-page offer with price and timeline. A list of 25-30 Nordic
companies in the safe verticals. Then send it.

**Phase C - product work, but only what a prospect actually asks for.** Export
centres, multi-source ingestion, alerting. Do not start Phase C before Phase B
has produced a real conversation; the audit is what tells you which of these is
worth building.

The fastest first revenue is a Tier 1 audit. It needs no further product work at
all - the live demos are credibility, not the deliverable.

## Deploying to Streamlit Community Cloud

Proven on Pillar 1. The recipe:

1. `git init -b main`, then pin the identity **repo-locally** so the repo cannot
   inherit a work identity later:
   `git config user.email nguyenhuuthien27296@gmail.com`
2. Check `.gitignore` covers `.venv/`, `__pycache__/`, `.env`,
   `.streamlit/secrets.toml` and any derived data directory. Confirm with
   `git add -A && git diff --cached --name-only` before the first commit.
3. Create an **empty** repo at github.com/new under the personal account
   (`AndrewNguyen27296`) - no README, no .gitignore, no licence, or the first
   push conflicts.
4. `git remote add origin <url> && git push -u origin main`
5. share.streamlit.io -> New app -> pick the repo, branch `main`, main file
   `app.py`.

**The trap that cost Pillar 1 its first deploy:** Community Cloud builds on
**Python 3.14**. A pinned dependency with no cp314 wheel makes pip fall back to
compiling from source, and the build image has no `cmake`. `pyarrow==21.0.0`
ships wheels only to cp313, so the build died. Fixed by moving to
`pyarrow==25.0.1`, which covers 3.10-3.14.

Before deploying anything, check every pin for a 3.14 wheel against
`https://pypi.org/pypi/<pkg>/<version>/json`. Wheels tagged `py3-none-*` or
`cp39-abi3` are version-agnostic and fine; a wheel range ending at cp313 is not.

Note that `streamlit` itself depends on `pyarrow>=7.0`, so pyarrow is installed
whether or not it is listed - the only real choice is which version.

## Hard rules

- **Domain restriction.** These repositories stay entirely out of the energy and
  utility sector: no consumption data, no metering, no utility billing, no
  sustainability reporting - not in code, samples, docs or test fixtures. Safe
  verticals are logistics and freight, e-commerce, retail, corporate travel, and
  professional services. Each pillar enforces this with a test that greps every
  tracked file, and those tests ban the specific vocabulary. Do not restate the
  banned words here: this file is scanned too, and a continuation line that
  carries them without the test suite marker fails the build.
- **Never commit the parent `AI Startup/` folder.** It holds private strategy
  notes. One repository per pillar, rooted in that pillar's own directory.
- **Public repos.** These are or will be public. Do not write the author's
  employer, work email, or client names into any tracked file. Commit as the
  personal identity above, never the work one.
- **Personal equipment and personal hours only.**

## Where this pillar stands

**V1 built. Not in git, not deployed.** Phase A has not started here.

A dependency pre-flight has already been run against Streamlit Cloud's Python
3.14, and this pillar is clear:

| Pin | Wheels |
| :--- | :--- |
| `streamlit==1.63.0` | pure python |
| `chromadb==1.5.9` | `cp39-abi3`, forward-compatible to 3.14 |
| `pypdf==6.18.0` | pure python |
| `python-dotenv==1.2.2` | pure python |
| `openai==3.13.0` | pure python |
| `anthropic==1.5.0` | pure python |

`chromadb`'s wheel is tagged `cp39-abi3`, which looks like a Python 3.9 pin but
is not - abi3 wheels install on 3.9 and every later version.

**The embedding-model gap is closed.** `scripts/verify_v0.py` ran on
2026-09-14 against the real `all-MiniLM-L6-v2` ONNX model, downloaded fresh.
All 7 golden questions returned the expected page; off-topic questions scored
at most 0.204 against an in-scope floor of 0.539, a +0.336 margin; retrieval
took about 180 ms. The script's suggested floor of 0.37 is now the
`SIMILARITY_FLOOR` default. The domain-vocabulary scan the hard rules
promise now exists as `tests/test_domain_scope.py` and passes.

This pillar calls a model at runtime, so it needs a key. It goes in Streamlit
Cloud under Settings -> Secrets, never in a tracked file. The README mentions a
per-session spend guard - verify it is active before the URL is public, because
a public URL spends the author's key.

## Next action here

Phase A, step 1: `git init` and push, then deploy, following the recipe
above. Set the API key in Streamlit Cloud secrets and confirm the spend guard is
active before sharing the URL.
