// static/js/campaigns_admin.js
(() => {
  'use strict';

  window.addEventListener('DOMContentLoaded', () => {
    const dataDiv = document.querySelector('[data-pl-list]');
    const PL_LIST   = dataDiv.dataset.plList;
    const PL_OWNERS = dataDiv.dataset.plOwnersBase;   // ends with /0
    const PL_TARGETS= dataDiv.dataset.plTargetsBase;  // ends with /0

    const C_LIST    = dataDiv.dataset.cList;
    const C_CREATE  = dataDiv.dataset.cCreate;
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

    const $ = s => document.querySelector(s);
    const cTbody = $('#cTbody');
    const cName = $('#cName'), cPL = $('#cPL'), cStart = $('#cStart'), cEnd = $('#cEnd');
    const cAgency = $('#cAgency'), cClient = $('#cClient'), cProduct = $('#cProduct');
    const cCountry = $('#cCountry'), cSplitRatio = $('#cSplitRatio');
    const cCreate = $('#cCreate');

    const wavePanel = $('#wavePanel');
    const wavesDiv  = $('#waves');
    const noCampaign = $('#noCampaign');
    
    const tvcName = $('#tvcName'), tvcDuration = $('#tvcDuration');
    const tvcAdd = $('#tvcAdd'), tvcList = $('#tvcList');

    let lists = [];     // pricing lists
    let campaigns = []; // campaigns
    let currentCampaign = null;
    let tvcs = [];      // TVCs for current campaign
    let filteredCampaignId = null; // ID of campaign to show exclusively
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
      // GRP = TRP * channel_share * pt_zone_share
      const trps = parseFloat(item.trps) || 0;
      const channelShare = parseFloat(item.channel_share) || 0.75;
      const ptZoneShare = parseFloat(item.pt_zone_share) || 0.55;
      return trps * channelShare * ptZoneShare;
    }

    function calculateGrossPrice(item, grossCpp) {
      // Gross Price = TRP * Gross CPP * duration * duration_index * seasonal_index * trp_purchase_index * advance_purchase_index * position_index
      // Note: duration_index and seasonal_index come from database (pricing list), not from form
      const trps = parseFloat(item.trps) || 0;
      const cpp = parseFloat(grossCpp) || 0;
      const duration = parseInt(item.clip_duration) || 10;
      const durationIndex = parseFloat(item.duration_index) || 1.0; // From DB
      const seasonalIndex = parseFloat(item.seasonal_index) || 1.0; // From DB
      const trpPurchaseIndex = parseFloat(item.trp_purchase_index) || 0.95;
      const advancePurchaseIndex = parseFloat(item.advance_purchase_index) || 0.95;
      const positionIndex = parseFloat(item.position_index) || 1.0;
      
      return trps * cpp * duration * durationIndex * seasonalIndex * trpPurchaseIndex * advancePurchaseIndex * positionIndex;
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

    // -------- load pricing lists into select --------
    async function loadPricingLists(){
      lists = await fetchJSON(PL_LIST);
      cPL.innerHTML = '';
      lists.forEach(l => {
        const opt = document.createElement('option');
        opt.value = l.id; opt.textContent = l.name;
        cPL.appendChild(opt);
      });
    }

    // -------- campaigns table --------
    function filterCampaign(campaignId) {
      filteredCampaignId = campaignId;
      renderCampaigns();
    }
    
    function clearFilter() {
      filteredCampaignId = null;
      renderCampaigns();
    }
    
    function renderCampaigns(){
      cTbody.innerHTML = '';
      
      // Filter campaigns if needed
      const campaignsToShow = filteredCampaignId 
        ? campaigns.filter(c => c.id === filteredCampaignId)
        : campaigns;
      
      // Add a clear filter button if filter is active
      if(filteredCampaignId && campaignsToShow.length > 0) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td colspan="6" class="px-4 py-2 bg-yellow-50">
            <div class="flex items-center justify-between">
              <span class="text-sm text-yellow-700">Rodoma tik pasirinkta kampanija</span>
              <button class="clear-filter px-3 py-1 text-xs rounded-lg border border-yellow-300 bg-yellow-100 text-yellow-700 hover:bg-yellow-200">Rodyti visas kampanijas</button>
            </div>
          </td>`;
        tr.querySelector('.clear-filter').addEventListener('click', clearFilter);
        cTbody.appendChild(tr);
      }
      
      campaignsToShow.forEach(c => {
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
              <a href="/tv-planner/campaigns/${c.id}/export/client-excel" class="export-client px-3 py-1.5 text-xs rounded-lg border border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 no-underline inline-block">Excel klientui</a>
              <a href="/tv-planner/campaigns/${c.id}/export/agency-csv" class="export-agency px-3 py-1.5 text-xs rounded-lg border border-blue-300 bg-blue-50 text-blue-700 hover:bg-blue-100 no-underline inline-block">CSV agentūrai</a>
              <button class="del px-3 py-1.5 text-xs rounded-lg border border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100">Šalinti</button>
            </div>
          </td>`;
        tr.querySelector('.open').addEventListener('click', () => openCampaign(c));
        tr.querySelector('.del').addEventListener('click', async () => {
          if(!confirm('Šalinti kampaniją?')) return;
          await fetchJSON(urlReplace(C_DELETE, c.id), { method: 'DELETE' });
          await loadCampaigns();
          if(currentCampaign && currentCampaign.id === c.id){
            currentCampaign = null;
            renderCurrentCampaign();
          }
          // Clear filter if we deleted the filtered campaign
          if(filteredCampaignId === c.id) {
            clearFilter();
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

    async function loadCampaigns(){
      campaigns = await fetchJSON(C_LIST);
      renderCampaigns();
    }

    cCreate.addEventListener('click', async () => {
      const name = cName.value.trim();
      const pricing_list_id = +cPL.value;
      const start_date = cStart.value || null;
      const end_date   = cEnd.value || null;
      const agency = cAgency.value.trim();
      const client = cClient.value.trim();
      const product = cProduct.value.trim();
      const country = cCountry.value.trim() || 'Lietuva';
      const split_ratio = cSplitRatio.value.trim() || '70:30';
      
      if(!name || !pricing_list_id){ alert('Įveskite pavadinimą ir parinkite kainoraštį'); return; }
      
      const response = await fetchJSON(C_CREATE, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ 
          name, pricing_list_id, start_date, end_date,
          agency, client, product, country, split_ratio
        })
      });
      
      // Clear form (except agency which is fixed)
      cName.value=''; cStart.value=''; cEnd.value='';
      cClient.value=''; cProduct.value='';
      cCountry.value='Lietuva'; cSplitRatio.value='70:30';
      
      await loadCampaigns();
      
      // Automatically open the newly created campaign
      if(response && response.id) {
        const newCampaign = campaigns.find(c => c.id === response.id);
        if(newCampaign) {
          openCampaign(newCampaign);
          // Filter to show only this campaign
          filterCampaign(response.id);
        }
      }
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
    }

    function updateAllTVCSelections() {
      const tvcSelects = wavesDiv.querySelectorAll('.tvc-select');
      tvcSelects.forEach(select => {
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
      if(!currentCampaign){
        wavePanel.classList.add('hidden');
        noCampaign.classList.remove('hidden');
        wavesDiv.innerHTML = '';
        return;
      }
      wavePanel.classList.remove('hidden');
      noCampaign.classList.add('hidden');
      loadTVCs(currentCampaign.id);  // Load TVCs when campaign opens
      loadWaves(currentCampaign.id);
      renderCampaignCalendar(); // Render calendar when campaign opens
    }
    
    function renderCampaignCalendar() {
      const calendarDiv = document.querySelector('#campaignCalendar');
      if (!calendarDiv || !currentCampaign) return;
      
      // Generate calendar based on campaign dates
      const startDate = currentCampaign.start_date ? new Date(currentCampaign.start_date) : new Date();
      const endDate = currentCampaign.end_date ? new Date(currentCampaign.end_date) : new Date(startDate.getTime() + 30 * 24 * 60 * 60 * 1000); // 30 days default
      
      let html = '<div class="calendar-grid">';
      
      // Generate weeks header
      html += '<div class="grid grid-cols-7 gap-1 text-xs font-medium text-slate-600 mb-2">';
      const weekDays = ['Pr', 'An', 'Tr', 'Ke', 'Pe', 'Še', 'Sk'];
      weekDays.forEach(day => {
        html += `<div class="text-center">${day}</div>`;
      });
      html += '</div>';
      
      // Generate calendar days
      html += '<div class="grid grid-cols-7 gap-1">';
      
      // Start from Monday of the first week
      const firstDay = new Date(startDate);
      const dayOfWeek = firstDay.getDay();
      const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
      firstDay.setDate(firstDay.getDate() + mondayOffset);
      
      // Generate calendar cells
      const currentDate = new Date(firstDay);
      const waveColors = ['bg-green-100', 'bg-purple-100', 'bg-yellow-100', 'bg-pink-100', 'bg-indigo-100'];
      
      while (currentDate <= endDate || currentDate.getDay() !== 1) {
        const isInRange = currentDate >= startDate && currentDate <= endDate;
        const isToday = currentDate.toDateString() === new Date().toDateString();
        const dateStr = currentDate.toISOString().split('T')[0];
        
        // Check if date is in any wave period
        let waveIndex = -1;
        let isInWave = false;
        if (currentWaves) {
          for (let i = 0; i < currentWaves.length; i++) {
            const wave = currentWaves[i];
            if (wave.start_date && wave.end_date) {
              const waveStart = new Date(wave.start_date);
              const waveEnd = new Date(wave.end_date);
              if (currentDate >= waveStart && currentDate <= waveEnd) {
                isInWave = true;
                waveIndex = i;
                break;
              }
            }
          }
        }
        
        let cellClass = 'p-2 text-center text-xs rounded ';
        if (isInWave) {
          cellClass += `${waveColors[waveIndex % waveColors.length]} hover:opacity-80 cursor-pointer `;
        } else if (isInRange) {
          cellClass += 'bg-blue-50 hover:bg-blue-100 cursor-pointer ';
        } else {
          cellClass += 'bg-gray-50 text-gray-400 ';
        }
        if (isToday) {
          cellClass += 'ring-2 ring-blue-500 ';
        }
        
        html += `<div class="${cellClass}" data-date="${dateStr}" title="${isInWave ? currentWaves[waveIndex].name : ''}" onclick="toggleDateSelection('${dateStr}')">
                   ${currentDate.getDate()}
                 </div>`;
        
        currentDate.setDate(currentDate.getDate() + 1);
        
        // Break if we've completed a full week after the end date
        if (currentDate > endDate && currentDate.getDay() === 1) {
          break;
        }
      }
      
      html += '</div>';
      html += '</div>';
      
      // Add wave legend if there are waves
      if (currentWaves && currentWaves.length > 0) {
        html += '<div class="mt-4 pt-4 border-t border-slate-200">';
        html += '<div class="text-xs text-slate-600">';
        html += '<div class="font-medium mb-2">Bangos:</div>';
        const waveColors = ['bg-green-100', 'bg-purple-100', 'bg-yellow-100', 'bg-pink-100', 'bg-indigo-100'];
        currentWaves.forEach((wave, index) => {
          if (wave.start_date && wave.end_date) {
            html += `<div class="flex items-center gap-2 mb-1">
                      <div class="w-3 h-3 rounded ${waveColors[index % waveColors.length]}"></div>
                      <span>${wave.name || 'Banga ' + (index + 1)}: ${wave.start_date} - ${wave.end_date}</span>
                     </div>`;
          }
        });
        html += '</div>';
        html += '</div>';
      }
      
      // Add TRP distribution controls
      html += '<div class="mt-4 pt-4 border-t border-slate-200">';
      html += '<div class="text-xs">';
      html += '<div class="font-medium mb-2">TRP paskirstymas:</div>';
      html += '<div class="text-xs text-slate-500 mb-2">💡 Sistema automatiškai naudoja bangų datas arba galite pažymėti dieną rankomis</div>';
      html += '<div class="mb-2">';
      html += '<input id="trpValue" type="number" step="0.01" placeholder="Įveskite TRP" class="w-20 px-2 py-1 text-xs border rounded mr-2">';
      html += '<button onclick="distributeTRP()" class="px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600">Paskirstyti</button>';
      html += '</div>';
      html += '<div id="selectedDates" class="text-xs text-slate-600 mb-2"></div>';
      html += '<div id="dailyWeight" class="text-xs font-medium text-emerald-700"></div>';
      html += '</div>';
      
      // Add campaign info
      html += '<div class="mt-2 pt-2 border-t border-slate-200">';
      html += '<div class="text-xs text-slate-600">';
      html += `<div class="mb-1"><strong>Kampanija:</strong> ${currentCampaign.name}</div>`;
      html += `<div class="mb-1"><strong>Pradžia:</strong> ${currentCampaign.start_date || 'Nenustatyta'}</div>`;
      html += `<div><strong>Pabaiga:</strong> ${currentCampaign.end_date || 'Nenustatyta'}</div>`;
      html += '</div>';
      html += '</div>';
      
      calendarDiv.innerHTML = html;
    }

    // -------- TRP Distribution functions --------
    let selectedDates = new Set();
    
    function toggleDateSelection(dateStr) {
      if (selectedDates.has(dateStr)) {
        selectedDates.delete(dateStr);
      } else {
        selectedDates.add(dateStr);
      }
      
      // Update visual selection
      const calendarDiv = document.querySelector('#campaignCalendar');
      const dateCell = calendarDiv.querySelector(`[data-date="${dateStr}"]`);
      if (dateCell) {
        if (selectedDates.has(dateStr)) {
          dateCell.classList.add('bg-yellow-200', 'border-2', 'border-yellow-400');
        } else {
          dateCell.classList.remove('bg-yellow-200', 'border-2', 'border-yellow-400');
        }
      }
      
      updateSelectedDatesDisplay();
    }
    
    function updateSelectedDatesDisplay() {
      const selectedDatesDiv = document.querySelector('#selectedDates');
      if (selectedDatesDiv) {
        if (selectedDates.size > 0) {
          const sortedDates = Array.from(selectedDates).sort();
          selectedDatesDiv.innerHTML = `Pasirinktos dienos (${selectedDates.size}): ${sortedDates.join(', ')}`;
        } else {
          selectedDatesDiv.innerHTML = 'Nepasirinkta nei vienos dienos';
        }
      }
    }
    
    window.distributeTRP = function() {
      const trpInput = document.querySelector('#trpValue');
      const dailyWeightDiv = document.querySelector('#dailyWeight');
      
      if (!trpInput || !dailyWeightDiv) return;
      
      const totalTRP = parseFloat(trpInput.value);
      if (!totalTRP || totalTRP <= 0) {
        alert('Įveskite teisingą TRP reikšmę');
        return;
      }
      
      // Auto-select wave dates if no manual selection
      if (selectedDates.size === 0 && currentWaves.length > 0) {
        // Auto-populate with all wave dates
        currentWaves.forEach(wave => {
          if (wave.start_date && wave.end_date) {
            const waveStart = new Date(wave.start_date);
            const waveEnd = new Date(wave.end_date);
            
            // Add all dates in wave range
            const currentDate = new Date(waveStart);
            while (currentDate <= waveEnd) {
              const dateStr = currentDate.toISOString().split('T')[0];
              selectedDates.add(dateStr);
              currentDate.setDate(currentDate.getDate() + 1);
            }
          }
        });
        
        // Update display
        updateSelectedDatesDisplay();
        
        // Refresh calendar to show selection
        renderCampaignCalendar();
      }
      
      if (selectedDates.size === 0) {
        alert('Nėra bangų datų arba pasirinkite bent vieną dieną kalendoriuje');
        return;
      }
      
      const dailyWeight = totalTRP / selectedDates.size;
      dailyWeightDiv.innerHTML = `Daily svoris: ${dailyWeight.toFixed(2)} TRP per dieną (${totalTRP} TRP ÷ ${selectedDates.size} dienos)`;
      
      // Here you could save this distribution to the database
      console.log('TRP Distribution:', {
        totalTRP: totalTRP,
        selectedDates: Array.from(selectedDates),
        dailyWeight: dailyWeight
      });
    };

    function openCampaign(c){
      currentCampaign = c;
      renderCurrentCampaign();
    }

    // -------- waves + items --------
    let currentWaves = []; // Store waves for calendar display
    
    async function loadWaves(cid){
      const waves = await fetchJSON(urlReplace(W_LIST, cid));
      currentWaves = waves; // Store for calendar
      
      // Clear waves div
      wavesDiv.innerHTML = '';
      
      // If no waves, show message
      if (!waves || waves.length === 0) {
        wavesDiv.innerHTML = '<div class="text-center text-gray-500 py-8">Nėra sukurtų bangų. Sukurkite bangą naudodami formą viršuje.</div>';
        renderCampaignCalendar();
        return;
      }
      
      // Update calendar with wave information
      renderCampaignCalendar();
      
      for(const w of waves){
        const section = document.createElement('div');
        section.className = "mb-8 border border-slate-200 rounded-xl overflow-hidden";
        
        try {
        section.innerHTML = `
          <div class="px-4 py-3 bg-slate-50 flex items-center justify-between">
            <div class="font-medium">${w.name || '(be pavadinimo)'} <span class="text-slate-500 ml-2">${(w.start_date||'')} ${w.end_date?('– '+w.end_date):''}</span></div>
            <div class="flex gap-2">
              <button class="w-del px-3 py-1.5 text-xs rounded-lg border border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100">Šalinti bangą</button>
            </div>
          </div>
          <div class="p-4">
            <!-- Excel-based wave item form -->
            <div class="bg-white rounded-lg border p-4 mb-4">
              <h4 class="font-medium text-slate-700 mb-3">Pridėti naują eilutę (Excel struktūra)</h4>
              
              <!-- Basic fields row 1 -->
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
                  <label class="block text-xs text-slate-600 mb-1">Pagrindinio kanalo dalis (%)</label>
                  <input class="channel-share rounded border-slate-300 px-2 py-1 text-sm w-full" type="number" step="0.1" value="75" placeholder="75">
                </div>
                <div>
                  <label class="block text-xs text-slate-600 mb-1">PT zonos dalis (%)</label>
                  <input class="pt-zone-share rounded border-slate-300 px-2 py-1 text-sm w-full" type="number" step="0.1" value="55" placeholder="55">
                </div>
              </div>
              
              <!-- Basic fields row 2 -->
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
                <div>
                  <label class="block text-xs text-slate-600 mb-1">TVC (iš duomenų bazės)</label>
                  <select class="tvc-select rounded border-slate-300 px-2 py-1 text-sm w-full">
                    <option value="">Pasirinkti TVC</option>
                  </select>
                </div>
                <div>
                  <label class="block text-xs text-slate-600 mb-1">Klipo trukmė (sek.) - automatiškai</label>
                  <input class="clip-duration rounded border-slate-300 px-2 py-1 text-sm w-full bg-gray-100" type="number" value="10" readonly>
                </div>
                <div>
                  <label class="block text-xs text-slate-600 mb-1">TRP perkami</label>
                  <input class="trps rounded border-slate-300 px-2 py-1 text-sm w-full" type="number" step="0.01" placeholder="35.14">
                </div>
                <div>
                  <label class="block text-xs text-slate-600 mb-1">Affinity 1</label>
                  <input class="affinity1 rounded border-slate-300 px-2 py-1 text-sm w-full" type="number" step="0.1" placeholder="88.2">
                </div>
                <div>
                  <label class="block text-xs text-slate-600 mb-1">Affinity 2</label>
                  <input class="affinity2 rounded border-slate-300 px-2 py-1 text-sm w-full" type="number" step="0.1">
                </div>
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
                  <div>
                    <label class="block text-xs text-slate-600 mb-1">Kliento nuolaida (% - iš apatinės sekcijos)</label>
                    <div class="px-2 py-1 text-xs bg-gray-100 rounded border">Valdoma apacioje</div>
                  </div>
                  <div>
                    <label class="block text-xs text-slate-600 mb-1">Agentūros nuolaida (% - iš apatinės sekcijos)</label>
                    <div class="px-2 py-1 text-xs bg-gray-100 rounded border">Valdoma apacioje</div>
                  </div>
                </div>
              </details>
              
              <button class="i-add px-4 py-2 text-sm rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium">Pridėti Excel eilutę</button>
            </div>
            <!-- Discounts Section -->
            <div class="mb-4 p-3 bg-slate-50 rounded-lg">
              <h4 class="text-sm font-medium text-slate-700 mb-2">Nuolaidos</h4>
              <div class="grid md:grid-cols-3 gap-3 items-end">
                <div>
                  <label class="block text-xs text-slate-600 mb-1">Kliento nuolaida (%)</label>
                  <input class="client-discount w-full rounded border-slate-300 px-2 py-1 text-sm" type="number" step="0.1" min="0" max="100" placeholder="0">
                </div>
                <div>
                  <label class="block text-xs text-slate-600 mb-1">Agentūros nuolaida (%)</label>
                  <input class="agency-discount w-full rounded border-slate-300 px-2 py-1 text-sm" type="number" step="0.1" min="0" max="100" placeholder="0">
                </div>
                <div class="flex gap-2">
                  <button class="save-discounts px-3 py-1 text-xs rounded-lg border border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100">Išsaugoti nuolaidas</button>
                </div>
              </div>
              <div class="wave-costs mt-2 text-xs text-slate-600"></div>
            </div>
            
            <div class="overflow-x-auto">
              <table class="min-w-full text-xs">
                <thead class="bg-slate-50 text-slate-700 border-b border-slate-200">
                  <tr>
                    <th class="text-left font-medium px-2 py-1">Kanalų grupė</th>
                    <th class="text-left font-medium px-2 py-1">Perkama TG</th>
                    <th class="text-left font-medium px-2 py-1">TVC</th>
                    <th class="text-left font-medium px-2 py-1">TG dydis (*000)</th>
                    <th class="text-left font-medium px-2 py-1">TG dalis (%)</th>
                    <th class="text-left font-medium px-2 py-1">TG imtis</th>
                    <th class="text-left font-medium px-2 py-1">Kanalo dalis</th>
                    <th class="text-left font-medium px-2 py-1">PT zonos dalis</th>
                    <th class="text-left font-medium px-2 py-1">Trukmė</th>
                    <th class="text-left font-medium px-2 py-1">GRP plan.</th>
                    <th class="text-left font-medium px-2 py-1">TRP perk.</th>
                    <th class="text-left font-medium px-2 py-1">Affinity1</th>
                    <th class="text-left font-medium px-2 py-1">Gross CPP</th>
                    <th class="text-left font-medium px-2 py-1">Trukm.koef</th>
                    <th class="text-left font-medium px-2 py-1">Sez.koef</th>
                    <th class="text-left font-medium px-2 py-1">TRP pirk.</th>
                    <th class="text-left font-medium px-2 py-1">Išank.</th>
                    <th class="text-left font-medium px-2 py-1">Pozic.</th>
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
          const tgValue = section.querySelector('.tg').value;
          const tvcSelect = section.querySelector('.tvc');
          const durationInput = section.querySelector('.duration-index');
          const seasonalInput = section.querySelector('.seasonal-index');
          
          if (!tgValue || !tvcSelect.value || !W_INDICES) return;
          
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
        
        channelSel.addEventListener('change', () => loadTargetGroups(channelSel.value));
        
        // Update shares when target group changes
        tgSel.addEventListener('change', () => {
          updateSharesFromTRP(channelSel.value, tgSel.value);
        });
        
        // Update clip duration when TVC changes
        const tvcSelect = section.querySelector('.tvc-select');
        const clipDurationInput = section.querySelector('.clip-duration');
        
        tvcSelect.addEventListener('change', () => {
          const tvcId = tvcSelect.value;
          if (tvcId) {
            const selectedTVC = tvcs.find(tvc => tvc.id == tvcId);
            if (selectedTVC) {
              clipDurationInput.value = selectedTVC.duration;
            }
          } else {
            clipDurationInput.value = 10; // Default duration
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
          
          // Collect all form data
          const tvcId = section.querySelector('.tvc-select').value;
          const formData = {
            channel_group: channelGroupName,
            target_group: targetGroup,
            trps: parseFloat(trps),
            channel_share: (parseFloat(section.querySelector('.channel-share').value) || 75) / 100, // Convert % to decimal
            pt_zone_share: (parseFloat(section.querySelector('.pt-zone-share').value) || 55) / 100, // Convert % to decimal
            clip_duration: parseInt(section.querySelector('.clip-duration').value) || 10,
            tvc_id: tvcId ? parseInt(tvcId) : null,
            affinity1: parseFloat(section.querySelector('.affinity1').value) || null,
            affinity2: parseFloat(section.querySelector('.affinity2').value) || null,
            duration_index: parseFloat(section.querySelector('.duration-index').value) || 1.25,
            seasonal_index: parseFloat(section.querySelector('.seasonal-index').value) || 0.9,
            trp_purchase_index: parseFloat(section.querySelector('.trp-purchase-index').value) || 0.95,
            advance_purchase_index: parseFloat(section.querySelector('.advance-purchase-index').value) || 0.95,
            position_index: parseFloat(section.querySelector('.position-index').value) || 1.0,
            client_discount: 0, // Will be set via discount management section below
            agency_discount: 0  // Will be set via discount management section below
          };
          
          try {
            await fetchJSON(urlReplace(I_CREATE, w.id), {
              method:'POST', headers:{'Content-Type':'application/json'},
              body: JSON.stringify(formData)
            });
            await reloadItems();
            await updateCostDisplay();
            
            // Clear form
            section.querySelector('.trps').value = '';
            section.querySelector('.affinity1').value = '';
            section.querySelector('.affinity2').value = '';
            // Keep default values for other fields
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

        // discount management
        const clientDiscountInput = section.querySelector('.client-discount');
        const agencyDiscountInput = section.querySelector('.agency-discount');
        const saveDiscountsBtn = section.querySelector('.save-discounts');
        const waveCostsDiv = section.querySelector('.wave-costs');

        async function loadDiscounts() {
          try {
            const discounts = await fetchJSON(urlReplace(WD_LIST, w.id));
            discounts.forEach(d => {
              if (d.discount_type === 'client') {
                clientDiscountInput.value = d.discount_percentage;
              } else if (d.discount_type === 'agency') {
                agencyDiscountInput.value = d.discount_percentage;
              }
            });
            await updateCostDisplay();
          } catch (e) {
            console.error('Error loading discounts:', e);
          }
        }

        async function updateCostDisplay() {
          try {
            const costs = await fetchJSON(urlReplace(W_TOTAL, w.id));
            waveCostsDiv.innerHTML = `
              <div>Bazinė kaina: €${costs.base_cost.toFixed(2)}</div>
              <div>Kaina klientui: €${costs.client_cost.toFixed(2)} ${costs.client_discount_percent > 0 ? `(-${costs.client_discount_percent}%)` : ''}</div>
              <div>Kaina agentūrai: €${costs.agency_cost.toFixed(2)} ${costs.agency_discount_percent > 0 ? `(-${costs.agency_discount_percent}%)` : ''}</div>
            `;
          } catch (e) {
            console.error('Error updating cost display:', e);
          }
        }

        saveDiscountsBtn.addEventListener('click', async () => {
          try {
            const clientDiscount = parseFloat(clientDiscountInput.value || 0);
            const agencyDiscount = parseFloat(agencyDiscountInput.value || 0);

            // Delete existing discounts for this wave
            const existingDiscounts = await fetchJSON(urlReplace(WD_LIST, w.id));
            for (const discount of existingDiscounts) {
              await fetchJSON(urlReplace(D_DELETE, discount.id), { method: 'DELETE' });
            }

            // Create new discounts if values are provided
            if (clientDiscount > 0) {
              await fetchJSON(urlReplace(WD_CREATE, w.id), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ discount_type: 'client', discount_percentage: clientDiscount })
              });
            }

            if (agencyDiscount > 0) {
              await fetchJSON(urlReplace(WD_CREATE, w.id), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ discount_type: 'agency', discount_percentage: agencyDiscount })
              });
            }

            await updateCostDisplay();
            
            // Recalculate wave item prices with new discounts
            await fetchJSON(urlReplace(W_RECALC, w.id), { method: 'POST' });
            
            // Reload waves to update wave items calculations with new discounts
            await loadWaves(currentCampaign.id);
            alert('Nuolaidos išsaugotos ir perskaičiuotos');
          } catch (e) {
            alert('Klaida išsaugant nuolaidas: ' + e.message);
          }
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
              <td class="px-2 py-1 text-xs bg-green-50">${r.tg_size_thousands || '-'}</td>
              <td class="px-2 py-1 text-xs bg-green-50">${r.tg_share_percent ? r.tg_share_percent.toFixed(1) + '%' : '-'}</td>
              <td class="px-2 py-1 text-xs bg-green-50">${r.tg_sample_size || '-'}</td>
              <td class="px-2 py-1 text-xs">${(r.channel_share * 100).toFixed(1)}%</td>
              <td class="px-2 py-1 text-xs">${(r.pt_zone_share * 100).toFixed(1)}%</td>
              <td class="px-2 py-1 text-xs">${r.clip_duration || 10}</td>
              <td class="px-2 py-1 text-xs">${grpPlanned.toFixed(2)}</td>
              <td class="px-2 py-1"><input class="w-16 text-xs border rounded px-1 py-0.5" type="number" step="0.01" value="${r.trps || ''}"></td>
              <td class="px-2 py-1"><input class="w-12 text-xs border rounded px-1 py-0.5" type="number" step="0.1" value="${r.affinity1 || ''}"></td>
              <td class="px-2 py-1 text-xs">€${grossCpp.toFixed(2)}</td>
              <td class="px-2 py-1 text-xs bg-yellow-50">${(r.duration_index || 1.25).toFixed(2)}</td>
              <td class="px-2 py-1 text-xs bg-yellow-50">${(r.seasonal_index || 0.9).toFixed(2)}</td>
              <td class="px-2 py-1 text-xs bg-yellow-50">${(r.trp_purchase_index || 0.95).toFixed(2)}</td>
              <td class="px-2 py-1 text-xs bg-yellow-50">${(r.advance_purchase_index || 0.95).toFixed(2)}</td>
              <td class="px-2 py-1 text-xs bg-yellow-50">${(r.position_index || 1.0).toFixed(2)}</td>
              <td class="px-2 py-1 text-xs">€${grossPrice.toFixed(2)}</td>
              <td class="px-2 py-1 text-xs">${r.client_discount || 0}%</td>
              <td class="px-2 py-1 text-xs">€${netPrice.toFixed(2)}</td>
              <td class="px-2 py-1 text-xs">${r.agency_discount || 0}%</td>
              <td class="px-2 py-1 text-xs">${netNetPrice.toFixed(2)}</td>
              <td class="px-2 py-1">
                <div class="flex gap-1">
                  <button class="itm-save px-2 py-0.5 text-xs rounded border border-emerald-300 bg-emerald-50 text-emerald-700">Saugoti</button>
                  <button class="itm-del px-2 py-0.5 text-xs rounded border border-rose-300 bg-rose-50 text-rose-700">X</button>
                </div>
              </td>
            `;
            tr.querySelector('.itm-save').addEventListener('click', async () => {
              const trps = tr.querySelector('.itm-trps').value;
              const pps  = tr.querySelector('.itm-eur').value;
              
              await fetchJSON(urlReplace(I_UPDATE, r.id), {
                method:'PATCH', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({ 
                  trps, 
                  price_per_sec_eur: pps
                })
              });
              await updateCostDisplay(); // Update costs after saving item  
              await loadWaves(currentCampaign.id); // Reload to show updated calculations
              alert('Wave item išsaugotas');
            });
            tr.querySelector('.itm-del').addEventListener('click', async () => {
              if(!confirm('Šalinti eilutę?')) return;
              await fetchJSON(urlReplace(I_DELETE, r.id), { method:'DELETE' });
              tr.remove();
              await updateCostDisplay(); // Update costs after deleting item
            });
            itemsTbody.appendChild(tr);
          });
        }

        await reloadItems();
        await loadDiscounts(); // Load existing discounts when wave loads
        wavesDiv.appendChild(section);
        
        // Now add event listeners for auto-indices (after section is in DOM)
        const tgSelectForIndices = section.querySelector('.tg');
        const tvcSelectForIndices = section.querySelector('.tvc');
        
        if (tgSelectForIndices) {
          tgSelectForIndices.addEventListener('change', () => {
            updateAutoIndices(w.id, section);
          });
        }
        
        if (tvcSelectForIndices) {
          tvcSelectForIndices.addEventListener('change', () => {
            updateAutoIndices(w.id, section);
          });
        }
        
        } catch (error) {
          console.error('Error creating wave section:', error, w);
          // Create fallback simple wave display
          const fallbackSection = document.createElement('div');
          fallbackSection.className = "mb-4 p-4 border rounded bg-red-50";
          fallbackSection.innerHTML = `<div class="text-red-700">Klaida generuojant bangą: ${w.name} (${error.message})</div>`;
          wavesDiv.appendChild(fallbackSection);
        }
      }
      
      // Update TVC selections in all wave forms after loading all waves
      updateAllTVCSelections();
    }

    // TVC add button
    tvcAdd.addEventListener('click', createTVC);

    // add wave
    $('#wAdd').addEventListener('click', async () => {
      if(!currentCampaign){ alert('Pirma pasirinkite kampaniją'); return; }
      const name  = $('#wName').value.trim();
      const start = $('#wStart').value || null;
      const end   = $('#wEnd').value || null;
      await fetchJSON(urlReplace(W_CREATE, currentCampaign.id), {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ name, start_date:start, end_date:end })
      });
      $('#wName').value = ''; $('#wStart').value = ''; $('#wEnd').value = '';
      await loadWaves(currentCampaign.id);
    });

    // initial boot
    (async () => {
      await loadPricingLists();
      await loadCampaigns();
    })();
  });
})();
