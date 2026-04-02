# Auto News Bot

Автоматический Telegram-бот для публикации автомобильных новостей в нейтральном новостном стиле.

Что умеет:

- забирает новости из RSS-лент;
- переводит мировые авто-новости на русский язык перед публикацией;
- отфильтровывает обзоры, тест-драйвы, рейтинги и явно не-новостной контент;
- удаляет дубли по ссылкам и похожим заголовкам;
- ранжирует новости по теме, свежести и числу совпавших источников;
- старается чередовать темы и издания, чтобы лента не состояла из одинаковых `recall`-новостей;
- оформляет посты для Telegram с жирными заголовками, курсивом, эмодзи, ссылкой и скрытым блоком с оригиналом;
- для новинок и авто-гаджетов добавляет в пост отдельный блок с характеристиками, если они есть в источнике;
- если в одном материале несколько моделей, бот раскладывает характеристики по моделям, а цену выносит в конец поста;
- умеет отправлять не только одно фото, но и небольшую карусель, если на странице новости найдено несколько изображений;
- публикует посты в Telegram-канал без ручного подтверждения;
- хранит историю в SQLite, чтобы не повторять уже опубликованное;
- умеет работать в `dry-run`, чтобы сначала посмотреть результат без публикации.

## Структура

- `main.py` — точка входа и цикл планировщика.
- `news_bot/config.py` — загрузка конфигурации.
- `news_bot/feeds.py` — получение и разбор RSS/Atom.
- `news_bot/ranking.py` — фильтрация, дедупликация и оценка важности.
- `news_bot/formatter.py` — нейтральный текст постов.
- `news_bot/translation.py` — перевод мировых новостей на русский.
- `news_bot/storage.py` — SQLite-хранилище.
- `news_bot/telegram_api.py` — отправка в Telegram.
- `config.example.json` — шаблон конфига.

## Быстрый старт

1. Скопируйте `config.example.json` в `config.json`.
2. Укажите:
   - `bot_token`
   - `channel_id`
   - нужные RSS-ленты
3. Запустите проверку без публикации:

```bash
python3 main.py --config config.json --once --dry-run
```

4. Если результат устраивает, запустите обычный режим:

```bash
python3 main.py --config config.json
```

Для локальной демонстрации без внешнего RSS и без публикации есть готовый конфиг:

```bash
python3 main.py --config config.sample.local.json --once --dry-run --verbose
```

## GitHub Actions 24/7

Если нужно, чтобы бот работал бесплатно, когда ноутбук выключен, можно запускать его через GitHub Actions.

Что уже добавлено в проект:

- workflow: `.github/workflows/auto-news-bot.yml`
- сборка безопасного CI-конфига: `scripts/build_ci_config.py`
- отдельное хранилище состояния: `state/news.db`

Что нужно сделать на GitHub:

1. Создать репозиторий и загрузить туда проект.
2. В `Settings -> Secrets and variables -> Actions` добавить секреты:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHANNEL_ID`
3. При желании добавить переменную:
   - `AUTO_NEWS_PUBLICATION_TITLE`
4. В `Settings -> Actions -> General` включить для `GITHUB_TOKEN` режим `Read and write permissions`, чтобы workflow мог сохранять `state/news.db`.
5. Открыть вкладку `Actions` и вручную запустить workflow `Auto News Bot` один раз.

Как это работает:

- workflow запускается каждые 30 минут;
- бот публикует новости в Telegram;
- база уже опубликованных новостей сохраняется в `auto_news_bot/state/news.db`;
- после публикации workflow коммитит обновленное состояние обратно в репозиторий, чтобы не было дублей между запусками.

Важные ограничения GitHub:

- по официальной документации минимальный интервал расписания — 5 минут;
- в публичных репозиториях scheduled workflows могут быть автоматически отключены после 60 дней без активности репозитория;
- GitHub Actions бесплатен для стандартных раннеров в public-репозиториях, а для private-репозиториев GitHub Free включает 2,000 минут в месяц.

## Настройка Telegram

1. Создайте бота через `@BotFather`.
2. Получите токен и впишите его в `bot_token`.
3. Добавьте бота администратором в ваш канал.
4. В `channel_id` укажите:
   - публичный канал: `@my_channel_name`
   - приватный канал: id вида `-1001234567890`

## Как выбрать стиль без оценочности

Бот специально:

- не публикует обзоры, мнения, подборки и сравнения;
- убирает восклицания, вопросительные заголовки и часть кликбейтных формулировок;
- оформляет пост как короткое нейтральное сообщение по схеме:
  - тема;
  - факт;
  - краткая суть;
  - источник.

При этом для Telegram включено богатое форматирование через `parse_mode: HTML`, потому что так надежнее работают:

- жирный заголовок;
- курсив для лида;
- ссылка `Читать полностью`;
- `tg-spoiler` для скрытого оригинала;
- эмодзи и хэштеги без сложного экранирования.

Если в исходной ленте сам заголовок очень эмоциональный, бот попытается его сгладить, но на 100% убрать редакционную окраску у всех внешних источников невозможно. Для максимально ровного стиля лучше использовать деловые или нейтральные RSS-источники.

## Мировые новости на русском

По умолчанию бот поддерживает смешанный поток:

- русскоязычные авто-источники;
- англоязычные мировые авто-источники с автоматическим переводом на русский.

В текущем шаблоне это настраивается через блок `translation` и список `sources`.

Сейчас базовый поток уже можно держать сбалансированным по регионам:

- СНГ и русскоязычная повестка: `Drom`, `Motor.ru`;
- Европа: `Autocar`, `BMW Group`;
- глобальные англоязычные авто-СМИ: `Motor1`, `InsideEVs`, `Motor Authority`, `The Car Connection`, `Green Car Reports`;
- официальные newsroom-источники брендов: `BMW Group`, `Hyundai`.

Редакционный профиль канала можно держать таким:

- новые автомобили и премьеры;
- посты с ценами и ценовыми анонсами;
- ДТП и аварии по всему миру;
- автогаджеты: навигаторы, мультимедиа, `CarPlay`, `Android Auto`, видеорегистраторы;
- авто-технологии: роботакси, ADAS, цифровые кокпиты, ПО для машин;
- полезные лайфхаки и советы по эксплуатации;
- техно-материалы по мототехнике, если это именно гаджеты, электроника, навигация или обслуживание.

## Медиа в постах

Бот теперь старается публиковать только новости с медиа:

- если у новости найдено видео, в Telegram отправляется видео;
- если видео нет, бот берет фото;
- если у материала нет ни видео, ни фото, новость пропускается.

## Как сделать ленту разнообразнее

В конфиг добавлен блок `diversity`:

- `max_per_publisher` ограничивает число постов от одного издания за цикл;
- `max_per_topic` не дает одной теме занять весь цикл публикации;
- `topic_limits` позволяет жестко ограничить отдельные темы, например `recalls`.

У источника можно задать поле `group`, если у одного медиа несколько RSS-лент. Это помогает считать их одним изданием при диверсификации.

## Пример запуска по расписанию на macOS

Есть готовый шаблон `launchd`:

- `launchd/com.playground.auto-news-bot.plist.example`

После настройки путей его можно положить в `~/Library/LaunchAgents/` и включить командой:

```bash
launchctl load ~/Library/LaunchAgents/com.playground.auto-news-bot.plist
```

## Проверка

Синтаксис:

```bash
python3 -m py_compile main.py news_bot/*.py
```

Разовый прогон:

```bash
python3 main.py --config config.json --once --dry-run
```

## Подсказки по источникам

В шаблоне уже есть один подтвержденный официальный RSS-источник:

- Drom.ru RSS export: [https://www.drom.ru/export/](https://www.drom.ru/export/)

Из подтвержденных официальных англоязычных авто-RSS можно добавить:

- Motor.ru RSS: [https://motor.ru/exports/rss](https://motor.ru/exports/rss)
- Motor1 RSS: [https://www.motor1.com/rss/](https://www.motor1.com/rss/)
- Motor Authority RSS: [https://www.motorauthority.com/rss-feeds](https://www.motorauthority.com/rss-feeds)
- InsideEVs RSS: [https://insideevs.com/rss/](https://insideevs.com/rss/)
- The Car Connection RSS: [https://www.thecarconnection.com/rss](https://www.thecarconnection.com/rss)
- Green Car Reports RSS: [https://www.greencarreports.com/news/rss-feed](https://www.greencarreports.com/news/rss-feed)
- Autocar RSS: [https://www.autocar.co.uk/rss](https://www.autocar.co.uk/rss)
- BMW Group PressClub RSS: [https://www.press.bmwgroup.com/global/info/rss](https://www.press.bmwgroup.com/global/info/rss)
- Hyundai Newsroom RSS: [https://www.hyundai.com/worldwide/en/newsroom](https://www.hyundai.com/worldwide/en/newsroom)

Источники проверены по их официальным страницам RSS:

- Drom.ru export page: [https://www.drom.ru/export/](https://www.drom.ru/export/)
- Motor.ru main page with RSS link in footer: [https://motor.ru/](https://motor.ru/)
- Motor1 RSS page: [https://www.motor1.com/rss/](https://www.motor1.com/rss/)
- Motor Authority RSS page: [https://www.motorauthority.com/rss-feeds](https://www.motorauthority.com/rss-feeds)
- InsideEVs RSS page: [https://insideevs.com/rss/](https://insideevs.com/rss/)
- The Car Connection RSS page: [https://www.thecarconnection.com/rss](https://www.thecarconnection.com/rss)
- Green Car Reports RSS page: [https://www.greencarreports.com/news/rss-feed](https://www.greencarreports.com/news/rss-feed)
- Autocar RSS feed: [https://www.autocar.co.uk/rss](https://www.autocar.co.uk/rss)
- BMW Group RSS page: [https://www.press.bmwgroup.com/global/info/rss](https://www.press.bmwgroup.com/global/info/rss)
- Hyundai Newsroom RSS page: [https://www.hyundai.com/worldwide/en/newsroom](https://www.hyundai.com/worldwide/en/newsroom)
