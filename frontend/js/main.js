/* SIA-RAG — main.js */
'use strict';

// Empty string = relative URLs, so it works from any host/port
const API_BASE = '';

// ── DOM References ──────────────────────────────────────────────
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');
const expandBtn = document.getElementById('expand-btn');

const newChatBtn = document.getElementById('new-chat-btn');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const browseBtn = document.getElementById('browse-btn');
const uploadStatus = document.getElementById('upload-status');

const docList = document.getElementById('doc-list');
const docEmpty = document.getElementById('doc-empty');
const clearDbBtn = document.getElementById('clear-db-btn');

const historyList = document.getElementById('history-list');
const clearHistoryBtn = document.getElementById('clear-history-btn');

const chatHistory = document.getElementById('chat-history');
const chatTitle = document.getElementById('chat-title');
const welcomeState = document.getElementById('welcome-state');
const modePills = document.querySelectorAll('.mode-pill');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const statusDot = document.querySelector('.status-dot');
const statusText = document.getElementById('status-text');

// ── State ───────────────────────────────────────────────────────
let currentMode = 'auto';
let chatSessions = JSON.parse(localStorage.getItem('sia_sessions') || '[]');
let currentSession = null;
let isLoading = false;

// ── Sidebar toggle ───────────────────────────────────────────────
function toggleSidebar(collapsed) {
    sidebar.classList.toggle('collapsed', collapsed);
    expandBtn.style.display = collapsed ? 'flex' : 'none';
}

sidebarToggle.addEventListener('click', () => toggleSidebar(true));
expandBtn.addEventListener('click', () => toggleSidebar(false));
expandBtn.style.display = 'none';

// ── Mode selector ────────────────────────────────────────────────
modePills.forEach(pill => {
    pill.addEventListener('click', () => {
        modePills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        currentMode = pill.dataset.mode;
    });
});

// ── Auto-resize textarea ──────────────────────────────────────────
userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 160) + 'px';
    sendBtn.classList.toggle('ready', userInput.value.trim().length > 0);
});

// ── Suggestion chips ──────────────────────────────────────────────
document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
        userInput.value = chip.dataset.query;
        userInput.dispatchEvent(new Event('input'));
        userInput.focus();
    });
});

// ── New chat ──────────────────────────────────────────────────────
newChatBtn.addEventListener('click', startNewChat);

function startNewChat() {
    currentSession = null;
    chatTitle.textContent = 'SIA-RAG Assistant';
    chatHistory.innerHTML = '';
    chatHistory.appendChild(welcomeState);
    welcomeState.style.display = 'flex';
    userInput.value = '';
    userInput.style.height = 'auto';
    sendBtn.classList.remove('ready');
}

// ── Session history ───────────────────────────────────────────────
function saveSessions() {
    localStorage.setItem('sia_sessions', JSON.stringify(chatSessions.slice(0, 30)));
}

function renderHistory() {
    historyList.innerHTML = '';
    [...chatSessions].reverse().forEach((s, i) => {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.innerHTML = `
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <span>${escapeHtml(s.title)}</span>`;
        item.title = s.title;
        item.addEventListener('click', () => loadSession(chatSessions.length - 1 - i));
        historyList.appendChild(item);
    });
}

function loadSession(index) {
    const s = chatSessions[index];
    if (!s) return;
    currentSession = index;
    chatTitle.textContent = s.title;
    chatHistory.innerHTML = '';
    s.messages.forEach(m => appendBubble(m.role, m.text, false));
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

clearHistoryBtn.addEventListener('click', () => {
    chatSessions = [];
    saveSessions();
    renderHistory();
    startNewChat();
});

// ── Document list ─────────────────────────────────────────────────
async function loadDocuments() {
    try {
        const res = await fetch(`${API_BASE}/documents/`);
        if (!res.ok) return;
        const data = await res.json();
        renderDocList(data.documents || []);
    } catch {
        // backend offline — silently skip
    }
}

function renderDocList(docs) {
    docList.querySelectorAll('.doc-item').forEach(el => el.remove());

    if (!docs || docs.length === 0) {
        docEmpty.style.display = 'block';
        return;
    }
    docEmpty.style.display = 'none';

    docs.forEach(doc => {
        const row = document.createElement('div');
        row.className = 'doc-item';
        row.dataset.docId = doc.doc_id;
        const label = doc.source || doc.doc_id;

        row.innerHTML = `
            <svg class="doc-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
            </svg>
            <span class="doc-name" title="${escapeHtml(label)}">${escapeHtml(label)}</span>
            <span class="doc-badge">${doc.chunk_count}</span>
            <button class="doc-del-btn" title="Remove this document">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                    <path d="M10 11v6"/><path d="M14 11v6"/>
                </svg>
            </button>`;

        row.querySelector('.doc-del-btn').addEventListener('click', async e => {
            e.stopPropagation();
            await deleteDocument(doc.doc_id, label, row);
        });

        docList.appendChild(row);
    });
}

async function deleteDocument(docId, label, rowEl) {
    if (!confirm(`Remove "${label}" from the database?`)) return;
    try {
        rowEl.style.opacity = '0.4';
        const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(docId)}`, { method: 'DELETE' });
        if (res.ok) {
            rowEl.remove();
            if (docList.querySelectorAll('.doc-item').length === 0) {
                docEmpty.style.display = 'block';
            }
            appendSystemMsg(`"${label}" removed from the database.`);
        } else {
            rowEl.style.opacity = '1';
            alert('Failed to remove document.');
        }
    } catch {
        rowEl.style.opacity = '1';
        alert('Could not reach server.');
    }
}

clearDbBtn.addEventListener('click', async () => {
    if (!confirm('Clear the ENTIRE database? This will remove all indexed PDFs.')) return;
    try {
        clearDbBtn.style.opacity = '0.4';
        const res = await fetch(`${API_BASE}/documents/`, { method: 'DELETE' });
        if (res.ok) {
            renderDocList([]);
            appendSystemMsg('Database cleared. All documents removed.');
        } else {
            alert('Failed to clear database.');
        }
    } catch {
        alert('Could not reach server.');
    } finally {
        clearDbBtn.style.opacity = '1';
    }
});

// ── Upload ────────────────────────────────────────────────────────
browseBtn.addEventListener('click', e => { e.stopPropagation(); fileInput.click(); });
dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', e => {
    if (e.target.files.length > 0) handleUploadMultiple(Array.from(e.target.files));
    fileInput.value = '';   // reset so the same file(s) can be re-selected
});

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const files = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.pdf'));
    if (files.length > 0) handleUploadMultiple(files);
});

async function handleUploadMultiple(files) {
    if (files.length === 1) {
        // Single file — original simple path
        await handleUpload(files[0]);
        return;
    }

    let succeeded = 0;
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (!file.name.endsWith('.pdf')) continue;
        setUploadStatus(`Uploading ${i + 1} / ${files.length}: ${file.name}`, 'loading');
        const fd = new FormData();
        fd.append('file', file);
        try {
            const res = await fetch(`${API_BASE}/upload/`, { method: 'POST', body: fd });
            const data = await res.json();
            if (res.ok) {
                succeeded++;
                appendSystemMsg(`"${data.filename}" indexed and ready.`);
            } else {
                appendSystemMsg(`⚠ Failed: ${file.name} — ${data.detail || 'error'}`);
            }
        } catch {
            appendSystemMsg(`⚠ Could not reach server for: ${file.name}`);
        }
    }

    setUploadStatus(`✓ ${succeeded} of ${files.length} PDFs indexed`, succeeded > 0 ? 'success' : 'error');
    await loadDocuments();
}

async function handleUpload(file) {
    if (!file.name.endsWith('.pdf')) {
        setUploadStatus('Only PDFs are supported', 'error');
        return;
    }
    setUploadStatus('Uploading…', 'loading');

    const fd = new FormData();
    fd.append('file', file);
    try {
        const res = await fetch(`${API_BASE}/upload/`, { method: 'POST', body: fd });
        const data = await res.json();
        if (res.ok) {
            setUploadStatus(`✓ ${data.filename}`, 'success');
            appendSystemMsg(`"${data.filename}" indexed and ready.`);
            await loadDocuments();   // refresh document list
        } else {
            setUploadStatus(`Error: ${data.detail || 'failed'}`, 'error');
        }
    } catch {
        setUploadStatus('Cannot reach server', 'error');
    }
}

function setUploadStatus(msg, type) {
    uploadStatus.textContent = msg;
    uploadStatus.className = `upload-status ${type}`;
}

// ── Chat ──────────────────────────────────────────────────────────
sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

async function sendMessage() {
    const query = userInput.value.trim();
    if (!query || isLoading) return;
    isLoading = true;

    if (welcomeState.parentNode === chatHistory) {
        welcomeState.style.display = 'none';
        chatHistory.removeChild(welcomeState);
    }

    if (currentSession === null) {
        const title = query.length > 40 ? query.slice(0, 40) + '…' : query;
        chatSessions.push({ title, messages: [] });
        currentSession = chatSessions.length - 1;
        chatTitle.textContent = title;
        renderHistory();
    }

    appendBubble('user', query, true);
    chatSessions[currentSession].messages.push({ role: 'user', text: query });
    saveSessions();

    userInput.value = '';
    userInput.style.height = 'auto';
    sendBtn.classList.remove('ready');

    const typingRow = appendTyping();
    scrollBottom();

    try {
        const res = await fetch(`${API_BASE}/chat/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, search_mode: currentMode })
        });
        const data = await res.json();
        typingRow.remove();

        const answer = res.ok ? data.answer : `Error: ${data.detail || 'Something went wrong'}`;
        const bubble = appendBubble('ai', answer, true);
        if (!res.ok) bubble.classList.add('error');

        chatSessions[currentSession].messages.push({ role: 'ai', text: answer });
        saveSessions();
    } catch {
        typingRow.remove();
        appendBubble('ai', 'Error: Could not connect to the backend.', true).classList.add('error');
    } finally {
        isLoading = false;
        scrollBottom();
    }
}

// ── UI helpers ────────────────────────────────────────────────────
function appendBubble(role, text, animate) {
    const row = document.createElement('div');
    row.className = `msg-row ${role}`;
    if (!animate) row.style.animation = 'none';

    if (role === 'ai') {
        row.innerHTML = `
            <div class="ai-avatar">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                    <path d="M2 17l10 5 10-5"/>
                    <path d="M2 12l10 5 10-5"/>
                </svg>
            </div>
            <div class="msg-bubble"></div>`;
        row.querySelector('.msg-bubble').textContent = text;
    } else {
        row.innerHTML = `<div class="msg-bubble">${escapeHtml(text)}</div>`;
    }

    chatHistory.appendChild(row);
    return row.querySelector('.msg-bubble');
}

function appendSystemMsg(text) {
    const row = document.createElement('div');
    row.className = 'msg-row system';
    row.innerHTML = `<div class="msg-bubble">${escapeHtml(text)}</div>`;
    chatHistory.appendChild(row);
    scrollBottom();
}

function appendTyping() {
    const row = document.createElement('div');
    row.className = 'msg-row ai';
    row.innerHTML = `
        <div class="ai-avatar">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/>
                <path d="M2 12l10 5 10-5"/>
            </svg>
        </div>
        <div class="msg-bubble">
            <div class="typing-dots"><span></span><span></span><span></span></div>
        </div>`;
    chatHistory.appendChild(row);
    return row;
}

function scrollBottom() {
    chatHistory.scrollTo({ top: chatHistory.scrollHeight, behavior: 'smooth' });
}

function escapeHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ── Backend health check ──────────────────────────────────────────
async function checkBackend() {
    try {
        const res = await fetch(`${API_BASE}/`, { signal: AbortSignal.timeout(4000) });
        if (res.ok) {
            statusDot.style.background = '#6ee7b7';
            statusDot.style.boxShadow = '0 0 6px #6ee7b760';
            statusText.textContent = 'Online';
        } else { throw new Error(); }
    } catch {
        statusDot.style.background = '#fca5a5';
        statusDot.style.boxShadow = '0 0 6px #fca5a560';
        statusText.textContent = 'Offline';
    }
}

// ── Init ──────────────────────────────────────────────────────────
renderHistory();
checkBackend();
loadDocuments();
