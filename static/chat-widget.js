(function () {
  const widget = document.getElementById('ia-chat-widget');
  if (!widget) return;

  const toggleBtn = document.getElementById('ia-chat-toggle');
  const panel = document.getElementById('ia-chat-panel');
  const closeBtn = document.getElementById('ia-chat-close');
  const form = document.getElementById('ia-chat-form');
  const input = document.getElementById('ia-chat-input');
  const messages = document.getElementById('ia-chat-messages');

  const csrfToken = widget.dataset.csrfToken || '';
  const userType = widget.dataset.userType || 'docente';

  let historyLoaded = false;
  let typingNode = null;

  function escapeHtml(text) {
    return String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function scrollToBottom() {
    messages.scrollTop = messages.scrollHeight;
  }

  function createBubble(sender, text) {
    const item = document.createElement('div');
    item.className = 'ia-chat-message ' + (sender === 'user' ? 'user' : 'assistant');

    const bubble = document.createElement('div');
    bubble.className = 'ia-chat-bubble';
    bubble.innerHTML = escapeHtml(text).replace(/\n/g, '<br>');

    item.appendChild(bubble);
    return item;
  }

  function addMessage(sender, text) {
    messages.appendChild(createBubble(sender, text));
    scrollToBottom();
  }

  function setTyping(active) {
    if (active && !typingNode) {
      typingNode = document.createElement('div');
      typingNode.className = 'ia-chat-typing';
      typingNode.textContent = 'IA escribiendo...';
      messages.appendChild(typingNode);
      scrollToBottom();
      return;
    }

    if (!active && typingNode) {
      typingNode.remove();
      typingNode = null;
    }
  }

  function setOpen(open) {
    panel.classList.toggle('active', open);
    toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');

    if (open) {
      if (!historyLoaded) {
        loadHistory();
      }
      input.focus();
      return;
    }

    setTyping(false);
  }

  async function loadHistory() {
    try {
      const response = await fetch('/api/chat/history', {
        headers: { 'Accept': 'application/json' },
      });
      const data = await response.json();

      if (!response.ok || !data.ok) {
        return;
      }

      if (Array.isArray(data.messages) && data.messages.length > 0) {
        messages.innerHTML = '';
        data.messages.forEach((item) => {
          addMessage(item.sender === 'user' ? 'user' : 'assistant', item.text || '');
        });
      }

      historyLoaded = true;
    } catch (_) {
      // Silencioso: el chat sigue funcionando aunque no cargue historial.
    }
  }

  async function sendMessage(messageText) {
    addMessage('user', messageText);
    setTyping(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-CSRF-Token': csrfToken,
        },
        body: JSON.stringify({ message: messageText, user_type: userType }),
      });

      const data = await response.json();
      setTyping(false);

      if (!response.ok || !data.ok) {
        addMessage('assistant', data.error || 'No pude responder en este momento.');
        return;
      }

      addMessage('assistant', data.reply || 'No recibi respuesta del asistente.');
    } catch (_) {
      setTyping(false);
      addMessage('assistant', 'No fue posible conectar con el servicio de IA.');
    }
  }

  toggleBtn.addEventListener('click', function () {
    setOpen(!panel.classList.contains('active'));
  });

  closeBtn.addEventListener('click', function () {
    setOpen(false);
  });

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    sendMessage(text);
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && panel.classList.contains('active')) {
      setOpen(false);
    }
  });
})();
