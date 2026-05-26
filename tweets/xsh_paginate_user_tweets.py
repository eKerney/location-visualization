import json, os, sys, time
from urllib.request import Request, urlopen, HTTPError

AUTH_FILE = os.path.expanduser("~/.config/xsh/auth.json")

def _load_bearer_token():
    val = os.environ.get("X_BEARER_TOKEN")
    if val:
        return val
    # Try loading from .env in parent dirs (project root)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for dir in [os.getcwd(), script_dir, os.path.dirname(script_dir)]:
        env_path = os.path.join(dir, ".env")
        if os.path.isfile(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("X_BEARER_TOKEN="):
                        return line.split("=", 1)[1]
    print("Warning: X_BEARER_TOKEN not found in env or .env. Using hardcoded fallback.", file=sys.stderr)
    return ""

BEARER_TOKEN = _load_bearer_token()
MAX_TWEETS_SAFETY = 5000

OPERATIONS = {
    "tweets": {
        "operation": "UserTweets",
        "query_id": "5M8UuGym7_VyIEggQIyjxQ",
        "desc": "Original tweets only",
    },
    "tweets_and_replies": {
        "operation": "UserTweetsAndReplies",
        "query_id": "C3YpYjTsQZznJIdyy2JKuQ",
        "desc": "Tweets + replies",
    },
}

FEATURES = {
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_enhance_cards_enabled": True,
}

FIELD_TOGGLES = {"withArticlePlainText": False}


def load_auth():
    with open(AUTH_FILE) as f:
        data = json.load(f)
    acct = data.get("accounts", {}).get("default", {})
    cookies = acct.get("cookies", acct)
    return {
        "auth_token": cookies.get("auth_token"),
        "ct0": cookies.get("ct0"),
        "twid": cookies.get("twid"),
    }


def graphql_post(url, variables, auth):
    payload = {
        "variables": json.dumps(variables),
        "features": json.dumps(FEATURES),
        "fieldToggles": json.dumps(FIELD_TOGGLES),
    }
    body = json.dumps(payload).encode()
    req = Request(url, data=body)
    req.add_header("authorization", f"Bearer {BEARER_TOKEN}")
    req.add_header("x-csrf-token", auth["ct0"])
    req.add_header("x-twitter-auth-type", "OAuth2Session")
    req.add_header("x-twitter-client-language", "en")
    req.add_header("content-type", "application/json")
    req.add_header(
        "user-agent",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    )
    req.add_header("origin", "https://x.com")
    req.add_header("referer", "https://x.com/")
    req.add_header(
        "cookie",
        f"auth_token={auth['auth_token']}; ct0={auth['ct0']}; twid={auth['twid']}",
    )
    with urlopen(req) as resp:
        return json.loads(resp.read())


def get_user_id(auth, handle):
    user_qid = "pLsOiyHJ1eFwPJlNmLp4Bg"
    url = f"https://x.com/i/api/graphql/{user_qid}/UserByScreenName"
    variables = {"screen_name": handle, "withSafetyModeUserFields": True}
    raw = graphql_post(url, variables, auth)
    return raw["data"]["user"]["result"]["rest_id"]


def extract_tweets(raw):
    tweets = []
    bottom_cursor = ""
    has_more = False

    try:
        instructions = (
            raw["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]
        )
    except (KeyError, TypeError):
        return tweets, bottom_cursor, has_more

    entries = []
    for instr in instructions:
        if instr.get("type") == "TimelineAddEntries":
            entries = instr.get("entries", [])
            break

    for entry in entries:
        eid = entry.get("entryId", "")
        content = entry.get("content", {})

        if "cursor" in eid.lower():
            if content.get("cursorType") == "Bottom":
                bottom_cursor = content.get("value", "")
                has_more = True
            continue

        if not (eid.startswith("tweet-") or eid.startswith("profile-grid-")):
            continue

        item_content = content.get("itemContent", {})
        tweet_result = item_content.get("tweet_results", {}).get("result", {})

        if not tweet_result:
            continue

        legacy = tweet_result.get("legacy", {})
        if legacy:
            tweet_data = {
                "id": legacy.get("id_str", ""),
                "text": legacy.get("full_text", ""),
                "created_at": legacy.get("created_at", ""),
                "author_id": legacy.get("user_id_str", ""),
                "favorite_count": legacy.get("favorite_count", 0),
                "retweet_count": legacy.get("retweet_count", 0),
                "reply_count": legacy.get("reply_count", 0),
                "quote_count": legacy.get("quote_count", 0),
                "lang": legacy.get("lang", ""),
                "in_reply_to_status_id_str": legacy.get(
                    "in_reply_to_status_id_str"
                ),
                "is_retweet": "retweeted_status_result" in tweet_result,
                "rest_id": tweet_result.get("rest_id", ""),
                "views": tweet_result.get("views", {}).get("count", ""),
            }
            tweets.append(tweet_data)
        else:
            nested = tweet_result.get("tweet", {})
            if nested:
                legacy = nested.get("legacy", {})
                if legacy:
                    tweet_data = {
                        "id": legacy.get("id_str", ""),
                        "text": legacy.get("full_text", ""),
                        "created_at": legacy.get("created_at", ""),
                        "author_id": legacy.get("user_id_str", ""),
                        "favorite_count": legacy.get("favorite_count", 0),
                        "retweet_count": legacy.get("retweet_count", 0),
                        "reply_count": legacy.get("reply_count", 0),
                        "quote_count": legacy.get("quote_count", 0),
                        "lang": legacy.get("lang", ""),
                        "in_reply_to_status_id_str": legacy.get(
                            "in_reply_to_status_id_str"
                        ),
                        "is_retweet": True,
                        "rest_id": nested.get("rest_id", ""),
                        "views": nested.get("views", {}).get("count", ""),
                    }
                    tweets.append(tweet_data)

    return tweets, bottom_cursor, has_more


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <handle> [max_pages] [mode]", file=sys.stderr)
        print(f"  mode: 'tweets' (default) or 'tweets_and_replies'", file=sys.stderr)
        sys.exit(1)

    handle = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 999
    mode = sys.argv[3] if len(sys.argv) > 3 else "tweets"

    if mode not in OPERATIONS:
        print(f"Unknown mode: {mode}. Choose from: {list(OPERATIONS.keys())}", file=sys.stderr)
        sys.exit(1)

    op = OPERATIONS[mode]
    url = f"https://x.com/i/api/graphql/{op['query_id']}/{op['operation']}"
    print(f"Mode: {op['operation']} ({op['desc']})", file=sys.stderr)

    auth = load_auth()
    print(f"Resolving @{handle}...", file=sys.stderr)
    user_id = get_user_id(auth, handle)
    print(f"User ID: {user_id}", file=sys.stderr)

    all_tweets = []
    cursor = ""
    page = 0

    while page < max_pages:
        page += 1
        print(f"Fetching page {page}...", file=sys.stderr)

        variables = {
            "userId": user_id,
            "count": 100,
            "includePromotedContent": False,
            "withQuickPromoteEligibilityTweetFields": False,
            "withVoice": True,
            "withV2Timeline": True,
        }
        if cursor:
            variables["cursor"] = cursor

        try:
            raw = graphql_post(url, variables, auth)
        except HTTPError as e:
            body = e.read().decode()
            print(f"HTTP Error {e.code}: {body[:500]}", file=sys.stderr)
            break

        tweets, cursor, has_more = extract_tweets(raw)
        all_tweets.extend(tweets)
        print(
            f"  Got {len(tweets)} tweets ({len(all_tweets)} total, "
            f"has_more={has_more})",
            file=sys.stderr,
        )

        if len(all_tweets) >= MAX_TWEETS_SAFETY:
            print(f"  Reached safety limit of {MAX_TWEETS_SAFETY} tweets", file=sys.stderr)
            break

        if not has_more or not cursor:
            print("  No more pages (has_more or cursor empty)", file=sys.stderr)
            break

        if len(tweets) == 0:
            print("  Stopping: empty page", file=sys.stderr)
            break

        time.sleep(1.5)

    print(f"\nFinal count: {len(all_tweets)} tweets", file=sys.stderr)
    print(json.dumps(all_tweets, indent=2))


if __name__ == "__main__":
    main()
