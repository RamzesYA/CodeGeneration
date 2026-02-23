// Content script: injects a button into editor.plantuml.com and sends PUML to local server

async function getConfig() {
  return new Promise((resolve) => {
    chrome.storage.local.get({ serverUrl: 'http://localhost:8000', token: '', method: 'python', sync: true }, (items) => {
      resolve(items);
    });
  });
}

function getPumlFromPage() {
  // First try the specific XPath requested by the user
  try {
    const xpath = "//*[@id=\"editor\"]/div[2]/div/div[3]";
    const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
    const node = result.singleNodeValue;
    if (node) {
      // Try to preserve line breaks and indentation.
      // If node has explicit child lines (div/span per line), join them with '\n'.
      try {
        const children = Array.from(node.children || []);
        if (children.length > 0) {
          const lines = children.map((c) => {
            // Replace non-breaking spaces with normal spaces to preserve indentation
            let s = c.textContent || c.innerText || '';
            s = s.replace(/\u00A0/g, ' ');
            return s.replace(/\r/g, '');
          });
          const joined = lines.join('\n');
          if (joined.trim().length > 0) return joined;
        }
      } catch (e) {
        // fallback below
      }

      // Fallback: convert innerHTML breaks to newlines and decode &nbsp;
      let html = node.innerHTML || '';
      if (html) {
        // normalize <br> and <div> boundaries to newline
        html = html.replace(/<br\s*\/?>/gi, '\n');
        html = html.replace(/<\/div>/gi, '\n');
        // remove remaining tags
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        let text = tmp.textContent || tmp.innerText || '';
        text = text.replace(/\u00A0/g, ' ');
        if (text.trim().length > 0) return text;
      }

      // prefer value (for textarea-like), then textContent
      const v = node.value || node.textContent || node.innerText;
      if (v && v.trim().length > 0) return v.replace(/\u00A0/g, ' ');
    }
  } catch (e) {
    console.warn('XPath read failed', e);
  }

  // Fallbacks: try common editor elements
  let ta = document.querySelector('textarea') || document.querySelector('textarea#code') || document.querySelector('.CodeMirror textarea') || document.querySelector('.monaco-editor textarea');
  if (ta) return ta.value;

  let pre = document.querySelector('.CodeMirror .CodeMirror-code') || document.querySelector('.editor-textarea') || document.querySelector('.editor');
  if (pre) return pre.innerText || pre.textContent;

  let any = document.querySelector('[data-uml]') || document.querySelector('#text');
  if (any) return any.value || any.innerText || any.textContent;

  return null;
}

function injectButton() {
  if (document.getElementById('puml-send-btn')) return;

  const btn = document.createElement('button');
  btn.id = 'puml-send-btn';
  btn.textContent = 'Send to Local Generator';
  btn.style.position = 'fixed';
  btn.style.right = '16px';
  btn.style.bottom = '16px';
  btn.style.zIndex = 999999;
  btn.style.padding = '8px 12px';
  btn.style.background = '#0b5fff';
  btn.style.color = 'white';
  btn.style.border = 'none';
  btn.style.borderRadius = '6px';
  btn.style.boxShadow = '0 2px 6px rgba(0,0,0,0.2)';

  btn.addEventListener('click', async () => {
    const config = await getConfig();
    let puml = getPumlFromPage();
    if (!puml) {
      puml = prompt('Could not detect PlantUML on the page. Paste PlantUML text here:');
      if (!puml) return;
    }
    // Print the detected PlantUML to the page console for debugging/learning
    try {
      // Log to page console for developer visibility
      console.log('Detected PlantUML:\n', puml);
    } catch (e) { /* ignore */ }
    // Show diagram/type selection dialog to choose diagram type and languages
    try {
      const choice = await showDiagramDialog();
      if (!choice) return; // cancelled

      const payload = {
        action: 'log_puml',
        payload: {
          serverUrl: config.serverUrl,
          token: config.token,
          puml,
          diagramType: choice.diagramType,
          languages: choice.languages // array, may be empty for deployment
        }
      };

      const resp = await new Promise((resolve) => chrome.runtime.sendMessage(payload, (r) => resolve(r)));
      if (!resp) throw new Error(resp && resp.error ? resp.error : 'no response');
      console.log('Server response (raw):', resp);
      if (resp.data && resp.data.result) console.log('Parsed JSON result from server:', resp.data.result);

      if (resp.status === 200) {
        const jobId = resp.data && resp.data.job_id;
        if (!jobId) {
          alert('PlantUML sent, but no job_id returned from server.');
          return;
        }

        const filename = await downloadGeneratedFiles(config.serverUrl, config.token, jobId);
        alert('Готово. Скачан файл: ' + filename);
      } else {
        const detail = resp && resp.data && resp.data.detail;
        if (detail) {
          alert(typeof detail === 'string' ? detail : JSON.stringify(detail));
        } else {
          alert('Server response: ' + resp.status + ' ' + JSON.stringify(resp.data || resp));
        }
      }
    } catch (e) {
      alert('Network error: ' + e.message);
    }
  });

  document.body.appendChild(btn);
}

function extractFilename(contentDisposition, fallbackName) {
  if (!contentDisposition) return fallbackName;
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1].trim());
    } catch (e) {
      return utf8Match[1].trim();
    }
  }
  const plainMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  if (plainMatch && plainMatch[1]) return plainMatch[1].trim();
  return fallbackName;
}

function fallbackNameByContentType(contentType, jobId) {
  const ct = (contentType || '').toLowerCase();
  if (ct.includes('zip')) return `${jobId}.zip`;
  if (ct.includes('json')) return `${jobId}.json`;
  if (ct.includes('sql')) return `${jobId}.sql`;
  if (ct.includes('yaml') || ct.includes('yml')) return `${jobId}.yaml`;
  if (ct.includes('java')) return `${jobId}.java`;
  if (ct.includes('c++') || ct.includes('cpp')) return `${jobId}.cpp`;
  if (ct.includes('python') || ct.includes('x-python')) return `${jobId}.py`;
  return `${jobId}.txt`;
}

async function downloadGeneratedFiles(serverUrl, token, jobId) {
  const base = (serverUrl || '').replace(/\/$/, '');
  const url = `${base}/download/${encodeURIComponent(jobId)}`;
  const resp = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': 'Bearer ' + (token || '')
    }
  });

  if (!resp.ok) {
    const errText = await resp.text().catch(() => '');
    throw new Error(`download failed: ${resp.status} ${errText}`);
  }

  const blob = await resp.blob();
  const contentDisposition = resp.headers.get('Content-Disposition');
  const contentType = resp.headers.get('Content-Type');
  const fallback = fallbackNameByContentType(contentType, jobId);
  const filename = extractFilename(contentDisposition, fallback);
  console.log('Download response:', {
    status: resp.status,
    contentType,
    contentDisposition,
    blobSize: blob.size,
    filename
  });

  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = objectUrl;
  a.download = filename;
  a.style.display = 'none';
  document.body.appendChild(a);
  // Defer click to the next frame to make the download start reliably.
  requestAnimationFrame(() => a.click());
  setTimeout(() => {
    try {
      a.remove();
    } catch (e) {
      // ignore
    }
    // Keep object URL long enough; early revoke may break larger downloads.
    URL.revokeObjectURL(objectUrl);
  }, 60000);
  return filename;
}

// Modal dialog for selecting diagram type and languages
function showDiagramDialog() {
  return new Promise((resolve) => {
    // Build overlay
    const overlay = document.createElement('div');
    overlay.style.position = 'fixed';
    overlay.style.left = 0;
    overlay.style.top = 0;
    overlay.style.right = 0;
    overlay.style.bottom = 0;
    overlay.style.background = 'rgba(0,0,0,0.45)';
    overlay.style.zIndex = 1000000;
    overlay.style.display = 'flex';
    overlay.style.alignItems = 'center';
    overlay.style.justifyContent = 'center';

    const box = document.createElement('div');
    box.style.maxWidth = '560px';
    box.style.width = '95%';
    box.style.background = '#fff';
    box.style.padding = '20px';
    box.style.borderRadius = '10px';
    box.style.boxShadow = '0 12px 40px rgba(0,0,0,0.35)';
    box.style.fontFamily = 'Segoe UI, Roboto, Arial, sans-serif';
    box.style.color = '#111';

    const closeX = document.createElement('button');
    closeX.innerHTML = '&times;';
    closeX.setAttribute('aria-label', 'Close');
    closeX.style.position = 'absolute';
    closeX.style.right = '18px';
    closeX.style.top = '18px';
    closeX.style.background = 'transparent';
    closeX.style.border = 'none';
    closeX.style.fontSize = '20px';
    closeX.style.cursor = 'pointer';
    closeX.style.color = '#444';
    closeX.addEventListener('click', () => { cleanupAndResolve(null); });

    const title = document.createElement('div');
    title.textContent = 'Выберите тип диаграммы и языки';
    title.style.fontSize = '18px';
    title.style.fontWeight = 700;
    title.style.marginBottom = '6px';

    const subtitle = document.createElement('div');
    subtitle.textContent = 'Тип диаграммы определяет варианты генерации. Можно выбрать несколько языков.';
    subtitle.style.fontSize = '13px';
    subtitle.style.color = '#555';
    subtitle.style.marginBottom = '12px';

    box.appendChild(closeX);
    box.appendChild(title);
    box.appendChild(subtitle);

    // Diagram type radios (displayed as horizontal pills)
    const types = [
      { id: 'classes', label: 'Классы' },
      { id: 'database', label: 'БД' },
      { id: 'deployment', label: 'Развертывание' }
    ];
    const typeWrap = document.createElement('div');
    typeWrap.style.display = 'flex';
    typeWrap.style.gap = '8px';
    typeWrap.style.marginBottom = '14px';

    types.forEach((t, idx) => {
      const pill = document.createElement('label');
      pill.style.display = 'flex';
      pill.style.alignItems = 'center';
      pill.style.gap = '8px';
      pill.style.padding = '8px 12px';
      pill.style.borderRadius = '8px';
      pill.style.border = idx === 0 ? '2px solid #0b5fff' : '1px solid #d0d7de';
      pill.style.cursor = 'pointer';

      const r = document.createElement('input');
      r.type = 'radio';
      r.name = 'puml_diagram_type';
      r.value = t.id;
      r.style.cursor = 'pointer';
      if (idx === 0) r.checked = true;
      r.addEventListener('change', () => {
        // highlight current pill
        Array.from(typeWrap.children).forEach((ch) => ch.style.border = '1px solid #d0d7de');
        pill.style.border = '2px solid #0b5fff';
      });

      const span = document.createElement('span');
      span.textContent = t.label;
      span.style.fontSize = '14px';

      pill.appendChild(r);
      pill.appendChild(span);
      typeWrap.appendChild(pill);
    });
    box.appendChild(typeWrap);

    // Languages area (checkboxes appear based on selection)
    const langWrap = document.createElement('div');
    langWrap.style.marginTop = '8px';
    box.appendChild(langWrap);
    const validationNote = document.createElement('div');
    validationNote.style.marginTop = '8px';
    validationNote.style.fontSize = '12px';
    validationNote.style.color = '#b42318';
    validationNote.style.display = 'none';
    validationNote.textContent = 'Выберите хотя бы один язык для генерации.';
    box.appendChild(validationNote);

    const langSets = {
      classes: [
        { id: 'python', label: 'Python' },
        { id: 'cpp', label: 'C++' },
        { id: 'java', label: 'Java' }
      ],
      database: [
        { id: 'oracle', label: 'Oracle' },
        { id: 'postgresql', label: 'PostgreSQL' },
        { id: 'mysql', label: 'MySQL' }
      ],
      deployment: []
    };

    function renderLangs(selectedType) {
      langWrap.innerHTML = '';
      const header = document.createElement('div');
      header.style.fontWeight = 600;
      header.textContent = 'Языки (можно выбрать несколько)';
      header.style.marginBottom = '8px';
      langWrap.appendChild(header);

      const set = langSets[selectedType] || [];
      if (!set.length) {
        const note = document.createElement('div');
        note.style.color = '#666';
        note.style.marginTop = '6px';
        note.textContent = 'Нет дополнительных языков для выбранного типа.';
        langWrap.appendChild(note);
        return;
      }

      const grid = document.createElement('div');
      grid.style.display = 'grid';
      grid.style.gridTemplateColumns = '1fr 1fr';
      grid.style.gap = '8px 16px';

      set.forEach((l) => {
        const lab = document.createElement('label');
        lab.style.display = 'flex';
        lab.style.alignItems = 'center';
        lab.style.gap = '8px';
        lab.style.padding = '6px 8px';
        lab.style.borderRadius = '6px';
        lab.style.border = '1px solid #eef2f6';

        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.name = 'puml_lang';
        cb.value = l.id;
        cb.style.width = '16px';
        cb.style.height = '16px';

        const span = document.createElement('span');
        span.textContent = l.label;
        span.style.fontSize = '14px';

        lab.appendChild(cb);
        lab.appendChild(span);
        grid.appendChild(lab);
      });

      langWrap.appendChild(grid);
    }

    // buttons
    const btnRow = document.createElement('div');
    btnRow.style.display = 'flex';
    btnRow.style.justifyContent = 'flex-end';
    btnRow.style.marginTop = '18px';
    btnRow.style.gap = '8px';

    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Отмена';
    cancelBtn.style.background = 'transparent';
    cancelBtn.style.border = '1px solid #cbd5e1';
    cancelBtn.style.padding = '8px 12px';
    cancelBtn.style.borderRadius = '6px';
    cancelBtn.addEventListener('click', () => { cleanupAndResolve(null); });

    const okBtn = document.createElement('button');
    okBtn.textContent = 'ОК';
    okBtn.style.background = '#0b5fff';
    okBtn.style.color = 'white';
    okBtn.style.border = 'none';
    okBtn.style.padding = '8px 14px';
    okBtn.style.borderRadius = '6px';

    function updateOkState() {
      const selectedTypeNode = typeWrap.querySelector('input[name="puml_diagram_type"]:checked');
      const selectedType = selectedTypeNode ? selectedTypeNode.value : 'classes';
      const selectedLangsCount = langWrap.querySelectorAll('input[name="puml_lang"]:checked').length;
      const requiresLanguage = selectedType === 'classes' || selectedType === 'database';
      const canSubmit = !requiresLanguage || selectedLangsCount > 0;

      okBtn.disabled = !canSubmit;
      okBtn.style.opacity = canSubmit ? '1' : '0.5';
      okBtn.style.cursor = canSubmit ? 'pointer' : 'not-allowed';
      validationNote.style.display = canSubmit ? 'none' : 'block';
    }

    okBtn.addEventListener('click', () => {
      if (okBtn.disabled) return;
      const diagramType = typeWrap.querySelector('input[name="puml_diagram_type"]:checked').value;
      const langs = Array.from(langWrap.querySelectorAll('input[name="puml_lang"]:checked')).map((n) => n.value);
      cleanupAndResolve({ diagramType, languages: langs });
    });

    // initial render
    renderLangs('classes');
    updateOkState();

    // update on radio change
    typeWrap.addEventListener('change', () => {
      const v = typeWrap.querySelector('input[name="puml_diagram_type"]:checked').value;
      renderLangs(v);
      updateOkState();
    });
    langWrap.addEventListener('change', updateOkState);

    btnRow.appendChild(cancelBtn);
    btnRow.appendChild(okBtn);
    box.appendChild(btnRow);

    overlay.appendChild(box);
    document.body.appendChild(overlay);

    // focus and cleanup helpers
    function cleanupAndResolve(value) {
      try {
        document.body.removeChild(overlay);
      } catch (e) { /* already removed */ }
      document.removeEventListener('keydown', onKey);
      resolve(value);
    }

    function onKey(e) {
      if (e.key === 'Escape') cleanupAndResolve(null);
    }

    document.addEventListener('keydown', onKey);
    // focus first radio for keyboard access
    const firstRadio = typeWrap.querySelector('input[name="puml_diagram_type"]');
    if (firstRadio) firstRadio.focus();
  });
}

// Listen to messages from popup
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.action === 'send_puml') {
    // simulate button click
    const el = document.getElementById('puml-send-btn');
    if (el) el.click();
    else injectButton();
    sendResponse({ ok: true });
  }
});

// Try to inject button on load and also periodically in case app modifies DOM
try {
  injectButton();
  const observer = new MutationObserver(() => injectButton());
  observer.observe(document.body, { childList: true, subtree: true });
} catch (e) {
  console.error('puml extension failed to inject button', e);
}
