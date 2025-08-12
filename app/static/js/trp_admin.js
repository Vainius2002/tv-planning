(() => {
  'use strict';

  window.addEventListener("DOMContentLoaded", () => {
    const dataDiv = document.querySelector('[data-trp-get]');
    const TRP_GET  = dataDiv.dataset.trpGet;
    const TRP_POST = dataDiv.dataset.trpPost;
    const TRP_BASE = dataDiv.dataset.trpBase;

    const FIELDS = [
      "owner","target_group","primary_label","secondary_label",
      "share_primary","share_secondary","prime_share_primary","prime_share_secondary",
      "price_per_sec_eur"
    ];

    const SEED_AMB = ["A25–55","A25–65","A55+","W25–55","W25–65","M25–65"].map(tg => ({
      owner:"AMB Baltics", target_group:tg, primary_label:"TV3",
      secondary_label:"TV6 + TV8 + TV3 Plus",
      share_primary:"", share_secondary:"", prime_share_primary:"", prime_share_secondary:"",
      price_per_sec_eur:""
    }));

    const SEED_MG = [
      "Visi nuo 4 m.","Visi, 30–65 m.","Moterys, 25–60 m.","Visi, 20–60 m.",
      "Moterys nuo 20 m.","Moterys, 30–60 m.","Visi, 20–65 m.","Moterys nuo 30 m.",
      "Moterys, 30–65 m.","Visi, 25–60 m.","Moterys, 20–60 m.","Moterys, 25–65 m.",
      "Visi, 30–60 m.","Moterys, 20–65 m."
    ].map(tg => ({
      owner:"MG grupė", target_group:tg, primary_label:"LNK", secondary_label:"",
      share_primary:"", share_secondary:"", prime_share_primary:"", prime_share_secondary:"",
      price_per_sec_eur:""
    }));

    const $ = s => document.querySelector(s);
    const tbody = () => $("#grid tbody");
    const ownerFilter = () => $("#ownerFilter");

    async function fetchJSON(url, options) {
      const res = await fetch(url, options);
      let data = null; try { data = await res.json(); } catch {}
      if (!res.ok) throw new Error((data && (data.message||data.error)) || `${res.status} ${res.statusText}`);
      return data;
    }

    async function load(owner="") {
      const url = owner ? `${TRP_GET}?owner=${encodeURIComponent(owner)}` : TRP_GET;
      const rows = await fetchJSON(url);
      tbody().innerHTML = "";
      rows.forEach(addRow);
      updateLayoutForOwner(owner);
    }

    function addRow(row = {}) {
      const tpl = document.getElementById("rowTpl");
      const tr = tpl.content.firstElementChild.cloneNode(true);
      tr.dataset.id = row.id || "";

      const filteredOwner = ownerFilter()?.value || "";
      if (!row.owner && filteredOwner) {
        row.owner = filteredOwner;
        if (filteredOwner === "MG grupė") {
          row.primary_label = row.primary_label || "LNK";
          row.secondary_label = "";
        } else if (filteredOwner === "AMB Baltics") {
          row.primary_label = row.primary_label || "TV3";
          row.secondary_label = row.secondary_label || "TV6 + TV8 + TV3 Plus";
        }
      }

      FIELDS.forEach(f => {
        const td = tr.querySelector(`[data-field="${f}"]`);
        const val = row[f] ?? "";
        td.textContent = (f === "price_per_sec_eur" && val !== "" && val != null)
          ? Number(val).toString()
          : val;
        td.addEventListener("input", () => tr.classList.add("dirty"));
      });

      // lock by default and stash current values
      setRowEditable(tr, false);
      stashOriginal(tr);

      // actions
      tr.querySelector(".edit")?.addEventListener("click", () => {
        stashOriginal(tr);
        setRowEditable(tr, true);
      });

      tr.querySelector(".save")?.addEventListener("click", async () => {
        await saveRow(tr);            // POST (new) or PATCH (existing)
        setRowEditable(tr, false);
        stashOriginal(tr);
      });

      tr.querySelector(".revert")?.addEventListener("click", () => {
        restoreOriginal(tr);
        setRowEditable(tr, false);
      });

      tr.querySelector(".delete")?.addEventListener("click", () => deleteRow(tr));

      // keyboard shortcuts
      tr.addEventListener("keydown", (e) => {
        if (!tr.classList.contains('editing')) return;
        if (e.key === "Enter") { e.preventDefault(); tr.querySelector(".save")?.click(); }
        if (e.key === "Escape") { e.preventDefault(); tr.querySelector(".revert")?.click(); }
      });

      tbody().appendChild(tr);
      return tr;
    }

    // ---- edit helpers ----
    function setRowEditable(tr, editable) {
      tr.classList.toggle('editing', editable);

      const disabledForMG = ['secondary_label','share_secondary','prime_share_secondary'];
      const isMG = (tr.querySelector('[data-field="owner"]')?.textContent.trim() === 'MG grupė');

      tr.querySelectorAll('[data-field]').forEach(td => {
        if (isMG && disabledForMG.includes(td.dataset.field)) {
          td.contentEditable = "false";
          td.classList.add("opacity-50");
        } else {
          td.contentEditable = editable ? "true" : "false";
          if (!editable) td.classList.remove("opacity-50");
        }
      });

      tr.querySelector(".edit")?.classList.toggle("hidden", editable);
      tr.querySelector(".save")?.classList.toggle("hidden", !editable);
      tr.querySelector(".revert")?.classList.toggle("hidden", !editable);
    }

    function stashOriginal(tr) {
      tr.dataset.original = JSON.stringify(getRowPayload(tr));
    }
    function restoreOriginal(tr) {
      const orig = tr.dataset.original ? JSON.parse(tr.dataset.original) : {};
      Object.entries(orig).forEach(([k,v]) => {
        const td = tr.querySelector(`[data-field="${k}"]`);
        if (td) td.textContent = v ?? "";
      });
      tr.classList.remove("dirty");
    }

    // ---- CRUD helpers ----
    function getRowPayload(tr) {
      const payload = {};
      tr.querySelectorAll("[data-field]").forEach(td => {
        payload[td.dataset.field] = td.textContent.trim() || null;
      });
      return payload;
    }

    async function saveRow(tr) {
      const payload = getRowPayload(tr);
      for (const req of ["owner","target_group","primary_label","price_per_sec_eur"]) {
        if (!payload[req]) { alert(`Trūksta lauko: ${req}`); return; }
      }
      const id = tr.dataset.id;
      const url = id ? `${TRP_BASE}/${id}` : TRP_POST;
      const method = id ? "PATCH" : "POST";
      try {
        await fetchJSON(url, {
          method,
          headers: { "Content-Type":"application/json" },
          body: JSON.stringify(payload)
        });
        tr.classList.remove("dirty");
        if (!id) await load(ownerFilter().value); // get new id from DB
      } catch (e) {
        alert("Klaida: " + e.message);
      }
    }

    async function deleteRow(tr) {
      const id = tr.dataset.id;
      if (!id) { tr.remove(); return; }
      if (!confirm("Šalinti eilutę?")) return;
      try {
        await fetchJSON(`${TRP_BASE}/${id}`, { method: "DELETE" });
        tr.remove();
      } catch (e) {
        alert("Klaida: " + e.message);
      }
    }

    function prefillRows(seed) {
      seed.forEach(r => {
        const tr = addRow(r);
        tr.classList.add("dirty");
      });
    }

    async function saveAllDirty() {
      const dirty = Array.from(document.querySelectorAll("tr.dirty"));
      if (!dirty.length) { alert("Nėra pakeistų eilučių."); return; }
      for (const tr of dirty) await saveRow(tr);
      alert("Išsaugota!");
    }

    function updateLayoutForOwner(owner) {
      const isMG = owner === "MG grupė";
      const thSharePrimary = document.getElementById("th-share-primary");
      const thPrimePrimary = document.getElementById("th-prime-primary");
      if (thSharePrimary) thSharePrimary.textContent = isMG ? "LNK kanalo reitingų dalis %" : "TRP dalis (pagr.) %";
      if (thPrimePrimary) thPrimePrimary.textContent = isMG ? "Reitingų dalis po 17 val %" : "Prime dalis (pagr.) %";

      // grey-out secondary fields for MG even when not in edit mode
      const disable = ['secondary_label','share_secondary','prime_share_secondary'];
      document.querySelectorAll("#grid [data-field]").forEach(td => {
        const rowIsMG = td.parentElement?.querySelector('[data-field="owner"]')?.textContent.trim() === 'MG grupė';
        if (rowIsMG && disable.includes(td.dataset.field)) {
          td.contentEditable = "false";
          td.classList.add("opacity-50");
        }
      });
    }

    // Toolbar
    $("#addRow")?.addEventListener("click", () => addRow({}));
    $("#reload")?.addEventListener("click", () => load(ownerFilter().value));
    $("#prefillAMB")?.addEventListener("click", () => prefillRows(SEED_AMB));
    $("#prefillMG")?.addEventListener("click", () => prefillRows(SEED_MG));
    $("#saveDirty")?.addEventListener("click", () => saveAllDirty());
    ownerFilter()?.addEventListener("change", e => load(e.target.value));

    // Initial load
    load();
  });
})();
