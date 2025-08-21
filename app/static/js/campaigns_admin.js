// static/js/campaigns_admin.js
(() => {
  'use strict';

  window.addEventListener('DOMContentLoaded', () => {
    const dataDiv = document.querySelector('[data-c-list]');

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
    const cName = $('#cName'), cStart = $('#cStart'), cEnd = $('#cEnd');
    const cAgency = $('#cAgency'), cClient = $('#cClient'), cProduct = $('#cProduct');
    const cCountry = $('#cCountry');
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
      
      return trps * cpp * durationIndex * seasonalIndex * trpPurchaseIndex * advancePurchaseIndex * positionIndex;
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
    
    function renderCampaigns(){
      cTbody.innerHTML = '';
      
      campaigns.forEach(c => {
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
      const start_date = cStart.value || null;
      const end_date   = cEnd.value || null;
      const agency = cAgency.value.trim();
      const client = cClient.value.trim();
      const product = cProduct.value.trim();
      const country = cCountry.value.trim() || 'Lietuva';
      
      if(!name){ alert('Įveskite kampanijos pavadinimą'); return; }
      
      const response = await fetchJSON(C_CREATE, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ 
          name, start_date, end_date,
          agency, client, product, country
        })
      });
      
      // Clear form (except agency which is fixed)
      cName.value=''; cStart.value=''; cEnd.value='';
      cClient.value=''; cProduct.value='';
      cCountry.value='Lietuva';
      
      await loadCampaigns();
      
      // Automatically open the newly created campaign
      if(response && response.id) {
        const newCampaign = campaigns.find(c => c.id === response.id);
        if(newCampaign) {
          openCampaign(newCampaign);
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
      
      // Wave rows
      if (currentWaves && currentWaves.length > 0) {
        currentWaves.forEach((wave, waveIndex) => {
          if (wave.start_date && wave.end_date) {
            html += '<tr class="border-b border-slate-200 hover:bg-slate-50">';
            tempDate = new Date(startDate);
            const waveStart = new Date(wave.start_date);
            const waveEnd = new Date(wave.end_date);
            
            while (tempDate <= endDate) {
              const isInWave = tempDate >= waveStart && tempDate <= waveEnd;
              const dateStr = tempDate.toISOString().split('T')[0];
              const isWeekend = tempDate.getDay() === 0 || tempDate.getDay() === 6;
              
              if (isInWave) {
                html += `<td class="px-1 py-2 text-center border-r border-slate-200 ${isWeekend ? 'bg-green-100' : 'bg-green-200'} cursor-pointer hover:bg-green-300" data-wave="${waveIndex}" data-date="${dateStr}">`;
                html += `<span class="text-xs font-medium">B${waveIndex + 1}</span>`;
              } else {
                html += `<td class="px-1 py-2 border-r border-slate-200 ${isWeekend ? 'bg-gray-50' : ''}"`;
                html += '';
              }
              html += '</td>';
              tempDate.setDate(tempDate.getDate() + 1);
            }
            html += '</tr>';
          }
        });
      }
      
      // TRP distribution row
      html += '<tr class="border-t-2 border-slate-400 bg-amber-50">';
      tempDate = new Date(startDate);
      const dailyTRPs = {}; // Store TRP values per date
      
      while (tempDate <= endDate) {
        const dateStr = tempDate.toISOString().split('T')[0];
        const isWeekend = tempDate.getDay() === 0 || tempDate.getDay() === 6;
        html += `<td class="px-1 py-1 border-r border-slate-200 ${isWeekend ? 'bg-amber-100' : 'bg-amber-50'}">`;
        html += `<input type="number" step="0.01" class="trp-input w-full text-xs px-1 py-0.5 border-0 bg-transparent text-center font-medium" data-date="${dateStr}" placeholder="0" />`;
        html += '</td>';
        tempDate.setDate(tempDate.getDate() + 1);
      }
      html += '</tr>';
      
      // Total TRP row
      html += '<tr class="border-t border-slate-300 bg-slate-100 font-medium">';
      html += `<td colspan="${Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24)) + 1}" class="px-2 py-2 text-xs text-right">`;
      html += 'Viso TRP: <span id="totalTRP" class="font-bold text-slate-700">0.00</span>';
      html += '</td>';
      html += '</tr>';
      
      html += '</tbody>';
      html += '</table>';
      
      calendarDiv.innerHTML = html;
      
      // Add event listeners first
      const trpInputs = calendarDiv.querySelectorAll('.trp-input');
      trpInputs.forEach(input => {
        input.addEventListener('input', () => {
          updateTotalTRP();
          saveTRPDistribution(); // Saugojam iškart kai keičiasi
        });
        input.addEventListener('blur', saveTRPDistribution); // Ir kai palieka lauką
      });
      
      // Then load existing TRP data
      loadTRPDistribution().then(() => {
        updateTotalTRP(); // Calculate initial total after loading data
      });
    }

    // -------- TRP Distribution functions --------
    async function loadTRPDistribution() {
      if (!currentCampaign) return;
      
      try {
        // For now, use localStorage to store TRP data
        // In future, this should load from database
        const storageKey = `trp_distribution_${currentCampaign.id}`;
        const storedData = localStorage.getItem(storageKey);
        
        console.log('Loading TRP for campaign', currentCampaign.id, 'with key:', storageKey);
        console.log('Found data:', storedData);
        
        if (storedData) {
          const trpData = JSON.parse(storedData);
          
          // Fill in the input fields - use specific selector for TRP inputs
          Object.keys(trpData).forEach(date => {
            const input = document.querySelector(`.trp-input[data-date="${date}"]`);
            if (input) {
              input.value = trpData[date] > 0 ? trpData[date].toFixed(2) : '';
              console.log('Set input for', date, 'to', trpData[date]);
            } else {
              console.log('TRP Input not found for date:', date);
            }
          });
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
          const value = parseFloat(input.value) || 0;
          console.log(`Processing input for ${date}: value="${input.value}", parsed=${value}`);
          trpData[date] = value; // Saugok visus, net ir 0
        });
        
        // For now, save to localStorage
        // In future, this should save to database via API
        const storageKey = `trp_distribution_${currentCampaign.id}`;
        localStorage.setItem(storageKey, JSON.stringify(trpData));
        
        console.log('TRP Distribution saved for campaign', currentCampaign.id, ':', trpData);
        console.log('Storage key:', storageKey);
      } catch (error) {
        console.error('Error saving TRP distribution:', error);
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
      currentWaves = waves; // Store for calendar
      
      // Clear waves div
      wavesDiv.innerHTML = '';
      
      // If no waves, show message
      if (!waves || waves.length === 0) {
        wavesDiv.innerHTML = '<div class="text-center text-gray-500 py-8">Nėra sukurtų bangų. Sukurkite bangą naudodami formą viršuje.</div>';
      }
      
      // Update calendar with wave information (called once for all cases)
      renderCampaignCalendar();
      
      for(const w of waves){
        const section = document.createElement('div');
        section.className = "mb-8 border border-slate-200 rounded-xl overflow-hidden";
        
        try {
        section.innerHTML = `
          <div class="px-4 py-3 bg-slate-50 flex items-center justify-between">
            <div class="font-medium">Banga ${waves.indexOf(w) + 1} <span class="text-slate-500 ml-2">${(w.start_date||'')} ${w.end_date?('– '+w.end_date):''}</span></div>
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
          updateIndicesFromDatabase(tgSel.value, clipDurationInput.value);
        });
        
        // Update clip duration when TVC changes
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
            client_discount: 0, // Default 0, will be edited in the table
            agency_discount: 0  // Default 0, will be edited in the table
          };
          
          try {
            await fetchJSON(urlReplace(I_CREATE, w.id), {
              method:'POST', headers:{'Content-Type':'application/json'},
              body: JSON.stringify(formData)
            });
            await reloadItems();
            
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
              <td class="px-2 py-1"><input class="itm-trps w-16 text-xs border rounded px-1 py-0.5 bg-purple-50" type="number" step="0.01" value="${r.trps || ''}" placeholder="TRP"></td>
              <td class="px-2 py-1"><input class="itm-affinity1 w-12 text-xs border rounded px-1 py-0.5 bg-purple-50" type="number" step="0.1" value="${r.affinity1 || ''}" placeholder="Affinity"></td>
              <td class="px-2 py-1 text-xs">€${grossCpp.toFixed(2)}</td>
              <td class="px-2 py-1 text-xs bg-yellow-50">${(r.duration_index || 1.25).toFixed(2)}</td>
              <td class="px-2 py-1 text-xs bg-yellow-50">${(r.seasonal_index || 0.9).toFixed(2)}</td>
              <td class="px-2 py-1"><input class="itm-trp-purchase w-12 text-xs border rounded px-1 py-0.5 bg-gray-100" type="number" step="0.01" value="${(r.trp_purchase_index || 0.95).toFixed(2)}" title="TRP pirkimo indeksas (default: 0.95)"></td>
              <td class="px-2 py-1"><input class="itm-advance-purchase w-12 text-xs border rounded px-1 py-0.5 bg-gray-100" type="number" step="0.01" value="${(r.advance_purchase_index || 0.95).toFixed(2)}" title="Išankstinio pirkimo indeksas (default: 0.95)"></td>
              <td class="px-2 py-1"><input class="itm-position w-12 text-xs border rounded px-1 py-0.5 bg-gray-100" type="number" step="0.01" value="${(r.position_index || 1.0).toFixed(2)}" title="Pozicijos indeksas (default: 1.0)"></td>
              <td class="px-2 py-1 text-xs">€${grossPrice.toFixed(2)}</td>
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
              const clientDiscount = parseFloat(tr.querySelector('.itm-client-discount').value) || 0;
              const agencyDiscount = parseFloat(tr.querySelector('.itm-agency-discount').value) || 0;
              const newNetPrice = calculateNetPrice(grossPrice, clientDiscount);
              const newNetNetPrice = calculateNetNetPrice(newNetPrice, agencyDiscount);
              
              // Update the displayed prices using classes
              const netPriceCell = tr.querySelector('.net-price');
              const netNetPriceCell = tr.querySelector('.net-net-price');
              if (netPriceCell) netPriceCell.innerHTML = `€${newNetPrice.toFixed(2)}`;
              if (netNetPriceCell) netNetPriceCell.innerHTML = `€${newNetNetPrice.toFixed(2)}`;
            };
            
            tr.querySelector('.itm-client-discount').addEventListener('input', recalculatePrices);
            tr.querySelector('.itm-agency-discount').addEventListener('input', recalculatePrices);
            
            tr.querySelector('.itm-save').addEventListener('click', async () => {
              try {
                // Get only editable values
                const trps = parseFloat(tr.querySelector('.itm-trps').value) || 0;
                const affinity1 = parseFloat(tr.querySelector('.itm-affinity1').value) || null;
                const trpPurchaseIndex = parseFloat(tr.querySelector('.itm-trp-purchase').value) || 0.95;
                const advancePurchaseIndex = parseFloat(tr.querySelector('.itm-advance-purchase').value) || 0.95;
                const positionIndex = parseFloat(tr.querySelector('.itm-position').value) || 1.0;
                const clientDiscount = parseFloat(tr.querySelector('.itm-client-discount').value) || 0;
                const agencyDiscount = parseFloat(tr.querySelector('.itm-agency-discount').value) || 0;
                
                console.log('Saving wave item:', r.id, {
                  trps: trps,
                  affinity1: affinity1,
                  trp_purchase_index: trpPurchaseIndex,
                  advance_purchase_index: advancePurchaseIndex,
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
              await fetchJSON(urlReplace(I_DELETE, r.id), { method:'DELETE' });
              tr.remove();
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

    // add wave
    $('#wAdd').addEventListener('click', async () => {
      if(!currentCampaign){ alert('Pirma pasirinkite kampaniją'); return; }
      const start = $('#wStart').value || null;
      const end   = $('#wEnd').value || null;
      
      if (!start || !end) {
        alert('Prašome pasirinkti bangos pradžios ir pabaigos datas');
        return;
      }
      
      await fetchJSON(urlReplace(W_CREATE, currentCampaign.id), {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ name: '', start_date:start, end_date:end })
      });
      $('#wStart').value = ''; $('#wEnd').value = '';
      await loadWaves(currentCampaign.id);
    });

    // initial boot
    (async () => {
      await loadCampaigns();
    })();
  });
})();
