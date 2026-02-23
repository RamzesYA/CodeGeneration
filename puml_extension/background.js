// Background service worker: performs network requests on behalf of content script

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || !msg.action) return;

  // Log-only flow: send PlantUML to /receive which prints it on the server console.
  if (msg.action === 'log_puml') {
    const { serverUrl, token, puml, diagramType, languages } = msg.payload;
    (async () => {
      try {
        const body = { puml };
        if (diagramType) body['diagramType'] = diagramType;
        if (languages) body['languages'] = languages;

        const resp = await fetch(serverUrl.replace(/\/$/, '') + '/receive', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + (token || '')
          },
          body: JSON.stringify(body)
        });
        const data = await resp.json().catch(() => null);
        sendResponse({ ok: true, status: resp.status, data });
      } catch (err) {
        sendResponse({ ok: false, error: err.message || String(err) });
      }
    })();
    return true;
  }

  // backward compatibility: handle other actions minimally
  if (msg.action === 'send_to_server') {
    const { serverUrl, token, puml, diagramType, languages } = msg.payload;
    (async () => {
      try {
        const body = {
          puml: puml,
          method: diagramType || 'auto',
          options: { languages: Array.isArray(languages) ? languages : [], diagram_type: diagramType },
          sync: true
        };
        const resp = await fetch(serverUrl.replace(/\/$/, '') + '/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + (token || '')
          },
          body: JSON.stringify(body)
        });
        const text = await resp.text();
        let data = null;
        try { data = JSON.parse(text); } catch (e) { data = text; }
        sendResponse({ ok: true, status: resp.status, data });
      } catch (err) {
        sendResponse({ ok: false, error: err.message || String(err) });
      }
    })();
    return true;
  }
});
