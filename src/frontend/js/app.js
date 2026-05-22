(function () {
    'use strict';

    const API_BASE_URL = '';
    const POLL_INTERVAL = 2000;
    const MAX_POLL_ATTEMPTS = 150;
    const MAX_FILE_SIZE = 10 * 1024 * 1024;
    const ALLOWED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.pdf'];

    const state = {
        currentJobId: null,
        currentFile: null,
        pollTimer: null,
        pollCount: 0,
        report: null,
        provider: 'openai',
        apiKey: ''
    };

    const $ = (id) => document.getElementById(id);

    const els = {
        uploadZone: $('uploadZone'),
        fileInput: $('fileInput'),
        fileInfo: $('fileInfo'),
        fileName: $('fileName'),
        fileSize: $('fileSize'),
        uploadBtn: $('uploadBtn'),
        uploadError: $('uploadError'),
        uploadSection: $('uploadSection'),
        statusSection: $('statusSection'),
        statusError: $('statusError'),
        statusErrorMsg: $('statusErrorMsg'),
        statusMeta: $('statusMeta'),
        statusTime: $('statusTime'),
        resultSection: $('resultSection'),
        componentsList: $('componentsList'),
        risksList: $('risksList'),
        recommendationsList: $('recommendationsList'),
        downloadJson: $('downloadJson'),
        downloadPdf: $('downloadPdf'),
        reportContent: $('reportContent'),
        providerToggle: $('providerToggle'),
        apiKeyInput: $('apiKeyInput'),
        toggleKeyVisibility: $('toggleKeyVisibility')
    };

    // Provider & API Key
    function initProvider() {
        els.providerToggle.addEventListener('click', (e) => {
            const btn = e.target.closest('.provider-btn');
            if (!btn) return;
            els.providerToggle.querySelectorAll('.provider-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.provider = btn.dataset.provider;
        });

        els.apiKeyInput.addEventListener('input', (e) => {
            state.apiKey = e.target.value.trim();
        });

        els.toggleKeyVisibility.addEventListener('click', () => {
            const input = els.apiKeyInput;
            input.type = input.type === 'password' ? 'text' : 'password';
        });
    }

    // Upload
    function initUpload() {
        els.uploadZone.addEventListener('click', (e) => {
            if (e.target === els.fileInput) return;
            els.fileInput.click();
        });
        els.fileInput.addEventListener('change', (e) => handleFileSelect(e.target.files[0]));
        els.uploadBtn.addEventListener('click', submitUpload);

        els.uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            els.uploadZone.classList.add('drag-over');
        });
        els.uploadZone.addEventListener('dragleave', () => {
            els.uploadZone.classList.remove('drag-over');
        });
        els.uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            els.uploadZone.classList.remove('drag-over');
            if (e.dataTransfer.files.length) {
                handleFileSelect(e.dataTransfer.files[0]);
            }
        });
    }

    function handleFileSelect(file) {
        if (!file) return;

        hideError();
        const ext = '.' + file.name.split('.').pop().toLowerCase();

        if (!ALLOWED_EXTENSIONS.includes(ext)) {
            showError('Formato não suportado. Use PNG, JPG, JPEG ou PDF.');
            return;
        }

        if (file.size > MAX_FILE_SIZE) {
            showError('Arquivo muito grande. Tamanho máximo: 10MB.');
            return;
        }

        state.currentFile = file;
        els.fileName.textContent = file.name;
        els.fileSize.textContent = formatSize(file.size);
        els.fileInfo.hidden = false;
    }

    async function submitUpload() {
        if (!state.currentFile) return;

        state.apiKey = els.apiKeyInput.value.trim();

        if (!state.apiKey) {
            showError('Informe sua chave de API antes de enviar.');
            return;
        }

        els.uploadBtn.disabled = true;
        els.uploadBtn.classList.add('btn-loading');
        hideError();

        const formData = new FormData();
        formData.append('file', state.currentFile);
        formData.append('provider', state.provider);
        formData.append('apiKey', state.apiKey);

        try {
            const response = await fetch(`${API_BASE_URL}/api/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => null);
                throw new Error(errorData?.message || `Erro ${response.status}: falha no envio`);
            }

            const data = await response.json();
            state.currentJobId = data.jobId;
            startStatusPolling();
        } catch (err) {
            showError(err.message || 'Erro ao enviar arquivo. Verifique sua conexão.');
        } finally {
            els.uploadBtn.disabled = false;
            els.uploadBtn.classList.remove('btn-loading');
        }
    }

    // Status Polling
    function startStatusPolling() {
        els.statusSection.hidden = false;
        els.resultSection.hidden = true;
        state.pollCount = 0;
        resetStepper();
        hideStatusError();
        updateStep('step-received', 'active');

        state.pollTimer = setInterval(pollStatus, POLL_INTERVAL);
        pollStatus();
    }

    async function pollStatus() {
        state.pollCount++;

        if (state.pollCount > MAX_POLL_ATTEMPTS) {
            stopPolling();
            showStatusError('Tempo limite excedido. O processamento demorou mais que o esperado.');
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/status/${state.currentJobId}`);

            if (response.status === 404) {
                updateStep('step-received', 'active');
                return;
            }

            if (!response.ok) {
                throw new Error(`Erro ${response.status}`);
            }

            const data = await response.json();
            updateStatusUI(data);
        } catch (err) {
            // Silently retry on network errors
        }
    }

    function updateStatusUI(data) {
        const status = data.status;

        if (data.updatedAt) {
            els.statusMeta.hidden = false;
            els.statusTime.textContent = `Atualizado: ${formatDate(data.updatedAt)}`;
        }

        switch (status) {
            case 'Received':
                hideStatusError();
                updateStep('step-received', 'active');
                break;

            case 'Processing':
                hideStatusError();
                updateStep('step-received', 'completed');
                updateStep('step-processing', 'active');
                break;

            case 'Analyzed':
                hideStatusError();
                updateStep('step-received', 'completed');
                updateStep('step-processing', 'completed');
                updateStep('step-analyzed', 'completed');
                stopPolling();
                fetchReport();
                break;

            case 'Failed':
                stopPolling();
                updateStep('step-received', 'completed');
                updateStep('step-processing', 'error');
                showStatusError(data.errorMessage || 'Ocorreu um erro durante a análise.');
                break;
        }
    }

    function stopPolling() {
        if (state.pollTimer) {
            clearInterval(state.pollTimer);
            state.pollTimer = null;
        }
    }

    function resetStepper() {
        document.querySelectorAll('.step').forEach((step) => {
            step.classList.remove('step--active', 'step--completed', 'step--error');
        });
        hideStatusError();
        els.statusMeta.hidden = true;
    }

    function updateStep(stepId, status) {
        const step = document.getElementById(stepId);
        step.classList.remove('step--active', 'step--completed', 'step--error');
        step.classList.add(`step--${status}`);
    }

    function showStatusError(msg) {
        els.statusError.hidden = false;
        els.statusErrorMsg.textContent = msg;
    }

    function hideStatusError() {
        els.statusError.hidden = true;
        els.statusErrorMsg.textContent = '';
    }

    // Report
    async function fetchReport() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/report/${state.currentJobId}`);

            if (!response.ok) {
                throw new Error('Não foi possível carregar o relatório.');
            }

            const data = await response.json();
            state.report = data;
            renderReport(data);
        } catch (err) {
            showStatusError(err.message);
        }
    }

    function renderReport(report) {
        els.resultSection.hidden = false;

        renderList(els.componentsList, report.components || []);
        renderList(els.risksList, report.risks || []);
        renderList(els.recommendationsList, report.recommendations || []);

        els.resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function renderList(ul, items) {
        ul.innerHTML = '';
        if (items.length === 0) {
            const li = document.createElement('li');
            li.textContent = 'Nenhum item identificado';
            li.style.color = 'var(--text-muted)';
            ul.appendChild(li);
            return;
        }
        items.forEach((item) => {
            const li = document.createElement('li');
            li.textContent = item;
            ul.appendChild(li);
        });
    }

    // Download
    function initDownload() {
        els.downloadJson.addEventListener('click', downloadAsJSON);
        els.downloadPdf.addEventListener('click', downloadAsPDF);
    }

    function downloadAsJSON() {
        if (!state.report) return;

        const blob = new Blob([JSON.stringify(state.report, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `relatorio-${state.currentJobId}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function downloadAsPDF() {
        if (!state.report) return;
        window.print();
    }

    // Helpers
    function showError(msg) {
        els.uploadError.textContent = msg;
        els.uploadError.hidden = false;
    }

    function hideError() {
        els.uploadError.hidden = true;
    }

    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function formatDate(isoString) {
        const date = new Date(isoString);
        return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    // Init
    function init() {
        initProvider();
        initUpload();
        initDownload();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
