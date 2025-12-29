---
title: GitHub Pages Custom Domain
description: Step-by-step guide to set up a GitHub Pages custom domain (apex or www), enable HTTPS, and avoid common DNS and verification pitfalls.
date: 2026-01-02T08:37:33+08:00
draft: false
keywords:
- github pages custom domain
- github pages dns
- github pages enforce https
- verify custom domain github pages
pillar: /github-pages/
priority: P0
commercial_value: 3
affiliate_products: []
faq:
- question: Should I use apex or www for GitHub Pages?
  answer: For most sites, www (a subdomain) is simpler because you can point it
    to GitHub Pages with a CNAME record. Apex domains (example.com) typically require
    A/AAAA records (or a DNS provider feature like CNAME flattening/ALIAS). If you
    want the least DNS friction, start with www.
- question: Why is “Enforce HTTPS” disabled or missing in GitHub Pages?
  answer: GitHub Pages only enables HTTPS after your DNS is correctly pointed at
    GitHub and the certificate is provisioned. Fix DNS first, then allow time for
    provisioning (GitHub Docs notes it can take up to an hour after configuring your
    custom domain).
- question: Do I need a CNAME file in my repository?
  answer: GitHub Pages uses a CNAME file to remember your custom domain. If you
    deploy from a branch, GitHub may add it for you when you set the custom domain
    in Settings. If you deploy via GitHub Actions, ensure your published output
    includes the CNAME file.
- question: Can I use the same custom domain for multiple GitHub Pages sites?
  answer: Not at the same time. A domain can only resolve to one site at a time in
    DNS. If you “reuse” the same domain across repos, you must switch DNS and the
    Pages custom domain setting accordingly.
- question: How do I prevent someone else from using my domain on GitHub Pages?
  answer: Use GitHub Pages domain verification. GitHub Docs recommends verifying
    your domain—especially if you use wildcard DNS—so only you can configure GitHub
    Pages sites with that domain.
howto:
  name: How to set up a GitHub Pages custom domain
  totalTime: PT30M
  steps:
  - name: Decide apex vs www
    text: Choose whether you will use example.com (apex) or www.example.com (subdomain).
      www is usually simpler for GitHub Pages because it supports CNAME.
  - name: Add DNS records
    text: Point your domain to GitHub Pages with the correct A/AAAA records (apex)
      or a CNAME record (www). Wait for DNS propagation.
  - name: Configure GitHub Pages settings
    text: In the repo’s Settings → Pages, set the custom domain and confirm DNS checks
      pass.
  - name: Enable HTTPS and verify domain
    text: Turn on Enforce HTTPS once available, and verify your domain to reduce
      takeover risk (recommended for wildcard DNS).
lastmod: '2025-12-29T20:05:34+08:00'
type: cluster
---
Setting up a GitHub Pages custom domain is mostly a DNS problem, not a “GitHub” problem. Once the DNS points to the correct place, Pages can publish the same static site you already have—but with your own domain and (usually) HTTPS.

This guide walks through a safe setup path: pick the right domain shape (apex vs `www`), configure DNS, connect the domain in GitHub Pages settings, enable HTTPS, and (optionally but strongly recommended) verify the domain to reduce hijacking/takeover risk.

## Key Takeaways

- **Start with `www` unless you have a reason not to**: subdomains can use a simple CNAME to GitHub Pages; apex domains often require A/AAAA (or provider features like CNAME flattening).
- **DNS first, GitHub second**: don’t debug Pages UI until `dig`/`nslookup` confirms your records are correct.
- **Expect propagation + certificate time**: DNS changes and HTTPS provisioning are not instant; GitHub Docs notes it can take up to an hour for your site to become available over HTTPS after you configure your custom domain.
- **Use domain verification for safety**: GitHub recommends verifying your domain, especially if you use wildcard DNS.
- **Keep it reproducible**: record your DNS records, repo settings, and validation commands in a runbook so you can re-do it later.

## What is a GitHub Pages Custom Domain?

By default, GitHub Pages sites live under GitHub’s domain:

- user/org site: `https://<user>.github.io/`
- project site: `https://<user>.github.io/<repo>/`

A **custom domain** means you serve the same site from your own domain, like `https://example.com/` or `https://www.example.com/`.

Under the hood:

1. Your DNS records route the domain to GitHub Pages.
2. GitHub Pages serves your published static files.
3. GitHub can provision a TLS certificate so your site supports HTTPS.

GitHub Docs describes this flow and the DNS record types required to point an apex or subdomain at Pages.

## Why a Custom Domain Matters

A custom domain is not just branding. It improves:

- **Trust**: `example.com` usually looks more credible than a platform subdomain.
- **Portability**: you can move hosts later without changing the public URL; you update DNS instead.
- **SEO hygiene**: consistent canonical URLs reduce duplication and split signals.

But it also adds operational surface area: DNS, certificate provisioning, and security considerations (domain verification).

## Step-by-Step: Set Up a GitHub Pages Custom Domain (Safe Path)

### Step 1: Decide apex vs `www`

You typically choose one of these:

- **Apex**: `example.com`
- **Subdomain**: `www.example.com`

Practical trade-off:

- `www` is simpler because GitHub Pages supports pointing a subdomain to Pages with a CNAME record.
- Apex domains cannot use a CNAME in “pure DNS” (many providers offer workarounds such as ALIAS/ANAME or CNAME flattening).

If you want the least friction: use `www` as the primary domain and optionally redirect apex → `www` using your DNS provider or another layer you control.

### Step 2: Add DNS records (the part that actually matters)

#### Option A: `www.example.com` (recommended)

Create a CNAME record:

- **Name/Host**: `www`
- **Type**: `CNAME`
- **Target**: `<user>.github.io`

GitHub Docs documents using CNAME records for subdomains pointing to Pages.

#### Option B: `example.com` (apex/root domain)

GitHub Docs provides A and AAAA records for apex domains. As of the referenced documentation, the A records are:

- `185.199.108.153`
- `185.199.109.153`
- `185.199.110.153`
- `185.199.111.153`

And the AAAA records are:

- `2606:50c0:8000::153`
- `2606:50c0:8001::153`
- `2606:50c0:8002::153`
- `2606:50c0:8003::153`

Important: treat these as “check the docs” values—always verify the current IPs in GitHub Docs before you rely on them.

#### DNS record cheat sheet

| Domain | Record type | What you set | When to use |
|---|---|---|---|
| `www.example.com` | CNAME | `<user>.github.io` | Recommended default for Pages |
| `example.com` | A | GitHub Pages A records | Apex domain without provider-specific features |
| `example.com` | AAAA | GitHub Pages AAAA records | IPv6 support for apex domain |

### Step 2.5: Understand what changes for project sites

If your Pages site is a **project site** (served under `/<repo>/` on the default domain), moving to a custom domain typically changes your public base path to `/`. That is a good thing, but it can break sites that hard-code the repo prefix in links or asset URLs.

Before you flip the switch, scan for:

- absolute links that include `/<repo>/...`
- generator base path settings that are tied to the project-site URL
- hard-coded canonical URLs that still point to `<user>.github.io`

The easiest way to avoid surprises is to use relative URLs where possible, and to keep base-path configuration in a single place (for example, `_config.yml` for Jekyll or a single `baseURL`/`publicPath` setting for your generator).

#### What about “CNAME flattening” / ALIAS / ANAME?

Some DNS providers (Cloudflare included) offer features that let you use a CNAME-like workflow at the apex by returning A/AAAA answers at query time (commonly called “CNAME flattening”). Cloudflare documents how CNAME flattening works and when it applies.

If your DNS provider supports it, you can keep your apex setup closer to the `www` flow—but you should still validate the resolved A/AAAA answers with `dig`.

### Step 3: Configure the custom domain in GitHub Pages

In your repository:

1. Go to **Settings → Pages**.
2. Find **Custom domain**.
3. Enter your domain (for example `www.example.com`).

GitHub Docs notes that when you set a custom domain, GitHub Pages may create a commit that adds a `CNAME` file to the publishing source. That `CNAME` file is how Pages remembers the domain for branch-based publishing.

If you deploy via GitHub Actions, make sure the published output includes a `CNAME` file so the domain stays attached to your site.

### Step 4: Validate DNS + Pages resolution

Before debugging “GitHub settings”, validate DNS directly:

```bash
# Replace with your domain
dig +short www.example.com CNAME
dig +short example.com A
dig +short example.com AAAA
```

What you want to see:

- `www.example.com` returns a CNAME to `<user>.github.io`
- `example.com` returns the GitHub Pages A/AAAA answers (or your provider’s flattened results)

Then validate HTTP:

```bash
curl -I https://www.example.com/
```

### Step 5: Enable HTTPS (and understand the waiting time)

GitHub Pages can provision certificates and lets you enable **Enforce HTTPS**. GitHub Docs notes it can take up to an hour for your site to become available over HTTPS after you configure your custom domain.

> It can take up to an hour for your site to become available over HTTPS after you configure your custom domain.
> — GitHub Docs (Troubleshooting custom domains and GitHub Pages), adapted

If “Enforce HTTPS” is disabled:

1. Re-check DNS first (wrong records are the #1 cause).
2. Confirm the custom domain is set in Pages settings.
3. Wait for certificate provisioning to complete.

### Step 6 (Recommended): Verify your domain

Domain verification is a safety feature. GitHub Docs recommends verifying your domain, especially if you use wildcard DNS records:

- verification requires adding a TXT record to your domain
- once verified, only your GitHub account can use that domain for GitHub Pages

> GitHub recommends verifying your domain, particularly when using wildcard DNS records.
> — GitHub Docs (Verifying your custom domain for GitHub Pages), adapted

This reduces the chance of “domain takeover” style issues where a third party can configure a Pages site that appears to be on your domain.

## Migration Checklist (Default Domain → Custom Domain)

If you already have a working site at `<user>.github.io` and you’re moving to `example.com`, do a quick migration pass before you declare the domain “done”:

1. **Pick a canonical hostname**: decide whether `example.com` or `www.example.com` is the primary URL and stick to it everywhere (site config, canonical tags, social links).
2. **Update generator base path**:
   - project site → custom domain often changes base path from `/<repo>/` to `/`
   - fix your generator config so links/assets are correct for the new base path
3. **Remove hard-coded hostnames**: search for `<user>.github.io` in your repository and replace with the custom domain (or use relative URLs).
4. **Confirm the `CNAME` file behavior**: if you deploy via Actions, verify that the final published output includes the `CNAME` file so Pages keeps the mapping.
5. **Test deep links**: open a few nested URLs and confirm:
   - the page loads (no 404)
   - assets load (no CSS/JS 404)
   - the 404 page behaves as expected
6. **Validate HTTP behavior**: use `curl -I` for both HTTP and HTTPS to confirm the final redirects and status codes match your expectations.

This sounds like extra work, but it is much faster than discovering broken assets after a search engine has already crawled the new domain.

## Troubleshooting (Common Failures and Fixes)

| Symptom | Likely cause | Fast fix |
|---|---|---|
| Pages shows a default 404 page | DNS isn’t pointing at Pages or custom domain not set | Re-check DNS records and set custom domain in Settings → Pages |
| “DNS check unsuccessful” | Wrong record type/target or propagation not finished | Validate with `dig`, fix record, wait for propagation |
| “Enforce HTTPS” disabled | DNS misconfigured or certificate not provisioned yet | Fix DNS; wait up to an hour after DNS is correct |
| Apex domain won’t accept a CNAME | DNS rules for apex | Use A/AAAA from GitHub Docs or use a provider feature (ALIAS / CNAME flattening) |
| You lose the custom domain after rebuild | Missing `CNAME` in published output | Ensure `CNAME` is present in the publishing source/output |

## Best Practices

1. **Prefer `www` as the primary domain**: it’s operationally simpler and easier to migrate later.
2. **Treat DNS changes like deployments**: document records, keep a rollback plan (restore old records), and validate with `dig`.
3. **Use a low TTL during migrations**: lower TTL reduces how long bad records stick around while you fix them.
4. **Verify the domain**: domain verification is a low-effort, high-value safety step.
5. **Keep HTTPS enforced**: once certificate provisioning is stable, enable “Enforce HTTPS” and avoid mixed-content issues.

## Common Mistakes

1. **Mixing apex and `www` without a plan** — decide which is canonical, then redirect/standardize.
2. **Setting a CNAME at the apex without provider support** — use A/AAAA or a provider feature like CNAME flattening.
3. **Assuming DNS is instant** — always validate with `dig` and allow time for propagation.
4. **Forgetting the `CNAME` file when using GitHub Actions** — ensure the published output includes it.
5. **Skipping domain verification with wildcard DNS** — this increases risk and is avoidable.

## Frequently Asked Questions

### Should I use apex or www for GitHub Pages?

For most sites, `www` is simpler because you can use a single CNAME record. Apex domains often require A/AAAA records or a DNS provider feature (ALIAS/ANAME/CNAME flattening). If you want the least DNS friction, use `www` as the canonical domain.

### Why is “Enforce HTTPS” disabled or missing in GitHub Pages?

GitHub Pages only enables HTTPS after your DNS is correctly pointed to GitHub and a certificate is provisioned. Fix DNS first, then allow time for provisioning—GitHub Docs notes it can take up to an hour after you configure your custom domain.

### Do I need a CNAME file in my repository?

Yes, in most workflows. GitHub Pages uses a `CNAME` file to remember your custom domain. For branch publishing, GitHub may create it when you set the domain in Settings. For Actions publishing, ensure your build/deploy step includes it in the published output.

### Can I use the same custom domain for multiple GitHub Pages sites?

Not simultaneously. DNS routes the domain to one target at a time, and the Pages custom domain setting is effectively “one domain → one site.” If you need multiple sites, use subdomains (`docs.example.com`, `blog.example.com`) instead of trying to reuse the same apex.

### How do I prevent someone else from using my domain on GitHub Pages?

Verify your domain in GitHub. GitHub Docs recommends verifying your domain, especially if you use wildcard DNS, so only your account can configure GitHub Pages sites with that domain.

## Conclusion

GitHub Pages custom domains are straightforward when you approach them in the right order:

1) decide apex vs `www`,  
2) configure DNS and validate it with `dig`,  
3) set the custom domain in GitHub Pages,  
4) enable HTTPS, and  
5) verify the domain for safety.

If you get stuck, treat it as a DNS/debugging exercise: confirm records, confirm the published site exists, then confirm HTTPS provisioning.

## References

1. [GitHub Docs: Managing a custom domain for your GitHub Pages site](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)
2. [GitHub Docs: Verifying your custom domain for GitHub Pages](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages)
3. [GitHub Docs: Securing your GitHub Pages site with HTTPS](https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https)
4. [GitHub Docs: Troubleshooting custom domains and GitHub Pages](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/troubleshooting-custom-domains-and-github-pages)
5. [GitHub Docs: About GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages)
6. [Cloudflare Docs: CNAME flattening](https://developers.cloudflare.com/dns/cname-flattening/)
