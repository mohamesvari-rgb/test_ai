/* Scientific Evaluation Agent — front-end (no external libraries; works offline). */
(function () {
  'use strict';

  // ------------------------------------------------------------------ i18n
  const I18N = {
    fa: {
      brand: 'دستیار ارزیابی علمی',
      'engine.checking': 'در حال بررسی موتور…',
      'history.title': 'ارزیابی‌های اخیر',
      theme: 'تغییر پوسته',
      'hero.eyebrow': 'داوری علمی با هوش مصنوعی',
      'hero.title': 'ارزیابی، مقایسه و تلفیق پاسخ‌های یک چالش علمی',
      'hero.sub': 'پاسخ‌های Word شرکت‌کنندگان را بارگذاری کنید؛ عامل هوشمند آن‌ها را با یک روبریک شفاف ۱۰۰ امتیازی داوری می‌کند، نوآوری‌ها را استخراج می‌کند، برای هر ایده راهکار بهبود می‌دهد و در پایان یک راه‌حل جامع و گزارش فارسی (Word و PDF) تحویل می‌دهد.',
      'hero.p1': 'روبریک ۱۰ معیاره و وزن‌دار',
      'hero.p2': 'استخراج نوآوری و خلاقیت',
      'hero.p3': 'مقایسه و راه‌حل جامع',
      'hero.p4': 'قابل اجرا به‌صورت کاملاً آفلاین',
      's1.title': 'تعریف چالش',
      's1.hint': 'مسئله‌ای که شرکت‌کنندگان به آن پاسخ داده‌اند را توصیف کنید.',
      's1.load': 'بارگذاری نمونه',
      'f.title': 'عنوان چالش',
      'ph.title': 'مثلاً: تشخیص زودهنگام تنش آبی گیاهان',
      'f.field': 'حوزه تخصصی',
      'ph.field': 'مثلاً: سنجش از دور / پزشکی / انرژی',
      'f.background': 'شرح مسئله و پیشینه',
      'ph.background': 'زمینه مسئله، اهمیت آن و آنچه در حال حاضر کم است.',
      'f.objectives': 'اهداف',
      'f.perline': '(هر مورد در یک خط)',
      's1.more': 'محدودیت‌ها، خروجی‌های مورد انتظار و یادداشت داور (اختیاری)',
      'f.constraints': 'محدودیت‌ها',
      'f.outputs': 'خروجی‌های مورد انتظار',
      'f.notes': 'یادداشت داور',
      'f.notesHint': '(اختیاری، اما کیفیت داوری را بسیار بهتر می‌کند)',
      'ph.notes': 'پاسخ عالی چه ویژگی‌هایی دارد و چه چیزی باید جریمه شود.',
      's2.title': 'بارگذاری پاسخ‌ها',
      's2.hint': 'فقط فایل Word (‎.docx‎)؛ یک فایل برای هر شرکت‌کننده. نام فایل، نام شرکت‌کننده در گزارش می‌شود.',
      's2.samples': 'استفاده از پاسخ‌های نمونه',
      's2.samplesN': 'افزودن {n} پاسخ نمونه',
      's2.samplesRemove': 'حذف پاسخ‌های نمونه',
      's2.choose': 'انتخاب فایل‌ها',
      's2.drag': 'یا کشیدن و رها کردن در این‌جا',
      's2.limit': 'چند فایل هم‌زمان · حداکثر ۶۴ مگابایت',
      's2.sampleTag': 'نمونه',
      's2.remove': 'حذف',
      's3.title': 'موتور هوش مصنوعی',
      's3.hint': 'آنلاین برای بهترین کیفیت و سرعت؛ آفلاین وقتی اینترنت در دسترس نیست یا داده‌ها نباید از سیستم خارج شوند.',
      'e.cloud': 'API آنلاین',
      'e.cloudDesc': 'بالاترین کیفیت و سرعت · نیازمند اینترنت',
      'e.offline': 'آفلاین (روی همین رایانه)',
      'e.offlineDesc': 'بدون اینترنت · داده‌ها از سیستم خارج نمی‌شوند',
      'e.mock': 'حالت نمایشی',
      'e.mockDesc': 'بدون هوش مصنوعی · فقط پیش‌نمایش قالب گزارش',
      'e.ready': 'آماده',
      'e.provider': 'سرویس‌دهنده',
      'e.model': 'مدل',
      'e.key': 'کلید API',
      'e.baseUrl': 'آدرس API (Base URL)',
      'e.localModel': 'مدل محلی',
      'e.server': 'سرور Ollama',
      'e.test': 'آزمایش اتصال',
      'e.keyEnv': 'کلید از فایل ‎.env‎ خوانده می‌شود ({env}). برای استفاده از کلید دیگر، آن را این‌جا وارد کنید.',
      'e.keyNeeded': 'کلید را این‌جا وارد کنید یا در فایل ‎.env‎ با نام {env} قرار دهید.',
      'e.keyPh': 'تنظیم‌شده در ‎.env‎',
      'e.signup': 'دریافت کلید',
      'e.keyOk': 'کلید تنظیم شده',
      'e.keyMissing': 'نیازمند کلید API',
      'e.olReady': 'آماده · {model}',
      'e.olNoModel': 'مدل {model} نصب نشده',
      'e.olDown': 'Ollama در حال اجرا نیست',
      'e.olRunning': '{url} · در حال اجرا (نسخه {v})',
      'e.olStopped': '{url} · در حال اجرا نیست',
      'e.olHelpDown': 'برای حالت آفلاین، Ollama را از <a href="https://ollama.com/download/windows" target="_blank" rel="noopener">ollama.com/download</a> نصب کنید و سپس <code>install_offline_model.bat</code> را اجرا کنید تا مدل دانلود شود. از آن پس <code>start.bat</code> سرور را خودکار روشن می‌کند.',
      'e.olHelpModel': 'مدل <code>{model}</code> روی این سیستم نصب نیست. <code>install_offline_model.bat</code> را اجرا کنید یا در خط فرمان بزنید: <code>ollama pull {model}</code>',
      'e.testing': 'در حال آزمایش…',
      'e.testOk': 'اتصال برقرار است · {sec} ثانیه',
      'e.testFail': 'اتصال ناموفق: {err}',
      'e.mockPill': 'حالت نمایشی (بدون هوش مصنوعی)',
      'e.offlinePill': 'آفلاین · {model}',
      's4.title': 'خروجی گزارش',
      's4.hint': 'گزارش فارسی راست‌به‌چپ با جداول و نمودارهای تحلیلی (B Nazanin و Times New Roman).',
      's4.lang': 'زبان گزارش',
      's4.fa': 'فارسی (راست‌به‌چپ)',
      's4.en': 'English',
      's4.format': 'قالب فایل',
      's4.both': 'Word و PDF',
      's4.docx': 'فقط Word (‎.docx‎)',
      's4.pdf': 'فقط PDF',
      'sum.title': 'خلاصه اجرا',
      'sum.challenge': 'چالش',
      'sum.answers': 'پاسخ‌ها',
      'sum.engine': 'موتور',
      'sum.calls': 'فراخوانی هوش مصنوعی',
      'sum.callsN': '{n} درخواست',
      'sum.noAI': 'بدون هوش مصنوعی',
      'sum.answersN': '{n} فایل',
      run: 'شروع ارزیابی',
      'sum.hint': 'همه فایل‌ها و گزارش‌ها روی همین رایانه نگهداری می‌شوند.',
      'sum.hintOnline': 'متن پاسخ‌ها برای ارزیابی به سرویس‌دهنده API ارسال می‌شود؛ فایل‌ها و گزارش‌ها روی همین رایانه می‌مانند.',
      'sum.hintOffline': 'همه پردازش‌ها روی همین رایانه انجام می‌شود و هیچ داده‌ای ارسال نمی‌شود.',
      back: 'بازگشت به تنظیمات',
      'p.running': 'در حال ارزیابی',
      'p.queued': 'در صف اجرا',
      'p.done': 'ارزیابی کامل شد',
      'p.failed': 'ارزیابی ناموفق بود',
      'p.stages': 'مراحل',
      'p.log': 'گزارش فنی اجرا',
      'p.meta': '{engine} · {n} پاسخ',
      'st.read': 'خواندن و پیش‌پردازش پاسخ‌ها',
      'st.scoring': 'امتیازدهی و استخراج نوآوری…',
      'st.improving': 'پیشنهاد راهکار بهبود…',
      'st.partDone': 'تکمیل شد',
      'st.compare': 'مقایسه و رتبه‌بندی پاسخ‌ها',
      'st.synth': 'تلفیق ایده‌ها در راه‌حل جامع',
      'st.recommend': 'نگارش توصیه نهایی',
      'st.render': 'تولید گزارش Word و PDF',
      'st.evaluate': 'ارزیابی پاسخ {name}',
      'st.waiting': 'در انتظار شروع…',
      'r.eyebrow': 'نتیجه ارزیابی',
      'r.ranking': 'رتبه‌بندی نهایی',
      'r.top': 'پاسخ برتر',
      'r.heatmap': 'امتیاز هر معیار (۰ تا ۱۰)',
      'r.heatHint': 'ردیف‌ها به ترتیب رتبه مرتب شده‌اند؛ عدد زیر نام هر معیار، وزن آن از ۱۰۰ است.',
      'r.solution': 'راه‌حل جامع',
      'r.recommendation': 'توصیه نهایی',
      'r.comparison': 'مقایسه پاسخ‌ها',
      'r.new': 'ارزیابی جدید',
      'r.clear': 'حذف فایل‌های این ارزیابی از سرور',
      'r.participant': 'شرکت‌کننده',
      'r.total': 'کل',
      'r.kParticipants': 'تعداد پاسخ‌ها',
      'r.kTop': 'بالاترین امتیاز',
      'r.kAvg': 'میانگین امتیاز',
      'r.kTime': 'مدت ارزیابی',
      'r.of100': 'از ۱۰۰',
      'r.strengths': 'نقاط قوت',
      'r.weaknesses': 'نقاط ضعف',
      'r.innovations': 'نوآوری‌های اصلی',
      'r.rationale': 'دلیل رتبه‌بندی',
      'r.salient': 'نقاط برجسته',
      'r.distinctive': 'وجه تمایز',
      'r.overlap': 'ایده‌های مشترک',
      'r.complementary': 'ایده‌های مکمل',
      'r.dlDocx': 'گزارش Word',
      'r.dlPdf': 'گزارش PDF',
      'r.dlJson': 'داده خام JSON',
      'r.empty': 'محتوایی وجود ندارد.',
      'r.meta': '{engine} · {date}',
      'r.confirmClear': 'فایل‌ها و گزارش‌های این ارزیابی از این رایانه حذف شوند؟',
      'r.pdfMissing': 'فایل PDF ساخته نشد؛ گزارش Word آماده است (جزئیات در گزارش فنی اجرا).',
      'history.empty': 'هنوز ارزیابی‌ای انجام نشده است.',
      'history.answers': '{n} پاسخ',
      'status.done': 'کامل',
      'status.error': 'ناموفق',
      'status.running': 'در حال اجرا',
      'status.queued': 'در صف',
      footer: 'ارزیابی‌های هوش مصنوعی کمکی هستند و جایگزین داوری متخصص نیستند.',
      'err.missing': 'لطفاً فیلدهای الزامی چالش (عنوان، حوزه، شرح مسئله و اهداف) را تکمیل کنید.',
      'err.noFiles': 'دست‌کم یک پاسخ ‎.docx‎ بارگذاری کنید یا از پاسخ‌های نمونه استفاده کنید.',
      'err.skipped': 'فایل «{name}» نادیده گرفته شد؛ فقط ‎.docx‎ پشتیبانی می‌شود.',
      'err.noKey': 'کلید API برای این سرویس‌دهنده تنظیم نشده است. کلید را وارد کنید (یا در ‎.env‎ قرار دهید) یا موتور آفلاین/نمایشی را انتخاب کنید.',
      'err.ollamaDown': 'Ollama در حال اجرا نیست. Ollama را اجرا کنید (start.bat این کار را خودکار انجام می‌دهد) یا موتور دیگری انتخاب کنید.',
      'err.baseUrl': 'آدرس API (Base URL) را وارد کنید.',
      'err.network': 'ارتباط با برنامه برقرار نشد. آیا پنجره start.bat هنوز باز است؟',
      'err.example': 'بارگذاری نمونه ممکن نشد.',
      'err.badKey': 'سرویس‌دهنده کلید API را نپذیرفت؛ کلید یا اعتبار حساب را بررسی کنید.',
      'err.failed': 'ارزیابی با خطا متوقف شد:',
    },
    en: {
      brand: 'Scientific Evaluation Agent',
      'engine.checking': 'Checking engine…',
      'history.title': 'Recent evaluations',
      theme: 'Toggle theme',
      'hero.eyebrow': 'AI-assisted scientific review',
      'hero.title': 'Evaluate, compare and integrate the answers to a scientific challenge',
      'hero.sub': 'Upload the participants’ Word answers. The agent reviews each one against a transparent 100-point rubric, extracts its innovations, proposes improvements for every idea and delivers an integrated solution plus a Persian report (Word and PDF).',
      'hero.p1': '10-criterion weighted rubric',
      'hero.p2': 'Innovation & creativity extraction',
      'hero.p3': 'Comparison & integrated solution',
      'hero.p4': 'Can run fully offline',
      's1.title': 'Define the challenge',
      's1.hint': 'Describe the problem the participants were asked to solve.',
      's1.load': 'Load sample',
      'f.title': 'Challenge title',
      'ph.title': 'e.g. Early detection of crop water stress',
      'f.field': 'Field',
      'ph.field': 'e.g. remote sensing / medicine / energy',
      'f.background': 'Background / problem statement',
      'ph.background': 'Context of the problem, why it matters, what is currently missing.',
      'f.objectives': 'Objectives',
      'f.perline': '(one per line)',
      's1.more': 'Constraints, expected outputs and reviewer notes (optional)',
      'f.constraints': 'Constraints',
      'f.outputs': 'Expected outputs',
      'f.notes': 'Reviewer notes',
      'f.notesHint': '(optional, but improves grading a lot)',
      'ph.notes': 'What an excellent answer looks like, and what should be penalized.',
      's2.title': 'Upload the answers',
      's2.hint': 'Word (.docx) files only, one per participant. The file name becomes the participant’s name in the report.',
      's2.samples': 'Use sample answers',
      's2.samplesN': 'Add {n} sample answers',
      's2.samplesRemove': 'Remove sample answers',
      's2.choose': 'Choose files',
      's2.drag': 'or drag them here',
      's2.limit': 'Multiple files · max 64 MB total',
      's2.sampleTag': 'sample',
      's2.remove': 'Remove',
      's3.title': 'AI engine',
      's3.hint': 'Online for the best quality and speed; offline when there is no internet or data must not leave this computer.',
      'e.cloud': 'Online API',
      'e.cloudDesc': 'Best quality and speed · needs internet',
      'e.offline': 'Offline (this computer)',
      'e.offlineDesc': 'No internet · data never leaves the machine',
      'e.mock': 'Demo mode',
      'e.mockDesc': 'No AI · previews the report layout only',
      'e.ready': 'Ready',
      'e.provider': 'Provider',
      'e.model': 'Model',
      'e.key': 'API key',
      'e.baseUrl': 'API base URL',
      'e.localModel': 'Local model',
      'e.server': 'Ollama server',
      'e.test': 'Test connection',
      'e.keyEnv': 'The key is read from .env ({env}). Type a key here to use a different one.',
      'e.keyNeeded': 'Paste the key here, or put it in .env as {env}.',
      'e.keyPh': 'set in .env',
      'e.signup': 'Get a key',
      'e.keyOk': 'Key configured',
      'e.keyMissing': 'API key required',
      'e.olReady': 'Ready · {model}',
      'e.olNoModel': 'Model {model} not installed',
      'e.olDown': 'Ollama is not running',
      'e.olRunning': '{url} · running (v{v})',
      'e.olStopped': '{url} · not running',
      'e.olHelpDown': 'For offline mode, install Ollama from <a href="https://ollama.com/download/windows" target="_blank" rel="noopener">ollama.com/download</a>, then run <code>install_offline_model.bat</code> to download the model. After that, <code>start.bat</code> starts the server automatically.',
      'e.olHelpModel': 'The model <code>{model}</code> is not installed. Run <code>install_offline_model.bat</code>, or in a terminal: <code>ollama pull {model}</code>',
      'e.testing': 'Testing…',
      'e.testOk': 'Connected · {sec} s',
      'e.testFail': 'Connection failed: {err}',
      'e.mockPill': 'Demo mode (no AI)',
      'e.offlinePill': 'Offline · {model}',
      's4.title': 'Report output',
      's4.hint': 'Right-to-left Persian report with analytical tables and charts (B Nazanin and Times New Roman).',
      's4.lang': 'Report language',
      's4.fa': 'Persian (RTL)',
      's4.en': 'English',
      's4.format': 'File format',
      's4.both': 'Word + PDF',
      's4.docx': 'Word only (.docx)',
      's4.pdf': 'PDF only',
      'sum.title': 'Run summary',
      'sum.challenge': 'Challenge',
      'sum.answers': 'Answers',
      'sum.engine': 'Engine',
      'sum.calls': 'AI requests',
      'sum.callsN': '{n} requests',
      'sum.noAI': 'no AI',
      'sum.answersN': '{n} files',
      run: 'Run evaluation',
      'sum.hint': 'All files and reports stay on this computer.',
      'sum.hintOnline': 'Answer text is sent to the API provider for evaluation; files and reports stay on this computer.',
      'sum.hintOffline': 'Everything runs on this computer; nothing is sent anywhere.',
      back: 'Back to setup',
      'p.running': 'Evaluating',
      'p.queued': 'Queued',
      'p.done': 'Evaluation complete',
      'p.failed': 'Evaluation failed',
      'p.stages': 'Stages',
      'p.log': 'Technical log',
      'p.meta': '{engine} · {n} answers',
      'st.read': 'Reading and preprocessing the answers',
      'st.scoring': 'scoring & extracting innovations…',
      'st.improving': 'proposing improvements…',
      'st.partDone': 'done',
      'st.compare': 'Comparing and ranking the answers',
      'st.synth': 'Integrating ideas into one solution',
      'st.recommend': 'Writing the final recommendation',
      'st.render': 'Rendering the Word and PDF report',
      'st.evaluate': 'Evaluating {name}',
      'st.waiting': 'Waiting to start…',
      'r.eyebrow': 'Evaluation result',
      'r.ranking': 'Final ranking',
      'r.top': 'Top answer',
      'r.heatmap': 'Score per criterion (0–10)',
      'r.heatHint': 'Rows are sorted by rank; the number under each criterion is its weight out of 100.',
      'r.solution': 'Integrated solution',
      'r.recommendation': 'Final recommendation',
      'r.comparison': 'Comparison',
      'r.new': 'New evaluation',
      'r.clear': 'Delete this evaluation’s files',
      'r.participant': 'Participant',
      'r.total': 'Total',
      'r.kParticipants': 'Answers',
      'r.kTop': 'Top score',
      'r.kAvg': 'Average score',
      'r.kTime': 'Duration',
      'r.of100': 'out of 100',
      'r.strengths': 'Strengths',
      'r.weaknesses': 'Weaknesses',
      'r.innovations': 'Main innovations',
      'r.rationale': 'Ranking rationale',
      'r.salient': 'Salient points',
      'r.distinctive': 'Distinctive points',
      'r.overlap': 'Overlapping ideas',
      'r.complementary': 'Complementary ideas',
      'r.dlDocx': 'Word report',
      'r.dlPdf': 'PDF report',
      'r.dlJson': 'Raw JSON',
      'r.empty': 'Nothing here.',
      'r.meta': '{engine} · {date}',
      'r.confirmClear': 'Delete the files and reports of this evaluation from this computer?',
      'r.pdfMissing': 'The PDF could not be produced; the Word report is ready (see the technical log).',
      'history.empty': 'No evaluations yet.',
      'history.answers': '{n} answers',
      'status.done': 'done',
      'status.error': 'failed',
      'status.running': 'running',
      'status.queued': 'queued',
      footer: 'AI evaluations are assistive and do not replace expert review.',
      'err.missing': 'Please fill in the required challenge fields (title, field, background and objectives).',
      'err.noFiles': 'Upload at least one .docx answer or use the sample answers.',
      'err.skipped': 'Skipped “{name}” — only .docx files are supported.',
      'err.noKey': 'No API key is configured for this provider. Paste a key (or put it in .env), or choose the offline or demo engine.',
      'err.ollamaDown': 'Ollama is not running. Start Ollama (start.bat does it automatically) or choose another engine.',
      'err.baseUrl': 'Enter the API base URL.',
      'err.network': 'Cannot reach the app. Is the start.bat window still open?',
      'err.example': 'Could not load the sample.',
      'err.badKey': 'The provider rejected the API key; check the key or the account balance.',
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
  function shortLabel(p) { return ((lang === 'fa' ? p.label_fa : p.label) || p.key).split(' — ')[0]; }

  // Localize the server errors a presenter is most likely to hit.
  function friendly(msg) {
    const m = String(msg || '').replace(/^\w*Error: /, '');
    if (/No API key/i.test(m)) return t('err.noKey');
    if (/Ollama is not running/i.test(m)) return t('err.ollamaDown');
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
  const state = {
    engines: null, mode: null, packs: [], samplePack: null, chosen: [],
    jobId: null, job: null, poll: null, tick: null, tab: 'solution',
  };
  const els = {
    form: $('#form'), alert: $('#alert'), files: $('#files'), drop: $('#drop'), fileList: $('#fileList'),
    packSelect: $('#packSelect'), cloudProvider: $('#cloudProvider'), cloudModel: $('#cloudModel'),
    apiKey: $('#apiKey'), baseUrl: $('#baseUrl'), ollamaModel: $('#ollamaModel'),
  };

  // ------------------------------------------------------------- language
  function applyLang() {
    const html = document.documentElement;
    html.lang = lang;
    html.dir = lang === 'fa' ? 'rtl' : 'ltr';
    $$('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
    $$('[data-i18n-ph]').forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
    $$('[data-i18n-title]').forEach(el => { el.title = t(el.dataset.i18nTitle); });
    $$('.step-num').forEach((el, i) => { el.textContent = num(i + 1); });
    $$('.lang-switch button').forEach(b => b.classList.toggle('active', b.dataset.lang === lang));
    renderPacks(); renderFiles(); renderEngines(); updateSummary();
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
  function showError(msg, el) {
    const box = el || els.alert;
    box.innerHTML = icon('alert') + '<div>' + esc(msg) + '</div>';
    box.classList.remove('hidden');
    box.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  function hideError() { els.alert.classList.add('hidden'); }

  // ------------------------------------------------------------ demo packs
  async function loadPacks() {
    try {
      const data = await api('/api/demo-packs');
      state.packs = data.packs || [];
    } catch (e) { state.packs = []; }
    renderPacks();
  }
  function currentPack() {
    return state.packs.find(p => p.id === els.packSelect.value) || state.packs[0] || null;
  }
  function renderPacks() {
    const sel = els.packSelect;
    const prev = sel.value;
    sel.innerHTML = state.packs.map(p =>
      '<option value="' + esc(p.id) + '">' + esc(lang === 'fa' ? p.title_fa : p.title) + '</option>').join('');
    if (prev && state.packs.some(p => p.id === prev)) sel.value = prev;
    sel.classList.toggle('hidden', state.packs.length < 2);
    $('#loadExample').disabled = state.packs.length === 0;
    const pack = currentPack();
    const btn = $('#useSamples');
    btn.classList.toggle('hidden', !pack);
    if (pack) {
      $('#useSamplesText').textContent = state.samplePack
        ? t('s2.samplesRemove') : t('s2.samplesN', { n: num(pack.files.length) });
    }
  }
  els.packSelect.addEventListener('change', () => {
    if (state.samplePack) state.samplePack = els.packSelect.value;
    renderPacks(); renderFiles(); updateSummary();
  });
  $('#loadExample').addEventListener('click', async () => {
    const pack = currentPack();
    try {
      const c = await api('/api/example-challenge?pack=' + encodeURIComponent(pack ? pack.id : ''));
      $('#title').value = c.title || '';
      $('#field').value = c.field || '';
      $('#background').value = c.background || '';
      $('#objectives').value = (c.objectives || []).join('\n');
      $('#constraints').value = (c.constraints || []).join('\n');
      $('#expected_outputs').value = (c.expected_outputs || []).join('\n');
      $('#evaluation_notes').value = c.evaluation_notes || '';
      $('#moreFields').open = true;
      $$('.field.invalid').forEach(f => f.classList.remove('invalid'));
      if (pack && !state.chosen.length && !state.samplePack) state.samplePack = pack.id;
      hideError(); renderPacks(); renderFiles(); updateSummary();
    } catch (e) { showError(t('err.example')); }
  });
  $('#useSamples').addEventListener('click', () => {
    const pack = currentPack();
    state.samplePack = state.samplePack ? null : (pack && pack.id);
    renderPacks(); renderFiles(); updateSummary();
  });

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
    renderFiles(); updateSummary();
  }
  function sampleFiles() {
    const pack = state.samplePack && state.packs.find(p => p.id === state.samplePack);
    return pack ? pack.files : [];
  }
  function answerCount() { return state.chosen.length + sampleFiles().length; }
  function renderFiles() {
    const items = [];
    sampleFiles().forEach(f => items.push(
      '<li>' + icon('doc') + '<span class="fname" title="' + esc(f.name) + '">' + esc(f.name) + '</span>' +
      '<span class="tag">' + esc(t('s2.sampleTag')) + '</span><span class="fsize">' + kb(f.size) + '</span></li>'));
    state.chosen.forEach((f, i) => items.push(
      '<li>' + icon('doc') + '<span class="fname" title="' + esc(f.name) + '">' + esc(f.name) + '</span>' +
      '<span class="fsize">' + kb(f.size) + '</span>' +
      '<button type="button" data-rm="' + i + '" title="' + esc(t('s2.remove')) + '">' + icon('x') + '</button></li>'));
    els.fileList.innerHTML = items.join('');
    $$('[data-rm]', els.fileList).forEach(b => b.addEventListener('click', () => {
      state.chosen.splice(Number(b.dataset.rm), 1); renderFiles(); updateSummary();
    }));
  }

  // --------------------------------------------------------------- engines
  async function loadEngines() {
    try { state.engines = await api('/api/engines'); } catch (e) { state.engines = null; }
    if (state.engines && !state.mode) {
      const d = state.engines.default;
      const prov = providerByKey(d);
      const ol = ollamaInfo();
      if (d === 'mock') state.mode = 'mock';
      else if (d === 'ollama') state.mode = 'ollama';
      else if (prov && (prov.has_key || !(ol.running && ol.hasModel))) state.mode = 'cloud';
      else state.mode = ol.running && ol.hasModel ? 'ollama' : 'cloud';
      fillCloud(prov && prov.kind !== 'ollama' && prov.kind !== 'mock' ? prov.key : 'avalai');
    }
    if (state.engines) fillOllama();
    renderEngines(); updateSummary();
  }
  // Re-check when the window regains focus (e.g. Ollama was started meanwhile).
  window.addEventListener('focus', () => { if (!$('#setupView').classList.contains('hidden')) loadEngines(); });
  function providerByKey(k) {
    return state.engines ? state.engines.providers.find(p => p.key === k) : null;
  }
  function cloudProviders() {
    return state.engines ? state.engines.providers.filter(p => p.kind === 'openai' || p.kind === 'anthropic') : [];
  }
  function ollamaInfo() {
    const o = (state.engines && state.engines.ollama) || { running: false, models: [] };
    const preset = providerByKey('ollama') || { model: '' };
    const model = (els.ollamaModel.value || preset.model || '').trim();
    const names = (o.models || []).map(m => m.name);
    const hasModel = names.some(n => n === model || n === model + ':latest' || n.split(':')[0] === model);
    return { running: !!o.running, version: o.version, url: o.base_url, names, model, hasModel };
  }
  function fillCloud(key) {
    const sel = els.cloudProvider;
    sel.innerHTML = cloudProviders().map(p =>
      '<option value="' + esc(p.key) + '">' + esc(lang === 'fa' ? p.label_fa : p.label) + '</option>').join('');
    if (key) sel.value = key;
    onProviderChange();
  }
  function onProviderChange() {
    const p = providerByKey(els.cloudProvider.value);
    if (!p) return;
    els.cloudModel.value = p.model || '';
    $('#cloudModels').innerHTML = (p.models || []).map(m => '<option value="' + esc(m) + '">').join('');
    els.baseUrl.value = p.key === 'custom' ? (p.base_url || '') : '';
    els.apiKey.value = '';
    renderEngines(); updateSummary();
  }
  function fillOllama() {
    const preset = providerByKey('ollama');
    const o = ollamaInfo();
    if (!els.ollamaModel.value) {
      els.ollamaModel.value = (preset && preset.model) || '';
      // If the configured model is missing but another one is installed, offer it.
      if (o.running && !ollamaInfo().hasModel && o.names.length) els.ollamaModel.value = o.names[0];
    }
    const suggestions = Array.from(new Set(o.names.concat((preset && preset.models) || [])));
    $('#ollamaModels').innerHTML = suggestions.map(m => '<option value="' + esc(m) + '">').join('');
  }
  els.cloudProvider.addEventListener('change', onProviderChange);
  [els.cloudModel, els.apiKey, els.baseUrl, els.ollamaModel].forEach(el =>
    el.addEventListener('input', () => { renderEngines(); updateSummary(); }));
  $$('.engine-card input').forEach(r => r.addEventListener('change', () => {
    state.mode = r.value; $('#testResult').textContent = ''; renderEngines(); updateSummary();
  }));

  function cloudReady() {
    const p = providerByKey(els.cloudProvider.value);
    return !!(p && (p.has_key || els.apiKey.value.trim()));
  }
  function engineLabel() {
    if (state.mode === 'mock') return t('e.mockPill');
    if (state.mode === 'ollama') return t('e.offlinePill', { model: ollamaInfo().model || '—' });
    const p = providerByKey(els.cloudProvider.value);
    return p ? shortLabel(p) + ' · ' + (els.cloudModel.value || p.model || '—') : '—';
  }
  function engineHealth() {
    if (!state.engines) return 'err';
    if (state.mode === 'mock') return 'ok';
    if (state.mode === 'ollama') { const o = ollamaInfo(); return !o.running ? 'err' : (o.hasModel ? 'ok' : 'warn'); }
    return cloudReady() ? 'ok' : 'warn';
  }
  function renderEngines() {
    if (!state.engines) {
      $('#enginePillText').textContent = t('engine.checking');
      return;
    }
    $$('.engine-card').forEach(c => {
      const on = c.dataset.mode === state.mode;
      c.classList.toggle('selected', on);
      $('input', c).checked = on;
    });
    // Status lines on the cards.
    const sc = $('#statusCloud');
    const ready = cloudReady();
    sc.className = 'engine-status ' + (ready ? 'ok' : 'warn');
    sc.textContent = ready ? t('e.keyOk') : t('e.keyMissing');
    const o = ollamaInfo();
    const so = $('#statusOllama');
    so.className = 'engine-status ' + (!o.running ? 'err' : (o.hasModel ? 'ok' : 'warn'));
    so.textContent = !o.running ? t('e.olDown') : (o.hasModel ? t('e.olReady', { model: o.model }) : t('e.olNoModel', { model: o.model }));

    // Detail panels.
    $('#detailCloud').classList.toggle('hidden', state.mode !== 'cloud');
    $('#detailOllama').classList.toggle('hidden', state.mode !== 'ollama');
    $('.engine-test').classList.toggle('hidden', state.mode === 'mock');

    const p = providerByKey(els.cloudProvider.value);
    if (p) {
      // Keep option labels in the current language.
      $$('option', els.cloudProvider).forEach(opt => {
        const q = providerByKey(opt.value); if (q) opt.textContent = lang === 'fa' ? q.label_fa : q.label;
      });
      $('#baseUrlField').classList.toggle('hidden', p.key !== 'custom');
      els.apiKey.placeholder = p.has_key ? t('e.keyPh') : (p.key === 'avalai' ? 'aa-…' : 'sk-…');
      let hint = esc(p.has_key ? t('e.keyEnv', { env: p.key_env }) : t('e.keyNeeded', { env: p.key_env }));
      if (p.signup_url) hint += ' <a href="' + esc(p.signup_url) + '" target="_blank" rel="noopener">' + esc(t('e.signup')) + '</a>';
      if (lang === 'fa' ? p.note_fa : p.note) hint += '<br>' + esc(lang === 'fa' ? p.note_fa : p.note);
      $('#keyHint').innerHTML = hint;
    }
    $('#ollamaServer').textContent = o.running
      ? t('e.olRunning', { url: o.url, v: o.version || '?' }) : t('e.olStopped', { url: o.url || '127.0.0.1:11434' });
    const help = $('#ollamaHelp');
    if (!o.running) { help.innerHTML = t('e.olHelpDown'); help.classList.remove('hidden'); }
    else if (!o.hasModel) { help.innerHTML = t('e.olHelpModel', { model: esc(o.model) }); help.classList.remove('hidden'); }
    else help.classList.add('hidden');

    // Top-bar pill.
    const health = engineHealth();
    $('#enginePill .dot').className = 'dot ' + health;
    $('#enginePillText').textContent = engineLabel();
    $('#enginePill').title = engineLabel();
  }
  $('#enginePill').addEventListener('click', () => {
    showView('setup');
    $('#step3').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  function engineParams() {
    if (state.mode === 'mock') return { provider: 'mock' };
    if (state.mode === 'ollama') return { provider: 'ollama', model: els.ollamaModel.value.trim() };
    return {
      provider: els.cloudProvider.value, model: els.cloudModel.value.trim(),
      api_key: els.apiKey.value.trim(), base_url: els.baseUrl.value.trim(),
    };
  }

  $('#testEngine').addEventListener('click', async () => {
    const out = $('#testResult');
    out.className = 'test-result';
    out.textContent = t('e.testing');
    const btn = $('#testEngine'); btn.disabled = true;
    try {
      const r = await api('/api/test-engine', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(engineParams()),
      });
      if (r.ok) {
        out.className = 'test-result ok';
        out.innerHTML = icon('check') + esc(t('e.testOk', { sec: num(r.latency_ms / 1000, 1) })) +
          (r.reply ? ' · «' + esc(r.reply) + '»' : '');
      } else {
        out.className = 'test-result err';
        out.textContent = t('e.testFail', { err: friendly(r.error) });
      }
    } catch (e) {
      out.className = 'test-result err';
      out.textContent = t('e.testFail', { err: e.message });
    } finally {
      btn.disabled = false;
      loadEngines();          // refresh Ollama/key status as a side effect
    }
  });

  // --------------------------------------------------------------- summary
  function updateSummary() {
    const title = $('#title').value.trim();
    $('#sumChallenge').textContent = title ? (title.length > 70 ? title.slice(0, 68) + '…' : title) : '—';
    const n = answerCount();
    $('#sumAnswers').textContent = n ? t('sum.answersN', { n: num(n) }) : '—';
    $('#sumEngine').textContent = state.engines ? engineLabel() : '—';
    const calls = n ? 3 * n + (n > 1 ? 3 : 2) : 0;
    $('#sumCalls').textContent = state.mode === 'mock' ? t('sum.noAI') : (n ? t('sum.callsN', { n: num(calls) }) : '—');
    $('#sumHint').textContent = state.mode === 'cloud' ? t('sum.hintOnline')
      : (state.mode === 'ollama' ? t('sum.hintOffline') : t('sum.hint'));
    $('#step1').classList.toggle('done', !!(title && $('#field').value.trim() && $('#background').value.trim() && $('#objectives').value.trim()));
    $('#step2').classList.toggle('done', n > 0);
    $('#step3').classList.toggle('done', engineHealth() === 'ok');
  }
  ['title', 'field', 'background', 'objectives'].forEach(id => $('#' + id).addEventListener('input', e => {
    e.target.closest('.field').classList.remove('invalid'); updateSummary();
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
    if (!answerCount()) { showError(t('err.noFiles')); return; }
    if (state.mode === 'cloud' && !cloudReady()) { showError(t('err.noKey')); return; }
    if (state.mode === 'cloud' && els.cloudProvider.value === 'custom' && !els.baseUrl.value.trim()
        && !(providerByKey('custom') || {}).base_url) { showError(t('err.baseUrl')); return; }
    if (state.mode === 'ollama' && !ollamaInfo().running) { showError(t('err.ollamaDown')); return; }

    const fd = new FormData(els.form);
    fd.delete('submissions'); fd.delete('engine_mode');
    const params = engineParams();
    Object.keys(params).forEach(k => fd.append(k, params[k]));
    if (state.samplePack) fd.append('sample_pack', state.samplePack);
    state.chosen.forEach(f => fd.append('submissions', f, f.name));

    const btn = $('#run'); btn.disabled = true;
    try {
      const data = await api('/api/evaluate', { method: 'POST', body: fd });
      openJob(data.job_id);
    } catch (err) {
      const map = { missing_fields: 'err.missing', no_files: 'err.noFiles', no_api_key: 'err.noKey', no_base_url: 'err.baseUrl' };
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
    $('#runError') && $('#runError').remove();
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
    $('#runMeta').textContent = t('p.meta', { engine: job.engine || '…', n: num((job.participants || []).length) });
    const stateKey = { done: 'p.done', error: 'p.failed', queued: 'p.queued' }[job.status] || 'p.running';
    $('#runState').textContent = t(stateKey);
    $('#progressCard').classList.toggle('done', job.status === 'done');
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
    $('#resMeta').textContent = t('r.meta', { engine: job.engine || '', date: fmtDate(job.finished_at) });

    // Downloads.
    const label = { docx: t('r.dlDocx'), pdf: t('r.dlPdf'), json: t('r.dlJson') };
    $('#downloads').innerHTML = (job.files || []).map(f => {
      const ext = (f.split('.').pop() || '').toLowerCase();
      return '<a class="dl-btn" href="/api/download/' + encodeURIComponent(job.id) + '/' + encodeURIComponent(f) + '">' +
        '<span class="ext ' + esc(ext) + '">' + esc(ext.toUpperCase()) + '</span>' + esc(label[ext] || f) + icon('download') + '</a>';
    }).join('') + (pdfWarning && !(job.files || []).some(f => f.endsWith('.pdf'))
      ? '<p class="hint small">' + esc(t('r.pdfMissing')) + '</p>' : '');

    // KPIs.
    const scores = parts.map(p => p.score);
    const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
    const dur = job.started_at && job.finished_at ? (new Date(job.finished_at) - new Date(job.started_at)) / 1000 : 0;
    const top = parts[0];
    const kpi = (labelText, value, sub) => '<div class="kpi"><div class="kpi-label">' + esc(labelText) +
      '</div><div class="kpi-value">' + value + '</div><div class="kpi-sub" title="' + esc(sub) + '">' + esc(sub) + '</div></div>';
    $('#kpis').innerHTML = [
      kpi(t('r.kParticipants'), num(parts.length), job.title || ''),
      kpi(t('r.kTop'), top ? num(top.score, 1) : '—', top ? top.participant_id : ''),
      kpi(t('r.kAvg'), scores.length ? num(avg, 1) : '—', t('r.of100')),
      kpi(t('r.kTime'), clock(dur), job.engine || ''),
    ].join('');

    // Ranking.
    $('#ranking').innerHTML = parts.map(p =>
      '<li class="rank-' + p.rank + '"><span class="rank-badge">' + num(p.rank) + '</span>' +
      '<span class="rank-name" title="' + esc(plain(p.title) || p.participant_id) + '">' + esc(p.participant_id) + '</span>' +
      '<span class="rank-score">' + num(p.score, 1) + '</span>' +
      '<span class="rank-bar"><span style="width:' + Math.max(0, Math.min(100, p.score)) + '%"></span></span></li>').join('');

    // Winner.
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
    const out = []; let list = null; let para = [];
    const flushPara = () => { if (para.length) { out.push('<p>' + inline(para.join(' ')) + '</p>'); para = []; } };
    const flushList = () => { if (list) { out.push('<ul>' + list.map(li => '<li>' + inline(li) + '</li>').join('') + '</ul>'); list = null; } };
    String(text).split(/\r?\n/).forEach(raw => {
      const line = raw.trim();
      let m;
      if (!line) { flushPara(); flushList(); return; }
      if ((m = /^#{1,6}\s+(.*)$/.exec(line))) { flushPara(); flushList(); out.push('<h4>' + inline(m[1]) + '</h4>'); return; }
      if ((m = /^(?:[-*•]|\d+[.)]|[۰-۹]+[.)])\s+(.*)$/.exec(line))) { flushPara(); (list = list || []).push(m[1]); return; }
      flushList(); para.push(line);
    });
    flushPara(); flushList();
    return out.join('');
  }
  function renderTab() {
    const s = (state.job && state.job.summary) || {};
    $$('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === state.tab));
    const panel = $('#tabPanel');
    if (state.tab === 'solution') { panel.innerHTML = mdLite(s.synthesized_solution); return; }
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
        (r.engine ? ' · ' + esc(r.engine) : '') +
        (r.top ? ' · ' + icon('trophy') + ' ' + esc(r.top.participant_id) + ' (' + num(r.top.score, 1) + ')' : '') +
        '</span></button></li>').join('') : '<li class="empty">' + esc(t('history.empty')) + '</li>';
      $$('[data-job]', ul).forEach(b => b.addEventListener('click', () => { dialog.close(); openJob(b.dataset.job); }));
    } catch (e) { ul.innerHTML = '<li class="empty">' + esc(e.message) + '</li>'; }
  });
  $('#historyClose').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });

  // ------------------------------------------------------------------ init
  applyLang();
  loadPacks();
  loadEngines();
})();
