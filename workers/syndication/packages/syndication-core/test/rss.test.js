import assert from "node:assert/strict";
import test from "node:test";
import { parseRSSXml } from "../dist/rss.js";

test("parseRSSXml: 能解析 Hugo RSS（含 content:encoded CDATA）", () => {
  const xml = `<?xml version="1.0" encoding="utf-8"?>
  <rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
    <channel>
      <item>
        <title>Test &amp; Title</title>
        <link>https://example.com/a</link>
        <pubDate>Mon, 23 Dec 2025 10:00:00 +0800</pubDate>
        <description>plain excerpt</description>
        <content:encoded><![CDATA[# Hello\\n\\nBody]]></content:encoded>
      </item>
    </channel>
  </rss>`;

  const articles = parseRSSXml(xml, { maxItems: 10 });
  assert.equal(articles.length, 1);
  assert.equal(articles[0].title, "Test & Title");
  assert.equal(articles[0].url, "https://example.com/a");
  assert.equal(articles[0].excerpt, "plain excerpt");
  assert.equal(articles[0].content, "# Hello\\n\\nBody");
});

