/* Scientific Evaluation Agent — front-end (no external libraries; works offline). */
(function () {
  'use strict';

  // ------------------------------------------------------------------ i18n
  const I18N = {
    fa: {
      brand: 'دستیار ارزیابی علمی',
      'history.title': 'ارزیابی‌های اخیر',
      theme: 'تغییر پوسته',
      'head.title': 'ارزیابی جدید',
      'head.sub': 'پاسخ‌های یک چالش علمی را بر پایه معیارهای وزن‌دار ارزیابی و مقایسه کنید و گزارش تحلیلی آن را دریافت کنید.',
      's1.title': 'تعریف چالش',
      'f.title': 'عنوان چالش',
      'f.field': 'حوزه تخصصی',
      'f.background': 'شرح مسئله و پیشینه',
      'f.objectives': 'اهداف',
      'f.perline': '(هر مورد در یک خط)',
      's1.more': 'محدودیت‌ها، خروجی‌های مورد انتظار و یادداشت داور (اختیاری)',
      'f.constraints': 'محدودیت‌ها',
      'f.outputs': 'خروجی‌های مورد انتظار',
      'f.notes': 'یادداشت داور',
      's2.title': 'پاسخ‌ها',
      's2.hint': 'یک فایل Word برای هر شرکت‌کننده. نام فایل، نام شرکت‌کننده در گزارش خواهد بود.',
      's2.choose': 'انتخاب فایل‌ها',
      's2.drag': 'یا کشیدن و رها کردن در این‌جا',
      's2.limit': '‎.docx‎ · حداکثر ۶۴ مگابایت',
      's2.remove': 'حذف',
      's3.title': 'موتور هوش مصنوعی',
      'e.online': 'آنلاین',
      'e.offline': 'آفلاین',
      'e.key': 'کلید API',
      'e.keySaved': 'ذخیره‌شده روی این رایانه',
      'e.offReady': 'موتور آفلاین آماده است.',
      'e.offDown': 'موتور آفلاین در دسترس نیست. <a href="https://ollama.com/download/windows" target="_blank" rel="noopener">Ollama</a> را نصب کنید، <code>install_offline_model.bat</code> را اجرا کنید و برنامه را با <code>start.bat</code> دوباره باز کنید.',
      'e.offNoModel': 'مدل آفلاین نصب نشده است. <code>install_offline_model.bat</code> را اجرا کنید.',
      's4.title': 'خروجی گزارش',
      's4.lang': 'زبان گزارش',
      's4.fa': 'فارسی',
      's4.en': 'English',
      's4.format': 'قالب فایل',
      's4.both': 'Word و PDF',
      's4.docx': 'فقط Word',
      's4.pdf': 'فقط PDF',
      'rd.challenge': 'چالش',
      'rd.answers': 'پاسخ‌ها: {n}',
      'rd.key': 'کلید API',
      'rd.offline': 'موتور آفلاین',
      run: 'شروع ارزیابی',
      back: 'بازگشت',
      'p.running': 'در حال ارزیابی',
      'p.queued': 'در صف اجرا',
      'p.done': 'ارزیابی کامل شد',
      'p.failed': 'ارزیابی ناموفق بود',
      'p.log': 'گزارش فنی اجرا',
      'p.meta': '{n} پاسخ',
      'st.read': 'خواندن و پیش‌پردازش پاسخ‌ها',
      'st.scoring': 'امتیازدهی و استخراج نوآوری',
      'st.improving': 'پیشنهاد راهکار بهبود',
      'st.partDone': 'تکمیل شد',
      'st.compare': 'مقایسه و رتبه‌بندی پاسخ‌ها',
      'st.synth': 'تلفیق ایده‌ها در راه‌حل جامع',
      'st.recommend': 'نگارش توصیه نهایی',
      'st.render': 'تولید گزارش',
      'st.evaluate': 'ارزیابی {name}',
      'st.waiting': 'در انتظار شروع',
      'r.eyebrow': 'نتیجه ارزیابی',
      'r.ranking': 'رتبه‌بندی نهایی',
      'r.top': 'پاسخ برتر',
      'r.heatmap': 'امتیاز هر معیار (۰ تا ۱۰)',
      'r.heatHint': 'عدد زیر نام هر معیار، وزن آن از ۱۰۰ است.',
      'r.solution': 'راه‌حل جامع',
      'r.recommendation': 'توصیه نهایی',
      'r.comparison': 'مقایسه پاسخ‌ها',
      'r.new': 'ارزیابی جدید',
      'r.clear': 'حذف فایل‌های این ارزیابی',
      'r.participant': 'شرکت‌کننده',
      'r.total': 'کل',
      'r.kParticipants': 'تعداد پاسخ‌ها',
      'r.kTop': 'بالاترین امتیاز',
      'r.kAvg': 'میانگین امتیاز',
      'r.kTime': 'مدت ارزیابی',
      'r.of100': 'از ۱۰۰',
      'r.strengths': 'نقاط قوت',
      'r.strengthsOfEach': 'نقاط قوت و رویکرد هر پاسخ',
      'r.score': 'امتیاز',
      'r.weaknesses': 'نقاط ضعف',
      'r.innovations': 'نوآوری‌های اصلی',
      'r.rationale': 'دلیل رتبه‌بندی',
      'r.salient': 'نقاط برجسته',
      'r.distinctive': 'وجه تمایز',
      'r.overlap': 'ایده‌های مشترک',
      'r.complementary': 'ایده‌های مکمل',
      'r.dlDocx': 'Word',
      'r.dlPdf': 'PDF',
      'r.dlJson': 'JSON',
      'r.empty': 'محتوایی وجود ندارد.',
      'r.confirmClear': 'فایل‌ها و گزارش‌های این ارزیابی از این رایانه حذف شوند؟',
      'r.pdfMissing': 'فایل PDF ساخته نشد؛ گزارش Word آماده است.',
      'r.reportMissing': 'فایل گزارش ساخته نشد؛ نتایج ارزیابی در این صفحه و فایل JSON در دسترس است.',
      'history.empty': 'هنوز ارزیابی‌ای انجام نشده است.',
      'history.answers': '{n} پاسخ',
      'status.done': 'کامل',
      'status.error': 'ناموفق',
      'status.running': 'در حال اجرا',
      'status.queued': 'در صف',
      footer: 'ارزیابی‌های هوش مصنوعی کمکی هستند و جایگزین داوری متخصص نیستند.',
      'err.missing': 'لطفاً فیلدهای الزامی چالش (عنوان، حوزه، شرح مسئله و اهداف) را تکمیل کنید.',
      'err.noFiles': 'دست‌کم یک پاسخ ‎.docx‎ بارگذاری کنید.',
      'err.skipped': 'فایل «{name}» نادیده گرفته شد؛ فقط ‎.docx‎ پشتیبانی می‌شود.',
      'err.noKey': 'کلید API را وارد کنید.',
      'err.ollamaDown': 'موتور آفلاین در حال اجرا نیست. Ollama را اجرا کنید و دوباره تلاش کنید.',
      'err.offlineModel': 'مدل آفلاین نصب نشده است. install_offline_model.bat را اجرا کنید.',
      'err.network': 'ارتباط با برنامه برقرار نشد. آیا پنجره start.bat هنوز باز است؟',
      'err.badKey': 'کلید API پذیرفته نشد؛ کلید یا اعتبار حساب را بررسی کنید.',
      'err.failed': 'ارزیابی با خطا متوقف شد:',
    },
    en: {
      brand: 'Scientific Evaluation Agent',
      'history.title': 'Recent evaluations',
      theme: 'Toggle theme',
      'head.title': 'New evaluation',
      'head.sub': 'Assess and compare the responses to a scientific challenge against weighted criteria, and receive an analytical report.',
      's1.title': 'Challenge',
      'f.title': 'Challenge title',
      'f.field': 'Field',
      'f.background': 'Background and problem statement',
      'f.objectives': 'Objectives',
      'f.perline': '(one per line)',
      's1.more': 'Constraints, expected outputs and reviewer notes (optional)',
      'f.constraints': 'Constraints',
      'f.outputs': 'Expected outputs',
      'f.notes': 'Reviewer notes',
      's2.title': 'Responses',
      's2.hint': 'One Word file per participant. The file name becomes the participant’s name in the report.',
      's2.choose': 'Choose files',
      's2.drag': 'or drag them here',
      's2.limit': '.docx · up to 64 MB',
      's2.remove': 'Remove',
      's3.title': 'AI engine',
      'e.online': 'Online',
      'e.offline': 'Offline',
      'e.key': 'API key',
      'e.keySaved': 'Saved on this computer',
      'e.offReady': 'The offline engine is ready.',
      'e.offDown': 'The offline engine is not available. Install <a href="https://ollama.com/download/windows" target="_blank" rel="noopener">Ollama</a>, run <code>install_offline_model.bat</code>, then reopen the app with <code>start.bat</code>.',
      'e.offNoModel': 'The offline model is not installed. Run <code>install_offline_model.bat</code>.',
      's4.title': 'Report output',
      's4.lang': 'Report language',
      's4.fa': 'Persian',
      's4.en': 'English',
      's4.format': 'File format',
      's4.both': 'Word and PDF',
      's4.docx': 'Word only',
      's4.pdf': 'PDF only',
      'rd.challenge': 'Challenge',
      'rd.answers': 'Responses: {n}',
      'rd.key': 'API key',
      'rd.offline': 'Offline engine',
      run: 'Start evaluation',
      back: 'Back',
      'p.running': 'Evaluating',
      'p.queued': 'Queued',
      'p.done': 'Evaluation complete',
      'p.failed': 'Evaluation failed',
      'p.log': 'Technical log',
      'p.meta': '{n} responses',
      'st.read': 'Reading and preprocessing the responses',
      'st.scoring': 'scoring and extracting innovations',
      'st.improving': 'proposing improvements',
      'st.partDone': 'done',
      'st.compare': 'Comparing and ranking the responses',
      'st.synth': 'Integrating ideas into one solution',
      'st.recommend': 'Writing the final recommendation',
      'st.render': 'Generating the report',
      'st.evaluate': 'Evaluating {name}',
      'st.waiting': 'Waiting to start',
      'r.eyebrow': 'Evaluation result',
      'r.ranking': 'Final ranking',
      'r.top': 'Top response',
      'r.heatmap': 'Score per criterion (0–10)',
      'r.heatHint': 'The number under each criterion is its weight out of 100.',
      'r.solution': 'Integrated solution',
      'r.recommendation': 'Final recommendation',
      'r.comparison': 'Comparison',
      'r.new': 'New evaluation',
      'r.clear': 'Delete this evaluation’s files',
      'r.participant': 'Participant',
      'r.total': 'Total',
      'r.kParticipants': 'Responses',
      'r.kTop': 'Top score',
      'r.kAvg': 'Average score',
      'r.kTime': 'Duration',
      'r.of100': 'out of 100',
      'r.strengths': 'Strengths',
      'r.strengthsOfEach': 'Strengths and approach of each response',
      'r.score': 'Score',
      'r.weaknesses': 'Weaknesses',
      'r.innovations': 'Main innovations',
      'r.rationale': 'Ranking rationale',
      'r.salient': 'Salient points',
      'r.distinctive': 'Distinctive points',
      'r.overlap': 'Overlapping ideas',
      'r.complementary': 'Complementary ideas',
      'r.dlDocx': 'Word',
      'r.dlPdf': 'PDF',
      'r.dlJson': 'JSON',
      'r.empty': 'Nothing here.',
      'r.confirmClear': 'Delete the files and reports of this evaluation from this computer?',
      'r.pdfMissing': 'The PDF could not be produced; the Word report is ready.',
      'r.reportMissing': 'The report file could not be produced; the results are on this page and in the JSON file.',
      'history.empty': 'No evaluations yet.',
      'history.answers': '{n} responses',
      'status.done': 'done',
      'status.error': 'failed',
      'status.running': 'running',
      'status.queued': 'queued',
      footer: 'AI evaluations are assistive and do not replace expert review.',
      'err.missing': 'Please fill in the required challenge fields (title, field, background and objectives).',
      'err.noFiles': 'Upload at least one .docx response.',
      'err.skipped': 'Skipped “{name}”: only .docx files are supported.',
      'err.noKey': 'Enter the API key.',
      'err.ollamaDown': 'The offline engine is not running. Start Ollama and try again.',
      'err.offlineModel': 'The offline model is not installed. Run install_offline_model.bat.',
      'err.network': 'Cannot reach the app. Is the start.bat window still open?',
      'err.badKey': 'The API key was not accepted; check the key or the account balance.',
      'err.failed': 'The evaluation stopped with an error:',
    },
  };

  // Short English column labels for the criteria heatmap.
  const SHORT_EN = {
    relevance: 'Relevance', scientific_accuracy: 'Accuracy', methodology: 'Method',
    innovation: 'Innovation', creativity: 'Creativity', feasibility: 'Feasibility',
    technical_depth: 'Depth', clarity: 'Clarity', impact: 'Impact', risk_awareness: 'Risk',
  };

  // --------------------------------------------------------------- helpers
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const store = {
    get(k) { try { return localStorage.getItem('sea.' + k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem('sea.' + k, v); } catch (e) { /* private mode */ } },
  };
  let lang = store.get('lang') === 'en' ? 'en' : 'fa';

  function t(key, vars) {
    let s = (I18N[lang] && I18N[lang][key]) || I18N.fa[key] || key;
    if (vars) Object.keys(vars).forEach(k => { s = s.split('{' + k + '}').join(vars[k]); });
    return s;
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  function num(v, digits) {
    let s = digits != null ? Number(v).toFixed(digits) : String(v);
    if (lang === 'fa') s = s.replace(/[0-9]/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]).replace('.', '٫');
    return s;
  }
  function clock(sec) {
    sec = Math.max(0, Math.round(sec));
    const m = Math.floor(sec / 60), s = sec % 60;
    return num(String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0'));
  }
  function fmtDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    try {
      return d.toLocaleString(lang === 'fa' ? 'fa-IR' : 'en-GB', { dateStyle: 'medium', timeStyle: 'short' });
    } catch (e) { return d.toLocaleString(); }
  }
  // Titles come straight from the answer documents: drop Markdown/LaTeX markers.
  function plain(s) {
    return String(s || '').replace(/\*\*|__|\$+|\\text\{([^}]*)\}/g, (m, g) => g || '').replace(/^#+\s*/, '').trim();
  }
  function kb(bytes) { return num(Math.max(1, Math.round(bytes / 1024))) + (lang === 'fa' ? ' ک.ب' : ' KB'); }
  function icon(id, cls) { return '<svg' + (cls ? ' class="' + cls + '"' : '') + '><use href="#i-' + id + '"/></svg>'; }

  // Localize the server errors a presenter is most likely to hit.
  function friendly(msg) {
    const m = String(msg || '').replace(/^\w*Error: /, '');
    if (/No API key/i.test(m)) return t('err.noKey');
    if (/Ollama is not running/i.test(m)) return t('err.ollamaDown');
    if (/not installed in Ollama/i.test(m)) return t('err.offlineModel');
    if (/rejected the key/i.test(m)) return t('err.badKey');
    return m;
  }

  async function api(url, opts) {
    let r;
    try { r = await fetch(url, opts); } catch (e) { throw new Error(t('err.network')); }
    let data = {};
    try { data = await r.json(); } catch (e) { /* non-JSON */ }
    if (!r.ok) {
      const err = new Error(data.error || ('HTTP ' + r.status));
      err.code = data.code;
      throw err;
    }
    return data;
  }

  // ---------------------------------------------------------------- state
  const state = { engine: null, mode: null, chosen: [], jobId: null, job: null, poll: null, tick: null, tab: 'solution' };
  const els = {
    form: $('#form'), alert: $('#alert'), files: $('#files'), drop: $('#drop'),
    fileList: $('#fileList'), apiKey: $('#apiKey'),
  };

  // ------------------------------------------------------------- language
  function applyLang() {
    const html = document.documentElement;
    html.lang = lang;
    html.dir = lang === 'fa' ? 'rtl' : 'ltr';
    $$('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
    $$('[data-i18n-title]').forEach(el => { el.title = t(el.dataset.i18nTitle); });
    $$('.lang-switch button').forEach(b => b.classList.toggle('active', b.dataset.lang === lang));
    renderFiles(); renderEngine(); updateReadiness();
    if (state.job) renderJob(state.job);
  }
  $$('.lang-switch button').forEach(b => b.addEventListener('click', () => {
    lang = b.dataset.lang; store.set('lang', lang); applyLang();
  }));

  // ---------------------------------------------------------------- theme
  (function initTheme() {
    const saved = store.get('theme');
    if (saved === 'light' || saved === 'dark') document.documentElement.dataset.theme = saved;
    $('#themeBtn').addEventListener('click', () => {
      const root = document.documentElement;
      const dark = root.dataset.theme ? root.dataset.theme === 'dark'
        : window.matchMedia('(prefers-color-scheme: dark)').matches;
      root.dataset.theme = dark ? 'light' : 'dark';
      store.set('theme', root.dataset.theme);
    });
  })();

  // ---------------------------------------------------------------- alert
  function showError(msg) {
    els.alert.innerHTML = icon('alert') + '<div>' + esc(msg) + '</div>';
    els.alert.classList.remove('hidden');
    els.alert.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  function hideError() { els.alert.classList.add('hidden'); }

  // --------------------------------------------------------------- uploads
  els.drop.addEventListener('click', () => els.files.click());
  els.drop.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); els.files.click(); } });
  els.drop.addEventListener('dragover', e => { e.preventDefault(); els.drop.classList.add('over'); });
  els.drop.addEventListener('dragleave', () => els.drop.classList.remove('over'));
  els.drop.addEventListener('drop', e => { e.preventDefault(); els.drop.classList.remove('over'); addFiles(e.dataTransfer.files); });
  els.files.addEventListener('change', () => { addFiles(els.files.files); els.files.value = ''; });

  function addFiles(list) {
    for (const f of list) {
      if (!f.name.toLowerCase().endsWith('.docx')) { showError(t('err.skipped', { name: f.name })); continue; }
      if (!state.chosen.some(c => c.name === f.name && c.size === f.size)) state.chosen.push(f);
    }
    renderFiles(); updateReadiness();
  }
  function renderFiles() {
    els.fileList.innerHTML = state.chosen.map((f, i) =>
      '<li>' + icon('doc') + '<span class="fname" title="' + esc(f.name) + '">' + esc(f.name) + '</span>' +
      '<span class="fsize">' + kb(f.size) + '</span>' +
      '<button type="button" data-rm="' + i + '" title="' + esc(t('s2.remove')) + '">' + icon('x') + '</button></li>').join('');
    $$('[data-rm]', els.fileList).forEach(b => b.addEventListener('click', () => {
      state.chosen.splice(Number(b.dataset.rm), 1); renderFiles(); updateReadiness();
    }));
  }

  // ---------------------------------------------------------------- engine
  async function loadEngine() {
    try { state.engine = await api('/api/engine'); } catch (e) { state.engine = null; }
    if (state.engine && !state.mode) {
      const saved = store.get('mode');
      state.mode = saved === 'online' || saved === 'offline' ? saved : state.engine.mode;
    }
    renderEngine(); updateReadiness();
  }
  function isDemo() { return !!state.engine && state.engine.mode === 'demo'; }
  function isOffline() { return state.mode === 'offline'; }
  function offlineReady() {
    const o = state.engine && state.engine.offline;
    return !!(o && o.running && o.model_installed);
  }
  function engineReady() {
    if (isDemo()) return true;
    if (isOffline()) return offlineReady();
    return !!(state.engine && state.engine.online.has_key) || !!els.apiKey.value.trim();
  }
  function renderEngine() {
    $('#step3').classList.toggle('hidden', isDemo());
    $('#rdKey').classList.toggle('hidden', isDemo());
    $$('input[name=engine_mode]').forEach(r => { r.checked = r.value === (state.mode || 'online'); });
    $('#onlinePanel').classList.toggle('hidden', isOffline());
    const panel = $('#offlinePanel');
    panel.classList.toggle('hidden', !isOffline());
    if (isOffline()) {
      const o = (state.engine && state.engine.offline) || {};
      panel.classList.toggle('ok', offlineReady());
      panel.innerHTML = '<span>' + (offlineReady() ? esc(t('e.offReady'))
        : t(o.running ? 'e.offNoModel' : 'e.offDown')) + '</span>';
    }
    els.apiKey.placeholder = state.engine && state.engine.online && state.engine.online.has_key ? t('e.keySaved') : '';
    $$('.section:not(.hidden) .sec-num').forEach((el, i) => { el.textContent = num(i + 1); });
  }
  els.apiKey.addEventListener('input', updateReadiness);
  $$('input[name=engine_mode]').forEach(r => r.addEventListener('change', () => {
    state.mode = r.value; store.set('mode', r.value);
    hideError(); renderEngine(); updateReadiness();
  }));
  // Re-check when the window regains focus (e.g. Ollama was started meanwhile).
  window.addEventListener('focus', () => { if (!$('#setupView').classList.contains('hidden')) loadEngine(); });

  // ------------------------------------------------------------- readiness
  function challengeReady() {
    return ['title', 'field', 'background', 'objectives'].every(id => $('#' + id).value.trim());
  }
  function updateReadiness() {
    const n = state.chosen.length;
    const set = (id, ok, text) => { const el = $(id); el.classList.toggle('ok', ok); el.textContent = text; };
    set('#rdChallenge', challengeReady(), t('rd.challenge'));
    set('#rdAnswers', n > 0, t('rd.answers', { n: num(n) }));
    set('#rdKey', engineReady(), t(isOffline() ? 'rd.offline' : 'rd.key'));
    $('#step1').classList.toggle('done', challengeReady());
    $('#step2').classList.toggle('done', n > 0);
    $('#step3').classList.toggle('done', engineReady());
  }
  ['title', 'field', 'background', 'objectives'].forEach(id => $('#' + id).addEventListener('input', e => {
    e.target.closest('.field').classList.remove('invalid'); updateReadiness();
  }));

  // ---------------------------------------------------------------- submit
  // Enter in a single-line field must not start a (possibly long) evaluation.
  els.form.addEventListener('keydown', e => {
    if (e.key === 'Enter' && e.target.matches('input[type=text], input[type=password]')) e.preventDefault();
  });
  els.form.addEventListener('submit', async e => {
    e.preventDefault();
    hideError();
    const missing = ['title', 'field', 'background', 'objectives'].filter(id => !$('#' + id).value.trim());
    missing.forEach(id => $('#' + id).closest('.field').classList.add('invalid'));
    if (missing.length) { showError(t('err.missing')); return; }
    if (!state.chosen.length) { showError(t('err.noFiles')); return; }
    if (!engineReady()) {
      const o = state.engine && state.engine.offline;
      showError(t(!isOffline() ? 'err.noKey' : (o && o.running ? 'err.offlineModel' : 'err.ollamaDown')));
      return;
    }

    const fd = new FormData(els.form);
    fd.delete('submissions'); fd.delete('engine_mode');
    if (!isDemo() && state.engine) {
      fd.append('provider', isOffline() ? 'ollama' : state.engine.online.provider);
      if (!isOffline()) fd.append('api_key', els.apiKey.value.trim());
    }
    state.chosen.forEach(f => fd.append('submissions', f, f.name));

    const btn = $('#run'); btn.disabled = true;
    try {
      const data = await api('/api/evaluate', { method: 'POST', body: fd });
      openJob(data.job_id);
    } catch (err) {
      const map = { missing_fields: 'err.missing', no_files: 'err.noFiles', no_api_key: 'err.noKey' };
      showError(map[err.code] ? t(map[err.code]) : err.message);
    } finally { btn.disabled = false; }
  });

  // ------------------------------------------------------------------ views
  function showView(name) {
    $('#setupView').classList.toggle('hidden', name !== 'setup');
    $('#runView').classList.toggle('hidden', name !== 'run');
    window.scrollTo({ top: 0 });
  }
  $('#backBtn').addEventListener('click', () => { showView('setup'); });
  $('#newRun').addEventListener('click', () => { showView('setup'); });

  function stopTimers() {
    if (state.poll) clearInterval(state.poll);
    if (state.tick) clearInterval(state.tick);
    state.poll = state.tick = null;
  }
  async function openJob(id) {
    stopTimers();
    state.jobId = id; state.job = null; state.tab = 'solution';
    $('#log').textContent = ''; $('#stages').innerHTML = '';
    $('#resultView').classList.add('hidden');
    $('#progressCard').classList.remove('hidden');
    if ($('#runError')) $('#runError').remove();
    showView('run');
    await pollOnce();
    if (state.job && (state.job.status === 'running' || state.job.status === 'queued')) {
      state.poll = setInterval(pollOnce, 1200);
      state.tick = setInterval(() => state.job && renderClock(state.job), 1000);
    }
  }
  async function pollOnce() {
    if (!state.jobId) return;
    try {
      const job = await api('/api/status/' + state.jobId);
      state.job = job;
      renderJob(job);
      if (job.status === 'done' || job.status === 'error') stopTimers();
    } catch (e) {
      stopTimers();
      showRunError(e.message);
    }
  }

  // -------------------------------------------------------------- progress
  function parseProgress(job) {
    const parts = job.participants || [];
    const st = { read: 'pending', parts: {}, compare: 'pending', synth: 'pending', recommend: 'pending', render: 'pending' };
    parts.forEach(p => { st.parts[p] = 'pending'; });
    let pdfWarning = false;
    (job.messages || []).forEach(m => {
      let r;
      if (/^(Starting evaluation|Reading )/.test(m)) { if (st.read === 'pending') st.read = 'active'; }
      else if ((r = /^Evaluating (.+)$/.exec(m))) { st.read = 'done'; st.parts[r[1]] = 'scoring'; }
      else if ((r = /^Proposing improvements for (.+)$/.exec(m))) { st.parts[r[1]] = 'improving'; }
      else if ((r = /^Finished (.+)$/.exec(m))) { st.parts[r[1]] = 'done'; }
      else if (/^Comparing and ranking/.test(m)) { st.read = 'done'; st.compare = 'active'; }
      else if (/^Synthesizing/.test(m)) { st.compare = 'done'; st.synth = 'active'; }
      else if (/^Writing final recommendation/.test(m)) { st.synth = 'done'; st.recommend = 'active'; }
      else if (/^Rendering/.test(m)) { st.recommend = 'done'; st.render = 'active'; }
      else if (/^WARNING: PDF/.test(m)) { pdfWarning = true; }
      else if (/^Done\./.test(m)) { st.render = 'done'; }
    });
    if (job.status === 'done') {
      ['read', 'compare', 'synth', 'recommend', 'render'].forEach(k => { st[k] = 'done'; });
      parts.forEach(p => { st.parts[p] = 'done'; });
    }
    const n = parts.length;
    let units = 0;
    const total = 3 * n + 5;
    units += st.read === 'done' ? 1 : (st.read === 'active' ? 0.5 : 0);
    parts.forEach(p => { units += { pending: 0, scoring: 0.8, improving: 2, done: 3 }[st.parts[p]] || 0; });
    ['compare', 'synth', 'recommend', 'render'].forEach(k => { units += st[k] === 'done' ? 1 : (st[k] === 'active' ? 0.4 : 0); });
    return { st, pct: Math.min(100, Math.round(100 * units / total)), pdfWarning };
  }

  function renderClock(job) {
    const start = job.started_at || job.created_at;
    const end = job.finished_at && (job.status === 'done' || job.status === 'error') ? new Date(job.finished_at) : new Date();
    $('#elapsed').textContent = start ? clock((end - new Date(start)) / 1000) : clock(0);
  }

  function renderJob(job) {
    const { st, pct, pdfWarning } = parseProgress(job);
    $('#runTitle').textContent = job.title || '—';
    $('#runMeta').textContent = t('p.meta', { n: num((job.participants || []).length) });
    const stateKey = { done: 'p.done', error: 'p.failed', queued: 'p.queued' }[job.status] || 'p.running';
    $('#runState').textContent = t(stateKey);
    $('#progressBar').style.width = (job.status === 'done' ? 100 : pct) + '%';
    $('#progressPct').textContent = num(job.status === 'done' ? 100 : pct) + (lang === 'fa' ? '٪' : '%');
    $('#backBtn').classList.toggle('hidden', job.status === 'running' || job.status === 'queued');
    renderClock(job);

    // Stage list.
    const failed = job.status === 'error';
    const rows = [];
    const mark = s => (failed && (s === 'active' || s === 'scoring' || s === 'improving')) ? 'failed'
      : (s === 'done' ? 'done' : (s === 'pending' ? '' : 'active'));
    const row = (s, label, note, sub) => {
      const cls = mark(s);
      const ic = cls === 'done' ? icon('check') : (cls === 'failed' ? icon('x') : '');
      rows.push('<li class="' + cls + (sub ? ' sub' : '') + '"><span class="st-icon">' + ic + '</span>' +
        '<span class="st-label">' + esc(label) + '</span>' + (note ? '<span class="st-note">' + esc(note) + '</span>' : '') + '</li>');
    };
    row(st.read, t('st.read'));
    (job.participants || []).forEach(p => {
      const s = st.parts[p];
      const note = s === 'scoring' ? t('st.scoring') : s === 'improving' ? t('st.improving') : s === 'done' ? t('st.partDone') : '';
      row(s, t('st.evaluate', { name: p }), note, true);
    });
    row(st.compare, t('st.compare'));
    row(st.synth, t('st.synth'));
    row(st.recommend, t('st.recommend'));
    row(st.render, t('st.render'));
    $('#stages').innerHTML = rows.join('');
    const active = $$('#stages li.active .st-label');
    $('#progressLabel').textContent = job.status === 'queued' ? t('st.waiting')
      : (active.length ? active.map(a => a.textContent).slice(0, 2).join(' · ') : '');

    const log = $('#log');
    const atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 8;
    log.textContent = (job.messages || []).join('\n');
    if (atBottom) log.scrollTop = log.scrollHeight;

    if (failed) {
      $('#logBox').open = true;
      showRunError(t('err.failed') + '\n' + friendly(job.error));
    }
    if (job.status === 'done') {
      $('#progressCard').classList.add('hidden');
      renderResults(job, pdfWarning);
    }
  }

  function showRunError(msg) {
    let box = $('#runError');
    if (!box) {
      box = document.createElement('div');
      box.id = 'runError'; box.className = 'alert';
      $('#progressCard').before(box);
    }
    box.innerHTML = icon('alert') + '<div>' + esc(msg) + '</div>';
  }

  // --------------------------------------------------------------- results
  function renderResults(job, pdfWarning) {
    const s = job.summary || {};
    const parts = s.participants || [];
    $('#resultView').classList.remove('hidden');
    $('#resTitle').textContent = job.title || '—';
    $('#resMeta').textContent = fmtDate(job.finished_at);

    // Downloads.
    const label = { docx: t('r.dlDocx'), pdf: t('r.dlPdf'), json: t('r.dlJson') };
    $('#downloads').innerHTML = (job.files || []).map(f => {
      const ext = (f.split('.').pop() || '').toLowerCase();
      return '<a class="dl-btn" href="/api/download/' + encodeURIComponent(job.id) + '/' + encodeURIComponent(f) + '">' +
        icon('download') + esc(label[ext] || f) + '</a>';
    }).join('') + (pdfWarning && !(job.files || []).some(f => f.endsWith('.pdf'))
      ? '<p class="hint small">' + esc(t('r.pdfMissing')) + '</p>' : '')
      + ((job.messages || []).some(m => /^WARNING: the report file/.test(m))
        ? '<p class="hint small">' + esc(t('r.reportMissing')) + '</p>' : '');

    // KPIs.
    const scores = parts.map(p => p.score);
    const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
    const dur = job.started_at && job.finished_at ? (new Date(job.finished_at) - new Date(job.started_at)) / 1000 : 0;
    const top = parts[0];
    // The ranking may break a near-tie against raw score, so find the highest score itself.
    const best = parts.reduce((a, b) => (!a || b.score > a.score ? b : a), null);
    const kpi = (labelText, value, sub) => '<div class="kpi"><div class="kpi-label">' + esc(labelText) +
      '</div><div class="kpi-value">' + value + '</div><div class="kpi-sub" title="' + esc(sub) + '">' + esc(sub) + '</div></div>';
    $('#kpis').innerHTML = [
      kpi(t('r.kParticipants'), num(parts.length), ''),
      kpi(t('r.kTop'), best ? num(best.score, 1) : '—', best ? best.participant_id : ''),
      kpi(t('r.kAvg'), scores.length ? num(avg, 1) : '—', t('r.of100')),
      kpi(t('r.kTime'), clock(dur), ''),
    ].join('');

    // Ranking.
    $('#ranking').innerHTML = parts.map(p =>
      '<li class="rank-' + p.rank + '"><span class="rank-badge">' + num(p.rank) + '</span>' +
      '<span class="rank-name" title="' + esc(plain(p.title) || p.participant_id) + '">' + esc(p.participant_id) + '</span>' +
      '<span class="rank-score">' + num(p.score, 1) + '</span>' +
      '<span class="rank-bar"><span style="width:' + Math.max(0, Math.min(100, p.score)) + '%"></span></span></li>').join('');

    // Top response.
    const list = (items, cls, ic) => (items && items.length)
      ? '<ul class="pill-list ' + cls + '">' + items.map(x => '<li>' + icon(ic) + '<span>' + esc(x) + '</span></li>').join('') + '</ul>' : '';
    $('#winner').innerHTML = top ? (
      '<p class="winner-name">' + esc(top.participant_id) + ' · ' + num(top.score, 1) + '</p>' +
      (top.title ? '<p class="winner-title">' + esc(plain(top.title)) + '</p>' : '') +
      (top.summary ? '<p class="winner-summary">' + esc(top.summary) + '</p>' : '') +
      (top.strengths && top.strengths.length ? '<p class="mini-title">' + esc(t('r.strengths')) + '</p>' + list(top.strengths.slice(0, 3), 'good', 'check') : '') +
      (top.innovations && top.innovations.length ? '<p class="mini-title">' + esc(t('r.innovations')) + '</p>' + list(top.innovations.slice(0, 3), 'idea', 'spark') : '') +
      (top.weaknesses && top.weaknesses.length ? '<p class="mini-title">' + esc(t('r.weaknesses')) + '</p>' + list(top.weaknesses.slice(0, 2), 'bad', 'alert') : '')
    ) : '<p class="empty">' + esc(t('r.empty')) + '</p>';

    // Heatmap.
    const crit = s.criteria || [];
    let h = '<thead><tr><th class="rowh">' + esc(t('r.participant')) + '</th>';
    crit.forEach(c => {
      const name = lang === 'fa' ? (c.short_fa || c.name_fa || c.name) : (SHORT_EN[c.key] || c.name);
      h += '<th title="' + esc(lang === 'fa' ? c.name_fa : c.name) + '">' + esc(name) + '<small>' + num(c.weight) + '</small></th>';
    });
    h += '<th>' + esc(t('r.total')) + '</th></tr></thead><tbody>';
    parts.forEach(p => {
      h += '<tr><th class="rowh" title="' + esc(p.participant_id) + '">' + esc(p.participant_id) + '</th>';
      crit.forEach(c => {
        const v = Number((p.scores || {})[c.key] || 0);
        const pctv = Math.round(Math.max(0, Math.min(10, v)) * 10);
        const fg = v >= 6 ? '#fff' : 'var(--ink)';
        h += '<td style="background:color-mix(in oklab, var(--heat-hi) ' + pctv + '%, var(--heat-lo));color:' + fg + '">' + num(Math.round(v * 10) / 10) + '</td>';
      });
      h += '<td class="total">' + num(p.score, 1) + '</td></tr>';
    });
    $('#heatmap').innerHTML = h + '</tbody>';

    renderTab();
  }

  function mdLite(text) {
    if (!text || !String(text).trim()) return '<p class="empty">' + esc(t('r.empty')) + '</p>';
    const inline = s => esc(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code>$1</code>');
    const out = []; let list = null; let para = []; let table = null;
    const flushPara = () => { if (para.length) { out.push('<p>' + inline(para.join(' ')) + '</p>'); para = []; } };
    const flushList = () => { if (list) { out.push('<ul>' + list.map(li => '<li>' + inline(li) + '</li>').join('') + '</ul>'); list = null; } };
    const flushTable = () => {
      if (!table) return;
      const cells = (row, tag) => '<tr>' + row.map(c => '<' + tag + '>' + inline(c) + '</' + tag + '>').join('') + '</tr>';
      out.push('<div class="md-table"><table><thead>' + cells(table[0], 'th') + '</thead><tbody>' +
        table.slice(1).map(r => cells(r, 'td')).join('') + '</tbody></table></div>');
      table = null;
    };
    String(text).split(/\r?\n/).forEach(raw => {
      const line = raw.trim();
      let m;
      if (/^\|.*\|/.test(line)) {
        flushPara(); flushList();
        if (!/^[|:\-\s]+$/.test(line)) (table = table || []).push(line.replace(/^\||\|$/g, '').split('|').map(c => c.trim()));
        return;
      }
      flushTable();
      if (!line || /^[-*_]{3,}$/.test(line)) { flushPara(); flushList(); return; }
      if ((m = /^#{1,6}\s+(.*)$/.exec(line))) { flushPara(); flushList(); out.push('<h4>' + inline(m[1]) + '</h4>'); return; }
      if ((m = /^(?:[-*•]|\d+[.)]|[۰-۹]+[.)])\s+(.*)$/.exec(line))) { flushPara(); (list = list || []).push(m[1]); return; }
      flushList(); para.push(line);
    });
    flushPara(); flushList(); flushTable();
    return out.join('');
  }
  function renderTab() {
    const s = (state.job && state.job.summary) || {};
    $$('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === state.tab));
    const panel = $('#tabPanel');
    if (state.tab === 'solution') {
      const cell = items => (items || []).slice(0, 3).map(x => '<div>• ' + esc(x) + '</div>').join('') || '—';
      const rows = (s.participants || []).map(p => '<tr><td>' + esc(p.participant_id) + '</td><td>' + num(p.score, 1) +
        '</td><td>' + cell(p.strengths) + '</td><td>' + cell(p.innovations) + '</td></tr>').join('');
      panel.innerHTML = (rows ? '<h4>' + esc(t('r.strengthsOfEach')) + '</h4><div class="md-table"><table><thead><tr><th>' +
        esc(t('r.participant')) + '</th><th>' + esc(t('r.score')) + '</th><th>' + esc(t('r.strengths')) + '</th><th>' +
        esc(t('r.innovations')) + '</th></tr></thead><tbody>' + rows + '</tbody></table></div>' : '') + mdLite(s.synthesized_solution);
      return;
    }
    if (state.tab === 'recommendation') { panel.innerHTML = mdLite(s.final_recommendation); return; }
    const ul = items => (items && items.length) ? '<ul>' + items.map(x => '<li>' + esc(x) + '</li>').join('') + '</ul>' : '';
    let html = s.rationale ? '<h4>' + esc(t('r.rationale')) + '</h4><p>' + esc(s.rationale) + '</p>' : '';
    (s.participants || []).forEach(p => {
      if ((p.salient && p.salient.length) || (p.distinctive && p.distinctive.length)) {
        html += '<h4>' + num(p.rank) + '. ' + esc(p.participant_id) + ' · ' + num(p.score, 1) + '</h4>';
        if (p.salient && p.salient.length) html += '<p><strong>' + esc(t('r.salient')) + '</strong></p>' + ul(p.salient);
        if (p.distinctive && p.distinctive.length) html += '<p><strong>' + esc(t('r.distinctive')) + '</strong></p>' + ul(p.distinctive);
      }
    });
    if (s.overlapping_ideas && s.overlapping_ideas.length) html += '<h4>' + esc(t('r.overlap')) + '</h4>' + ul(s.overlapping_ideas);
    if (s.complementary_ideas && s.complementary_ideas.length) html += '<h4>' + esc(t('r.complementary')) + '</h4>' + ul(s.complementary_ideas);
    panel.innerHTML = html || '<p class="empty">' + esc(t('r.empty')) + '</p>';
  }
  $$('.tab').forEach(b => b.addEventListener('click', () => { state.tab = b.dataset.tab; renderTab(); }));

  $('#clear').addEventListener('click', async () => {
    if (!state.jobId || !window.confirm(t('r.confirmClear'))) return;
    try { await api('/api/cleanup/' + state.jobId, { method: 'POST' }); } catch (e) { /* already gone */ }
    stopTimers(); state.jobId = null; state.job = null;
    showView('setup');
  });

  // --------------------------------------------------------------- history
  const dialog = $('#historyDialog');
  $('#historyBtn').addEventListener('click', async () => {
    const ul = $('#historyList');
    ul.innerHTML = '<li class="empty">…</li>';
    if (typeof dialog.showModal === 'function') dialog.showModal(); else dialog.setAttribute('open', '');
    try {
      const data = await api('/api/runs');
      const runs = data.runs || [];
      ul.innerHTML = runs.length ? runs.map(r =>
        '<li><button type="button" data-job="' + esc(r.id) + '">' +
        '<span class="h-title">' + esc(r.title || r.id) + '</span>' +
        '<span class="h-badge ' + esc(r.status) + '">' + esc(t('status.' + r.status)) + '</span>' +
        '<span class="h-meta">' + esc(fmtDate(r.created_at)) + ' · ' + esc(t('history.answers', { n: num(r.count) })) +
        (r.top ? ' · ' + esc(r.top.participant_id) + ' (' + num(r.top.score, 1) + ')' : '') +
        '</span></button></li>').join('') : '<li class="empty">' + esc(t('history.empty')) + '</li>';
      $$('[data-job]', ul).forEach(b => b.addEventListener('click', () => { dialog.close(); openJob(b.dataset.job); }));
    } catch (e) { ul.innerHTML = '<li class="empty">' + esc(e.message) + '</li>'; }
  });
  $('#historyClose').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });

  // ------------------------------------------------------------------ init
  applyLang();
  loadEngine();
})();
