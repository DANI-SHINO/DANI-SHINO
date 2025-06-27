
    async function actualizarTotales() {
      const res = await fetch('/api/dashboard_data');
      const data = await res.json();
      document.getElementById('total-administradores').innerText = data.total_administradores;
      document.getElementById('total-lectores').innerText = data.total_lectores;
      document.getElementById('total-libros').innerText = data.total_libros;
      document.getElementById('total-prestamos').innerText = data.total_prestamos;
      document.getElementById('total-reservas').innerText = data.total_reservas;
      document.getElementById('total-reportes').innerText = data.total_reportes;
    }

    actualizarTotales();
    setInterval(actualizarTotales, 30000);
