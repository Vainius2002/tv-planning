// indices_admin.js - Channel Group specific indices management
(function() {
    'use strict';

    // Global state
    let apiUrls = {};
    let channelGroups = [];
    let selectedCG = null;
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
        const container = document.querySelector('[data-channel-groups]');
        if (!container) return;

        apiUrls = {
            channelGroups: container.dataset.channelGroups,
            durationList: container.dataset.durationList,
            durationCreate: container.dataset.durationCreate,
            durationDeleteBase: container.dataset.durationDeleteBase,
            seasonalList: container.dataset.seasonalList,
            seasonalUpdateBase: container.dataset.seasonalUpdateBase,
            positionList: container.dataset.positionList
        };
    }

    function bindEventListeners() {
        // Channel group selector
        const cgSelector = document.getElementById('channelGroupSelector');
        if (cgSelector) {
            cgSelector.addEventListener('change', handleChannelGroupChange);
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
            // Load channel groups
            const cgResponse = await fetch(apiUrls.channelGroups);
            if (cgResponse.ok) {
                channelGroups = await cgResponse.json();
                renderChannelGroupSelector();
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

            // Update display if channel group is selected
            if (selectedCG) {
                updateDisplayForSelectedCG();
            }

        } catch (error) {
            console.error('Error loading data:', error);
            showError('Nepavyko užkrauti duomenų');
        }
    }

    function renderChannelGroupSelector() {
        const selector = document.getElementById('channelGroupSelector');
        if (!selector) return;

        selector.innerHTML = '<option value="">Pasirinkite kanalų grupę</option>';
        
        channelGroups.forEach(cg => {
            const option = document.createElement('option');
            option.value = cg.name;
            option.textContent = cg.name;
            selector.appendChild(option);
        });
    }

    function handleChannelGroupChange(e) {
        selectedCG = e.target.value;
        updateDisplayForSelectedCG();
    }

    function updateDisplayForSelectedCG() {
        if (!selectedCG) {
            // Clear displays
            document.getElementById('durationSummary').innerHTML = 
                '<p class="text-sm text-slate-600">Pasirinkite kanalų grupę, kad pamatytumėte jos trukmės indeksus</p>';
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

        const cgDurationIndices = durationIndices.filter(item => item.channel_group_name === selectedCG);
        
        if (cgDurationIndices.length === 0) {
            summary.innerHTML = '<p class="text-sm text-slate-600">Nerasta trukmės indeksų šiai kanalų grupei</p>';
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

        cgDurationIndices.forEach(item => {
            const dur = item.duration_seconds;
            if (dur >= 5 && dur <= 9) ranges['5-9'].values.push(item);
            else if (dur >= 10 && dur <= 14) ranges['10-14'].values.push(item);
            else if (dur >= 15 && dur <= 19) ranges['15-19'].values.push(item);
            else if (dur >= 20 && dur <= 24) ranges['20-24'].values.push(item);
            else if (dur >= 25 && dur <= 29) ranges['25-29'].values.push(item);
            else if (dur >= 30 && dur <= 44) ranges['30-44'].values.push(item);
            else if (dur >= 45) ranges['45+'].values.push(item);
        });

        // Get representative index value for each range
        Object.keys(ranges).forEach(range => {
            if (ranges[range].values.length > 0) {
                ranges[range].index = ranges[range].values[0].index_value;
            }
        });

        // Render summary
        let html = `<h4 class="font-medium text-slate-700 mb-2">Trukmės indeksai - ${selectedCG}</h4>`;
        html += '<div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">';
        
        Object.keys(ranges).forEach(range => {
            const data = ranges[range];
            const active = data.index !== null;
            const badgeClass = active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-500';
            
            html += `<div class="px-2 py-1 rounded ${badgeClass}">
                ${range}": ${active ? data.index.toFixed(2) : 'N/A'}
            </div>`;
        });
        
        html += '</div>';
        summary.innerHTML = html;
    }

    function renderSeasonalIndices() {
        const tbody = document.getElementById('seasonalTbody');
        if (!tbody) return;

        const cgSeasonalIndices = seasonalIndices.filter(item => item.channel_group_name === selectedCG);
        
        if (cgSeasonalIndices.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center py-4 text-slate-500">Nerasta sezoninių indeksų šiai kanalų grupei</td></tr>';
            return;
        }

        const months = [
            'Sausis', 'Vasaris', 'Kovas', 'Balandis', 'Gegužė', 'Birželis',
            'Liepa', 'Rugpjūtis', 'Rugsėjis', 'Spalis', 'Lapkritis', 'Gruodis'
        ];

        tbody.innerHTML = '';
        
        for (let month = 1; month <= 12; month++) {
            const monthData = cgSeasonalIndices.find(item => item.month === month);
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="px-4 py-2 font-medium">${months[month - 1]}</td>
                <td class="px-4 py-2">
                    <input type="number" step="0.01" min="0" max="3" 
                           value="${monthData ? monthData.index_value : ''}" 
                           class="w-20 text-sm border rounded px-2 py-1 seasonal-input"
                           data-month="${month}">
                </td>
                <td class="px-4 py-2 text-sm text-slate-600">${monthData ? monthData.description || '' : ''}</td>
                <td class="px-4 py-2">
                    <button class="text-xs px-2 py-1 rounded border border-blue-300 bg-blue-50 text-blue-700 hover:bg-blue-100 save-seasonal"
                            data-month="${month}">Išsaugoti</button>
                </td>
            `;
            
            tbody.appendChild(tr);
        }

        // Bind seasonal save buttons
        tbody.querySelectorAll('.save-seasonal').forEach(btn => {
            btn.addEventListener('click', handleSaveSeasonal);
        });
    }

    function renderPositionIndices() {
        const tbody = document.getElementById('positionTbody');
        if (!tbody) return;

        const cgPositionIndices = positionIndices.filter(item => item.channel_group_name === selectedCG);
        
        tbody.innerHTML = '';
        
        const positions = [
            { type: 'first', name: 'Pirma pozicija' },
            { type: 'second', name: 'Antra pozicija' },
            { type: 'last', name: 'Paskutinė pozicija' },
            { type: 'other', name: 'Kita speciali' }
        ];

        positions.forEach(pos => {
            const posData = cgPositionIndices.find(item => item.position_type === pos.type);
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="px-4 py-2 font-medium">${pos.name}</td>
                <td class="px-4 py-2">${posData ? posData.index_value.toFixed(2) : 'N/A'}</td>
                <td class="px-4 py-2 text-sm text-slate-600">${posData ? posData.description || '' : ''}</td>
                <td class="px-4 py-2 text-xs text-slate-500">Tik skaityti</td>
            `;
            
            tbody.appendChild(tr);
        });
    }

    function handleDurationRangeChange(e) {
        const range = e.target.value;
        const indexInput = document.getElementById('durationIndex');
        const descInput = document.getElementById('durationDescription');
        
        if (!range) {
            indexInput.value = '';
            descInput.value = '';
            return;
        }

        // Map ranges to default values
        const defaults = {
            '5-9': { index: 1.35, desc: '5"-9" sekundės' },
            '10-14': { index: 1.25, desc: '10"-14" sekundžių' },
            '15-19': { index: 1.2, desc: '15"-19" sekundžių' },
            '20-24': { index: 1.15, desc: '20"-24" sekundės' },
            '25-29': { index: 1.1, desc: '25"-29" sekundės' },
            '30-44': { index: 1.0, desc: '30"-44" sekundės' },
            '45+': { index: 1.0, desc: '45+ sekundžių' }
        };

        const defaultData = defaults[range];
        if (defaultData) {
            indexInput.value = defaultData.index;
            descInput.value = defaultData.desc;
        }
    }

    async function handleUpdateDuration() {
        const range = document.getElementById('durationRange').value;
        const indexValue = parseFloat(document.getElementById('durationIndex').value);
        const description = document.getElementById('durationDescription').value;

        if (!range || !selectedCG || isNaN(indexValue)) {
            showError('Užpildykite visus laukus');
            return;
        }

        // Determine duration range
        let durFrom, durTo;
        switch (range) {
            case '5-9': durFrom = 5; durTo = 9; break;
            case '10-14': durFrom = 10; durTo = 14; break;
            case '15-19': durFrom = 15; durTo = 19; break;
            case '20-24': durFrom = 20; durTo = 24; break;
            case '25-29': durFrom = 25; durTo = 29; break;
            case '30-44': durFrom = 30; durTo = 44; break;
            case '45+': durFrom = 45; durTo = 300; break;
            default: return;
        }

        try {
            // Update each duration in the range
            for (let duration = durFrom; duration <= Math.min(durTo, 300); duration++) {
                const response = await fetch(apiUrls.durationCreate, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        channel_group: selectedCG,
                        duration_seconds: duration,
                        index_value: indexValue,
                        description: description
                    })
                });

                if (!response.ok) {
                    throw new Error(`Klaida atnaujinant ${duration}s: ${response.statusText}`);
                }
            }

            showSuccess(`Atnaujinti ${range}" indeksai kanalų grupei "${selectedCG}"`);
            
            // Reload data and refresh display
            await loadData();
            updateDisplayForSelectedCG();

        } catch (error) {
            showError('Nepavyko atnaujinti indeksų: ' + error.message);
        }
    }

    async function handleSaveSeasonal(e) {
        const month = parseInt(e.target.dataset.month);
        const input = e.target.closest('tr').querySelector('.seasonal-input');
        const indexValue = parseFloat(input.value);

        if (!selectedCG || isNaN(indexValue)) {
            showError('Nepavyko išsaugoti - patikrinkite reikšmę');
            return;
        }

        try {
            const url = apiUrls.seasonalUpdateBase.replace('__CG__', encodeURIComponent(selectedCG)).replace('0', month);
            const response = await fetch(url, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    index_value: indexValue,
                    description: `${month} mėnuo (${selectedCG})`
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            showSuccess(`${month} mėnesio indeksas išsaugotas`);
            
            // Reload data
            await loadData();
            renderSeasonalIndices();

        } catch (error) {
            showError('Nepavyko išsaugoti: ' + error.message);
        }
    }

    function showError(message) {
        // Simple error display - you might want to enhance this
        alert('Klaida: ' + message);
    }

    function showSuccess(message) {
        // Simple success display - you might want to enhance this  
        alert('Sėkmingai: ' + message);
    }

})();