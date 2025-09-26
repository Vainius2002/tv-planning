(() => {
  'use strict';

  window.addEventListener('DOMContentLoaded', () => {
    const dataDiv = document.querySelector('[data-cg-list]');
    const CG_LIST        = dataDiv.dataset.cgList;
    const CG_CREATE      = dataDiv.dataset.cgCreate;
    const CG_UPDATE_BASE = dataDiv.dataset.cgUpdateBase; // .../channel-groups/0
    const CG_DELETE_BASE = dataDiv.dataset.cgDeleteBase; // .../channel-groups/0

    const CH_LIST_BASE   = dataDiv.dataset.chListBase;   // append /<gid>/channels
    const CH_UPDATE_BASE = dataDiv.dataset.chUpdateBase; // .../channels/0
    const CH_DELETE_BASE = dataDiv.dataset.chDeleteBase; // .../channels/0

    const DEV_SEED  = dataDiv.dataset.devSeed;

    const $ = s => document.querySelector(s);
    const cgTbody  = $('#cgTbody');
    const cgSelect = $('#cgSelect');
    const chTbody  = $('#chTbody');

    const cgUpdateUrl = gid => CG_UPDATE_BASE.replace(/\/0$/, `/${gid}`);
    const cgDeleteUrl = gid => CG_DELETE_BASE.replace(/\/0$/, `/${gid}`);
    const chListUrl   = gid => `${CH_LIST_BASE}/${gid}/channels`;
    const chUpdateUrl = cid => CH_UPDATE_BASE.replace(/\/0$/, `/${cid}`);
    const chDeleteUrl = cid => CH_DELETE_BASE.replace(/\/0$/, `/${cid}`);

    async function fetchJSON(url, opt){
      const r = await fetch(url, opt);
      let data = null; try { data = await r.json(); } catch {}
      if(!r.ok) throw new Error((data && (data.message||data.error)) || `${r.status} ${r.statusText}`);
      return data;
    }

    async function loadGroups(){
      const groups = await fetchJSON(CG_LIST);
      cgTbody.innerHTML = '';
      cgSelect.innerHTML = '';

      groups.forEach(g => {
        // table row with rename + show + delete
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="px-4 py-2 text-slate-500">${g.id}</td>
          <td class="px-4 py-2">
            <input value="${g.name.replace(/"/g,'&quot;')}" class="cg-name w-full rounded-lg border-slate-300 bg-slate-50 px-2 py-1 text-sm">
          </td>
          <td class="px-4 py-2">
            <div class="flex gap-2">
              <button data-id="${g.id}" class="px-3 py-1.5 text-xs rounded-lg border border-slate-300 bg-white hover:bg-slate-50 load">Rodyti kanalus</button>
              <button class="px-3 py-1.5 text-xs rounded-lg border border-blue-300 bg-blue-50 text-blue-700 hover:bg-blue-100 export-excel" data-group-id="${g.id}">Excel kanalui</button>
              <button class="px-3 py-1.5 text-xs rounded-lg border border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 cg-save">Saugoti</button>
              <button class="px-3 py-1.5 text-xs rounded-lg border border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100 cg-del">Šalinti</button>
            </div>
          </td>`;
        // handlers
        tr.querySelector('.load').addEventListener('click', async (e) => {
          const gid = e.currentTarget.dataset.id;
          cgSelect.value = gid;
          await loadChannels(gid);
        });
        tr.querySelector('.export-excel').addEventListener('click', (e) => {
          const groupId = e.currentTarget.dataset.groupId;
          console.log('Export button clicked, groupId:', groupId);

          if (!groupId) {
            alert('Klaida: grupės ID nerastas');
            return;
          }

          // Use the same method as window.location.href - simplest approach
          const url = `/tv-planner/channel-groups/${groupId}/export-excel`;
          console.log('Navigating to:', url);

          window.open(url, '_blank');
        });
        tr.querySelector('.cg-save').addEventListener('click', async () => {
          const name = tr.querySelector('.cg-name').value.trim();
          if(!name){ alert('Įveskite pavadinimą'); return; }
          await fetchJSON(cgUpdateUrl(g.id), {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
          });
          alert('Išsaugota');
          await loadGroups(); // refresh list/dropdown
        });
        tr.querySelector('.cg-del').addEventListener('click', async () => {
          if(!confirm(`Šalinti grupę „${g.name}“ ir visus jos kanalus?`)) return;
          await fetchJSON(cgDeleteUrl(g.id), { method: 'DELETE' });
          // if deleted selection, pick first available
          await loadGroups();
          if (cgSelect.options.length) {
            await loadChannels(cgSelect.value);
          } else {
            chTbody.innerHTML = '';
          }
        });

        cgTbody.appendChild(tr);

        // dropdown option
        const opt = document.createElement('option');
        opt.value = g.id;
        opt.textContent = g.name;
        cgSelect.appendChild(opt);
      });

      if (groups[0]) {
        cgSelect.value = groups[0].id;
        await loadChannels(groups[0].id);
      } else {
        chTbody.innerHTML = '';
      }
    }

    async function loadChannels(gid){
      const rows = await fetchJSON(chListUrl(gid));
      chTbody.innerHTML = '';
      rows.forEach(ch => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="px-4 py-2 text-slate-500">${ch.id}</td>
          <td class="px-4 py-2">
            <input value="${ch.name.replace(/"/g,'&quot;')}" class="w-full rounded-lg border-slate-300 bg-slate-50 px-2 py-1 text-sm ch-name" placeholder="pvz. TV3">
          </td>
          <td class="px-4 py-2">
            <select class="rounded-lg border-slate-300 px-2 py-1 text-sm ch-size">
              <option value="big"${ch.size==='big'?' selected':''}>Didelis</option>
              <option value="small"${ch.size==='small'?' selected':''}>Mažas</option>
            </select>
          </td>
          <td class="px-4 py-2">
            <div class="flex gap-2">
              <button class="px-3 py-1.5 text-xs rounded-lg border border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 save">Saugoti</button>
              <button class="px-3 py-1.5 text-xs rounded-lg border border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100 del">Šalinti</button>
            </div>
          </td>`;

        tr.querySelector('.save').addEventListener('click', async () => {
          const name = tr.querySelector('.ch-name').value.trim();
          const size = tr.querySelector('.ch-size').value;
          await fetchJSON(chUpdateUrl(ch.id), {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, size })
          });
          alert('Išsaugota');
        });

        tr.querySelector('.del').addEventListener('click', async () => {
          if(!confirm(`Šalinti kanalą „${ch.name}“?`)) return;
          await fetchJSON(chDeleteUrl(ch.id), { method: 'DELETE' });
          tr.remove();
        });

        chTbody.appendChild(tr);
      });
    }

    // Top controls
    $('#cgAdd').addEventListener('click', async () => {
      const name = $('#cgName').value.trim();
      if(!name) { alert('Įveskite pavadinimą'); return; }
      await fetchJSON(CG_CREATE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      $('#cgName').value = '';
      await loadGroups();
    });

    $('#cgSeed').addEventListener('click', async () => {
      await fetchJSON(DEV_SEED, { method: 'POST' });
      await loadGroups();
      alert('Užpildyta pavyzdžiais');
    });

    $('#chAdd').addEventListener('click', async () => {
      const gid = cgSelect.value;
      const name = $('#chName').value.trim();
      const size = $('#chSize').value;
      if(!gid) { alert('Pasirinkite grupę'); return; }
      if(!name) { alert('Įveskite kanalo pavadinimą'); return; }
      await fetchJSON(chListUrl(gid), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, size })
      });
      $('#chName').value = '';
      await loadChannels(gid);
    });

    cgSelect.addEventListener('change', e => loadChannels(e.target.value));

    // Initial
    loadGroups();
  });
})();
