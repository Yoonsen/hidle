const elements = {
  corpusSelect: document.getElementById("corpusSelect"),
  filterInput: document.getElementById("filterInput"),
  stats: document.getElementById("stats"),
  docList: document.getElementById("docList"),
  docMeta: document.getElementById("docMeta"),
  docContent: document.getElementById("docContent"),
  concordanceQuery: document.getElementById("concordanceQuery"),
  concordanceContext: document.getElementById("concordanceContext"),
  concordanceMaxHits: document.getElementById("concordanceMaxHits"),
  concordanceButton: document.getElementById("concordanceButton"),
  concordancePanel: document.getElementById("concordancePanel"),
  concordanceToggle: document.getElementById("concordanceToggle"),
  concordanceStatus: document.getElementById("concordanceStatus"),
  concordanceResults: document.getElementById("concordanceResults"),
};

let documentsCache = [];
let documentsById = new Map();
let filteredDocuments = [];
let selectedDocumentId = "";
let dataSource = "unknown";
let selectedCorpus = "alle";

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

function getDocumentId(doc) {
  return doc.id || doc.name;
}

function normalizeCorpus(value) {
  return value === "foer-2022" || value === "fra-2022" || value === "uten-aar" ? value : "alle";
}

function readCorpusFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return normalizeCorpus(params.get("corpus") || "alle");
}

function syncUrl() {
  const url = new URL(window.location.href);
  if (selectedCorpus === "alle") {
    url.searchParams.delete("corpus");
  } else {
    url.searchParams.set("corpus", selectedCorpus);
  }
  url.hash = selectedDocumentId ? encodeURIComponent(selectedDocumentId) : "";
  window.history.replaceState({}, "", url);
}

function getCorpusDocuments() {
  if (selectedCorpus === "alle") {
    return documentsCache;
  }
  return documentsCache.filter((doc) => doc.corpus === selectedCorpus);
}

function getVisibleDocuments() {
  const filter = elements.filterInput.value.trim().toLowerCase();
  const corpusDocuments = getCorpusDocuments();
  if (!filter) {
    return corpusDocuments;
  }
  return corpusDocuments.filter((doc) => {
    const blob = `${doc.name} ${doc.sender} ${doc.year} ${doc.corpus || ""}`.toLowerCase();
    return blob.includes(filter);
  });
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

function setConcordanceCollapsed(collapsed) {
  elements.concordancePanel.classList.toggle("collapsed", collapsed);
  elements.concordanceToggle.textContent = collapsed ? "Vis" : "Skjul";
}

function renderList() {
  const corpusDocuments = getCorpusDocuments();
  filteredDocuments = getVisibleDocuments();

  elements.docList.innerHTML = "";
  const scopeLabel = selectedCorpus === "alle" ? "alle korpus" : selectedCorpus;
  setStatus(`${filteredDocuments.length} av ${corpusDocuments.length} dokumenter i ${scopeLabel}`);

  if (filteredDocuments.length === 0) {
    const empty = document.createElement("li");
    empty.className = "muted";
    empty.textContent =
      corpusDocuments.length === 0 ? "Ingen dokumenter i valgt korpus." : "Ingen treff for filteret.";
    elements.docList.appendChild(empty);
    return;
  }

  filteredDocuments.forEach((doc) => {
    const li = document.createElement("li");
    li.className = "doc-item";
    const documentId = getDocumentId(doc);

    const button = document.createElement("button");
    button.type = "button";
    button.className = documentId === selectedDocumentId ? "active" : "";
    button.innerHTML = `
      <span class="doc-title">${doc.sender}</span>
      <span class="doc-subtitle">${doc.year} · ${formatNumber(doc.wordCount)} ord</span>
      <span class="doc-action">Les dokument</span>
    `;
    button.addEventListener("click", () => selectDocument(documentId));

    li.appendChild(button);
    elements.docList.appendChild(li);
  });
}

async function loadDocument(documentId) {
  if (dataSource === "static") {
    const doc = documentsById.get(documentId);
    if (!doc) {
      throw new Error("Fant ikke dokument i statisk datasett.");
    }
    return doc;
  }

  const response = await fetch(`api/document?id=${encodeURIComponent(documentId)}`);
  if (!response.ok) {
    throw new Error("Klarte ikke laste dokument via API.");
  }
  return response.json();
}

async function runConcordance() {
  setConcordanceCollapsed(false);

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

  const docsToSearch = filteredDocuments;
  elements.concordanceStatus.textContent = `Søker i ${docsToSearch.length} dokumenter...`;
  elements.concordanceResults.innerHTML = "";

  let docsWithHits = 0;
  let totalHits = 0;
  const chunks = [];

  for (let i = 0; i < docsToSearch.length; i += 1) {
    const docMeta = docsToSearch[i];
    const documentId = getDocumentId(docMeta);
    let fullDoc = documentsById.get(documentId);
    if (!fullDoc || !fullDoc.content) {
      // Load on demand when running with API backend.
      fullDoc = await loadDocument(documentId);
      documentsById.set(documentId, fullDoc);
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
        <button type="button" class="read-doc-button" data-doc-id="${encodeURIComponent(documentId)}">Les dokument</button>
      </article>
    `);
  }

  elements.concordanceStatus.textContent =
    `Treff for "${query}" i ${docsWithHits} dokument(er), totalt ${totalHits} forekomster.`;
  elements.concordanceResults.innerHTML =
    chunks.length > 0 ? chunks.join("") : '<p class="muted">Ingen treff i valgt utvalg.</p>';
}

function resetConcordanceView() {
  elements.concordanceStatus.textContent = "Søk i innholdet i dokumentene.";
  elements.concordanceResults.innerHTML = "";
}

async function selectDocument(documentId) {
  selectedDocumentId = documentId;
  renderList();
  resetConcordanceView();
  setConcordanceCollapsed(true);

  elements.docMeta.textContent = "Laster dokument...";
  elements.docContent.textContent = "";

  try {
    const doc = await loadDocument(documentId);
    documentsById.set(documentId, doc);
    const modified = new Date(doc.modifiedUtc).toLocaleString("nb-NO");
    const corpusLabel = doc.corpus ? `<br>Korpus: <code>${doc.corpus}</code>` : "";
    elements.docMeta.innerHTML = `
      <strong>${doc.sender}</strong> (${doc.year})<br>
      Fil: <code>${doc.name}</code><br>
      ${corpusLabel}
      ${formatNumber(doc.wordCount)} ord · ${formatNumber(doc.charCount)} tegn · Oppdatert: ${modified}
    `;
    elements.docContent.textContent = doc.content || "(Tomt dokument)";
    syncUrl();
    elements.docContent.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    elements.docMeta.textContent = "Kunne ikke hente dokument.";
    elements.docContent.textContent = String(error);
  }
}

async function loadDocuments() {
  setStatus("Laster dokumentliste...");
  selectedCorpus = readCorpusFromUrl();
  elements.corpusSelect.value = selectedCorpus;
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

  documentsById = new Map(documentsCache.map((doc) => [getDocumentId(doc), doc]));
  renderList();

  if (documentsCache.length === 0) {
    if (dataSource === "static") {
      elements.docMeta.textContent = "Ingen dokumenter i statisk datafil.";
    } else {
      elements.docMeta.textContent = "Fant ingen filer i høringer/.";
    }
    return;
  }

  const hashDocumentId = decodeURIComponent(window.location.hash.replace(/^#/, ""));
  const defaultDoc =
    filteredDocuments.find((doc) => getDocumentId(doc) === hashDocumentId || doc.name === hashDocumentId) ||
    filteredDocuments[0] ||
    documentsCache.find((doc) => getDocumentId(doc) === hashDocumentId || doc.name === hashDocumentId) ||
    documentsCache[0];
  if (!defaultDoc) {
    elements.docMeta.textContent = "Ingen dokumenter i valgt korpus.";
    elements.docContent.textContent = "";
    return;
  }
  await selectDocument(getDocumentId(defaultDoc));
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch((error) => {
      console.error("Service worker feilet:", error);
    });
  }
}

elements.filterInput.addEventListener("input", renderList);
elements.corpusSelect.addEventListener("change", () => {
  selectedCorpus = normalizeCorpus(elements.corpusSelect.value);
  renderList();
  const selectedStillVisible = filteredDocuments.some((doc) => getDocumentId(doc) === selectedDocumentId);
  if (selectedStillVisible) {
    syncUrl();
    return;
  }
  const nextDoc = filteredDocuments[0];
  if (nextDoc) {
    selectDocument(getDocumentId(nextDoc)).catch((error) => {
      elements.docMeta.textContent = "Kunne ikke åpne dokument.";
      elements.docContent.textContent = String(error);
    });
    return;
  }
  selectedDocumentId = "";
  syncUrl();
  elements.docMeta.textContent = "Ingen dokumenter i valgt korpus.";
  elements.docContent.textContent = "";
  resetConcordanceView();
});
elements.concordanceButton.addEventListener("click", runConcordance);
elements.concordanceToggle.addEventListener("click", () => {
  const collapsed = !elements.concordancePanel.classList.contains("collapsed");
  setConcordanceCollapsed(collapsed);
});
elements.concordanceResults.addEventListener("click", (event) => {
  const rawTarget = event.target;
  const button =
    rawTarget instanceof Element
      ? rawTarget.closest(".read-doc-button")
      : rawTarget instanceof Node && rawTarget.parentElement
        ? rawTarget.parentElement.closest(".read-doc-button")
        : null;
  if (!button) {
    return;
  }

  const rawDocumentId = button.getAttribute("data-doc-id");
  if (!rawDocumentId) {
    return;
  }

  const documentId = decodeURIComponent(rawDocumentId);
  selectDocument(documentId).catch((error) => {
    elements.docMeta.textContent = "Kunne ikke åpne dokument.";
    elements.docContent.textContent = String(error);
  });
});
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
