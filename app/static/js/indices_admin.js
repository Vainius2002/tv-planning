// indices_admin.js - TG-specific indices management
(function() {
    'use strict';

    // Global state
    let apiUrls = {};
    let targetGroups = [];
    let selectedTG = null;
    let durationIndices = [];
    let seasonalIndices = [];
    let positionIndices = [];

    // Initialize when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        initializeApiUrls();
        bindEventListeners();
        loadData();
    });

    function initializeApiUrls() {
        const container = document.querySelector('[data-target-groups]');
        if (!container) return;

        apiUrls = {
            targetGroups: container.dataset.targetGroups,
            durationList: container.dataset.durationList,
            durationCreate: container.dataset.durationCreate,
            durationDeleteBase: container.dataset.durationDeleteBase,
            seasonalList: container.dataset.seasonalList,
            seasonalUpdateBase: container.dataset.seasonalUpdateBase,
            positionList: container.dataset.positionList
        };
    }

    function bindEventListeners() {
        // Target group selector
        const tgSelector = document.getElementById('targetGroupSelector');
        if (tgSelector) {
            tgSelector.addEventListener('change', handleTargetGroupChange);
        }

        // Duration range selector
        const durationRange = document.getElementById('durationRange');
        if (durationRange) {
            durationRange.addEventListener('change', handleDurationRangeChange);
        }

        // Update duration button
        const updateBtn = document.getElementById('updateDuration');
        if (updateBtn) {
            updateBtn.addEventListener('click', handleUpdateDuration);
        }
    }

    async function loadData() {
        try {
            // Load target groups
            const tgResponse = await fetch(apiUrls.targetGroups);
            if (tgResponse.ok) {
                targetGroups = await tgResponse.json();
                renderTargetGroupSelector();
            }

            // Load all indices data
            const [durationResponse, seasonalResponse, positionResponse] = await Promise.all([
                fetch(apiUrls.durationList),
                fetch(apiUrls.seasonalList),
                fetch(apiUrls.positionList)
            ]);

            if (durationResponse.ok) durationIndices = await durationResponse.json();
            if (seasonalResponse.ok) seasonalIndices = await seasonalResponse.json();
            if (positionResponse.ok) positionIndices = await positionResponse.json();

            // Update display if TG is selected
            if (selectedTG) {
                updateDisplayForSelectedTG();
            }

        } catch (error) {
            console.error('Error loading data:', error);
            showError('Nepavyko užkrauti duomenų');
        }
    }

    function renderTargetGroupSelector() {
        const selector = document.getElementById('targetGroupSelector');
        if (!selector) return;

        selector.innerHTML = '<option value="">Pasirinkite tikslinę grupę</option>';
        
        targetGroups.forEach(tg => {
            const option = document.createElement('option');
            option.value = tg;
            option.textContent = tg;
            selector.appendChild(option);
        });
    }

    function handleTargetGroupChange(e) {
        selectedTG = e.target.value;
        updateDisplayForSelectedTG();
    }

    function updateDisplayForSelectedTG() {
        if (!selectedTG) {
            // Clear displays
            document.getElementById('durationSummary').innerHTML = 
                '<p class="text-sm text-slate-600">Pasirinkite tikslinę grupę, kad pamatytumėte jos trukmės indeksus</p>';
            document.getElementById('seasonalTbody').innerHTML = '';
            document.getElementById('positionTbody').innerHTML = '';
            document.getElementById('updateDuration').disabled = true;
            return;
        }

        // Update duration summary
        renderDurationSummary();
        
        // Update seasonal indices table
        renderSeasonalIndices();
        
        // Update position indices table
        renderPositionIndices();

        // Enable duration form
        document.getElementById('updateDuration').disabled = false;
    }

    function renderDurationSummary() {
        const summary = document.getElementById('durationSummary');
        if (!summary) return;

        const tgDurationIndices = durationIndices.filter(item => item.target_group === selectedTG);
        
        if (tgDurationIndices.length === 0) {
            summary.innerHTML = '<p class="text-sm text-slate-600">Nerasta trukmės indeksų šiai TG</p>';
            return;
        }

        // Group by duration ranges
        const ranges = {
            '5-9': { values: [], index: null },
            '10-14': { values: [], index: null },
            '15-19': { values: [], index: null },
            '20-24': { values: [], index: null },
            '25-29': { values: [], index: null },
            '30-44': { values: [], index: null },
            '45+': { values: [], index: null }
        };

        tgDurationIndices.forEach(item => {
            const dur = item.duration_seconds;
            if (dur >= 5 && dur <= 9) ranges['5-9'].values.push(item);
            else if (dur >= 10 && dur <= 14) ranges['10-14'].values.push(item);
            else if (dur >= 15 && dur <= 19) ranges['15-19'].values.push(item);
            else if (dur >= 20 && dur <= 24) ranges['20-24'].values.push(item);
            else if (dur >= 25 && dur <= 29) ranges['25-29'].values.push(item);
            else if (dur >= 30 && dur <= 44) ranges['30-44'].values.push(item);
            else if (dur >= 45) ranges['45+'].values.push(item);
        });

        let html = '<div class="grid grid-cols-2 md:grid-cols-4 gap-4">';
        Object.entries(ranges).forEach(([range, data]) => {
            if (data.values.length > 0) {
                const indexValue = data.values[0].index_value;
                html += `
                    <div class="bg-white rounded-lg p-3 border">
                        <div class="text-sm font-medium text-slate-700">${range}</div>
                        <div class="text-lg font-bold text-blue-600">${indexValue}</div>
                        <div class="text-xs text-slate-500">${data.values.length} sek.</div>
                    </div>
                `;
            }
        });
        html += '</div>';

        summary.innerHTML = html;
    }

    function renderSeasonalIndices() {
        const tbody = document.getElementById('seasonalTbody');
        if (!tbody) return;

        tbody.innerHTML = '';

        const tgSeasonalIndices = seasonalIndices.filter(item => item.target_group === selectedTG);
        
        const monthNames = [
            '', 'Sausis', 'Vasaris', 'Kovas', 'Balandis', 'Gegužė', 'Birželis',
            'Liepa', 'Rugpjūtis', 'Rugsėjis', 'Spalis', 'Lapkritis', 'Gruodis'
        ];

        tgSeasonalIndices.forEach(item => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-slate-50';
            
            row.innerHTML = `
                <td class="px-4 py-2 font-medium">${monthNames[item.month]}</td>
                <td class="px-4 py-2">
                    <input type="number" step="0.01" min="0" value="${item.index_value}" 
                           class="seasonal-index-input w-20 rounded border-slate-300 px-2 py-1 text-sm"
                           data-month="${item.month}">
                </td>
                <td class="px-4 py-2">
                    <input type="text" value="${item.description || ''}" 
                           class="seasonal-desc-input w-full rounded border-slate-300 px-2 py-1 text-sm"
                           data-month="${item.month}">
                </td>
                <td class="px-4 py-2">
                    <button class="update-seasonal-btn px-2 py-1 text-xs rounded bg-blue-100 text-blue-700 hover:bg-blue-200"
                            data-month="${item.month}">
                        Atnaujinti
                    </button>
                </td>
            `;

            // Bind row-specific event listeners
            const updateBtn = row.querySelector('.update-seasonal-btn');
            const indexInput = row.querySelector('.seasonal-index-input');
            const descInput = row.querySelector('.seasonal-desc-input');

            if (updateBtn) {
                updateBtn.addEventListener('click', () => handleUpdateSeasonal(item.month));
            }

            // Update on Enter key
            [indexInput, descInput].forEach(input => {
                if (input) {
                    input.addEventListener('keypress', (e) => {
                        if (e.key === 'Enter') {
                            handleUpdateSeasonal(item.month);
                        }
                    });
                }
            });

            tbody.appendChild(row);
        });
    }

    function renderPositionIndices() {
        const tbody = document.getElementById('positionTbody');
        if (!tbody) return;

        tbody.innerHTML = '';

        const tgPositionIndices = positionIndices.filter(item => item.target_group === selectedTG);
        
        const positionNames = {
            'first': 'Pirma pozicija',
            'second': 'Antra pozicija',
            'last': 'Paskutinė',
            'other': 'Kita spec.'
        };

        tgPositionIndices.forEach(item => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-slate-50';
            
            row.innerHTML = `
                <td class="px-4 py-2 font-medium">${positionNames[item.position_type] || item.position_type}</td>
                <td class="px-4 py-2">
                    <span class="inline-block w-20 px-2 py-1 text-sm font-mono bg-slate-100 rounded">${item.index_value}</span>
                </td>
                <td class="px-4 py-2 text-sm text-slate-600">${item.description || ''}</td>
            `;

            tbody.appendChild(row);
        });
    }

    function handleDurationRangeChange(e) {
        const range = e.target.value;
        const descInput = document.getElementById('durationDescription');
        const indexInput = document.getElementById('durationIndex');

        if (!range) {
            descInput.value = '';
            indexInput.value = '';
            return;
        }

        // Set description based on range
        descInput.value = range;

        // Find current index value for this range
        if (selectedTG) {
            const tgDurationIndices = durationIndices.filter(item => item.target_group === selectedTG);
            // Get first value from the range (they should all be the same)
            let sampleDuration;
            switch(range) {
                case '5-9': sampleDuration = 5; break;
                case '10-14': sampleDuration = 10; break;
                case '15-19': sampleDuration = 15; break;
                case '20-24': sampleDuration = 20; break;
                case '25-29': sampleDuration = 25; break;
                case '30-44': sampleDuration = 30; break;
                case '45+': sampleDuration = 45; break;
            }

            const sampleItem = tgDurationIndices.find(item => item.duration_seconds === sampleDuration);
            if (sampleItem) {
                indexInput.value = sampleItem.index_value;
            }
        }
    }

    async function handleUpdateDuration() {
        if (!selectedTG) {
            showError('Pasirinkite tikslinę grupę');
            return;
        }

        const range = document.getElementById('durationRange').value;
        const indexValue = parseFloat(document.getElementById('durationIndex').value);

        if (!range) {
            showError('Pasirinkite trukmės intervalą');
            return;
        }

        if (!indexValue || indexValue <= 0) {
            showError('Įveskite teisingą indekso reikšmę');
            return;
        }

        // Update all durations in the range
        let durations = [];
        switch(range) {
            case '5-9': durations = Array.from({length: 5}, (_, i) => i + 5); break;
            case '10-14': durations = Array.from({length: 5}, (_, i) => i + 10); break;
            case '15-19': durations = Array.from({length: 5}, (_, i) => i + 15); break;
            case '20-24': durations = Array.from({length: 5}, (_, i) => i + 20); break;
            case '25-29': durations = Array.from({length: 5}, (_, i) => i + 25); break;
            case '30-44': durations = Array.from({length: 15}, (_, i) => i + 30); break;
            case '45+': durations = [45, 60, 90, 120]; break; // Common longer durations
        }

        try {
            // Update each duration in the range
            for (const duration of durations) {
                await fetch(apiUrls.durationCreate, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        target_group: selectedTG,
                        duration_seconds: duration,
                        index_value: indexValue,
                        description: `${range} (${selectedTG})`
                    })
                });
            }

            showSuccess(`Trukmės indeksai atnaujinti intervalui ${range}`);
            loadData(); // Reload to get updated values
        } catch (error) {
            console.error('Error updating duration indices:', error);
            showError('Nepavyko atnaujinti trukmės indeksų');
        }
    }

    async function handleUpdateSeasonal(month) {
        if (!selectedTG) {
            showError('Pasirinkite tikslinę grupę');
            return;
        }

        const indexInput = document.querySelector(`input[data-month="${month}"].seasonal-index-input`);
        const descInput = document.querySelector(`input[data-month="${month}"].seasonal-desc-input`);

        if (!indexInput) return;

        const indexValue = parseFloat(indexInput.value);
        const description = descInput ? descInput.value.trim() : '';

        if (!indexValue || indexValue <= 0) {
            showError('Įveskite teisingą indekso reikšmę');
            return;
        }

        try {
            const url = apiUrls.seasonalUpdateBase.replace('__TG__', encodeURIComponent(selectedTG)).replace('0', month);
            const response = await fetch(url, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    index_value: indexValue,
                    description: description || null
                })
            });

            const result = await response.json();
            
            if (response.ok && result.status === 'ok') {
                showSuccess('Sezoninis indeksas atnaujintas');
                loadData();
            } else {
                showError(result.message || 'Klaida atnaujinant indeksą');
            }
        } catch (error) {
            console.error('Error updating seasonal index:', error);
            showError('Nepavyko atnaujinti indekso');
        }
    }

    function showSuccess(message) {
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50';
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => notification.remove(), 3000);
    }

    function showError(message) {
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50';
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => notification.remove(), 5000);
    }
})();