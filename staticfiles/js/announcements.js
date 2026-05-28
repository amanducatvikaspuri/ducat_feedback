// Handle Announcement Modal Logic for Bulk WhatsApp
function openAnnouncementModal() {
    const modal = document.getElementById('announcementModal');
    const batchListBody = document.getElementById('batchCheckboxList');
    
    batchListBody.innerHTML = '';
    
    // Extract unique batches from trainersData
    const allBatches = [];
    trainersData.forEach(trainer => {
        trainer.batches.forEach(batch => {
            // Check if batch already exists in list (by name and type)
            const exists = allBatches.some(b => b.name === batch.batch_name && b.type === batch.type);
            if (!exists) {
                allBatches.push({ 
                    id: batch.id || (Math.random() * 1000000).toFixed(0), // Fallback if no ID
                    name: batch.batch_name, 
                    type: batch.type,
                    trainer: trainer.name
                });
            }
        });
    });

    if (allBatches.length === 0) {
        batchListBody.innerHTML = '<p style="color:var(--text-muted); font-size:0.8rem; grid-column:span 2;">No batches found.</p>';
    }

    allBatches.forEach(batch => {
        const item = document.createElement('div');
        item.style.display = 'flex';
        item.style.alignItems = 'center';
        item.style.justifyContent = 'space-between';
        item.style.gap = '10px';
        item.style.padding = '8px 12px';
        item.style.background = 'rgba(255,255,255,0.02)';
        item.style.borderRadius = '10px';
        item.style.border = '1px solid rgba(255,255,255,0.03)';
        
        item.innerHTML = `
            <div style="display:flex; align-items:center; gap:10px; flex:1;">
                <input type="checkbox" class="batch-checkbox" 
                    value="${batch.id}" 
                    id="batch_${batch.id}" 
                    data-name="${batch.name}" 
                    data-trainer="${batch.trainer}"
                    style="width:18px; height:18px; accent-color:var(--primary);">
                <label for="batch_${batch.id}" style="font-size:0.75rem; cursor:pointer; flex: 1;">
                    <span style="font-weight:800; color:var(--text-light);">${batch.name}</span>
                    <span style="display:block; font-size:0.6rem; color:var(--text-muted);">${batch.type} | ${batch.trainer}</span>
                </label>
            </div>
            <button onclick="batchIndividualAnnounce('${batch.id}', '${batch.name}', '${batch.trainer}')" 
                style="background:rgba(37, 211, 102, 0.1); color:#25d366; border:1px solid rgba(37, 211, 102, 0.2); width:30px; height:30px; border-radius:8px; cursor:pointer; flex-shrink:0; transition:0.3s;" 
                title="Send Personal (Individual) to this batch">
                <i class="fa-brands fa-whatsapp"></i>
            </button>
        `;
        batchListBody.appendChild(item);
    });

    modal.style.display = 'flex';
    modal.classList.add('active');
}

function closeAnnouncementModal() {
    const modal = document.getElementById('announcementModal');
    modal.style.display = 'none';
    modal.classList.remove('active');
    
    // Reset status
    document.getElementById('sendingStatus').style.display = 'none';
    document.getElementById('broadcastBtn').disabled = false;
    document.getElementById('broadcastBtn').innerHTML = '<i class="fa-solid fa-paper-plane"></i> SEND BROADCAST';
}

function insertTag(tag) {
    const textarea = document.getElementById('whatsappMsgBody');
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    textarea.value = text.substring(0, start) + tag + text.substring(end);
    textarea.focus();
    textarea.setSelectionRange(start + tag.length, start + tag.length);
}

function toggleSelectAllBatches() {
    const checkboxes = document.querySelectorAll('.batch-checkbox');
    if (checkboxes.length === 0) return;
    
    // Check if everything is currently checked
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    
    // Toggle all
    checkboxes.forEach(cb => cb.checked = !allChecked);
}

async function broadcastWhatsApp() {
    const selectedCheckboxes = document.querySelectorAll('.batch-checkbox:checked');
    const batchIds = Array.from(selectedCheckboxes).map(cb => cb.value);
    const message = document.getElementById('whatsappMsgBody').value.trim();
    const btn = document.getElementById('broadcastBtn');
    const statusDiv = document.getElementById('sendingStatus');
    const statusText = document.getElementById('statusText');
    const progress = document.getElementById('statusProgress');

    if (batchIds.length === 0) {
        alert("Please select at least one batch!");
        return;
    }
    if (!message) {
        alert("Please enter a message!");
        return;
    }

    if (!confirm(`Are you sure you want to send this broadcast to ${batchIds.length} batches?`)) {
        return;
    }

    // Start UI sending state
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> PREPARING...';
    statusDiv.style.display = 'block';
    progress.style.width = '10%';
    statusText.innerText = 'Initializing WATI Gateway...';

    try {
        const response = await fetch('/api/send-bulk-whatsapp/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRF()
            },
            body: JSON.stringify({
                batch_ids: batchIds,
                message: message
            })
        });

        const data = await response.json();

        if (data.status === 'success') {
            progress.style.width = '100%';
            statusText.style.color = '#10b981';
            statusText.innerHTML = `SUCCESS! Sent: ${data.summary.sent} | Failed: ${data.summary.failed}`;
            
            if (data.summary.failed > 0) {
                console.error("WhatsApp Send Errors:", data.summary.errors);
                alert(`Broadcast complete with some errors. Sent: ${data.summary.sent}, Failed: ${data.summary.failed}. Check console for details.`);
            } else {
                alert(`Broadcast Successful! Sent to ${data.summary.sent} students.`);
            }
        } else {
            throw new Error(data.message || 'Unknown error occurred');
        }
    } catch (err) {
        statusText.style.color = '#ef4444';
        statusText.innerText = 'ERROR: ' + err.message;
        alert("Failed to send broadcast: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> LAUNCH ANNOUNCEMENT';
    }
}

async function broadcastPersonalWhatsApp() {
    const selectedCheckboxes = document.querySelectorAll('.batch-checkbox:checked');
    const batchIds = Array.from(selectedCheckboxes).map(cb => cb.value);
    const message = document.getElementById('whatsappMsgBody').value.trim();

    if (batchIds.length === 0) {
        alert("Please select batches first.");
        return;
    }
    
    // User might select multiple batches
    const firstCb = selectedCheckboxes[0];
    const batchName = firstCb.dataset.name + (batchIds.length > 1 ? ` & ${batchIds.length - 1} more` : '');
    const trainerName = firstCb.dataset.trainer;

    // Use existing individual sender logic
    // We modify the backend to handle multiple batch_ids if we want, 
    // or just loop here. Actually, looping here is slower but gives more browser control.
    // Let's modify the backend call to take an ARRAY of batch_ids.
    
    const msg = message || prompt(`Enter personal message for students:`, `Dear {name}, this is a personal message regarding your batch {batch}.`);
    if (!msg) return;

    if (!confirm(`This will open individual WhatsApp tabs for EVERY student in the ${batchIds.length} selected batches. Proceed?`)) {
        return;
    }

    try {
        const response = await fetch('/api/send-batch-individual-whatsapp/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRF()
            },
            body: JSON.stringify({ 
                batch_id: batchIds.join(','), // Support comma-separated for multi-batch
                message: msg 
            })
        });

        const data = await response.json();
        if (data.status === 'success') {
            alert(data.message);
        } else {
            alert("Automation Error: " + data.message);
        }
    } catch (err) {
        alert("Server communication failed.");
    }
}

function triggerBatchPersonalFromModal() {
    if (typeof currentTrainerIndex === 'undefined' || currentTrainerIndex === null) {
        alert("Could not identify current batch.");
        return;
    }
    const trainer = trainersData[currentTrainerIndex];
    const batch = trainer.batches.find(b => b.type === currentBatchType);
    if (!batch) {
        alert("Batch data not found.");
        return;
    }
    
    batchIndividualAnnounce(batch.id || '', batch.batch_name, trainer.name);
}

// Utility to get CSRF token
function getCSRF() {
    // Try cookie first, then hidden input
    let cookieVal = getCookie('csrftoken');
    if (!cookieVal) {
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        if (input) cookieVal = input.value;
    }
    return cookieVal;
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function quickAnnounce(batchId, batchName, trainerName) {
    openAnnouncementModal();
    
    // Wait for checkboxes to render
    setTimeout(() => {
        // Uncheck all
        document.querySelectorAll('.batch-checkbox').forEach(cb => cb.checked = false);
        
        // Find and check
        const cb = document.getElementById(`batch_${batchId}`);
        if (cb) {
            cb.checked = true;
            cb.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        
        const textarea = document.getElementById('whatsappMsgBody');
        if (!textarea.value.trim()) {
            textarea.value = `Dear {name}, this is an announcement for batch {batch}. `;
        }
    }, 150);
}

async function batchIndividualAnnounce(batchId, batchName, trainerName) {
    const msg = prompt(`Enter message for ALL students in ${batchName}:`, `Dear {name}, this is a personal announcement for your batch {batch}.`);
    if (!msg) return;

    if (!confirm(`WARNING: This will open individual WhatsApp windows for EVERY student in this batch. \n\nBatch: ${batchName}\nTrainer: ${trainerName}\n\nProceed?`)) {
        return;
    }

    try {
        const response = await fetch('/api/send-batch-individual-whatsapp/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRF()
            },
            body: JSON.stringify({ batch_id: batchId, message: msg })
        });

        if (!response.ok) {
            const body = await response.text();
            console.error("Batch Personal API Error:", body);
            throw new Error(`HTTP Error: ${response.status}`);
        }
        const data = await response.json();
        if (data.status === 'success') {
            alert(data.message);
        } else {
            alert("Send Error: " + data.message);
        }
    } catch (err) {
        console.error("Batch Personal Debug:", err);
        alert("Batch Communication Failed: " + err.message);
    }
}

let isHistoryVisible = false;
async function toggleAnnouncementHistory() {
    const mainGrid = document.querySelector('#announcementModal .modal-body > div:first-child');
    const historySection = document.getElementById('announcementHistorySection');
    const toggleBtn = document.getElementById('historyToggleBtn');

    if (!isHistoryVisible) {
        // Show History
        mainGrid.style.display = 'none';
        historySection.style.display = 'flex';
        toggleBtn.innerHTML = '<i class="fa-solid fa-arrow-left"></i> BACK TO COMPOSER';
        toggleBtn.style.color = 'var(--primary)';
        loadAnnouncementLogs();
    } else {
        // Show Composer
        mainGrid.style.display = 'grid';
        historySection.style.display = 'none';
        toggleBtn.innerHTML = '<i class="fa-solid fa-clock-rotate-left"></i> VIEW HISTORY';
        toggleBtn.style.color = 'var(--text-muted)';
    }
    isHistoryVisible = !isHistoryVisible;
}

async function loadAnnouncementLogs() {
    const tbody = document.getElementById('announcementLogsBody');
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px; color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Loading logs...</td></tr>';

    try {
        const response = await fetch('/api/announcement-logs/');
        const data = await response.json();

        if (data.status === 'success' && data.logs.length > 0) {
            tbody.innerHTML = '';
            data.logs.forEach(log => {
                const statusColor = log.status === 'Sent' ? '#10b981' : '#ef4444';
                const row = document.createElement('tr');
                row.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
                row.innerHTML = `
                    <td style="padding:12px 10px; color:var(--text-muted);">${log.time}</td>
                    <td style="padding:12px 10px; font-weight:700;">${log.student}</td>
                    <td style="padding:12px 10px;"><span style="color:#818cf8;">${log.batch}</span></td>
                    <td style="padding:12px 10px;"><span style="color:${statusColor}; font-weight:800; font-size:0.6rem; text-transform:uppercase;">${log.status}</span></td>
                `;
                tbody.appendChild(row);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px; color:var(--text-muted);">No history records found.</td></tr>';
        }
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px; color:#ef4444;">Failed to load history.</td></tr>';
    }
}

// Reset when modal closes
const originalCloseModal = closeAnnouncementModal;
closeAnnouncementModal = function() {
    originalCloseModal();
    const mainGrid = document.querySelector('#announcementModal .modal-body > div:first-child');
    const historySection = document.getElementById('announcementHistorySection');
    const toggleBtn = document.getElementById('historyToggleBtn');
    
    if (isHistoryVisible) {
        mainGrid.style.display = 'grid';
        historySection.style.display = 'none';
        toggleBtn.innerHTML = '<i class="fa-solid fa-clock-rotate-left"></i> VIEW HISTORY';
        toggleBtn.style.color = 'var(--text-muted)';
        isHistoryVisible = false;
    }
};

async function handleStudentImport(input) {
    if (!input.files || !input.files[0]) return;
    
    const file = input.files[0];
    const formData = new FormData();
    formData.append('csv_file', file);
    
    // CSRF Token workaround for Django AJAX
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : '';

    try {
        const response = await fetch('/api/import-students/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': csrftoken
            }
        });
        const data = await response.json();
        if (data.status === 'success') {
            alert(data.message);
            location.reload(); // Refresh to show linked counts
        } else {
            alert('Import Error: ' + data.message);
        }
    } catch (err) {
        alert('Failed to connect to import API.');
    }
    input.value = ''; // Reset input
}

// Student Roster Logic
function openStudentRoster() {
    const modal = document.getElementById('rosterModal');
    modal.style.display = 'flex';
    
    // Auto-sync with main dashboard course filter
    const globalCourse = document.getElementById('technologyFilter').value;
    const rosterFilter = document.getElementById('rosterCourseFilter');
    
    if (globalCourse && rosterFilter) {
        rosterFilter.value = globalCourse;
    }
    
    filterRoster(); // Initial load
}

function closeRosterModal() {
    document.getElementById('rosterModal').style.display = 'none';
}

function filterRoster() {
    const courseFilter = document.getElementById('rosterCourseFilter').value;
    const searchVal = document.getElementById('rosterSearch').value.toLowerCase();
    const students = JSON.parse(document.getElementById('all-students-data').textContent);
    const tbody = document.getElementById('rosterTableBody');
    
    tbody.innerHTML = '';
    
    const filtered = students.filter(s => {
        const matchesCourse = courseFilter === '' || s.technology === courseFilter;
        const matchesSearch = s.name.toLowerCase().includes(searchVal) || s.sid.toLowerCase().includes(searchVal);
        return matchesCourse && matchesSearch;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:40px; color:var(--text-muted);">No students found matching your filters.</td></tr>';
        return;
    }

    filtered.forEach(s => {
        const row = document.createElement('tr');
        row.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
        row.innerHTML = `
            <td style="padding:15px 20px; font-weight:800; color:var(--primary); cursor:pointer; text-decoration:underline;" onclick="openStudentProfile('${s.sid}', '${s.name.replace(/'/g, "\\'")}')" title="View Full Profile">${s.sid}</td>
            <td style="padding:15px 20px; font-weight:700; color:white; cursor:pointer;" onclick="openStudentProfile('${s.sid}', '${s.name.replace(/'/g, "\\'")}')">
                <span style="border-bottom: 1px dashed rgba(255,255,255,0.4); padding-bottom: 2px;">${s.name}</span>
            </td>
            <td style="padding:15px 20px; font-size:0.8rem; color:white;">${s.phone}</td>
            <td style="padding:15px 20px; font-size:0.75rem; color:#a5b4fc;">${s.email}</td>
            <td style="padding:15px 20px;"><span style="background:rgba(99, 102, 241, 0.1); color:#818cf8; padding:4px 10px; border-radius:30px; font-size:0.7rem; font-weight:800;">${s.technology}</span></td>
            <td style="padding:15px 20px;">
                <button onclick="sendSingleWhatsApp('${s.phone}', '${s.name}')" 
                    style="background:#25d366; color:white; border:none; padding:6px 12px; border-radius:6px; cursor:pointer; font-size:0.7rem; font-weight:800; display:flex; align-items:center; gap:5px;">
                    <i class="fa-brands fa-whatsapp"></i> SEND
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

async function sendSingleWhatsApp(phone, name) {
    const msg = prompt(`Enter message for ${name}:`, `Dear ${name}, this is an announcement from Ducat Vikaspuri.`);
    if (!msg) return;

    // Show loading state (you could make this fancier)
    const originalBtn = event.currentTarget;
    const originalContent = originalBtn.innerHTML;
    originalBtn.disabled = true;
    originalBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

    try {
        const response = await fetch('/api/send-single-whatsapp/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRF()
            },
            body: JSON.stringify({ phone, message: msg })
        });

        if (!response.ok) {
            const body = await response.text();
            console.error("API Error Response:", body);
            throw new Error(`HTTP Error: ${response.status}`);
        }
        const data = await response.json();
        if (data.status === 'success') {
            alert(data.message);
        } else {
            alert("Automation Error: " + data.message);
        }
    } catch (err) {
        console.error("Connection Debug:", err);
        alert("Automation Failed: " + err.message);
    } finally {
        originalBtn.disabled = false;
        originalBtn.innerHTML = originalContent;
    }
}

// Registration QR Logic
function toggleRegistrationQR() {
    const modal = document.getElementById('regQRModal');
    if (modal.style.display === 'flex') {
        modal.style.display = 'none';
    } else {
        const baseUrl = window.location.origin;
        const regUrl = baseUrl + '/form/register/';
        // Switching to api.qrserver.com for better reliability
        const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(regUrl)}`;
        
        document.getElementById('regQRCodeImg').src = qrUrl;
        document.getElementById('regURLText').textContent = regUrl;
        modal.style.display = 'flex';
    }
}
