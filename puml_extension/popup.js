document.addEventListener('DOMContentLoaded', () => {
  const serverUrl = document.getElementById('serverUrl');
  const token = document.getElementById('token');
  const method = document.getElementById('method');
  const save = document.getElementById('save');
  const send = document.getElementById('send');

  chrome.storage.local.get({ serverUrl: 'http://localhost:8000', token: '', method: 'python' }, (items) => {
    serverUrl.value = items.serverUrl || '';
    token.value = items.token || '';
    method.value = items.method || 'python';
  });

  save.addEventListener('click', () => {
    chrome.storage.local.set({ serverUrl: serverUrl.value.trim(), token: token.value.trim(), method: method.value }, () => {
      save.textContent = 'Saved';
      setTimeout(() => (save.textContent = 'Save'), 1200);
    });
  });

  send.addEventListener('click', async () => {
    // send message to active tab's content script
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) return;
    chrome.tabs.sendMessage(tab.id, { action: 'send_puml' }, (resp) => {
      // ignore
    });
  });
});
