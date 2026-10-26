const sidebarToggle = document.querySelector(".admin-sidebar-toggle");
const adminSidebar = document.querySelector("#admin-sidebar");

if (sidebarToggle && adminSidebar) {
    sidebarToggle.addEventListener("click", () => {
        const isOpen = sidebarToggle.getAttribute("aria-expanded") === "true";
        sidebarToggle.setAttribute("aria-expanded", String(!isOpen));
        sidebarToggle.setAttribute("aria-label", isOpen ? "Open navigation" : "Close navigation");
        adminSidebar.classList.toggle("is-open", !isOpen);
    });
}

document.querySelector("[data-print-order]")?.addEventListener("click", () => {
    window.print();
});

document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
        if (!window.confirm(form.dataset.confirm)) {
            event.preventDefault();
        }
    });
});
