import json, sys
from datetime import datetime

def main():
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    with open(input_file) as f:
        tweets = json.load(f)

    # Sort chronologically (oldest first)
    def parse_date(t):
        try:
            return datetime.strptime(t["created_at"], "%a %b %d %H:%M:%S +0000 %Y")
        except:
            return datetime.min

    tweets.sort(key=parse_date)

    lines = []
    lines.append("# @LocationArtist Tweet Archive\n")
    lines.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d')}*\n")
    lines.append(f"**{len(tweets)} tweets spanning {tweets[0]['created_at'][-4:]}–{tweets[-1]['created_at'][-4:]}**\n")
    lines.append("---\n")

    for i, t in enumerate(tweets):
        created = t.get("created_at", "")
        try:
            dt = datetime.strptime(created, "%a %b %d %H:%M:%S +0000 %Y")
            date_str = dt.strftime("%b %d, %Y")
        except:
            date_str = created

        text = t.get("text", "")
        tweet_id = t.get("id", t.get("rest_id", ""))
        likes = t.get("favorite_count", 0)
        retweets = t.get("retweet_count", 0)
        replies = t.get("reply_count", 0)
        views = t.get("views", "")
        is_retweet = t.get("is_retweet", False)

        lines.append(f"## Tweet #{len(tweets) - i}\n")
        lines.append(f"**{date_str}** · [View on X](https://x.com/LocationArtist/status/{tweet_id})\n")
        if is_retweet:
            lines.append("*🔁 Retweet*\n")
        lines.append(f"{text}\n")
        lines.append(f"❤️ {likes} · 🔁 {retweets} · 💬 {replies}" + (f" · 👁️ {views}" if views else "") + "\n")
        lines.append("---\n")

    output = "\n".join(lines)

    if output_file:
        with open(output_file, "w") as f:
            f.write(output)
        print(f"Wrote {len(tweets)} tweets to {output_file}")
    else:
        print(output)

if __name__ == "__main__":
    main()
