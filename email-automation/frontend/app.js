(function () {
  const gmailEl = document.getElementById("gmail");
  const passwordEl = document.getElementById("password");
  const csvFileEl = document.getElementById("csvFile");
  const csvPreviewEl = document.getElementById("csvPreview");
  const csvTableWrapEl = document.getElementById("csvTableWrap");
  const csvPreviewCountEl = document.getElementById("csvPreviewCount");
  const templateListEl = document.getElementById("templateList");
  const newTemplateIdEl = document.getElementById("newTemplateId");
  const newTemplateSubjectEl = document.getElementById("newTemplateSubject");
  const newTemplateBodyEl = document.getElementById("newTemplateBody");
  const addTemplateBtnEl = document.getElementById("addTemplateBtn");
  const addTemplateStatusEl = document.getElementById("addTemplateStatus");
  const signatureListEl = document.getElementById("signatureList");
  const newSignatureNameEl = document.getElementById("newSignatureName");
  const newSignatureNameFieldEl = document.getElementById("newSignatureNameField");
  const newSignatureEmailEl = document.getElementById("newSignatureEmail");
  const newSignatureTitleEl = document.getElementById("newSignatureTitle");
  const addSignatureBtnEl = document.getElementById("addSignatureBtn");
  const addSignatureStatusEl = document.getElementById("addSignatureStatus");
  const sendBtnEl = document.getElementById("sendBtn");
  const sendProgressEl = document.getElementById("sendProgress");

  let recipients = [];
  let templates = [];
  let signatures = [];
  let selectedTemplateId = null;
  let selectedSignatureId = null;

  function setStatus(el, text, isError) {
    el.textContent = text;
    el.className = "status" + (isError ? " error" : " success");
  }

  function parseCsv(text) {
    const lines = text.trim().split(/\r?\n/);
    if (lines.length < 2) return [];
    const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
    const nameIdx = headers.indexOf("name");
    const emailIdx = headers.indexOf("email");
    if (nameIdx === -1 || emailIdx === -1) return [];
    const rows = [];
    for (let i = 1; i < lines.length; i++) {
      const parts = lines[i].split(",").map((p) => p.trim());
      const name = parts[nameIdx] || "";
      const email = parts[emailIdx] || "";
      if (email) rows.push({ name, email });
    }
    return rows;
  }

  function renderCsvPreview() {
    csvTableWrapEl.style.display = "none";
    csvTableWrapEl.innerHTML = "";
    csvPreviewCountEl.textContent = "";
    if (recipients.length === 0) return;
    csvPreviewEl.textContent = recipients.length + " recipient(s) loaded.";
    csvPreviewEl.className = "status success";
    const table = document.createElement("table");
    table.className = "csv-preview-table";
    table.innerHTML = "<thead><tr><th>Name</th><th>Email</th></tr></thead><tbody></tbody>";
    const tbody = table.querySelector("tbody");
    const maxRows = 50;
    for (let i = 0; i < Math.min(recipients.length, maxRows); i++) {
      const r = recipients[i];
      const tr = document.createElement("tr");
      tr.innerHTML = "<td>" + escapeHtml(r.name) + "</td><td>" + escapeHtml(r.email) + "</td>";
      tbody.appendChild(tr);
    }
    csvTableWrapEl.appendChild(table);
    csvTableWrapEl.style.display = "block";
    if (recipients.length > maxRows) {
      csvPreviewCountEl.textContent = "Showing first " + maxRows + " of " + recipients.length + " recipients.";
    } else {
      csvPreviewCountEl.textContent = recipients.length + " recipient(s) will receive the email.";
    }
  }

  csvFileEl.addEventListener("change", function (e) {
    const file = e.target.files && e.target.files[0];
    if (!file) {
      recipients = [];
      csvPreviewEl.textContent = "";
      csvPreviewEl.className = "status";
      renderCsvPreview();
      updateSendButton();
      return;
    }
    const reader = new FileReader();
    reader.onload = function (ev) {
      recipients = parseCsv(ev.target.result || "");
      if (recipients.length === 0) {
        csvPreviewEl.textContent = "No valid rows (need name and email columns).";
        csvPreviewEl.className = "status error";
        csvTableWrapEl.style.display = "none";
        csvTableWrapEl.innerHTML = "";
        csvPreviewCountEl.textContent = "";
      } else {
        renderCsvPreview();
      }
      updateSendButton();
    };
    reader.readAsText(file);
  });

  function updateSendButton() {
    const hasCreds = gmailEl.value.trim() && passwordEl.value.trim();
    sendBtnEl.disabled = !hasCreds || recipients.length === 0 || !selectedTemplateId;
  }

  gmailEl.addEventListener("input", updateSendButton);
  passwordEl.addEventListener("input", updateSendButton);

  function renderTemplates() {
    templateListEl.innerHTML = "";
    templates.forEach((t) => {
      const card = document.createElement("div");
      card.className = "template-card" + (selectedTemplateId === t.id ? " selected" : "");
      card.innerHTML = "<strong>" + escapeHtml(t.id) + "</strong><small>" + escapeHtml((t.subject || "").slice(0, 60)) + "</small>";
      card.addEventListener("click", function () {
        selectedTemplateId = t.id;
        renderTemplates();
        updateSendButton();
      });
      templateListEl.appendChild(card);
    });
  }

  function renderSignatures() {
    signatureListEl.innerHTML = "";
    signatures.forEach((s) => {
      const card = document.createElement("div");
      card.className = "signature-card" + (selectedSignatureId === s.id ? " selected" : "");
      card.innerHTML = "<strong>" + escapeHtml(s.id) + "</strong><small>" + escapeHtml(s.name || "") + " · " + escapeHtml(s.title || "") + "</small>";
      card.addEventListener("click", function () {
        selectedSignatureId = s.id;
        renderSignatures();
        updateSendButton();
      });
      signatureListEl.appendChild(card);
    });
  }

  function loadSignatures() {
    fetch("/api/signatures")
      .then((r) => r.json())
      .then((data) => {
        signatures = Array.isArray(data) ? data : [];
        if (!selectedSignatureId && signatures.length) selectedSignatureId = signatures[0].id;
        renderSignatures();
        updateSendButton();
      })
      .catch(() => {
        signatures = [];
        renderSignatures();
      });
  }

  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function loadTemplates() {
    fetch("/api/templates")
      .then((r) => r.json())
      .then((data) => {
        templates = Array.isArray(data) ? data : [];
        if (!selectedTemplateId && templates.length) selectedTemplateId = templates[0].id;
        renderTemplates();
        updateSendButton();
      })
      .catch((err) => {
        templateListEl.innerHTML = "<p class='status error'>Failed to load templates: " + err.message + "</p>";
      });
  }

  addSignatureBtnEl.addEventListener("click", function () {
    const signature_name = newSignatureNameEl.value.trim();
    const name = newSignatureNameFieldEl.value.trim();
    const email = newSignatureEmailEl.value.trim();
    const title = newSignatureTitleEl.value.trim();
    if (!signature_name) {
      setStatus(addSignatureStatusEl, "Enter a signature name.", true);
      return;
    }
    addSignatureBtnEl.disabled = true;
    fetch("/api/signatures", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ signature_name, name, email, title }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.error) throw new Error(data.error);
        signatures = data.signatures || [];
        selectedSignatureId = signature_name;
        renderSignatures();
        updateSendButton();
        newSignatureNameEl.value = "";
        newSignatureNameFieldEl.value = "";
        newSignatureEmailEl.value = "";
        newSignatureTitleEl.value = "";
        setStatus(addSignatureStatusEl, "Signature added.", false);
      })
      .catch((err) => setStatus(addSignatureStatusEl, err.message, true))
      .finally(() => (addSignatureBtnEl.disabled = false));
  });

  addTemplateBtnEl.addEventListener("click", function () {
    const id = newTemplateIdEl.value.trim();
    const subject = newTemplateSubjectEl.value.trim();
    const body = newTemplateBodyEl.value.trim();
    if (!id) {
      setStatus(addTemplateStatusEl, "Enter a template ID.", true);
      return;
    }
    addTemplateBtnEl.disabled = true;
    fetch("/api/templates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, subject, body }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.error) throw new Error(data.error);
        templates = data.templates || [];
        selectedTemplateId = id;
        renderTemplates();
        updateSendButton();
        newTemplateIdEl.value = "";
        newTemplateSubjectEl.value = "";
        newTemplateBodyEl.value = "";
        setStatus(addTemplateStatusEl, "Template added.", false);
      })
      .catch((err) => setStatus(addTemplateStatusEl, err.message, true))
      .finally(() => (addTemplateBtnEl.disabled = false));
  });

  sendBtnEl.addEventListener("click", function () {
    const gmail = gmailEl.value.trim();
    const password = passwordEl.value.trim();
    if (!gmail || !password || recipients.length === 0 || !selectedTemplateId) return;
    sendBtnEl.disabled = true;
    sendProgressEl.textContent = "Sending...";
    sendProgressEl.className = "status";

    fetch("/api/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        gmail,
        password,
        templateId: selectedTemplateId,
        signatureId: selectedSignatureId || null,
        recipients,
      }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.error) throw new Error(data.error);
        const failed = data.failed || [];
        const sent = data.sent || 0;
        if (failed.length) {
          sendProgressEl.textContent = "Sent: " + sent + ". Failed: " + failed.length + " (" + failed.map((f) => f.email + ": " + f.error).join("; ") + ")";
          sendProgressEl.className = "status error";
        } else {
          sendProgressEl.textContent = "Done. Sent " + sent + " email(s).";
          sendProgressEl.className = "status success";
        }
      })
      .catch((err) => {
        sendProgressEl.textContent = "Error: " + err.message;
        sendProgressEl.className = "status error";
      })
      .finally(() => {
        sendBtnEl.disabled = false;
        updateSendButton();
      });
  });

  loadTemplates();
  loadSignatures();
  updateSendButton();
})();
