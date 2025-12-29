---
title: Deploy To GitHub Pages
description: A practical, repeatable guide to deploy a static site to GitHub Pages using branch publishing or GitHub Actions, with checks and troubleshooting.
date: '2026-01-02T02:25:54+08:00'
draft: true
commercial_value: 3
affiliate_products: []
keywords:
- deploy to github pages
- github pages deploy workflow
- github pages publishing source
- deploy static site to github pages
pillar: /github-pages/
faq:
- question: Should I deploy from a branch or GitHub Actions?
  answer: Use GitHub Actions if you have a build step (Hugo, Next.js export, Astro, etc.)
    or want reproducible deployments. Branch publishing is simplest when your repo already
    contains ready-to-serve static files.
- question: Why does my site deploy but shows a 404?
  answer: Most site-wide 404s come from the wrong URL (project site vs user site) or the
    wrong publish root. Verify the Pages source setting and confirm the published root
    contains index.html.
- question: What files must exist for a GitHub Pages deploy to work?
  answer: The published root must contain an entry file (typically index.html). If you
    deploy via Actions, the uploaded artifact must include the entry file at the top level.
- question: How do I keep my custom domain working after deploys?
  answer: Ensure the CNAME file is preserved. For branch publishing, GitHub may manage it;
    for Actions publishing, include the CNAME file in the published artifact output.
- question: How do I verify a deploy end-to-end?
  answer: Check the Pages build status, validate the live URL and a deep link, and use
    browser DevTools to confirm assets load without 404s or mixed-content warnings.
howto:
  name: How to deploy to GitHub Pages
  totalTime: PT30M
  steps:
  - name: Choose a publishing model
    text: Decide between branch publishing (branch and folder) and GitHub Actions based
      on whether your site needs a build step.
  - name: Configure the publishing source
    text: Set the Pages source in Settings, or commit a Pages workflow that builds and
      deploys an artifact.
  - name: Deploy and validate
    text: Push changes, confirm the build succeeds, and verify index.html and key assets
      are served from the correct base path.
lastmod: '2025-12-29T20:34:22+08:00'
type: cluster
---

Deploying to GitHub Pages is conceptually simple: GitHub Pages serves static files from a publishing source you configure. In practice, most failures happen when the publishing source doesn’t match your build output, or when the site URL/base path is misunderstood (especially for project sites).

This guide gives you a repeatable deployment workflow with two supported models:

1) **Branch + folder publishing** (lowest moving parts)  
2) **GitHub Actions workflow** (best for sites that must be built)

## Key Takeaways

- **Pages is static hosting**: if the published root doesn’t contain the file for a requested path, the browser will get a 404.
- **Pick a deployment model first**: branch publishing is simplest; Actions is best when you have a build step.
- **Validate the publish root, not your local dev server**: confirm the published artifact contains index.html at the top level.
- **Project sites have a base path**: `/<repo>/` is part of the URL on the default domain; base-path mistakes cause asset 404s.
- **Treat deployments as a workflow**: preflight checks, one “golden” deploy path, and a small troubleshooting map.

## What “Deploy To GitHub Pages” Means

To “deploy” to GitHub Pages is to make your site’s built output available at a public URL (either `github.io` or a custom domain). GitHub’s documentation summarizes it as choosing a publishing source: publish on pushes to a branch/folder, or publish via a GitHub Actions workflow.

> Paraphrased: You can publish Pages from a branch and folder, or by using a GitHub Actions workflow.
> — GitHub Docs, adapted

From an operator perspective, there are only two things that matter:

1. **What folder is GitHub Pages publishing from?**  
2. **Does that folder contain the files you think it does?**

Everything else (framework choice, CI, local dev server) is secondary.

## Choose Your Publishing Model (Branch vs GitHub Actions)

Both models are supported by GitHub Pages. Pick based on how your site is produced.

| Model | Best for | How it works | Main risk |
|---|---|---|---|
| Branch + folder | “Already-static” sites | GitHub publishes directly from a branch/folder (e.g., `main` + `/docs`) | You accidentally publish the wrong folder or forget to commit build output |
| GitHub Actions | Built sites (Hugo/Next.js export/Astro/etc.) | Workflow builds the site and deploys a Pages artifact | Workflow permissions, artifact path mistakes, missing index.html in artifact |

If you are unsure: choose GitHub Actions. It is the most reproducible and closest to “real” CI deployments.

## Preflight Checklist (Do This Before You Touch Settings)

1. **Know your site type**
   - user/org site: `https://<user>.github.io/`
   - project site: `https://<user>.github.io/<repo>/`
2. **Know your publish root**
   - Which folder (branch/folder or artifact root) becomes public?
3. **Confirm the entry file exists**
   - The publish root must contain index.html (or an equivalent entry file at the top level).
4. **Confirm base path behavior**
   - Project sites include the repo base path; absolute links can break.

## Option A: Deploy With Branch + Folder Publishing

This is the simplest path when your repository already contains the static files you want to serve.

### Step 1: Put your built site in a known folder

Pick one of these common patterns:

- `/docs` folder on `main`
- `/` (repo root) on a dedicated branch like `gh-pages`

GitHub Docs calls out an important requirement: if you publish from a branch and folder, the entry file must be at the top level of that folder.

> Paraphrased: If you publish from a branch and folder, the entry file must live at the top level of the source folder.
> — GitHub Docs, adapted

### Step 2: Configure the Pages publishing source

In your repo:

1. Go to **Settings → Pages**.
2. Under the Pages section, choose the publishing source:
   - Branch (e.g., `main`)
   - Folder (e.g., `/docs`)
3. Save and wait for the build/deploy status.

### Step 3: Validate the live site

Validate from the outside (browser), not from local dev:

1. Open your site URL and verify the homepage loads.
2. Open a deep link (a nested page) to confirm base paths work.
3. Open DevTools → Network and confirm key assets return 200 (not 404).

If HTML loads but assets 404, this is almost always a base-path issue (most commonly, a project site expecting `/`).

## Option B: Deploy With GitHub Actions (Recommended for Built Sites)

If your site needs a build step, the safest approach is:

1) build in CI,  
2) upload a Pages artifact,  
3) deploy it.

GitHub Docs notes an important constraint: if your publishing source is a workflow, the artifact you deploy must include the entry file at the top level of the artifact.

> Paraphrased: When publishing via Actions, the deployed artifact must include the entry file at the top level.
> — GitHub Docs, adapted

### Step 1: Start from GitHub’s Pages workflow model

GitHub’s Pages docs show a standard structure:

- a build job that uploads the Pages artifact
- a deploy job that uses the deployment action
- permissions that allow Pages deployment

### Step 2: Use correct workflow permissions

From GitHub’s Pages workflow examples, the deploy job commonly needs:

- contents read
- pages write
- id-token write

If you do not grant these permissions, deployments can fail even if your build succeeds.

### Step 3: Example workflow (generic static site)

This is a minimal skeleton you can adapt to your generator. Replace the build step and output folder.

```yaml
name: Deploy GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - name: Build site
        run: |
          # Replace this with your real build command
          # and ensure the output folder contains index.html.
          echo \"TODO: build\" 
      - uses: actions/upload-pages-artifact@v3
        with:
          path: ./public

  deploy:
    runs-on: ubuntu-latest
    needs: build
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy artifact
        id: deployment
        uses: actions/deploy-pages@v4
```

Key validation points:

- `path: ./public` must be the folder that contains index.html at its top level.
- If you use a custom domain with Actions, make sure the output includes a CNAME file.

## Generator Notes (Jekyll, Hugo, Next.js Export, and “Anything Static”)

GitHub Pages doesn’t care which tool generated your files. It only cares about what ends up in the published root. Still, different generators fail in predictable ways. Use this section as a quick “where should my files be?” reference.

| Generator | Typical build output folder | Common deploy gotcha | What to verify |
|---|---|---|---|
| Jekyll | site output is handled by Pages (classic) or built in Actions | Mixing Pages’ built-in Jekyll with a custom build unintentionally | One single publishing model, not both |
| Hugo | `public/` | `baseURL` / relative URLs wrong for project sites | Built pages and assets load under `/<repo>/` when needed |
| Next.js static export | exported static output folder (often `out/`) | Base path and asset prefixes for project sites | index.html exists, assets don’t 404 |
| “Plain static” | any folder you choose | Publishing the wrong folder | Folder contains index.html at the top level |

Two practical rules reduce most generator-specific pain:

1. **Make the output folder explicit** (in docs and in CI). Don’t rely on tribal knowledge like “it’s probably public”.
2. **Fail the build if index.html is missing**. A deployment without an entry file is not a deployment.

If you are deploying a single-page app (SPA), ensure your build actually produces static HTML and does not depend on server rewrites that GitHub Pages cannot provide.

## Troubleshooting Map (Fast Diagnosis)

| Symptom | Most likely cause | Fast check |
|---|---|---|
| Whole site 404s | Wrong Pages source or missing index.html | Settings → Pages + confirm index.html exists in publish root |
| HTML loads, assets 404 | Base path mismatch for project sites | Network tab: do asset URLs include `/<repo>/`? |
| Actions build passes, deploy fails | Missing Pages permissions | Compare permissions with GitHub’s Pages workflow docs |
| Custom domain breaks after deploy | Missing CNAME file in output | Confirm CNAME exists in published branch/artifact |
| Jekyll works locally but not on Pages | Dependency/version mismatch | Check Pages build logs and supported Jekyll behavior in GitHub Docs |

## Deployment Verification Checklist (Copy/Paste)

Use this when you want to be confident a deploy is “done” (not just “it didn’t error”):

- [ ] Correct URL opened (user/org site vs project site)
- [ ] Pages source confirmed (branch/folder or workflow)
- [ ] Publish root contains index.html and 404.html
- [ ] One deep link loads (not just homepage)
- [ ] DevTools shows no 404 assets and no blocked loads
- [ ] If project site: asset URLs include `/<repo>/` (or you intentionally generate relative URLs)
- [ ] If custom domain: CNAME file is preserved and DNS still points correctly
- [ ] If HTTPS is enabled: HTTP redirects to HTTPS and no mixed content warnings

## Rollback Strategy (When a Deploy Goes Wrong)

Static hosting makes rollback easier than most platforms, but only if you plan for it.

**Branch publishing rollback**

- Revert the last commit that introduced the bad output, or
- Switch the Pages source back to a known-good branch/folder temporarily.

**Actions publishing rollback**

- Revert the commit and let the workflow redeploy, or
- Re-run a known-good workflow run if your process allows it.

Operational tip: tag “known good” releases (even for static sites). It gives you an obvious rollback target and a clean audit trail when you’re debugging later.

If you need safer iteration, consider adding a lightweight preview habit: build locally from a clean checkout, or validate the Pages artifact output in CI before deployment. GitHub Pages is typically a single production endpoint, so your safety comes from verification steps and fast rollback rather than multi-environment complexity.

## Best Practices

1. **Keep a single “golden path”**
   - one branch/folder or one workflow that is known-good
2. **Validate the output folder in CI**
   - fail the workflow if index.html is missing
3. **Keep URLs base-path-safe**
   - especially for project sites on the default domain
4. **Log the deployment facts**
   - publish root, build command, output path, custom domain behavior
5. **Re-run from scratch occasionally**
   - a clean workflow run catches hidden local assumptions

## Common Mistakes

1. **Publishing the wrong folder** — Pages is serving `/docs` while your build outputs to `/public`.
2. **Forgetting index.html** — the site cannot load if the entry file isn’t at the published root.
3. **Mixing user site and project site URLs** — wrong URL looks like “deploy failed” even when it succeeded.
4. **Breaking base paths** — absolute links (`/assets/...`) fail on project sites unless configured correctly.
5. **Dropping the CNAME file** — custom domains silently detach after rebuilds if CNAME is not preserved.

## Frequently Asked Questions

### Should I deploy from a branch or GitHub Actions?

Use GitHub Actions if you have a build step or want reproducible deployments. Use branch publishing when your repo already contains ready-to-serve static files and you want the simplest possible setup.

### Why does my site deploy but shows a 404?

Start with:

1. Correct URL (user/org site vs project site)
2. Correct publish root (Pages source or artifact output)
3. Presence of index.html in that publish root

### What files must exist for a GitHub Pages deploy to work?

The publish root must contain an entry file (typically index.html). If you deploy via Actions, your uploaded artifact must include the entry file at the top level.

### How do I keep my custom domain working after deploys?

Preserve the CNAME file. For Actions deployments, include it in the build output folder so the deployed artifact keeps the domain mapping.

### How do I verify a deploy end-to-end?

Validate in production:

- homepage loads
- a deep link loads
- assets return 200 (no 404)
- the 404 page renders for a fake URL

## Conclusion

Deploying to GitHub Pages is easiest when you reduce it to a reproducible workflow:

1) choose branch publishing or Actions,  
2) ensure the publish root contains index.html, and  
3) validate the live URL and asset paths.

If something fails, debug from the publish root outward. Most “mystery” deploy issues become obvious once you inspect what Pages actually serves.

## References

1. [GitHub Docs: Configuring a publishing source for your GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
2. [GitHub Docs: Using custom workflows with GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
3. [GitHub Docs: Creating a GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)
4. [GitHub Docs: Quickstart for GitHub Pages](https://docs.github.com/en/pages/quickstart)
5. [GitHub Docs: Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
6. [GitHub Docs: About GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages)
