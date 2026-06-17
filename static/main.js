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
    const valido = /^\d{3,12}$/.test(val);
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
  const certContainerEl = document.getElementById('csd-cert-container');
  const requisitosContainerEl = document.getElementById('csd-requisitos-container');
  const requisitosListEl = document.getElementById('csd-requisitos-list');
  const requisitosSubtitleEl = document.getElementById('csd-requisitos-subtitle');

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

  function escapeHtml(texto) {
    return String(texto || '').replace(/[&<>"']/g, function(match) {
      return {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      }[match];
    });
  }

  function renderRequisitos(curso) {
    if (!requisitosContainerEl) return;
    const raw = String((curso && curso.requisitos) || '').trim();
    if (!raw) {
      if (requisitosSubtitleEl) requisitosSubtitleEl.textContent = 'Sin requisitos definidos';
      if (requisitosListEl) {
        requisitosListEl.innerHTML = '';
        requisitosListEl.style.display = 'none';
      }
      return;
    }

    const items = raw.split(/[,;\n]+/).map(item => item.trim()).filter(Boolean);
    if (!items.length) {
      if (requisitosSubtitleEl) requisitosSubtitleEl.textContent = 'Sin requisitos definidos';
      if (requisitosListEl) {
        requisitosListEl.innerHTML = '';
        requisitosListEl.style.display = 'none';
      }
      return;
    }

    if (requisitosSubtitleEl) {
      requisitosSubtitleEl.textContent = `${items.length} requisito(s) para aprobar`;
    }
    if (requisitosListEl) {
      requisitosListEl.style.display = 'block';
      requisitosListEl.innerHTML = items.map(item => `<li>${escapeHtml(item)}</li>`).join('');
    }
  }

  function renderCertificado(curso) {
    if (!certContainerEl) return;
    
    if (curso.estado_matricula === 'APROBADA') {
      if (curso.plantilla_disponible) {
        certContainerEl.innerHTML = `
          <div style="display: flex; align-items: center; gap: .85rem;">
            <div class="csd-cert-icon" style="background: rgba(16, 185, 129, .2); color: #047857;"><span class="material-symbols-outlined" style="vertical-align: middle; font-size: inherit;">military_tech</span></div>
            <div>
              <p class="csd-cert-title" style="color: #065f46;">Certificado Listo</p>
              <p class="csd-cert-sub">Tu certificado ya está disponible</p>
            </div>
          </div>
          <a href="/descargar_certificado/${curso.matricula_id}" target="_blank" style="text-decoration: none;">
            <button type="button" class="btn-primary-ipsd" style="font-size: .8rem; padding: .4rem .8rem; background: #059669; border: none;">
              Descargar
            </button>
          </a>
        `;
      } else {
        certContainerEl.innerHTML = `
          <div style="display: flex; align-items: center; gap: .85rem;">
            <div class="csd-cert-icon" style="background: rgba(226, 232, 240, .8); color: #64748b;"><span class="material-symbols-outlined" style="vertical-align: middle; font-size: inherit;">military_tech</span></div>
            <div>
              <p class="csd-cert-title" style="color:#334155;">Certificado no configurado</p>
              <p class="csd-cert-sub">Pendiente de emisión por la dirección</p>
            </div>
          </div>
          <div class="csd-cert-lock" style="color: #94a3b8; padding-right: 0.5rem;"><span class="material-symbols-outlined" style="vertical-align: middle; font-size: inherit;">info</span></div>
        `;
      }
    } else {
      certContainerEl.innerHTML = `
        <div style="display: flex; align-items: center; gap: .85rem;">
          <div class="csd-cert-icon" style="background: rgba(255, 223, 153, .4); color: #775a00;"><span class="material-symbols-outlined" style="vertical-align: middle; font-size: inherit;">military_tech</span></div>
          <div>
            <p class="csd-cert-title">Certificado no disponible</p>
            <p class="csd-cert-sub">Se habilita al aprobar</p>
          </div>
        </div>
        <div class="csd-cert-lock" style="color: #747780; padding-right: 0.5rem;"><span class="material-symbols-outlined" style="vertical-align: middle; font-size: inherit;">lock</span></div>
      `;
    }
  }

  function renderInfoCurso(curso) {
    const modalidad = curso.modalidad || 'No definida';
    const periodo = `${curso.mes || ''} ${curso.anio || ''}`.trim() + (curso.periodo ? ` · Período ${curso.periodo}` : '');
    const horario = curso.horario_matriculado || 'Por confirmar';
    const horasTotales = Number(curso.horas_totales || 0);
    const semanasDuracion = Number(curso.semanas_duracion || 1);
    const duracion = `${horasTotales}h · ${semanasDuracion} semana(s)`;

    // Fill bento info cells
    const elMod = document.getElementById('csd-info-modalidad');
    const elPer = document.getElementById('csd-info-periodo');
    const elDur = document.getElementById('csd-info-duracion');
    const elJor = document.getElementById('csd-info-jornada');
    if (elMod) elMod.textContent = modalidad;
    if (elPer) elPer.textContent = periodo || '—';
    if (elDur) elDur.textContent = duracion;
    if (elJor) elJor.textContent = horario;

    // Badge ID
    const badgeId = document.getElementById('csd-badge-id');
    if (badgeId) badgeId.textContent = curso.catalogo_id || curso.id || '—';

    // Badge status
    const badgeStatus = document.getElementById('csd-badge-status');
    if (badgeStatus) {
      const estado = curso.estado_matricula || '';
      badgeStatus.className = 'csd-badge csd-badge--status';
      if (estado === 'APROBADA') {
        badgeStatus.textContent = 'APROBADO';
        badgeStatus.classList.add('csd-status-aprobado');
      } else if (estado === 'CANCELADA' || estado === 'NO_APROBADA' || estado === 'ABANDONO') {
        badgeStatus.textContent = curso.estado_matricula_nombre || estado;
        badgeStatus.classList.add('csd-status-cancelado');
      } else {
        badgeStatus.textContent = curso.estado_matricula_nombre || 'EN CURSO';
      }
    }
  }

  function renderTablaSesiones(container, sesiones) {
    if (!container) return;

    if (!sesiones || sesiones.length === 0) {
      container.innerHTML = '<p class="curso-sesiones-empty" style="font-size:.8rem; color:#747780; padding:.5rem 0;">Sin sesiones para mostrar.</p>';
      return;
    }

    const MESES_CORTOS = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC'];

    const items = sesiones.map(s => {
      // Parse date chip
      let chipMonth = '—', chipDay = '—';
      if (s.fecha) {
        const partes = s.fecha.split('-');
        if (partes.length === 3) {
          chipMonth = MESES_CORTOS[parseInt(partes[1], 10) - 1] || '—';
          chipDay = String(parseInt(partes[2], 10));
        }
      }

      const hora = (s.hora_inicio && s.hora_fin)
        ? `${s.hora_inicio.slice(0,5)} - ${s.hora_fin.slice(0,5)}`
        : 'Hora no definida';

      const docente = s.docente_sesion ? `<span class="material-symbols-outlined" style="vertical-align: middle; font-size: inherit;">person</span> ${s.docente_sesion}` : `<span class="material-symbols-outlined" style="vertical-align: middle; font-size: inherit;">schedule</span> ${hora}`;

      let badgeHtml;
      if (s.asistencia_marcada) {
        badgeHtml = '<span class="csd-session-badge csd-session-badge--asistio">✓ ASISTIÓ</span>';
      } else if (s.estado_texto === 'Finalizada') {
        badgeHtml = '<span class="csd-session-badge csd-session-badge--ausente">✕ AUSENTE</span>';
      } else {
        badgeHtml = '<span class="csd-session-badge csd-session-badge--pendiente">⏳ PENDIENTE</span>';
      }

      const tema = s.tema_sesion || s.jornada || 'Sesión programada';

      return `
        <div class="csd-session-item">
          <div class="csd-session-left">
            <div class="csd-session-date-chip">
              <span class="chip-month">${chipMonth}</span>
              <span class="chip-day">${chipDay}</span>
            </div>
            <div class="csd-session-info">
              <p class="csd-session-name">${tema}</p>
              <p class="csd-session-meta">${docente}</p>
            </div>
          </div>
          ${badgeHtml}
        </div>
      `;
    }).join('');

    container.innerHTML = items;
  }

  async function cargarDetalleCurso(idCurso) {
    // Reset title & status badge
    const titleEl2 = document.getElementById('curso-sesiones-title');
    if (titleEl2) titleEl2.textContent = 'Cargando...';
    const badgeId2 = document.getElementById('csd-badge-id');
    if (badgeId2) badgeId2.textContent = '…';
    const badgeStatus2 = document.getElementById('csd-badge-status');
    if (badgeStatus2) { badgeStatus2.textContent = 'EN CURSO'; badgeStatus2.className = 'csd-badge csd-badge--status'; }

    // Reset bento cells
    ['csd-info-modalidad','csd-info-periodo','csd-info-inicio','csd-info-jornada'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = '…';
    });

    if (futurasEl) futurasEl.innerHTML = '<p class="curso-sesiones-empty" style="font-size:.8rem;color:#747780;padding:.5rem 0;">Cargando...</p>';
    if (pasadasEl) pasadasEl.innerHTML = '<p class="curso-sesiones-empty" style="font-size:.8rem;color:#747780;padding:.5rem 0;">Cargando...</p>';
    if (qrCardEl) qrCardEl.style.display = 'none';
    if (requisitosSubtitleEl) requisitosSubtitleEl.textContent = 'Cargando requisitos...';
    if (requisitosListEl) {
      requisitosListEl.innerHTML = '';
      requisitosListEl.style.display = 'none';
    }

    abrirModalSesiones();

    try {
      const response = await fetch(`/api/curso_detalle/${encodeURIComponent(idCurso)}`, {
        method: 'GET',
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' },
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || `Error HTTP ${response.status}`);
      }

      const curso = payload.curso || {};
      if (titleEl2) titleEl2.textContent = curso.nombre || 'Detalle del curso';

      renderInfoCurso(curso);
      renderCertificado(curso);
      renderRequisitos(curso);

      const sesionesFuturas = payload.sesiones_futuras || [];
      const sesionesPasadas = payload.sesiones_pasadas || [];

      // Show/hide section wrappers
      const secFuturas = document.getElementById('csd-section-futuras');
      const secPasadas = document.getElementById('csd-section-pasadas');
      if (secFuturas) secFuturas.style.display = sesionesFuturas.length ? '' : 'none';
      if (secPasadas) secPasadas.style.display = sesionesPasadas.length ? '' : 'none';

      renderTablaSesiones(futurasEl, sesionesFuturas);
      renderTablaSesiones(pasadasEl, sesionesPasadas);
      renderQrSesionAbierta([...sesionesFuturas, ...sesionesPasadas], curso);
    } catch (error) {
      const msg = (error && error.message) || 'No se pudo cargar el detalle.';
      if (futurasEl) futurasEl.innerHTML = `<p style="font-size:.82rem;color:#dc2626;padding:.4rem 0;">${msg}</p>`;
      if (pasadasEl) pasadasEl.innerHTML = '';
      if (qrCardEl) qrCardEl.style.display = 'none';
      if (requisitosSubtitleEl) requisitosSubtitleEl.textContent = 'No disponible';
      if (requisitosListEl) {
        requisitosListEl.innerHTML = '';
        requisitosListEl.style.display = 'none';
      }
    }
  }

  function renderQrSesionAbierta(sesionesDisponibles, curso) {
    var tipoAccion = ((curso && curso.tipo_accion) || '').toUpperCase();
    var esConferencia = tipoAccion === 'CONFERENCIA';

    var puedeMarcarAsistencia = curso && typeof curso.puede_marcar_asistencia === 'boolean'
      ? curso.puede_marcar_asistencia
      : !!(curso && curso.matricula_activa);

    // ── CONFERENCIA: sistema de clics ─────────────────────────────────────
    if (esConferencia) {
      console.log('esConferencia TRUE', {puedeMarcarAsistencia, id_sesion_conferencia: curso.id_sesion_conferencia, curso});
      if (qrCardEl) qrCardEl.style.display = 'none';
      if (marcarBtn) marcarBtn.closest && marcarBtn.closest('.qr-card-section') &&
        (marcarBtn.closest('.qr-card-section').style.display = 'none');
        
      if (curso.id_sesion_conferencia && window.iniciarSistemaClics) {
        window.iniciarSistemaClics(curso.id_sesion_conferencia, qrCardEl);
      } else {
        console.warn('No se puede iniciar clics: id_sesion_conferencia o iniciarSistemaClics no disponible', {
          id_sesion: curso.id_sesion_conferencia,
          fn_iniciar: !!window.iniciarSistemaClics
        });
      }
      return;
    }

    // Detener clics si venía de una conferencia anterior
    if (window.detenerSistemaClics) window.detenerSistemaClics();

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
        
        if (currentCursoId) {
            cargarDetalleCurso(currentCursoId);
        }
        
        // Let's also dispatch an event so the dashboard can reload itself silently
        document.dispatchEvent(new Event('asistencia_marcada_ok'));
        
      } catch (error) {
        marcarBtn.disabled = false;
        setFeedback((error && error.message) || 'No se pudo marcar asistencia.', true);
      }
    });
  }

  let currentCursoId = null;

  function activarInteraccionCurso(elemento) {
    if (!elemento) return;

    const abrir = function() {
      const idCurso = (elemento.dataset.cursoModalId || elemento.dataset.idCurso || '').trim();
      if (!idCurso) return;
      currentCursoId = idCurso;
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

  window.bindCursoModals = function() {
    document.querySelectorAll('.curso-modal-trigger').forEach(function(el) {
      if (!el.dataset.interaccionBound) {
        el.dataset.interaccionBound = 'true';
        activarInteraccionCurso(el);
      }
    });
  };

  window.bindCursoModals();
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
    const modalidad = String(evento.modalidad || '').toLowerCase();

    if (evento.tipo_evento === 'curso') {
      return 'is-inicio';
    }
    if (Number(evento.estado) === 2) {
      return 'is-fin';
    }
    if (modalidad.includes('presencial')) {
      return 'is-presencial';
    }
    if (modalidad.includes('virtual')) {
      return 'is-virtual';
    }
    return 'is-otros';
  }

  function textoEvento(evento) {
    const nombre = evento.nombre_curso || evento.edicion_id || evento.id_curso || 'Curso';
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


// ─── SISTEMA DE CLICS DE ATENCIÓN — CONFERENCIA ───────────────────────────
(function () {
  'use strict';

  var POLL_INTERVAL_MS = 25000;   // cada 25 segundos
  var _pollTimer       = null;
  var _idSesionConf    = null;    // sesion activa de conferencia
  var _ventanaActiva   = null;    // objeto {ventana_id, segundos_restantes}
  var _cuentaTimer     = null;    // setInterval del countdown

  // ── Elementos del DOM ─────────────────────────────────────────────────────
  function _el(id) { return document.getElementById(id); }

  // ── CSS del stepper (inyectado una sola vez) ──────────────────────────────
  (function injectCss() {
    if (document.getElementById('ca-style')) return;
    var s = document.createElement('style');
    s.id = 'ca-style';
    s.textContent = [
      '#ca-container{background:#ffffff;border:1px solid #e2e8f0;border-radius:1rem;padding:1.5rem;box-shadow:0 4px 6px -1px rgba(0,0,0,0.05),0 2px 4px -2px rgba(0,0,0,0.05);margin-top:1.5rem;}',
      '#ca-title{font-size:1.1rem;font-weight:700;color:#1e293b;margin:0 0 1.25rem 0;display:flex;align-items:center;gap:0.5rem;}',
      '#ca-stepper{display:flex;align-items:center;gap:0;margin-bottom:1.1rem;}',
      '.ca-step{display:flex;flex-direction:column;align-items:center;flex:1;}',
      '.ca-step-circle{width:28px;height:28px;border-radius:50%;border:2.5px solid #d1d5db;background:#f9fafb;',
        'display:flex;align-items:center;justify-content:center;',
        'font-size:.7rem;font-weight:700;color:#9ca3af;transition:all .35s ease;position:relative;z-index:1;}',
      '.ca-step.done .ca-step-circle{background:#10b981;border-color:#10b981;color:#fff;}',
      '.ca-step.active .ca-step-circle{background:#f59e0b;border-color:#f59e0b;color:#fff;',
        'box-shadow:0 0 0 5px rgba(245,158,11,.25);animation:ca-pulse 1.6s infinite;}',
      '.ca-step-line{flex:1;height:2.5px;background:#e5e7eb;transition:background .35s;}',
      '.ca-step.done + .ca-step-line,.ca-step.done ~ .ca-step .ca-step-line{background:#10b981;}',
      '.ca-step-label{font-size:.62rem;color:#9ca3af;margin-top:.3rem;font-weight:600;letter-spacing:.02em;}',
      '.ca-step.done .ca-step-label{color:#059669;}',
      '.ca-step.active .ca-step-label{color:#d97706;}',
      '#ca-progress-bar-wrap{background:#cbd5e1;border-radius:999px;height:8px;overflow:hidden;margin-bottom:1.2rem;box-shadow:inset 0 1px 2px rgba(0,0,0,0.1);}',
      '#ca-progress-bar{height:100%;border-radius:999px;background:linear-gradient(90deg,#f59e0b,#10b981);',
        'width:0%;transition:width .6s ease;}',
      '#ca-btn-clic{width:100%;padding:.65rem;border:none;border-radius:.85rem;font-size:.9rem;',
        'font-weight:700;cursor:pointer;transition:all .25s;display:flex;align-items:center;',
        'justify-content:center;gap:.5rem;}',
      '#ca-btn-clic.ca-estado-espera{background:#f3f4f6;color:#9ca3af;cursor:default;}',
      '#ca-btn-clic.ca-estado-activo{background:linear-gradient(135deg,#f59e0b 0%,#d97706 100%);',
        'color:#fff;animation:ca-pulse 1.6s infinite;cursor:pointer;}',
      '#ca-btn-clic.ca-estado-ok{background:#ecfdf5;color:#059669;cursor:default;}',
      '#ca-btn-clic.ca-estado-aprobado{background:linear-gradient(135deg,#10b981,#059669);',
        'color:#fff;cursor:default;}',
      '#ca-feedback{font-size:.78rem;margin-top:.5rem;padding:.4rem .7rem;border-radius:.5rem;',
        'display:none;text-align:center;}',
      '#ca-feedback.ok{background:#ecfdf5;color:#065f46;display:block;}',
      '#ca-feedback.err{background:#fef2f2;color:#991b1b;display:block;}',
      '#ca-feedback.info{background:#fffbeb;color:#92400e;display:block;}',
      '@keyframes ca-pulse{0%,100%{box-shadow:0 0 0 4px rgba(245,158,11,.25);}50%{box-shadow:0 0 0 8px rgba(245,158,11,.08);}}',
    ].join('');
    document.head.appendChild(s);
  })();

  // ── Crear / actualizar el contenedor del stepper ──────────────────────────
  function _getOrCreateContainer(qrCardEl) {
    var existing = _el('ca-container');
    if (existing) return existing;

    var div = document.createElement('div');
    div.id = 'ca-container';
    div.innerHTML = [
      '<h4 id="ca-title"><span class="material-symbols-outlined" style="color:#d97706;font-size:1.4rem;">timer</span> Control de Atención</h4>',
      '<div id="ca-stepper"></div>',
      '<div id="ca-progress-bar-wrap"><div id="ca-progress-bar"></div></div>',
      '<button id="ca-btn-clic" class="ca-estado-espera">',
        '<span class="material-symbols-outlined" style="font-size:1.1rem;vertical-align:middle;">hourglass_empty</span>',
        '<span id="ca-btn-label">Esperando siguiente confirmación...</span>',
      '</button>',
      '<div id="ca-feedback"></div>',
    ].join('');

    // Insertar al final de la columna derecha (debajo de sesiones pasadas)
    var targetParent = document.querySelector('.csd-right');
    if (targetParent) {
      targetParent.appendChild(div);
    } else if (qrCardEl) {
      qrCardEl.parentNode.insertBefore(div, qrCardEl);
    } else {
      document.body.appendChild(div);
    }
    return div;
  }

  // ── Renderizar stepper según progreso ────────────────────────────────────
  function _renderStepper(completadas, total, activa) {
    var stepperEl = _el('ca-stepper');
    var progressEl = _el('ca-progress-bar');
    if (!stepperEl) return;

    stepperEl.innerHTML = '';
    for (var i = 1; i <= total; i++) {
      var done  = completadas.indexOf(i) !== -1;
      var isAct = activa && activa.ventana_id === i && !done;

      var cls = done ? 'done' : (isAct ? 'active' : '');
      var icon = done ? '✓' : (isAct ? '!' : i);

      var step = document.createElement('div');
      step.className = 'ca-step ' + cls;
      step.innerHTML =
        '<div class="ca-step-circle">' + icon + '</div>' +
        '<div class="ca-step-label">' + (done ? 'OK' : (isAct ? '¡Ahora!' : 'V' + i)) + '</div>';

      stepperEl.appendChild(step);

      // Línea separadora
      if (i < total) {
        var line = document.createElement('div');
        line.className = 'ca-step-line' + (done ? ' done' : '');
        stepperEl.appendChild(line);
      }
    }

    // Barra de progreso
    if (progressEl) {
      var pct = total > 0 ? Math.round((completadas.length / total) * 100) : 0;
      progressEl.style.width = pct + '%';
    }
  }

  // ── Actualizar el botón según el estado ──────────────────────────────────
  function _actualizarBoton(estado) {
    var btn   = _el('ca-btn-clic');
    var label = _el('ca-btn-label');
    if (!btn || !label) return;

    _detenerCuenta();
    btn.disabled = false;

    if (estado.aprobado) {
      btn.className = 'ca-estado-aprobado';
      btn.onclick = null;
      btn.disabled = true;
      label.textContent = '¡Conferencia aprobada! 🎉';
      _mostrarFeedback('ok', '¡Felicidades! Has cumplido el control de atención y tu matrícula ha sido aprobada.');
      return;
    }

    if (!estado.conferencia_activa) {
      btn.className = 'ca-estado-espera';
      btn.onclick = null;
      label.textContent = estado.motivo || 'La conferencia no está activa.';
      return;
    }

    if (!estado.ventana_activa) {
      btn.className = 'ca-estado-espera';
      btn.onclick = null;
      var restantes = (estado.total_ventanas || 5) - (estado.total_completadas || 0);
      label.textContent = restantes > 0 ? 'Esperando siguiente confirmación...' : 'Todas las ventanas completadas';
      return;
    }

    // Ventana activa
    _ventanaActiva = estado.ventana_activa;
    var seg = _ventanaActiva.segundos_restantes;

    btn.className = 'ca-estado-activo';
    btn.onclick = _onClickConfirmar;

    _iniciarCuenta(seg);
  }

  function _iniciarCuenta(seg) {
    _detenerCuenta();
    var segundos = seg;
    _actualizarLabelCuenta(segundos);
    _cuentaTimer = setInterval(function () {
      segundos--;
      if (segundos <= 0) {
        _detenerCuenta();
        var btn = _el('ca-btn-clic');
        var label = _el('ca-btn-label');
        if (btn) { btn.className = 'ca-estado-espera'; btn.onclick = null; }
        if (label) label.textContent = 'Ventana cerrada — espera la siguiente';
        _ventanaActiva = null;
      } else {
        _actualizarLabelCuenta(segundos);
      }
    }, 1000);
  }

  function _actualizarLabelCuenta(s) {
    var label = _el('ca-btn-label');
    var mm = Math.floor(s / 60), ss = s % 60;
    if (label) label.textContent =
      '¡CONFIRMA ATENCIÓN! ' + mm + ':' + (ss < 10 ? '0' : '') + ss;
  }

  function _detenerCuenta() {
    if (_cuentaTimer) { clearInterval(_cuentaTimer); _cuentaTimer = null; }
  }

  // ── Registrar el clic del docente ────────────────────────────────────────
  function _onClickConfirmar() {
    if (!_idSesionConf || !_ventanaActiva) return;
    var btn = _el('ca-btn-clic');
    if (btn) { btn.disabled = true; btn.onclick = null; }
    _detenerCuenta();

    fetch('/api/conferencia/' + _idSesionConf + '/clic', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ ventana_id: _ventanaActiva.ventana_id }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) {
          _mostrarFeedback('ok', data.mensaje || '¡Confirmación registrada!');
          _ventanaActiva = null;
          // Forzar polling inmediato para actualizar el stepper
          _poll();
        } else {
          _mostrarFeedback('err', data.error || 'No se pudo registrar el clic.');
          if (btn) btn.disabled = false;
        }
      })
      .catch(function () {
        _mostrarFeedback('err', 'Error de conexión. Intenta de nuevo.');
        if (btn) btn.disabled = false;
      });
  }

  // ── Polling ───────────────────────────────────────────────────────────────
  function _poll() {
    if (!_idSesionConf) return;
    fetch('/api/conferencia/' + _idSesionConf + '/estado', {
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' },
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) return;
        _renderStepper(
          data.ventanas_completadas || [],
          data.total_ventanas || 5,
          data.ventana_activa
        );
        _actualizarBoton(data);
      })
      .catch(function () {});
  }

  function _mostrarFeedback(tipo, msg) {
    var fb = _el('ca-feedback');
    if (!fb) return;
    fb.textContent = msg;
    fb.className = tipo;
    clearTimeout(fb._hideTimer);
    // Auto-ocultar mensajes de éxito (no los de aprobación)
    if (tipo === 'ok' && msg.indexOf('aprobada') === -1) {
      fb._hideTimer = setTimeout(function () { fb.className = ''; }, 5000);
    }
  }

  // ── Punto de entrada: llamado por cargarDetalleCurso cuando es CONFERENCIA ─
  window.iniciarSistemaClics = function (idSesion, qrCardEl) {
    // Limpiar poll anterior si cambió de curso
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
    _detenerCuenta();
    _idSesionConf   = idSesion;
    _ventanaActiva  = null;

    _getOrCreateContainer(qrCardEl);
    _poll();
    _pollTimer = setInterval(_poll, POLL_INTERVAL_MS);
  };

  window.detenerSistemaClics = function () {
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
    _detenerCuenta();
    _idSesionConf  = null;
    _ventanaActiva = null;
    var c = _el('ca-container');
    if (c) c.remove();
  };
})();
