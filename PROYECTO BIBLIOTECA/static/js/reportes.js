document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("modalReporte");
  const modalBody = document.getElementById("modal-reporte-body");
  const modalTitle = document.getElementById("modalReporteLabel");
  const contenido = document.getElementById("contenido-opcion");

  const aplicarAnimacion = (elemento) => {
    elemento.style.opacity = 0;
    elemento.style.transform = "translateY(40px)";
    elemento.style.transition = "opacity 0.2s ease, transform 0.2s ease";
    setTimeout(() => {
      elemento.style.opacity = 1;
      elemento.style.transform = "translateY(0)";
    }, 10);
  };

  const mostrarCargando = (contenedor) => {
    contenedor.innerHTML = `
      <div class="d-flex justify-content-center align-items-center p-4">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Cargando...</span>
        </div>
      </div>
    `;
  };

  const cargarContenido = (url, forzarModal = false) => {
    const mostrarEnModal = url.includes("nuevo") || url.includes("editar") || forzarModal;

    if (mostrarEnModal) {
      modalTitle.textContent = url.includes("nuevo")
        ? "Agregar Reporte"
        : url.includes("editar")
        ? "Editar Reporte"
        : "Lista de Reportes";

      mostrarCargando(modalBody);

      fetch(url)
        .then((response) => response.text())
        .then((html) => {
          modalBody.innerHTML = html;
          aplicarAnimacion(modalBody);
          new bootstrap.Modal(modalElement).show();
        });
    } else {
      mostrarCargando(contenido);
      fetch(url)
        .then((response) => response.text())
        .then((html) => {
          contenido.innerHTML = html;
          aplicarAnimacion(contenido);
        });
    }
  };

  document.getElementById("btn-mostrar-reportes")?.addEventListener("click", () => {
    cargarContenido("/admin/reportes/mostrar", true); // Se abre como modal
  });

  document.getElementById("btn-agregar-reportes")?.addEventListener("click", () => {
    cargarContenido("/admin/reportes/nuevo");
  });

  document.getElementById("btn-editar-reportes")?.addEventListener("click", () => {
    cargarContenido("/admin/reportes/editar");
  });

  document.getElementById("btn-eliminar-reportes")?.addEventListener("click", () => {
    cargarContenido("/admin/reportes/eliminar");
  });
});
