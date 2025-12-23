---
title: GitHub Pages
description: 'Learn GitHub Pages: custom domains, Jekyll, hosting, redirects, and
  common pitfalls.'
date: 2025-12-23 12:11:00+08:00
draft: false
commercial_value: 3
faq:
- question: What is GitHub Pages?
  answer: GitHub Pages is a static site hosting service that publishes content from
    a GitHub repository (with optional Jekyll builds) to a public URL.
- question: Why does GitHub Pages matter?
  answer: It’s a simple, low-cost way to publish docs and portfolios using Git workflows,
    with HTTPS and custom domains supported.
- question: How do I get started with GitHub Pages?
  answer: Create a repository, push a static site (or generator output), then enable
    Pages in repository settings and pick the source branch/folder.
- question: What are common mistakes with GitHub Pages?
  answer: Misconfigured base paths for SPAs, missing CNAME/DNS records for custom domains,
    and build outputs committed to the wrong branch/folder.
- question: What tools are best for GitHub Pages?
  answer: A static site generator (Jekyll/Hugo), GitHub Actions for builds, and a DNS
    provider for domain/HTTPS configuration.
keywords:
- github pages
---

GitHub Pages is a lightweight way to publish a **static website** directly from a GitHub repository. It’s commonly used for documentation sites, personal portfolios, project landing pages, and simple marketing pages—especially when you want “push to Git → site updates” with minimal ops.

This pillar is a practical, end-to-end guide to GitHub Pages in 2025: site types, publishing sources (branch vs GitHub Actions), custom domains and DNS, HTTPS, and the most common failure modes (404s, broken assets, and CNAME-related surprises).

## Key Takeaways

- **Static hosting, Git workflow**: GitHub Pages hosts static files; you deploy by pushing to Git or running a Pages workflow.
- **Two publishing models**: publish from a branch/folder (simple) or publish via a custom GitHub Actions workflow (more control).
- **Custom domains are doable (and easy to break)**: apex vs subdomain configuration is different; CNAME files and DNS records matter.
- **HTTPS is supported**: you can enforce HTTPS and GitHub provisions certificates for correctly configured custom domains.
- **Most issues are predictable**: missing `index.html`, wrong source folder, overwritten `CNAME`, broken base paths, or DNS mistakes.

## What is GitHub Pages?

GitHub Pages is a hosting feature that serves static files (HTML/CSS/JS and assets) from a GitHub repository. You choose a **publishing source** (a branch + folder, or a GitHub Actions workflow), and GitHub builds/deploys your site to a predictable URL.

> Paraphrased: GitHub Pages can publish when changes are pushed to a specific branch, or you can publish via a custom GitHub Actions workflow.
> — GitHub Docs, “Configuring a publishing source for your GitHub Pages site” (adapted)

### What GitHub Pages is (and is not)

- **It is**: static hosting for files you commit or generate during a build (think docs, portfolios, landing pages).
- **It is not**: a general-purpose backend runtime. GitHub Pages does not support server-side languages like PHP, Ruby, or Python.

If you need server-side rendering, databases, long-running background jobs, or custom server middleware, you’ll likely want a different hosting model (or keep GitHub Pages for the static portion and use APIs elsewhere).

## How GitHub Pages Works (In Practice)

At a high level, Pages is a pipeline:

1. You push content (or content source) to a GitHub repository.
2. GitHub builds your site (either automatically via the Pages build flow, or via your GitHub Actions workflow).
3. GitHub deploys static output to Pages infrastructure and serves it under a default domain (and optionally your custom domain).

Two details matter for almost every setup:

- **Entry file**: GitHub Pages expects an entry file such as `index.html` (and for some flows, `index.md` or `README.md` can act as entry content). The entry file must be at the top level of the publishing source folder (or at the top of the deployed artifact if you publish via Actions).
- **Publishing source**: branch/folder vs GitHub Actions changes how you structure your repository, where build output lives, and how you handle `CNAME`.

## Why GitHub Pages Matters

- **Low overhead**: no server to manage, no database, and a simple deployment model.
- **Trust and portability**: content lives in Git, versioned and reviewable like code.
- **Fast iteration**: combine Markdown + generator + CI for a docs workflow that scales.
- **Good enough performance**: static assets are easy to cache and serve quickly.

For a lot of developer-facing content, GitHub Pages is the “80/20” hosting choice: it gives you a stable URL and deployment story without forcing you into a platform-specific build pipeline—unless you want one.

## Site Types and Default URLs

GitHub Pages is commonly described in terms of **site types** because the default URL and base path behavior differs.

| Site type | Typical use | Default URL pattern | Base path gotcha |
|----------|-------------|---------------------|------------------|
| User / org site | Personal or org homepage | `https://<user>.github.io/` | Usually served at `/` |
| Project site | Project docs/landing page | `https://<user>.github.io/<repo>/` | Assets and routing often need `/<repo>/` base path |
| Docs-in-repo | Docs for an existing repo | Depends on settings | The entry file must be top-level in chosen source folder |

If you’re deploying a single-page application (SPA) to a **project site**, the base path is where most issues happen: local dev may work, but production breaks because assets and routes are expected under `/<repo>/`.

## Step-by-Step: Publish a Site Safely

This checklist is designed to minimize “works locally but not on Pages” failures.

1. **Decide your publishing source**: “Deploy from a branch” if you want the simplest flow; “GitHub Actions” if you need a non-Jekyll build, a custom build pipeline, or want to avoid committing compiled output to a branch.
2. **Create your entry file**: ensure `index.html` (or your generator output) is at the top level of the publishing source folder (or top of the Actions artifact).
3. **Configure Pages settings**: in your repository, go to **Settings → Pages**, then choose the source (branch/folder or GitHub Actions).
4. **Verify the build/deploy path**: confirm the output directory matches what Pages expects (for example, your generator’s output folder).
5. **Smoke test URLs**: visit the default Pages URL and validate key paths (homepage, a deep link, and at least one static asset).
6. **Add a custom domain (optional)**: set it in Pages settings first, then update DNS records; wait for DNS propagation.
7. **Enforce HTTPS (optional, recommended)**: after the domain is configured and certificate is provisioned, enable “Enforce HTTPS”.

> Paraphrased: GitHub Pages looks for an `index.html` entry file, and it must be at the top level of your chosen publishing source (or the top of the deployed artifact).
> — GitHub Docs, “Creating a GitHub Pages site” and “Troubleshooting 404 errors for GitHub Pages sites” (adapted)

## Publishing Sources: Branch vs GitHub Actions

The publishing source choice drives almost everything else: repo layout, build output location, and how you debug failures.

| Publishing source | Best for | How it works | Key trade-offs |
|------------------|----------|--------------|----------------|
| Deploy from a branch | Simple static sites, Jekyll-by-default | GitHub publishes a chosen branch + folder (root or `/docs`) | Less control over build; non-Jekyll setups need extra care |
| GitHub Actions workflow | Hugo/Next.js static export, custom build steps | A workflow builds output and deploys an artifact | More moving parts; you maintain CI configuration |

GitHub’s own guidance is pragmatic:

- If you **don’t** need build control, publish from a **branch**.
- If you want a build process **other than Jekyll**, or you don’t want a dedicated branch containing compiled output, publish with a **GitHub Actions workflow**.

### A note on Jekyll and `.nojekyll`

If you publish from a source branch, GitHub Pages will use Jekyll by default. If your output includes folders that Jekyll would normally ignore (for example, paths starting with `_`), or you are using a non-Jekyll build where the output is already final, add an empty `.nojekyll` file to the publishing root to bypass the Jekyll build step.

## Repository Layout Patterns (What Actually Works)

GitHub Pages is flexible, but not every repository layout is equally pleasant to maintain. These three patterns cover most real-world scenarios.

| Pattern | When to use it | Publishing source | Pros | Cons |
|--------|-----------------|------------------|------|------|
| `docs/` in default branch | Code repo that needs docs | Deploy from branch + `/docs` | Keeps docs next to code; minimal CI | Easy to break if `/docs` is removed/moved |
| Separate `gh-pages` branch | Generator output committed as static files | Deploy from branch + `gh-pages` root | Simple serving; no build step on Pages | You must keep build output in sync |
| Actions build → Pages deploy | Any non-Jekyll build (Hugo, static export, custom tooling) | GitHub Actions | Full control; no compiled branch in Git | Requires CI config and troubleshooting |

### Choosing between `docs/` and `gh-pages`

- Prefer **`/docs`** if your site is documentation for a codebase and you want docs changes reviewed like code changes.
- Prefer **`gh-pages`** if your workflow already produces a fully built output directory and you want Pages to serve it with minimal “smart build” behavior.

If you use external CI that commits build output to `gh-pages`, GitHub notes that Pages will still deploy via a GitHub Actions workflow run; the workflow detects whether a build step is needed and deploys what’s already in the branch.

### A practical rule: keep the publishing root deterministic

Most Pages incidents come down to “the publishing root isn’t what I think it is.” Make the publishing root deterministic:

- Ensure the build output always contains `index.html` at the top level.
- Keep `CNAME` (for branch publishing) and `.nojekyll` (for non-Jekyll output) in the publishing root.
- Avoid force-pushing generated output if it can drop `CNAME` or other required files.

## SPA Routing and Base Paths (The #1 Project Site Pitfall)

If your site is a single-page application, GitHub Pages behaves differently from a dev server:

- Pages is static hosting: deep links like `/docs/getting-started` don’t “route” unless a file exists at that path.
- Project sites live under a prefix like `/<repo>/`, so asset URLs and router base paths often need to include that prefix.

Here’s a safe mental model:

1. **User/org sites** behave like a site at `/` (base path is root).
2. **Project sites** behave like a site mounted under a subfolder `/<repo>/`.

### Checklist for SPA deployments

1. **Set a base path** for your router (for example, React Router `basename`) that matches the Pages prefix.
2. **Use relative or correct-prefixed asset URLs** so CSS/JS loads from the right location.
3. **Decide how to handle deep links**: either generate static files for routes (preferred) or use a fallback strategy (such as a `404.html` that loads your app), understanding that fallback hacks can complicate caching and debugging.

If you can access the homepage but links break across the site (especially after adding/removing a custom domain), GitHub’s 404 troubleshooting guide suggests triggering a rebuild and ensuring routing paths match the published URL structure.

## Custom Domains, DNS, and the `CNAME` File

Custom domains are often the most time-consuming part of GitHub Pages—not because it’s hard, but because DNS has sharp edges: propagation delays, conflicting records, and easy-to-miss differences between apex domains and subdomains.

> Paraphrased: GitHub Pages supports custom domains, letting you use any domain you own instead of the default `*.github.io` URL.
> — GitHub Docs, “About custom domains and GitHub Pages” (adapted)

### Subdomain vs apex domain

- A **subdomain** is something like `www.example.com` or `blog.example.com`. GitHub recommends `www` as the most stable option.
- An **apex domain** is the root domain, like `example.com`. Apex domains use **A / AAAA** records or **ALIAS / ANAME** records (depending on your DNS provider).

### Why you should set the domain in GitHub first

GitHub explicitly warns that configuring DNS for a custom domain before adding it in GitHub can create takeover risk (someone else could potentially serve content at that domain if it points at Pages but isn’t bound to your repo). A safer order is:

1. Set the custom domain in **Pages settings**.
2. Then configure DNS records at your DNS provider.

### How `CNAME` behaves

GitHub Pages uses a `CNAME` file as the stored source-of-truth for branch-based publishing:

- If you publish from a **branch**, saving the custom domain in Pages settings creates a commit that adds a `CNAME` file to the root of your publishing source.
- If you publish from a **custom GitHub Actions workflow**, no `CNAME` file is created, and any existing `CNAME` file is ignored.

This difference is a common source of confusion when migrating between branch-based publishing and Actions-based publishing.

### DNS records you’ll commonly use

This table summarizes the most common DNS configurations from GitHub’s documentation. Always verify against the latest GitHub Docs for your scenario and DNS provider capabilities.

| Scenario | Record type | Name | Value |
|----------|------------|------|-------|
| Apex domain (`example.com`) | `A` | `@` | `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153` |
| Apex domain (`example.com`) | `AAAA` (optional) | `@` | `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153` |
| Apex domain (`example.com`) | `ALIAS` / `ANAME` (provider-specific) | `@` | `USERNAME.github.io` |
| Subdomain (`www.example.com`) | `CNAME` | `www` | `USERNAME.github.io` (exclude the repository name) |

GitHub’s docs also recommend **not** using wildcard DNS records like `*.example.com`, and recommend adding a `www` subdomain even if you also use the apex domain (to support stable redirects and HTTPS).

### Verify DNS quickly with `dig`

When debugging, use `dig` (or an online DNS lookup tool) to confirm what the internet actually sees.

```bash
# Apex domain A records
dig EXAMPLE.COM +noall +answer -t A

# Apex domain AAAA records
dig EXAMPLE.COM +noall +answer -t AAAA

# Subdomain CNAME chain
dig WWW.EXAMPLE.COM +nostats +nocomments +nocmd
```

If you’re not getting the expected records, wait for propagation (GitHub notes this can take up to 24 hours) or check for conflicting DNS records.

## HTTPS: Enforcing Encryption and Avoiding “Certificate not yet created”

GitHub Pages supports HTTPS for `github.io` domains automatically (for sites created after mid-2016) and supports HTTPS for correctly configured custom domains. You can also **enforce HTTPS**, which transparently redirects HTTP traffic to HTTPS.

> Paraphrased: You can enforce HTTPS for your GitHub Pages site to redirect all HTTP requests to HTTPS, and GitHub provisions TLS certificates for correctly configured custom domains.
> — GitHub Docs, “Securing your GitHub Pages site with HTTPS” (adapted)

### What happens during certificate provisioning

When you set or change a custom domain in Pages settings, GitHub runs an automatic DNS check. If your DNS configuration passes, GitHub requests a TLS certificate from Let’s Encrypt and deploys it to the Pages infrastructure. If it stalls, GitHub’s guidance is to remove and re-add the custom domain to restart provisioning.

Two practical tips:

- **CAA records**: if you use Certification Authority Authorization (CAA) records, GitHub Docs notes you need at least one CAA record allowing `letsencrypt.org`.
- **Mixed content**: if your HTML references assets over `http://`, browsers may warn or block them. Fix by switching assets to `https://`.

## Common Mistakes (and How to Avoid Them)

These are the patterns that show up again and again in Pages debugging.

1. **Missing or misplaced `index.html`**: GitHub Pages expects `index.html` at the top level of your publishing source (or top of your Actions artifact). Also: filename casing matters (`Index.html` won’t work).
2. **Wrong publishing source**: publishing from `/docs` but deleting the folder later, or pointing Pages settings at the wrong branch/folder.
3. **CNAME file accidentally overwritten**: some generators or deploy scripts force-push build output and drop the `CNAME` file that GitHub added. If you build locally and push generated files, pull the commit that created `CNAME` so it’s included in your output.
4. **Broken base path on project sites**: assets and routes may need a `/<repo>/` base path. This hits SPAs especially hard: you can load the homepage but deep links 404.
5. **DNS mismatches and extra records**: apex domains need the correct A/AAAA (or ALIAS/ANAME) configuration; extra conflicting records can break HTTPS provisioning.
6. **Automation surprises**: GitHub Docs notes that commits pushed by a GitHub Actions workflow using `GITHUB_TOKEN` do not trigger a Pages build for branch-based publishing; use the recommended Pages workflow approach instead.

## Comparison Table: GitHub Pages vs Netlify vs Vercel

GitHub Pages is not trying to be a full deployment platform. It’s best viewed as “static hosting with a Git-native workflow.”

| Platform | Best For | Pros | Cons |
|---------|----------|------|------|
| GitHub Pages | Docs/portfolios, simple marketing pages | Free for many use cases, simple, GitHub-native | Static-only; SPA routing/base path pitfalls; fewer runtime features |
| Netlify | Static sites with rich build/deploy UX | Strong previews, build plugins, good DX | More platform surface area; costs can rise with traffic/build minutes |
| Vercel | Framework-centric frontends (especially Next.js) | Great preview workflows, first-class framework features | Best fit depends on architecture; pricing and limits vary by plan |

## Best Practices (Battle-Tested)

1. **Choose the simplest publishing source that fits**: branch-based for basic sites; GitHub Actions when you need custom builds.
2. **Keep the publishing root clean**: ensure the deployed output root contains `index.html` and that asset paths are correct.
3. **Treat custom domains as “infrastructure”**: document DNS records, avoid wildcard DNS, and verify your domain if you can.
4. **Use `www` even if you want apex**: it’s stable and makes redirects/HTTPS behavior more predictable.
5. **Check workflow runs when something breaks**: Pages deployments are visible via workflow runs; use them as your primary debugging surface.

## Conclusion

GitHub Pages is one of the most pragmatic ways to ship a static site: it’s simple, cheap, and tightly integrated with how developers already work. Most problems are configuration issues you can prevent with a small checklist: pick the right publishing source, keep `index.html` at the expected location, treat custom domain DNS as production configuration, and enforce HTTPS once the certificate is provisioned.

## References

1. [GitHub Docs: GitHub Pages](https://docs.github.com/en/pages)
2. [GitHub Docs: Creating a GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)
3. [GitHub Docs: Configuring a publishing source for your GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
4. [GitHub Docs: About custom domains and GitHub Pages](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/about-custom-domains-and-github-pages)
5. [GitHub Docs: Managing a custom domain for your GitHub Pages site](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)
6. [GitHub Docs: Troubleshooting custom domains and GitHub Pages](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/troubleshooting-custom-domains-and-github-pages)
7. [GitHub Docs: Securing your GitHub Pages site with HTTPS](https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https)
8. [GitHub Docs: Troubleshooting 404 errors for GitHub Pages sites](https://docs.github.com/en/pages/getting-started-with-github-pages/troubleshooting-404-errors-for-github-pages-sites)
9. [Jekyll Docs](https://jekyllrb.com/docs/)
10. [Hugo Docs](https://gohugo.io/documentation/)
