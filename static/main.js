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
