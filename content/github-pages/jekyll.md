---
title: GitHub Pages Jekyll
description: A practical guide to using Jekyll on GitHub Pages, including local builds, baseurl pitfalls, plugin limits, and when to switch to GitHub Actions.
date: 2026-01-02T16:38:34+08:00
draft: false
keywords:
- github pages jekyll
- github pages jekyll theme
- github pages gem
- jekyll baseurl github pages
pillar: /github-pages/
priority: P0
commercial_value: 3
affiliate_products: []
faq:
- question: Is Jekyll the default for GitHub Pages?
  answer: Yes. GitHub Pages has built-in support for Jekyll, and many sites can be
    published without writing a custom build pipeline. If you need more control, you can
    build with GitHub Actions and deploy the output.
- question: Should I use the github-pages gem or GitHub Actions?
  answer: Use GitHub Pages built-in Jekyll when you want the simplest setup. Use GitHub
    Actions when you need a custom Ruby version, extra build steps, or a build environment
    that differs from GitHub’s hosted Pages build.
- question: Why do my pages work locally but break on GitHub Pages?
  answer: Most mismatches come from baseurl settings (project sites), plugin differences,
    or building locally without matching the Pages environment. Align config and verify the
    generated output folder.
- question: How do I set baseurl correctly for project sites?
  answer: For a project site, your public path is /<repo> on the default domain. In Jekyll,
    set baseurl in _config.yml to match the repo name, and validate links and assets in the
    deployed site.
- question: Is Jekyll supported on Windows?
  answer: Jekyll itself is not officially supported on Windows according to Jekyll documentation,
    and GitHub Docs calls this out. If you develop on Windows, consider WSL or run the build in CI.
howto:
  name: How to deploy a Jekyll site on GitHub Pages
  totalTime: PT35M
  steps:
  - name: Choose a build model
    text: Decide whether GitHub Pages will build Jekyll for you, or whether you will build
      in GitHub Actions and deploy the generated site.
  - name: Configure baseurl and site URL
    text: For project sites, set baseurl to the repo path and validate internal links and assets.
  - name: Build locally and deploy
    text: Run a local build, then deploy and validate the live site URL and a deep link.
lastmod: '2025-12-29T21:02:41+08:00'
type: cluster
---
Jekyll is the “classic” GitHub Pages workflow: write Markdown, choose a theme, push to GitHub, and get a site. The confusing part is that there are now two common ways to ship a Jekyll site:

1) let GitHub Pages build Jekyll for you, or  
2) build Jekyll yourself in GitHub Actions and deploy the output.

Both can work. Most problems happen when you accidentally mix them (or you develop locally with a different environment than production). This guide shows a repeatable, low-drama path for each model, plus the baseurl and plugin gotchas that cause “it works locally but not on Pages”.

## Key Takeaways

- **Pick one build model**: GitHub-managed Jekyll is simplest; GitHub Actions gives maximum control. Mixing models creates version and plugin drift.
- **Project sites require baseurl**: your site is served under `/<repo>/` on the default domain; baseurl mistakes cause broken links and missing assets.
- **Match local to production**: if you build locally, align your environment with the GitHub Pages build (or treat CI as the source of truth).
- **Understand plugin limits**: not every Jekyll plugin is available in the GitHub Pages managed build; check supported plugins and dependencies.
- **Validate the generated output**: regardless of model, the published root must contain the correct entry files and asset paths.

## What is GitHub Pages + Jekyll?

Jekyll is a static site generator that converts Markdown and templates into a static website. GitHub Pages has built-in support for Jekyll, which is why many Pages sites can be created without a custom build pipeline.

GitHub’s Jekyll-on-Pages documentation also highlights the current direction: GitHub Actions is now the recommended approach for deploying and automating GitHub Pages sites, while the `github-pages` gem remains supported for some workflows.

> Paraphrased: The github-pages gem remains supported for some workflows, but GitHub Actions is now the recommended approach for Pages deployments.
> — GitHub Docs, adapted

In practice, “Jekyll on Pages” is a workflow decision:

- do you want GitHub to build your site, or
- do you want to build it yourself and just use Pages for hosting?

## Two Ways to Deploy a Jekyll Site

| Model | What you commit | Who builds | Pros | Cons |
|---|---|---|---|---|
| GitHub-managed Jekyll | source (Markdown, layouts, config) | GitHub Pages | simplest setup, fewer moving parts | limited plugins and environment constraints |
| Actions-built Jekyll | source + workflow | GitHub Actions | reproducible, full control over dependencies | more CI complexity; you must maintain workflow |

If your site is mostly Markdown + theme and you can live within GitHub Pages constraints, start with GitHub-managed Jekyll. If you need custom Ruby tooling, extra build steps, or strict reproducibility, prefer Actions.

## Step-by-Step: GitHub-Managed Jekyll (Simplest Path)

This is the “push and it publishes” path.

### 1) Choose the publishing source

In your repository:

1. Go to Settings → Pages
2. Choose the branch and folder (common options are the repository root or `/docs`)

GitHub’s “Create a Pages site with Jekyll” guide walks through this setup.

### 2) Create the minimum Jekyll structure

At minimum, you typically have:

- a homepage (often `index.md` or `index.html`)
- `_config.yml`

If you use themes, the theme configuration also lives in `_config.yml`.

### 3) Configure baseurl correctly (project sites)

For project sites, your deployed URL looks like:

`https://<user>.github.io/<repo>/`

This means the repo name is part of the public path. In Jekyll, that is commonly represented by `baseurl`.

Example `_config.yml` pattern:

```yaml
url: "https://<user>.github.io"
baseurl: "/<repo>"
```

If you do not set baseurl for a project site, you often get:

- working HTML (because the page exists),
- but broken assets and links (because they resolve from `/` instead of `/<repo>/`).

### 4) Deploy and validate

After you push:

1. Open the site URL
2. Open a deep link
3. Open DevTools → Network and confirm CSS/JS assets return 200

Treat “asset 404” as “baseurl or absolute path” until proven otherwise.

## Baseurl Pitfalls (And How to Avoid Them)

Baseurl issues are the #1 reason a Jekyll site “works locally” but breaks after deployment—especially for project sites on the default `github.io` domain.

### Common baseurl failure patterns

1. **Hard-coded root paths**
   - Example: CSS links like `/assets/main.css` assume the site lives at `/`.
   - On a project site, the site lives at `/<repo>/`, so `/assets/...` points to the wrong place.
2. **Theme assets that ignore baseurl**
   - Some themes are written assuming a user site (root path).
   - If the theme doesn’t use Jekyll’s URL filters, you’ll see “HTML loads but styling is gone.”
3. **Local dev vs production mismatch**
   - Locally you often run at `http://127.0.0.1:4000/` (root).
   - Production is `https://<user>.github.io/<repo>/` (subpath).

### Safer patterns in templates

When you write links in layouts/includes, prefer Jekyll’s URL helpers so you don’t manually concatenate base paths.

```liquid
<!-- Good: respects baseurl -->
<link rel="stylesheet" href="{{ "/assets/main.css" | relative_url }}">

<!-- Good: absolute URL when you need it -->
<a href="{{ "/docs/" | absolute_url }}">Docs</a>
```

If you see broken links in production, inspect the generated HTML in `/_site/` and confirm that your `<link>` and `<script>` tags contain the expected `/<repo>/` prefix.

### A quick validation checklist

- Open the homepage and confirm CSS loads.
- Open a deep link (not just `/`).
- Open DevTools → Network → filter by “CSS/JS” and confirm 200 responses.
- If assets are 404, check whether the request path starts with `/<repo>/`.

## How to Check Supported Plugins and Versions

If you let GitHub Pages build Jekyll for you, you are constrained by the Pages environment. Two practical ways to validate what’s supported:

1. **Check Pages dependency versions**
   - GitHub publishes a page showing the versions used by Pages (including the Jekyll version and key gems).
2. **Use the `github-pages` gem locally**
   - The `github-pages` gem represents the managed Pages environment, which helps reduce “it worked locally” drift.

If your required plugin isn’t available in the managed build, don’t fight it: switch to GitHub Actions, build the site yourself, and deploy the generated output.

### When to switch to GitHub Actions (Decision signals)

Use GitHub-managed Jekyll when it works, because it’s the least moving parts. Switch to Actions when you hit any of these signals:

- **You need unsupported plugins** (or you need to run custom Ruby code during build).
- **You have non-Ruby build steps**, like generating docs from OpenAPI, compiling assets, running a Node-based pipeline, or pulling content from an API.
- **You need strict reproducibility**, for example pinning Ruby, Jekyll, and gem versions exactly across all builds.
- **You want “CI as source of truth”**, where local builds are optional and the workflow always produces the deployable artifact.

This is a pragmatic boundary: Pages hosting is still great, but you move the build responsibility into CI so you can control it.

## Step-by-Step: Build Jekyll in GitHub Actions (More Control)

Use Actions when you need:

- strict dependency control,
- custom build steps (linting, extra generators),
- or to avoid differences between local builds and GitHub Pages’ hosted environment.

### 1) Choose output folder and publish model

For Actions deployment, your workflow must build the site and deploy a Pages artifact. The important rule is: the artifact must contain the generated site entry file (typically index.html) at the top level of the artifact.

### 2) Keep dependencies explicit (Gemfile + lockfile)

If you use Bundler, commit your `Gemfile` and `Gemfile.lock`. This makes the build reproducible and reduces “works on my machine” drift.

### 3) Deploy via a Pages workflow

GitHub Pages supports Actions-based workflows; you build the site, upload the artifact, then deploy it. The exact workflow steps can vary, but the success criteria are stable:

- the build produces a static output folder
- the artifact is uploaded from that folder
- the deployed site renders with correct base paths

## Plugins and the Pages Build Environment

Plugins are a common reason local builds diverge from production.

If you rely on GitHub Pages to build your Jekyll site, you are constrained by the Pages build environment. The `github-pages` gem exists to represent that environment (dependencies, supported plugins, and versions).

Practical guidance:

- If you need a plugin that is not supported in the managed Pages build, switch to Actions and build it yourself.
- If you want your local build to resemble GitHub Pages, use the `github-pages` gem when appropriate and follow GitHub’s “test locally” workflow.

## Local Development: The “Match Production” Checklist

GitHub provides a dedicated guide for testing your Pages site locally with Jekyll. Use it as your baseline.

Local checklist:

1. Install Ruby and Bundler in a clean environment.
2. Install dependencies from your Gemfile.
3. Run Jekyll via Bundler so you use the locked versions.
4. Validate that generated URLs match the final deployment URL structure.

The goal is not “it runs on my laptop”. The goal is “it builds the same output we deploy”.

## Common Mistakes

1. **Wrong baseurl for project sites** — links and assets resolve from `/` instead of `/<repo>/`.
2. **Mixing build models** — GitHub builds Jekyll sometimes, Actions builds other times; you get inconsistent output.
3. **Plugin drift** — local plugins are not available in the Pages managed build.
4. **Theme assumptions** — theme assets may assume a root path; validate with a project site URL.
5. **Windows friction** — Jekyll isn’t officially supported on Windows; use WSL or build in CI for consistency.

> Paraphrased: Jekyll is not officially supported for Windows; use supported approaches like WSL if needed.
> — GitHub Docs / Jekyll Docs, adapted

## Troubleshooting Map (Fast Diagnosis)

| Symptom | Most likely cause | First check |
|---|---|---|
| Whole site 404s | Wrong Pages publishing source | Settings → Pages configuration |
| CSS/JS missing | baseurl or absolute paths wrong | Project site URL includes `/<repo>/` |
| Builds locally but fails in GitHub | dependency drift | Gemfile.lock + build logs |
| Plugin works locally only | plugin not supported in managed build | Check `github-pages` gem supported plugins |
| Theme looks broken on project site | hard-coded `/` paths | Inspect generated HTML and asset URLs |

## Frequently Asked Questions

### Is Jekyll the default for GitHub Pages?

Yes. GitHub Pages has built-in support for Jekyll, and many sites can be published without a custom build pipeline. If you need more control, you can build with GitHub Actions and deploy the output.

### Should I use the github-pages gem or GitHub Actions?

Use GitHub Pages built-in Jekyll when you want the simplest setup. Use GitHub Actions when you need a custom Ruby version, extra build steps, or a build environment that differs from GitHub’s hosted Pages build.

### Why do my pages work locally but break on GitHub Pages?

Most mismatches come from baseurl settings (project sites), plugin differences, or building locally without matching the Pages environment. Align config and validate the generated output folder.

### How do I set baseurl correctly for project sites?

For a project site, your public path is `/<repo>/` on the default domain. In Jekyll, set baseurl in `_config.yml` to match the repo name, then validate links and assets in the deployed site.

### Is Jekyll supported on Windows?

Jekyll itself is not officially supported on Windows according to the Jekyll documentation, and GitHub Docs calls this out. If you develop on Windows, use WSL or build in CI for consistency.

## Conclusion

Jekyll on GitHub Pages works best when you choose one model and make it reproducible:

- Use GitHub-managed Jekyll for the simplest workflow.
- Use GitHub Actions when you need control over dependencies or build steps.

In both cases, the fastest way to debug is to inspect the generated output and validate baseurl behavior on the live site.

## References

1. [GitHub Docs: About GitHub Pages and Jekyll](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/about-github-pages-and-jekyll)
2. [GitHub Docs: Creating a GitHub Pages site with Jekyll](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/creating-a-github-pages-site-with-jekyll)
3. [GitHub Docs: Testing your GitHub Pages site locally with Jekyll](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/testing-your-github-pages-site-locally-with-jekyll)
4. [Jekyll Docs](https://jekyllrb.com/docs/)
5. [GitHub: github-pages gem](https://github.com/github/pages-gem)
6. [GitHub Pages: Dependency versions](https://pages.github.com/versions/)
