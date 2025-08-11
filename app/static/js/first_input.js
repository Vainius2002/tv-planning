document.getElementById("save").onclick = async () => {
      const payload = {
        owner: document.getElementById("owner").value,
        target_group: document.getElementById("tg").value,
        primary_label: document.getElementById("primary_label").value,
        secondary_label: document.getElementById("secondary_label").value || null,
        share_primary: document.getElementById("share_primary").value || null,
        share_secondary: document.getElementById("share_secondary").value || null,
        prime_share_primary: document.getElementById("prime_primary").value || null,
        prime_share_secondary: document.getElementById("prime_secondary").value || null,
        price_per_sec_eur: document.getElementById("price").value
      };

      const res = await fetch("/contacts/trp", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });

      console.log("POST /contacts/trp →", await res.json());

      // Quick sanity: fetch all after save
      const list = await fetch("/contacts/trp").then(r => r.json());
      console.log("All rows:", list);
      alert("Išsaugota!");
    };