# 文章来源检索记录（2025-12-29）

目的：为每篇文章提供可追溯的“联网搜索→挑选权威来源→写入 References”记录，避免引用凭空生成或过期链接。

---

## `/github-pages/404/`（`content/github-pages/404.md`）

### 搜索关键词（示例）

- `github pages custom 404 page 404.md permalink /404.html`
- `troubleshooting 404 errors github pages`
- `site:gohugo.io templates 404`
- `RFC 9110 404 Not Found`

### 选用来源（写入文章 References）

1. GitHub Docs: Creating a custom 404 page for your GitHub Pages site  
   `https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-custom-404-page-for-your-github-pages-site`
2. GitHub Docs: Troubleshooting 404 errors for GitHub Pages sites  
   `https://docs.github.com/en/pages/getting-started-with-github-pages/troubleshooting-404-errors-for-github-pages-sites`
3. GitHub Docs: Configuring a publishing source for your GitHub Pages site  
   `https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site`
4. GitHub Docs: About GitHub Pages  
   `https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages`
5. Hugo Docs: Custom 404 page  
   `https://gohugo.io/templates/404/`
6. Jekyll Docs: Permalinks  
   `https://jekyllrb.com/docs/permalinks/`
7. RFC 9110: HTTP Semantics (404 Not Found)  
   `https://www.rfc-editor.org/rfc/rfc9110.html#name-404-not-found`

### 备注

- MDN 的 404 状态码页面在本次工具打开时出现错误，因此改用 RFC 9110 作为更权威且稳定的“状态码定义”来源。

---

## `/github-pages/custom-domain/`（`content/github-pages/custom-domain.md`）

### 搜索关键词（示例）

- `GitHub Pages custom domain DNS A record AAAA CNAME Enforce HTTPS`
- `verifying custom domain for GitHub Pages wildcard DNS`
- `Cloudflare CNAME flattening documentation`

### 选用来源（写入文章 References）

1. GitHub Docs: Managing a custom domain for your GitHub Pages site  
   `https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site`
2. GitHub Docs: Verifying your custom domain for GitHub Pages  
   `https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages`
3. GitHub Docs: Securing your GitHub Pages site with HTTPS  
   `https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https`
4. GitHub Docs: About GitHub Pages  
   `https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages`
5. GitHub Docs: Troubleshooting custom domains and GitHub Pages  
   `https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/troubleshooting-custom-domains-and-github-pages`
6. Cloudflare Docs: CNAME flattening  
   `https://developers.cloudflare.com/dns/cname-flattening/`

### 备注

- GitHub 文档里列出的 Pages A/AAAA 记录可能随时间调整；文章内写明“以 GitHub Docs 为准”，并要求读者在实际配置前再次核对。
- HTTPS 生效时间以 GitHub Docs 为准；本文引用的排障文档提到“配置自定义域名后最多约 1 小时”。

---

## `/github-pages/deploy/`（`content/github-pages/deploy.md`）

### 搜索关键词（示例）

- `deploy to GitHub Pages branch folder vs GitHub Actions publishing source`
- `using custom workflows with GitHub Pages actions deploy-pages upload-pages-artifact`
- `creating a GitHub Pages site artifact entry file top level`

### 选用来源（写入文章 References）

1. GitHub Docs: Configuring a publishing source for your GitHub Pages site  
   `https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site`
2. GitHub Docs: Using custom workflows with GitHub Pages  
   `https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages`
3. GitHub Docs: Creating a GitHub Pages site  
   `https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site`
4. GitHub Docs: Quickstart for GitHub Pages  
   `https://docs.github.com/en/pages/quickstart`
5. GitHub Docs: Workflow syntax for GitHub Actions  
   `https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax`
6. GitHub Docs: About GitHub Pages  
   `https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages`

### 备注

- Deploy 文章以 GitHub Docs 为主；涉及 Actions 工作流权限时，以 “Using custom workflows with GitHub Pages” 中的示例为准（包含 pages/id-token 等权限配置）。

---

## `/github-pages/https/`（`content/github-pages/https.md`）

### 搜索关键词（示例）

- `GitHub Pages Enforce HTTPS certificate not yet created mixed content`
- `Troubleshooting custom domains and GitHub Pages HTTPS not working`
- `MDN HTTPS glossary mixed content`

### 选用来源（写入文章 References）

1. GitHub Docs: Securing your GitHub Pages site with HTTPS  
   `https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https`
2. GitHub Docs: Troubleshooting custom domains and GitHub Pages  
   `https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/troubleshooting-custom-domains-and-github-pages`
3. GitHub Docs: Managing a custom domain for your GitHub Pages site  
   `https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site`
4. GitHub Docs: About GitHub Pages  
   `https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages`
5. MDN Web Docs: HTTPS  
   `https://developer.mozilla.org/en-US/docs/Glossary/HTTPS`
6. MDN Web Docs: Mixed content  
   `https://developer.mozilla.org/en-US/docs/Web/Security/Mixed_content`

### 备注

- “Enforce HTTPS 不可用/证书未创建”优先按 GitHub Docs 的排障顺序处理：先 DNS，再等待证书流程完成，再考虑内容混合（Mixed Content）与缓存。

---

## `/github-pages/jekyll/`（`content/github-pages/jekyll.md`）

### 搜索关键词（示例）

- `About GitHub Pages and Jekyll github-pages gem supported workflows`
- `testing your GitHub Pages site locally with Jekyll`
- `GitHub Pages Jekyll plugins supported plugins`

### 选用来源（写入文章 References）

1. GitHub Docs: About GitHub Pages and Jekyll  
   `https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/about-github-pages-and-jekyll`
2. GitHub Docs: Creating a GitHub Pages site with Jekyll  
   `https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/creating-a-github-pages-site-with-jekyll`
3. GitHub Docs: Testing your GitHub Pages site locally with Jekyll  
   `https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/testing-your-github-pages-site-locally-with-jekyll`
4. Jekyll Docs: Documentation  
   `https://jekyllrb.com/docs/`
5. GitHub: github-pages gem (Pages build environment and supported plugins)  
   `https://github.com/github/pages-gem`

### 备注

- Jekyll 的“内置 Pages 构建”与“Actions 自建构建”是两套模式；文章会强调避免混用导致的版本/插件差异。

---

## `/github-pages/hugo/`（`content/github-pages/hugo.md`）

### 搜索关键词（示例）

- `Hugo host on GitHub Pages GitHub Actions workflow`
- `Hugo baseURL project site /<repo>/ GitHub Pages`
- `GitHub Pages using custom workflows permissions pages id-token`

### 选用来源（写入文章 References）

1. Hugo Docs: Host on GitHub Pages  
   `https://gohugo.io/host-and-deploy/host-on-github-pages/`
2. Hugo Docs: Configuration (baseURL and related settings)  
   `https://gohugo.io/configuration/all/`
3. GitHub Docs: Using custom workflows with GitHub Pages  
   `https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages`
4. GitHub Docs: Configuring a publishing source for your GitHub Pages site  
   `https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site`
5. GitHub Docs: About GitHub Pages  
   `https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages`

### 备注

- Hugo 部署到 GitHub Pages 的核心是“输出目录正确 + baseURL/相对链接正确 + Actions 权限正确”；文章会把这三点作为主线拆解。
