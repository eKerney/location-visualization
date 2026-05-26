# X/Twitter Archive for @LocationArtist

## Process Summary

### 1. Install xsh (cookie-based X CLI tool)

```bash
go install github.com/benoitpetit/xsh@latest
```

### 2. Authenticate

Extracted session cookies (`auth_token`, `ct0`, `twid`) from browser and saved to `~/.config/xsh/auth.json`.

Verify:
```bash
xsh user LocationArtist
```

### 3. The Problem: No User Tweet Pagination in CLI

**Root cause:** `xsh user tweets` (`cmd/user.go:99`) calls `GetUserTweets()` once with `cursor=""` — no pagination loop, only 20 tweets returned. Compare with `xsh search` (`cmd/search.go:51-59`) which correctly loops with `--pages` and passes `CursorBottom` between iterations. The bug is that `user tweets` simply wasn't implemented with pagination, while search was.

The internal `core.GetUserTweets()` function (in `core/api.go:304`) **does** accept a `cursor` parameter and the MCP handler (`cmd/mcp_extended_handlers.go:166`) exposes `next_cursor` — so the core API and MCP both support pagination, only the CLI command is broken.

The `xsh search` command does paginate with `--pages`, but X's search index is time-limited (~7-14 days), so `from:LocationArtist --pages 50` still returns ≤20 tweets.

### 3b. Environment Setup

The Bearer token is stored in `.env` at the project root (already in `.gitignore`):

```
X_BEARER_TOKEN=
```

The script also checks `os.environ["X_BEARER_TOKEN"]` and falls back to searching parent directories for `.env`. This is a **public** token embedded in X.com's JavaScript — not a secret — but moved to `.env` to follow the principle of not hardcoding tokens in source files.

### 4. Solution: Direct GraphQL Pagination

Wrote `xsh_paginate_user_tweets.py` — a Python script that:

- Reads xsh's auth cookies from `~/.config/xsh/auth.json`
- Calls X's internal GraphQL API directly (same endpoint xsh uses)
- Operation: `UserTweets` (query ID `5M8UuGym7_VyIEggQIyjxQ`)
- Paginates using the `cursor` variable in each request
- Sleeps 1.5s between pages for rate limit courtesy

The X GraphQL endpoint returns a timeline with `TimelineAddEntries` entries. Tweet entries have IDs like `tweet-{id}` with `legacy.full_text`. Cursor entries have `cursorType: "Bottom"` with a `value` token for the next page.

**Usage:**
```bash
python3 xsh_paginate_user_tweets.py LocationArtist [max_pages]
```

### 5. Results

Two API endpoints were queried and results combined:

| Source | Tweets | Date range |
|--------|--------|------------|
| `UserTweets` (original) | 228 | Feb 2020 – May 2026 |
| `UserTweetsAndReplies` | 179 | Jan 2021 – May 2026 |
| **Combined (deduped)** | **232** | **Feb 2020 – May 2026** |

No replies or retweets were detected in either dataset — the `UserTweetsAndReplies` endpoint returned a slightly different timeline slice (offset cursor) but the same type of content. X's profile "total tweets" count (1,035) likely includes deleted/unavailable tweets that the API can't return.

Years covered:

| Year | Tweets |
|------|--------|
| 2020 | 24 |
| 2021 | 47 |
| 2022 | 41 |
| 2023 | 55 |
| 2024 | 24 |
| 2025 | 30 |
| 2026 | 11 |

### 6. Files in This Directory

| File | Description |
|------|-------------|
| `README.md` | This file |
| `locationartist-archive.json` | Raw JSON output (all tweets) |
| `locationartist-archive.md` | Markdown-formatted archive |
| `xsh_paginate_user_tweets.py` | GraphQL pagination script |
| `archive_to_md.py` | JSON → Markdown converter |

### 7. Replies Endpoint Experiment

The `UserTweetsAndReplies` operation (query ID `C3YpYjTsQZznJIdyy2JKuQ`) was tested but returned no identifiable replies (`in_reply_to_status_id_str` was null on all tweets). The endpoint produced a different cursor slice of the same timeline rather than actual reply tweets. Likely reasons:

- X's API may now handle replies differently (conversation controls, reply-limiting)
- The `UserTweetsAndReplies` endpoint in this API version may primarily include quote tweets and conversation starters
- Profile tweet count (1,035) includes metrics that don't map 1:1 to API-accessible content

The script supports both modes via a third positional arg:

```bash
python3 xsh_paginate_user_tweets.py LocationArtist 50 tweets         # default
python3 xsh_paginate_user_tweets.py LocationArtist 50 tweets_and_replies
```

Safety limit of 5,000 tweets built in to prevent runaway pagination if `has_more` stays true on empty pages.

### 8. ### 9. How This Works (Not a "Bypass")

We are **not bypassing** X's API or paywall. We are using the **same internal GraphQL API that X.com's frontend uses**, served to logged-in browsers for free. The `Bearer` token (`AAAAAAAA...`) is hardcoded in X's own JavaScript bundle. The session cookies (`auth_token`, `ct0`) are what the web app sets in your browser after login.

Both xsh and our Python script replay those credentials against the same endpoints the web client calls — equivalent to acting as a headless browser session. If X changes the bearer token or query IDs, it breaks (which is why xsh has auto-discovery for those).

## Architecture Notes
- Base: `https://x.com/i/api/graphql/{queryId}/{operation}`
- Auth: Bearer token (public) + cookies (`auth_token`, `ct0`, `twid`)
- Features map (boolean flags) required in every request
- Pagination: `cursor` variable in request body, `cursorBottom` value in response entries
- Timeline response: `data.user.result.timeline.timeline.instructions` → `TimelineAddEntries`
