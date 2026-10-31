(() => {
  'use strict';

  const $ = (sel) => document.querySelector(sel);

  const els = {
    addVideo: $('#addVideo'),
    videoList: $('#videoList'),
    videoCount: $('#videoCount'),
    autoCrop: $('#autoCrop'),
    bulkSkipStart: $('#bulkSkipStart'),
    bulkSkipEnd: $('#bulkSkipEnd'),
    applySkip: $('#applySkip'),
    interval: $('#interval'),
    intervalOut: $('#intervalOut'),
    bandWidth: $('#bandWidth'),
    bandWidthOut: $('#bandWidthOut'),
    bandHint: $('#bandHint'),
    layoutGrid: $('#layoutGrid'),
    spiralField: $('#spiralField'),
    spiralTurns: $('#spiralTurns'),
    spiralOut: $('#spiralOut'),
    resPreset: $('#resPreset'),
    resOut: $('#resOut'),
    customRes: $('#customRes'),
    resW: $('#resW'),
    resH: $('#resH'),
    planLine: $('#planLine'),
    planNote: $('#planNote'),
    resetPost: $('#resetPost'),
    titleInput: $('#titleInput'),
    subtitleInput: $('#subtitleInput'),
    fontSelect: $('#fontSelect'),
    fontCount: $('#fontCount'),
    fontPreview: $('#fontPreview'),
    fontVibe: $('#fontVibe'),
    fontDownload: $('#fontDownload'),
    sizePct: $('#sizePct'),
    sizeOut: $('#sizeOut'),
    trackingPct: $('#trackingPct'),
    trackingOut: $('#trackingOut'),
    titleColor: $('#titleColor'),
    opacity: $('#opacity'),
    opacityOut: $('#opacityOut'),
    anchorGrid: $('#anchorGrid'),
    anchorOut: $('#anchorOut'),
    offsetX: $('#offsetX'),
    offsetY: $('#offsetY'),
    noise: $('#noise'),
    noiseOut: $('#noiseOut'),
    grain: $('#grain'),
    grainOut: $('#grainOut'),
    mono: $('#mono'),
    blur: $('#blur'),
    blurOut: $('#blurOut'),
    generate: $('#generate'),
    export: $('#export'),
    engine: $('#engineState'),
    stageBody: $('#stageBody'),
    emptyState: $('#emptyState'),
    canvasWrap: $('#canvasWrap'),
    canvasFrame: $('#canvasFrame'),
    canvas: $('#bandCanvas'),
    fxCanvas: $('#fxCanvas'),
    finalImage: $('#finalImage'),
    revealHud: $('#revealHud'),
    hudColor: $('#hudColor'),
    hudHex: $('#hudHex'),
    hudTime: $('#hudTime'),
    hudIndex: $('#hudIndex'),
    hudLive: $('#hudLive'),
    renderBadge: $('#renderBadge'),
    statDuration: $('#statDuration'),
    statBands: $('#statBands'),
    statInterval: $('#statInterval'),
    statCanvas: $('#statCanvas'),
    progressBar: $('#progressBar'),
    statusText: $('#statusText'),
    percentText: $('#percentText'),
    toast: $('#toast'),
  };

  const ctx = els.canvas.getContext('2d');
  const fxCtx = els.fxCanvas.getContext('2d');

  const POST_DEFAULTS = {
    title: '', subtitle: '', font: 'noto-serif', sizePct: 7, trackingPct: 4,
    color: '#f2eee6', opacity: 100, anchor: 'middle-center',
    offsetX: 0, offsetY: 0, noise: 12, grain: 2, mono: true, blur: 0,
  };

  const RES_PRESETS = {
    '2560x800': [2560, 800],
    '2560x1440': [2560, 1440],
    '3840x2160': [3840, 2160],
    '1920x1080': [1920, 1080],
    '2560x720': [2560, 720],
    '1080x1920': [1080, 1920],
    '1440x1440': [1440, 1440],
  };

  const ANCHOR_LABELS = {
    'top-left': '左上', 'top-center': '上方', 'top-right': '右上',
    'middle-left': '左侧', 'middle-center': '居中', 'middle-right': '右侧',
    'bottom-left': '左下', 'bottom-center': '下方', 'bottom-right': '右下',
  };

  const state = {
    videos: [],
    dragIndex: -1,
    bulkSkip: { start: 0, end: 0 },
    options: {
      interval: 2, bandWidth: 2, layout: 'horizontal',
      width: 2560, height: 800, spiralTurns: 5, autoCrop: true,
    },
    post: { ...POST_DEFAULTS },
    plan: null,
    planToken: 0,
    planTimer: 0,
    fonts: [],
    fontMap: {},
    jobId: null,
    jobPlan: null,
    layoutN: 0,
    bands: [],
    received: 0,
    revealed: 0,
    revealPos: 0,
    revealStart: 0,
    hudAt: 0,
    status: 'idle',
    finished: false,
    revealRunning: false,
    lastTick: 0,
    cw: 0,
    ch: 0,
    rev: 0,
    jobRev: 0,
    busy: false,
    renderTimer: 0,
    renderToken: 0,
    finalUrl: null,
    fontTimer: 0,
    toastTimer: 0,
  };

  /* ------------------------------ helpers ------------------------------ */

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function debounce(fn, delay) {
    let t = 0;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), delay);
    };
  }

  function fmtDuration(sec) {
    sec = Math.max(0, Math.round(Number(sec) || 0));
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    const p = (v) => String(v).padStart(2, '0');
    return h > 0 ? `${h}:${p(m)}:${p(s)}` : `${p(m)}:${p(s)}`;
  }

  function fmtBytes(n) {
    if (!n) return '';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    let v = n;
    while (v >= 1024 && i < units.length - 1) { v /= 1024; i += 1; }
    return `${v.toFixed(i ? 1 : 0)} ${units[i]}`;
  }

  function showToast(message, isError = false) {
    els.toast.textContent = message;
    els.toast.classList.toggle('error', isError);
    els.toast.classList.add('show');
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => els.toast.classList.remove('show'), 3600);
  }

  async function api(path, body, method) {
    const opt = { method: method || (body ? 'POST' : 'GET'), headers: {} };
    if (body) {
      opt.headers['Content-Type'] = 'application/json';
      opt.body = JSON.stringify(body);
    }
    const res = await fetch(path, opt);
    if (!res.ok) {
      let detail = `${res.status}`;
      try {
        const data = await res.json();
        detail = data.detail || detail;
      } catch (e) { /* ignore */ }
      throw new Error(detail);
    }
    return res.json();
  }

  /* ------------------------------ videos ------------------------------ */

  async function pickVideos() {
    if (state.busy) return;
    els.addVideo.disabled = true;
    try {
      const result = await api('/api/dialog', {});
      if (result.error) {
        showToast(`选择文件失败：${result.error}`, true);
      } else if (result.paths && result.paths.length) {
        await addPaths(result.paths);
      }
    } catch (err) {
      showToast(err.message || '选择文件失败', true);
    } finally {
      els.addVideo.disabled = false;
    }
  }

  async function addPaths(paths) {
    try {
      const result = await api('/api/probe', { paths });
      (result.videos || []).forEach((video) => {
        state.videos.push({
          ...video,
          skipStart: state.bulkSkip.start,
          skipEnd: state.bulkSkip.end,
          status: 'waiting',
        });
      });
      if (result.errors && result.errors.length) {
        showToast(result.errors[0].error || '部分文件读取失败', true);
      }
      state.rev += 1;
      renderVideoList();
      schedulePlan(120);
      updateGenerateButton();
    } catch (err) {
      showToast(err.message || '读取视频信息失败', true);
    }
  }

  function videoStatusLabel(status) {
    return {
      waiting: '待处理', running: '解析中', done: '已完成',
      skipped: '已跳过', error: '失败',
    }[status] || '待处理';
  }

  function renderVideoList() {
    els.videoList.innerHTML = '';
    if (!state.videos.length) {
      els.videoCount.textContent = '尚未添加';
      return;
    }
    const total = state.videos.reduce((s, v) => s + (v.duration || 0), 0);
    els.videoCount.textContent = `${state.videos.length} 部 · ${fmtDuration(total)}`;

    state.videos.forEach((video, index) => {
      const row = document.createElement('div');
      row.className = 'vrow';
      row.dataset.i = String(index);
      row.draggable = true;

      row.addEventListener('dragstart', (event) => {
        if (event.target.closest('input, button')) { event.preventDefault(); return; }
        state.dragIndex = index;
        row.classList.add('dragging');
        event.dataTransfer.effectAllowed = 'move';
        try { event.dataTransfer.setData('text/plain', String(index)); } catch (e) { /* ignore */ }
      });
      row.addEventListener('dragend', () => {
        row.classList.remove('dragging');
        state.dragIndex = -1;
        markDropRow(null);
      });
      row.addEventListener('dragover', (event) => {
        if (state.dragIndex < 0) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        markDropRow(row);
      });
      row.addEventListener('drop', (event) => {
        event.preventDefault();
        const from = state.dragIndex;
        state.dragIndex = -1;
        markDropRow(null);
        if (from < 0 || from === index) return;
        const moved = state.videos.splice(from, 1)[0];
        state.videos.splice(index, 0, moved);
        state.rev += 1;
        renderVideoList();
        schedulePlan(140);
        updateGenerateButton();
      });

      const top = document.createElement('div');
      top.className = 'vrow-top';

      const grip = document.createElement('span');
      grip.className = 'vgrip';
      grip.title = '拖动排序';
      grip.textContent = '⠿';
      grip.setAttribute('aria-hidden', 'true');

      const idx = document.createElement('span');
      idx.className = 'vindex';
      idx.textContent = String(index + 1).padStart(2, '0');

      const meta = document.createElement('div');
      meta.className = 'vmeta';
      const name = document.createElement('b');
      name.textContent = video.name;
      name.title = video.path;
      const sub = document.createElement('small');
      const res = video.width && video.height ? `${video.width}×${video.height}` : '';
      const fps = video.fps ? `${video.fps}fps` : '';
      sub.textContent = [res, fps, fmtDuration(video.duration), fmtBytes(video.size)]
        .filter(Boolean).join(' · ');
      meta.append(name, sub);

      const status = document.createElement('span');
      status.className = `vstatus ${video.status || 'waiting'}`;
      status.textContent = videoStatusLabel(video.status);

      const del = document.createElement('button');
      del.type = 'button';
      del.className = 'icon-btn';
      del.title = '移除';
      del.textContent = '✕';
      del.addEventListener('click', () => {
        state.videos.splice(index, 1);
        state.rev += 1;
        renderVideoList();
        schedulePlan(120);
        updateGenerateButton();
      });

      top.append(grip, idx, meta, status, del);

      const skip = document.createElement('div');
      skip.className = 'vrow-skip';

      const makeSkip = (label, key, placeholder) => {
        const wrap = document.createDocumentFragment();
        const text = document.createElement('span');
        text.textContent = label;
        const input = document.createElement('input');
        input.type = 'number';
        input.className = 'num';
        input.min = '0';
        input.step = '0.5';
        input.value = Number(video[key] || 0);
        input.title = placeholder;
        input.addEventListener('change', () => {
          const value = Math.max(0, Number(input.value) || 0);
          input.value = value;
          video[key] = value;
          state.rev += 1;
          schedulePlan(160);
          updateGenerateButton();
        });
        const em = document.createElement('em');
        em.textContent = '分';
        wrap.append(text, input, em);
        return wrap;
      };

      skip.append(makeSkip('片头', 'skipStart', '跳过片头（分钟）'));
      skip.append(makeSkip('片尾', 'skipEnd', '跳过片尾（分钟）'));

      const order = document.createElement('div');
      order.className = 'vorder';
      const up = document.createElement('button');
      up.type = 'button';
      up.className = 'icon-btn';
      up.textContent = '↑';
      up.title = '上移';
      up.disabled = index === 0;
      up.addEventListener('click', () => moveVideo(index, -1));
      const down = document.createElement('button');
      down.type = 'button';
      down.className = 'icon-btn';
      down.textContent = '↓';
      down.title = '下移';
      down.disabled = index === state.videos.length - 1;
      down.addEventListener('click', () => moveVideo(index, 1));
      order.append(up, down);
      skip.append(order);

      row.append(top, skip);
      els.videoList.append(row);
    });
  }

  function markDropRow(row) {
    els.videoList.querySelectorAll('.vrow').forEach((item) => {
      item.classList.toggle('drag-over', item === row);
    });
  }

  function applyBulkSkip() {
    const start = Math.max(0, Number(els.bulkSkipStart.value) || 0);
    const end = Math.max(0, Number(els.bulkSkipEnd.value) || 0);
    els.bulkSkipStart.value = start;
    els.bulkSkipEnd.value = end;
    state.bulkSkip = { start, end };
    if (!state.videos.length) {
      showToast('请先添加影片');
      return;
    }
    state.videos.forEach((video) => {
      video.skipStart = start;
      video.skipEnd = end;
    });
    state.rev += 1;
    renderVideoList();
    schedulePlan(120);
    updateGenerateButton();
    showToast(`片头 ${start} 分 / 片尾 ${end} 分已应用到 ${state.videos.length} 部影片`);
  }

  function moveVideo(index, delta) {
    const target = index + delta;
    if (target < 0 || target >= state.videos.length) return;
    const temp = state.videos[index];
    state.videos[index] = state.videos[target];
    state.videos[target] = temp;
    state.rev += 1;
    renderVideoList();
    schedulePlan(140);
    updateGenerateButton();
  }

  function updateVideoStatuses(states) {
    if (!states) return;
    states.forEach((item, i) => {
      const row = els.videoList.querySelector(`.vrow[data-i="${i}"]`);
      if (!row) return;
      const chip = row.querySelector('.vstatus');
      if (!chip) return;
      chip.className = `vstatus ${item.status}`;
      chip.textContent = videoStatusLabel(item.status);
      row.classList.toggle('running', item.status === 'running');
      if (item.status === 'error') row.classList.add('error');
    });
  }

  /* ------------------------------ plan ------------------------------ */

  function planPayload() {
    return {
      videos: state.videos.map((v) => ({
        path: v.path,
        name: v.name,
        duration: v.duration,
        skipStart: v.skipStart,
        skipEnd: v.skipEnd,
      })),
      options: { ...state.options },
    };
  }

  function schedulePlan(delay = 260) {
    clearTimeout(state.planTimer);
    state.planTimer = setTimeout(refreshPlan, delay);
  }

  async function refreshPlan() {
    if (!state.videos.length) {
      state.plan = null;
      updatePlanUI();
      updateGenerateButton();
      return;
    }
    const token = ++state.planToken;
    try {
      const plan = await api('/api/plan', planPayload());
      if (token !== state.planToken) return;
      state.plan = plan;
      updatePlanUI();
      updateGenerateButton();
    } catch (err) {
      if (token !== state.planToken) return;
      showToast(err.message || '无法计算采样计划', true);
    }
  }

  function updatePlanUI() {
    const plan = state.plan;
    if (!plan || !plan.bands) {
      els.planLine.textContent = plan ? '可采样时长不足，请调整跳过时长' : '等待添加影片';
      els.planNote.textContent = plan && plan.warnings && plan.warnings.length
        ? plan.warnings[0]
        : '添加影片后，这里会显示采样计划。';
      els.bandHint.textContent = '—';
    } else {
      els.planLine.innerHTML =
        `预计 <strong>${plan.bands}</strong> 条 · ` +
        `每 <strong>${plan.effectiveInterval.toFixed(1)}</strong> 秒/条 · ` +
        `<strong>${plan.bandPixels.toFixed(1)}</strong> px/条`;
      els.bandHint.textContent = `${plan.bands} 条`;

      const notes = [];
      if (plan.limitedBy === 'capacity') {
        notes.push(`画布容量上限 ${plan.capacity} 条，采样间隔已自动加宽。`);
      } else if (plan.limitedBy === 'max') {
        notes.push(`已达到单次生成上限 ${plan.bands} 条。`);
      } else {
        notes.push('色带数由采样间隔决定；加宽画布或调小色带宽度可容纳更多。');
      }
      if (plan.warnings && plan.warnings.length) notes.push(plan.warnings[0]);
      els.planNote.textContent = notes.join(' ');
    }

    if (!state.jobId || state.status === 'idle') {
      if (plan) {
        els.statDuration.textContent = plan.totalDuration ? fmtDuration(plan.totalDuration) : '—';
        els.statBands.textContent = plan.bands ? String(plan.bands) : '—';
        els.statInterval.textContent = plan.bands ? `${plan.effectiveInterval.toFixed(1)}s` : '—';
        els.statCanvas.textContent = `${state.options.width}×${state.options.height}`;
      } else {
        els.statDuration.textContent = '—';
        els.statBands.textContent = '—';
        els.statInterval.textContent = '—';
        els.statCanvas.textContent = `${state.options.width}×${state.options.height}`;
      }
    }
  }

  function isDirty() {
    if (!state.jobId) return false;
    if (state.rev !== state.jobRev) return true;
    if (state.plan && state.jobPlan && state.plan.bands !== state.jobPlan.bands) return true;
    return false;
  }

  function updateGenerateButton() {
    if (state.busy) {
      els.generate.textContent = '生成中…';
      els.generate.disabled = true;
      els.generate.classList.remove('dirty');
      return;
    }
    if (!state.videos.length) {
      els.generate.textContent = '生成色带';
      els.generate.disabled = true;
      els.generate.classList.remove('dirty');
      return;
    }
    const dirty = isDirty();
    els.generate.disabled = false;
    els.generate.classList.toggle('dirty', dirty);
    if (state.status === 'running') {
      els.generate.textContent = '重新生成';
    } else {
      els.generate.textContent = dirty ? '重新生成' : (state.jobId ? '再次生成' : '生成色带');
    }
  }

  /* ------------------------------ generation ------------------------------ */

  function resetJobVisual() {
    state.jobId = null;
    state.jobPlan = null;
    state.layoutN = 0;
    state.bands = [];
    state.received = 0;
    state.revealed = 0;
    state.revealPos = 0;
    state.revealStart = 0;
    state.hudAt = 0;
    state.status = 'idle';
    state.finished = false;
    state.revealRunning = false;
    els.finalImage.classList.remove('show');
    els.export.disabled = true;
    els.progressBar.style.width = '0%';
    els.canvasWrap.classList.remove('generating');
    els.revealHud.classList.remove('show');
    els.hudLive.textContent = '逐条生成';
    els.hudLive.classList.remove('done');
    setStatus('等待开始');
    setPercent('');
    clearCanvas();
  }

  async function generate() {
    if (state.busy) return;
    if (!state.videos.length) {
      showToast('请先选择视频文件');
      return;
    }
    state.busy = true;
    updateGenerateButton();

    const oldJob = state.jobId;
    resetJobVisual();
    if (oldJob) {
      try { await api(`/api/jobs/${oldJob}`, null, 'DELETE'); } catch (e) { /* ignore */ }
    }

    try {
      const result = await api('/api/jobs', planPayload());
      state.jobId = result.jobId;
      state.jobPlan = result.plan;
      state.layoutN = result.plan.bands;
      state.jobRev = state.rev;
      state.status = 'running';
      state.finished = false;

      els.emptyState.hidden = true;
      els.canvasWrap.hidden = false;
      els.canvasFrame.hidden = false;
      els.canvasWrap.classList.add('generating');
      els.revealHud.classList.add('show');
      els.hudLive.textContent = '逐条生成';
      els.hudLive.classList.remove('done');
      els.finalImage.classList.remove('show');
      els.export.disabled = true;

      fitCanvas(true);
      updateJobStats();
      setStatus('正在准备…');
      updateGenerateButton();
      pollJob(result.jobId);
    } catch (err) {
      showToast(err.message || '无法开始生成', true);
      state.status = 'idle';
      resetJobVisual();
    } finally {
      state.busy = false;
      updateGenerateButton();
    }
  }

  async function pollJob(id) {
    while (state.jobId === id) {
      let res;
      try {
        res = await api(`/api/jobs/${id}?since=${state.received}`, null, 'GET');
      } catch (err) {
        if (state.jobId === id) {
          state.status = 'error';
          setStatus(err.message || '解析中断');
          showToast(err.message || '解析中断', true);
          updateGenerateButton();
        }
        return;
      }
      if (state.jobId !== id) return;

      state.received = res.nextSince;
      if (res.bands && res.bands.length) {
        state.bands.push(...res.bands);
        if (!state.revealRunning) startReveal();
      }
      if (res.videos) updateVideoStatuses(res.videos);
      updateJobProgress(res);
      updateJobStats(res);

      if (res.status !== 'running') {
        state.status = res.status;
        if (res.status === 'error') {
          showToast(res.error || '解析失败', true);
          setStatus(`解析失败：${res.error || '未知错误'}`);
        } else if (res.status === 'cancelled') {
          setStatus('已取消');
        }
        if (res.status === 'done') {
          if (state.revealed < state.bands.length) startReveal();
          else maybeFinish();
        }
        updateGenerateButton();
        return;
      }
      await sleep(150);
    }
  }

  function updateJobProgress(res) {
    const planned = Math.max(1, state.layoutN || res.planned || 1);
    let pct;
    if (res.status === 'running') {
      pct = Math.min(1, (res.total || state.bands.length) / planned);
    } else {
      pct = Math.min(1, state.revealed / planned);
    }
    els.progressBar.style.width = `${(pct * 100).toFixed(1)}%`;
    setPercent(`${Math.round(pct * 100)}%`);

    if (res.status === 'running') {
      const running = (res.videos || []).find((v) => v.status === 'running');
      const suffix = running ? ` · ${running.name}` : '';
      setStatus(`${res.message || '解析中'}${suffix} · ${state.revealed}/${planned} 条`);
    } else if (res.status === 'done') {
      if (state.revealed < state.bands.length) {
        setStatus(`正在绘制色带 · ${state.revealed}/${planned}`);
      }
    }
  }

  function updateJobStats(res) {
    const plan = state.jobPlan;
    const planned = Math.max(1, state.layoutN || (plan ? plan.bands : 1));
    els.statDuration.textContent = plan ? fmtDuration(plan.totalDuration) : '—';
    els.statBands.textContent = state.finished
      ? String(state.bands.length)
      : `${state.revealed} / ${planned}`;
    els.statInterval.textContent = plan ? `${plan.effectiveInterval.toFixed(1)}s` : '—';
    els.statCanvas.textContent = `${state.options.width}×${state.options.height}`;
  }

  /* ------------------------------ reveal animation ------------------------------ */

  function startReveal() {
    if (state.revealRunning) return;
    if (!state.bands.length) return;
    state.revealRunning = true;
    state.lastTick = 0;
    if (!state.revealStart) state.revealStart = performance.now();
    requestAnimationFrame(tickReveal);
  }

  function tickReveal(ts) {
    const last = state.lastTick || ts;
    const dt = Math.min(120, Math.max(0, ts - last));
    state.lastTick = ts;

    const planned = Math.max(1, state.layoutN || state.bands.length || 1);
    const available = state.bands.length;
    // 整条时间轴在 4.2–9 秒内走完；条数少时足够慢，能看清一条条落下
    const dur = Math.min(9000, Math.max(4200, planned * 20));
    const speed = planned / dur; // 条 / 毫秒

    const elapsed = ts - (state.revealStart || ts);
    const ramp = 0.16 + 0.84 * Math.min(1, elapsed / 650); // 起手放慢
    const wobble = 1 + 0.12 * Math.sin(elapsed / 240);      // 轻微呼吸感

    let pos = state.revealPos + dt * speed * ramp * wobble;
    if (pos > available) pos = available;
    if (pos < state.revealPos) pos = state.revealPos;
    state.revealPos = pos;

    const whole = Math.min(available, Math.floor(pos));
    while (state.revealed < whole) {
      drawBand(state.revealed, state.bands[state.revealed], ctx);
      state.revealed += 1;
    }

    renderFrontier(pos);

    if (ts - state.hudAt >= 100) {
      updateHud(ts, pos);
      updateJobProgress({
        status: state.status,
        total: state.bands.length,
        planned,
        message: '',
        videos: [],
      });
      updateJobStats();
    }

    // 数据还没到齐：停在当前前沿，等新色带到达再继续
    if (pos >= available && state.status === 'running') {
      state.revealRunning = false;
      return;
    }
    if (state.revealed < available) {
      requestAnimationFrame(tickReveal);
      return;
    }
    state.revealRunning = false;
    maybeFinish();
  }

  function updateHud(ts, pos) {
    state.hudAt = ts;
    const planned = Math.max(1, state.layoutN || state.bands.length || 1);
    const idx = Math.max(0, Math.min(state.bands.length - 1, Math.floor(pos)));
    const color = state.bands[idx];
    if (color) {
      els.hudColor.style.background = color;
      els.hudHex.textContent = String(color).toUpperCase();
    }
    els.hudTime.textContent = fmtDuration(idx * revealInterval());
    els.hudIndex.textContent = `${String(Math.min(state.revealed, planned)).padStart(4, '0')} / ${planned}`;
  }

  function revealInterval() {
    if (state.jobPlan && state.jobPlan.effectiveInterval) return state.jobPlan.effectiveInterval;
    return state.options.interval || 1;
  }

  function maybeFinish() {
    if (state.status !== 'done') return;
    if (state.revealed < state.bands.length) return;
    if (state.finished) return;
    state.finished = true;
    if (state.cw && state.ch) fxCtx.clearRect(0, 0, state.cw, state.ch);
    els.canvasWrap.classList.remove('generating');
    els.hudLive.textContent = '完成';
    els.hudLive.classList.add('done');
    els.hudIndex.textContent = `${String(state.bands.length).padStart(4, '0')} / ${state.bands.length}`;
    els.export.disabled = false;
    els.progressBar.style.width = '100%';
    setPercent('100%');
    setStatus(`完成 · ${state.bands.length} 条色带`);
    updateJobStats();
    requestRender();
    updateGenerateButton();
  }

  /* ------------------------------ canvas drawing ------------------------------ */

  function clearCanvas() {
    if (!state.cw || !state.ch) return;
    ctx.fillStyle = '#050506';
    ctx.fillRect(0, 0, state.cw, state.ch);
    fxCtx.clearRect(0, 0, state.cw, state.ch);
  }

  function fitCanvas(force = false) {
    if (els.canvasFrame.hidden) return;
    const body = els.stageBody;
    const padX = body.clientWidth > 1000 ? 96 : 52;
    const padY = 92;
    const boxW = Math.max(120, body.clientWidth - padX);
    const boxH = Math.max(120, body.clientHeight - padY);
    const aspect = state.options.width / state.options.height;

    let w = boxW;
    let h = w / aspect;
    if (h > boxH) {
      h = boxH;
      w = h * aspect;
    }

    els.canvasFrame.style.width = `${Math.round(w)}px`;
    els.canvasFrame.style.height = `${Math.round(h)}px`;

    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const cw = Math.max(2, Math.round(w * dpr));
    const ch = Math.max(2, Math.round(h * dpr));
    if (!force && cw === state.cw && ch === state.ch) return;

    state.cw = cw;
    state.ch = ch;
    els.canvas.width = cw;
    els.canvas.height = ch;
    els.fxCanvas.width = cw;
    els.fxCanvas.height = ch;
    redrawAll();
  }

  function redrawAll() {
    if (!state.cw || !state.ch) return;
    ctx.fillStyle = '#050506';
    ctx.fillRect(0, 0, state.cw, state.ch);
    fxCtx.clearRect(0, 0, state.cw, state.ch);
    const limit = Math.min(state.revealed, state.bands.length);
    for (let i = 0; i < limit; i += 1) drawBand(i, state.bands[i], ctx);
  }

  function drawBand(i, color, target, frac = 1) {
    const n = Math.max(1, state.layoutN || state.bands.length);
    if (i >= n) return;
    const cw = state.cw;
    const ch = state.ch;
    if (!cw || !ch) return;
    const g = target || ctx;
    const layout = state.options.layout;
    const f = Math.max(0, Math.min(1, frac));
    if (f <= 0) return;
    g.fillStyle = color;

    if (layout === 'horizontal') {
      const w = cw / n;
      g.fillRect(i * w - 0.4, 0, w * f + 0.8, ch);
      return;
    }
    if (layout === 'vertical') {
      const h = ch / n;
      g.fillRect(0, i * h - 0.4, cw, h * f + 0.8);
      return;
    }
    if (layout === 'diagonal') {
      const diag = (cw + ch) / Math.sqrt(2);
      const bandW = (cw + ch) / (n * Math.sqrt(2));
      const x0 = (i * (cw + ch) / n) / Math.sqrt(2) - (cw + ch) / (2 * Math.sqrt(2));
      g.save();
      g.translate(cw / 2, ch / 2);
      g.rotate(Math.PI / 4);
      g.fillRect(x0 - 0.4, -diag * 0.8, bandW * f + 0.8, diag * 1.6);
      g.restore();
      return;
    }
    if (layout === 'rings') {
      const radius = Math.hypot(cw / 2, ch / 2);
      const t = radius / n;
      const r = (i + 0.5) * t;
      g.beginPath();
      g.arc(cw / 2, ch / 2, Math.max(0.3, r), -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * f);
      g.lineWidth = Math.max(t + 0.25, 0.7);
      g.lineCap = f < 1 ? 'round' : 'butt';
      g.strokeStyle = color;
      g.stroke();
      return;
    }
    // spiral
    const radius = Math.hypot(cw / 2, ch / 2);
    const turns = Math.max(2, state.options.spiralTurns);
    const u0 = i / n;
    const u1 = (i + f) / n;
    const steps = Math.max(2, Math.round(4 * f));
    g.beginPath();
    for (let k = 0; k <= steps; k += 1) {
      const u = u0 + ((u1 - u0) * k) / steps;
      const a = Math.PI * 2 * turns * u;
      const r = radius * u;
      const x = cw / 2 + r * Math.cos(a);
      const y = ch / 2 + r * Math.sin(a);
      if (k === 0) g.moveTo(x, y);
      else g.lineTo(x, y);
    }
    g.lineWidth = Math.max(radius / turns + 0.5, 0.7);
    g.lineCap = 'round';
    g.strokeStyle = color;
    g.stroke();
  }

  function renderFrontier(pos) {
    if (!fxCtx || !state.cw || !state.ch) return;
    fxCtx.clearRect(0, 0, state.cw, state.ch);
    const n = Math.max(1, state.layoutN || state.bands.length);
    if (pos >= n || pos <= 0) return;
    const whole = Math.floor(pos);
    const frac = Math.max(0.0001, Math.min(1, pos - whole));
    const color = state.bands[whole];
    if (!color) return;

    // 正在生长的色带
    drawBand(whole, color, fxCtx, frac);

    // 新生色带的白色高光，随生长淡出
    fxCtx.save();
    fxCtx.globalAlpha = 0.5 * Math.pow(1 - frac, 1.5);
    drawBand(whole, '#ffffff', fxCtx, frac);
    fxCtx.restore();

    const cw = state.cw;
    const ch = state.ch;
    const layout = state.options.layout;
    fxCtx.save();

    if (layout === 'horizontal') {
      const x = (pos / n) * cw;
      const gw = Math.min(Math.max((cw / n) * 7, 9), cw * 0.14);
      const grad = fxCtx.createLinearGradient(x - gw, 0, x, 0);
      grad.addColorStop(0, 'rgba(255,255,255,0)');
      grad.addColorStop(0.72, 'rgba(255,255,255,0.10)');
      grad.addColorStop(1, 'rgba(255,255,255,0.30)');
      fxCtx.fillStyle = grad;
      fxCtx.fillRect(x - gw, 0, gw, ch);
      fxCtx.fillStyle = 'rgba(255,255,255,0.72)';
      fxCtx.fillRect(x - 1, 0, 2, ch);
    } else if (layout === 'vertical') {
      const y = (pos / n) * ch;
      const gw = Math.min(Math.max((ch / n) * 7, 9), ch * 0.14);
      const grad = fxCtx.createLinearGradient(0, y - gw, 0, y);
      grad.addColorStop(0, 'rgba(255,255,255,0)');
      grad.addColorStop(0.72, 'rgba(255,255,255,0.10)');
      grad.addColorStop(1, 'rgba(255,255,255,0.30)');
      fxCtx.fillStyle = grad;
      fxCtx.fillRect(0, y - gw, cw, gw);
      fxCtx.fillStyle = 'rgba(255,255,255,0.72)';
      fxCtx.fillRect(0, y - 1, cw, 2);
    } else if (layout === 'diagonal') {
      const diag = (cw + ch) / Math.sqrt(2);
      const gw = Math.min(Math.max((diag / n) * 7, 9), diag * 0.14);
      const x = (pos * (cw + ch) / n) / Math.sqrt(2) - (cw + ch) / (2 * Math.sqrt(2));
      fxCtx.translate(cw / 2, ch / 2);
      fxCtx.rotate(Math.PI / 4);
      const grad = fxCtx.createLinearGradient(x - gw, 0, x, 0);
      grad.addColorStop(0, 'rgba(255,255,255,0)');
      grad.addColorStop(0.72, 'rgba(255,255,255,0.10)');
      grad.addColorStop(1, 'rgba(255,255,255,0.30)');
      fxCtx.fillStyle = grad;
      fxCtx.fillRect(x - gw, -diag * 0.8, gw, diag * 1.6);
      fxCtx.fillStyle = 'rgba(255,255,255,0.72)';
      fxCtx.fillRect(x - 1, -diag * 0.8, 2, diag * 1.6);
    } else if (layout === 'rings') {
      const cx = cw / 2;
      const cy = ch / 2;
      const radius = Math.hypot(cx, cy);
      const r = radius * (pos / n);
      radialGlow(cx, cy - r, Math.max(radius * 0.16, 26));
      fxCtx.beginPath();
      fxCtx.arc(cx, cy, Math.max(r, 0.3), -Math.PI / 2 - 0.6, -Math.PI / 2 + 0.02);
      fxCtx.strokeStyle = 'rgba(255,255,255,0.55)';
      fxCtx.lineWidth = 2;
      fxCtx.lineCap = 'round';
      fxCtx.stroke();
    } else {
      const cx = cw / 2;
      const cy = ch / 2;
      const radius = Math.hypot(cx, cy);
      const turns = Math.max(2, state.options.spiralTurns);
      const u = pos / n;
      const a = Math.PI * 2 * turns * u;
      const r = radius * u;
      radialGlow(cx + r * Math.cos(a), cy + r * Math.sin(a), Math.max(radius * 0.12, 20));
    }
    fxCtx.restore();
  }

  function radialGlow(x, y, r) {
    const grad = fxCtx.createRadialGradient(x, y, 0, x, y, r);
    grad.addColorStop(0, 'rgba(255,255,255,0.34)');
    grad.addColorStop(0.4, 'rgba(228,208,166,0.14)');
    grad.addColorStop(1, 'rgba(228,208,166,0)');
    fxCtx.fillStyle = grad;
    fxCtx.beginPath();
    fxCtx.arc(x, y, r, 0, Math.PI * 2);
    fxCtx.fill();
  }

  /* ------------------------------ final render ------------------------------ */

  function previewScale() {
    const scale = Math.min(1, 1500 / state.options.width, 1000 / state.options.height);
    return Math.max(0.08, Math.round(scale * 100) / 100);
  }

  function scheduleRender(delay = 320) {
    clearTimeout(state.renderTimer);
    state.renderTimer = setTimeout(() => requestRender(), delay);
  }

  async function requestRender() {
    if (!state.jobId || state.status !== 'done') return;
    if (state.revealed < state.bands.length) return;

    const token = ++state.renderToken;
    els.renderBadge.hidden = false;
    try {
      const res = await fetch('/api/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jobId: state.jobId,
          options: state.options,
          post: state.post,
          scale: previewScale(),
        }),
      });
      if (!res.ok) throw new Error('合成预览失败');
      const blob = await res.blob();
      if (token !== state.renderToken) return;
      const url = URL.createObjectURL(blob);
      const img = new Image();
      img.onload = () => {
        if (token !== state.renderToken) {
          URL.revokeObjectURL(url);
          return;
        }
        if (state.finalUrl) URL.revokeObjectURL(state.finalUrl);
        state.finalUrl = url;
        els.finalImage.src = url;
        requestAnimationFrame(() => els.finalImage.classList.add('show'));
        els.renderBadge.hidden = true;
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        if (token === state.renderToken) els.renderBadge.hidden = true;
      };
      img.src = url;
    } catch (err) {
      if (token === state.renderToken) els.renderBadge.hidden = true;
      showToast(err.message || '合成失败', true);
    }
  }

  async function exportPng() {
    if (!state.jobId || state.status !== 'done') return;
    const label = els.export.textContent;
    els.export.disabled = true;
    els.export.textContent = '导出中…';
    try {
      const res = await fetch('/api/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jobId: state.jobId,
          options: state.options,
          post: state.post,
          scale: 1,
          download: true,
        }),
      });
      if (!res.ok) throw new Error('导出失败');
      const blob = await res.blob();
      const name = (state.post.title || '').trim().replace(/[\\/:*?"<>|]/g, '') || 'anime-impression';
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `${name}-${state.options.width}x${state.options.height}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    } catch (err) {
      showToast(err.message || '导出失败', true);
    } finally {
      els.export.textContent = label;
      els.export.disabled = false;
    }
  }

  /* ------------------------------ fonts ------------------------------ */

  async function loadFonts() {
    try {
      const data = await api('/api/fonts', null, 'GET');
      state.fonts = data.fonts || [];
      state.fontMap = {};
      state.fonts.forEach((font) => { state.fontMap[font.key] = font; });

      const available = state.fonts.filter((f) => f.available);
      els.fontCount.textContent = `${available.length} / ${state.fonts.length} 已安装`;

      const groups = new Map();
      (data.categories || []).forEach((cat) => groups.set(cat, []));
      state.fonts.forEach((font) => {
        if (!groups.has(font.category)) groups.set(font.category, []);
        groups.get(font.category).push(font);
      });

      els.fontSelect.innerHTML = '';
      groups.forEach((items, category) => {
        if (!items.length) return;
        const group = document.createElement('optgroup');
        group.label = category;
        items.forEach((font) => {
          const option = document.createElement('option');
          option.value = font.key;
          option.textContent = font.available ? font.name : `${font.name}（未安装）`;
          option.disabled = !font.available;
          if (font.vibe) option.title = font.vibe;
          group.append(option);
        });
        els.fontSelect.append(group);
      });

      let preferred = 'noto-serif';
      if (!state.fontMap[preferred] || !state.fontMap[preferred].available) {
        preferred = available.length ? available[0].key : 'noto-serif';
      }
      state.post.font = preferred;
      els.fontSelect.value = preferred;
      updateFontCard();
    } catch (err) {
      showToast(err.message || '字体列表加载失败', true);
    }
  }

  function updateFontCard() {
    const font = state.fontMap[state.post.font];
    if (!font) return;
    const text = state.post.title.trim() || font.sample || '电影色带';
    els.fontPreview.src = `/api/fonts/preview?key=${encodeURIComponent(font.key)}&text=${encodeURIComponent(text)}&size=48`;
    els.fontVibe.textContent = `${font.category} · ${font.license}`;
    if (font.url) {
      els.fontDownload.hidden = false;
      els.fontDownload.href = font.url;
      els.fontDownload.textContent = font.available ? '字体来源' : '下载';
    } else {
      els.fontDownload.hidden = true;
    }
  }

  /* ------------------------------ UI sync ------------------------------ */

  function setStatus(text) { els.statusText.textContent = text; }
  function setPercent(text) { els.percentText.textContent = text; }

  function updateIntervalOutput() {
    els.intervalOut.textContent = `${state.options.interval.toFixed(1)} 秒 / 条`;
  }
  function updateBandWidthOutput() {
    els.bandWidthOut.textContent = `${state.options.bandWidth.toFixed(1)} px`;
  }
  function updateResOutput() {
    els.resOut.textContent = `${state.options.width} × ${state.options.height}`;
  }

  function syncOptionsUI() {
    els.interval.value = state.options.interval;
    els.bandWidth.value = state.options.bandWidth;
    els.spiralTurns.value = state.options.spiralTurns;
    els.spiralOut.textContent = `${state.options.spiralTurns} 圈`;
    updateIntervalOutput();
    updateBandWidthOutput();
    updateResOutput();
    els.autoCrop.checked = state.options.autoCrop;

    els.layoutGrid.querySelectorAll('.layout-card').forEach((card) => {
      card.classList.toggle('active', card.dataset.layout === state.options.layout);
    });
    els.spiralField.hidden = state.options.layout !== 'spiral';

    const preset = `${state.options.width}x${state.options.height}`;
    if (RES_PRESETS[preset]) {
      els.resPreset.value = preset;
      els.customRes.hidden = true;
    } else {
      els.resPreset.value = 'custom';
      els.customRes.hidden = false;
      els.resW.value = state.options.width;
      els.resH.value = state.options.height;
    }
    els.statCanvas.textContent = `${state.options.width}×${state.options.height}`;
  }

  function syncPostUI() {
    const p = state.post;
    els.titleInput.value = p.title;
    els.subtitleInput.value = p.subtitle;
    els.sizePct.value = p.sizePct;
    els.sizeOut.textContent = `${p.sizePct.toFixed(1)}%`;
    els.trackingPct.value = p.trackingPct;
    els.trackingOut.textContent = `${Math.round(p.trackingPct)}%`;
    els.titleColor.value = p.color;
    els.opacity.value = p.opacity;
    els.opacityOut.textContent = `${Math.round(p.opacity)}%`;
    els.offsetX.value = p.offsetX;
    els.offsetY.value = p.offsetY;
    els.noise.value = p.noise;
    els.noiseOut.textContent = String(Math.round(p.noise));
    els.grain.value = p.grain;
    els.grainOut.textContent = Number(p.grain).toFixed(1);
    els.mono.checked = p.mono;
    els.blur.value = p.blur;
    els.blurOut.textContent = `${Number(p.blur).toFixed(1)} px`;
    els.anchorOut.textContent = ANCHOR_LABELS[p.anchor] || '居中';
    els.anchorGrid.querySelectorAll('button').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.anchor === p.anchor);
    });
    if (state.fontMap[p.font]) {
      els.fontSelect.value = p.font;
    }
    updateFontCard();
  }

  function onPostChanged(options = {}) {
    scheduleRender();
    if (options.font || options.title) {
      clearTimeout(state.fontTimer);
      state.fontTimer = setTimeout(updateFontCard, 220);
    }
  }

  /* ------------------------------ bindings ------------------------------ */

  function setResolution(width, height) {
    state.options.width = Math.round(width);
    state.options.height = Math.round(height);
    els.statCanvas.textContent = `${width}×${height}`;
    updateResOutput();
    fitCanvas(true);
    schedulePlan(140);
    scheduleRender(260);
  }

  function bindControls() {
    els.addVideo.addEventListener('click', pickVideos);

    els.autoCrop.addEventListener('change', () => {
      state.options.autoCrop = els.autoCrop.checked;
      state.rev += 1;
      schedulePlan(120);
      updateGenerateButton();
    });

    els.applySkip.addEventListener('click', applyBulkSkip);
    [els.bulkSkipStart, els.bulkSkipEnd].forEach((input) => {
      input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
          event.preventDefault();
          applyBulkSkip();
        }
      });
    });

    els.interval.addEventListener('input', () => {
      state.options.interval = Number(els.interval.value);
      updateIntervalOutput();
      state.rev += 1;
      schedulePlan();
      updateGenerateButton();
    });

    els.bandWidth.addEventListener('input', () => {
      state.options.bandWidth = Number(els.bandWidth.value);
      updateBandWidthOutput();
      state.rev += 1;
      schedulePlan();
      updateGenerateButton();
    });

    els.spiralTurns.addEventListener('input', () => {
      state.options.spiralTurns = Number(els.spiralTurns.value);
      els.spiralOut.textContent = `${state.options.spiralTurns} 圈`;
      redrawAll();
      scheduleRender();
      updateGenerateButton();
    });

    els.layoutGrid.addEventListener('click', (event) => {
      const card = event.target.closest('.layout-card');
      if (!card) return;
      const layout = card.dataset.layout;
      if (layout === state.options.layout) return;
      state.options.layout = layout;
      els.layoutGrid.querySelectorAll('.layout-card').forEach((item) => {
        item.classList.toggle('active', item === card);
      });
      els.spiralField.hidden = layout !== 'spiral';
      redrawAll();
      schedulePlan(140);
      clearTimeout(state.renderTimer);
      state.renderTimer = setTimeout(requestRender, 360);
      updateGenerateButton();
    });

    els.resPreset.addEventListener('change', () => {
      const value = els.resPreset.value;
      if (value === 'custom') {
        els.customRes.hidden = false;
        els.resW.value = state.options.width;
        els.resH.value = state.options.height;
        return;
      }
      els.customRes.hidden = true;
      const [w, h] = RES_PRESETS[value];
      setResolution(w, h);
    });

    [els.resW, els.resH].forEach((input) => {
      input.addEventListener('change', () => {
        const w = Math.min(8192, Math.max(64, Number(els.resW.value) || 2560));
        const h = Math.min(8192, Math.max(64, Number(els.resH.value) || 800));
        els.resW.value = w;
        els.resH.value = h;
        setResolution(w, h);
      });
    });

    els.generate.addEventListener('click', generate);
    els.export.addEventListener('click', exportPng);

    els.titleInput.addEventListener('input', () => {
      state.post.title = els.titleInput.value;
      state.post = { ...state.post };
      onPostChanged({ title: true });
    });
    els.subtitleInput.addEventListener('input', () => {
      state.post.subtitle = els.subtitleInput.value;
      onPostChanged();
    });

    els.fontSelect.addEventListener('change', () => {
      state.post.font = els.fontSelect.value;
      updateFontCard();
      onPostChanged({ font: true });
    });

    els.sizePct.addEventListener('input', () => {
      state.post.sizePct = Number(els.sizePct.value);
      els.sizeOut.textContent = `${state.post.sizePct.toFixed(1)}%`;
      scheduleRender();
    });

    els.trackingPct.addEventListener('input', () => {
      state.post.trackingPct = Number(els.trackingPct.value);
      els.trackingOut.textContent = `${Math.round(state.post.trackingPct)}%`;
      scheduleRender();
    });

    els.titleColor.addEventListener('input', () => {
      state.post.color = els.titleColor.value;
      scheduleRender();
    });

    els.opacity.addEventListener('input', () => {
      state.post.opacity = Number(els.opacity.value);
      els.opacityOut.textContent = `${Math.round(state.post.opacity)}%`;
      scheduleRender();
    });

    els.anchorGrid.addEventListener('click', (event) => {
      const btn = event.target.closest('button[data-anchor]');
      if (!btn) return;
      state.post.anchor = btn.dataset.anchor;
      els.anchorOut.textContent = ANCHOR_LABELS[state.post.anchor] || '居中';
      els.anchorGrid.querySelectorAll('button').forEach((item) => {
        item.classList.toggle('active', item === btn);
      });
      scheduleRender();
    });

    els.offsetX.addEventListener('input', () => {
      state.post.offsetX = Number(els.offsetX.value);
      scheduleRender();
    });
    els.offsetY.addEventListener('input', () => {
      state.post.offsetY = Number(els.offsetY.value);
      scheduleRender();
    });

    els.noise.addEventListener('input', () => {
      state.post.noise = Number(els.noise.value);
      els.noiseOut.textContent = String(Math.round(state.post.noise));
      scheduleRender();
    });

    els.grain.addEventListener('input', () => {
      state.post.grain = Number(els.grain.value);
      els.grainOut.textContent = Number(state.post.grain).toFixed(1);
      scheduleRender();
    });

    els.mono.addEventListener('change', () => {
      state.post.mono = els.mono.checked;
      scheduleRender();
    });

    els.blur.addEventListener('input', () => {
      state.post.blur = Number(els.blur.value);
      els.blurOut.textContent = `${Number(state.post.blur).toFixed(1)} px`;
      scheduleRender();
    });

    els.resetPost.addEventListener('click', () => {
      state.post = { ...POST_DEFAULTS };
      syncPostUI();
      scheduleRender(120);
    });

    const resize = debounce(() => fitCanvas(), 180);
    window.addEventListener('resize', resize);
    if (window.ResizeObserver) {
      new ResizeObserver(resize).observe(els.stageBody);
    }
  }

  /* ------------------------------ boot ------------------------------ */

  async function checkHealth() {
    try {
      const info = await api('/api/health', null, 'GET');
      const ok = Boolean(info.ffmpeg);
      els.engine.classList.toggle('bad', !ok);
      els.engine.querySelector('span').textContent = ok
        ? `引擎就绪 · ${info.cpu} 线程`
        : '未找到 ffmpeg';
    } catch (err) {
      els.engine.classList.add('bad');
      els.engine.querySelector('span').textContent = '服务未连接';
    }
  }

  async function boot() {
    bindControls();
    syncOptionsUI();
    syncPostUI();
    renderVideoList();
    updateGenerateButton();
    checkHealth();
    await loadFonts();
    updatePlanUI();

    // 支持 ?videos=路径A|路径B 直接载入影片（便于从快捷方式启动）
    const preload = new URLSearchParams(location.search).get('videos');
    if (preload) {
      await addPaths(preload.split('|').map((item) => item.trim()).filter(Boolean));
    }
  }

  boot();
})();
