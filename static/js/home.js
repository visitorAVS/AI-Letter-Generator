let currentLetter = null;
let currentLetterId = null;

window.addEventListener('load', () => {
    loadUserInfo();
    loadLetters();
});

function loadUserInfo() {
    fetch('/api/check-auth', {
        credentials: 'include'
    })
        .then(r => r.json())
        .then(data => {
            if (data.authenticated) {
                document.getElementById('userName').textContent = data.name;
                document.getElementById('userAvatar').textContent = data.name.charAt(0).toUpperCase();
            } else {
                window.location.href = '/login';
            }
        })
        .catch(err => {
            console.error('Auth check failed:', err);
            window.location.href = '/login';
        });
}

function toggleCustom() {
    const type = document.getElementById('letterType').value;
    document.getElementById('customGroup').style.display = type === 'custom' ? 'block' : 'none';
}

async function generateLetter(event) {
    if (event) event.preventDefault();

    let letterType = document.getElementById('letterType').value;
    if (!letterType) { showMessage('formMessage', '❌ Please select a letter type', 'error'); return; }

    if (letterType === 'custom') {
        letterType = document.getElementById('customType').value;
        if (!letterType) { showMessage('formMessage', '❌ Please enter a custom letter type', 'error'); return; }
    }

    if (!document.getElementById('senderName').value) { showMessage('formMessage', '❌ Please enter your name', 'error'); return; }
    if (!document.getElementById('receiverName').value) { showMessage('formMessage', '❌ Please enter recipient name', 'error'); return; }
    if (!document.getElementById('receiverDesignation').value) { showMessage('formMessage', '❌ Please enter recipient designation', 'error'); return; }
    if (!document.getElementById('subject').value) { showMessage('formMessage', '❌ Please enter subject', 'error'); return; }

    document.getElementById('loading').style.display = 'block';
    document.getElementById('letterPreview').classList.remove('active');
    document.getElementById('emptyPreview').style.display = 'none';
    document.getElementById('actionButtons').style.display = 'none';

    try {
        const response = await fetch('/generate', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                letterType: letterType,
                language: document.getElementById('language').value,
                senderName: document.getElementById('senderName').value,
                receiverName: document.getElementById('receiverName').value,
                receiverDesignation: document.getElementById('receiverDesignation').value,
                organization: document.getElementById('organization').value || '',
                subject: document.getElementById('subject').value,
                reason: document.getElementById('reason').value || '',
                tone: document.getElementById('tone').value
            })
        });

        const data = await response.json();

        if (data.success) {
            currentLetter = data.letter;
            currentLetterId = data.letterId;
            document.getElementById('letterPreview').textContent = currentLetter;
            document.getElementById('letterPreview').classList.add('active');
            document.getElementById('actionButtons').style.display = 'flex';
            document.getElementById('emptyPreview').style.display = 'none';
            showMessage('formMessage', '✅ Letter generated successfully!', 'success');
            loadLetters();
        } else {
            showMessage('formMessage', '❌ ' + (data.error || 'Failed to generate letter'), 'error');
            document.getElementById('emptyPreview').style.display = 'block';
        }
    } catch (error) {
        console.error('Generate error:', error);
        showMessage('formMessage', '❌ Error: ' + error.message, 'error');
        document.getElementById('emptyPreview').style.display = 'block';
    } finally {
        document.getElementById('loading').style.display = 'none';
    }
}

function copyLetter() {
    if (!currentLetter) { showMessage('formMessage', '❌ No letter to copy', 'error'); return; }
    navigator.clipboard.writeText(currentLetter)
        .then(() => showMessage('formMessage', '✅ Copied to clipboard!', 'success'))
        .catch(() => showMessage('formMessage', '❌ Copy failed', 'error'));
}

function downloadTXT() {
    if (!currentLetter) { showMessage('formMessage', '❌ No letter to download', 'error'); return; }
    const el = document.createElement('a');
    el.href = 'data:text/plain;charset=utf-8,' + encodeURIComponent(currentLetter);
    el.download = 'letter_' + Date.now() + '.txt';
    document.body.appendChild(el);
    el.click();
    document.body.removeChild(el);
    showMessage('formMessage', '✅ Downloaded as TXT!', 'success');
}

function downloadPDF() {
    if (!currentLetterId) { showMessage('formMessage', '❌ Generate a letter first', 'error'); return; }
    showMessage('formMessage', '⏳ Generating PDF...', 'success');

    fetch(`/download-pdf/${currentLetterId}`, {
        credentials: 'include'
    })
        .then(response => {
            const contentType = response.headers.get('content-type') || '';
            if (!response.ok || !contentType.includes('application/pdf')) {
                return response.json().then(errData => {
                    throw new Error(errData.error || 'PDF generation failed');
                }).catch(() => {
                    throw new Error(`Server error: ${response.status}`);
                });
            }
            return response.blob();
        })
        .then(blob => {
            if (blob.size === 0) throw new Error('PDF file is empty');
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `letter_${Date.now()}.pdf`;
            document.body.appendChild(a);
            a.click();
            URL.revokeObjectURL(url);
            document.body.removeChild(a);
            showMessage('formMessage', '✅ PDF Downloaded successfully!', 'success');
        })
        .catch(e => showMessage('formMessage', '❌ PDF Error: ' + e.message, 'error'));
}

function printLetter() {
    if (!currentLetter) { showMessage('formMessage', '❌ No letter to print', 'error'); return; }
    const w = window.open('', '', 'height=600,width=800');
    w.document.write('<html><head><title>Letter</title><style>body{font-family:Georgia,serif;line-height:1.8;margin:40px;color:#1e3a8a;}pre{white-space:pre-wrap;word-wrap:break-word;}</style></head><body>');
    w.document.write('<pre>' + currentLetter + '</pre>');
    w.document.write('</body></html>');
    w.document.close();
    w.print();
}

async function loadLetters() {
    try {
        const response = await fetch('/history', {
            credentials: 'include'
        });
        const letters = await response.json();
        const tbody = document.getElementById('lettersBody');

        if (!Array.isArray(letters) || letters.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:30px;color:#999;">No letters yet. Generate your first letter!</td></tr>';
            return;
        }

        tbody.innerHTML = letters.map(letter => `
            <tr>
                <td><span class="letter-badge">${escapeHtml(letter.letterType || '')}</span></td>
                <td>${escapeHtml(letter.subject || '')}</td>
                <td>${formatDate(letter.created_at)}</td>
                <td>
                    <button class="action-btn btn-view" onclick="viewLetter('${letter.id}')">👁 View</button>
                    <button class="action-btn btn-delete" onclick="deleteLetter('${letter.id}')">🗑 Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading letters:', error);
    }
}

function viewLetter(id) {
    fetch(`/history/${id}`, {
        credentials: 'include'
    })
        .then(r => r.json())
        .then(letter => {
            if (letter.error) { showMessage('formMessage', '❌ Letter not found', 'error'); return; }
            currentLetter = letter.content;
            currentLetterId = letter.id;
            document.getElementById('letterPreview').textContent = currentLetter;
            document.getElementById('letterPreview').classList.add('active');
            document.getElementById('emptyPreview').style.display = 'none';
            document.getElementById('actionButtons').style.display = 'flex';
            window.scrollTo({ top: 0, behavior: 'smooth' });
        })
        .catch(e => showMessage('formMessage', '❌ Error: ' + e.message, 'error'));
}

function deleteLetter(id) {
    if (!confirm('Are you sure you want to delete this letter?')) return;

    fetch(`/delete/${id}`, {
        method: 'DELETE',
        credentials: 'include'
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showMessage('formMessage', '✅ Letter deleted!', 'success');
                if (currentLetterId === id) {
                    currentLetter = null;
                    currentLetterId = null;
                    document.getElementById('letterPreview').classList.remove('active');
                    document.getElementById('emptyPreview').style.display = 'block';
                    document.getElementById('actionButtons').style.display = 'none';
                }
                loadLetters();
            } else {
                showMessage('formMessage', '❌ Failed to delete letter', 'error');
            }
        })
        .catch(e => showMessage('formMessage', '❌ Error: ' + e.message, 'error'));
}

function logout() {
    if (!confirm('Are you sure you want to logout?')) return;
    fetch('/auth/logout', {
        method: 'POST',
        credentials: 'include'
    })
        .then(() => window.location.href = '/login')
        .catch(() => window.location.href = '/login');
}

function showMessage(elementId, message, type) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.innerHTML = `<div class="message ${type}">${message}</div>`;
    setTimeout(() => { el.innerHTML = ''; }, 5000);
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        return new Date(dateString).toLocaleDateString('en-IN', {
            year: 'numeric', month: 'short', day: 'numeric'
        });
    } catch { return dateString; }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}