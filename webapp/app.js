const elements = {
  filterInput: document.getElementById("filterInput"),
  stats: document.getElementById("stats"),
  docList: document.getElementById("docList"),
  docMeta: document.getElementById("docMeta"),
  docContent: document.getElementById("docContent"),
};

let documentsCache = [];
let selectedName = "";

function setStatus(text) {
  elements.stats.textContent = text;
}

function formatNumber(value) {
  return new Intl.NumberFormat("nb-NO").format(value);
}

function renderList() {
  const filter = elements.filterInput.value.trim().toLowerCase();
  const filtered = documentsCache.filter((doc) => {
    const blob = `${doc.name} ${doc.sender} ${doc.year}`.toLowerCase();
    return blob.includes(filter);
  });

  elements.docList.innerHTML = "";
  setStatus(`${filtered.length} av ${documentsCache.length} dokumenter`);

  if (filtered.length === 0) {
    const empty = document.createElement("li");
    empty.className = "muted";
    empty.textContent = "Ingen treff for filteret.";
    elements.docList.appendChild(empty);
    return;
  }

  filtered.forEach((doc) => {
    const li = document.createElement("li");
    li.className = "doc-item";

    const button = document.createElement("button");
    button.type = "button";
    button.className = doc.name === selectedName ? "active" : "";
    button.innerHTML = `
      <span class="doc-title">${doc.sender}</span>
      <span class="doc-subtitle">${doc.year} · ${formatNumber(doc.wordCount)} ord</span>
    `;
    button.addEventListener("click", () => selectDocument(doc.name));

    li.appendChild(button);
    elements.docList.appendChild(li);
  });
}

async function loadDocument(name) {
  const response = await fetch(`/api/document?name=${encodeURIComponent(name)}`);
  if (!response.ok) {
    throw new Error("Klarte ikke laste dokument.");
  }
  return response.json();
}

async function selectDocument(name) {
  selectedName = name;
  renderList();

  elements.docMeta.textContent = "Laster dokument...";
  elements.docContent.textContent = "";

  try {
    const doc = await loadDocument(name);
    const modified = new Date(doc.modifiedUtc).toLocaleString("nb-NO");
    elements.docMeta.innerHTML = `
      <strong>${doc.sender}</strong> (${doc.year})<br>
      Fil: <code>${doc.name}</code><br>
      ${formatNumber(doc.wordCount)} ord · ${formatNumber(doc.charCount)} tegn · Oppdatert: ${modified}
    `;
    elements.docContent.textContent = doc.content || "(Tomt dokument)";
    window.location.hash = encodeURIComponent(doc.name);
  } catch (error) {
    elements.docMeta.textContent = "Kunne ikke hente dokument.";
    elements.docContent.textContent = String(error);
  }
}

async function loadDocuments() {
  setStatus("Laster dokumentliste...");
  const response = await fetch("/api/documents");
  if (!response.ok) {
    throw new Error("Klarte ikke hente dokumentlisten.");
  }
  const data = await response.json();
  documentsCache = data.documents || [];
  renderList();

  if (documentsCache.length === 0) {
    elements.docMeta.textContent = "Fant ingen filer i høringer/.";
    return;
  }

  const hashName = decodeURIComponent(window.location.hash.replace(/^#/, ""));
  const defaultDoc = documentsCache.find((doc) => doc.name === hashName) || documentsCache[0];
  await selectDocument(defaultDoc.name);
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch((error) => {
      console.error("Service worker feilet:", error);
    });
  }
}

elements.filterInput.addEventListener("input", renderList);

loadDocuments().catch((error) => {
  setStatus("Feil ved lasting.");
  elements.docMeta.textContent = "Kunne ikke laste data fra server.";
  elements.docContent.textContent = String(error);
});

registerServiceWorker();
