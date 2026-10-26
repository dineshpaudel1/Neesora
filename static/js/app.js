const menuToggle = document.querySelector(".menu-toggle");
const navigationMenu = document.querySelector("#primary-menu");

if (menuToggle && navigationMenu) {
    const closeNavigation = () => {
        navigationMenu.classList.remove("is-open");
        navigationMenu.closest(".primary-menu-wrap")?.classList.remove("is-open");
        menuToggle.setAttribute("aria-expanded", "false");
        menuToggle.setAttribute("aria-label", "Open navigation menu");
    };

    menuToggle.addEventListener("click", () => {
        const isExpanded = menuToggle.getAttribute("aria-expanded") === "true";
        if (isExpanded) {
            closeNavigation();
            return;
        }

        navigationMenu.classList.add("is-open");
        navigationMenu.closest(".primary-menu-wrap")?.classList.add("is-open");
        menuToggle.setAttribute("aria-expanded", "true");
        menuToggle.setAttribute("aria-label", "Close navigation menu");
    });

    navigationMenu.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", closeNavigation);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && menuToggle.getAttribute("aria-expanded") === "true") {
            closeNavigation();
            menuToggle.focus();
        }
    });
}

const productGalleryMain = document.querySelector("[data-product-gallery-main]");
if (productGalleryMain) {
    document.querySelectorAll("[data-gallery-thumb]").forEach((thumbnail) => {
        thumbnail.addEventListener("click", () => {
            productGalleryMain.src = thumbnail.dataset.imageSrc;
            productGalleryMain.alt = thumbnail.dataset.imageAlt;
            document.querySelectorAll("[data-gallery-thumb]").forEach((item) => {
                item.setAttribute("aria-pressed", String(item === thumbnail));
            });
        });
    });
}

document.querySelectorAll("[data-password-toggle]").forEach((toggle) => {
    toggle.addEventListener("click", () => {
        const passwordInput = document.getElementById(toggle.dataset.passwordToggle);
        if (!passwordInput) {
            return;
        }

        const isVisible = passwordInput.type === "text";
        passwordInput.type = isVisible ? "password" : "text";
        toggle.setAttribute("aria-pressed", String(!isVisible));
        toggle.setAttribute("aria-label", isVisible ? "Show password" : "Hide password");
    });
});

document.querySelectorAll("[data-disable-on-submit]").forEach((form) => {
    form.addEventListener("submit", () => {
        const submitButton = form.querySelector('button[type="submit"]:focus') ||
            form.querySelector('button[type="submit"]');
        if (submitButton && !submitButton.disabled) {
            submitButton.disabled = true;
            submitButton.setAttribute("aria-busy", "true");
            submitButton.textContent = "Placing your order…";
        }
    });
});

document.querySelector("[data-print-invoice]")?.addEventListener("click", () => {
    window.print();
});

// Sticky header shadow on scroll
const siteHeader = document.querySelector(".site-header");
if (siteHeader) {
    const onScroll = () => {
        siteHeader.classList.toggle("is-scrolled", window.scrollY > 8);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
}
