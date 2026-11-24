const $ = (id) => document.getElementById(id);
const form = $("item-form");
let editingId = null;
let searchTimer = null;

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || "Something went wrong");
    err.fields = data.errors || null;
    throw err;
  }
  return data;
}

function toast(message, isError = false) {
  const t = $("toast");
  t.textContent = message;
  t.className = "show" + (isError ? " error" : "");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (t.className = ""), 3000);
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function clearErrors() {
  document.querySelectorAll(".error").forEach((e) => (e.textContent = ""));
  document.querySelectorAll(".invalid").forEach((e) => e.classList.remove("invalid"));
}

function showErrors(errors) {
  for (const [field, msg] of Object.entries(errors)) {
    const span = $("err-" + field);
    if (span) span.textContent = msg;
    const input = $(field);
    if (input) input.classList.add("invalid");
  }
}

function readForm() {
  const num = (id) => (form[id].value === "" ? null : Number(form[id].value));
  return {
    title: $("title").value.trim(),
    type: $("type").value,
    genre: $("genre").value.trim(),
    creator: $("creator").value.trim(),
    year: num("year"),
    length: num("length"),
    rating: num("rating"),
    notes: $("notes").value.trim(),
  };
}

function validateClient(d) {
  const errors = {};
  if (!d.title) errors.title = "Title is required";
  if (!d.genre) errors.genre = "Genre is required";
  if (d.rating === null || !Number.isInteger(d.rating) || d.rating < 1 || d.rating > 5)
    errors.rating = "Enter a whole number from 1 to 5";
  if (d.year !== null && (!Number.isInteger(d.year) || d.year < 1000 || d.year > 2100))
    errors.year = "Enter a year from 1000 to 2100";
  if (d.length !== null && (!Number.isInteger(d.length) || d.length < 1))
    errors.length = "Enter a whole number of 1 or more";
  return errors;
}

function resetForm() {
  form.reset();
  editingId = null;
  clearErrors();
  $("form-title").textContent = "Add an item";
  $("submit-btn").textContent = "Add item";
  $("cancel-btn").hidden = true;
}

function startEdit(item) {
  editingId = item._id;
  clearErrors();
  $("title").value = item.title;
  $("type").value = item.type;
  $("genre").value = item.genre;
  $("creator").value = item.creator || "";
  $("year").value = item.year ?? "";
  $("length").value = item.length ?? "";
  $("rating").value = item.rating;
  $("notes").value = item.notes || "";
  $("form-title").textContent = "Edit item";
  $("submit-btn").textContent = "Save changes";
  $("cancel-btn").hidden = false;
  $("form-card").scrollIntoView({ behavior: "smooth" });
}

function renderItem(item) {
  const li = el("li", "item");
  li.appendChild(el("h3", "", item.title));
  li.appendChild(el("div", "stars", "★".repeat(item.rating) + "☆".repeat(5 - item.rating)));

  const meta = [item.type, item.genre, item.creator, item.year,
    item.length ? item.length + (item.type === "book" ? " pages" : " episodes") : null]
    .filter(Boolean)
    .join(" · ");
  li.appendChild(el("div", "meta", meta));
  if (item.notes) li.appendChild(el("p", "notes", item.notes));

  const actions = el("div", "item-actions");
  const editBtn = el("button", "small secondary", "Edit");
  editBtn.addEventListener("click", () => startEdit(item));
  const delBtn = el("button", "small danger", "Delete");
  delBtn.addEventListener("click", () => deleteItem(item));
  actions.append(editBtn, delBtn);
  li.appendChild(actions);
  return li;
}

async function loadItems() {
  const list = $("item-list");
  const status = $("status");
  status.textContent = "Loading...";

  const params = new URLSearchParams();
  if ($("search").value.trim()) params.set("q", $("search").value.trim());
  if ($("filter-type").value) params.set("type", $("filter-type").value);
  try {
    const items = await api("/api/items?" + params.toString());
    list.replaceChildren(...items.map(renderItem));
    status.textContent = items.length
      ? items.length + (items.length === 1 ? " item" : " items")
      : "Nothing here yet. Add your first rating!";
      loadStats();
  } catch (err) {
    list.replaceChildren();
    status.textContent = "Couldn't load items: " + err.message;
  }
}

async function deleteItem(item) {
  if (!confirm(`Delete "${item.title}"? This can't be undone.`)) return;
  try {
    await api("/api/items/" + item._id, { method: "DELETE" });
    if (editingId === item._id) resetForm();
    toast("Deleted");
    loadItems();
  } catch (err) {
    toast(err.message, true);
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearErrors();
  const data = readForm();
  const errors = validateClient(data);
  if (Object.keys(errors).length) {
    showErrors(errors);
    return;
  }
  // Leave out empty optional numbers so the server doesn't see nulls
  if (data.year === null) delete data.year;
  if (data.length === null) delete data.length;

  const btn = $("submit-btn");
  const label = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Saving...";
  try {
    if (editingId) {
      await api("/api/items/" + editingId, { method: "PUT", body: JSON.stringify(data) });
      toast("Changes saved");
    } else {
      await api("/api/items", { method: "POST", body: JSON.stringify(data) });
      toast("Item added");
    }
    resetForm();
    loadItems();
  } catch (err) {
    if (err.fields) showErrors(err.fields);
    toast(err.message === "Something went wrong" ? "Please fix the highlighted fields" : err.message, true);
    btn.textContent = label;
  } finally {
    btn.disabled = false;
    if (!editingId) btn.textContent = "Add item";
    else btn.textContent = "Save changes";
  }
});

$("cancel-btn").addEventListener("click", resetForm);
$("filter-type").addEventListener("change", loadItems);
$("search").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadItems, 250);
});

const pform = $("predict-form");

async function loadStats() {
  try {
    const s = await api("/api/model/stats");
    $("lock-box").hidden = s.unlocked;
    pform.hidden = !s.unlocked;
    if (!s.unlocked) {
      const total = s.count + s.needed;
      $("lock-text").textContent =
        `${s.needed} more ${s.needed === 1 ? "rating" : "ratings"} until predictions unlock (${s.count}/${total})`;
      $("progress-bar").style.width = (s.count / total) * 100 + "%";
      $("prediction").replaceChildren();
    }
  } catch (err) {
    $("lock-text").textContent = "Couldn't load model status.";
  }
}

function renderPrediction(r) {
  const box = $("prediction");
  box.replaceChildren();
  const rounded = Math.round(r.predicted);
  box.appendChild(el("div", "pred-number", r.predicted.toFixed(1) + " / 5"));
  box.appendChild(el("div", "stars", "★".repeat(rounded) + "☆".repeat(5 - rounded)));
  box.appendChild(el("div", "meta", `Confidence: ${r.confidence} · based on ${r.based_on} ratings`));
  const ul = el("ul", "reasons");
  r.reasons.forEach((text) => ul.appendChild(el("li", "", text)));
  box.appendChild(ul);
}

pform.addEventListener("submit", async (e) => {
  e.preventDefault();
  pform.querySelectorAll(".error").forEach((s) => (s.textContent = ""));
  const num = (id) => ($(id).value === "" ? null : Number($(id).value));
  const data = {
    title: $("ptitle").value.trim(),
    type: $("ptype").value,
    genre: $("pgenre").value.trim(),
    creator: $("pcreator").value.trim(),
    year: num("pyear"),
    length: num("plength"),
  };
  let bad = false;
  if (!data.title) { $("perr-title").textContent = "Title is required"; bad = true; }
  if (!data.genre) { $("perr-genre").textContent = "Genre is required"; bad = true; }
  if (bad) return;
  if (data.year === null) delete data.year;
  if (data.length === null) delete data.length;

  const btn = $("predict-btn");
  btn.disabled = true;
  btn.textContent = "Predicting...";
  try {
    const result = await api("/api/predict", { method: "POST", body: JSON.stringify(data) });
    if (result.locked) loadStats();
    else renderPrediction(result);
  } catch (err) {
    if (err.fields) {
      for (const [f, msg] of Object.entries(err.fields)) {
        const span = $("perr-" + f);
        if (span) span.textContent = msg;
      }
    }
    toast(err.message === "Something went wrong" ? "Please fix the highlighted fields" : err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Predict my rating";
  }
});

loadItems();