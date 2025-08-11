function siusti_pirma() {
    let value = document.getElementById("pirma_value").value;

    fetch("/contacts/first_input", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ number: value })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Response from server:", data);
    })
    .catch(error => {
        console.error("Error:", error);
    });
}