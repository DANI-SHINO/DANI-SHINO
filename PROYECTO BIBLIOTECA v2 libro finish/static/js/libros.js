  document.addEventListener("DOMContentLoaded", function() {
    const contenido = document.getElementById("contenido-opcion");

    const cargarContenido = (url) => {
      fetch(url)
        .then(response => response.text())
        .then(html => {
          contenido.innerHTML = html;
          if (url.includes("mostrar")) {
            asignarEventosBotonesEditar();
          }
        });
    };

    document.getElementById("btn-agregar").addEventListener("click", () => {
      cargarContenido("/admin/libros/nuevo");
    });

    document.getElementById("btn-mostrar").addEventListener("click", () => {
      cargarContenido("/admin/libros/mostrar");
    });

    document.getElementById("btn-eliminar").addEventListener("click", () => {
      cargarContenido("/admin/libros/eliminar");
    });

    function asignarEventosBotonesEditar() {
      contenido.querySelectorAll(".btn-editar").forEach(btn => {
        btn.addEventListener("click", function () {
          const libroId = this.getAttribute("data-id");
          fetch(`/admin/libros/editar/${libroId}`)
            .then(response => response.text())
            .then(html => {
              contenido.innerHTML = html;
            });
        });
      });
    }
  });