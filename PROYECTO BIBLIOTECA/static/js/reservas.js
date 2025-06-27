document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("modalReserva");
  const modalBody = document.getElementById("modal-reserva-body");
  const modalTitle = document.getElementById("modalReservaLabel");
  const contenido = document.getElementById("contenido-opcion");

  // Animación suave
  const aplicarAnimacion = (elemento) => {
    elemento.style.opacity = 0;
    elemento.style.transform = "translateY(40px)";
    elemento.style.transition = "opacity 0.2s ease, transform 0.2s ease";
    setTimeout(() => {
      elemento.style.opacity = 1;
      elemento.style.transform = "translateY(0)";
    }, 10);
  };

  // Spinner de carga
  const mostrarCargando = (contenedor) => {
    contenedor.innerHTML = `
      <div class="d-flex justify-content-center align-items-center p-4">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Cargando...</span>
        </div>
      </div>
    `;
  };

  const cargarContenido = (url) => {
    if (url.includes("nuevo") || url.includes("editar") || url.includes("mostrar_modal")) {
      modalTitle.textContent = url.includes("nuevo")
        ? "Agregar Reserva"
        : url.includes("editar")
        ? "Editar Reserva"
        : "Lista de Reservas";

      mostrarCargando(modalBody);

      fetch(url)
        .then((res) => res.text())
        .then((html) => {
          modalBody.innerHTML = html;
          aplicarAnimacion(modalBody);
          const modal = new bootstrap.Modal(modalElement);
          modal.show();

          if (url.includes("nuevo")) {
            setTimeout(inicializarFormularioReserva, 100); // Lógica opcional del formulario
          }
        });
    } else {
      mostrarCargando(contenido);
      fetch(url)
        .then((res) => res.text())
        .then((html) => {
          contenido.innerHTML = html;
          aplicarAnimacion(contenido);
        });
    }
  };

  // Eventos
  document.getElementById("btn-mostrar-reservas")?.addEventListener("click", () => {
    cargarContenido("/admin/reservas/mostrar");
  });

  document.getElementById("btn-agregar-reservas")?.addEventListener("click", () => {
    cargarContenido("/admin/reservas/nuevo");
  });

  // Ejemplo de inicialización de formulario (si aplica)
  function inicializarFormularioReserva() {
    const form = document.getElementById("form-reserva");
    if (!form) return;

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      const datos = {
        usuario_id: document.getElementById("usuario_id").value,
        libro_id: document.getElementById("libro_id").value,
        fecha_reserva: document.getElementById("fecha_reserva").value
      };

      fetch("/admin/reservas/guardar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos)
      })
        .then((res) => res.json())
        .then((respuesta) => {
          if (respuesta.mensaje) {
            document.getElementById("notificacion-reserva")?.classList.remove("d-none");
            form.reset();
          }
        })
        .catch((err) => {
          console.error("Error al guardar reserva:", err);
          alert("Error al guardar la reserva.");
        });
    });
  }
});
