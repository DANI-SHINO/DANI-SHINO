document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("modalLibro");
  const modalBody = document.getElementById("modal-libro-body");
  const modalTitle = document.getElementById("modalLibroLabel");

  // ✅ Crear una sola instancia del modal
  const modalInstance = new bootstrap.Modal(modalElement);

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

  // Spinner mientras carga
  const mostrarCargando = (contenedor) => {
    contenedor.innerHTML = `
      <div class="d-flex justify-content-center align-items-center p-4">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Cargando...</span>
        </div>
      </div>
    `;
  };

  // Mostrar lista de usuarios
  document.getElementById("btn-mostrar-usuarios")?.addEventListener("click", () => {
    modalTitle.textContent = "Lista de Usuarios";
    mostrarCargando(modalBody);

    fetch('/admin/usuarios/mostrar')
      .then(response => response.text())
      .then(html => {
        modalBody.innerHTML = html;
        aplicarAnimacion(modalBody);
        modalInstance.show(); // ✅ Reutiliza la instancia
      });
  });

  // Mostrar formulario para agregar usuario
  document.getElementById("btn-agregar")?.addEventListener("click", () => {
    modalTitle.textContent = "Agregar Usuario";
    mostrarCargando(modalBody);

    fetch("/admin/usuarios/agregar")
      .then(response => response.text())
      .then(html => {
        modalBody.innerHTML = html;
        aplicarAnimacion(modalBody);
        modalInstance.show(); // ✅ Reutiliza la instancia
      });
  });

  // Delegación para botón editar
  document.addEventListener("click", function (e) {
    if (e.target.classList.contains("btn-editar-usuario")) {
      const userId = e.target.getAttribute("data-id");

      fetch(`/admin/usuarios/editar_formulario/${userId}`)
        .then((res) => res.text())
        .then((html) => {
          modalTitle.textContent = "Editar Usuario";
          modalBody.innerHTML = html;
          aplicarAnimacion(modalBody);
          modalInstance.show(); // ✅ Reutiliza la instancia
        });
    }
  });

  // Delegación para botón eliminar
  document.addEventListener("click", function (e) {
    if (e.target.classList.contains("btn-eliminar-usuario")) {
      const btn = e.target;
      const id = btn.dataset.id;
      if (confirm("¿Estás seguro de eliminar al usuario ID: " + id + "?")) {
        fetch(`/admin/usuarios/eliminar/${id}`, {
          method: "POST"
        })
          .then(resp => resp.json())
          .then(data => {
            alert(data.mensaje || "Usuario eliminado");
            btn.closest("tr").remove();
          })
          .catch(err => {
            console.error("Error al eliminar usuario:", err);
            alert("Error al eliminar usuario.");
          });
      }
    }
  });

  // Filtro en vivo (en caso de que esté visible desde el inicio)
  document.getElementById("busqueda-usuario")?.addEventListener("keyup", function () {
    const filtro = this.value.toLowerCase();
    const filas = document.querySelectorAll("#tabla-usuarios tbody tr");

    filas.forEach(fila => {
      const nombre = fila.dataset.nombre.toLowerCase();
      const email = fila.dataset.email.toLowerCase();
      const rol = fila.dataset.rol.toLowerCase();
      const coincide = nombre.includes(filtro) || email.includes(filtro) || rol.includes(filtro);
      fila.style.display = coincide ? "" : "none";
    });
  });
});
