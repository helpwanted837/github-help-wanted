---
title: GitHub Pages HTTPS
description: How HTTPS works on GitHub Pages, how to enable Enforce HTTPS, and how to fix certificate and mixed-content issues for custom domains.
date: '2026-01-02T03:55:54+08:00'
draft: true
commercial_value: 3
affiliate_products: []
keywords:
- github pages https
- enforce https github pages
- github pages certificate not yet created
- github pages mixed content
pillar: /github-pages/
faq:
- question: Is HTTPS automatic for GitHub Pages?
  answer: GitHub Pages supports HTTPS for all sites. Sites using the default github.io
    domain are typically served over HTTPS automatically, and custom domains can also
    use HTTPS once DNS is configured and a certificate is provisioned.
- question: Why is Enforce HTTPS disabled?
  answer: Enforce HTTPS is only available after GitHub can provision a certificate for
    your domain. Fix DNS and allow time for certificate provisioning, then enable it in
    Settings → Pages.
- question: What does Certificate not yet created mean?
  answer: It usually means GitHub cannot complete the automatic DNS check required for
    certificate provisioning. Re-check DNS records and the configured custom domain, then
    retry after propagation.
- question: Why do I see mixed content warnings on HTTPS?
  answer: Your page is loading some resources over HTTP. Update resource URLs to HTTPS,
    use protocol-relative or relative URLs, and verify third-party scripts support HTTPS.
- question: Should I use GitHub Pages for sensitive transactions?
  answer: No. GitHub Docs warns that GitHub Pages sites should not be used for sensitive
    transactions such as sending passwords or credit card numbers.
howto:
  name: How to enable HTTPS on GitHub Pages
  totalTime: PT20M
  steps:
  - name: Confirm your domain setup
    text: Identify whether you use the default github.io domain or a custom domain, and
      verify DNS records resolve to GitHub Pages correctly.
  - name: Wait for certificate provisioning
    text: After setting the custom domain, allow time for GitHub to provision the TLS
      certificate; fix DNS issues if provisioning is blocked.
  - name: Enable Enforce HTTPS
    text: In Settings → Pages, enable Enforce HTTPS when it becomes available, then
      validate redirects and fix mixed content.
lastmod: '2025-12-29T20:34:22+08:00'
type: cluster
---

HTTPS on GitHub Pages is usually “set it and forget it” for sites on the default `github.io` domain, but custom domains introduce two extra moving parts: DNS correctness and certificate provisioning. Most HTTPS problems on Pages are not about TLS details—they are about whether GitHub can validate your domain and whether your site loads everything over HTTPS.

This guide explains how HTTPS works on GitHub Pages, how to enable **Enforce HTTPS**, and how to troubleshoot the two most common failure modes: **certificate not provisioned** and **mixed content**.

## Key Takeaways

- **HTTPS is a security baseline**: it provides encryption, integrity, and authentication for web traffic.
- **GitHub Pages supports HTTPS**: default domains are served over HTTPS automatically, and custom domains can also use HTTPS after DNS and certificate provisioning.
- **Enforce HTTPS is the “lock”**: when enabled, GitHub Pages redirects HTTP to HTTPS for your site.
- **Certificate problems are usually DNS problems**: fix records first, then allow time for provisioning to complete.
- **Mixed content breaks the last mile**: one HTTP script or image can trigger warnings or blocked loads on an HTTPS page.

## What is HTTPS (and why it matters on Pages)?

HTTPS is HTTP over TLS. At a practical level it gives you:

- **Confidentiality**: traffic is encrypted in transit.
- **Integrity**: attackers cannot silently modify content in transit.
- **Authentication**: the browser can verify it is talking to the expected site (certificate validation).

MDN’s HTTPS overview summarizes HTTPS as a secure version of HTTP that uses TLS to protect communication between the browser and the server.

> Paraphrased: HTTPS is HTTP secured by TLS, protecting communication between clients and servers.
> — MDN, adapted

On GitHub Pages, HTTPS has two benefits beyond general security:

1. Visitors do not get scary “Not secure” browser messaging.
2. You can safely embed modern third-party scripts that require HTTPS (analytics, comments, embeds).

## How HTTPS Works on GitHub Pages

GitHub Docs explains that GitHub Pages sites support HTTPS and you can enforce HTTPS for your Pages site.

### Default domain vs custom domain

| Domain type | Example | Typical HTTPS behavior | Where issues usually come from |
|---|---|---|---|
| Default domain | `https://<user>.github.io/` | Served over HTTPS automatically for modern sites | Rare; mostly incorrect URL or base path |
| Custom domain | `https://www.example.com/` | HTTPS once DNS is correct and a certificate is provisioned | DNS misconfiguration, certificate not provisioned, mixed content |

### Enforce HTTPS (what it actually does)

When you enable **Enforce HTTPS** in Pages settings, the expectation is:

- HTTP requests are redirected to HTTPS
- your canonical browsing experience is HTTPS

This is important because users often type `http://` or click legacy links.

## Step-by-Step: Enable HTTPS and Enforce HTTPS on GitHub Pages

### Step 1: Confirm your domain configuration

Identify which case you’re in:

- Default domain only (`github.io`)
- Custom domain (apex or `www`)

If you use a custom domain, validate DNS first. A quick sanity check:

```bash
dig +short www.example.com CNAME
dig +short example.com A
dig +short example.com AAAA
```

You want to see records resolving to the expected GitHub Pages targets (or your DNS provider’s flattened results for apex domains).

### Step 2: Ensure your Pages site is published correctly

HTTPS troubleshooting is wasted effort if the site itself isn’t publishing. Before you chase certificates:

1. Confirm the Pages publishing source is correct.
2. Confirm the published root contains index.html.
3. Confirm you can load the site on the default domain.

This isolates “site deploy” from “HTTPS provisioning”.

### Step 3: Set the custom domain (if applicable)

In your repo:

1. Go to **Settings → Pages**
2. Under Custom domain, enter your domain (for example `www.example.com`)
3. Save and let GitHub run its automatic DNS check

### Step 4: Wait for certificate provisioning (and know what “blocked” looks like)

If you see **Certificate not yet created**, GitHub Docs explains this as part of the certificate provisioning troubleshooting flow. In practice, it usually means GitHub cannot complete its DNS validation.

The most reliable fix order is:

1. Fix DNS records (type, host, target, proxy settings if applicable).
2. Confirm DNS resolves as expected from your machine.
3. Wait for propagation and GitHub’s certificate process.

GitHub’s custom domain troubleshooting documentation notes that it can take up to an hour for your site to become available over HTTPS after configuring your custom domain.

> Paraphrased: After configuring a custom domain, HTTPS availability can take up to about an hour.
> — GitHub Docs, adapted

If you updated DNS after setting the domain, GitHub Docs also notes you may need to remove and re-add the custom domain to trigger the HTTPS enabling process again.

### Step 5: Enable Enforce HTTPS

Once the certificate is provisioned, return to **Settings → Pages** and enable **Enforce HTTPS**.

Then validate with a redirect check:

```bash
curl -I http://www.example.com/
curl -I https://www.example.com/
```

What you want:

- HTTP returns a redirect (301/302) to the HTTPS URL
- HTTPS returns 200 for the homepage

## Fix Mixed Content (The #1 “HTTPS is enabled but still broken” issue)

Mixed content means an HTTPS page loads some resources over HTTP. Modern browsers may warn or block these loads because they downgrade security.

GitHub Docs includes a “mixed content” troubleshooting section for GitHub Pages HTTPS, and MDN provides a detailed overview of what mixed content is and why browsers enforce it.

### How to detect mixed content quickly

1. Open the page in Chrome/Firefox.
2. Open DevTools → Console and Network.
3. Look for warnings like “Mixed Content” or blocked HTTP resources.

### Common causes (and fixes)

| Cause | Example | Fix |
|---|---|---|
| Hard-coded HTTP assets | `http://.../logo.png` | Change to `https://` or use a relative URL |
| Third-party scripts only support HTTP | legacy analytics script | Replace vendor or self-host a HTTPS-compatible version |
| Old canonical/OG URLs | canonical points to http | Update site config to output HTTPS URLs |
| CSS imports over HTTP | `@import url(http://...)` | Use HTTPS or bundle locally |

### Best practice for Pages sites

- Prefer relative URLs when possible.
- Ensure every external dependency supports HTTPS.
- Avoid “it works locally” assumptions; test in production with a cold cache.

## Canonical Host and Redirect Hygiene (Apex vs www)

Many “HTTPS issues” are really “hostname and redirect issues”:

- You configure `www.example.com` in Pages, but users visit `example.com`.
- Some pages link to HTTP, some to HTTPS.
- Some pages link to the apex, some to `www`.

These mismatches can create confusing behavior (loops, extra redirects, cookies that don’t stick) and make troubleshooting harder.

### Pick one canonical hostname

Decide which hostname is the primary URL for humans and crawlers:

- `https://www.example.com/` (common default)
- `https://example.com/` (apex)

Then align everything to that choice:

- Pages custom domain setting
- internal links in your site
- canonical tags and OG URLs (if your generator outputs them)
- your DNS provider’s redirect behavior (if you redirect apex ↔ www)

### Redirect strategy (keep it simple)

GitHub Pages can serve one custom domain per site. If you want both apex and `www` to work, you typically set one as canonical in Pages and handle the other with a redirect at the DNS provider/edge layer you control.

Practical examples:

| Goal | Recommended approach | Why |
|---|---|---|
| Use `www` as canonical | Set Pages domain to `www`, redirect apex → `www` | CNAME on `www` is usually simplest; redirect keeps one canonical URL |
| Use apex as canonical | Set Pages domain to apex, redirect `www` → apex | Works if your DNS provider supports apex routing cleanly |
| Avoid double redirects | Keep redirects to one hop | Fewer hops improves UX and reduces debugging ambiguity |

Validate redirect hygiene with:

```bash
curl -I http://example.com/
curl -I https://example.com/
curl -I http://www.example.com/
curl -I https://www.example.com/
```

You want a predictable pattern: everything ends up at the canonical HTTPS URL with minimal hops.

## Security and Scope Notes (Important Limitations)

GitHub Pages is static hosting. It is great for docs, portfolios, and content sites, but GitHub Docs explicitly warns:

> Paraphrased: GitHub Pages should not be used for sensitive transactions like sending passwords or credit card numbers.
> — GitHub Docs, adapted

If you need authentication, payments, or user data handling, treat Pages as a front-end only and use a proper backend with security controls.

## HTTPS Validation Checklist (What “Done” Looks Like)

After you enable Enforce HTTPS, do a quick production validation pass:

- [ ] HTTP redirects to HTTPS for the canonical hostname
- [ ] The certificate is valid in the browser (no interstitial errors)
- [ ] Homepage and one deep link load over HTTPS
- [ ] No mixed content warnings in DevTools
- [ ] Key third-party scripts load over HTTPS (analytics, embeds)
- [ ] Your 404 page is served over HTTPS (test a fake URL)

If one of these fails, don’t guess. Use the troubleshooting map and isolate the failure:

- DNS and certificate provisioning problems show up before the page renders correctly.
- Mixed content problems show up after the page renders, as missing/broken assets.

## Troubleshooting Map (Fast Diagnosis)

| Symptom | Most likely cause | Fast check |
|---|---|---|
| Enforce HTTPS is disabled | Certificate not provisioned | Validate DNS, wait for provisioning, then re-check Pages settings |
| Certificate not yet created | DNS check fails | Verify DNS records and re-add custom domain if required |
| HTTPS loads, but page looks broken | Mixed content blocked | DevTools: identify HTTP resources and update to HTTPS |
| Only custom domain fails | Wrong record/host | Compare `dig` output to GitHub Docs recommended record types |
| HTTPS works sometimes | Cache/propagation | Wait for propagation; re-test from another network |

## Common Mistakes

1. **Debugging TLS before DNS** — certificate provisioning depends on DNS being correct.
2. **Enabling HTTPS but ignoring mixed content** — one HTTP script can break your “secure” page.
3. **Using the wrong canonical host** — mixing apex and `www` creates confusing redirects and duplicate URLs.
4. **Assuming Pages is a secure app host** — static hosting is not a backend; do not handle sensitive transactions on Pages.
5. **Not validating redirects** — always confirm HTTP redirects to HTTPS after enabling enforcement.

## Frequently Asked Questions

### Is HTTPS automatic for GitHub Pages?

GitHub Pages supports HTTPS for all sites. Sites on the default `github.io` domain are typically served over HTTPS automatically, and custom domains can also use HTTPS after DNS is configured and a certificate is provisioned.

### Why is Enforce HTTPS disabled?

Enforce HTTPS only becomes available after GitHub can provision a certificate for your domain. Fix DNS issues and allow time for provisioning, then enable Enforce HTTPS in Settings → Pages.

### What does Certificate not yet created mean?

It usually means GitHub cannot complete the automatic DNS validation required for certificate provisioning. Re-check DNS records and the configured custom domain, and if you recently changed DNS, consider removing and re-adding the domain as GitHub’s troubleshooting guide suggests.

### Why do I see mixed content warnings on HTTPS?

Your HTTPS page is still loading one or more resources over HTTP. Update those URLs to HTTPS (or use relative URLs), and ensure third-party scripts support HTTPS.

### Should I use GitHub Pages for sensitive transactions?

No. GitHub Docs warns that GitHub Pages sites should not be used for sensitive transactions like sending passwords or credit card numbers.

## Conclusion

GitHub Pages HTTPS is reliable when you treat it as an ordered checklist:

1) publish the site successfully,  
2) configure DNS and the custom domain,  
3) wait for certificate provisioning,  
4) enable Enforce HTTPS, and  
5) fix mixed content so everything loads over HTTPS.

Most issues become straightforward once you separate “site publishing” from “certificate provisioning” and use DevTools to find mixed-content resources.

If you maintain multiple Pages sites, keep a tiny HTTPS runbook (DNS records, canonical host choice, validation commands). It turns “mysterious HTTPS” into a predictable checklist.

## References

1. [GitHub Docs: Securing your GitHub Pages site with HTTPS](https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https)
2. [GitHub Docs: Troubleshooting custom domains and GitHub Pages](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/troubleshooting-custom-domains-and-github-pages)
3. [GitHub Docs: Managing a custom domain for your GitHub Pages site](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)
4. [GitHub Docs: About GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages)
5. [MDN Web Docs: HTTPS](https://developer.mozilla.org/en-US/docs/Glossary/HTTPS)
6. [MDN Web Docs: Mixed content](https://developer.mozilla.org/en-US/docs/Web/Security/Mixed_content)
