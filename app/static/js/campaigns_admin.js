// static/js/campaigns_admin.js
(() => {
  'use strict';

  window.addEventListener('DOMContentLoaded', () => {
    const PL_LIST   = document.body.dataset.plList;
    const PL_OWNERS = document.body.dataset.plOwnersBase;   // ends with /0
    const PL_TARGETS= document.body.dataset.plTargetsBase;  // ends with /0

    const C_LIST    = document.body.dataset.cList;
    const C_CREATE  = document.body.dataset.cCreate;
    const C_UPDATE  = document.body.dataset.cUpdateBase;    // ends with /0
    const C_DELETE  = document.body.dataset.cDeleteBase;    // ends with /0

    const W_LIST    = document.body.dataset.wListBase;      // /campaigns/0/waves
    const W_CREATE  = document.body.dataset.wCreateBase;    // /campaigns/0/waves
    const W_UPDATE  = document.body.dataset.wUpdateBase;    // /waves/0
    const W_DELETE  = document.body.dataset.wDeleteBase;    // /waves/0

    const I_LIST    = document.body.dataset.iListBase;      // /waves/0/items
    const I_CREATE  = document.body.dataset.iCreateBase;    // /waves/0/items
    const I_UPDATE  = document.body.dataset.iUpdateBase;    // /wave-items/0
    const I_DELETE  = document.body.dataset.iDeleteBase;    // /wave-items/0

    const CD_LIST   = document.body.dataset.cdListBase;     // /campaigns/0/discounts
    const CD_CREATE = document.body.dataset.cdCreateBase;   // /campaigns/0/discounts
    const WD_LIST   = document.body.dataset.wdListBase;     // /waves/0/discounts
    const WD_CREATE = document.body.dataset.wdCreateBase;   // /waves/0/discounts
    const D_UPDATE  = document.body.dataset.dUpdateBase;    // /discounts/0
    const D_DELETE  = document.body.dataset.dDeleteBase;    // /discounts/0
    const W_TOTAL   = document.body.dataset.wTotalBase;     // /waves/0/total
    const C_STATUS  = document.body.dataset.cStatusBase;   // /campaigns/0/status
    
    const TVC_LIST   = document.body.dataset.tvcListBase;   // /campaigns/0/tvcs
    const TVC_CREATE = document.body.dataset.tvcCreateBase; // /campaigns/0/tvcs
    const TVC_UPDATE = document.body.dataset.tvcUpdateBase; // /tvcs/0
    const TVC_DELETE = document.body.dataset.tvcDeleteBase; // /tvcs/0

    const $ = s => document.querySelector(s);
    const cTbody = $('#cTbody');
    const cName = $('#cName'), cPL = $('#cPL'), cStart = $('#cStart'), cEnd = $('#cEnd');
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

    function urlReplace(base, id){ return base.replace(/\/0($|\/)/, `/${id}$1`); }

    async function fetchJSON(url, opt){
      const r = await fetch(url, opt);
      let data = null; try { data = await r.json(); } catch {}
      if(!r.ok) throw new Error((data && (data.message||data.error)) || `${r.status} ${r.statusText}`);
      return data;
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
          <td class="px-4 py-2">${c.name}</td>
          <td class="px-4 py-2">${c.pricing_list_name}</td>
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
              <a href="/trp-admin/campaigns/${c.id}/export/client-excel" class="export-client px-3 py-1.5 text-xs rounded-lg border border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 no-underline inline-block">Excel klientui</a>
              <a href="/trp-admin/campaigns/${c.id}/export/agency-csv" class="export-agency px-3 py-1.5 text-xs rounded-lg border border-blue-300 bg-blue-50 text-blue-700 hover:bg-blue-100 no-underline inline-block">CSV agentūrai</a>
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
      const pricing_list_id = +cPL.value;
      const start_date = cStart.value || null;
      const end_date   = cEnd.value || null;
      if(!name || !pricing_list_id){ alert('Įveskite pavadinimą ir parinkite kainoraštį'); return; }
      await fetchJSON(C_CREATE, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ name, pricing_list_id, start_date, end_date })
      });
      cName.value=''; cStart.value=''; cEnd.value='';
      await loadCampaigns();
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
    }

    function openCampaign(c){
      currentCampaign = c;
      renderCurrentCampaign();
    }

    // -------- waves + items --------
    async function loadWaves(cid){
      const waves = await fetchJSON(urlReplace(W_LIST, cid));
      wavesDiv.innerHTML = '';
      for(const w of waves){
        const section = document.createElement('div');
        section.className = "mb-8 border border-slate-200 rounded-xl overflow-hidden";
        section.innerHTML = `
          <div class="px-4 py-3 bg-slate-50 flex items-center justify-between">
            <div class="font-medium">${w.name || '(be pavadinimo)'} <span class="text-slate-500 ml-2">${(w.start_date||'')} ${w.end_date?('– '+w.end_date):''}</span></div>
            <div class="flex gap-2">
              <button class="w-del px-3 py-1.5 text-xs rounded-lg border border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100">Šalinti bangą</button>
            </div>
          </div>
          <div class="p-4">
            <div class="flex flex-wrap gap-3 items-end mb-3">
              <div>
                <label class="block text-sm text-slate-600 mb-1">Savininkas</label>
                <select class="owner rounded-lg border-slate-300 px-3 py-2 text-sm"></select>
              </div>
              <div>
                <label class="block text-sm text-slate-600 mb-1">Tikslinė grupė</label>
                <select class="tg rounded-lg border-slate-300 px-3 py-2 text-sm"></select>
              </div>
              <div>
                <label class="block text-sm text-slate-600 mb-1">TVC</label>
                <select class="tvc-select rounded-lg border-slate-300 px-3 py-2 text-sm">
                  <option value="">Pasirinkti TVC</option>
                </select>
              </div>
              <div>
                <label class="block text-sm text-slate-600 mb-1">TRP kiekis</label>
                <input class="trps rounded-lg border-slate-300 px-3 py-2 text-sm w-32" type="number" step="0.01" placeholder="pvz. 120">
              </div>
              <button class="i-add px-3 py-2 text-sm rounded-lg border border-slate-300 bg-white hover:bg-slate-50">Pridėti į eilutę</button>
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
              <table class="min-w-full text-sm">
                <thead class="bg-white text-slate-700 border-b border-slate-200">
                  <tr>
                    <th class="text-left font-medium px-3 py-2">Savininkas</th>
                    <th class="text-left font-medium px-3 py-2">Tikslinė grupė</th>
                    <th class="text-left font-medium px-3 py-2">TVC</th>
                    <th class="text-left font-medium px-3 py-2">TRP</th>
                    <th class="text-left font-medium px-3 py-2">€/sek</th>
                    <th class="text-left font-medium px-3 py-2 w-40">Veiksmai</th>
                  </tr>
                </thead>
                <tbody class="items divide-y divide-slate-100"></tbody>
              </table>
            </div>
          </div>
        `;
        // Populate owner/targets from pricing list for this campaign
        const ownerSel = section.querySelector('.owner');
        const tgSel    = section.querySelector('.tg');
        const tvcSel   = section.querySelector('.tvc-select');
        const itemsTbody = section.querySelector('.items');

        // load owners
        const owners = await fetchJSON(urlReplace(PL_OWNERS, currentCampaign.pricing_list_id));
        ownerSel.innerHTML = owners.map(o => `<option>${o}</option>`).join('');
        // load targets for first owner
        async function loadTargetsForOwner(owner){
          const url = urlReplace(PL_TARGETS, currentCampaign.pricing_list_id) + `?owner=${encodeURIComponent(owner)}`;
          const tgs = await fetchJSON(url);
          tgSel.innerHTML = tgs.map(t => `<option>${t}</option>`).join('');
        }
        if (owners[0]) await loadTargetsForOwner(owners[0]);
        ownerSel.addEventListener('change', () => loadTargetsForOwner(ownerSel.value));

        // load TVCs
        function loadTVCsIntoSelect(){
          tvcSel.innerHTML = '<option value="">Pasirinkti TVC</option>';
          tvcs.forEach(tvc => {
            tvcSel.innerHTML += `<option value="${tvc.id}">${tvc.name} (${tvc.duration} sek.)</option>`;
          });
        }
        loadTVCsIntoSelect();

        // add item
        section.querySelector('.i-add').addEventListener('click', async () => {
          const trps = section.querySelector('.trps').value;
          const tvcId = tvcSel.value || null;
          if(!ownerSel.value || !tgSel.value || !trps){ alert('Užpildykite savininką, tikslinę grupę ir TRP'); return; }
          const iid = await fetchJSON(urlReplace(I_CREATE, w.id), {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ owner: ownerSel.value, target_group: tgSel.value, trps, tvc_id: tvcId })
          });
          await reloadItems();
          await updateCostDisplay(); // Update costs after adding item
          section.querySelector('.trps').value = '';
          tvcSel.value = ''; // Reset TVC selection
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
            alert('Nuolaidos išsaugotos');
          } catch (e) {
            alert('Klaida išsaugant nuolaidas: ' + e.message);
          }
        });

        async function reloadItems(){
          const rows = await fetchJSON(urlReplace(I_LIST, w.id));
          itemsTbody.innerHTML = '';
          rows.forEach(r => {
            // Find TVC info if tvc_id exists
            const tvcInfo = r.tvc_id ? tvcs.find(tvc => tvc.id == r.tvc_id) : null;
            const tvcDisplay = tvcInfo ? `${tvcInfo.name} (${tvcInfo.duration}s)` : '-';
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td class="px-3 py-2">${r.owner}</td>
              <td class="px-3 py-2">${r.target_group}</td>
              <td class="px-3 py-2 text-sm text-slate-600">${tvcDisplay}</td>
              <td class="px-3 py-2"><input class="itm-trps w-24 rounded border-slate-300 px-2 py-1" type="number" step="0.01" value="${r.trps ?? ''}"></td>
              <td class="px-3 py-2"><input class="itm-eur w-24 rounded border-slate-300 px-2 py-1" type="number" step="0.01" value="${r.price_per_sec_eur ?? ''}"></td>
              <td class="px-3 py-2">
                <div class="flex gap-2">
                  <button class="itm-save px-3 py-1.5 text-xs rounded-lg border border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100">Saugoti</button>
                  <button class="itm-del px-3 py-1.5 text-xs rounded-lg border border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100">Šalinti</button>
                </div>
              </td>
            `;
            tr.querySelector('.itm-save').addEventListener('click', async () => {
              const trps = tr.querySelector('.itm-trps').value;
              const pps  = tr.querySelector('.itm-eur').value;
              await fetchJSON(urlReplace(I_UPDATE, r.id), {
                method:'PATCH', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({ trps, price_per_sec_eur: pps })
              });
              await updateCostDisplay(); // Update costs after saving item
              alert('Išsaugota');
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
      }
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
