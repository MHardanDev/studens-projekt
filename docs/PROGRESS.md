# سجل التقدم

آخر تحديث: 2026-09-13.

## ملخص الحالة

تم تنفيذ المراحل 0 حتى 7، ثم تنفيذ المرحلة 8 لنظام طلب الملفات الناقصة وصفحة المادة وإدارة الطلبات ضمن نطاق المشرف. لا توجد مفضلة أو معاينات تلقائية أو إرسال بريد حقيقي أو إعلانات.

## فحص المشروع قبل التعديل

- مجلد العمل: مسار مجلد المشروع الرئيسي.
- الموجود قبل التعديل: مجلد `.git` فقط حسب فحص `Get-ChildItem -Force`.
- حالة Git قبل التعديل: نظيفة حسب `git status --short`.
- لم توجد وثائق مشروع سابقة أو تطبيق قائم داخل مجلد العمل.

## سجل المراحل

| المرحلة | الحالة | المنجز فعلياً | الاختبارات أو الفحوص | العوائق |
|---|---|---|---|---|
| 0 | مكتملة | حفظ الدليل وإنشاء وثائق العقد والمنتج والمعمارية والتقدم والأسئلة المفتوحة | فحص بنية المجلد، فحص Git، قراءة الدليل كاملاً على دفعات | لا عائق يمنع المرحلة 1 |
| 1 | منفذة محلياً مع عائق PostgreSQL | تأسيس موقع Django server-rendered، Custom User، إعدادات مفصولة، i18n أساس عربي/إنكليزي/ألماني، صفحة رئيسية، صفحة تصفح أولية، صفحات أخطاء، health endpoint، CI، ملفات اعتماديات | `ruff check`, `manage.py check`, `manage.py migrate --noinput`, `manage.py test`, `collectstatic --dry-run`, فحص حجم CSS | PostgreSQL لم يختبر لأن Docker وpsql غير متاحين محلياً |
| 2 | مكتملة محلياً مع عائق PostgreSQL المتبقي | أضيفت نماذج الفهرس الدراسي والملفات الوصفية، Django admin، seed تجريبي، وربط `/ar/browse/` بقاعدة البيانات | `makemigrations catalog`, `migrate`, `seed_demo_catalog`, `check`, `test`, `ruff`, طلبات HTTP وظهور أسماء seed | PostgreSQL لم يختبر لأن Docker وpsql غير متاحين محلياً |
| 3 | مكتملة محلياً مع عائق اختبارات أجهزة حقيقية | واجهة عربية RTL موبايل أولاً، بحث GET، نتائج وحالات فارغة، عرض أحدث الملفات والكليات والمواد الناقصة، مبدل لغة | `check`, `test`, `ruff`, طلبات HTTP، تحقق نصي للبحث وRTL/LTR، فحص حجم CSS | لم تختبر على Android حقيقي أو Playwright |
| 4 | مكتملة محلياً | تسجيل دخول/خروج، أدوار، نطاقات مساهم/مشرف، دعوات single-use، قبول دعوة، admin مقيد لإدارة الدعوات والنطاقات | `makemigrations accounts`, `migrate`, `check`, `test`, `ruff`, طلبات HTTP للصفحات العامة والدخول | لم يختبر بريد حقيقي أو MFA أو صلاحيات مراجعة الملفات لأنها خارج نطاق المرحلة |
| 5 | مكتملة محلياً مع عائق فحص antivirus الحقيقي | صفحة رفع PDF للمساهم الموثوق ضمن نطاقه، تخزين خاص، تحقق امتداد/نوع/حجم/توقيع، حالة `uploaded_pending_scan`, و`scan_status=pending` | `makemigrations catalog`, `migrate`, `check`, `test`, `ruff` | ClamAV/worker الحقيقي غير متاح وغير منفذ؛ النظام fail-closed |
| 6 | مكتملة محلياً مع بقاء التنزيل الآمن مؤجلاً | Workflow مراجعة، صفحة مشرف، اعتماد/رفض، نسخ منشورة ثابتة، وبلاغات على الملفات المنشورة | `makemigrations catalog`, `migrate`, `seed_demo_catalog`, `check`, `test`, `ruff` | لا تنزيل عام بعد، ولا ClamAV/worker فعلي بعد |
| 7 | مكتملة وموثقة محلياً | صفحة ملف عامة، تنزيل خاص يدعم HEAD وRange وIf-Range مع Cache-Control: no-store، حقل صفحة آمن، تفاصيل الإصدار، اختبار تجميع Range وبصمة SHA-256، كوكي توفير البيانات، استئناف آخر مسار، وتوثيق Nginx للإنتاج | `check`, `test` (54 اختباراً), `ruff` | Nginx لم يشغل محلياً واكتفي بتوثيق إعداده؛ لم يختبر PDF حقيقي ضخم على اتصال ضعيف |
| 8 | مكتملة ضمن النطاق المطلوب | طلب ملف بلا حساب، صفحة مادة، حد إرسال، خصوصية البريد، وإدارة حالات وربط ملف ضمن ModeratorScope | migration، `check`, `test` (67 اختباراً), `ruff` | cache الإنتاجية وreverse proxy لم يختبرا؛ المفضلة خارج الطلب الحالي |
| 9 | غير منفذة | لا صفحات ثقة أو مسارات حقوق بعد | غير منفذ | تحتاج قرارات مالك المشروع قبل الإطلاق |
| 10 | غير منفذة | لا SEO أو قياس أو بنية إعلانات بعد | غير منفذ | الإعلانات تحتاج موافقة وبيانات خارجية لاحقاً |
| 11 | غير منفذة | لا تقرير QA بعد | غير منفذ | تعتمد على اكتمال المراحل السابقة |
| 12 | غير منفذة | لا تجهيز تشغيل أو إطلاق بعد | غير منفذ | الإطلاق قرار منفصل بعد إزالة العوائق |

## ما تغير في المرحلة 0

- أضيف [docs/BUILD_GUIDE_AR.md](BUILD_GUIDE_AR.md) كنسخة مرجعية داخل المشروع.
- أضيف [../AGENTS.md](../AGENTS.md) لقواعد العمل الثابتة.
- أضيف [PRODUCT.md](PRODUCT.md) لتعريف الهدف والنطاق والمتطلبات.
- أضيف [ARCHITECTURE.md](ARCHITECTURE.md) لتثبيت القرارات المعمارية والعقود.
- أضيف [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) للأسئلة التي تحتاج قرار مالك المشروع.

## ما تغير في المرحلة 1

- أضيف مشروع Django server-rendered بإعدادات مفصولة للتطوير والاختبار والإنتاج.
- أضيف `accounts.User` كـ Custom User مبكر قبل بناء نماذج المحتوى.
- أضيف تطبيق `pages` للصفحات العامة الخفيفة.
- أضيفت الصفحة الرئيسية العربية وصفحة تصفح كليات/مواد أولية ببيانات تجريبية.
- أضيف أساس تعدد اللغات: العربية افتراضياً، وبادئات `ar`, `en`, `de`.
- أضيفت صفحات 403 و404 و500 و`/health/`.
- أضيف CSS محلي بلا JavaScript إلزامي، وحجم `static/css/site.css` هو 4187 بايت.
- أضيفت ملفات الاعتماديات وDocker Compose لقاعدة PostgreSQL وCI بسيط.

## ما تغير في المرحلة 2

- أضيف تطبيق `catalog`.
- أضيفت نماذج `University`, `Faculty`, `Program`, `AcademicYearLevel`, `Term`, `Course`, `CourseOffering`, و`StudyDocument`.
- أضيفت قيود تفرد وفهارس أساسية وعلاقات تسمح بإدارة سنوات وفصول ومواد متعددة دون أرقام ثابتة في النموذج.
- أضيف Django admin للبحث والفلترة والترتيب وعرض الحقول المهمة.
- أضيف أمر `seed_demo_catalog` لإنشاء جامعة تشرين، كلية الاقتصاد، برنامج اقتصاد، 4 سنوات، فصلين لكل سنة، 3 مواد، و3 ملفات تجريبية بلا PDF.
- أصبحت صفحة `/ar/browse/` تقرأ من قاعدة البيانات وتعرض حالة فارغة إن لم توجد بيانات.
- أضيفت اختبارات لإنشاء الهيكل، seed، صفحة التصفح، وعدم افتراض حد أربع سنوات.

## ما تغير في المرحلة 3

- حسنت `templates/base.html` بإضافة مبدل لغة HTML عادي.
- أعيد تصميم `templates/pages/home.html` كصفحة أداة دراسية مختصرة: بحث، وصول للتصفح، أحدث الملفات، الكليات، والمواد الناقصة.
- أعيد تصميم `templates/pages/browse.html` لعرض الهيكل الدراسي الكامل والملفات التجريبية لكل مادة من قاعدة البيانات.
- أضيف بحث GET في `pages/views.py` للمواد وعناوين الملفات المعتمدة.
- أضيف `pages/context_processors.py` لبناء روابط اللغات دون JavaScript.
- حدث `static/css/site.css` لتخطيط موبايل أولاً، أزرار وروابط سهلة الضغط، وقوائم مضغوطة.
- حدثت اختبارات `pages/tests.py` لتغطي الرئيسية، التصفح، مبدل اللغة، البحث الناجح، وحالة عدم وجود نتائج.

## ما تغير في المرحلة 4

- أضيف حقل `role` إلى `accounts.User` بأدوار `Student`, `TrustedContributor`, `FacultyModerator`, و`SiteAdmin`.
- أضيفت نماذج `ContributorScope`, `ModeratorScope`, و`ContributorInvitation`.
- أضيفت صفحة تسجيل دخول وصفحة قبول دعوة، وخروج عبر POST.
- أضيفت روابط دخول/خروج صغيرة في الهيدر.
- أضيفت إدارة Django للنطاقات والدعوات مع فلاتر وبحث وقيود إدارة لـ`SiteAdmin` أو `superuser`.
- رابط الدعوة يظهر في admin فقط، ولا يرسل بريد حقيقي.
- أضيفت اختبارات للدخول والخروج، بقاء الصفحات العامة متاحة، إنشاء الدعوة، قبولها مرة واحدة، revoked/expired، عدم منح النشر، عدم تحويل المشرف إلى superuser، وعدم جعل نطاق المساهم عاماً.

## ما تغير في المرحلة 5

- أضيفت حقول رفع وفحص أولية إلى `StudyDocument`.
- أضيف `catalog/forms.py` بنموذج رفع PDF يتحقق من الامتداد، نوع المحتوى، الحجم، وتوقيع `%PDF-`.
- أضيفت صفحة رفع خفيفة في `templates/catalog/upload_document.html`.
- أضيف مسار `/ar/contribute/upload/` للمساهمين الموثوقين ضمن نطاق صالح.
- أضيف إعداد `MEDIA_ROOT` الخاص و`MAX_UPLOAD_SIZE`.
- حدثت admin لعرض وفلاتر `status`, `scan_status`, `contributor`, و`course`.
- عدلت استعلامات العرض العام لتعرض فقط الملفات `approved + clean`.
- أضيفت اختبارات منع الزائر والطالب والمساهم بلا نطاق، قبول الرفع ضمن نطاق، رفض غير PDF، رفض الحجم الزائد، منع النشر التلقائي، وعدم ظهور الملف المرفوع في التصفح العام.

## ما تغير في المرحلة 6

- أضيفت حالة `pending_review` الصريحة، وأصبح الانتقال إليها يتطلب `scan_status=clean`.
- أضيفت حقول المراجعة على `StudyDocument`: `reviewed_by`, `reviewed_at`, `rejection_reason`, و`published_version`.
- أضيفت طرق `move_to_pending_review()`, `approve()`, و`reject()` لضبط الانتقال بين الحالات.
- أضيف `accounts/permissions.py` للتحقق من نطاق المشرف ومنع مراجعة الشخص لملفه.
- أضيف `DocumentVersion` كنسخة منشورة ثابتة تحفظ metadata واسم الملف الداخلي وSHA-256 عند توفر الملف.
- أضيف `DocumentReport` للبلاغات، مع أنواع وحالات واضحة.
- أضيفت صفحة `/ar/moderation/documents/` للمشرفين ضمن نطاقهم فقط، وتعمل عبر POST للاعتماد والرفض.
- أضيفت صفحة بلاغ للملفات المنشورة فقط، ورابط بلاغ خفيف في صفحة التصفح دون رابط تنزيل.
- حدثت Django admin لعرض النسخ والبلاغات وحقول المراجعة وفلاترها، مع إجراء لإرسال الملفات النظيفة إلى المراجعة.
- حدث seed التجريبي لإنشاء `DocumentVersion` وربطها بالملفات التجريبية المعتمدة حتى تبقى ظاهرة في الصفحات العامة.
- أضيفت اختبارات المرحلة 6 لقواعد الفحص والمراجعة والنطاقات والرفض والنسخ والبلاغات.

## ما تغير في المرحلة 7

- أضيفت صفحة `/ar/documents/<id>/` لعرض metadata النسخة المنشورة وزري التنزيل والبلاغ.
- أضيف endpoint تنزيل خادمي خاص يتحقق من `approved + clean + published_version` ومن مسار الملف الداخلي.
- أضيف دعم `GET`, `HEAD`, نطاق بايتات واحد، `If-Range`, `206`, و`416` مع رؤوس ETag والحجم والنطاق وترويسة `Cache-Control: no-store` لمنع تخزين الملفات المحكومة بالحجب.
- أصبح الملف يبث على دفعات 64 KiB ولا يقرأ كاملاً إلى الذاكرة.
- أضيف حقل `page_count` (اختياري null=True) في `DocumentVersion` فقط دون محاولة استخراج تخمينية ودون حزم خارجية جديدة.
- تعرض صفحة الملف العامة حجم الملف ورقم الإصدار المنشور وعدد الصفحات إذا كان متاحاً بأمان.
- ربطت الملفات المنشورة في الرئيسية والبحث والتصفح بصفحاتها العامة، وبقيت الحالات غير المنشورة مخفية.
- أضيف وضع توفير البيانات عبر كوكي غير حساس وPOST بلا JavaScript، ولا توجد معاينة PDF تلقائية.
- أضيف حفظ آخر ملف أو تصفح أو بحث كمسار داخلي محدود، مع رابط `تابع من آخر مكان` في الرئيسية.
- أضيف اختبار واقعي مجزأ لإعادة تجميع استجابات Range لملف 16 KiB والتحقق من تطابق بايتات وبصمة SHA-256 للملف الكامل.
- وثقت معمارية وإعداد Nginx المطلوب مستقبلاً للإنتاج عبر `X-Accel-Redirect` في `ARCHITECTURE.md` مع إبقاء التسليم المباشر عبر Django للتطوير المحلي.
- أضيفت اختبارات المرحلة 7 للإتاحة العامة والتنزيل والرؤوس والنطاقات وإعادة التجميع والتفضيلات والاستئناف.

## ما تغير في المرحلة 8

- أضيف نموذج `MissingMaterialRequest` بعلاقة موحدة مع `CourseOffering` وأنواع طلب وحالات وملاحظات مشرف ورابط اختياري لملف منشور.
- أضيفت migration `catalog.0005_missingmaterialrequest` وطبقت محلياً على SQLite.
- أضيف نموذج طلب عام لا يحتاج حساباً، مع وصف مطلوب واسم وبريد اختياريين لا يعرضان للعامة.
- أضيف محدد إرسال قابل للضبط: ثلاثة طلبات صحيحة خلال عشر دقائق لكل حساب أو هوية زائر مشتقة دون تخزين IP في الطلب.
- أضيفت صفحة مادة `/ar/courses/<id>/` تعرض السياق والملفات المنشورة وزر طلب مسبق الاختيار.
- أضيفت روابط `اطلب ملفاً ناقصاً` في الرئيسية والتصفح وصفحة المادة، وكلها تعمل دون JavaScript.
- أضيفت صفحة `/ar/moderation/requests/` لتغيير الحالة والملاحظات وربط ملف منشور ضمن `ModeratorScope`.
- بقي `TrustedContributor` ممنوعاً من إدارة الطلبات افتراضياً؛ يحتاج permission صريحاً ونطاق إشراف مطابقاً.
- قيد Django admin للطلبات بحسب الدور والنطاق، وجعل الحذف والإضافة المباشرة مقتصرين على superuser.
- أضيفت 13 اختباراً للطلب العام وCSRF والحقول الفارغة والخصوصية والحد المؤقت والحالات والنطاق وربط الملف وقيمة المادة غير الصالحة.

## الاختبارات المنفذة

- `Get-ChildItem -Force`: أكد أن المشروع لم يكن يحتوي إلا `.git` قبل الوثائق.
- `git status --short`: أكد أن حالة Git كانت نظيفة قبل التعديل.
- مراجعة واستيعاب الدليل المرجعي `docs/BUILD_GUIDE_AR.md` كاملاً على دفعات.
- `python --version`: البيئة الحالية Python 3.13.5.
- `python -m django --version`: لم يكن Django مثبتاً قبل المرحلة 1.
- تثبيت الاعتماديات داخل `.venv` بعد السماح باتصال الشبكة.
- `.venv\Scripts\python manage.py makemigrations accounts`: أنشأ migration المستخدم المخصص.
- `.venv\Scripts\python manage.py migrate --noinput`: نجح على SQLite المحلي الاحتياطي.
- `.venv\Scripts\python manage.py check`: نجح بلا مشاكل.
- `.venv\Scripts\python manage.py test`: نجحت 4 اختبارات.
- `.venv\Scripts\python -m ruff check .`: نجح بعد تنظيف scaffold وضبط الاستثناءات المحدودة.
- `.venv\Scripts\python manage.py collectstatic --noinput --dry-run`: نجح، مع ملاحظة أن الأمر كتب `staticfiles/` رغم خيار dry-run في هذه البيئة، والمجلد مستثنى من Git.
- تشغيل خادم التطوير على `http://127.0.0.1:8000/` كعملية خلفية مخفية.
- `Invoke-WebRequest http://127.0.0.1:8000/ar/`: رجع 200.
- `Invoke-WebRequest http://127.0.0.1:8000/ar/browse/`: رجع 200.
- `Invoke-WebRequest http://127.0.0.1:8000/health/`: رجع 200 و`{"status": "ok"}`.
- `docker compose version`, `psql --version`, `pg_isready --version`: غير متاحة في البيئة الحالية.
- `.venv\Scripts\python manage.py makemigrations catalog`: أنشأ migration المرحلة 2.
- `.venv\Scripts\python manage.py migrate --noinput`: طبق migration `catalog.0001_initial` على SQLite المحلي.
- `.venv\Scripts\python manage.py seed_demo_catalog`: نجح وأنشأ البيانات التجريبية.
- عد بيانات seed بعد التشغيل: 1 جامعة، 1 كلية، 1 برنامج، 4 سنوات، 8 فصول، 3 مواد، 3 ملفات تجريبية.
- تحقق HTTP من `/ar/browse/`: رجع 200 واحتوى `جامعة تشرين` و`كلية الاقتصاد` والمواد الثلاث.
- `.venv\Scripts\python manage.py check`: نجح بعد المرحلة 3.
- `.venv\Scripts\python manage.py test`: نجحت 13 اختباراً بعد المرحلة 3.
- `.venv\Scripts\python -m ruff check .`: نجح بعد المرحلة 3.
- `Invoke-WebRequest` على `/ar/`, `/ar/browse/`, `/en/`, `/de/`, و`/health/`: كلها رجعت 200.
- تحقق نصي من بحث `/ar/?q=محاسبة`: ظهر نص البحث ونتيجة `مبادئ المحاسبة`.
- تحقق نصي من بحث بلا نتائج `/ar/?q=لاشيء`: ظهرت حالة `لا توجد نتائج مطابقة`.
- تحقق نصي من الاتجاه: `/ar/` يحتوي `dir="rtl"`، و`/en/` و`/de/` يحتويان `dir="ltr"`.
- حجم `static/css/site.css` بعد المرحلة 3 هو 7217 بايت.
- `.venv\Scripts\python manage.py makemigrations accounts`: أنشأ migration المرحلة 4.
- `.venv\Scripts\python manage.py migrate --noinput`: طبق migration المرحلة 4 على SQLite المحلي.
- `.venv\Scripts\python manage.py check`: نجح بعد المرحلة 4.
- `.venv\Scripts\python manage.py test`: نجحت 23 اختباراً بعد المرحلة 4.
- `.venv\Scripts\python -m ruff check .`: نجح بعد المرحلة 4.
- `Invoke-WebRequest` على `/ar/`, `/ar/browse/`, `/ar/accounts/login/`, و`/health/`: كلها رجعت 200.
- `.venv\Scripts\python manage.py makemigrations catalog`: أنشأ migration المرحلة 5.
- `.venv\Scripts\python manage.py migrate --noinput`: طبق migration المرحلة 5 على SQLite المحلي.
- `.venv\Scripts\python manage.py check`: نجح بعد المرحلة 5.
- `.venv\Scripts\python manage.py test`: نجحت 32 اختباراً بعد المرحلة 5.
- `.venv\Scripts\python -m ruff check .`: نجح بعد المرحلة 5.
- `.venv\Scripts\python manage.py makemigrations catalog`: أنشأ migration المرحلة 6.
- `.venv\Scripts\python manage.py migrate --noinput`: طبق migration المرحلة 6 على SQLite المحلي.
- `.venv\Scripts\python manage.py seed_demo_catalog`: حدث بيانات demo بربط النسخ المنشورة.
- `.venv\Scripts\python manage.py check`: نجح بعد المرحلة 6.
- `.venv\Scripts\python manage.py test`: نجحت 42 اختباراً بعد المرحلة 6.
- `.venv\Scripts\python -m ruff check .`: نجح بعد المرحلة 6.
- `.venv\Scripts\python manage.py check`: نجح بعد المرحلة 7 بلا مشاكل.
- `.venv\Scripts\python manage.py test`: نجحت 54 اختباراً بعد المرحلة 7.
- `.venv\Scripts\python -m ruff check .`: نجح بعد المرحلة 7.
- `.venv\Scripts\python manage.py makemigrations --check --dry-run`: لم يجد تغييرات نماذج غير مولدة.
- اختبارات المرحلة 7 المعزولة: نجحت 12 اختباراً، ومنها `HEAD`, `206`, `416`, و`If-Range` على ملف اختبار ذي توقيع PDF.
- فحص HTTP محلي: `/ar/` و`/ar/browse/` و`/health/` رجعت `200`، و`/ar/moderation/documents/` رجعت `302` إلى تسجيل الدخول للزائر كما يجب.
- `.venv\Scripts\python manage.py makemigrations catalog`: أنشأ migration المرحلة 8.
- `.venv\Scripts\python manage.py migrate --noinput`: طبق `catalog.0005_missingmaterialrequest` على SQLite المحلي.
- اختبارات المرحلة 8 المعزولة: نجحت 13 اختباراً.
- `.venv\Scripts\python manage.py check`: نجح بعد المرحلة 8 بلا مشاكل.
- `.venv\Scripts\python manage.py test`: نجحت 67 اختباراً بعد المرحلة 8.
- `.venv\Scripts\python -m ruff check .`: نجح بعد المرحلة 8.
- `.venv\Scripts\python manage.py makemigrations --check --dry-run`: لم يجد تغييرات غير مولدة بعد المرحلة 8.
- فحص HTTP محلي: `/ar/` و`/ar/browse/` و`/ar/requests/new/` و`/ar/courses/1/` و`/health/` رجعت `200`، وصفحة `/ar/moderation/requests/` أعادت الزائر إلى تسجيل الدخول بـ`302`.

## ما لم يختبر ولماذا

- لم تشغل اختبارات تطبيق لأن المرحلة 0 لا تنشئ تطبيقاً أو كوداً تنفيذياً.
- لم يختبر اتصال PostgreSQL فعلي لأن Docker وpsql غير متاحين على الجهاز.
- لم تختبر Playwright أو لقطات الأجهزة لأن المرحلة 1 أنشأت أساس الصفحات فقط، وستأتي فحوص الواجهة التفصيلية في مرحلة لاحقة.
- لم تختبر Playwright أو لقطات الأجهزة بعد؛ صفحة التصفح اختبرت عبر Django client وHTTP فقط.
- لم تختبر المرحلة 3 على جهاز Android حقيقي أو اتصال ضعيف حقيقي.
- لم تشغل Playwright لعرض 320px و360px؛ التحقق الحالي آلي عبر اختبارات Django وHTTP وفحص CSS، مع تصميم responsive في CSS.
- لم يختبر إرسال بريد حقيقي للدعوات لأنه غير منفذ عمداً في المرحلة 4.
- لم يختبر MFA لأنه مؤجل.
- لم يختبر ClamAV أو antivirus فعلي لأنه غير مدمج بعد؛ الحالة تبقى `pending` ولا تصبح clean تلقائياً.
- لم يختبر worker أو Redis لفحص الملفات؛ نقطة الامتداد موجودة عبر حقول `scan_status` و`scan_notes`.
- لم يختبر Range على ملف PDF دراسي حقيقي كبير؛ الاختبار الحالي يستخدم ملفاً اصطناعياً صغيراً ذا توقيع PDF صحيح.
- لم يختبر التخزين الخاص على S3 أو تسليم Nginx داخلي؛ الاختبار المحلي يستخدم Django وfilesystem storage.
- لم يختبر multi-range؛ endpoint يدعم نطاق بايتات واحد ويرفض الطلب متعدد النطاقات بـ`416`.
- لم يختبر جهاز Android حقيقي أو Playwright بعد هذه المرحلة؛ الواجهة اختبرت عبر Django client فقط.
- لم يختبر enforcement كامل داخل كل مسارات Django admin؛ المسار المعتمد للمراجعة هو صفحة الإشراف وطرق النموذج، مع ضبط جزئي في admin عبر `clean()`.
- لم يختبر rate limit عبر عدة عمليات خادم أو cache مشتركة؛ الاختبار الحالي يستخدم Django LocMemCache.
- لم تختبر هوية الزائر خلف reverse proxy؛ يجب ضبط `REMOTE_ADDR` أو وسيط موثوق في بيئة الإنتاج قبل الاعتماد على الحد.
- لم تنفذ المفضلة أو مساحات الطالب والمساهم الأوسع الواردة في الدليل، لأن طلب المرحلة 8 الحالي حصر التنفيذ بنظام طلب الملفات الناقصة.

## الخطوة التالية

الخطوة التالية عند طلبك الصريح هي المرحلة 9 فقط. قبل الإنتاج ما زال يلزم اختبار PostgreSQL وClamAV/worker وcache مشتركة وتخزين/تسليم الملفات في بيئة staging، وتجربة المسارات على اتصال ضعيف وجهاز Android حقيقي.
