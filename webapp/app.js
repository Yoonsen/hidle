const elements = {
  filterInput: document.getElementById("filterInput"),
  stats: document.getElementById("stats"),
  docList: document.getElementById("docList"),
  docMeta: document.getElementById("docMeta"),
  docContent: document.getElementById("docContent"),
  concordanceQuery: document.getElementById("concordanceQuery"),
  concordanceContext: document.getElementById("concordanceContext"),
  concordanceMaxHits: document.getElementById("concordanceMaxHits"),
  concordanceButton: document.getElementById("concordanceButton"),
  concordanceStatus: document.getElementById("concordanceStatus"),
  concordanceResults: document.getElementById("concordanceResults"),
};

let documentsCache = [];
let documentsByName = new Map();
let filteredDocuments = [];
let selectedName = "";
let dataSource = "unknown";

function setStatus(text) {
  elements.stats.textContent = text;
}

function formatNumber(value) {
  return new Intl.NumberFormat("nb-NO").format(value);
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function getMatches(text, query, width) {
  const safeQuery = query.trim();
  if (!safeQuery) {
    return [];
  }

  const pattern = new RegExp(escapeRegExp(safeQuery), "gi");
  const snippets = [];
  for (const match of text.matchAll(pattern)) {
    const start = Math.max(0, match.index - width);
    const end = Math.min(text.length, match.index + match[0].length + width);
    const prefix = start > 0 ? "..." : "";
    const suffix = end < text.length ? "..." : "";

    const before = escapeHtml(text.slice(start, match.index));
    const hit = escapeHtml(match[0]);
    const after = escapeHtml(text.slice(match.index + match[0].length, end));
    const snippet = `${prefix}${before}<b>${hit}</b>${after}${suffix}`;
    snippets.push(snippet.replace(/\s+/g, " ").trim());
  }
  return snippets;
}

function renderList() {
  const filter = elements.filterInput.value.trim().toLowerCase();
  filteredDocuments = documentsCache.filter((doc) => {
    const blob = `${doc.name} ${doc.sender} ${doc.year}`.toLowerCase();
    return blob.includes(filter);
  });

  elements.docList.innerHTML = "";
  setStatus(`${filteredDocuments.length} av ${documentsCache.length} dokumenter`);

  if (filteredDocuments.length === 0) {
    const empty = document.createElement("li");
    empty.className = "muted";
    empty.textContent = "Ingen treff for filteret.";
    elements.docList.appendChild(empty);
    return;
  }

  filteredDocuments.forEach((doc) => {
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
  if (dataSource === "static") {
    const doc = documentsByName.get(name);
    if (!doc) {
      throw new Error("Fant ikke dokument i statisk datasett.");
    }
    return doc;
  }

  const response = await fetch(`api/document?name=${encodeURIComponent(name)}`);
  if (!response.ok) {
    throw new Error("Klarte ikke laste dokument via API.");
  }
  return response.json();
}

async function runConcordance() {
  const query = elements.concordanceQuery.value.trim();
  if (!query) {
    elements.concordanceStatus.textContent = "Skriv inn et søkeord.";
    elements.concordanceResults.innerHTML = "";
    return;
  }

  const contextValue = Number.parseInt(elements.concordanceContext.value, 10);
  const maxHitsValue = Number.parseInt(elements.concordanceMaxHits.value, 10);
  const context = Number.isFinite(contextValue) ? Math.min(Math.max(contextValue, 20), 300) : 90;
  const maxHits = Number.isFinite(maxHitsValue) ? Math.min(Math.max(maxHitsValue, 1), 20) : 5;

  const docsToSearch = filteredDocuments.length > 0 ? filteredDocuments : documentsCache;
  elements.concordanceStatus.textContent = `Søker i ${docsToSearch.length} dokumenter...`;
  elements.concordanceResults.innerHTML = "";

  let docsWithHits = 0;
  let totalHits = 0;
  const chunks = [];

  for (let i = 0; i < docsToSearch.length; i += 1) {
    const docMeta = docsToSearch[i];
    let fullDoc = documentsByName.get(docMeta.name);
    if (!fullDoc || !fullDoc.content) {
      // Load on demand when running with API backend.
      fullDoc = await loadDocument(docMeta.name);
      documentsByName.set(docMeta.name, fullDoc);
    }

    const snippets = getMatches(fullDoc.content || "", query, context);
    if (snippets.length === 0) {
      continue;
    }

    docsWithHits += 1;
    totalHits += snippets.length;
    const shown = snippets.slice(0, maxHits);
    const snippetHtml = shown.map((snippet) => `<p class="conc-snippet">- ${snippet}</p>`).join("");
    const extra =
      snippets.length > maxHits
        ? `<p class="muted conc-snippet">... viser ${maxHits} av ${snippets.length} treff</p>`
        : "";

    chunks.push(`
      <article class="conc-doc">
        <div class="conc-doc-head">${escapeHtml(fullDoc.sender || "Ukjent avsender")}</div>
        <div class="conc-doc-meta">${escapeHtml(fullDoc.name)} · ${escapeHtml(fullDoc.year || "ukjent")} · ${formatNumber(snippets.length)} treff</div>
        ${snippetHtml}
        ${extra}
      </article>
    `);
  }

  elements.concordanceStatus.textContent =
    `Treff for "${query}" i ${docsWithHits} dokument(er), totalt ${totalHits} forekomster.`;
  elements.concordanceResults.innerHTML =
    chunks.length > 0 ? chunks.join("") : '<p class="muted">Ingen treff i valgt utvalg.</p>';
}

async function selectDocument(name) {
  selectedName = name;
  renderList();

  elements.docMeta.textContent = "Laster dokument...";
  elements.docContent.textContent = "";

  try {
    const doc = await loadDocument(name);
    documentsByName.set(name, doc);
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
  const staticResponse = await fetch("data/documents.json", { cache: "no-store" });
  if (staticResponse.ok) {
    const data = await staticResponse.json();
    documentsCache = data.documents || [];
    dataSource = "static";
  } else {
    const response = await fetch("api/documents");
    if (!response.ok) {
      throw new Error("Klarte ikke hente dokumentlisten.");
    }
    const data = await response.json();
    documentsCache = data.documents || [];
    dataSource = "api";
  }

  documentsByName = new Map(documentsCache.map((doc) => [doc.name, doc]));
  renderList();

  if (documentsCache.length === 0) {
    if (dataSource === "static") {
      elements.docMeta.textContent = "Ingen dokumenter i statisk datafil.";
    } else {
      elements.docMeta.textContent = "Fant ingen filer i høringer/.";
    }
    return;
  }

  const hashName = decodeURIComponent(window.location.hash.replace(/^#/, ""));
  const defaultDoc = documentsCache.find((doc) => doc.name === hashName) || documentsCache[0];
  await selectDocument(defaultDoc.name);
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch((error) => {
      console.error("Service worker feilet:", error);
    });
  }
}

elements.filterInput.addEventListener("input", renderList);
elements.concordanceButton.addEventListener("click", runConcordance);
elements.concordanceQuery.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    runConcordance();
  }
});

loadDocuments().catch((error) => {
  setStatus("Feil ved lasting.");
  elements.docMeta.textContent = "Kunne ikke laste data fra server.";
  elements.docContent.textContent = String(error);
});

registerServiceWorker();
