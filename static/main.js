/**
 * IPSD – Sistema de Matrícula | main.js
 * Funcionalidades generales del portal docente y admin
 */

// ─── VALIDACIÓN EN TIEMPO REAL DEL LOGIN DOCENTE ───
(function() {
  const emailInput = document.getElementById('correo_institucional');
  const emailError = document.getElementById('email-error');
  const empInput = document.getElementById('numero_empleado');
  const empError = document.getElementById('emp-error');
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  if (emailInput) {
    emailInput.addEventListener('input', function() {
      const val = this.value.trim();
      const valido = emailRegex.test(val.toLowerCase());
      const vacio = val.length === 0;

      if (vacio) {
        this.classList.remove('is-valid', 'is-invalid');
        if (emailError) emailError.classList.remove('show');
      } else if (valido) {
        this.classList.add('is-valid');
        this.classList.remove('is-invalid');
        if (emailError) emailError.classList.remove('show');
      } else {
        this.classList.add('is-invalid');
        this.classList.remove('is-valid');
        if (emailError) emailError.classList.add('show');
      }
    });
  }

  if (!empInput) return;

  empInput.addEventListener('input', function() {
    const val = this.value.trim();
    const valido = /^\d{4,12}$/.test(val);
    const vacio = val.length === 0;

    // Solo dígitos
    this.value = this.value.replace(/\D/g, '');

    if (vacio) {
      this.classList.remove('is-valid', 'is-invalid');
      if (empError) empError.classList.remove('show');
    } else if (valido) {
      this.classList.add('is-valid');
      this.classList.remove('is-invalid');
      if (empError) empError.classList.remove('show');
    } else {
      this.classList.add('is-invalid');
      this.classList.remove('is-valid');
      if (empError) empError.classList.add('show');
    }
  });
})();


// ─── EFECTO DE CARGA EN BOTONES AL HACER SUBMIT ───
(function() {
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
      const btn = this.querySelector('[type=submit]');
      if (!btn) return;

      // Si es un form de matrícula, validar selección de horario
      const select = this.querySelector('select[name="horario_elegido"]');
      if (select && !select.value) {
        e.preventDefault();
        select.classList.add('is-invalid');
        select.focus();
        const label = this.querySelector('.form-label');
        if (label) {
          label.style.color = 'var(--danger)';
          setTimeout(() => { label.style.color = ''; }, 2500);
        }
        return;
      }

      // Agregar estado de carga
      btn.classList.add('btn-loading');
      const originalText = btn.innerHTML;
      btn.setAttribute('data-original', originalText);
      btn.disabled = true;

      // Restaurar si la navegación tarda más de 10s
      setTimeout(() => {
        btn.classList.remove('btn-loading');
        btn.innerHTML = originalText;
        btn.disabled = false;
      }, 10000);
    });
  });
})();


// ─── AUTO-DISMISS DE ALERTAS ───
(function() {
  const alerts = document.querySelectorAll('.alert-ipsd[id]');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity .5s ease, transform .5s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-8px)';
      setTimeout(() => alert.remove(), 500);
    }, 5000);
  });
})();


// ─── MODAL DE CANCELACIÓN (PORTAL DOCENTE) ───
function abrirModalCancelacion(empleado, cursoId, nombreCurso) {
  const modal = document.getElementById('cancel-modal');
  if (!modal) return;

  document.getElementById('cancel-empleado').value = empleado;
  document.getElementById('cancel-curso').value    = cursoId;
  document.getElementById('modal-desc').innerHTML  =
    `Se cancelará tu inscripción en <strong>"${nombreCurso}"</strong>. Esta acción se puede deshacer volviendo a matricularte.`;

  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function cerrarModal(id) {
  const modal = document.getElementById(id || 'cancel-modal');
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// Cerrar modal al hacer clic en el fondo
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', function(e) {
      if (e.target === this) cerrarModal(this.id);
    });
  });

  // Cerrar con Escape
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.active').forEach(m => {
        m.classList.remove('active');
      });
      document.body.style.overflow = '';
    }
  });
});


// ─── ANIMACIONES DE ENTRADA AL HACER SCROLL ───
(function() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.curso-card, .stat-card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(16px)';
    el.style.transition = 'opacity .4s ease, transform .4s ease';
    observer.observe(el);
  });
})();


// ─── RESALTAR FILA DE TABLA AL HOVER (admin) ───
(function() {
  document.querySelectorAll('.table-ipsd tbody tr').forEach(row => {
    row.addEventListener('mouseenter', function() {
      this.style.background = '#f0f4ff';
    });
    row.addEventListener('mouseleave', function() {
      this.style.background = '';
    });
  });
})();


// ─── DETALLE DE CURSO (DOCENTE) ───
(function() {
  const modal = document.getElementById('curso-sesiones-modal');
  if (!modal) return;

  const titleEl = document.getElementById('curso-sesiones-title');
  const metaEl = document.getElementById('curso-sesiones-meta');
  const infoEl = document.getElementById('curso-detalle-info');
  const futurasEl = document.getElementById('curso-sesiones-futuras');
  const pasadasEl = document.getElementById('curso-sesiones-pasadas');
  const qrCardEl = document.getElementById('curso-sesiones-qr-card');
  const qrInfoEl = document.getElementById('curso-sesion-abierta-info');
  const qrBoxEl = document.getElementById('curso-sesion-qr');
  const feedbackEl = document.getElementById('curso-sesion-feedback');
  const marcarBtn = document.getElementById('btn-marcar-asistencia');

  let sesionAbiertaActual = null;

  function abrirModalSesiones() {
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function setFeedback(texto, esError) {
    if (!feedbackEl) return;
    feedbackEl.textContent = texto || '';
    feedbackEl.style.color = esError ? '#dc2626' : '#166534';
  }

  function estadoBadge(estadoTexto) {
    if (estadoTexto === 'Abierta') {
      return '<span class="badge-pill success text-xs">Abierta</span>';
    }
    if (estadoTexto === 'Finalizada') {
      return '<span class="badge-pill primary text-xs">Finalizada</span>';
    }
    return '<span class="badge-pill secondary text-xs">Cerrada</span>';
  }

  function estadoMatriculaBadge(codigo, nombre) {
    if (!codigo) return '<span class="badge-pill secondary text-xs">Sin estado</span>';

    if (codigo === 'APROBADA') {
      return `<span class="badge-pill success text-xs">${nombre || 'Aprobada'}</span>`;
    }
    if (codigo === 'NO_APROBADA') {
      return `<span class="badge-pill danger text-xs">${nombre || 'No aprobada'}</span>`;
    }
    if (codigo === 'ABANDONO') {
      return `<span class="badge-pill secondary text-xs">${nombre || 'Abandono'}</span>`;
    }
    if (codigo === 'CANCELADA') {
      return `<span class="badge-pill secondary text-xs">${nombre || 'Cancelada'}</span>`;
    }
    return `<span class="badge-pill primary text-xs">${nombre || codigo}</span>`;
  }

  function textoTipoAccion(tipoAccion) {
    if (tipoAccion === 'CONFERENCIA') return 'Conferencia';
    if (tipoAccion === 'SEMINARIO') return 'Seminario';
    return 'Curso';
  }

  function renderInfoCurso(curso) {
    if (!infoEl) return;

    const modalidad = curso.modalidad || 'No definida';
    const periodo = `${curso.mes || '-'} ${curso.anio || ''}`.trim();
    const horario = curso.horario_matriculado || 'No definido';
    const horasTotales = Number(curso.horas_totales || 0);
    const semanasDuracion = Number(curso.semanas_duracion || 1);
    const enlaceHtml = (modalidad === 'Virtual' && curso.enlace_virtual)
      ? `<a href="${curso.enlace_virtual}" target="_blank" rel="noopener noreferrer" style="font-size:.82rem; color:var(--primary); font-weight:700; text-decoration:none;">Abrir enlace virtual</a>`
      : '<span style="font-size:.82rem; color:var(--text-muted);">No aplica</span>';

    infoEl.innerHTML = `
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:.6rem;">
        <div style="border:1px solid var(--border); border-radius:10px; padding:.6rem .7rem; background:#f8fafc;">
          <div style="font-size:.72rem; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Codigo</div>
          <div style="font-size:.88rem; font-weight:700; color:#0f172a;">${curso.id || '-'}</div>
        </div>
        <div style="border:1px solid var(--border); border-radius:10px; padding:.6rem .7rem; background:#f8fafc;">
          <div style="font-size:.72rem; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Modalidad</div>
          <div style="font-size:.88rem; font-weight:700; color:#0f172a;">${modalidad}</div>
        </div>
        <div style="border:1px solid var(--border); border-radius:10px; padding:.6rem .7rem; background:#f8fafc;">
          <div style="font-size:.72rem; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Tipo de accion</div>
          <div style="font-size:.88rem; font-weight:700; color:#0f172a;">${textoTipoAccion(curso.tipo_accion)}</div>
        </div>
        <div style="border:1px solid var(--border); border-radius:10px; padding:.6rem .7rem; background:#f8fafc;">
          <div style="font-size:.72rem; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Duracion</div>
          <div style="font-size:.88rem; font-weight:700; color:#0f172a;">${horasTotales}h · ${semanasDuracion} semana(s)</div>
        </div>
        <div style="border:1px solid var(--border); border-radius:10px; padding:.6rem .7rem; background:#f8fafc;">
          <div style="font-size:.72rem; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Periodo</div>
          <div style="font-size:.88rem; font-weight:700; color:#0f172a;">${periodo} · Trim. ${curso.trimestre || '-'}</div>
        </div>
        <div style="border:1px solid var(--border); border-radius:10px; padding:.6rem .7rem; background:#f8fafc;">
          <div style="font-size:.72rem; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Jornada</div>
          <div style="font-size:.88rem; font-weight:700; color:#0f172a;">${horario}</div>
        </div>
        <div style="border:1px solid var(--border); border-radius:10px; padding:.6rem .7rem; background:#f8fafc;">
          <div style="font-size:.72rem; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Estado</div>
          <div>${estadoMatriculaBadge(curso.estado_matricula, curso.estado_matricula_nombre)}</div>
        </div>
        <div style="border:1px solid var(--border); border-radius:10px; padding:.6rem .7rem; background:#f8fafc; grid-column:1 / -1;">
          <div style="font-size:.72rem; color:var(--text-muted); font-weight:700; text-transform:uppercase; margin-bottom:.18rem;">Acceso Virtual</div>
          ${enlaceHtml}
        </div>
      </div>
    `;
  }

  function renderTablaSesiones(container, sesiones) {
    if (!container) return;

    if (!sesiones || sesiones.length === 0) {
      container.innerHTML = '<p class="curso-sesiones-empty">Sin sesiones para mostrar.</p>';
      return;
    }

    const rows = sesiones.map(s => {
      const asistencia = s.asistencia_marcada
        ? '<span class="badge-pill success text-xs">Marcada</span>'
        : '<span class="badge-pill secondary text-xs">Pendiente</span>';

      return `
        <tr>
          <td>${s.fecha || '—'}</td>
          <td>${s.hora_inicio || '—'} - ${s.hora_fin || '—'}</td>
          <td>${s.jornada || 'UNICA'}</td>
          <td>${s.docente_sesion || '—'}</td>
          <td>${estadoBadge(s.estado_texto || 'Cerrada')}</td>
          <td>${asistencia}</td>
        </tr>
      `;
    }).join('');

    container.innerHTML = `
      <table class="curso-sesiones-table">
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Hora</th>
            <th>Jornada</th>
            <th>Docente</th>
            <th>Estado</th>
            <th>Asistencia</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  }

  function renderQrSesionAbierta(sesionesDisponibles, curso) {
    const puedeMarcarAsistencia = curso && typeof curso.puede_marcar_asistencia === 'boolean'
      ? curso.puede_marcar_asistencia
      : !!(curso && curso.matricula_activa);
    sesionAbiertaActual = (sesionesDisponibles || []).find(s => s.estado === 1 && s.token_asistencia) || null;
    if (!puedeMarcarAsistencia || !sesionAbiertaActual || !qrCardEl || !qrInfoEl || !qrBoxEl || !marcarBtn) {
      if (qrCardEl) qrCardEl.style.display = 'none';
      return;
    }

    qrCardEl.style.display = 'block';
    qrInfoEl.textContent = `Sesion #${sesionAbiertaActual.id_sesion} · ${sesionAbiertaActual.fecha} ${sesionAbiertaActual.hora_inicio}-${sesionAbiertaActual.hora_fin}`;
    qrBoxEl.innerHTML = '';
    setFeedback('', false);

    if (window.QRCode && sesionAbiertaActual.token_asistencia) {
      new window.QRCode(qrBoxEl, {
        text: sesionAbiertaActual.token_asistencia,
        width: 180,
        height: 180,
      });
    } else {
      qrBoxEl.textContent = 'No se pudo generar el QR en este navegador.';
    }

    if (sesionAbiertaActual.asistencia_marcada) {
      marcarBtn.disabled = true;
      marcarBtn.textContent = 'Asistencia ya marcada';
      setFeedback('Tu asistencia ya fue registrada para esta sesion.', false);
    } else {
      marcarBtn.disabled = false;
      marcarBtn.textContent = 'Marcar Asistencia';
    }
  }

  async function cargarDetalleCurso(idCurso) {
    titleEl.textContent = 'Detalle del curso';
    metaEl.textContent = 'Cargando informacion...';
    if (infoEl) {
      infoEl.innerHTML = '<p class="curso-sesiones-empty">Cargando informacion del curso...</p>';
    }
    futurasEl.innerHTML = '<p class="curso-sesiones-empty">Cargando...</p>';
    pasadasEl.innerHTML = '<p class="curso-sesiones-empty">Cargando...</p>';
    if (qrCardEl) qrCardEl.style.display = 'none';
    abrirModalSesiones();

    try {
      const response = await fetch(`/api/curso_detalle/${encodeURIComponent(idCurso)}`, {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
          'Accept': 'application/json',
        },
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.ok) {
        const error = payload.error || `Error HTTP ${response.status}`;
        throw new Error(error);
      }

      const curso = payload.curso || {};
      titleEl.textContent = curso.nombre || 'Detalle del curso';
      metaEl.textContent = `${curso.id || ''} · ${curso.modalidad || 'Modalidad no definida'} · ${curso.mes || ''} ${curso.anio || ''}`.trim();

      renderInfoCurso(curso);
      const sesionesFuturas = payload.sesiones_futuras || [];
      const sesionesPasadas = payload.sesiones_pasadas || [];
      renderTablaSesiones(futurasEl, sesionesFuturas);
      renderTablaSesiones(pasadasEl, sesionesPasadas);
      renderQrSesionAbierta([...sesionesFuturas, ...sesionesPasadas], curso);
    } catch (error) {
      const mensaje = (error && error.message) || 'No se pudo cargar el detalle del curso.';
      if (infoEl) {
        infoEl.innerHTML = `<p class="curso-sesiones-empty" style="color:#dc2626;">${mensaje}</p>`;
      }
      futurasEl.innerHTML = `<p class="curso-sesiones-empty" style="color:#dc2626;">${mensaje}</p>`;
      pasadasEl.innerHTML = '<p class="curso-sesiones-empty">Sin datos.</p>';
      if (qrCardEl) qrCardEl.style.display = 'none';
    }
  }

  if (marcarBtn) {
    marcarBtn.addEventListener('click', async function() {
      if (!sesionAbiertaActual || !sesionAbiertaActual.id_sesion || !sesionAbiertaActual.token_asistencia) {
        setFeedback('No hay una sesion abierta para marcar asistencia.', true);
        return;
      }

      marcarBtn.disabled = true;
      setFeedback('Registrando asistencia...', false);

      try {
        const response = await fetch(`/api/sesion/${sesionAbiertaActual.id_sesion}/marcar_asistencia`, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          body: JSON.stringify({
            token_asistencia: sesionAbiertaActual.token_asistencia,
          }),
        });

        const payload = await response.json().catch(() => ({}));
        if (!response.ok || !payload.ok) {
          const error = payload.error || `Error HTTP ${response.status}`;
          throw new Error(error);
        }

        sesionAbiertaActual.asistencia_marcada = true;
        setFeedback(payload.mensaje || 'Asistencia registrada correctamente.', false);
        marcarBtn.textContent = 'Asistencia ya marcada';
      } catch (error) {
        marcarBtn.disabled = false;
        setFeedback((error && error.message) || 'No se pudo marcar asistencia.', true);
      }
    });
  }

  function activarInteraccionCurso(elemento) {
    if (!elemento) return;

    const abrir = function() {
      const idCurso = (elemento.dataset.cursoModalId || elemento.dataset.idCurso || '').trim();
      if (!idCurso) return;
      cargarDetalleCurso(idCurso);
    };

    elemento.addEventListener('click', function(event) {
      if (event.target.closest('form, button, a, input, select, textarea')) {
        return;
      }
      abrir();
    });

    elemento.addEventListener('keydown', function(event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        abrir();
      }
    });
  }

  document.querySelectorAll('.curso-modal-trigger').forEach(activarInteraccionCurso);
})();


// ─── CALENDARIO DOCENTE (MES / SEMANA / DIA) ───
(function() {
  const dataEl = document.getElementById('docente-calendar-data');
  const shellEl = document.getElementById('doc-cal-shell');
  const weekHeaderEl = document.getElementById('doc-cal-week-header');
  const gridEl = document.getElementById('doc-cal-grid');
  const titleEl = document.getElementById('doc-cal-title');
  const summaryEl = document.getElementById('doc-cal-summary');
  const prevBtn = document.getElementById('doc-cal-prev');
  const nextBtn = document.getElementById('doc-cal-next');
  const todayBtn = document.getElementById('doc-cal-today');
  const viewButtons = document.querySelectorAll('.doc-cal-view-btn[data-doc-view]');

  if (!dataEl || !gridEl || !titleEl || !shellEl) {
    return;
  }

  let eventos = [];
  try {
    const parsed = JSON.parse(dataEl.textContent || '[]');
    eventos = Array.isArray(parsed) ? parsed : [];
  } catch (_err) {
    eventos = [];
  }

  const meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
  const diasCortos = ['dom', 'lun', 'mar', 'mie', 'jue', 'vie', 'sab'];
  const diasLargos = ['domingo', 'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado'];
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);

  const estado = {
    vista: 'mes',
    cursor: new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate())
  };

  function inicioSemanaDomingo(fecha) {
    const base = normalizarFecha(fecha);
    base.setDate(base.getDate() - base.getDay());
    return base;
  }

  function tituloSemana(inicio, fin) {
    if (inicio.getMonth() === fin.getMonth() && inicio.getFullYear() === fin.getFullYear()) {
      return `Semana del ${inicio.getDate()} al ${fin.getDate()} de ${meses[inicio.getMonth()]} de ${inicio.getFullYear()}`;
    }
    return `Semana del ${inicio.getDate()} de ${meses[inicio.getMonth()]} al ${fin.getDate()} de ${meses[fin.getMonth()]} de ${fin.getFullYear()}`;
  }

  function normalizarFecha(fecha) {
    const copia = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
    copia.setHours(0, 0, 0, 0);
    return copia;
  }

  function sumarDias(fecha, dias) {
    const copia = normalizarFecha(fecha);
    copia.setDate(copia.getDate() + dias);
    return copia;
  }

  function fechaIso(fecha) {
    const y = String(fecha.getFullYear());
    const m = String(fecha.getMonth() + 1).padStart(2, '0');
    const d = String(fecha.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  const eventosPorFecha = {};
  eventos.forEach(evento => {
    const key = String(evento.fecha_iso || '').trim();
    if (!key) return;
    if (!eventosPorFecha[key]) {
      eventosPorFecha[key] = [];
    }
    eventosPorFecha[key].push(evento);
  });

  Object.keys(eventosPorFecha).forEach(key => {
    eventosPorFecha[key].sort((a, b) => {
      const hA = String(a.hora_inicio || '00:00').slice(0, 5);
      const hB = String(b.hora_inicio || '00:00').slice(0, 5);
      return hA.localeCompare(hB);
    });
  });

  function categoriaEvento(evento) {
    const idCurso = String(evento.id_curso || '').toUpperCase();
    const modalidad = String(evento.modalidad || '').toLowerCase();

    if (evento.tipo_evento === 'curso') {
      return 'is-inicio';
    }
    if (Number(evento.estado) === 2) {
      return 'is-fin';
    }
    if (modalidad.includes('presencial') || idCurso.includes('-P-')) {
      return 'is-presencial';
    }
    if (modalidad.includes('virtual') || idCurso.includes('-V-')) {
      return 'is-virtual';
    }
    return 'is-otros';
  }

  function textoEvento(evento) {
    const nombre = evento.nombre_curso || evento.id_curso || 'Curso';
    if (evento.tipo_evento === 'curso') {
      return `Inicio: ${nombre}`;
    }
    const hora = (evento.hora_inicio && evento.hora_fin)
      ? ` ${String(evento.hora_inicio).slice(0, 5)}-${String(evento.hora_fin).slice(0, 5)}`
      : '';
    return `${nombre}${hora}`;
  }

  function etiquetaTipoEvento(evento) {
    if (evento.tipo_evento === 'curso') {
      return 'Inicio';
    }
    if (Number(evento.estado) === 2) {
      return 'Fin';
    }
    return 'Sesion';
  }

  function etiquetaHoraEvento(evento) {
    if (!evento.hora_inicio || !evento.hora_fin) {
      return 'Todo el dia';
    }
    const inicio = String(evento.hora_inicio).slice(0, 5);
    const fin = String(evento.hora_fin).slice(0, 5);
    return `${inicio}-${fin}`;
  }

  function crearNodoEvento(evento) {
    const item = document.createElement('div');
    item.className = `doc-cal-event ${categoriaEvento(evento)}`;

    const top = document.createElement('div');
    top.className = 'doc-cal-event-top';

    const chip = document.createElement('span');
    chip.className = 'doc-cal-event-chip';
    chip.textContent = etiquetaTipoEvento(evento);

    const hora = document.createElement('span');
    hora.className = 'doc-cal-event-time';
    hora.textContent = etiquetaHoraEvento(evento);

    top.appendChild(chip);
    top.appendChild(hora);

    const text = document.createElement('div');
    text.className = 'doc-cal-event-title';
    text.textContent = textoEvento(evento);

    item.appendChild(top);
    item.appendChild(text);
    return item;
  }

  function renderEventos(celda, eventosDia, limite, mostrarTodos) {
    if (!eventosDia || !eventosDia.length) {
      return false;
    }

    const lista = document.createElement('div');
    lista.className = 'doc-cal-events';

    const items = mostrarTodos ? eventosDia : eventosDia.slice(0, limite);
    items.forEach(evento => lista.appendChild(crearNodoEvento(evento)));

    if (!mostrarTodos && eventosDia.length > limite) {
      const mas = document.createElement('span');
      mas.className = 'doc-cal-more';
      mas.textContent = `+${eventosDia.length - limite} mas`;
      lista.appendChild(mas);
    }

    celda.appendChild(lista);
    return true;
  }

  function crearCeldaDia(fecha, opciones = {}) {
    const {
      esOtroMes = false,
      mostrarEtiquetaDia = false,
      etiquetaDia = '',
      mostrarTodos = false,
      limite = 2,
      mostrarVacio = false,
      habilitarClickDia = false,
    } = opciones;

    const fechaActual = normalizarFecha(fecha);
    const iso = fechaIso(fechaActual);
    const eventosDia = eventosPorFecha[iso] || [];

    const celda = document.createElement('div');
    celda.className = `doc-cal-cell${esOtroMes ? ' other-month' : ''}`;

    if (fechaActual.getTime() === hoy.getTime()) {
      celda.classList.add('is-today');
    }

    if (habilitarClickDia && !esOtroMes) {
      celda.style.cursor = 'pointer';
      celda.addEventListener('click', function() {
        estado.cursor = fechaActual;
        activarVista('dia');
      });
    }

    const head = document.createElement('div');
    head.className = 'doc-cal-day-head';

    const numero = document.createElement('span');
    numero.className = 'doc-cal-day-number';
    numero.textContent = String(fechaActual.getDate());
    head.appendChild(numero);

    if (mostrarEtiquetaDia) {
      const etiqueta = document.createElement('span');
      etiqueta.className = 'doc-cal-day-label';
      etiqueta.textContent = etiquetaDia;
      head.appendChild(etiqueta);
    }

    celda.appendChild(head);

    const tieneEventos = renderEventos(celda, eventosDia, limite, mostrarTodos);
    if (!tieneEventos && mostrarVacio) {
      const vacio = document.createElement('div');
      vacio.className = 'doc-cal-empty';
      vacio.textContent = 'No hay eventos para esta fecha.';
      celda.appendChild(vacio);
    }

    return {
      celda,
      totalEventos: eventosDia.length,
    };
  }

  function aplicarVistaVisual() {
    shellEl.classList.remove('view-month', 'view-week', 'view-day');
    if (estado.vista === 'semana') {
      shellEl.classList.add('view-week');
      if (weekHeaderEl) weekHeaderEl.style.display = 'grid';
      return;
    }
    if (estado.vista === 'dia') {
      shellEl.classList.add('view-day');
      if (weekHeaderEl) weekHeaderEl.style.display = 'none';
      return;
    }
    shellEl.classList.add('view-month');
    if (weekHeaderEl) weekHeaderEl.style.display = 'grid';
  }

  function renderMes() {
    const base = normalizarFecha(estado.cursor);
    const year = base.getFullYear();
    const month = base.getMonth();
    const inicioMes = new Date(year, month, 1);
    const inicioGrilla = new Date(year, month, 1 - inicioMes.getDay());

    titleEl.textContent = `${meses[month]} de ${year}`;
    gridEl.innerHTML = '';

    let totalEventos = 0;

    for (let idx = 0; idx < 42; idx += 1) {
      const fecha = sumarDias(inicioGrilla, idx);
      const esOtroMes = fecha.getMonth() !== month;
      const nodo = crearCeldaDia(fecha, {
        esOtroMes,
        mostrarTodos: false,
        limite: 2,
        habilitarClickDia: true,
      });

      if (!esOtroMes) {
        totalEventos += nodo.totalEventos;
      }
      gridEl.appendChild(nodo.celda);
    }

    if (summaryEl) {
      summaryEl.textContent = `${totalEventos} evento(s) en ${meses[month]}`;
    }
  }

  function renderSemana() {
    const inicio = inicioSemanaDomingo(estado.cursor);
    const fin = sumarDias(inicio, 6);
    titleEl.textContent = tituloSemana(inicio, fin);
    gridEl.innerHTML = '';

    let totalEventos = 0;
    for (let idx = 0; idx < 7; idx += 1) {
      const fecha = sumarDias(inicio, idx);
      const nodo = crearCeldaDia(fecha, {
        mostrarEtiquetaDia: true,
        etiquetaDia: `${diasCortos[fecha.getDay()]} ${fecha.getDate()}`,
        mostrarTodos: true,
        limite: 8,
      });
      totalEventos += nodo.totalEventos;
      gridEl.appendChild(nodo.celda);
    }

    if (summaryEl) {
      summaryEl.textContent = `${totalEventos} evento(s) en esta semana`;
    }
  }

  function renderDia() {
    const fecha = normalizarFecha(estado.cursor);
    titleEl.textContent = `${diasLargos[fecha.getDay()]}, ${fecha.getDate()} de ${meses[fecha.getMonth()]} de ${fecha.getFullYear()}`;
    gridEl.innerHTML = '';

    const nodo = crearCeldaDia(fecha, {
      mostrarEtiquetaDia: true,
      etiquetaDia: diasLargos[fecha.getDay()],
      mostrarTodos: true,
      limite: 99,
      mostrarVacio: true,
    });
    gridEl.appendChild(nodo.celda);

    if (summaryEl) {
      summaryEl.textContent = `${nodo.totalEventos} evento(s) para este dia`;
    }
  }

  function renderActual() {
    aplicarVistaVisual();
    if (estado.vista === 'semana') {
      renderSemana();
      return;
    }
    if (estado.vista === 'dia') {
      renderDia();
      return;
    }
    renderMes();
  }

  function activarVista(vista) {
    estado.vista = ['mes', 'semana', 'dia'].includes(vista) ? vista : 'mes';
    viewButtons.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.docView === estado.vista);
    });
    renderActual();
  }

  function moverCursor(delta) {
    const cursor = normalizarFecha(estado.cursor);
    if (estado.vista === 'dia') {
      cursor.setDate(cursor.getDate() + delta);
    } else if (estado.vista === 'semana') {
      cursor.setDate(cursor.getDate() + (delta * 7));
    } else {
      cursor.setMonth(cursor.getMonth() + delta);
    }
    estado.cursor = cursor;
    renderActual();
  }

  if (prevBtn) {
    prevBtn.addEventListener('click', function() {
      moverCursor(-1);
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', function() {
      moverCursor(1);
    });
  }

  if (todayBtn) {
    todayBtn.addEventListener('click', function() {
      estado.cursor = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
      renderActual();
    });
  }

  viewButtons.forEach(btn => {
    btn.addEventListener('click', function() {
      activarVista(this.dataset.docView || 'mes');
    });
  });

  activarVista('mes');
})();
