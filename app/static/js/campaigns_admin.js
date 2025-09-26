// static/js/campaigns_admin.js
(() => {
  'use strict';

  window.addEventListener('DOMContentLoaded', () => {
    const dataDiv = document.querySelector('[data-c-list]');

    const C_LIST    = dataDiv.dataset.cList;
    const C_UPDATE  = dataDiv.dataset.cUpdateBase;    // ends with /0
    const C_DELETE  = dataDiv.dataset.cDeleteBase;    // ends with /0

    const W_LIST    = dataDiv.dataset.wListBase;      // /campaigns/0/waves
    const W_CREATE  = dataDiv.dataset.wCreateBase;    // /campaigns/0/waves
    const W_UPDATE  = dataDiv.dataset.wUpdateBase;    // /waves/0
    const W_DELETE  = dataDiv.dataset.wDeleteBase;    // /waves/0

    const I_LIST    = dataDiv.dataset.iListBase;      // /waves/0/items
    const I_CREATE  = dataDiv.dataset.iCreateBase;    // /waves/0/items
    const I_UPDATE  = dataDiv.dataset.iUpdateBase;    // /wave-items/0
    const I_DELETE  = dataDiv.dataset.iDeleteBase;    // /wave-items/0

    const CD_LIST   = dataDiv.dataset.cdListBase;     // /campaigns/0/discounts
    const CD_CREATE = dataDiv.dataset.cdCreateBase;   // /campaigns/0/discounts
    const WD_LIST   = dataDiv.dataset.wdListBase;     // /waves/0/discounts
    const WD_CREATE = dataDiv.dataset.wdCreateBase;   // /waves/0/discounts
    const D_UPDATE  = dataDiv.dataset.dUpdateBase;    // /discounts/0
    const D_DELETE  = dataDiv.dataset.dDeleteBase;    // /discounts/0
    const W_TOTAL   = dataDiv.dataset.wTotalBase;     // /waves/0/total
    const W_RECALC  = dataDiv.dataset.wRecalcBase;    // /waves/0/recalculate-discounts
    const C_STATUS  = dataDiv.dataset.cStatusBase;   // /campaigns/0/status
    
    const TVC_LIST   = dataDiv.dataset.tvcListBase;   // /campaigns/0/tvcs
    const TVC_CREATE = dataDiv.dataset.tvcCreateBase; // /campaigns/0/tvcs
    const TVC_UPDATE = dataDiv.dataset.tvcUpdateBase; // /tvcs/0
    const TVC_DELETE = dataDiv.dataset.tvcDeleteBase; // /tvcs/0
    const W_INDICES  = dataDiv.dataset.wIndicesBase;  // /waves/0/indices
    const C_EXPORT_EXCEL = dataDiv.dataset.cExportExcelBase; // /campaigns/0/export/client-excel
    const C_EXPORT_CSV = dataDiv.dataset.cExportCsvBase;     // /campaigns/0/export/agency-csv
    const TRP_SAVE = dataDiv.dataset.trpSaveBase;            // /campaigns/0/trp-distribution
    const TRP_LOAD = dataDiv.dataset.trpLoadBase;            // /campaigns/0/trp-distribution

    const $ = s => document.querySelector(s);
    const cTbody = $('#cTbody');
    const campaignSearch = $('#campaignSearch');
    const statusFilter = $('#statusFilter');
    const agencyFilter = $('#agencyFilter');
    const dateRangeFilter = $('#dateRangeFilter');
    const clearFilters = $('#clearFilters');
    const campaignsCount = $('#campaignsCount');
    const activeFiltersIndicator = $('#activeFiltersIndicator');

    const wavePanel = $('#wavePanel');
    const wavesDiv  = $('#waves');
    const noCampaign = $('#noCampaign');
    
    const tvcName = $('#tvcName'), tvcDuration = $('#tvcDuration');
    const tvcAdd = $('#tvcAdd'), tvcList = $('#tvcList');

    let lists = [];     // pricing lists
    let campaigns = []; // campaigns
    let filteredCampaigns = []; // filtered campaigns for search
    let currentCampaign = null;
    let tvcs = [];      // TVCs for current campaign
    let channels = [];  // Store channel groups for lookup

    function urlReplace(base, id){ return base.replace(/\/0($|\/)/, `/${id}$1`); }

    async function fetchJSON(url, opt){
      const r = await fetch(url, opt);
      let data = null; try { data = await r.json(); } catch {}
      if(!r.ok) throw new Error((data && (data.message||data.error)) || `${r.status} ${r.statusText}`);
      return data;
    }

    // -------- Excel calculation functions --------
    function calculateGRP(item) {
      // GRP = TRP * 100 / affinity1
      const trps = parseFloat(item.trps) || 0;
      const affinity1 = parseFloat(item.affinity1);
      
      if (!affinity1 || affinity1 === 0) {
        return 0; // Cannot calculate GRP without valid affinity1
      }
      
      return trps * 100 / affinity1;
    }

    function calculateGrossPrice(item, grossCpp) {
      // Gross Price = TRP * CPP * duration_index * seasonal_index * trp_purchase_index * advance_purchase_index * web_index * advance_payment_index * loyalty_discount_index * position_index
      const trps = parseFloat(item.trps) || 0;
      const cpp = parseFloat(grossCpp) || 0;
      const durationIndex = parseFloat(item.duration_index) || 1.0; // From DB
      const seasonalIndex = parseFloat(item.seasonal_index) || 1.0; // From DB
      const trpPurchaseIndex = parseFloat(item.trp_purchase_index) || 0.95;
      const advancePurchaseIndex = parseFloat(item.advance_purchase_index) || 0.95;
      const webIndex = parseFloat(item.web_index) || 1.0;
      const advancePaymentIndex = parseFloat(item.advance_payment_index) || 1.0;
      const loyaltyDiscountIndex = parseFloat(item.loyalty_discount_index) || 1.0;
      const positionIndex = parseFloat(item.position_index) || 1.0;

      return trps * cpp * durationIndex * seasonalIndex * trpPurchaseIndex * advancePurchaseIndex * webIndex * advancePaymentIndex * loyaltyDiscountIndex * positionIndex;
    }

    function calculateNetPrice(grossPrice, clientDiscount) {
      // Net Price = Gross Price * (1 - client_discount / 100)
      const discount = parseFloat(clientDiscount) || 0;
      return grossPrice * (1 - discount / 100);
    }

    function calculateNetNetPrice(netPrice, agencyDiscount) {
      // Net Net Price = Net Price * (1 - agency_discount / 100)
      const discount = parseFloat(agencyDiscount) || 0;
      return netPrice * (1 - discount / 100);
    }

    function getChannelName(channelId) {
      const channel = channels.find(ch => ch.id == channelId);
      return channel ? channel.name : null;
    }


    // -------- campaigns table --------
    
    // Generate TRP calendar data for Excel export
    function generateTRPCalendarData() {
      if (!currentCampaign || !currentWaves || currentWaves.length === 0) {
        return null;
      }
      
      // Get campaign date range
      let startDate = currentCampaign.start_date ? new Date(currentCampaign.start_date) : null;
      let endDate = currentCampaign.end_date ? new Date(currentCampaign.end_date) : null;
      
      // Extend to include all wave dates
      currentWaves.forEach(wave => {
        if (wave.start_date) {
          const waveStart = new Date(wave.start_date);
          if (!startDate || waveStart < startDate) startDate = waveStart;
        }
        if (wave.end_date) {
          const waveEnd = new Date(wave.end_date);
          if (!endDate || waveEnd > endDate) endDate = waveEnd;
        }
      });
      
      if (!startDate || !endDate) return null;
      
      // Generate date columns
      const dateColumns = [];
      const currentDate = new Date(startDate);
      while (currentDate <= endDate) {
        dateColumns.push(currentDate.toISOString().split('T')[0]);
        currentDate.setDate(currentDate.getDate() + 1);
      }
      
      // Generate wave data
      const waveRows = [];
      currentWaves.forEach((wave, waveIndex) => {
        if (!wave.start_date || !wave.end_date) return;
        
        // Calculate total TRP for this wave from table
        let waveTotalTRP = 0;
        const tableRows = document.querySelectorAll('#wavesTableBody tr');
        tableRows.forEach(row => {
          // Check if this row belongs to the current wave by matching dates
          const startDateCell = row.querySelector('td:nth-child(1)');
          const endDateCell = row.querySelector('td:nth-child(2)');
          if (startDateCell && endDateCell && 
              startDateCell.textContent === (wave.start_date || '-') && 
              endDateCell.textContent === (wave.end_date || '-')) {
            const trpInput = row.querySelector('.itm-trps');
            if (trpInput && trpInput.value) {
              waveTotalTRP += parseFloat(trpInput.value) || 0;
            }
          }
        });
        
        if (waveTotalTRP === 0) return;
        
        const waveStart = new Date(wave.start_date);
        const waveEnd = new Date(wave.end_date);
        const waveDays = Math.ceil((waveEnd - waveStart) / (1000 * 60 * 60 * 24)) + 1;
        const dailyTRP = waveTotalTRP / waveDays;
        
        // Create daily distribution
        const dailyValues = {};
        dateColumns.forEach(dateStr => {
          const date = new Date(dateStr);
          const isInWave = date >= waveStart && date <= waveEnd;
          dailyValues[dateStr] = isInWave ? Math.round(dailyTRP * 100) / 100 : 0;
        });
        
        waveRows.push({
          waveIndex: waveIndex + 1,
          waveName: wave.channel_group || `Banga ${waveIndex + 1}`,
          startDate: wave.start_date,
          endDate: wave.end_date,
          totalTRP: waveTotalTRP,
          dailyValues: dailyValues
        });
      });
      
      return {
        startDate: startDate.toISOString().split('T')[0],
        endDate: endDate.toISOString().split('T')[0],
        dateColumns: dateColumns,
        waveRows: waveRows,
        campaignName: currentCampaign.name
      };
    }

    function renderCampaigns(){
      cTbody.innerHTML = '';
      
      filteredCampaigns.forEach(c => {
        const tr = document.createElement('tr');
        const statusColors = {
          'draft': 'bg-slate-100 text-slate-700',
          'confirmed': 'bg-blue-100 text-blue-700',
          'orders_sent': 'bg-yellow-100 text-yellow-700',
          'active': 'bg-green-100 text-green-700',
          'completed': 'bg-gray-100 text-gray-700'
        };
        const statusLabels = {
          'draft': 'Juodraštis',
          'confirmed': 'Patvirtinta',
          'orders_sent': 'Užsakymai išsiųsti',
          'active': 'Aktyvi',
          'completed': 'Užbaigta'
        };
        
        tr.innerHTML = `
          <td class="px-4 py-2 text-slate-500">${c.id}</td>
          <td class="px-4 py-2">
            <div class="font-medium">${c.name}</div>
            <div class="text-xs text-slate-500">${c.client || ''} ${c.product ? '- ' + c.product : ''}</div>
          </td>
          <td class="px-4 py-2">
            <div>${c.agency || '-'}</div>
            <div class="text-xs text-slate-500">${c.country || 'Lietuva'}</div>
          </td>
          <td class="px-4 py-2">${(c.start_date||'')}${c.end_date?(' – '+c.end_date):''}</td>
          <td class="px-4 py-2">
            <select class="status-select rounded border-slate-300 px-2 py-1 text-xs ${statusColors[c.status] || statusColors.draft}">
              <option value="draft" ${c.status === 'draft' ? 'selected' : ''}>Juodraštis</option>
              <option value="confirmed" ${c.status === 'confirmed' ? 'selected' : ''}>Patvirtinta</option>
              <option value="orders_sent" ${c.status === 'orders_sent' ? 'selected' : ''}>Užsakymai išsiųsti</option>
              <option value="active" ${c.status === 'active' ? 'selected' : ''}>Aktyvi</option>
              <option value="completed" ${c.status === 'completed' ? 'selected' : ''}>Užbaigta</option>
            </select>
          </td>
          <td class="px-4 py-2">
            <div class="flex flex-wrap gap-1">
              <button class="open px-3 py-1.5 text-xs rounded-lg border border-slate-300 bg-white hover:bg-slate-50">Atidaryti</button>
              <button class="export-client px-3 py-1.5 text-xs rounded-lg border border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100" data-campaign-id="${c.id}">Excel klientui</button>
              <button class="del px-3 py-1.5 text-xs rounded-lg border border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100">Šalinti</button>
            </div>
          </td>`;
        tr.querySelector('.open').addEventListener('click', () => openCampaign(c));
        tr.querySelector('.export-client').addEventListener('click', () => {
          const url = urlReplace(C_EXPORT_EXCEL, c.id);
          console.log('Exporting client Excel for campaign:', c.id, 'URL:', url);

          // Use window.open to handle HTTP download properly
          window.open(url, '_blank');
        });
        tr.querySelector('.del').addEventListener('click', async () => {
          if(!confirm('Šalinti kampaniją?')) return;
          await fetchJSON(urlReplace(C_DELETE, c.id), { method: 'DELETE' });
          await loadCampaigns();
          if(currentCampaign && currentCampaign.id === c.id){
            currentCampaign = null;
            renderCurrentCampaign();
          }
        });
        tr.querySelector('.status-select').addEventListener('change', async (e) => {
          const newStatus = e.target.value;
          try {
            await fetchJSON(urlReplace(C_STATUS, c.id), {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ status: newStatus })
            });
            c.status = newStatus; // Update local data
            // Update the select styling
            e.target.className = `status-select rounded border-slate-300 px-2 py-1 text-xs ${statusColors[newStatus] || statusColors.draft}`;
          } catch (error) {
            alert('Klaida keičiant statusą: ' + error.message);
            e.target.value = c.status; // Revert on error
          }
        });
        cTbody.appendChild(tr);
      });
    }

    function populateAgencyFilter() {
      const agencies = [...new Set(campaigns.map(c => c.agency).filter(Boolean))];
      agencyFilter.innerHTML = '<option value="">Visos agentūros</option>';
      agencies.sort().forEach(agency => {
        const option = document.createElement('option');
        option.value = agency;
        option.textContent = agency;
        agencyFilter.appendChild(option);
      });
    }

    function matchesDateRange(campaign, dateRange) {
      if (!dateRange) return true;
      
      const now = new Date();
      const currentMonth = now.getMonth();
      const currentYear = now.getFullYear();
      
      const startDate = campaign.start_date ? new Date(campaign.start_date) : null;
      const endDate = campaign.end_date ? new Date(campaign.end_date) : null;
      
      switch (dateRange) {
        case 'current_month':
          return (startDate && startDate.getMonth() === currentMonth && startDate.getFullYear() === currentYear) ||
                 (endDate && endDate.getMonth() === currentMonth && endDate.getFullYear() === currentYear) ||
                 (startDate && endDate && startDate <= now && endDate >= now);
        case 'current_year':
          return (startDate && startDate.getFullYear() === currentYear) ||
                 (endDate && endDate.getFullYear() === currentYear);
        case 'past':
          return endDate && endDate < now;
        case 'future':
          return startDate && startDate > now;
        default:
          return true;
      }
    }

    function filterCampaigns(searchTerm = '', statusFilter = '', agencyFilter = '', dateRangeFilter = '') {
      filteredCampaigns = campaigns.filter(c => {
        // Search filter
        const matchesSearch = !searchTerm.trim() || 
          (c.name && c.name.toLowerCase().includes(searchTerm.toLowerCase())) ||
          (c.client && c.client.toLowerCase().includes(searchTerm.toLowerCase())) ||
          (c.product && c.product.toLowerCase().includes(searchTerm.toLowerCase())) ||
          (c.agency && c.agency.toLowerCase().includes(searchTerm.toLowerCase()));
        
        // Status filter
        const matchesStatus = !statusFilter || c.status === statusFilter;
        
        // Agency filter
        const matchesAgency = !agencyFilter || c.agency === agencyFilter;
        
        // Date range filter
        const matchesDate = matchesDateRange(c, dateRangeFilter);
        
        return matchesSearch && matchesStatus && matchesAgency && matchesDate;
      });
      updateResultsIndicator();
      renderCampaigns();
    }

    function updateResultsIndicator() {
      const total = campaigns.length;
      const showing = filteredCampaigns.length;
      
      if (total === showing) {
        campaignsCount.textContent = `Rodomos visos kampanijos (${total})`;
      } else {
        campaignsCount.textContent = `Rodomos ${showing} iš ${total} kampanijų`;
      }
      
      // Show active filters indicator
      const hasActiveFilters = 
        campaignSearch.value.trim() ||
        statusFilter.value ||
        agencyFilter.value ||
        dateRangeFilter.value;
      
      if (hasActiveFilters) {
        activeFiltersIndicator.classList.remove('hidden');
      } else {
        activeFiltersIndicator.classList.add('hidden');
      }
    }

    function applyFilters() {
      const searchTerm = campaignSearch.value;
      const statusValue = statusFilter.value;
      const agencyValue = agencyFilter.value;
      const dateRangeValue = dateRangeFilter.value;
      filterCampaigns(searchTerm, statusValue, agencyValue, dateRangeValue);
    }

    async function loadCampaigns(){
      campaigns = await fetchJSON(C_LIST);
      populateAgencyFilter();
      filteredCampaigns = [...campaigns];
      renderCampaigns();
    }

    // Event listeners
    campaignSearch.addEventListener('input', applyFilters);
    statusFilter.addEventListener('change', applyFilters);
    agencyFilter.addEventListener('change', applyFilters);
    dateRangeFilter.addEventListener('change', applyFilters);
    
    clearFilters.addEventListener('click', () => {
      campaignSearch.value = '';
      statusFilter.value = '';
      agencyFilter.value = '';
      dateRangeFilter.value = '';
      applyFilters();
    });

    // -------- TVC Management --------
    async function loadTVCs(campaignId) {
      try {
        tvcs = await fetchJSON(urlReplace(TVC_LIST, campaignId));
        renderTVCs();
      } catch (e) {
        console.error('Error loading TVCs:', e);
        tvcs = [];
        renderTVCs();
      }
    }

    function renderTVCs() {
      tvcList.innerHTML = '';
      tvcs.forEach(tvc => {
        const div = document.createElement('div');
        div.className = 'flex items-center justify-between bg-white px-3 py-2 rounded border';
        div.innerHTML = `
          <div class="flex items-center gap-3">
            <span class="font-medium">${tvc.name}</span>
            <span class="text-sm text-slate-500">${tvc.duration} sek.</span>
          </div>
          <div class="flex gap-2">
            <button class="edit-tvc text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-50" data-id="${tvc.id}">Redaguoti</button>
            <button class="delete-tvc text-xs px-2 py-1 rounded border border-rose-300 text-rose-700 hover:bg-rose-50" data-id="${tvc.id}">Šalinti</button>
          </div>
        `;
        
        div.querySelector('.edit-tvc').addEventListener('click', () => editTVC(tvc));
        div.querySelector('.delete-tvc').addEventListener('click', () => deleteTVC(tvc.id));
        
        tvcList.appendChild(div);
      });
      
      // Update TVC selections in all wave forms
      updateAllTVCSelections();
      
      // Update initial form TVCs
      if (window.updateInitialFormTVCs) {
        window.updateInitialFormTVCs();
      }
    }

    function updateAllTVCSelections() {
      const tvcSelects = wavesDiv.querySelectorAll('.tvc-select');
      const waveFormSelect = document.querySelector('#wTVC'); // Wave creation form select
      
      // Update both wave form and wave item selects
      const allSelects = [...tvcSelects];
      if (waveFormSelect) allSelects.push(waveFormSelect);
      
      allSelects.forEach(select => {
        const currentValue = select.value;
        select.innerHTML = '<option value="">Pasirinkti TVC</option>';
        tvcs.forEach(tvc => {
          select.innerHTML += `<option value="${tvc.id}">${tvc.name} (${tvc.duration} sek.)</option>`;
        });
        // Restore selected value if still exists
        if (currentValue && tvcs.some(tvc => tvc.id == currentValue)) {
          select.value = currentValue;
        }
      });
    }


    async function createTVC() {
      const name = tvcName.value.trim();
      const duration = parseInt(tvcDuration.value) || 0;
      
      if (!name) {
        alert('Įveskite TVC pavadinimą');
        return;
      }
      if (duration <= 0) {
        alert('Įveskite teisingą trukmę');
        return;
      }
      
      try {
        await fetchJSON(urlReplace(TVC_CREATE, currentCampaign.id), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, duration })
        });
        
        tvcName.value = '';
        tvcDuration.value = '';
        await loadTVCs(currentCampaign.id);
        await loadWaves(currentCampaign.id); // Reload waves to update TVC dropdowns
      } catch (e) {
        alert('Klaida kuriant TVC: ' + e.message);
      }
    }

    function editTVC(tvc) {
      const newName = prompt('TVC pavadinimas:', tvc.name);
      const newDuration = prompt('Trukmė (sek.):', tvc.duration);
      
      if (newName === null || newDuration === null) return;
      
      if (!newName.trim()) {
        alert('Pavadinimas negali būti tuščias');
        return;
      }
      
      const duration = parseInt(newDuration) || 0;
      if (duration <= 0) {
        alert('Trukmė turi būti teigiama');
        return;
      }
      
      updateTVC(tvc.id, newName.trim(), duration);
    }

    async function updateTVC(id, name, duration) {
      try {
        await fetchJSON(urlReplace(TVC_UPDATE, id), {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, duration })
        });
        await loadTVCs(currentCampaign.id);
        await loadWaves(currentCampaign.id); // Reload waves to update TVC displays
      } catch (e) {
        alert('Klaida redaguojant TVC: ' + e.message);
      }
    }

    async function deleteTVC(id) {
      if (!confirm('Šalinti TVC?')) return;
      
      try {
        await fetchJSON(urlReplace(TVC_DELETE, id), { method: 'DELETE' });
        await loadTVCs(currentCampaign.id);
        await loadWaves(currentCampaign.id); // Reload waves to update TVC displays
      } catch (e) {
        alert('Klaida šalinant TVC: ' + e.message);
      }
    }

    function renderCurrentCampaign(){
      const campaignsSection = document.querySelector('#campaignsSection');
      const wavesSection = document.querySelector('#wavesSection');
      const campaignInfo = document.querySelector('#campaignInfo');
      
      if(!currentCampaign){
        // Show campaigns list, hide waves
        campaignsSection.classList.remove('hidden');
        wavesSection.classList.add('hidden');
        wavePanel.classList.add('hidden');
        noCampaign.classList.remove('hidden');
        wavesDiv.innerHTML = '';
        return;
      }
      
      // Hide campaigns list, show waves section
      campaignsSection.classList.add('hidden');
      wavesSection.classList.remove('hidden');
      wavePanel.classList.remove('hidden');
      noCampaign.classList.add('hidden');
      
      // Show campaign info
      campaignInfo.innerHTML = `
        <strong>${currentCampaign.name}</strong> | 
        ${currentCampaign.client || ''} ${currentCampaign.product ? '- ' + currentCampaign.product : ''} | 
        ${currentCampaign.start_date || 'Nėra datos'} - ${currentCampaign.end_date || 'Nėra datos'}
      `;
      
      // Set date limits for initial wave form based on campaign dates
      const firstWaveStart = document.querySelector('#firstWaveStart');
      const firstWaveEnd = document.querySelector('#firstWaveEnd');
      
      if (firstWaveStart && currentCampaign.start_date) {
        firstWaveStart.min = currentCampaign.start_date;
        firstWaveStart.value = currentCampaign.start_date; // Default to campaign start
      }
      if (firstWaveEnd && currentCampaign.end_date) {
        firstWaveEnd.max = currentCampaign.end_date;
        firstWaveEnd.value = currentCampaign.end_date; // Default to campaign end
      }
      if (firstWaveStart && currentCampaign.end_date) {
        firstWaveStart.max = currentCampaign.end_date;
      }
      if (firstWaveEnd && currentCampaign.start_date) {
        firstWaveEnd.min = currentCampaign.start_date;
      }
      
      loadTVCs(currentCampaign.id);  // Load TVCs when campaign opens
      loadWaves(currentCampaign.id); // loadWaves will call renderCampaignCalendar
    }
    
    function renderCampaignCalendar() {
      console.log('renderCampaignCalendar called');
      const calendarDiv = document.querySelector('#campaignCalendar');
      if (!calendarDiv || !currentCampaign) return;
      
      // Generate calendar based on campaign dates, but extend to include all waves
      let startDate = currentCampaign.start_date ? new Date(currentCampaign.start_date) : new Date();
      let endDate = currentCampaign.end_date ? new Date(currentCampaign.end_date) : new Date(startDate.getTime() + 30 * 24 * 60 * 60 * 1000); // 30 days default
      
      // Check if any waves extend beyond campaign dates
      if (currentWaves && currentWaves.length > 0) {
        currentWaves.forEach(wave => {
          if (wave.start_date) {
            const waveStart = new Date(wave.start_date);
            if (waveStart < startDate) {
              startDate = new Date(waveStart);
            }
          }
          if (wave.end_date) {
            const waveEnd = new Date(wave.end_date);
            if (waveEnd > endDate) {
              endDate = new Date(waveEnd);
            }
          }
        });
      }
      
      // Create horizontal table like Excel
      let html = '<table class="min-w-full">';
      html += '<thead>';
      
      // Month row
      html += '<tr class="border-b border-slate-200">';
      html += `<th class="px-2 py-1 text-xs font-medium text-slate-700 bg-slate-50 border-r border-slate-300 sticky left-0">Kanalų grupė</th>`;
      
      const months = [];
      const monthDays = {};
      let tempDate = new Date(startDate);
      
      while (tempDate <= endDate) {
        const monthKey = `${tempDate.getFullYear()}-${tempDate.getMonth()}`;
        const monthName = tempDate.toLocaleDateString('lt-LT', { month: 'long', year: 'numeric' });
        if (!monthDays[monthKey]) {
          monthDays[monthKey] = { name: monthName, days: 0 };
          months.push(monthKey);
        }
        monthDays[monthKey].days++;
        tempDate.setDate(tempDate.getDate() + 1);
      }
      
      months.forEach(monthKey => {
        html += `<th colspan="${monthDays[monthKey].days}" class="px-2 py-1 text-xs font-medium text-slate-700 bg-slate-50 border-r border-slate-200">${monthDays[monthKey].name}</th>`;
      });
      html += '</tr>';
      
      // Day numbers row
      html += '<tr class="border-b border-slate-300">';
      html += `<th class="px-2 py-1 text-xs font-medium bg-slate-50 border-r border-slate-300 sticky left-0"></th>`;
      tempDate = new Date(startDate);
      while (tempDate <= endDate) {
        const dayNum = tempDate.getDate();
        const isWeekend = tempDate.getDay() === 0 || tempDate.getDay() === 6;
        html += `<th class="px-1 py-1 text-xs font-medium ${isWeekend ? 'bg-gray-100 text-gray-500' : 'bg-white text-slate-700'} border-r border-slate-200 min-w-[40px]">${dayNum}</th>`;
        tempDate.setDate(tempDate.getDate() + 1);
      }
      html += '</tr>';
      
      // Week days row  
      html += '<tr class="border-b border-slate-200">';
      html += `<td class="px-2 py-1 text-xs bg-slate-50 border-r border-slate-300 sticky left-0"></td>`;
      tempDate = new Date(startDate);
      const weekDayNames = ['S', 'P', 'A', 'T', 'K', 'Pn', 'Š'];
      while (tempDate <= endDate) {
        const weekDay = weekDayNames[tempDate.getDay()];
        const isWeekend = tempDate.getDay() === 0 || tempDate.getDay() === 6;
        html += `<td class="px-1 py-1 text-xs text-center ${isWeekend ? 'bg-gray-100 text-gray-500' : 'bg-white text-slate-600'} border-r border-slate-200">${weekDay}</td>`;
        tempDate.setDate(tempDate.getDate() + 1);
      }
      html += '</tr>';
      html += '</thead>';
      html += '<tbody>';
      
      // Wave rows with TRP inputs
      if (currentWaves && currentWaves.length > 0) {
        currentWaves.forEach((wave, waveIndex) => {
          if (wave.start_date && wave.end_date) {
            html += `<tr class="border-b border-slate-200 hover:bg-slate-50">`;
            html += `<td class="px-2 py-2 text-xs font-medium bg-slate-100 border-r border-slate-300 sticky left-0">
              <div class="flex items-center justify-between">
                <span>${wave.channel_group || `Banga ${waveIndex + 1}`}</span>
                <button class="calendar-wave-delete ml-2 text-rose-600 hover:text-rose-800 text-xs" data-wave-id="${wave.id}" title="Šalinti bangą">✕</button>
              </div>
            </td>`;
            
            tempDate = new Date(startDate);
            const waveStart = new Date(wave.start_date);
            const waveEnd = new Date(wave.end_date);
            
            while (tempDate <= endDate) {
              const isInWave = tempDate >= waveStart && tempDate <= waveEnd;
              const dateStr = tempDate.toISOString().split('T')[0];
              const isWeekend = tempDate.getDay() === 0 || tempDate.getDay() === 6;
              
              if (isInWave) {
                html += `<td class="px-1 py-1 border-r border-slate-200 ${isWeekend ? 'bg-green-100' : 'bg-green-200'}">`;
                html += `<input type="text" inputmode="decimal" class="trp-input-wave w-full text-xs px-1 py-0.5 border-0 bg-transparent text-center font-medium text-slate-700" data-wave-id="${wave.id}" data-date="${dateStr}" placeholder="0.00" />`;
              } else {
                html += `<td class="px-1 py-1 border-r border-slate-200 ${isWeekend ? 'bg-gray-50' : ''}">`;
              }
              html += '</td>';
              tempDate.setDate(tempDate.getDate() + 1);
            }
            html += '</tr>';
          }
        });
      }
      
      // Auto-distribution controls row
      html += '<tr class="bg-slate-50 border-t border-slate-200">';
      html += `<td class="px-2 py-2 text-xs bg-slate-100 border-r border-slate-300 sticky left-0"></td>`;
      html += `<td colspan="${Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24))}" class="px-2 py-2 text-xs">`;
      html += '<div class="flex gap-2 items-center justify-center">';
      html += '<button id="autoDistributeTRP" class="px-3 py-1 text-xs rounded bg-emerald-600 text-white hover:bg-emerald-700 transition-colors">📊 Auto-paskirstyti TRP (visiems bangoms)</button>';
      html += '<button id="clearTRP" class="px-3 py-1 text-xs rounded bg-slate-400 text-white hover:bg-slate-500 transition-colors">🗑️ Išvalyti visus TRP</button>';
      html += '<span class="text-slate-600 ml-3">Kiekvienos bangos TRP bus paskirstyti per jos aktyvias dienas</span>';
      html += '</div>';
      html += '</td>';
      html += '</tr>';
      
      html += '</tbody>';
      html += '</table>';
      
      calendarDiv.innerHTML = html;
      
      // Add event listeners for wave-specific TRP inputs
      const trpWaveInputs = calendarDiv.querySelectorAll('.trp-input-wave');
      trpWaveInputs.forEach(input => {
        input.addEventListener('input', () => {
          saveWaveTRPDistribution(input.dataset.waveId);
        });
        input.addEventListener('blur', () => {
          saveWaveTRPDistribution(input.dataset.waveId);
        });
      });

      // Add event listeners for calendar wave delete buttons
      const calendarWaveDeleteBtns = calendarDiv.querySelectorAll('.calendar-wave-delete');
      calendarWaveDeleteBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
          if (!confirm('Šalinti bangą iš kalendoriaus?')) return;
          
          try {
            const waveId = btn.dataset.waveId;
            console.log('Deleting wave from calendar:', waveId);
            
            await fetchJSON(urlReplace(W_DELETE, waveId), { method: 'DELETE' });
            
            console.log('Wave deleted, reloading...');
            await loadWaves(currentCampaign.id);
          } catch (error) {
            console.error('Error deleting wave from calendar:', error);
            alert('Klaida šalinant bangą: ' + error.message);
          }
        });
      });

      // Auto-distribute TRP button
      const autoDistributeBtn = document.getElementById('autoDistributeTRP');
      if (autoDistributeBtn) {
        autoDistributeBtn.addEventListener('click', autoDistributeTRP);
      }

      // Clear TRP button
      const clearBtn = document.getElementById('clearTRP');
      if (clearBtn) {
        clearBtn.addEventListener('click', clearAllTRP);
      }
      
      // Then load existing TRP data for each wave
      if (currentWaves && currentWaves.length > 0) {
        currentWaves.forEach(wave => {
          loadWaveTRPDistribution(wave.id);
        });
      }
    }

    // -------- TRP Distribution functions --------
    async function loadTRPDistribution() {
      if (!currentCampaign) return;
      
      try {
        const response = await fetchJSON(urlReplace(TRP_LOAD, currentCampaign.id));
        
        if (response.status === 'ok' && response.data) {
          const trpData = response.data;
          console.log('Loading TRP from database for campaign', currentCampaign.id, ':', trpData);
          
          // Fill in the input fields
          Object.keys(trpData).forEach(date => {
            const input = document.querySelector(`.trp-input[data-date="${date}"]`);
            if (input) {
              const roundedValue = trpData[date] > 0 ? Math.round(trpData[date] * 100) / 100 : 0;
              input.value = roundedValue > 0 ? roundedValue.toString() : '';
              console.log('Set input for', date, 'to', roundedValue, '(from', trpData[date], ')');
            } else {
              console.log('TRP Input not found for date:', date);
            }
          });
        } else {
          console.log('No TRP distribution data found for campaign', currentCampaign.id);
        }
      } catch (error) {
        console.error('Error loading TRP distribution:', error);
      }
    }
    
    function updateTotalTRP() {
      const trpInputs = document.querySelectorAll('.trp-input');
      let total = 0;
      
      trpInputs.forEach(input => {
        const value = parseFloat(input.value) || 0;
        total += value;
      });
      
      const totalSpan = document.querySelector('#totalTRP');
      if (totalSpan) {
        totalSpan.textContent = total.toFixed(2);
      }
    }
    
    async function saveTRPDistribution() {
      if (!currentCampaign) return;
      
      try {
        updateTotalTRP();
        
        const trpData = {};
        const trpInputs = document.querySelectorAll('.trp-input');
        console.log('Found TRP inputs:', trpInputs.length);
        
        trpInputs.forEach(input => {
          const date = input.dataset.date;
          const rawValue = input.value.trim();
          const value = rawValue === '' ? 0 : parseFloat(rawValue) || 0;
          console.log(`SAVE DEBUG: Processing input for ${date}: raw_value="${rawValue}", parsed=${value}, type="${input.type}"`);
          trpData[date] = value; // Saugok visus, net ir 0
        });
        
        // Save to database via API
        try {
          const response = await fetchJSON(urlReplace(TRP_SAVE, currentCampaign.id), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trp_data: trpData })
          });
          
          if (response.status === 'ok') {
            console.log('TRP Distribution saved to database for campaign', currentCampaign.id, ':', trpData);
          } else {
            console.error('Failed to save TRP distribution:', response.message);
          }
        } catch (apiError) {
          console.error('Error saving TRP distribution to database:', apiError);
        }
      } catch (error) {
        console.error('Error saving TRP distribution:', error);
      }
    }

    // Auto-distribute TRP across each wave's active days
    function autoDistributeTRP() {
      if (!currentWaves || currentWaves.length === 0) {
        alert('Nėra bangų, kurioms galima paskirstyti TRP');
        return;
      }

      let totalDistributed = 0;
      let totalDays = 0;

      // Process each wave separately
      currentWaves.forEach((wave, waveIndex) => {
        if (!wave.start_date || !wave.end_date) return;

        // Get TRP for this specific wave from the table
        let waveTRP = 0;
        const tableRows = document.querySelectorAll('#wavesTableBody tr');
        tableRows.forEach(row => {
          // Check if this row belongs to the current wave by matching dates
          const startDateCell = row.querySelector('td:nth-child(1)');
          const endDateCell = row.querySelector('td:nth-child(2)');
          if (startDateCell && endDateCell && 
              startDateCell.textContent === (wave.start_date || '-') && 
              endDateCell.textContent === (wave.end_date || '-')) {
            const trpInput = row.querySelector('.itm-trps');
            if (trpInput && trpInput.value) {
              waveTRP += parseFloat(trpInput.value) || 0;
            }
          }
        });

        if (waveTRP === 0) return; // Skip waves with no TRP

        // Get active days for this wave
        const startDate = new Date(wave.start_date);
        const endDate = new Date(wave.end_date);
        const activeDays = [];
        
        for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
          activeDays.push(d.toISOString().split('T')[0]);
        }

        if (activeDays.length === 0) return;

        // Calculate daily TRP for this wave
        const dailyTRP = waveTRP / activeDays.length;
        const roundedDaily = Math.round(dailyTRP * 100) / 100;

        // Clear this wave's inputs first
        const waveInputs = document.querySelectorAll(`.trp-input-wave[data-wave-id="${wave.id}"]`);
        waveInputs.forEach(input => {
          input.value = '';
        });

        // Fill this wave's active days with calculated daily TRP
        activeDays.forEach(dateStr => {
          const input = document.querySelector(`.trp-input-wave[data-wave-id="${wave.id}"][data-date="${dateStr}"]`);
          if (input) {
            input.value = roundedDaily.toString();
          }
        });

        // Save this wave's TRP distribution
        saveWaveTRPDistribution(wave.id);

        totalDistributed += waveTRP;
        totalDays += activeDays.length;
      });

      if (totalDistributed === 0) {
        alert('Įveskite TRP reikšmes bangų eilutėse pirmiau auto-paskirstymo');
        return;
      }

      alert(`TRP paskirstyti: ${totalDistributed.toFixed(2)} TRP per ${currentWaves.length} bangas`);
    }

    // -------- Wave-specific TRP Distribution functions --------
    async function loadWaveTRPDistribution(waveId) {
      if (!currentCampaign || !waveId) return;
      
      try {
        // Use wave-specific endpoint if available, otherwise fall back to campaign TRP
        const response = await fetchJSON(`/tv-planner/waves/${waveId}/trp-distribution`);
        
        if (response.status === 'ok' && response.data) {
          const trpData = response.data;
          
          // Fill in the input fields for this wave
          Object.keys(trpData).forEach(date => {
            const input = document.querySelector(`.trp-input-wave[data-wave-id="${waveId}"][data-date="${date}"]`);
            if (input && trpData[date] > 0) {
              const roundedValue = Math.round(trpData[date] * 100) / 100;
              input.value = roundedValue.toString();
            }
          });
        }
      } catch (error) {
        console.log(`No TRP distribution found for wave ${waveId} (this is normal for new waves)`);
      }
    }
    
    async function saveWaveTRPDistribution(waveId) {
      if (!currentCampaign || !waveId) return;
      
      try {
        const trpData = {};
        const waveInputs = document.querySelectorAll(`.trp-input-wave[data-wave-id="${waveId}"]`);
        
        waveInputs.forEach(input => {
          const date = input.dataset.date;
          const rawValue = input.value.trim();
          const value = rawValue === '' ? 0 : parseFloat(rawValue) || 0;
          trpData[date] = value;
        });
        
        // Save to database via wave-specific endpoint
        try {
          const response = await fetchJSON(`/tv-planner/waves/${waveId}/trp-distribution`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trp_data: trpData })
          });
          
          console.log(`TRP Distribution saved for wave ${waveId}:`, trpData);
        } catch (apiError) {
          // Fall back to campaign-level save if wave-specific endpoint doesn't exist
          console.log('Wave-specific TRP endpoint not available, using campaign-level save');
          const response = await fetchJSON(urlReplace(TRP_SAVE, currentCampaign.id), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trp_data: trpData, wave_id: waveId })
          });
        }
      } catch (error) {
        console.error(`Error saving TRP distribution for wave ${waveId}:`, error);
      }
    }

    // Clear all TRP inputs
    function clearAllTRP() {
      if (!confirm('Ar tikrai norite išvalyti visus TRP paskirstymus?')) {
        return;
      }

      const trpInputs = document.querySelectorAll('.trp-input-wave');
      trpInputs.forEach(input => {
        input.value = '';
      });

      // Save cleared data for each wave
      if (currentWaves) {
        currentWaves.forEach(wave => {
          saveWaveTRPDistribution(wave.id);
        });
      }
    }

    function openCampaign(c){
      currentCampaign = c;
      renderCurrentCampaign();
    }

    // -------- waves + items --------
    let currentWaves = []; // Store waves for calendar display
    
    async function loadWaves(cid){
      const waves = await fetchJSON(urlReplace(W_LIST, cid));
      
      // Load items for each wave to get channel group
      for(const wave of waves) {
        try {
          const items = await fetchJSON(urlReplace(I_LIST, wave.id));
          wave.items = items;
          // Get channel group from first item
          if (items && items.length > 0) {
            wave.channel_group = items[0].channel_group || items[0].owner || `Banga ${waves.indexOf(wave) + 1}`;
          } else {
            wave.channel_group = `Banga ${waves.indexOf(wave) + 1}`;
          }
        } catch(e) {
          wave.items = [];
          wave.channel_group = `Banga ${waves.indexOf(wave) + 1}`;
        }
      }
      
      currentWaves = waves; // Store for calendar
      
      // Clear old waves div (will be removed eventually)
      wavesDiv.innerHTML = '';
      
      // Update the single table with all waves
      const wavesTable = document.querySelector('#wavesTable');
      const wavesTableBody = document.querySelector('#wavesTableBody');
      
      if (wavesTableBody) {
        wavesTableBody.innerHTML = '';
        
        if (waves && waves.length > 0) {
          // Show the table
          if (wavesTable) {
            wavesTable.style.display = 'block';
          }
          
          // Load all items for all waves and display in single table
          for(const w of waves){
            try {
              const items = await fetchJSON(urlReplace(I_LIST, w.id));
              const waveIndex = waves.indexOf(w) + 1;
              
              if (items && items.length > 0) {
                for(const item of items) {
                  const tvcName = item.tvc_id && tvcs.find(tvc => tvc.id == item.tvc_id)?.name || '-';
                  
                  // Calculate derived values
                  const grpPlanned = calculateGRP(item);
                  const grossCpp = item.gross_cpp_eur || 0;
                  const grossPrice = calculateGrossPrice(item, grossCpp);
                  const netPrice = calculateNetPrice(grossPrice, item.client_discount || 0);
                  const netNetPrice = calculateNetNetPrice(netPrice, item.agency_discount || 0);
                  
                  const tr = document.createElement('tr');
                  tr.innerHTML = `
                    <td class="px-2 py-1 text-xs">${w.start_date || '-'}</td>
                    <td class="px-2 py-1 text-xs">${w.end_date || '-'}</td>
                    <td class="px-2 py-1 text-xs">${item.channel_group || getChannelName(item.channel_id) || item.owner || '-'}</td>
                    <td class="px-2 py-1 text-xs">${item.target_group || '-'}</td>
                    <td class="px-2 py-1 text-xs bg-blue-50">${tvcName}</td>
                    <td class="px-2 py-1 text-xs">${item.clip_duration || 10}</td>
                    <td class="px-2 py-1 text-xs bg-green-50">${item.tg_size_thousands || '-'}</td>
                    <td class="px-2 py-1 text-xs bg-green-50">${item.tg_share_percent ? item.tg_share_percent.toFixed(1) + '%' : '-'}</td>
                    <td class="px-2 py-1 text-xs bg-green-50">${item.tg_sample_size || '-'}</td>
                    <td class="px-2 py-1 text-xs">${((item.channel_share || 0.75) * 100).toFixed(1)}%</td>
                    <td class="px-2 py-1 text-xs">${((item.pt_zone_share || 0.55) * 100).toFixed(1)}%</td>
                    <td class="px-2 py-1 text-xs">${((item.npt_zone_share || 0.45) * 100).toFixed(1)}%</td>
                    <td class="px-2 py-1 text-xs grp-planned">${grpPlanned.toFixed(2)}</td>
                    <td class="px-2 py-1"><input class="itm-trps w-16 text-xs border rounded px-1 py-0.5 bg-purple-50" type="number" step="0.01" value="${item.trps || ''}" placeholder="TRP" data-item-id="${item.id}"></td>
                    <td class="px-2 py-1"><input class="itm-affinity1 w-12 text-xs border rounded px-1 py-0.5 bg-purple-50" type="number" step="0.1" value="${item.affinity1 || ''}" placeholder="Affinity" data-item-id="${item.id}"></td>
                    <td class="px-2 py-1 text-xs">€${grossCpp.toFixed(2)}</td>
                    <td class="px-2 py-1 text-xs bg-yellow-50">${(item.duration_index || 1.25).toFixed(2)}</td>
                    <td class="px-2 py-1 text-xs bg-yellow-50">${(item.seasonal_index || 0.9).toFixed(2)}</td>
                    <td class="px-2 py-1"><input class="itm-trp-purchase w-12 text-xs border rounded px-1 py-0.5 bg-gray-100" type="number" step="0.01" value="${(item.trp_purchase_index || 0.95).toFixed(2)}" data-item-id="${item.id}"></td>
                    <td class="px-2 py-1"><input class="itm-advance-purchase w-12 text-xs border rounded px-1 py-0.5 bg-gray-100" type="number" step="0.01" value="${(item.advance_purchase_index || 0.95).toFixed(2)}" data-item-id="${item.id}"></td>
                    <td class="px-2 py-1"><input class="itm-web w-12 text-xs border rounded px-1 py-0.5 bg-gray-100" type="number" step="0.01" value="${(item.web_index || 1.0).toFixed(2)}" data-item-id="${item.id}"></td>
                    <td class="px-2 py-1"><input class="itm-advance-payment w-12 text-xs border rounded px-1 py-0.5 bg-gray-100" type="number" step="0.01" value="${(item.advance_payment_index || 1.0).toFixed(2)}" data-item-id="${item.id}"></td>
                    <td class="px-2 py-1"><input class="itm-loyalty-discount w-12 text-xs border rounded px-1 py-0.5 bg-gray-100" type="number" step="0.01" value="${(item.loyalty_discount_index || 1.0).toFixed(2)}" data-item-id="${item.id}"></td>
                    <td class="px-2 py-1"><input class="itm-position w-12 text-xs border rounded px-1 py-0.5 bg-gray-100" type="number" step="0.01" value="${(item.position_index || 1.0).toFixed(2)}" data-item-id="${item.id}"></td>
                    <td class="px-2 py-1 text-xs gross-price">€${grossPrice.toFixed(2)}</td>
                    <td class="px-2 py-1"><input class="itm-client-discount w-12 text-xs border rounded px-1 py-0.5 bg-blue-50" type="number" step="0.1" min="0" max="100" value="${item.client_discount || 0}" data-item-id="${item.id}"></td>
                    <td class="px-2 py-1 text-xs net-price">€${netPrice.toFixed(2)}</td>
                    <td class="px-2 py-1"><input class="itm-agency-discount w-12 text-xs border rounded px-1 py-0.5 bg-blue-50" type="number" step="0.1" min="0" max="100" value="${item.agency_discount || 0}" data-item-id="${item.id}"></td>
                    <td class="px-2 py-1 text-xs net-net-price">€${netNetPrice.toFixed(2)}</td>
                    <td class="px-2 py-1">
                      <div class="flex gap-1">
                        <button class="itm-save px-2 py-0.5 text-xs rounded border border-emerald-300 bg-emerald-50 text-emerald-700" data-item-id="${item.id}">Saugoti</button>
                        <button class="wave-item-del px-2 py-0.5 text-xs rounded border border-rose-300 bg-rose-50 text-rose-700" data-wave-id="${w.id}" data-item-id="${item.id}">X</button>
                      </div>
                    </td>
                  `;
                  
                  // Add real-time calculation functions
                  const recalculatePrices = () => {
                    // Get current values from inputs and stored data
                    const trps = parseFloat(tr.querySelector('.itm-trps').value) || 0;
                    const durationIndex = parseFloat(item.duration_index) || 1.0;
                    const seasonalIndex = parseFloat(item.seasonal_index) || 1.0;  
                    const trpPurchaseIndex = parseFloat(tr.querySelector('.itm-trp-purchase').value) || 0.95;
                    const advancePurchaseIndex = parseFloat(tr.querySelector('.itm-advance-purchase').value) || 0.95;
                    const webIndex = parseFloat(tr.querySelector('.itm-web').value) || 1.0;
                    const advancePaymentIndex = parseFloat(tr.querySelector('.itm-advance-payment').value) || 1.0;
                    const loyaltyDiscountIndex = parseFloat(tr.querySelector('.itm-loyalty-discount').value) || 1.0;
                    const positionIndex = parseFloat(tr.querySelector('.itm-position').value) || 1.0;
                    const clientDiscount = parseFloat(tr.querySelector('.itm-client-discount').value) || 0;
                    const agencyDiscount = parseFloat(tr.querySelector('.itm-agency-discount').value) || 0;
                    
                    // Recalculate gross price with current values
                    const itemData = {
                      trps: trps,
                      duration_index: durationIndex,
                      seasonal_index: seasonalIndex,
                      trp_purchase_index: trpPurchaseIndex,
                      advance_purchase_index: advancePurchaseIndex,
                      web_index: webIndex,
                      advance_payment_index: advancePaymentIndex,
                      loyalty_discount_index: loyaltyDiscountIndex,
                      position_index: positionIndex
                    };
                    
                    const newGrossPrice = calculateGrossPrice(itemData, grossCpp);
                    const newNetPrice = calculateNetPrice(newGrossPrice, clientDiscount);
                    const newNetNetPrice = calculateNetNetPrice(newNetPrice, agencyDiscount);
                    
                    // Update all displayed prices
                    const grossPriceCell = tr.querySelector('.gross-price');
                    const netPriceCell = tr.querySelector('.net-price');
                    const netNetPriceCell = tr.querySelector('.net-net-price');
                    
                    if (grossPriceCell) grossPriceCell.innerHTML = `€${newGrossPrice.toFixed(2)}`;
                    if (netPriceCell) netPriceCell.innerHTML = `€${newNetPrice.toFixed(2)}`;
                    if (netNetPriceCell) netNetPriceCell.innerHTML = `€${newNetNetPrice.toFixed(2)}`;
                  };
                  
                  // Function to recalculate and update GRP when TRP or affinity changes
                  const recalculateGRP = () => {
                    const trps = parseFloat(tr.querySelector('.itm-trps').value) || 0;
                    const affinity1 = parseFloat(tr.querySelector('.itm-affinity1').value);
                    
                    let newGRP = 0;
                    if (affinity1 && affinity1 !== 0 && trps > 0) {
                      newGRP = trps * 100 / affinity1;
                    }
                    
                    // Update the GRP display
                    const grpCell = tr.querySelector('.grp-planned');
                    if (grpCell) {
                      grpCell.textContent = newGRP.toFixed(2);
                    }
                  };
                  
                  // Add event listeners for real-time calculations
                  tr.querySelector('.itm-trps').addEventListener('input', () => {
                    recalculateGRP();
                    recalculatePrices();
                  });
                  tr.querySelector('.itm-affinity1').addEventListener('input', recalculateGRP);
                  tr.querySelector('.itm-trp-purchase').addEventListener('input', recalculatePrices);
                  tr.querySelector('.itm-advance-purchase').addEventListener('input', recalculatePrices);
                  tr.querySelector('.itm-web').addEventListener('input', recalculatePrices);
                  tr.querySelector('.itm-advance-payment').addEventListener('input', recalculatePrices);
                  tr.querySelector('.itm-loyalty-discount').addEventListener('input', recalculatePrices);
                  tr.querySelector('.itm-position').addEventListener('input', recalculatePrices);
                  tr.querySelector('.itm-client-discount').addEventListener('input', recalculatePrices);
                  tr.querySelector('.itm-agency-discount').addEventListener('input', recalculatePrices);
                  
                  // Add save handler
                  tr.querySelector('.itm-save').addEventListener('click', async () => {
                    try {
                      const itemId = tr.querySelector('.itm-save').dataset.itemId;
                      const trps = parseFloat(tr.querySelector('.itm-trps').value) || 0;
                      const affinity1 = parseFloat(tr.querySelector('.itm-affinity1').value) || 0;
                      const trpPurchaseIndex = parseFloat(tr.querySelector('.itm-trp-purchase').value) || 0.95;
                      const advancePurchaseIndex = parseFloat(tr.querySelector('.itm-advance-purchase').value) || 0.95;
                      const webIndex = parseFloat(tr.querySelector('.itm-web').value) || 1.0;
                      const advancePaymentIndex = parseFloat(tr.querySelector('.itm-advance-payment').value) || 1.0;
                      const loyaltyDiscountIndex = parseFloat(tr.querySelector('.itm-loyalty-discount').value) || 1.0;
                      const positionIndex = parseFloat(tr.querySelector('.itm-position').value) || 1.0;
                      const clientDiscount = parseFloat(tr.querySelector('.itm-client-discount').value) || 0;
                      const agencyDiscount = parseFloat(tr.querySelector('.itm-agency-discount').value) || 0;
                      
                      await fetchJSON(urlReplace(I_UPDATE, itemId), {
                        method:'PATCH', 
                        headers:{'Content-Type':'application/json'},
                        body: JSON.stringify({
                          trps: trps,
                          affinity1: affinity1,
                          trp_purchase_index: trpPurchaseIndex,
                          advance_purchase_index: advancePurchaseIndex,
                          web_index: webIndex,
                          advance_payment_index: advancePaymentIndex,
                          loyalty_discount_index: loyaltyDiscountIndex,
                          position_index: positionIndex,
                          client_discount: clientDiscount,
                          agency_discount: agencyDiscount
                        })
                      });
                      
                      await loadWaves(currentCampaign.id);
                      alert('Išsaugota');
                    } catch (error) {
                      alert('Klaida išsaugant: ' + error.message);
                    }
                  });
                  
                  // Add delete handler
                  tr.querySelector('.wave-item-del').addEventListener('click', async () => {
                    if(!confirm('Šalinti eilutę?')) return;
                    
                    try {
                      console.log('Deleting wave item:', item.id);
                      
                      // Delete the item
                      await fetchJSON(urlReplace(I_DELETE, item.id), { method:'DELETE' });
                      
                      // Check if this was the last item in the wave
                      const remainingItems = items.filter(i => i.id !== item.id);
                      if (remainingItems.length === 0) {
                        console.log('Deleting wave too:', w.id);
                        // Delete the wave too if it was the last item
                        await fetchJSON(urlReplace(W_DELETE, w.id), { method:'DELETE' });
                      }
                      
                      console.log('Reloading waves...');
                      await loadWaves(currentCampaign.id);
                      console.log('Waves reloaded successfully');
                    } catch (error) {
                      console.error('Error during deletion:', error);
                      alert('Klaida šalinant: ' + error.message);
                    }
                  });
                  
                  wavesTableBody.appendChild(tr);
                }
              }
            } catch (e) {
              console.error('Error loading items for wave', w.id, e);
            }
          }
        } else {
          // Hide the table if no waves
          if (wavesTable) {
            wavesTable.style.display = 'none';
          }
        }
      }
      
      // Update calendar with wave information (called once for all cases)
      renderCampaignCalendar();
      
      // Don't render the old wave containers anymore
      return;
      
      for(const w of waves){
        const section = document.createElement('div');
        section.className = "mb-8 border border-slate-200 rounded-xl overflow-hidden";
        
        try {
        section.innerHTML = `
          <div class="px-4 py-3 bg-slate-50 flex items-center justify-between">
            <div class="font-medium">${w.channel_group || `Banga ${waves.indexOf(w) + 1}`} <span class="text-slate-500 ml-2">${(w.start_date||'')} ${w.end_date?('– '+w.end_date):''}</span></div>
            <div class="flex gap-2">
              <button class="w-del px-3 py-1.5 text-xs rounded-lg border border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100">Šalinti bangą</button>
            </div>
          </div>
          <div class="p-4">
            <!-- Excel-based wave item form -->
            <div class="bg-white rounded-lg border p-4 mb-4">
              <h4 class="font-medium text-slate-700 mb-3">Pridėti naują eilutę (Excel struktūra)</h4>
              
              <!-- Essential fields only -->
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
                <div>
                  <label class="block text-xs text-slate-600 mb-1">Kanalų grupė</label>
                  <select class="channel rounded border-slate-300 px-2 py-1 text-sm w-full">
                    <option value="">Pasirinkti kanalų grupę</option>
                  </select>
                </div>
                <div>
                  <label class="block text-xs text-slate-600 mb-1">Perkama TG</label>
                  <select class="tg rounded border-slate-300 px-2 py-1 text-sm w-full"></select>
                </div>
                <div>
                  <label class="block text-xs text-slate-600 mb-1">TVC (iš duomenų bazės)</label>
                  <select class="tvc-select rounded border-slate-300 px-2 py-1 text-sm w-full">
                    <option value="">Pasirinkti TVC</option>
                  </select>
                </div>
                <div>
                  <label class="block text-xs text-slate-600 mb-1">TRP perkami</label>
                  <input class="trps rounded border-slate-300 px-2 py-1 text-sm w-full" type="number" step="0.01" placeholder="35.14">
                </div>
              </div>
              
              <!-- Hidden advanced fields (default values) -->
              <div style="display: none;">
                <input class="channel-share" type="number" value="75">
                <input class="pt-zone-share" type="number" value="55">
                <input class="clip-duration" type="number" value="10">
                <input class="affinity1" type="number" value="">
                <input class="affinity2" type="number" value="">
              </div>
              
              <!-- Advanced fields (collapsible) -->
              <details class="mb-3">
                <summary class="cursor-pointer text-xs font-medium text-slate-700 mb-2">▼ Papildomi parametrai (default reikšmės)</summary>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2">
                  <div>
                    <label class="block text-xs text-slate-600 mb-1">Trukmės koef. <span class="text-emerald-600">(auto)</span></label>
                    <input class="duration-index rounded border-slate-300 px-2 py-1 text-xs w-full bg-emerald-50" type="number" step="0.01" value="1.25" placeholder="1.25" readonly title="Automatiškai užpildomas pagal TG ir TVC trukmę">
                  </div>
                  <div>
                    <label class="block text-xs text-slate-600 mb-1">Sezoninis koef. <span class="text-emerald-600">(auto)</span></label>
                    <input class="seasonal-index rounded border-slate-300 px-2 py-1 text-xs w-full bg-emerald-50" type="number" step="0.01" value="0.9" placeholder="0.9" readonly title="Automatiškai užpildomas pagal TG ir bangos mėnesį">
                  </div>
                  <div>
                    <label class="block text-xs text-slate-600 mb-1">TRP pirk. koef.</label>
                    <input class="trp-purchase-index rounded border-slate-300 px-2 py-1 text-xs w-full" type="number" step="0.01" value="0.95">
                  </div>
                  <div>
                    <label class="block text-xs text-slate-600 mb-1">Išankst. pirk. koef.</label>
                    <input class="advance-purchase-index rounded border-slate-300 px-2 py-1 text-xs w-full" type="number" step="0.01" value="0.95">
                  </div>
                  <div>
                    <label class="block text-xs text-slate-600 mb-1">Pozicijos koef.</label>
                    <input class="position-index rounded border-slate-300 px-2 py-1 text-xs w-full" type="number" step="0.01" value="1.0">
                  </div>
                </div>
              </details>
              
              <button class="i-add px-4 py-2 text-sm rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium">Pridėti Excel eilutę</button>
            </div>
            
            <div class="overflow-x-auto">
              <table class="min-w-full text-xs">
                <thead class="bg-slate-50 text-slate-700 border-b border-slate-200">
                  <tr>
                    <th class="text-left font-medium px-2 py-1">Kanalų grupė</th>
                    <th class="text-left font-medium px-2 py-1">Perkama TG</th>
                    <th class="text-left font-medium px-2 py-1">TVC</th>
                    <th class="text-left font-medium px-2 py-1">Trukmė</th>
                    <th class="text-left font-medium px-2 py-1">TG dydis (*000)</th>
                    <th class="text-left font-medium px-2 py-1">TG dalis (%)</th>
                    <th class="text-left font-medium px-2 py-1">TG imtis</th>
                    <th class="text-left font-medium px-2 py-1">Kanalo dalis</th>
                    <th class="text-left font-medium px-2 py-1">PT zonos dalis</th>
                    <th class="text-left font-medium px-2 py-1">GRP plan.</th>
                    <th class="text-left font-medium px-2 py-1">TRP perkamas</th>
                    <th class="text-left font-medium px-2 py-1">Affinity1</th>
                    <th class="text-left font-medium px-2 py-1">Gross CPP</th>
                    <th class="text-left font-medium px-2 py-1">Trukmės koeficientas</th>
                    <th class="text-left font-medium px-2 py-1">Sezoninis koeficientas</th>
                    <th class="text-left font-medium px-2 py-1">TRP pirkimo</th>
                    <th class="text-left font-medium px-2 py-1">Išankstinio pirkimo</th>
                    <th class="text-left font-medium px-2 py-1">WEB</th>
                    <th class="text-left font-medium px-2 py-1">Išankstinio mokėjimo</th>
                    <th class="text-left font-medium px-2 py-1">Lojalumo nuolaida</th>
                    <th class="text-left font-medium px-2 py-1">Pozicijos indeksas</th>
                    <th class="text-left font-medium px-2 py-1">Gross kaina</th>
                    <th class="text-left font-medium px-2 py-1 bg-blue-50">Kl. nuol. %</th>
                    <th class="text-left font-medium px-2 py-1">Net kaina</th>
                    <th class="text-left font-medium px-2 py-1 bg-blue-50">Ag. nuol. %</th>
                    <th class="text-left font-medium px-2 py-1">Net net kaina</th>
                    <th class="text-left font-medium px-2 py-1 w-32">Veiksmai</th>
                  </tr>
                </thead>
                <tbody class="items divide-y divide-slate-100"></tbody>
              </table>
            </div>
          </div>
        `;
        // Get form elements
        const channelSel = section.querySelector('.channel');
        const tgSel    = section.querySelector('.tg');
        const itemsTbody = section.querySelector('.items');

        // load channel groups (not individual channels)
        async function loadChannelGroups() {
          try {
            const groups = await fetchJSON('/tv-planner/channel-groups'); // Store globally
            channelSel.innerHTML = '<option value="">Pasirinkti kanalų grupę</option>';
            groups.forEach(group => {
              channelSel.innerHTML += `<option value="${group.name}">${group.name}</option>`;
            });
          } catch (e) {
            console.error('Error loading channel groups:', e);
          }
        }
        await loadChannelGroups();
        
        // Function to update auto indices based on TG and TVC selection
        async function updateAutoIndices(waveId, section) {
          const tgValue = section.querySelector('.tg')?.value;
          const tvcSelect = section.querySelector('.tvc');
          const durationInput = section.querySelector('.duration-index');
          const seasonalInput = section.querySelector('.seasonal-index');
          
          if (!tgValue || !tvcSelect?.value || !durationInput || !seasonalInput) {
            console.log('updateAutoIndices: Missing elements', {tgValue, tvcSelect: !!tvcSelect, durationInput: !!durationInput, seasonalInput: !!seasonalInput});
            return;
          }
          
          try {
            // Get selected TVC duration
            const selectedTVC = JSON.parse(tvcSelect.value);
            const duration = selectedTVC.duration || 30; // default 30 seconds
            
            const url = urlReplace(W_INDICES, waveId) + `?target_group=${encodeURIComponent(tgValue)}&duration_seconds=${duration}`;
            const response = await fetchJSON(url);
            
            if (response.status === 'ok') {
              durationInput.value = response.duration_index.toFixed(2);
              seasonalInput.value = response.seasonal_index.toFixed(2);
              
              // Update visual indicators
              durationInput.style.backgroundColor = response.duration_index !== 1.0 ? '#dcfce7' : '#f1f5f9';
              seasonalInput.style.backgroundColor = response.seasonal_index !== 1.0 ? '#dcfce7' : '#f1f5f9';
            }
          } catch (error) {
            console.error('Error updating auto indices:', error);
            // Keep default values if error
            durationInput.value = '1.25';
            seasonalInput.value = '0.90';
          }
        }

        // load target groups based on selected channel group  
        async function loadTargetGroups(channelGroupName) {
          if (!channelGroupName) {
            tgSel.innerHTML = '<option value="">Pirma pasirinkite kanalų grupę</option>';
            return;
          }
          try {
            // Get target groups from TRP rates for the selected channel group
            const tgs = await fetchJSON(`/tv-planner/trp?owner=${encodeURIComponent(channelGroupName)}`);
            
            // Store TRP rates data for later use
            window.currentTRPRates = tgs;
            
            // Extract unique target groups
            const uniqueTGs = [...new Set(tgs.map(item => item.target_group))];
            
            tgSel.innerHTML = uniqueTGs.map(t => `<option value="${t}">${t}</option>`).join('');
            if (uniqueTGs.length === 0) {
              tgSel.innerHTML = '<option value="">Nėra prieinamu TG šiai grupei</option>';
            }
          } catch (e) {
            console.error('Error loading target groups:', e);
            tgSel.innerHTML = '<option value="">Klaida kraunant TG</option>';
          }
        }
        
        // Auto-populate channel share and PT zone based on selected TG
        async function updateSharesFromTRP(channelGroupName, targetGroup) {
          if (!channelGroupName || !targetGroup || !window.currentTRPRates) return;
          
          // Find the TRP rate for this combination
          const rate = window.currentTRPRates.find(r => 
            r.owner === channelGroupName && r.target_group === targetGroup
          );
          
          if (rate) {
            // Update channel share (primary + secondary = 100%)
            const channelShareInput = section.querySelector('.channel-share');
            const ptZoneShareInput = section.querySelector('.pt-zone-share');
            
            // Use primary share as channel share percentage
            if (rate.share_primary) {
              channelShareInput.value = rate.share_primary.toFixed(1);
            }
            
            // Use prime share primary as PT zone share percentage  
            if (rate.prime_share_primary) {
              ptZoneShareInput.value = rate.prime_share_primary.toFixed(1);
            }
          }
        }
        
        // Update duration and seasonal indices from database (old format)
        async function updateIndicesFromDatabaseOld(targetGroup, duration, waveId, section) {
          if (!targetGroup || !duration || !waveId) return;
          
          const durationInput = section.querySelector('.duration-index');
          const seasonalInput = section.querySelector('.seasonal-index');
          
          if (!durationInput || !seasonalInput) return;
          
          try {
            const url = `/tv-planner/waves/${waveId}/indices?target_group=${encodeURIComponent(targetGroup)}&duration_seconds=${duration}`;
            console.log('DEBUG Indices: Requesting', {url, targetGroup, duration, waveId});
            
            const response = await fetchJSON(url);
            console.log('DEBUG Indices: Response', {response, targetGroup});
            
            if (response.status === 'ok') {
              durationInput.value = response.duration_index.toFixed(2);
              seasonalInput.value = response.seasonal_index.toFixed(2);
              
              console.log('DEBUG Indices: Updated values', {
                duration_index: response.duration_index,
                seasonal_index: response.seasonal_index,
                targetGroup,
                waveId
              });
              
              // Update visual indicators
              durationInput.style.backgroundColor = response.duration_index !== 1.0 ? '#dcfce7' : '#f1f5f9';
              seasonalInput.style.backgroundColor = response.seasonal_index !== 1.0 ? '#dcfce7' : '#f1f5f9';
            }
          } catch (error) {
            console.error('Error updating indices from database:', error);
          }
        }

        // Update duration and seasonal indices from database (new format)
        async function updateIndicesFromDatabase(targetGroup, duration) {
          if (!targetGroup || !duration || !window.currentWave) return;
          
          const durationInput = section.querySelector('.duration-index');
          const seasonalInput = section.querySelector('.seasonal-index');
          
          if (!durationInput || !seasonalInput) return;
          
          try {
            const url = `/tv-planner/waves/${window.currentWave.id}/indices?target_group=${encodeURIComponent(targetGroup)}&duration_seconds=${duration}`;
            const response = await fetchJSON(url);
            
            if (response.status === 'ok') {
              durationInput.value = response.duration_index.toFixed(2);
              seasonalInput.value = response.seasonal_index.toFixed(2);
              
              // Update visual indicators
              durationInput.style.backgroundColor = response.duration_index !== 1.0 ? '#dcfce7' : '#f1f5f9';
              seasonalInput.style.backgroundColor = response.seasonal_index !== 1.0 ? '#dcfce7' : '#f1f5f9';
            }
          } catch (error) {
            console.error('Error updating indices from database:', error);
          }
        }
        
        channelSel.addEventListener('change', () => loadTargetGroups(channelSel.value));
        
        // Update shares and indices when target group changes
        tgSel.addEventListener('change', () => {
          updateSharesFromTRP(channelSel.value, tgSel.value);
          const clipDurationInput = section.querySelector('.clip-duration');
          updateIndicesFromDatabase(tgSel.value, clipDurationInput ? clipDurationInput.value : 10);
        });
        
        // Update clip duration when TVC changes (hidden field)
        const tvcSelect = section.querySelector('.tvc-select');
        const clipDurationInput = section.querySelector('.clip-duration');
        
        tvcSelect.addEventListener('change', () => {
          const tvcId = tvcSelect.value;
          const targetGroup = tgSel.value;
          
          if (tvcId) {
            const selectedTVC = tvcs.find(tvc => tvc.id == tvcId);
            if (selectedTVC) {
              clipDurationInput.value = selectedTVC.duration;
              // Update indices when duration changes
              if (targetGroup) {
                updateIndicesFromDatabaseOld(targetGroup, selectedTVC.duration, w.id, section);
              }
            }
          } else {
            clipDurationInput.value = 10; // Default duration
            if (targetGroup) {
              updateIndicesFromDatabaseOld(targetGroup, 10, w.id, section);
            }
          }
        });
        
        // Update indices when clip duration is manually changed
        clipDurationInput.addEventListener('change', () => {
          const targetGroup = tgSel.value;
          if (targetGroup) {
            updateIndicesFromDatabaseOld(targetGroup, clipDurationInput.value, w.id, section);
          }
        });

        // Note: TVC selection will be handled by the global updateAllTVCSelections function

        // add item with all Excel fields
        section.querySelector('.i-add').addEventListener('click', async () => {
          const channelGroupName = channelSel.value;
          const targetGroup = tgSel.value;
          const trps = section.querySelector('.trps').value;
          
          if(!channelGroupName || !targetGroup || !trps){ 
            alert('Užpildykite kanalų grupę, tikslinę grupę ir TRP'); 
            return; 
          }
          
          // Collect all form data (visible and hidden with defaults)
          const tvcId = section.querySelector('.tvc-select').value;
          const selectedTVC = tvcs.find(tvc => tvc.id == tvcId);
          const clipDuration = selectedTVC ? selectedTVC.duration : 10;
          
          const formData = {
            channel_group: channelGroupName,
            target_group: targetGroup,
            trps: parseFloat(trps),
            // Hidden fields with default values
            channel_share: 0.75, // 75% default
            pt_zone_share: 0.55, // 55% default
            npt_zone_share: 0.45, // 45% default
            clip_duration: clipDuration,
            tvc_id: tvcId ? parseInt(tvcId) : 0,
            affinity1: 0, // Will be editable in resulting table
            affinity2: 0,
            // Advanced parameters with defaults
            duration_index: parseFloat(section.querySelector('.duration-index').value) || 1.25,
            seasonal_index: parseFloat(section.querySelector('.seasonal-index').value) || 0.9,
            trp_purchase_index: parseFloat(section.querySelector('.trp-purchase-index').value) || 0.95,
            advance_purchase_index: parseFloat(section.querySelector('.advance-purchase-index').value) || 0.95,
            position_index: parseFloat(section.querySelector('.position-index').value) || 1.0,
            client_discount: 0, // Default 0, will be edited in the table
            agency_discount: 0  // Default 0, will be edited in the table
          };
          
          try {
            await fetchJSON(urlReplace(I_CREATE, w.id), {
              method:'POST', headers:{'Content-Type':'application/json'},
              body: JSON.stringify(formData)
            });
            await reloadItems();
            
            // Clear form (only visible fields)
            section.querySelector('.trps').value = '';
            // affinity1 and affinity2 are now hidden - no need to clear
          } catch (error) {
            alert('Klaida pridedant eilutę: ' + error.message);
          }
        });

        // delete wave
        section.querySelector('.w-del').addEventListener('click', async () => {
          if(!confirm('Šalinti bangą?')) return;
          await fetchJSON(urlReplace(W_DELETE, w.id), { method:'DELETE' });
          await loadWaves(currentCampaign.id);
        });


        async function reloadItems(){
          const rows = await fetchJSON(urlReplace(I_LIST, w.id));
          itemsTbody.innerHTML = '';
          rows.forEach(r => {
            // Calculate derived values
            const grpPlanned = calculateGRP(r);
            const grossCpp = r.gross_cpp_eur || 0;
            const grossPrice = calculateGrossPrice(r, grossCpp);
            const netPrice = calculateNetPrice(grossPrice, r.client_discount || 0);
            const netNetPrice = calculateNetNetPrice(netPrice, r.agency_discount || 0);
            
            // Get TVC name if available
            const tvcName = r.tvc_id && tvcs.find(tvc => tvc.id == r.tvc_id)?.name || '-';
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td class="px-2 py-1 text-xs">${getChannelName(r.channel_id) || r.owner || '-'}</td>
              <td class="px-2 py-1 text-xs">${r.target_group || '-'}</td>
              <td class="px-2 py-1 text-xs bg-blue-50">${tvcName}</td>
              <td class="px-2 py-1 text-xs">${r.clip_duration || 10}</td>
              <td class="px-2 py-1 text-xs bg-green-50">${r.tg_size_thousands || '-'}</td>
              <td class="px-2 py-1 text-xs bg-green-50">${r.tg_share_percent ? r.tg_share_percent.toFixed(1) + '%' : '-'}</td>
              <td class="px-2 py-1 text-xs bg-green-50">${r.tg_sample_size || '-'}</td>
              <td class="px-2 py-1 text-xs">${(r.channel_share * 100).toFixed(1)}%</td>
              <td class="px-2 py-1 text-xs">${(r.pt_zone_share * 100).toFixed(1)}%</td>
              <td class="px-2 py-1 text-xs">${((r.npt_zone_share || 0.45) * 100).toFixed(1)}%</td>
              <td class="px-2 py-1 text-xs grp-planned">${grpPlanned.toFixed(2)}</td>
              <td class="px-2 py-1"><input class="itm-trps w-16 text-xs border rounded px-1 py-0.5 bg-purple-50" type="number" step="0.01" value="${r.trps || ''}" placeholder="TRP"></td>
              <td class="px-2 py-1"><input class="itm-affinity1 w-12 text-xs border rounded px-1 py-0.5 bg-purple-50" type="number" step="0.1" value="${r.affinity1 || ''}" placeholder="Affinity"></td>
              <td class="px-2 py-1 text-xs">€${grossCpp.toFixed(2)}</td>
              <td class="px-2 py-1 text-xs bg-yellow-50">${(r.duration_index || 1.25).toFixed(2)}</td>
              <td class="px-2 py-1 text-xs bg-yellow-50">${(r.seasonal_index || 0.9).toFixed(2)}</td>
              <td class="px-2 py-1"><input class="itm-trp-purchase w-12 text-xs border rounded px-1 py-0.5 bg-gray-100" type="number" step="0.01" value="${(r.trp_purchase_index || 0.95).toFixed(2)}" title="TRP pirkimo indeksas (default: 0.95)"></td>
              <td class="px-2 py-1"><input class="itm-advance-purchase w-12 text-xs border rounded px-1 py-0.5 bg-gray-100" type="number" step="0.01" value="${(r.advance_purchase_index || 0.95).toFixed(2)}" title="Išankstinio pirkimo indeksas (default: 0.95)"></td>
              <td class="px-2 py-1"><input class="itm-web w-12 text-xs border rounded px-1 py-0.5 bg-gray-100" type="number" step="0.01" value="${(r.web_index || 1.0).toFixed(2)}" title="WEB indeksas (default: 1.0)"></td>
              <td class="px-2 py-1"><input class="itm-advance-payment w-12 text-xs border rounded px-1 py-0.5 bg-gray-100" type="number" step="0.01" value="${(r.advance_payment_index || 1.0).toFixed(2)}" title="Išankstinio mokėjimo indeksas (default: 1.0)"></td>
              <td class="px-2 py-1"><input class="itm-loyalty-discount w-12 text-xs border rounded px-1 py-0.5 bg-gray-100" type="number" step="0.01" value="${(r.loyalty_discount_index || 1.0).toFixed(2)}" title="Lojalumo nuolaidos indeksas (default: 1.0)"></td>
              <td class="px-2 py-1"><input class="itm-position w-12 text-xs border rounded px-1 py-0.5 bg-gray-100" type="number" step="0.01" value="${(r.position_index || 1.0).toFixed(2)}" title="Pozicijos indeksas (default: 1.0)"></td>
              <td class="px-2 py-1 text-xs gross-price">€${grossPrice.toFixed(2)}</td>
              <td class="px-2 py-1"><input class="itm-client-discount w-12 text-xs border rounded px-1 py-0.5 bg-blue-50" type="number" step="0.1" min="0" max="100" value="${r.client_discount || 0}" title="Kliento nuolaida (%)"></td>
              <td class="px-2 py-1 text-xs net-price">€${netPrice.toFixed(2)}</td>
              <td class="px-2 py-1"><input class="itm-agency-discount w-12 text-xs border rounded px-1 py-0.5 bg-blue-50" type="number" step="0.1" min="0" max="100" value="${r.agency_discount || 0}" title="Agentūros nuolaida (%)"></td>
              <td class="px-2 py-1 text-xs net-net-price">€${netNetPrice.toFixed(2)}</td>
              <td class="px-2 py-1">
                <div class="flex gap-1">
                  <button class="itm-save px-2 py-0.5 text-xs rounded border border-emerald-300 bg-emerald-50 text-emerald-700">Saugoti</button>
                  <button class="itm-del px-2 py-0.5 text-xs rounded border border-rose-300 bg-rose-50 text-rose-700">X</button>
                </div>
              </td>
            `;
            // Add real-time price recalculation when discounts change
            const recalculatePrices = () => {
              // Get current values from inputs and stored data
              const trps = parseFloat(tr.querySelector('.itm-trps').value) || 0;
              const durationIndex = parseFloat(r.duration_index) || 1.0; // From original data
              const seasonalIndex = parseFloat(r.seasonal_index) || 1.0; // From original data  
              const trpPurchaseIndex = parseFloat(tr.querySelector('.itm-trp-purchase').value) || 0.95;
              const advancePurchaseIndex = parseFloat(tr.querySelector('.itm-advance-purchase').value) || 0.95;
              const webIndex = parseFloat(tr.querySelector('.itm-web').value) || 1.0;
              const advancePaymentIndex = parseFloat(tr.querySelector('.itm-advance-payment').value) || 1.0;
              const loyaltyDiscountIndex = parseFloat(tr.querySelector('.itm-loyalty-discount').value) || 1.0;
              const positionIndex = parseFloat(tr.querySelector('.itm-position').value) || 1.0;
              const clientDiscount = parseFloat(tr.querySelector('.itm-client-discount').value) || 0;
              const agencyDiscount = parseFloat(tr.querySelector('.itm-agency-discount').value) || 0;
              
              // Recalculate gross price with current values
              const itemData = {
                trps: trps,
                duration_index: durationIndex,
                seasonal_index: seasonalIndex,
                trp_purchase_index: trpPurchaseIndex,
                advance_purchase_index: advancePurchaseIndex,
                web_index: webIndex,
                advance_payment_index: advancePaymentIndex,
                loyalty_discount_index: loyaltyDiscountIndex,
                position_index: positionIndex
              };
              
              const newGrossPrice = calculateGrossPrice(itemData, grossCpp);
              const newNetPrice = calculateNetPrice(newGrossPrice, clientDiscount);
              const newNetNetPrice = calculateNetNetPrice(newNetPrice, agencyDiscount);
              
              // Update all displayed prices
              const grossPriceCell = tr.querySelector('.gross-price');
              const netPriceCell = tr.querySelector('.net-price');
              const netNetPriceCell = tr.querySelector('.net-net-price');
              
              if (grossPriceCell) grossPriceCell.innerHTML = `€${newGrossPrice.toFixed(2)}`;
              if (netPriceCell) netPriceCell.innerHTML = `€${newNetPrice.toFixed(2)}`;
              if (netNetPriceCell) netNetPriceCell.innerHTML = `€${newNetNetPrice.toFixed(2)}`;
            };
            
            // Function to recalculate and update GRP when TRP or affinity changes
            const recalculateGRP = () => {
              const trps = parseFloat(tr.querySelector('.itm-trps').value) || 0;
              const affinity1 = parseFloat(tr.querySelector('.itm-affinity1').value);
              
              let newGRP = 0;
              if (affinity1 && affinity1 !== 0 && trps > 0) {
                newGRP = trps * 100 / affinity1;
              }
              
              // Update the GRP display
              const grpCell = tr.querySelector('.grp-planned');
              if (grpCell) {
                grpCell.textContent = newGRP.toFixed(2);
              }
            };
            
            // Add event listeners for GRP recalculation
            tr.querySelector('.itm-trps').addEventListener('input', recalculateGRP);
            tr.querySelector('.itm-affinity1').addEventListener('input', recalculateGRP);
            
            // Add event listeners for price recalculation (any field that affects pricing)
            tr.querySelector('.itm-trps').addEventListener('input', recalculatePrices);
            tr.querySelector('.itm-trp-purchase').addEventListener('input', recalculatePrices);
            tr.querySelector('.itm-advance-purchase').addEventListener('input', recalculatePrices);
            tr.querySelector('.itm-web').addEventListener('input', recalculatePrices);
            tr.querySelector('.itm-advance-payment').addEventListener('input', recalculatePrices);
            tr.querySelector('.itm-loyalty-discount').addEventListener('input', recalculatePrices);
            tr.querySelector('.itm-position').addEventListener('input', recalculatePrices);
            tr.querySelector('.itm-client-discount').addEventListener('input', recalculatePrices);
            tr.querySelector('.itm-agency-discount').addEventListener('input', recalculatePrices);
            
            tr.querySelector('.itm-save').addEventListener('click', async () => {
              try {
                // Get only editable values
                const trps = parseFloat(tr.querySelector('.itm-trps').value) || 0;
                const affinity1 = parseFloat(tr.querySelector('.itm-affinity1').value) || 0;
                const trpPurchaseIndex = parseFloat(tr.querySelector('.itm-trp-purchase').value) || 0.95;
                const advancePurchaseIndex = parseFloat(tr.querySelector('.itm-advance-purchase').value) || 0.95;
                const webIndex = parseFloat(tr.querySelector('.itm-web').value) || 1.0;
                const advancePaymentIndex = parseFloat(tr.querySelector('.itm-advance-payment').value) || 1.0;
                const loyaltyDiscountIndex = parseFloat(tr.querySelector('.itm-loyalty-discount').value) || 1.0;
                const positionIndex = parseFloat(tr.querySelector('.itm-position').value) || 1.0;
                const clientDiscount = parseFloat(tr.querySelector('.itm-client-discount').value) || 0;
                const agencyDiscount = parseFloat(tr.querySelector('.itm-agency-discount').value) || 0;
                
                console.log('Saving wave item:', r.id, {
                  trps: trps,
                  affinity1: affinity1,
                  trp_purchase_index: trpPurchaseIndex,
                  advance_purchase_index: advancePurchaseIndex,
                  web_index: webIndex,
                  advance_payment_index: advancePaymentIndex,
                  loyalty_discount_index: loyaltyDiscountIndex,
                  position_index: positionIndex,
                  client_discount: clientDiscount,
                  agency_discount: agencyDiscount
                });
                
                const response = await fetchJSON(urlReplace(I_UPDATE, r.id), {
                  method:'PATCH', headers:{'Content-Type':'application/json'},
                  body: JSON.stringify({
                    trps: trps,
                    affinity1: affinity1,
                    trp_purchase_index: trpPurchaseIndex,
                    advance_purchase_index: advancePurchaseIndex,
                    web_index: webIndex,
                    advance_payment_index: advancePaymentIndex,
                    loyalty_discount_index: loyaltyDiscountIndex,
                    position_index: positionIndex,
                    client_discount: clientDiscount,
                    agency_discount: agencyDiscount
                  })
                });
                
                console.log('Save response:', response);
                
                await loadWaves(currentCampaign.id); // Reload to show updated calculations
                alert('Wave item išsaugotas');
              } catch (error) {
                console.error('Error saving wave item:', error);
                alert('Klaida išsaugant: ' + error.message);
              }
            });
            tr.querySelector('.itm-del').addEventListener('click', async () => {
              if(!confirm('Šalinti eilutę?')) return;
              
              try {
                console.log('Deleting item (itm-del):', r.id);
                await fetchJSON(urlReplace(I_DELETE, r.id), { method:'DELETE' });
                console.log('Item deleted, reloading waves...');
                await loadWaves(currentCampaign.id);
                console.log('Waves reloaded successfully');
              } catch (error) {
                console.error('Error during deletion:', error);
                alert('Klaida šalinant: ' + error.message);
              }
            });
            itemsTbody.appendChild(tr);
          });
        }

        await reloadItems();
        wavesDiv.appendChild(section);
        
        // Now add event listeners for auto-indices (after section is in DOM)
        const tgSelectForIndices = section.querySelector('.tg');
        const tvcSelectForIndices = section.querySelector('.tvc');
        
        if (tgSelectForIndices) {
          tgSelectForIndices.addEventListener('change', () => {
            // Use the new indices update system
            const clipDuration = section.querySelector('.clip-duration')?.value || 30;
            updateIndicesFromDatabaseOld(tgSelectForIndices.value, clipDuration, w.id, section);
          });
        }
        
        if (tvcSelectForIndices) {
          tvcSelectForIndices.addEventListener('change', () => {
            try {
              const selectedTVC = JSON.parse(tvcSelectForIndices.value);
              const duration = selectedTVC.duration || 30;
              const targetGroup = section.querySelector('.tg')?.value;
              if (targetGroup) {
                updateIndicesFromDatabaseOld(targetGroup, duration, w.id, section);
              }
            } catch (e) {
              console.error('Error parsing TVC selection:', e);
            }
          });
        }
        
        // Add listener for manual clip duration changes (old system)
        const clipDurationForIndices = section.querySelector('.clip-duration');
        if (clipDurationForIndices) {
          clipDurationForIndices.addEventListener('change', () => {
            const targetGroup = section.querySelector('.tg')?.value;
            if (targetGroup) {
              updateIndicesFromDatabaseOld(targetGroup, clipDurationForIndices.value, w.id, section);
            }
          });
        }
        
        } catch (error) {
          console.error('Error creating wave section:', error, w);
          // Create fallback simple wave display
          const fallbackSection = document.createElement('div');
          fallbackSection.className = "mb-4 p-4 border rounded bg-red-50";
          fallbackSection.innerHTML = `<div class="text-red-700">Klaida generuojant bangą: ${error.message}</div>`;
          wavesDiv.appendChild(fallbackSection);
        }
      }
      
      // Update TVC selections in all wave forms after loading all waves
      updateAllTVCSelections();
    }

    // TVC add button
    tvcAdd.addEventListener('click', createTVC);
    
    // Back to campaigns button
    const backBtn = document.querySelector('#backToCampaigns');
    if (backBtn) {
      backBtn.addEventListener('click', () => {
        currentCampaign = null;
        renderCurrentCampaign();
      });
    }
    
    // Add date validation to wave creation form
    const wStart = document.querySelector('#wStart');
    const wEnd = document.querySelector('#wEnd');
    
    if (wStart) {
      wStart.addEventListener('change', () => {
        if (wEnd && wStart.value) {
          wEnd.min = wStart.value; // End date cannot be before start date
        }
      });
    }
    
    if (wEnd) {
      wEnd.addEventListener('change', () => {
        if (wStart && wEnd.value) {
          wStart.max = wEnd.value; // Start date cannot be after end date
        }
      });
    }


    // Handle initial wave form
    const setupInitialWaveForm = async () => {
      const channelSelect = document.querySelector('#firstWaveChannel');
      const tgSelect = document.querySelector('#firstWaveTG');
      const tvcSelect = document.querySelector('#firstWaveTVC');
      const createBtn = document.querySelector('#createFirstWave');
      
      if (!channelSelect || !tgSelect || !tvcSelect || !createBtn) return;
      
      // Load channel groups
      try {
        const groups = await fetchJSON('/tv-planner/channel-groups');
        channelSelect.innerHTML = '<option value="">Pasirinkti kanalų grupę</option>';
        groups.forEach(group => {
          channelSelect.innerHTML += `<option value="${group.name}">${group.name}</option>`;
        });
      } catch (e) {
        console.error('Error loading channel groups:', e);
      }
      
      // Update TVC selection
      const updateTVCSelection = () => {
        tvcSelect.innerHTML = '<option value="">Pasirinkti TVC</option>';
        if (tvcs && tvcs.length > 0) {
          tvcs.forEach(tvc => {
            tvcSelect.innerHTML += `<option value="${tvc.id}">${tvc.name} (${tvc.duration} sek.)</option>`;
          });
        }
      };
      
      // Listen for TVC updates
      window.updateInitialFormTVCs = updateTVCSelection;
      
      // Add date validation listeners
      const startDateInput = document.querySelector('#firstWaveStart');
      const endDateInput = document.querySelector('#firstWaveEnd');
      
      if (startDateInput) {
        startDateInput.addEventListener('change', () => {
          if (endDateInput && startDateInput.value) {
            endDateInput.min = startDateInput.value; // End date cannot be before start date
          }
        });
      }
      
      if (endDateInput) {
        endDateInput.addEventListener('change', () => {
          if (startDateInput && endDateInput.value) {
            startDateInput.max = endDateInput.value; // Start date cannot be after end date
          }
        });
      }
      
      // Handle channel selection
      channelSelect.addEventListener('change', async () => {
        const channelGroupName = channelSelect.value;
        if (!channelGroupName) {
          tgSelect.innerHTML = '<option value="">Pirma pasirinkite kanalų grupę</option>';
          return;
        }
        
        try {
          const tgs = await fetchJSON(`/tv-planner/trp?owner=${encodeURIComponent(channelGroupName)}`);
          const uniqueTGs = [...new Set(tgs.map(item => item.target_group))];
          
          tgSelect.innerHTML = uniqueTGs.map(t => `<option value="${t}">${t}</option>`).join('');
          if (uniqueTGs.length === 0) {
            tgSelect.innerHTML = '<option value="">Nėra prieinamu TG šiai grupei</option>';
          }
        } catch (e) {
          console.error('Error loading target groups:', e);
          tgSelect.innerHTML = '<option value="">Klaida kraunant TG</option>';
        }
      });
      
      // Handle wave creation (adds row to table)
      createBtn.addEventListener('click', async () => {
        if (!currentCampaign) {
          alert('Pirma pasirinkite kampaniją');
          return;
        }
        
        const startDate = document.querySelector('#firstWaveStart').value;
        const endDate = document.querySelector('#firstWaveEnd').value;
        const channelGroup = channelSelect.value;
        const targetGroup = tgSelect.value;
        const tvcId = tvcSelect.value;
        const trps = parseFloat(document.querySelector('#firstWaveTRP').value) || 0;
        
        if (!startDate || !endDate) {
          alert('Prašome pasirinkti bangos pradžios ir pabaigos datas');
          return;
        }
        
        if (!channelGroup || !targetGroup || !trps) {
          alert('Užpildykite kanalų grupę, tikslinę grupę ir TRP');
          return;
        }
        
        if (startDate > endDate) {
          alert('Pradžios data negali būti vėlesnė nei pabaigos data');
          return;
        }
        
        // Validate dates are within campaign period
        if (currentCampaign.start_date && startDate < currentCampaign.start_date) {
          alert(`Bangos pradžia negali būti anksčiau nei kampanijos pradžia (${currentCampaign.start_date})`);
          return;
        }
        if (currentCampaign.end_date && endDate > currentCampaign.end_date) {
          alert(`Bangos pabaiga negali būti vėliau nei kampanijos pabaiga (${currentCampaign.end_date})`);
          return;
        }
        
        try {
          // Each row is its own wave, so always create a new wave
          // Refresh wave count to ensure we start from 1 if no waves exist
          const freshWaves = await fetchJSON(urlReplace(W_LIST, currentCampaign.id));
          const waveCount = freshWaves ? freshWaves.length + 1 : 1;
          
          // Create new wave for this row
          const waveResponse = await fetchJSON(urlReplace(W_CREATE, currentCampaign.id), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              name: `Banga ${waveCount}`,
              start_date: startDate,
              end_date: endDate
            })
          });
          
          if (!waveResponse || !waveResponse.id) {
            throw new Error('Failed to create wave');
          }
          
          const waveId = waveResponse.id;
          
          if (waveId) {
            // Create first item in the wave
            const selectedTVC = tvcs.find(tvc => tvc.id == tvcId);
            const clipDuration = selectedTVC ? selectedTVC.duration : 10;
            
            await fetchJSON(urlReplace(I_CREATE, waveId), {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                channel_group: channelGroup || '',
                target_group: targetGroup || '',
                trps: trps || 0,
                channel_share: 0.75,
                pt_zone_share: 0.55,
                npt_zone_share: 0.45,
                clip_duration: clipDuration || 30,
                tvc_id: tvcId ? parseInt(tvcId) : 0,
                affinity1: 0, // Changed from null to 0
                affinity2: 0, // Changed from null to 0
                duration_index: 1.25,
                seasonal_index: 0.9,
                trp_purchase_index: 0.95,
                advance_purchase_index: 0.95,
                position_index: 1.0,
                client_discount: 0,
                agency_discount: 0,
                // Add these fields to prevent null issues
                tg_size_thousands: 0,
                tg_share_percent: 0,
                tg_sample_size: 0,
                gross_cpp_eur: 0
              })
            });
            
            // Clear form for next entry
            document.querySelector('#firstWaveStart').value = '';
            document.querySelector('#firstWaveEnd').value = '';
            document.querySelector('#firstWaveTRP').value = '';
            channelSelect.value = '';
            tgSelect.innerHTML = '<option value="">Pirma pasirinkite kanalų grupę</option>';
            tvcSelect.value = '';
            
            // Reload waves to show new row in table
            await loadWaves(currentCampaign.id);
          }
        } catch (error) {
          alert('Klaida kuriant bangą: ' + error.message);
        }
      });
    };
    
    // initial boot
    (async () => {
      await loadCampaigns();
      await setupInitialWaveForm();
    })();
  });
})();
