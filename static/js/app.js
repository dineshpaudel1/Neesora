const menuToggle = document.querySelector(".menu-toggle");
const navigationMenu = document.querySelector("#primary-menu");

if (menuToggle && navigationMenu) {
    menuToggle.addEventListener("click", () => {
        const isExpanded = menuToggle.getAttribute("aria-expanded") === "true";
        menuToggle.setAttribute("aria-expanded", String(!isExpanded));
        navigationMenu.classList.toggle("is-open", !isExpanded);
    });
}
