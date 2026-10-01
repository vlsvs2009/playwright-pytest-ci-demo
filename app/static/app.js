"use strict";

const TOKEN_KEY = "so.token";
const USER_KEY = "so.user";
const STATUS_LABELS = { new: "New", in_progress: "In progress", done: "Done" };
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

const $ = (selector) => document.querySelector(selector);
let latestListRequest = 0;

// ---------- API ----------
async function api(path, { method = "GET", body } = {}) {
  const headers = { Accept: "application/json" };
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 401 && path !== "/api/auth/login") {
    clearSession();
    showLogin();
    throw new Error("Session expired");
  }
  return response;
}

function describeValidationErrors(payload) {
  if (!payload || !Array.isArray(payload.detail)) return ["Request was rejected by the server."];
  return payload.detail.map((err) => `${err.loc[err.loc.length - 1]}: ${err.msg}`);
}

// ---------- Session ----------
function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function showLogin() {
  $("#orders-view").hidden = true;
  $("#login-view").hidden = false;
  $("#username").focus();
}

function showOrders() {
  $("#login-view").hidden = true;
  $("#orders-view").hidden = false;
  $('[data-testid="current-user"]').textContent = localStorage.getItem(USER_KEY) || "";
  loadOrders();
}

async function onLogin(event) {
  event.preventDefault();
  const error = $("#login-error");
  const username = $("#username").value.trim();
  const password = $("#password").value;
  error.hidden = true;

  if (!username || !password) {
    showError(error, ["Enter your username and password."]);
    return;
  }
  const response = await api("/api/auth/login", { method: "POST", body: { username, password } });
  if (!response.ok) {
    showError(error, ["Invalid username or password."]);
    return;
  }
  const { access_token: token } = await response.json();
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, username);
  $("#login-form").reset();
  showOrders();
}

async function onLogout() {
  try {
    await api("/api/auth/logout", { method: "POST" });
  } catch (_) {
    /* already signed out */
  }
  clearSession();
  showLogin();
}

// ---------- Orders ----------
async function loadOrders() {
  const requestId = ++latestListRequest;
  const table = $('[data-testid="orders-table"]');
  const filter = $("#status-filter").value;
  table.setAttribute("aria-busy", "true");

  const response = await api(filter ? `/api/orders?status=${encodeURIComponent(filter)}` : "/api/orders");
  const data = await response.json();
  if (requestId !== latestListRequest) return; // a newer request superseded this one

  renderOrders(data.items);
  table.setAttribute("aria-busy", "false");
}

function renderOrders(orders) {
  const body = $("#orders-body");
  body.replaceChildren(...orders.map(renderRow));
  $('[data-testid="orders-count"]').textContent = `${orders.length} ${orders.length === 1 ? "order" : "orders"}`;
  $('[data-testid="empty-state"]').hidden = orders.length > 0;
}

function cell(text, testId, className) {
  const td = document.createElement("td");
  td.textContent = text;
  if (testId) td.dataset.testid = testId;
  if (className) td.className = className;
  return td;
}

function renderRow(order) {
  const tr = document.createElement("tr");
  tr.dataset.testid = "order-row";
  tr.dataset.orderId = String(order.id);

  const badge = document.createElement("span");
  badge.className = `badge badge-${order.status}`;
  badge.dataset.testid = "order-status";
  badge.textContent = STATUS_LABELS[order.status] || order.status;
  const statusCell = document.createElement("td");
  statusCell.append(badge);

  const buttons = document.createElement("div");
  buttons.className = "actions";
  if (order.status !== "done") {
    buttons.append(button("Mark done", "mark-done", () => markDone(order.id)));
  }
  buttons.append(button("Delete", "delete-order", () => deleteOrder(order.id), "danger"));
  const actions = document.createElement("td");
  actions.append(buttons);

  tr.append(
    cell(`#${order.id}`, "order-id", "muted"),
    cell(order.customer, "order-customer"),
    cell(order.service, "order-service"),
    cell(money.format(order.price), "order-price", "num"),
    statusCell,
    actions,
  );
  return tr;
}

function button(label, testId, onClick, className) {
  const el = document.createElement("button");
  el.type = "button";
  el.textContent = label;
  el.dataset.testid = testId;
  if (className) el.className = className;
  el.addEventListener("click", onClick);
  return el;
}

async function markDone(id) {
  await api(`/api/orders/${id}`, { method: "PATCH", body: { status: "done" } });
  await loadOrders();
}

async function deleteOrder(id) {
  await api(`/api/orders/${id}`, { method: "DELETE" });
  await loadOrders();
}

function validateOrder(form) {
  const errors = [];
  const invalid = [];
  if (form.customer.length < 2) {
    errors.push("Customer name must be at least 2 characters.");
    invalid.push("customer");
  }
  if (form.service.length < 2) {
    errors.push("Service must be at least 2 characters.");
    invalid.push("service");
  }
  if (form.priceRaw === "" || Number.isNaN(form.price)) {
    errors.push("Price is required.");
    invalid.push("price");
  } else if (form.price <= 0) {
    errors.push("Price must be greater than 0.");
    invalid.push("price");
  }
  return { errors, invalid };
}

async function onCreateOrder(event) {
  event.preventDefault();
  const formEl = $("#order-form");
  const error = $("#form-error");
  const submit = formEl.querySelector('button[type="submit"]');
  const form = {
    customer: $("#customer").value.trim(),
    service: $("#service").value.trim(),
    priceRaw: $("#price").value.trim(),
    price: Number.parseFloat($("#price").value),
    status: $("#status").value,
  };

  for (const id of ["customer", "service", "price"]) $(`#${id}`).removeAttribute("aria-invalid");
  error.hidden = true;

  const { errors, invalid } = validateOrder(form);
  if (errors.length) {
    invalid.forEach((id) => $(`#${id}`).setAttribute("aria-invalid", "true"));
    showError(error, errors);
    return;
  }

  submit.disabled = true;
  try {
    const response = await api("/api/orders", {
      method: "POST",
      body: { customer: form.customer, service: form.service, price: form.price, status: form.status },
    });
    if (response.status === 422) {
      showError(error, describeValidationErrors(await response.json()));
      return;
    }
    if (!response.ok) {
      showError(error, [`Could not save the order (HTTP ${response.status}).`]);
      return;
    }
    formEl.reset();
    await loadOrders();
  } finally {
    submit.disabled = false;
  }
}

function showError(container, messages) {
  container.replaceChildren(
    ...messages.map((message) => {
      const line = document.createElement("div");
      line.textContent = message;
      return line;
    }),
  );
  container.hidden = false;
}

// ---------- Boot ----------
document.addEventListener("DOMContentLoaded", () => {
  $("#login-form").addEventListener("submit", onLogin);
  $("#order-form").addEventListener("submit", onCreateOrder);
  $("#logout").addEventListener("click", onLogout);
  $("#status-filter").addEventListener("change", loadOrders);

  if (localStorage.getItem(TOKEN_KEY)) showOrders();
  else showLogin();
});
