#!/usr/bin/env python3
"""Local web console for AdsPower ChatGPT browser profiles."""

from __future__ import annotations

import json
import html as html_lib
import os
import random
import re
import socket
import subprocess
import sys
import threading
import time
import webbrowser
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib import error, request
from urllib.parse import parse_qs, quote, urlparse

from adspower_open_chatgpt import (
    DEFAULT_BASE_URL,
    DEFAULT_PROXY_FILE,
    DEFAULT_TARGET_URL,
    AdsPowerError,
    check_connection,
    create_profile,
    load_proxies,
    normalize_proxy_line,
    open_profile,
    open_url_by_debug_port,
    request_json,
)


DEFAULT_PORT = 8765
DEFAULT_MAIL_FILE = "mail_accounts.json"
DEFAULT_COMPLETED_FILE = "completed_accounts.txt"
DEFAULT_COMPLETED_META_FILE = "completed_profiles.json"
GITHUB_REPO = "ziyisj/own-tools"
COUNTRY_CACHE: Dict[str, str] = {}


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AdsPower 环境管理</title>
  <style>
    :root {
      --bg: #f5f7fb;
      --panel: #fff;
      --text: #111827;
      --muted: #5b6472;
      --line: #d8dde6;
      --blue: #2563eb;
      --red: #dc2626;
      --green: #059669;
      --shadow: 0 1px 2px rgba(15, 23, 42, .06);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: clamp(12px, .78vw, 14px)/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    }
    header {
      padding: 14px 22px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      position: sticky;
      top: 0;
      z-index: 10;
    }
    h1 { font-size: 20px; margin: 0; }
    h2 { font-size: 16px; margin: 0 0 10px; }
    main { padding: 16px; display: grid; gap: 14px; max-width: 1680px; margin: 0 auto; }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 14px;
      box-shadow: var(--shadow);
    }
    .grid {
      display: grid;
      grid-template-columns: 1.1fr 1.1fr 110px 110px 1.3fr 1.2fr 110px;
      gap: 10px;
      align-items: end;
    }
    .two {
      display: grid;
      grid-template-columns: 1fr;
      gap: 14px;
      align-items: start;
    }
    .section-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
    }
    .table-wrap {
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }
    .mail-view {
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 12px;
      align-items: stretch;
    }
    .mail-list {
      border: 1px solid var(--line);
      border-radius: 6px;
      overflow: hidden;
      background: #fff;
      max-height: 360px;
      overflow-y: auto;
    }
    .mail-item {
      display: grid;
      gap: 4px;
      padding: 10px;
      border-bottom: 1px solid var(--line);
      cursor: pointer;
    }
    .mail-item:hover, .mail-item.active { background: #eff6ff; }
    .mail-item-code {
      color: #1d4ed8;
      font: 700 18px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
    }
    .mail-panel {
      display: grid;
      gap: 8px;
    }
    label { display: grid; gap: 5px; color: var(--muted); font-size: 12px; }
    input, textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 4px;
      padding: 8px 10px;
      color: var(--text);
      background: #fff;
      font: inherit;
    }
    textarea { min-height: 180px; resize: vertical; }
    #mailBox { min-height: 300px; }
    button {
      border: 0;
      border-radius: 4px;
      padding: 9px 12px;
      color: #fff;
      background: #374151;
      cursor: pointer;
      font: inherit;
      white-space: nowrap;
    }
    td button {
      padding: 5px 8px;
      font-size: inherit;
    }
    td select {
      padding: 5px 8px;
      font-size: inherit;
      max-width: 100%;
    }
    button.primary { background: var(--blue); }
    button.danger { background: var(--red); }
    button.success { background: var(--green); }
    button:disabled { opacity: .55; cursor: not-allowed; }
    .row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    table {
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      table-layout: fixed;
      min-width: 1120px;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 8px;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    th { background: #eef2f7; font-weight: 600; }
    thead th { position: sticky; top: 0; z-index: 1; }
    td:first-child, th:first-child { width: 42px; }
    .id { width: 105px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    .proxy { width: 230px; }
    .state-cell { cursor: pointer; }
    .muted { color: var(--muted); }
    #statusBar {
      padding: 10px 16px;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 6px;
      color: #1e40af;
      font-weight: 700;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      min-width: 68px;
      justify-content: center;
      border-radius: 999px;
      padding: 3px 8px;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid transparent;
    }
    .badge-idle { color: #475569; background: #f1f5f9; border-color: #cbd5e1; }
    .badge-checking { color: #92400e; background: #fef3c7; border-color: #f59e0b; }
    .badge-ok { color: #065f46; background: #d1fae5; border-color: #10b981; }
    .badge-fail { color: #991b1b; background: #fee2e2; border-color: #ef4444; }
    #mailCode {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 180px;
      min-height: 64px;
      border: 1px solid #bfdbfe;
      border-radius: 6px;
      background: #eff6ff;
      color: #1d4ed8;
      font: 700 34px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
      letter-spacing: 2px;
      margin: 8px 0 12px;
    }
    .code-cell {
      font: 700 18px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
      color: #1d4ed8;
      letter-spacing: 1px;
    }
    .copy-email {
      color: #2563eb;
      cursor: pointer;
      text-decoration: underline;
      text-underline-offset: 2px;
    }
    .copy-code {
      color: #1d4ed8;
      cursor: pointer;
      text-decoration: underline;
      text-underline-offset: 2px;
    }
    #log {
      white-space: pre-wrap;
      min-height: 88px;
      max-height: 180px;
      overflow: auto;
      background: #0f172a;
      color: #dbeafe;
      border-radius: 4px;
      padding: 10px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    }
    @media (max-width: 1200px) {
      .grid, .two, .mail-view {
        grid-template-columns: 1fr;
      }
      header {
        align-items: flex-start;
        flex-direction: column;
      }
      .section-head {
        align-items: flex-start;
        flex-direction: column;
      }
    }
  </style>
</head>
<body>
  <header>
    <h1>AdsPower 环境管理</h1>
  </header>

  <main>
    <div id="statusBar">就绪</div>

    <section class="grid">
      <label>API 地址 <input id="baseUrl" value="http://localhost:50325"></label>
      <label>API Key <input id="apiKey" type="password" value=""></label>
      <button class="primary" onclick="refreshProfiles()">连接/刷新</button>
      <label>分组 ID <input id="groupId" value="0"></label>
      <label>打开网址 <input id="targetUrl" value="https://www.chatgpt.com"></label>
      <label>代理文件 <input id="proxyFile" value="proxies.txt"></label>
      <button onclick="updateProject()">在线更新</button>
    </section>

    <div class="two">
      <section>
        <div class="section-head">
          <h2>创建环境</h2>
        </div>
        <p class="muted">支持普通邮箱，或 <code>邮箱----密码----邮件API地址</code>。邮箱只写入环境名称和备注；邮件只在下方读取展示。</p>
        <label>邮箱列表（每行一个，可为空）
          <textarea id="emails" placeholder="name@example.com----password----https://example.com/latest/name@example.com"></textarea>
        </label>
        <div class="row" style="margin-top:10px">
          <label style="width:110px">空环境数量 <input id="count" type="number" min="1" value="1"></label>
          <label style="display:flex; align-items:center; gap:6px; color:var(--text); font-size:14px">
            <input id="openAfter" type="checkbox" checked style="width:auto"> 创建后打开
          </label>
        </div>
        <div class="row" style="margin-top:12px">
          <button id="createEmailBtn" class="success" onclick="createFromEmails()">按邮箱创建</button>
          <button id="createEmptyBtn" onclick="createEmpty()">创建空环境</button>
        </div>
      </section>

      <section>
        <div class="section-head">
          <h2>环境列表 <span id="countText" class="muted"></span></h2>
          <div class="row">
            <button onclick="toggleAllProfiles(true)">全选</button>
            <button onclick="toggleAllProfiles(false)">取消全选</button>
            <button class="danger" onclick="deleteSelected()">删除选中</button>
            <button class="success" onclick="exportCompleted()">导出完成数据</button>
            <button onclick="fetchAllMail()">读取全部邮件</button>
            <label style="display:flex; align-items:center; gap:6px; color:var(--text); font-size:14px">
              <input id="autoMail" type="checkbox" onchange="toggleAutoMail()" style="width:auto"> 自动读取验证码
            </label>
            <label style="width:92px">间隔秒 <input id="mailInterval" type="number" min="5" max="120" value="15"></label>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th></th><th>序号</th><th class="id">环境ID</th><th>名称</th><th>邮箱备注</th><th>邮件</th><th>验证码</th><th class="proxy">代理</th><th>代理状态</th><th>快捷删除</th><th>类型</th><th>完成</th>
              </tr>
            </thead>
            <tbody id="profilesBody"></tbody>
          </table>
        </div>
      </section>
    </div>

    <section>
      <div class="section-head">
        <h2>添加代理</h2>
      </div>
      <p class="muted">一行一个，支持 <code>IP:端口:账号:密码</code>、<code>host:port:user:pass</code> 或 <code>socks5://user:pass@host:port</code>。默认按 SOCKS5 保存。</p>
      <label>代理内容
        <textarea id="proxyInput" placeholder="175.208.116.50:11201:tjz:vkq"></textarea>
      </label>
      <div class="row" style="margin-top:10px">
        <button class="success" onclick="addProxies()">识别并添加代理</button>
      </div>
    </section>

    <section>
      <div class="section-head">
        <h2>邮件读取</h2>
      </div>
      <p class="muted">从导入邮箱里的 API 地址读取最新邮件内容，不通过 AdsPower。</p>
      <div class="mail-view">
        <div>
          <div class="muted" style="margin-bottom:6px">已读取邮箱</div>
          <div id="mailList" class="mail-list">
            <div class="mail-item">
              <span class="muted">暂无邮件记录</span>
            </div>
          </div>
        </div>
        <div class="mail-panel">
          <div>当前验证码</div>
          <div id="mailCode">------</div>
          <label>当前邮箱
            <input id="mailCurrentEmail" readonly placeholder="点击环境列表里的“读取邮件”后显示">
          </label>
          <label>最新邮件内容
            <textarea id="mailBox" readonly placeholder="不同邮箱会分开保存，点击左侧邮箱切换查看"></textarea>
          </label>
        </div>
      </div>
    </section>

    <section>
      <div class="section-head">
        <h2>已添加代理列表 <span id="proxyCountText" class="muted"></span></h2>
        <div class="row">
          <button onclick="refreshProxies()">刷新代理列表</button>
          <button class="primary" onclick="checkSelectedProxies()">检测选中</button>
          <button class="primary" onclick="checkAllProxies()">检测全部</button>
          <button class="danger" onclick="deleteSelectedProxies()">删除选中</button>
          <label style="width:92px">并发数 <input id="proxyConcurrency" type="number" min="1" max="30" value="5"></label>
          <label style="width:92px">超时秒 <input id="proxyTimeout" type="number" min="2" max="30" value="8"></label>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th></th><th>#</th><th>类型</th><th>主机</th><th>端口</th><th>用户名</th><th>状态</th><th>出口IP</th><th>国家</th><th>耗时</th>
            </tr>
          </thead>
          <tbody id="proxiesBody"></tbody>
        </table>
      </div>
    </section>

    <section>
      <h2>日志</h2>
      <div id="log"></div>
    </section>
  </main>

  <script>
    let profiles = [];
    let proxies = [];
    let profileCodes = {};
    let mailResults = {};
    let completedProfiles = {};
    let currentMailEmail = "";
    let autoMailTimer = null;
    let profileRefreshing = false;
    let mailReading = false;
    const envApiKey = "__API_KEY__";
    if (envApiKey) document.getElementById("apiKey").value = envApiKey;

    function cfg() {
      return {
        base_url: document.getElementById("baseUrl").value.trim(),
        api_key: document.getElementById("apiKey").value.trim(),
        group_id: document.getElementById("groupId").value.trim() || "0",
        target_url: document.getElementById("targetUrl").value.trim(),
        proxy_file: document.getElementById("proxyFile").value.trim(),
      };
    }
    function log(msg) {
      const box = document.getElementById("log");
      box.textContent += `${new Date().toLocaleTimeString()}  ${msg}\n`;
      box.scrollTop = box.scrollHeight;
      document.getElementById("statusBar").textContent = msg;
    }
    async function api(path, body) {
      const res = await fetch(path, {
        method: body ? "POST" : "GET",
        headers: body ? {"Content-Type": "application/json"} : {},
        body: body ? JSON.stringify(body) : undefined,
      });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "请求失败");
      return data;
    }
    function selectedIds() {
      return [...document.querySelectorAll(".profile-check:checked")].map(el => el.value);
    }
    function toggleAllProfiles(checked) {
      document.querySelectorAll(".profile-check").forEach(el => { el.checked = checked; });
      log(checked ? "已全选环境" : "已取消全选环境");
    }
    function renderProfiles(items) {
      profiles = items;
      document.getElementById("countText").textContent = `(${items.length})`;
      const body = document.getElementById("profilesBody");
      body.innerHTML = "";
      for (const item of items) {
        const proxy = item.user_proxy_config || {};
        const remark = item.remark || "";
        const email = remark.startsWith("email:") ? remark.replace("email:", "").trim() : remark;
        const proxyPayload = proxy.proxy_host ? {
          host: proxy.proxy_host,
          port: proxy.proxy_port,
          user: proxy.proxy_user || "",
          password: proxy.proxy_password || "",
        } : null;
        const currentProxyValue = proxyPayload
          ? `${proxyPayload.host}:${proxyPayload.port}:${proxyPayload.user}:${proxyPayload.password}`
          : "";
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><input class="profile-check" type="checkbox" value="${item.user_id || ""}"></td>
          <td>${item.serial_number || ""}</td>
          <td class="id"></td>
          <td>${item.name || ""}</td>
          <td></td>
          <td></td>
          <td class="code-cell" id="mail-code-${item.user_id || ""}">------</td>
          <td class="proxy"></td>
          <td id="profile-proxy-status-${item.user_id || ""}" class="state-cell"><span class="badge badge-idle">点此检测</span></td>
          <td></td>
          <td></td>
          <td></td>`;
        if (email) {
          const emailSpan = document.createElement("span");
          emailSpan.className = "copy-email";
          emailSpan.textContent = email;
          emailSpan.title = "点击复制邮箱";
          emailSpan.onclick = () => {
            copyEmail(email);
            if (mailResults[email]) showMailResult(email);
          };
          tr.children[4].appendChild(emailSpan);

          const button = document.createElement("button");
          button.textContent = "读取邮件";
          button.onclick = () => fetchMail(email, item.user_id || "");
          tr.children[5].appendChild(button);

          const savedCode = profileCodes[item.user_id || ""];
          if (savedCode) setCodeCell(tr.children[6], savedCode);
        }
        const idLink = document.createElement("span");
        idLink.className = "copy-email";
        idLink.textContent = item.user_id || "";
        idLink.title = "点击打开环境";
        idLink.onclick = () => showProfile(item.user_id || "");
        tr.children[2].appendChild(idLink);

        const select = createProxySelect(item.user_id || "", currentProxyValue);
        tr.children[7].appendChild(select);
        if (proxyPayload) {
          tr.children[8].onclick = () => checkProfileProxy(item.user_id || "", proxyPayload);
          tr.children[8].title = "点击检测当前环境代理";
        }
        const deleteButton = document.createElement("button");
        deleteButton.textContent = "删除";
        deleteButton.className = "danger";
        deleteButton.onclick = () => deleteProfiles([item.user_id || ""]);
        tr.children[9].appendChild(deleteButton);

        const completed = completedProfiles[item.user_id || ""];
        const tierSelect = document.createElement("select");
        tierSelect.id = `tier-select-${item.user_id || ""}`;
        for (const tier of ["5X", "20X"]) {
          const option = document.createElement("option");
          option.value = tier;
          option.textContent = tier;
          option.selected = completed ? completed.tier === tier : tier === "5X";
          tierSelect.appendChild(option);
        }
        tierSelect.disabled = Boolean(completed);
        tr.children[10].appendChild(tierSelect);

        const doneButton = document.createElement("button");
        doneButton.textContent = completed ? "已完成" : "完成";
        doneButton.className = "success";
        doneButton.disabled = Boolean(completed);
        doneButton.id = `complete-btn-${item.user_id || ""}`;
        doneButton.onclick = () => completeProfile(item.user_id || "", email);
        tr.children[11].appendChild(doneButton);
        body.appendChild(tr);
      }
    }
    function renderProxies(items) {
      proxies = items;
      renderProfiles(profiles);
      document.getElementById("proxyCountText").textContent = `(${items.length})`;
      const body = document.getElementById("proxiesBody");
      body.innerHTML = "";
      for (const item of items) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><input class="proxy-check" type="checkbox" value="${item.index}"></td>
          <td>${item.index + 1}</td>
          <td>${item.type}</td>
          <td>${item.host}</td>
          <td>${item.port}</td>
          <td>${item.user}</td>
          <td id="proxy-status-${item.index}"><span class="badge badge-idle">未检测</span></td>
          <td id="proxy-ip-${item.index}"></td>
          <td id="proxy-country-${item.index}"></td>
          <td id="proxy-ms-${item.index}"></td>`;
        body.appendChild(tr);
      }
    }
    function proxyOptionLabel(item) {
      return `${item.index + 1}. ${item.user}`;
    }
    function createProxySelect(profileId, currentValue = "") {
      const select = document.createElement("select");
      select.id = `proxy-select-${profileId}`;
      const empty = document.createElement("option");
      empty.value = "";
      empty.textContent = proxies.length ? "选择已有代理" : "暂无代理";
      select.appendChild(empty);
      for (const proxy of proxies) {
        const option = document.createElement("option");
        option.value = proxy.value;
        option.textContent = proxyOptionLabel(proxy);
        option.selected = proxy.value === currentValue;
        select.appendChild(option);
      }
      select.onchange = () => {
        if (select.value) updateProfileProxy(profileId, select.value);
      };
      return select;
    }
    async function refreshProfiles() {
      if (profileRefreshing) return;
      profileRefreshing = true;
      try {
        const data = await api(`/api/profiles?config=${encodeURIComponent(JSON.stringify(cfg()))}`);
        renderProfiles(data.profiles);
        log(`刷新完成，共 ${data.profiles.length} 个环境`);
        if (document.getElementById("autoMail")?.checked) {
          fetchAllMail(true);
        }
      } catch (err) { log(`错误：${err.message}`); }
      finally { profileRefreshing = false; }
    }
    async function refreshProxies() {
      try {
        const data = await api(`/api/proxies?proxy_file=${encodeURIComponent(document.getElementById("proxyFile").value.trim())}`);
        renderProxies(data.proxies);
        log(`代理列表刷新完成，共 ${data.proxies.length} 条`);
      } catch (err) { log(`错误：${err.message}`); }
    }
    async function createFromEmails() {
      const emails = parseEmailInput();
      if (!emails.length) { log("请先输入邮箱，或使用创建空环境"); return; }
      await createProfiles(emails);
    }
    function parseEmailInput() {
      return document.getElementById("emails").value.split(/\n+/).map(line => {
        const value = line.trim();
        if (!value) return null;
        const parts = value.split("----");
        if (parts.length >= 3) {
          return {email: parts[0].trim(), password: parts[1].trim(), mail_url: parts.slice(2).join("----").trim()};
        }
        return {email: value, password: "", mail_url: ""};
      }).filter(Boolean);
    }
    async function createEmpty() {
      const count = Math.max(1, Number(document.getElementById("count").value || 1));
      await createProfiles(Array.from({length: count}, () => null));
    }
    async function createProfiles(emails) {
      const createEmailBtn = document.getElementById("createEmailBtn");
      const createEmptyBtn = document.getElementById("createEmptyBtn");
      createEmailBtn.disabled = true;
      createEmptyBtn.disabled = true;
      try {
        log(`开始创建 ${emails.length} 个环境...`);
        const data = await api("/api/create", {...cfg(), emails, open_after: document.getElementById("openAfter").checked});
        log(data.message);
        renderProfiles(data.profiles);
      } catch (err) { log(`错误：${err.message}`); }
      finally {
        createEmailBtn.disabled = false;
        createEmptyBtn.disabled = false;
      }
    }
    async function openSelected() {
      const ids = selectedIds();
      if (!ids.length) { log("请先选择环境"); return; }
      try {
        const data = await api("/api/open", {...cfg(), ids});
        log(data.message);
      } catch (err) { log(`错误：${err.message}`); }
    }
    async function openAll() {
      const ids = profiles.map(p => p.user_id).filter(Boolean);
      if (!ids.length) { log("没有可打开的环境"); return; }
      try {
        const data = await api("/api/open", {...cfg(), ids});
        log(data.message);
      } catch (err) { log(`错误：${err.message}`); }
    }
    async function showProfile(profileId) {
      if (!profileId) return;
      try {
        const data = await api("/api/open", {...cfg(), ids: [profileId]});
        log(data.message);
      } catch (err) { log(`错误：${err.message}`); }
    }
    async function deleteSelected() {
      const ids = selectedIds();
      if (!ids.length) { log("请先选择环境"); return; }
      await deleteProfiles(ids);
    }
    async function deleteProfiles(ids) {
      ids = ids.filter(Boolean);
      if (!ids.length) return;
      if (!confirm(`确认删除 ${ids.length} 个环境？`)) return;
      try {
        const data = await api("/api/delete", {...cfg(), ids});
        log(data.message);
        renderProfiles(data.profiles);
      } catch (err) { log(`错误：${err.message}`); }
    }
    async function completeProfile(profileId, email) {
      if (!profileId || !email) {
        log("这个环境没有邮箱备注，不能保存完成记录");
        return;
      }
      const tier = document.getElementById(`tier-select-${profileId}`)?.value || "5X";
      try {
        const data = await api("/api/completed/add", {profile_id: profileId, email, tier});
        completedProfiles[profileId] = {email, tier};
        const button = document.getElementById(`complete-btn-${profileId}`);
        if (button) {
          button.textContent = "已完成";
          button.disabled = true;
        }
        const tierSelect = document.getElementById(`tier-select-${profileId}`);
        if (tierSelect) {
          tierSelect.value = tier;
          tierSelect.disabled = true;
        }
        log(data.message);
      } catch (err) { log(`错误：${err.message}`); }
    }
    async function exportCompleted() {
      try {
        const res = await fetch("/api/completed/export", {method: "POST"});
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.error || "导出失败");
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `completed_accounts_${timestampMinute()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        completedProfiles = {};
        renderProfiles(profiles);
        log("已导出完成数据，并清空本地完成列表");
      } catch (err) { log(`错误：${err.message}`); }
    }
    function timestampMinute() {
      const now = new Date();
      const pad = value => String(value).padStart(2, "0");
      return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}`;
    }
    async function updateProject() {
      if (!confirm("确认在线更新并重启？Windows 版会从 GitHub Releases 下载最新 exe。")) return;
      try {
        log("正在在线更新...");
        const data = await api("/api/update", {});
        log(data.message);
      } catch (err) { log(`错误：${err.message}`); }
    }
    async function refreshCompletedProfiles() {
      try {
        const data = await api("/api/completed/list", {});
        completedProfiles = data.records || {};
        renderProfiles(profiles);
      } catch (err) { log(`错误：${err.message}`); }
    }
    async function addProxies() {
      const raw = document.getElementById("proxyInput").value;
      if (!raw.trim()) { log("请先粘贴代理"); return; }
      try {
        const data = await api("/api/proxies/add", {...cfg(), raw});
        log(data.message);
        document.getElementById("proxyInput").value = "";
        refreshProxies();
      } catch (err) { log(`错误：${err.message}`); }
    }
    function selectedProxyIndexes() {
      return [...document.querySelectorAll(".proxy-check:checked")].map(el => Number(el.value));
    }
    async function checkSelectedProxies() {
      const indexes = selectedProxyIndexes();
      if (!indexes.length) { log("请先选择代理"); return; }
      await checkProxies(indexes);
    }
    async function checkAllProxies() {
      const indexes = proxies.map(p => p.index);
      if (!indexes.length) { log("没有可检测的代理"); return; }
      await checkProxies(indexes);
    }
    async function checkProxies(indexes) {
      log(`开始检测 ${indexes.length} 条代理...`);
      for (const index of indexes) setProxyStatus(index, "checking", "检测中");
      try {
        const concurrency = Math.max(1, Math.min(30, Number(document.getElementById("proxyConcurrency").value || 5)));
        const timeout = Math.max(2, Math.min(30, Number(document.getElementById("proxyTimeout").value || 8)));
        const data = await api("/api/proxies/check", {proxy_file: document.getElementById("proxyFile").value.trim(), indexes, concurrency, timeout});
        for (const item of data.results) {
          const ip = document.getElementById(`proxy-ip-${item.index}`);
          const country = document.getElementById(`proxy-country-${item.index}`);
          const ms = document.getElementById(`proxy-ms-${item.index}`);
          const statusText = item.ok ? "可用" : (item.stage_label || "失败");
          const detail = item.detail || item.error || "";
          setProxyStatus(item.index, item.ok ? "ok" : "fail", statusText, detail);
          if (ip) ip.textContent = item.ip || "";
          if (country) country.textContent = item.country || "";
          if (ms) ms.textContent = item.ms ? `${item.ms} ms` : "";
        }
        log(data.message);
      } catch (err) { log(`错误：${err.message}`); }
    }
    function setProxyStatus(index, state, text, title = "") {
      const status = document.getElementById(`proxy-status-${index}`);
      if (!status) return;
      const cls = {
        idle: "badge-idle",
        checking: "badge-checking",
        ok: "badge-ok",
        fail: "badge-fail",
      }[state] || "badge-idle";
      status.innerHTML = `<span class="badge ${cls}" title="${title.replaceAll('"', "'")}">${text}</span>`;
    }
    function setProfileProxyStatus(profileId, state, text, title = "") {
      const status = document.getElementById(`profile-proxy-status-${profileId}`);
      if (!status) return;
      const cls = {
        idle: "badge-idle",
        checking: "badge-checking",
        ok: "badge-ok",
        fail: "badge-fail",
      }[state] || "badge-idle";
      status.innerHTML = `<span class="badge ${cls}" title="${title.replaceAll('"', "'")}">${text}</span>`;
    }
    async function checkProfileProxy(profileId, proxy) {
      if (!profileId || !proxy) return;
      setProfileProxyStatus(profileId, "checking", "检测中");
      try {
        const timeout = Math.max(2, Math.min(30, Number(document.getElementById("proxyTimeout").value || 8)));
        const data = await api("/api/profile-proxy/check", {proxy, timeout});
        const result = data.result;
        setProfileProxyStatus(
          profileId,
          result.ok ? "ok" : "fail",
          result.ok ? `可用 ${result.ip || ""} ${result.country || ""}` : (result.stage_label || "失败"),
          result.detail || result.error || ""
        );
        log(result.ok ? `环境 ${profileId} 代理可用：${result.ip}` : `环境 ${profileId} 代理失败：${result.stage_label || "失败"} ${result.error || ""}`);
      } catch (err) {
        setProfileProxyStatus(profileId, "fail", "失败", err.message);
        log(`错误：${err.message}`);
      }
    }
    async function updateProfileProxy(profileId, proxyText) {
      if (!profileId) return;
      try {
        log(proxyText ? `正在修改环境 ${profileId} 代理...` : `正在随机修改环境 ${profileId} 代理...`);
        const data = await api("/api/profile-proxy/update", {...cfg(), profile_id: profileId, proxy: proxyText});
        log(data.message);
        renderProfiles(data.profiles);
      } catch (err) {
        log(`错误：${err.message}`);
      }
    }
    async function copyEmail(email) {
      await copyText(email, `已复制邮箱：${email}`);
    }
    async function copyCode(code) {
      await copyText(code, `已复制验证码：${code}`);
    }
    async function copyText(value, message) {
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(value);
        } else {
          const input = document.createElement("textarea");
          input.value = value;
          input.style.position = "fixed";
          input.style.left = "-9999px";
          document.body.appendChild(input);
          input.focus();
          input.select();
          document.execCommand("copy");
          document.body.removeChild(input);
        }
        log(message);
      } catch (err) {
        log(`复制失败：${err.message}`);
      }
    }
    function setCodeCell(cell, code) {
      cell.innerHTML = "";
      if (!code) {
        cell.textContent = "未找到";
        return;
      }
      const span = document.createElement("span");
      span.className = "copy-code";
      span.textContent = code;
      span.title = "点击复制验证码";
      span.onclick = () => copyCode(code);
      cell.appendChild(span);
    }
    function saveMailResult(email, code, content) {
      if (!email) return;
      mailResults[email] = {
        email,
        code: code || "",
        content: content || "",
        time: new Date().toLocaleTimeString(),
      };
      currentMailEmail = email;
      renderMailList();
      showMailResult(email);
    }
    function renderMailList() {
      const list = document.getElementById("mailList");
      const items = Object.values(mailResults).sort((a, b) => b.time.localeCompare(a.time));
      list.innerHTML = "";
      if (!items.length) {
        const empty = document.createElement("div");
        empty.className = "mail-item";
        empty.innerHTML = `<span class="muted">暂无邮件记录</span>`;
        list.appendChild(empty);
        return;
      }
      for (const item of items) {
        const row = document.createElement("div");
        row.className = `mail-item ${item.email === currentMailEmail ? "active" : ""}`;
        row.onclick = () => showMailResult(item.email);
        row.innerHTML = `
          <strong>${item.email}</strong>
          <span class="mail-item-code">${item.code || "未找到"}</span>
          <span class="muted">${item.time}</span>`;
        list.appendChild(row);
      }
    }
    function showMailResult(email) {
      const item = mailResults[email];
      if (!item) return;
      currentMailEmail = email;
      const bigCode = document.getElementById("mailCode");
      bigCode.textContent = item.code || "未找到";
      bigCode.style.cursor = item.code ? "pointer" : "default";
      bigCode.onclick = item.code ? () => copyCode(item.code) : null;
      document.getElementById("mailCurrentEmail").value = item.email;
      document.getElementById("mailBox").value = item.content || "";
      renderMailList();
    }
    function updateCodeIfFresh(profileId, cell, code) {
      if (!code) {
        if (!profileCodes[profileId] && cell.textContent.trim() === "------") {
          cell.textContent = "未找到";
        }
        return;
      }
      const oldCode = profileCodes[profileId] || "";
      if (oldCode === code) return;
      profileCodes[profileId] = code;
      setCodeCell(cell, code);
    }
    async function deleteSelectedProxies() {
      const indexes = selectedProxyIndexes();
      if (!indexes.length) { log("请先选择代理"); return; }
      if (!confirm(`确认删除 ${indexes.length} 条代理？`)) return;
      try {
        const data = await api("/api/proxies/delete", {proxy_file: document.getElementById("proxyFile").value.trim(), indexes});
        log(data.message);
        renderProxies(data.proxies);
      } catch (err) { log(`错误：${err.message}`); }
    }
    async function fetchMail(email, profileId = "", quiet = false) {
      try {
        if (!quiet) log(`读取邮件：${email}`);
        if (profileId) {
          const cell = document.getElementById(`mail-code-${profileId}`);
          if (cell && !quiet) cell.textContent = "读取中";
        }
        const data = await api("/api/mail/fetch", {email});
        if (profileId) {
          const cell = document.getElementById(`mail-code-${profileId}`);
          if (cell) {
            if (quiet) {
              updateCodeIfFresh(profileId, cell, data.code);
            } else {
              setCodeCell(cell, data.code);
              if (data.code) profileCodes[profileId] = data.code;
            }
          }
        }
        saveMailResult(email, data.code, data.content);
        if (!quiet) log(data.code ? `${data.message}，验证码 ${data.code}` : data.message);
      } catch (err) {
        if (profileId) {
          const cell = document.getElementById(`mail-code-${profileId}`);
          if (cell && !quiet) cell.textContent = "失败";
        }
        if (!quiet) log(`错误：${err.message}`);
      }
    }
    async function fetchAllMail(quiet = false) {
      if (mailReading) return;
      const items = profiles.map(item => {
        const remark = item.remark || "";
        const email = remark.startsWith("email:") ? remark.replace("email:", "").trim() : remark;
        return email ? {email, profileId: item.user_id || ""} : null;
      }).filter(Boolean);
      if (!items.length) {
        if (!quiet) log("没有可读取邮件的环境");
        return;
      }
      mailReading = true;
      if (!quiet) log(`开始读取 ${items.length} 个邮箱的验证码...`);
      try {
        for (const item of items) {
          await fetchMail(item.email, item.profileId, true);
        }
        if (!quiet) log(`读取完成，共 ${items.length} 个邮箱`);
      } finally {
        mailReading = false;
      }
    }
    function toggleAutoMail() {
      if (autoMailTimer) {
        clearInterval(autoMailTimer);
        autoMailTimer = null;
      }
      if (!document.getElementById("autoMail").checked) {
        log("已关闭自动读取验证码");
        return;
      }
      const interval = Math.max(5, Math.min(120, Number(document.getElementById("mailInterval").value || 15)));
      log(`已开启自动读取验证码，每 ${interval} 秒读取一次`);
      fetchAllMail(true);
      autoMailTimer = setInterval(() => fetchAllMail(true), interval * 1000);
    }
    refreshProfiles();
    refreshProxies();
    refreshCompletedProfiles();
  </script>
</body>
</html>
"""


def list_profiles(base_url: str, api_key: Optional[str]) -> List[Dict[str, Any]]:
    profiles: List[Dict[str, Any]] = []
    page = 1
    while True:
        data = request_json(
            "GET",
            base_url,
            f"/api/v1/user/list?page={page}&page_size=100",
            api_key=api_key,
        )
        batch = data.get("data", {}).get("list", [])
        profiles.extend(batch)
        if len(batch) < 100:
            return profiles
        page += 1


def parse_mail_account(item: Any) -> Dict[str, str]:
    if isinstance(item, dict):
        return {
            "email": str(item.get("email") or "").strip(),
            "password": str(item.get("password") or "").strip(),
            "mail_url": str(item.get("mail_url") or "").strip(),
        }

    value = str(item or "").strip()
    if not value:
        return {"email": "", "password": "", "mail_url": ""}
    parts = value.split("----")
    if len(parts) >= 3:
        return {
            "email": parts[0].strip(),
            "password": parts[1].strip(),
            "mail_url": "----".join(parts[2:]).strip(),
        }
    return {"email": value, "password": "", "mail_url": ""}


def load_mail_accounts() -> Dict[str, Dict[str, str]]:
    if not os.path.exists(DEFAULT_MAIL_FILE):
        return {}
    with open(DEFAULT_MAIL_FILE, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def save_mail_accounts(accounts: Dict[str, Dict[str, str]]) -> None:
    with open(DEFAULT_MAIL_FILE, "w", encoding="utf-8") as handle:
        json.dump(accounts, handle, ensure_ascii=False, indent=2)


def load_completed_profiles() -> Dict[str, Dict[str, str]]:
    if not os.path.exists(DEFAULT_COMPLETED_META_FILE):
        return {}
    with open(DEFAULT_COMPLETED_META_FILE, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def save_completed_profiles(records: Dict[str, Dict[str, str]]) -> None:
    with open(DEFAULT_COMPLETED_META_FILE, "w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)


def append_completed_account(profile_id: str, email: str, tier: str) -> str:
    if not profile_id:
        raise AdsPowerError("profile_id is required")
    records = load_completed_profiles()
    if profile_id in records:
        raise AdsPowerError("这个环境已经完成过，不能重复完成")

    accounts = load_mail_accounts()
    account = accounts.get(email, {})
    password = account.get("password", "")
    if not password:
        raise AdsPowerError(f"No saved password for {email}")
    tier = tier if tier in ("5X", "20X") else "5X"
    line = f"{email}----{password}----{tier}"

    records[profile_id] = {"email": email, "tier": tier, "line": line}
    save_completed_profiles(records)
    with open(DEFAULT_COMPLETED_FILE, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return line


def export_completed_accounts() -> str:
    if not os.path.exists(DEFAULT_COMPLETED_FILE):
        return ""
    with open(DEFAULT_COMPLETED_FILE, "r", encoding="utf-8") as handle:
        content = handle.read()
    with open(DEFAULT_COMPLETED_FILE, "w", encoding="utf-8") as handle:
        handle.write("")
    save_completed_profiles({})
    return content


def upsert_mail_accounts(items: List[Any]) -> None:
    accounts = load_mail_accounts()
    changed = False
    for item in items:
        account = parse_mail_account(item)
        email = account["email"]
        if not email or not account["mail_url"]:
            continue
        accounts[email] = account
        changed = True
    if changed:
        save_mail_accounts(accounts)


def fetch_url_text(url: str) -> str:
    req = request.Request(url, headers={"Accept": "text/plain, application/json, text/html"})
    try:
        with request.urlopen(req, timeout=25) as resp:
            raw = resp.read(1024 * 512)
    except error.URLError as exc:
        raise AdsPowerError(f"Cannot read URL: {exc}") from exc
    return raw.decode("utf-8", "replace").strip()


def fetch_b2u_mail(account: Dict[str, str]) -> Optional[str]:
    parsed = urlparse(account["mail_url"])
    parts = [part for part in parsed.path.split("/") if part]
    if not parts or "b2u.me" not in parsed.netloc:
        return None

    link_code = parts[0]
    email = account["email"]
    password = account["password"]

    candidates = []
    if password:
        candidates.append(
            f"https://bsh.bhdata.com:30015/{quote(link_code)}/"
            f"{quote(email, safe='@.')}/{quote(password, safe='')}"
        )
    candidates.append(f"https://bsh.bhdata.com:30015/{quote(link_code)}/{quote(email, safe='@.')}/")

    data = None
    last_error = None
    for api_url in candidates:
        text = fetch_url_text(api_url)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AdsPowerError(f"Mail API returned non-JSON content: {text[:120]}") from exc
        if data.get("code") == 0:
            break
        last_error = data.get("msg") or data
    else:
        raise AdsPowerError(f"Mail API failed: {last_error}")

    result = data.get("data", {}).get("result", "")
    if not isinstance(result, str):
        return json.dumps(result, ensure_ascii=False, indent=2)

    text_result = html_lib.unescape(result)
    text_result = re.sub(r"<script[\s\S]*?</script>", "", text_result, flags=re.I)
    text_result = re.sub(r"<style[\s\S]*?</style>", "", text_result, flags=re.I)
    text_result = re.sub(r"<br\s*/?>", "\n", text_result, flags=re.I)
    text_result = re.sub(r"<[^>]+>", "", text_result)
    text_result = re.sub(r"\n\s+\n", "\n\n", text_result)
    return text_result.strip()


def fetch_latest_mail(email: str) -> str:
    accounts = load_mail_accounts()
    account = accounts.get(email)
    if not account or not account.get("mail_url"):
        raise AdsPowerError(f"No mail API URL saved for {email}")

    b2u_content = fetch_b2u_mail(account)
    if b2u_content is not None:
        return b2u_content

    text = fetch_url_text(account["mail_url"])
    try:
        parsed = json.loads(text)
        return json.dumps(parsed, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return text


def extract_six_digit_code(content: str) -> str:
    candidates = re.findall(r"(?<!\d)(\d{6})(?!\d)", content)
    return candidates[0] if candidates else ""


def append_proxies(proxy_file: str, raw: str) -> Dict[str, int]:
    lines = [line.strip() for line in raw.replace(",", "\n").splitlines() if line.strip()]
    normalized = []
    skipped = 0
    for line in lines:
        try:
            normalized.append(normalize_proxy_line(line))
        except AdsPowerError:
            skipped += 1

    path = proxy_file or DEFAULT_PROXY_FILE
    existing = set()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            existing = {line.strip() for line in handle if line.strip() and not line.strip().startswith("#")}

    added = [line for line in normalized if line not in existing]
    if added:
        with open(path, "a", encoding="utf-8") as handle:
            for line in added:
                handle.write(line + "\n")
    return {"added": len(added), "duplicate": len(normalized) - len(added), "skipped": skipped}


def delete_proxies(proxy_file: str, indexes: List[int]) -> int:
    path = proxy_file or DEFAULT_PROXY_FILE
    if not os.path.exists(path):
        return 0

    delete_set = set(indexes)
    kept_lines = []
    proxy_index = 0
    deleted = 0
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                kept_lines.append(raw_line)
                continue
            try:
                normalize_proxy_line(stripped)
            except AdsPowerError:
                kept_lines.append(raw_line)
                continue
            if proxy_index in delete_set:
                deleted += 1
            else:
                kept_lines.append(raw_line if raw_line.endswith("\n") else raw_line + "\n")
            proxy_index += 1

    with open(path, "w", encoding="utf-8") as handle:
        handle.writelines(kept_lines)
    return deleted


def read_proxy_entries(proxy_file: str) -> List[Dict[str, Any]]:
    path = proxy_file or DEFAULT_PROXY_FILE
    if not os.path.exists(path):
        return []

    entries = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            try:
                normalized = normalize_proxy_line(value)
                host, port, user, _password = normalized.split(":", 3)
            except AdsPowerError:
                continue
            entries.append(
                {
                    "index": len(entries),
                    "type": "socks5",
                    "host": host,
                    "port": port,
                    "user": user,
                    "value": normalized,
                }
            )
    return entries


PROXY_STAGE_LABELS = {
    "tcp": "TCP失败",
    "method": "握手失败",
    "auth": "认证失败",
    "connect": "目标失败",
    "outbound": "出口失败",
    "config": "配置错误",
}


class ProxyCheckError(AdsPowerError):
    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage
        self.stage_label = PROXY_STAGE_LABELS.get(stage, "失败")


def proxy_fail_result(started: float, exc: Exception) -> Dict[str, Any]:
    stage = getattr(exc, "stage", "outbound")
    stage_label = getattr(exc, "stage_label", PROXY_STAGE_LABELS.get(stage, "失败"))
    return {
        "ok": False,
        "ip": "",
        "country": "",
        "ms": int((time.monotonic() - started) * 1000),
        "stage": stage,
        "stage_label": stage_label,
        "error": str(exc),
        "detail": f"{stage_label}：{exc}",
    }


def recv_exact(sock: socket.socket, length: int, stage: str) -> bytes:
    chunks = []
    remaining = length
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ProxyCheckError(stage, "connection closed before SOCKS5 reply was complete")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def socks5_connect(proxy: Dict[str, str], dest_host: str, dest_port: int, timeout: float = 12) -> socket.socket:
    try:
        sock = socket.create_connection((proxy["host"], int(proxy["port"])), timeout=timeout)
    except Exception as exc:
        raise ProxyCheckError("tcp", str(exc)) from exc
    sock.settimeout(timeout)
    user = proxy["user"].encode("utf-8")
    password = proxy["password"].encode("utf-8")

    try:
        sock.sendall(b"\x05\x01\x02")
        version, method = recv_exact(sock, 2, "method")
    except ProxyCheckError:
        sock.close()
        raise
    except Exception as exc:
        sock.close()
        raise ProxyCheckError("method", str(exc)) from exc
    if version != 5 or method != 2:
        sock.close()
        raise ProxyCheckError("method", f"server selected method {method}, expected username/password")

    if len(user) > 255 or len(password) > 255:
        sock.close()
        raise ProxyCheckError("config", "SOCKS5 username/password is too long")
    try:
        sock.sendall(b"\x01" + bytes([len(user)]) + user + bytes([len(password)]) + password)
        auth = recv_exact(sock, 2, "auth")
    except ProxyCheckError:
        sock.close()
        raise
    except Exception as exc:
        sock.close()
        raise ProxyCheckError("auth", str(exc)) from exc
    if len(auth) != 2 or auth[1] != 0:
        sock.close()
        status = auth[1] if len(auth) > 1 else "?"
        raise ProxyCheckError("auth", f"username/password rejected, status {status}")

    host_bytes = dest_host.encode("idna")
    request_packet = b"\x05\x01\x00\x03" + bytes([len(host_bytes)]) + host_bytes + dest_port.to_bytes(2, "big")
    try:
        sock.sendall(request_packet)
        reply = recv_exact(sock, 4, "connect")
    except ProxyCheckError:
        sock.close()
        raise
    except Exception as exc:
        sock.close()
        raise ProxyCheckError("connect", str(exc)) from exc
    if len(reply) != 4 or reply[1] != 0:
        sock.close()
        code = reply[1] if len(reply) > 1 else "?"
        raise ProxyCheckError("connect", f"SOCKS5 target connect failed, code {code}")

    atyp = reply[3]
    try:
        if atyp == 1:
            recv_exact(sock, 4, "connect")
        elif atyp == 3:
            size = recv_exact(sock, 1, "connect")[0]
            recv_exact(sock, size, "connect")
        elif atyp == 4:
            recv_exact(sock, 16, "connect")
        recv_exact(sock, 2, "connect")
    except ProxyCheckError:
        sock.close()
        raise
    except Exception as exc:
        sock.close()
        raise ProxyCheckError("connect", str(exc)) from exc
    return sock


def check_proxy_line(value: str, timeout: float = 8) -> Dict[str, Any]:
    normalized = normalize_proxy_line(value)
    host, port, user, password = normalized.split(":", 3)
    proxy = {"host": host, "port": port, "user": user, "password": password}
    started = time.monotonic()
    sock: Optional[socket.socket] = None
    try:
        sock = socks5_connect(proxy, "api.ipify.org", 80, timeout=timeout)
        sock.sendall(b"GET /?format=text HTTP/1.1\r\nHost: api.ipify.org\r\nConnection: close\r\n\r\n")
        chunks = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks).decode("utf-8", "replace")
        body = raw.split("\r\n\r\n", 1)[-1].strip().splitlines()[0].strip()
        if not re.match(r"^(\d{1,3}\.){3}\d{1,3}$|^[0-9a-fA-F:]{3,}$", body):
            raise ProxyCheckError("outbound", "no valid outbound IP returned")
        return {
            "ok": True,
            "ip": body,
            "country": lookup_country_code(body),
            "ms": int((time.monotonic() - started) * 1000),
            "stage": "ok",
            "stage_label": "可用",
            "error": "",
            "detail": "",
        }
    except Exception as exc:
        return proxy_fail_result(started, exc)
    finally:
        if sock:
            sock.close()


def check_proxy_config(config: Dict[str, Any], timeout: float = 8) -> Dict[str, Any]:
    host = str(config.get("host") or "").strip()
    port = str(config.get("port") or "").strip()
    user = str(config.get("user") or "").strip()
    password = str(config.get("password") or "").strip()
    if not host or not port or not user or not password:
        exc = ProxyCheckError("config", "proxy config is incomplete")
        return proxy_fail_result(time.monotonic(), exc)
    return check_proxy_line(f"{host}:{port}:{user}:{password}", timeout=timeout)


def lookup_country_code(ip: str) -> str:
    if not ip:
        return ""
    if ip in COUNTRY_CACHE:
        return COUNTRY_CACHE[ip]
    try:
        text = fetch_url_text(f"http://ip-api.com/json/{ip}?fields=status,countryCode")
        data = json.loads(text)
        code = data.get("countryCode", "") if data.get("status") == "success" else ""
    except Exception:
        code = ""
    COUNTRY_CACHE[ip] = code
    return code


def proxy_config_from_line(line: str) -> Dict[str, str]:
    host, port, username, password = normalize_proxy_line(line).split(":", 3)
    return {
        "proxy_soft": "other",
        "proxy_type": "socks5",
        "proxy_host": host,
        "proxy_port": port,
        "proxy_user": username,
        "proxy_password": password,
    }


def update_profile_proxy(
    base_url: str,
    api_key: Optional[str],
    profile_id: str,
    proxy_config: Dict[str, str],
) -> None:
    payload = {"profile_id": profile_id, "user_proxy_config": proxy_config}
    request_json("POST", base_url, "/api/v2/browser-profile/update", payload, api_key)


def run_online_update() -> Dict[str, Any]:
    if getattr(sys, "frozen", False):
        return run_windows_exe_update()
    return run_source_update()


def run_source_update() -> Dict[str, Any]:
    cwd = os.path.dirname(os.path.abspath(__file__))
    remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=cwd,
        text=True,
        capture_output=True,
    )
    if remote.returncode != 0 or not remote.stdout.strip():
        raise AdsPowerError("当前项目还没有配置 GitHub remote origin")

    pull = subprocess.run(
        ["git", "pull", "--ff-only", "origin", "main"],
        cwd=cwd,
        text=True,
        capture_output=True,
    )
    if pull.returncode != 0:
        raise AdsPowerError((pull.stderr or pull.stdout or "git pull failed").strip())

    compile_check = subprocess.run(
        [sys.executable, "-m", "py_compile", "adspower_web.py", "adspower_open_chatgpt.py"],
        cwd=cwd,
        text=True,
        capture_output=True,
    )
    if compile_check.returncode != 0:
        raise AdsPowerError((compile_check.stderr or "compile check failed").strip())

    return {
        "remote": remote.stdout.strip(),
        "output": (pull.stdout or pull.stderr or "").strip(),
        "restart": "source",
    }


def run_windows_exe_update() -> Dict[str, Any]:
    app_dir = os.path.dirname(os.path.abspath(sys.executable))
    release_api = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    release = json.loads(fetch_url_text(release_api))
    assets = release.get("assets", [])
    asset = next((item for item in assets if item.get("name") == "AdsPowerConsole-Windows.zip"), None)
    if not asset:
        raise AdsPowerError("最新 Release 里没有 AdsPowerConsole-Windows.zip")

    zip_path = os.path.join(app_dir, "AdsPowerConsole-Windows-update.zip")
    update_dir = os.path.join(app_dir, "_update")
    os.makedirs(update_dir, exist_ok=True)

    req = request.Request(asset["browser_download_url"], headers={"Accept": "application/octet-stream"})
    try:
        with request.urlopen(req, timeout=90) as resp, open(zip_path, "wb") as handle:
            handle.write(resp.read())
    except error.URLError as exc:
        raise AdsPowerError(f"下载更新失败: {exc}") from exc

    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(update_dir)

    next_exe = os.path.join(update_dir, "AdsPowerConsole.exe")
    if not os.path.exists(next_exe):
        raise AdsPowerError("更新包里没有 AdsPowerConsole.exe")

    def ps_quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    batch_path = os.path.join(app_dir, "apply_update.bat")
    ps_path = os.path.join(app_dir, "apply_update.ps1")
    current_exe = os.path.abspath(sys.executable)
    ps_script = f"""Start-Sleep -Seconds 2
Copy-Item -LiteralPath {ps_quote(next_exe)} -Destination {ps_quote(current_exe)} -Force
$startBat = Join-Path {ps_quote(update_dir)} 'start.bat'
if (Test-Path -LiteralPath $startBat) {{
  Copy-Item -LiteralPath $startBat -Destination (Join-Path {ps_quote(app_dir)} 'start.bat') -Force
}}
$readme = Join-Path {ps_quote(update_dir)} 'README-Windows.txt'
if (Test-Path -LiteralPath $readme) {{
  Copy-Item -LiteralPath $readme -Destination (Join-Path {ps_quote(app_dir)} 'README-Windows.txt') -Force
}}
Remove-Item -LiteralPath {ps_quote(update_dir)} -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath {ps_quote(zip_path)} -Force -ErrorAction SilentlyContinue
Start-Process -FilePath {ps_quote(current_exe)}
Start-Sleep -Milliseconds 500
Remove-Item -LiteralPath {ps_quote(batch_path)} -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath {ps_quote(ps_path)} -Force -ErrorAction SilentlyContinue
"""
    batch_script = """@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply_update.ps1"
"""
    with open(ps_path, "w", encoding="utf-8-sig", newline="\r\n") as handle:
        handle.write(ps_script)
    with open(batch_path, "w", encoding="ascii", newline="\r\n") as handle:
        handle.write(batch_script)

    return {
        "remote": f"https://github.com/{GITHUB_REPO}/releases/latest",
        "output": "已下载最新 Windows 版，服务即将重启并替换 exe",
        "restart": "windows-exe",
        "batch_path": batch_path,
    }


def schedule_restart() -> None:
    def restart() -> None:
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])

    threading.Timer(1.0, restart).start()


def schedule_windows_exe_restart(batch_path: str) -> None:
    def restart() -> None:
        subprocess.Popen(["cmd", "/c", batch_path], cwd=os.path.dirname(os.path.abspath(sys.executable)))
        os._exit(0)

    threading.Timer(1.0, restart).start()


def response(handler: BaseHTTPRequestHandler, status: int, payload: Any, content_type: str = "application/json") -> None:
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def error_response(handler: BaseHTTPRequestHandler, exc: Exception) -> None:
    response(handler, 500, {"ok": False, "error": str(exc)})


def read_json(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length).decode("utf-8")
    return json.loads(raw) if raw else {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                api_key = os.getenv("ADSPOWER_API_KEY", "")
                html = HTML.replace("__API_KEY__", api_key)
                response(self, 200, html.encode("utf-8"), "text/html; charset=utf-8")
                return
            if parsed.path == "/api/proxies":
                proxy_file = parse_qs(parsed.query).get("proxy_file", [DEFAULT_PROXY_FILE])[0]
                response(self, 200, {"ok": True, "proxies": read_proxy_entries(proxy_file)})
                return
            if parsed.path == "/api/profiles":
                config_raw = parse_qs(parsed.query).get("config", ["{}"])[0]
                cfg = json.loads(config_raw)
                profiles = list_profiles(cfg.get("base_url") or DEFAULT_BASE_URL, cfg.get("api_key") or None)
                response(self, 200, {"ok": True, "profiles": profiles})
                return
            response(self, 404, {"ok": False, "error": "Not found"})
        except Exception as exc:
            error_response(self, exc)

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            data = read_json(self)

            if parsed.path == "/api/mail/fetch":
                email = str(data.get("email") or "").strip()
                if not email:
                    raise AdsPowerError("Email is required")
                content = fetch_latest_mail(email)
                code = extract_six_digit_code(content)
                response(
                    self,
                    200,
                    {
                        "ok": True,
                        "message": f"已读取 {email} 的最新邮件",
                        "code": code,
                        "content": content,
                    },
                )
                return

            if parsed.path == "/api/profile-proxy/check":
                timeout = max(2, min(30, float(data.get("timeout") or 8)))
                result = check_proxy_config(data.get("proxy") or {}, timeout=timeout)
                response(self, 200, {"ok": True, "result": result})
                return

            if parsed.path == "/api/completed/add":
                email = str(data.get("email") or "").strip()
                profile_id = str(data.get("profile_id") or "").strip()
                tier = str(data.get("tier") or "5X").strip()
                if not email:
                    raise AdsPowerError("Email is required")
                saved_line = append_completed_account(profile_id, email, tier)
                response(self, 200, {"ok": True, "message": f"已保存完成记录：{saved_line}"})
                return

            if parsed.path == "/api/completed/list":
                response(self, 200, {"ok": True, "records": load_completed_profiles()})
                return

            if parsed.path == "/api/completed/export":
                content = export_completed_accounts()
                if not content.strip():
                    raise AdsPowerError("没有可导出的完成数据")
                body = content.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                filename = f"completed_accounts_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if parsed.path == "/api/update":
                result = run_online_update()
                if result.get("restart") == "windows-exe":
                    schedule_windows_exe_restart(result["batch_path"])
                else:
                    schedule_restart()
                response(
                    self,
                    200,
                    {
                        "ok": True,
                        "message": f"更新成功，服务即将重启。{result['output']}",
                        "remote": result["remote"],
                    },
                )
                return

            base_url = data.get("base_url") or DEFAULT_BASE_URL
            api_key = data.get("api_key") or None
            check_connection(base_url, api_key)

            if parsed.path == "/api/create":
                emails = data.get("emails") or []
                upsert_mail_accounts(emails)
                proxies = load_proxies(data.get("proxy_file") or DEFAULT_PROXY_FILE)
                created = []
                for index, item in enumerate(emails, start=1):
                    account = parse_mail_account(item)
                    email = account["email"]
                    label = email or f"no-email-{index}"
                    profile_id = create_profile(
                        base_url,
                        api_key,
                        data.get("group_id") or "0",
                        data.get("target_url") or DEFAULT_TARGET_URL,
                        f"ChatGPT - {label}",
                        random.choice(proxies) if proxies else None,
                        account_email=email,
                    )
                    created.append(profile_id)
                    time.sleep(1.1)
                    if data.get("open_after"):
                        started = open_profile(base_url, api_key, profile_id)
                        debug_port = str(started.get("data", {}).get("debug_port") or "")
                        open_url_by_debug_port(debug_port, data.get("target_url") or DEFAULT_TARGET_URL)
                        time.sleep(1.1)
                response(self, 200, {"ok": True, "message": f"创建完成，共 {len(created)} 个", "profiles": list_profiles(base_url, api_key)})
                return

            if parsed.path == "/api/open":
                ids = data.get("ids") or []
                for profile_id in ids:
                    started = open_profile(base_url, api_key, profile_id)
                    debug_port = str(started.get("data", {}).get("debug_port") or "")
                    open_url_by_debug_port(debug_port, data.get("target_url") or DEFAULT_TARGET_URL)
                    time.sleep(1.1)
                response(self, 200, {"ok": True, "message": f"已打开 {len(ids)} 个环境"})
                return

            if parsed.path == "/api/delete":
                ids = data.get("ids") or []
                request_json("POST", base_url, "/api/v1/user/delete", {"user_ids": ids}, api_key)
                response(self, 200, {"ok": True, "message": f"已删除 {len(ids)} 个环境", "profiles": list_profiles(base_url, api_key)})
                return

            if parsed.path == "/api/profile-proxy/update":
                profile_id = str(data.get("profile_id") or "").strip()
                if not profile_id:
                    raise AdsPowerError("profile_id is required")
                proxy_text = str(data.get("proxy") or "").strip()
                if proxy_text:
                    proxy_config = proxy_config_from_line(proxy_text)
                else:
                    entries = read_proxy_entries(data.get("proxy_file") or DEFAULT_PROXY_FILE)
                    if not entries:
                        raise AdsPowerError("Proxy file has no usable proxies")
                    proxy_config = proxy_config_from_line(random.choice(entries)["value"])
                update_profile_proxy(base_url, api_key, profile_id, proxy_config)
                response(
                    self,
                    200,
                    {
                        "ok": True,
                        "message": f"已修改环境 {profile_id} 的代理",
                        "profiles": list_profiles(base_url, api_key),
                    },
                )
                return

            if parsed.path == "/api/proxies/add":
                stats = append_proxies(data.get("proxy_file") or DEFAULT_PROXY_FILE, data.get("raw") or "")
                response(
                    self,
                    200,
                    {
                        "ok": True,
                        "message": (
                            f"代理添加完成：新增 {stats['added']} 条，"
                            f"重复 {stats['duplicate']} 条，无法识别 {stats['skipped']} 条"
                        ),
                    },
                )
                return

            if parsed.path == "/api/proxies/check":
                entries = read_proxy_entries(data.get("proxy_file") or DEFAULT_PROXY_FILE)
                indexes = set(data.get("indexes") or [])
                selected = [entry for entry in entries if entry["index"] in indexes]
                concurrency = max(1, min(30, int(data.get("concurrency") or 5)))
                timeout = max(2, min(30, float(data.get("timeout") or 8)))
                results = []
                with ThreadPoolExecutor(max_workers=concurrency) as executor:
                    future_map = {
                        executor.submit(check_proxy_line, entry["value"], timeout): entry["index"]
                        for entry in selected
                    }
                    for future in as_completed(future_map):
                        result = future.result()
                        result["index"] = future_map[future]
                        results.append(result)
                results.sort(key=lambda item: item["index"])
                ok_count = sum(1 for item in results if item["ok"])
                response(
                    self,
                    200,
                    {
                        "ok": True,
                        "message": (
                            f"检测完成：可用 {ok_count} 条，失败 {len(results) - ok_count} 条，"
                            f"并发 {concurrency}，超时 {timeout:g}s"
                        ),
                        "results": results,
                    },
                )
                return

            if parsed.path == "/api/proxies/delete":
                deleted = delete_proxies(data.get("proxy_file") or DEFAULT_PROXY_FILE, data.get("indexes") or [])
                proxy_file = data.get("proxy_file") or DEFAULT_PROXY_FILE
                response(
                    self,
                    200,
                    {
                        "ok": True,
                        "message": f"已删除 {deleted} 条代理",
                        "proxies": read_proxy_entries(proxy_file),
                    },
                )
                return

            response(self, 404, {"ok": False, "error": "Not found"})
        except Exception as exc:
            error_response(self, exc)


def main() -> int:
    port = int(os.getenv("ADSPOWER_WEB_PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"AdsPower web console: {url}")
    threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
