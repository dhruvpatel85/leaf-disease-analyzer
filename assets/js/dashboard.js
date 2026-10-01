// ============================================
// Leaf Analyzer - Dashboard JavaScript
// ============================================

document.addEventListener('DOMContentLoaded', function() {

    // ── Element references ────────────────────────────────────────────────
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const previewImage = document.getElementById('previewImage');
    const uploadPlaceholder = document.getElementById('uploadPlaceholder');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resultSection = document.getElementById('resultSection');
    const resultCard = document.getElementById('resultCard');
    const loading = document.getElementById('loading');
    const resetBtn = document.getElementById('resetBtn');
    const jsErrorBox = document.getElementById('jsErrorBox');

    // Guard: abort silently if we're not on the dashboard page
    if (!uploadArea || !fileInput || !analyzeBtn) return;

    let selectedFile = null;
    let historyRowCount = window.LEAF_HISTORY_COUNT || 0;

    // ── Click upload area to open file picker ─────────────────────────────
    uploadArea.addEventListener('click', function(e) {
        if (e.target === previewImage) return; // don't re-trigger on image click
        fileInput.click();
    });

    // ── File selected via picker ──────────────────────────────────────────
    fileInput.addEventListener('change', function() {
        if (this.files[0]) handleFile(this.files[0]);
    });

    // ── Drag & Drop ───────────────────────────────────────────────────────
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });

    ['dragleave', 'dragend'].forEach(function(evt) {
        uploadArea.addEventListener(evt, function() {
            uploadArea.classList.remove('drag-over');
        });
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
    });

    // ── Handle file selection ─────────────────────────────────────────────
    function handleFile(file) {
        const validTypes = ['image/jpeg', 'image/png', 'image/jpg'];

        if (!validTypes.includes(file.type)) {
            showError('Please upload a JPG or PNG image.');
            return;
        }
        if (file.size > 5 * 1024 * 1024) {
            showError('File size must be under 5 MB.');
            return;
        }

        clearError();
        selectedFile = file;

        // Show image preview
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImage.src = e.target.result;
            previewImage.classList.remove('hidden');
            uploadPlaceholder.classList.add('hidden');
        };
        reader.readAsDataURL(file);

        analyzeBtn.disabled = false;
        resultSection.classList.add('hidden');
    }

    // ── Analyze button click ──────────────────────────────────────────────
    analyzeBtn.addEventListener('click', function() {
        if (!selectedFile) return;

        clearError();
        setLoading(true);

        const formData = new FormData();
        formData.append('leaf_image', selectedFile);

        fetch('analyze.php', {
                method: 'POST',
                body: formData
            })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Server error: HTTP ' + response.status + ' ' + response.statusText);
                }
                return response.text();
            })
            .then(function(text) {
                let data;
                try {
                    data = JSON.parse(text);
                } catch (e) {
                    // PHP likely printed a fatal error — show raw output for debugging
                    throw new Error(
                        'Server did not return valid JSON.\n\n' +
                        'Raw server output:\n' +
                        text.replace(/<[^>]+>/g, '').trim().substring(0, 500)
                    );
                }
                return data;
            })
            .then(function(data) {
                setLoading(false);

                if (data.success) {
                    displayResult(data);
                    prependHistoryRow(data);
                } else {
                    const msg = data.message || 'Analysis failed.';
                    const dbg = data.debug ? '\n\nDebug:\n' + data.debug : '';
                    showError(msg + dbg);
                }
            })
            .catch(function(err) {
                setLoading(false);
                showError(err.message);
                console.error('[LeafAnalyzer]', err);
            });
    });

    // ── Display analysis result ───────────────────────────────────────────
    function displayResult(data) {
        const isHealthy = data.status === 'healthy';

        // Icon + headline
        document.getElementById('resultIcon').textContent = isHealthy ? '✅' : '⚠️';
        document.getElementById('resultStatus').textContent = isHealthy ?
            'Leaf is Healthy!' :
            'Disease Detected: ' + (data.disease || 'Unknown');

        // Severity badge
        const severityBadge = document.getElementById('severityBadge');
        if (data.severity && data.severity !== 'None') {
            severityBadge.textContent = '⚡ Severity: ' + data.severity;
            severityBadge.className = 'severity-badge severity-' + data.severity.toLowerCase();
            severityBadge.classList.remove('hidden');
        } else {
            severityBadge.classList.add('hidden');
        }

        // Card border colour
        resultCard.className = 'result-card ' + (isHealthy ? 'healthy' : 'unhealthy');

        // Disease name row
        const diseaseRow = document.getElementById('diseaseRow');
        if (isHealthy) {
            diseaseRow.classList.add('hidden');
        } else {
            diseaseRow.classList.remove('hidden');
            document.getElementById('diseaseName').textContent = data.disease || 'Unknown';
        }

        // Description
        document.getElementById('descriptionText').textContent = data.description || '';

        // Confidence value + animated bar
        const pct = parseFloat(data.confidence) || 0;
        document.getElementById('confidenceValue').textContent = pct.toFixed(1) + '%';

        const fill = document.getElementById('confidenceFill');
        fill.style.transition = 'none';
        fill.style.width = '0%';
        requestAnimationFrame(function() {
            requestAnimationFrame(function() {
                fill.style.transition = 'width 1s ease';
                fill.style.width = pct + '%';
            });
        });

        // Solution / recommendations
        document.getElementById('solutionText').textContent = data.solution || 'N/A';

        // Show result section + smooth scroll
        resultSection.classList.remove('hidden');
        setTimeout(function() {
            resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 120);
    }

    // ── Prepend a new row to the history table without page reload ────────
    function prependHistoryRow(data) {
        const now = new Date();
        const dateStr = now.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }) +
            ' ' + now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
        const isHealthy = data.status === 'healthy';
        const badgeClass = isHealthy ? 'badge-healthy' : 'badge-unhealthy';
        const statusText = isHealthy ? 'Healthy' : 'Unhealthy';
        const imgSrc = '../' + (data.image || '');

        // Build the new <tr>
        const tr = document.createElement('tr');
        tr.innerHTML =
            '<td>' + (++historyRowCount) + '</td>' +
            '<td><img src="' + imgSrc + '" class="history-thumb" alt="Leaf" onerror="this.style.display=\'none\'"></td>' +
            '<td><span class="badge ' + badgeClass + '">' + statusText + '</span></td>' +
            '<td>' + (data.disease ? escapeHtml(data.disease) : '—') + '</td>' +
            '<td>' + data.confidence.toFixed(1) + '%</td>' +
            '<td>' + dateStr + '</td>';

        // If the table already exists, prepend to tbody and renumber
        const tbody = document.getElementById('historyBody');
        if (tbody) {
            tbody.insertBefore(tr, tbody.firstChild);
            // Renumber all rows
            Array.from(tbody.querySelectorAll('tr')).forEach(function(row, idx) {
                row.cells[0].textContent = idx + 1;
            });
            // Trim to 10 rows max
            while (tbody.rows.length > 10) {
                tbody.deleteRow(tbody.rows.length - 1);
            }
        } else {
            // Table didn't exist yet (empty state) — build the whole table
            const container = document.getElementById('historyContainer');
            if (!container) return;

            container.innerHTML =
                '<div class="history-table-wrapper">' +
                '<table class="history-table">' +
                '<thead><tr>' +
                '<th>#</th><th>Image</th><th>Status</th>' +
                '<th>Disease</th><th>Confidence</th><th>Date</th>' +
                '</tr></thead>' +
                '<tbody id="historyBody"></tbody>' +
                '</table>' +
                '</div>';

            document.getElementById('historyBody').appendChild(tr);
        }

        // Brief highlight on the new row
        tr.classList.add('row-highlight');
        setTimeout(function() { tr.classList.remove('row-highlight'); }, 2000);
    }

    // ── Reset button ──────────────────────────────────────────────────────
    resetBtn.addEventListener('click', function() {
        fileInput.value = '';
        selectedFile = null;

        previewImage.classList.add('hidden');
        previewImage.src = '';
        uploadPlaceholder.classList.remove('hidden');

        analyzeBtn.disabled = true;
        resultSection.classList.add('hidden');
        loading.classList.add('hidden');
        uploadArea.classList.remove('drag-over');
        clearError();
    });

    // ── Helpers ───────────────────────────────────────────────────────────
    function setLoading(on) {
        loading.classList.toggle('hidden', !on);
        resultSection.classList.add('hidden');
        analyzeBtn.disabled = on;
    }

    function showError(msg) {
        if (!jsErrorBox) return;
        jsErrorBox.style.display = 'block';
        jsErrorBox.textContent = msg;
    }

    function clearError() {
        if (!jsErrorBox) return;
        jsErrorBox.style.display = 'none';
        jsErrorBox.textContent = '';
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

});