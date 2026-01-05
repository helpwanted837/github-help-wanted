export function decodeXmlEntities(input: string): string {
  const base = input
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&quot;", "\"")
    .replaceAll("&apos;", "'")
    .replaceAll("&amp;", "&");

  return base
    .replaceAll(/&#x([0-9a-fA-F]+);/g, (_, hex) =>
      String.fromCodePoint(Number.parseInt(hex, 16))
    )
    .replaceAll(/&#(\d+);/g, (_, num) =>
      String.fromCodePoint(Number.parseInt(num, 10))
    );
}

export function extractCDATA(text: string): string {
  const match = text.match(/<!\[CDATA\[([\s\S]*?)\]\]>/);
  return match ? match[1] : text;
}
