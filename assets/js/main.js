// 由 Hugo Pipes 处理的源文件（assets/js/main.js）
(() => {
  const toggle = document.querySelector("[data-menu-toggle]");
  const nav = document.getElementById("site-nav");
  if (!toggle || !nav) return;

  const closeMenu = () => {
    nav.classList.remove("is-open");
    toggle.setAttribute("aria-expanded", "false");
    document.documentElement.classList.remove("nav-open");
  };

  const openMenu = () => {
    nav.classList.add("is-open");
    toggle.setAttribute("aria-expanded", "true");
    document.documentElement.classList.add("nav-open");
  };

  toggle.addEventListener("click", () => {
    const isOpen = nav.classList.contains("is-open");
    isOpen ? closeMenu() : openMenu();
  });

  // 点击导航链接后关闭菜单
  nav.addEventListener("click", (e) => {
    if (e.target.closest(".nav-link")) {
      closeMenu();
    }
  });

  // ESC 键关闭菜单
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && nav.classList.contains("is-open")) {
      closeMenu();
      toggle.focus();
    }
  });

  // 窗口 resize 时关闭菜单（从移动端切换到桌面端）
  window.addEventListener("resize", () => {
    if (window.innerWidth > 720 && nav.classList.contains("is-open")) {
      closeMenu();
    }
  });
})();

// 移动端表格：自动添加 data-label 属性
(() => {
  const tables = document.querySelectorAll(".prose table, .comparison-table");
  for (const table of tables) {
    const headers = Array.from(table.querySelectorAll("thead th")).map(
      (th) => th.textContent?.trim() || ""
    );
    if (!headers.length) continue;

    const rows = table.querySelectorAll("tbody tr");
    for (const row of rows) {
      const cells = row.querySelectorAll("td");
      cells.forEach((cell, i) => {
        if (headers[i]) {
          cell.setAttribute("data-label", headers[i]);
        }
      });
    }
  }
})();

(() => {
  const codeBlocks = document.querySelectorAll("pre > code");
  for (const code of codeBlocks) {
    const pre = code.parentElement;
    if (!pre) continue;
    if (pre.querySelector(".copy-btn")) continue;

    pre.style.position = "relative";

    const btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.type = "button";
    btn.textContent = "Copy";
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(code.textContent || "");
        btn.textContent = "Copied!";
        window.setTimeout(() => (btn.textContent = "Copy"), 2000);
      } catch {
        btn.textContent = "Failed";
        window.setTimeout(() => (btn.textContent = "Copy"), 2000);
      }
    });
    pre.appendChild(btn);
  }
})();
