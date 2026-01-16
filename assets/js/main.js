// 由 Hugo Pipes 处理的源文件（assets/js/main.js）

// Header Dropdown Navigation
(() => {
  const dropdowns = document.querySelectorAll('.nav-dropdown');
  if (!dropdowns.length) return;

  // 桌面端：hover 展开
  dropdowns.forEach(dropdown => {
    const trigger = dropdown.querySelector('.nav-dropdown-trigger');
    if (!trigger) return;

    // 点击展开/收起
    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = dropdown.classList.contains('is-open');
      // 关闭其他下拉
      dropdowns.forEach(d => d.classList.remove('is-open'));
      if (!isOpen) {
        dropdown.classList.add('is-open');
        trigger.setAttribute('aria-expanded', 'true');
      } else {
        trigger.setAttribute('aria-expanded', 'false');
      }
    });

    // 桌面端 hover 展开
    if (window.matchMedia('(min-width: 768px)').matches) {
      dropdown.addEventListener('mouseenter', () => {
        dropdown.classList.add('is-open');
        trigger.setAttribute('aria-expanded', 'true');
      });
      dropdown.addEventListener('mouseleave', () => {
        dropdown.classList.remove('is-open');
        trigger.setAttribute('aria-expanded', 'false');
      });
    }
  });

  // 点击外部关闭
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.nav-dropdown')) {
      dropdowns.forEach(d => {
        d.classList.remove('is-open');
        d.querySelector('.nav-dropdown-trigger')?.setAttribute('aria-expanded', 'false');
      });
    }
  });

  // ESC 关闭
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      dropdowns.forEach(d => {
        d.classList.remove('is-open');
        d.querySelector('.nav-dropdown-trigger')?.setAttribute('aria-expanded', 'false');
      });
    }
  });
})();

// Mobile Nav Toggle
(() => {
  const toggle = document.querySelector("[data-menu-toggle]");
  const nav = document.getElementById("site-nav");
  const backdrop = document.querySelector("[data-nav-backdrop]");
  const closeBtn = nav?.querySelector("[data-nav-close]");
  if (!toggle || !nav) return;

  let lastFocused = null;

  const getFocusable = () => {
    const selectors = [
      'a[href]:not([tabindex="-1"])',
      'button:not([disabled]):not([tabindex="-1"])',
      'input:not([disabled]):not([tabindex="-1"])',
      'select:not([disabled]):not([tabindex="-1"])',
      'textarea:not([disabled]):not([tabindex="-1"])',
      '[tabindex]:not([tabindex="-1"])',
    ];
    return Array.from(nav.querySelectorAll(selectors.join(","))).filter((el) => {
      if (!(el instanceof HTMLElement)) return false;
      if (el.hasAttribute("hidden")) return false;
      const style = window.getComputedStyle(el);
      return style.visibility !== "hidden" && style.display !== "none";
    });
  };

  const closeMenu = () => {
    nav.classList.remove("is-open");
    backdrop?.classList.remove("is-visible");
    toggle.setAttribute("aria-expanded", "false");
    document.documentElement.classList.remove("nav-open");

    if (lastFocused instanceof HTMLElement) {
      lastFocused.focus();
      lastFocused = null;
    } else {
      toggle.focus();
    }
  };

  const openMenu = () => {
    lastFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    nav.classList.add("is-open");
    backdrop?.classList.add("is-visible");
    toggle.setAttribute("aria-expanded", "true");
    document.documentElement.classList.add("nav-open");

    const focusables = getFocusable();
    (closeBtn || focusables[0] || nav).focus?.();
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

  // 点击遮罩关闭菜单
  backdrop?.addEventListener("click", closeMenu);

  // 点击关闭按钮关闭菜单
  closeBtn?.addEventListener("click", closeMenu);

  // ESC 键关闭菜单
  document.addEventListener("keydown", (e) => {
    if (!nav.classList.contains("is-open")) return;
    if (e.key === "Escape") closeMenu();
    if (e.key !== "Tab") return;

    const focusables = getFocusable();
    if (focusables.length === 0) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];

    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });

  // 窗口 resize 时关闭菜单（从移动端切换到桌面端）
  window.addEventListener("resize", () => {
    if (window.innerWidth >= 768 && nav.classList.contains("is-open")) {
      closeMenu();
    }
  });
})();

// 横向滚动表格：滚动提示阴影控制（右侧渐变）
(() => {
  const containers = document.querySelectorAll(".comparison-table-wrap, .table-wrap");
  if (!containers.length) return;

  const update = (container) => {
    const maxScrollLeft = container.scrollWidth - container.clientWidth;
    const isScrollable = maxScrollLeft > 1;
    if (!isScrollable) {
      container.classList.add("is-scrolled-end");
      return;
    }

    const isEnd = container.scrollLeft >= maxScrollLeft - 10;
    container.classList.toggle("is-scrolled-end", isEnd);
  };

  const onResize = () => {
    containers.forEach(update);
  };

  window.addEventListener("resize", onResize, { passive: true });

  containers.forEach((container) => {
    const onScroll = () => update(container);
    container.addEventListener("scroll", onScroll, { passive: true });
    update(container);
  });
})();

(() => {
  const codeBlocks = document.querySelectorAll("pre > code");
  for (const code of codeBlocks) {
    const pre = code.parentElement;
    if (!pre) continue;
    if (pre.querySelector(".copy-btn")) continue;

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
    pre.insertBefore(btn, code);
  }
})();
