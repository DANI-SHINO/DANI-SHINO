function loadContent(pagina) {
  document.getElementById('main-content').src = `/admin/${pagina}`;
}


document.addEventListener("DOMContentLoaded", () => {
  const links = document.querySelectorAll(".menu-link");

  links.forEach((link) => {
    link.addEventListener("click", () => {
      links.forEach((l) => l.classList.remove("active"));
      link.classList.add("active");
    });
  });

  const sidebar = document.getElementById("sidebar");
  const toggleBtn = document.getElementById("toggle-btn");

  toggleBtn.addEventListener("click", () => {
    sidebar.classList.toggle("collapsed");
  });
});
