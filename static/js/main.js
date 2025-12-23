(() => {
  const toggle = document.querySelector("[data-menu-toggle]");
  const nav = document.getElementById("site-nav");
  if (!toggle || !nav) return;

  toggle.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
  });
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
