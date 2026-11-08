
import json
import os
import pathlib
import urllib.parse
import urllib.request
from datetime import datetime, timezone

IG_USER_ID = "17841400217434229"
GRAPH_URL = "https://graph.facebook.com/v27.0/" + IG_USER_ID + "/media"
FIELDS = "id,media_type,media_url,thumbnail_url,permalink,timestamp"
PER_PAGE = 12


def fetch_batch(token, after=None):
    params = {"fields": FIELDS, "limit": "100"}
    if after:
        params["after"] = after
    url = GRAPH_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"Authorization": "Bearer " + token}
    )
    with urllib.request.urlopen(req, timeout=40) as response:
        return json.load(response)


def main():
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
    if not token:
        raise SystemExit("Missing GitHub secret: INSTAGRAM_ACCESS_TOKEN")

    items = []
    after = None
    seen = set()

    for _ in range(100):
        result = fetch_batch(token, after)
        batch = result.get("data")
        if not isinstance(batch, list):
            raise RuntimeError("Instagram API returned no media list")

        for item in batch:
            media_type = item.get("media_type", "")
            image = (
                (item.get("thumbnail_url") if media_type == "VIDEO" else None)
                or item.get("media_url")
                or item.get("thumbnail_url")
            )
            if not image or not item.get("permalink"):
                continue

            items.append({
                "id": item.get("id", ""),
                "type": media_type,
                "image": image,
                "link": item["permalink"],
                "date": item.get("timestamp", ""),
            })

        paging = result.get("paging") or {}
        if not paging.get("next"):
            break

        after = (paging.get("cursors") or {}).get("after")
        if not after or after in seen:
            raise RuntimeError("Instagram pagination cursor error")
        seen.add(after)
    else:
        raise RuntimeError("Instagram pagination limit reached")

    if not items:
        raise RuntimeError("No usable Instagram posts")

    folder = pathlib.Path("site/feed")
    folder.mkdir(parents=True, exist_ok=True)

    for number, start in enumerate(range(0, len(items), PER_PAGE), 1):
        path = folder / ("page-%04d.json" % number)
        path.write_text(
            json.dumps(items[start:start + PER_PAGE], ensure_ascii=False),
            encoding="utf-8"
        )

    manifest = {
        "account": "jejuphonebook_today",
        "total_posts": len(items),
        "total_pages": (len(items) + PER_PAGE - 1) // PER_PAGE,
        "per_page": PER_PAGE,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    (folder / "index.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )

    print(
        "Feed prepared: %d posts in %d pages"
        % (manifest["total_posts"], manifest["total_pages"])
    )


if __name__ == "__main__":
    main()
