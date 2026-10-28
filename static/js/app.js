/* ── Mobile menu ─────────────────────────────────────────────── */
const menuBtn   = document.querySelector(".nav-menu-btn");
const mobileNav = document.getElementById("nav-mobile");

if (menuBtn && mobileNav) {
    const closeMenu = () => {
        mobileNav.hidden = true;
        menuBtn.setAttribute("aria-expanded", "false");
        menuBtn.setAttribute("aria-label", "Open menu");
    };

    menuBtn.addEventListener("click", () => {
        const isOpen = menuBtn.getAttribute("aria-expanded") === "true";
        if (isOpen) { closeMenu(); return; }
        mobileNav.hidden = false;
        menuBtn.setAttribute("aria-expanded", "true");
        menuBtn.setAttribute("aria-label", "Close menu");
    });

    mobileNav.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", closeMenu);
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && menuBtn.getAttribute("aria-expanded") === "true") {
            closeMenu();
            menuBtn.focus();
        }
    });
}

/* ── Search panel ────────────────────────────────────────────── */
const searchBtn   = document.querySelector(".nav-search-btn");
const searchPanel = document.getElementById("site-search");
const searchClose = searchPanel ? searchPanel.querySelector(".search-panel-close") : null;
const searchInput = searchPanel ? searchPanel.querySelector(".search-panel-input") : null;

if (searchBtn && searchPanel) {
    const closeSearch = () => {
        searchPanel.hidden = true;
        searchBtn.setAttribute("aria-expanded", "false");
    };

    searchBtn.addEventListener("click", () => {
        searchPanel.hidden = false;
        searchBtn.setAttribute("aria-expanded", "true");
        searchInput && searchInput.focus();
    });

    searchClose && searchClose.addEventListener("click", closeSearch);

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !searchPanel.hidden) {
            closeSearch();
            searchBtn.focus();
        }
    });
}

/* ── Product gallery thumbnails ──────────────────────────────── */
const galleryMain = document.querySelector("[data-product-gallery-main]");
if (galleryMain) {
    document.querySelectorAll("[data-gallery-thumb]").forEach((thumb) => {
        thumb.addEventListener("click", () => {
            galleryMain.src = thumb.dataset.imageSrc;
            galleryMain.alt = thumb.dataset.imageAlt;
            document.querySelectorAll("[data-gallery-thumb]").forEach((t) => {
                t.setAttribute("aria-pressed", String(t === thumb));
            });
        });
    });
}

/* ── Password visibility toggle ──────────────────────────────── */
document.querySelectorAll("[data-password-toggle]").forEach((toggle) => {
    toggle.addEventListener("click", () => {
        const input = document.getElementById(toggle.dataset.passwordToggle);
        if (!input) return;
        const visible = input.type === "text";
        input.type = visible ? "password" : "text";
        toggle.setAttribute("aria-pressed", String(!visible));
        toggle.setAttribute("aria-label", visible ? "Show password" : "Hide password");
    });
});

/* ── Disable checkout button on submit ───────────────────────── */
document.querySelectorAll("[data-disable-on-submit]").forEach((form) => {
    form.addEventListener("submit", () => {
        const btn = form.querySelector("button[type='submit']:focus") ||
                    form.querySelector("button[type='submit']");
        if (btn && !btn.disabled) {
            btn.disabled = true;
            btn.setAttribute("aria-busy", "true");
            btn.textContent = "Placing your order…";
        }
    });
});

/* ── Print invoice ───────────────────────────────────────────── */
document.querySelector("[data-print-invoice]")?.addEventListener("click", () => {
    window.print();
});

/* ── Sticky header shadow ────────────────────────────────────── */
const siteHeader = document.querySelector(".site-header");
if (siteHeader) {
    const onScroll = () => {
        siteHeader.classList.toggle("is-scrolled", window.scrollY > 8);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
}
