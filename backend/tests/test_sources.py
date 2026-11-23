from etl.sources import parse_blog_feed, parse_google_news, parse_hacker_news

GOOGLE_NEWS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Databricks - Google News</title>
<item>
<title>Databricks raises $1B in new funding - TechCrunch</title>
<link>https://news.google.com/rss/articles/CBMiabc?oc=5</link>
<pubDate>Tue, 17 Nov 2026 09:30:00 GMT</pubDate>
<description>&lt;a href="https://news.google.com/rss/articles/CBMiabc?oc=5"&gt;Databricks raises $1B&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font&gt;TechCrunch&lt;/font&gt;</description>
<source url="https://techcrunch.com">TechCrunch</source>
</item>
</channel></rss>"""

BLOG_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Company blog</title>
<item>
<title>Introducing our new lakehouse feature</title>
<link>https://example.com/blog/lakehouse</link>
<pubDate>Wed, 18 Nov 2026 10:00:00 GMT</pubDate>
<description>&lt;p&gt;Today we are &lt;b&gt;launching&lt;/b&gt; a feature.&lt;/p&gt;</description>
</item>
</channel></rss>"""


def test_parse_google_news_strips_publisher_from_title():
    items = parse_google_news("Databricks", GOOGLE_NEWS_XML)
    assert len(items) == 1
    item = items[0]
    assert item.title == "Databricks raises $1B in new funding"
    assert item.source == "Google News (TechCrunch)"
    assert item.company == "Databricks"
    assert item.published_at.year == 2026 and item.published_at.month == 11
    assert item.url.startswith("https://news.google.com/")


def test_parse_blog_feed_cleans_summary():
    items = parse_blog_feed("Databricks", "Databricks blog", BLOG_XML)
    assert items[0].title == "Introducing our new lakehouse feature"
    assert items[0].text == "Today we are launching a feature."
    assert items[0].source == "Databricks blog"


def test_parse_hacker_news_skips_low_scoring_posts_and_uses_fallback_url():
    payload = {
        "hits": [
            {"objectID": "1", "title": "Databricks open sources a thing", "url": "https://example.com/x", "points": 120, "created_at_i": 1763000000},
            {"objectID": "2", "title": "Ask HN: Databricks pricing?", "url": None, "points": 40, "created_at_i": 1763000100, "story_text": "<p>How much?</p>"},
            {"objectID": "3", "title": "Ignored low score post", "url": "https://example.com/y", "points": 1, "created_at_i": 1763000200},
        ]
    }
    items = parse_hacker_news("Databricks", payload)
    assert [item.title for item in items] == ["Databricks open sources a thing", "Ask HN: Databricks pricing?"]
    assert items[1].url == "https://news.ycombinator.com/item?id=2"
    assert items[1].text == "How much?"
    assert items[0].source == "Hacker News"
