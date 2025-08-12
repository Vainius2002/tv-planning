(() => {
  'use strict';

  window.addEventListener('DOMContentLoaded', () => {
    const PL_LIST   = document.body.dataset.plList;
    const PL_CREATE = document.body.dataset.plCreate;
    const PL_DELETE_BASE = document.body.dataset.plDeleteBase; // .../pricing-lists/0
    const PL_DUP_BASE    = document.body.dataset.plDupBase;    // .../pricing-lists/0/duplicate

    const PLI_LIST_BASE   = document.body.dataset.pliListBase;   // .../pricing-lists/0/items
    const PLI_UPDATE_BASE = document.body.dataset.pliUpdateBase; // .../pricing-list-items/0
    const PLI_DELETE_BASE = document.body.dataset.pliDeleteBase; // .../pricing-list-items/0

    const CG_LIST = document.body.dataset.cgList;

    const $ = s => document.querySelector(s);
    const plSelect = $('#plSelect');
    const plName   = $('#plName');
    const plCopyName = $('#plCopyName');
    const pliTbody = $('#pliTbody');

    let channelGroups = []; // [{id, name}]
    let currentListId = null;

    function url_replace_tail(base, id) {
      return base.replace(/\/0(\b|$)/, `/${id}`);
    }

    async function fetchJSON(url, opt) {
      const r = await fetch(url, opt);
      let data = null; try { data = await r.json(); } catch {}
      if (!r.ok) throw new Error((data && (data.message||data.error)) || `${r.status} ${r.statusText}`);
      return data;
    }

    async function loadChannelGroups() {
      channelGroups = await fetchJSON(CG_LIST);
    }

    function fillOwnerSelect(sel, selectedId) {
      sel.innerHTML = '';
      channelGroups.forEach(g => {
        const opt = document.createElement('option');
        opt.value = g.id;
        opt.textContent = g.name;
        if (selectedId && Number(selectedId) === g.id) opt.selected = true;
        sel.appendChild(opt);
      });
    }

    async function loadLists() {
      const lists = await fetchJSON(PL_LIST);
      plSelect.innerHTML = '';
      lists.forEach(l => {
        const opt = document.createElement('option');
        opt.value = l.id;
        opt.textContent = l.name;
        plSelect.appendChild(opt);
      });
      if (lists[0]) {
        currentListId = lists[0].id;
        plSelect.value = currentListId;
        await loadItems(currentListId);
      } else {
        currentListId = null;
        pliTbody.innerHTML = '';
      }
    }

    async function loadItems(listId) {
      const rows = await fetchJSON(url_replace_tail(PLI_LIST_BASE, listId));
      pliTbody.innerHTML = '';
      rows.forEach(addRow);
    }

    function addRow(row = {}) {
      const tpl = document.getElementById('rowTpl');
      const tr = tpl.content.firstElementChild.cloneNode(true);
      tr.dataset.id = row.id || '';

      // owner dropdown
      const ownerSel = tr.querySelector('.ownerSel');
      fillOwnerSelect(ownerSel, row.channel_group_id);

      // Fill editable cells
      tr.querySelectorAll('[data-field]').forEach(td => {
        if (td.tagName === 'SELECT') return; // handled above
        const key = td.dataset.field;
        td.textContent = (row[key] ?? '');
        td.addEventListener('input', () => tr.classList.add('dirty'));
      });

      ownerSel.addEventListener('change', () => tr.classList.add('dirty'));

      // actions
      tr.querySelector('.save').addEventListener('click', () => saveRow(tr));
      tr.querySelector('.revert').addEventListener('click', () => revertRow(tr, row));
      tr.querySelector('.delete').addEventListener('click', () => deleteRow(tr));

      pliTbody.appendChild(tr);
      return tr;
    }

    function getPayload(tr) {
      const payload = {};
      tr.querySelectorAll('[data-field]').forEach(td => {
        if (td.tagName === 'SELECT') {
          payload[td.dataset.field] = td.value;
        } else {
          payload[td.dataset.field] = td.textContent.trim() || null;
        }
      });
      return payload;
    }

    function revertRow(tr, original) {
      const sel = tr.querySelector('.ownerSel');
      fillOwnerSelect(sel, original.channel_group_id);
      tr.querySelectorAll('[data-field]').forEach(td => {
        if (td.tagName !== 'SELECT') {
          const k = td.dataset.field;
          td.textContent = original[k] ?? '';
        }
      });
      tr.classList.remove('dirty');
    }

    async function saveRow(tr) {
      if (!currentListId) { alert('Pasirinkite sąrašą'); return; }
      const payload = getPayload(tr);
      // required
      if (!payload.channel_group_id || !payload.target_group || !payload.primary_label || !payload.price_per_sec_eur) {
        alert('Užpildykite: grupė, tikslinė grupė, pagr. kanalas, kaina');
        return;
      }

      const id = tr.dataset.id;
      try {
        if (!id) {
          // create
          await fetchJSON(url_replace_tail(PLI_LIST_BASE, currentListId), {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify(payload)
          });
          await loadItems(currentListId); // to get fresh IDs
        } else {
          // update
          await fetchJSON(url_replace_tail(PLI_UPDATE_BASE, id), {
            method: 'PATCH',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify(payload)
          });
          tr.classList.remove('dirty');
        }
      } catch (e) {
        alert('Klaida: ' + e.message);
      }
    }

    async function deleteRow(tr) {
      const id = tr.dataset.id;
      if (!id) { tr.remove(); return; }
      if (!confirm('Šalinti eilutę?')) return;
      try {
        await fetchJSON(url_replace_tail(PLI_DELETE_BASE, id), { method: 'DELETE' });
        tr.remove();
      } catch (e) {
        alert('Klaida: ' + e.message);
      }
    }

    // Toolbar
    $('#addRow').addEventListener('click', () => {
      const tr = addRow({});
      tr.classList.add('dirty');
    });

    $('#plAdd').addEventListener('click', async () => {
      const name = plName.value.trim();
      if (!name) { alert('Įveskite pavadinimą'); return; }
      try {
        await fetchJSON(PL_CREATE, {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ name })
        });
        plName.value = '';
        await loadLists();
      } catch (e) {
        alert('Klaida: ' + e.message);
      }
    });

    $('#plDuplicate').addEventListener('click', async () => {
      if (!currentListId) return;
      const name = plCopyName.value.trim();
      if (!name) { alert('Įveskite kopijos pavadinimą'); return; }
      try {
        await fetchJSON(url_replace_tail(PL_DUP_BASE, currentListId), {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ name })
        });
        plCopyName.value = '';
        await loadLists();
      } catch (e) {
        alert('Klaida: ' + e.message);
      }
    });

    $('#plDelete').addEventListener('click', async () => {
      if (!currentListId) return;
      if (!confirm('Šalinti sąrašą ir visus jo įrašus?')) return;
      try {
        await fetchJSON(url_replace_tail(PL_DELETE_BASE, currentListId), { method: 'DELETE' });
        await loadLists();
      } catch (e) {
        alert('Klaida: ' + e.message);
      }
    });

    plSelect.addEventListener('change', async e => {
      currentListId = Number(e.target.value);
      await loadItems(currentListId);
    });

    // bootstrap
    (async () => {
      await loadChannelGroups();
      await loadLists();
    })();
  });
})();
