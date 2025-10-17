<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/d3234e5e-7a99-4aa2-a13e-830cb3f17eda" />

# CardForge

CardForge — это фреймворк для быстрого прототипирования и разработки карточных Telegram-ботов. Он предоставляет доменные сущности, хранилища, интеграцию с aiogram, административный инструментарий и утилиты для диагностики экономики.

## Возможности
- Декларативный JSON-формат каталогов (карты, изображения, паки, валюты).
- Модульная система карточек, паков, валют и мини-игр.
- Настраиваемые веса выпадения (по карте, пакам, редкостям) и стратегии обработки дубликатов.
- Административные сервисы: бан, выдача карт и валют, корректировка прогресса с настраиваемыми командами.
- Интеграция с aiogram: готовые роутеры, фильтры, клавиатуры и мини-игровые команды.
- Поддержка in-memory и SQLAlchemy-бэкендов (SQLite по умолчанию).
- Диагностика экономики: симулятор дропов и чек-лист баланса.
- Тестовые утилиты: фабрики, фикстуры pytest, тест-клиент.
- Готовые пользовательские команды: `/drop`, `/profile`, `/collection`, `/cooldown`, `/games`, административные `/ban`, `/grantcard` (или ваши кастомные).

## Структура проекта
```
cardforge/
  app.py               # Основной класс BotApp
  config.py            # Конфигурация фреймворка
  domain/              # Доменные модели и сервисы
  storage/             # Адаптеры хранилищ
  telegram/            # Интеграция с aiogram
  admin/               # Админ-команды и сервисы
  diagnostics/         # Диагностика экономики
  testing/             # Утилиты для тестирования
examples/
  basic_bot.py         # Пример регистрации бота
docs/
  en/                  # Documentation in English
    architecture.md
    getting_started.md
    development_guide.md
    core_reference.md
  ru/                  # Документация на русском языке
    architecture.md
    getting_started.md
    development_guide.md
    core_reference.md
```

## Быстрый старт
1. Установите зависимости:
   ```bash
   pip install -e .[dev]
   ```
2. Опишите карты и паки в JSON (`examples/catalog/cards.json`) или модуле.
3. Запустите симулятор экономики:
   ```bash
   cardforge-sim examples.basic_bot starters --pulls 500
   ```
4. Проверьте чек-лист баланса:
   ```bash
   cardforge-check examples.basic_bot
   ```
5. Подключите роутеры в вашем Telegram-боте на aiogram:
   ```python
   from aiogram import Bot, Dispatcher
   from pathlib import Path
   from cardforge import BotApp
   from cardforge.config import CardForgeConfig
   from cardforge.telegram import build_router
   from cardforge.loaders import load_catalog_from_json
   from cardforge.admin import build_admin_router

   app = BotApp(CardForgeConfig.from_env())
   load_catalog_from_json(app, Path("examples/catalog/cards.json"))

   bot = Bot(app.config.bot_token)
   dp = Dispatcher()
   dp.include_router(build_router(app, default_pack="starters"))
   dp.include_router(build_admin_router(app))
   ```

## Документация
- `docs/ru/getting_started.md` и `docs/en/getting_started.md` — пошаговая настройка и примеры конфигурации.
- `docs/ru/development_guide.md` и `docs/en/development_guide.md` — детальное руководство по разработке, тестам и стратегиям.
- `docs/ru/architecture.md` и `docs/en/architecture.md` — архитектурный обзор.
- `docs/ru/core_reference.md` и `docs/en/core_reference.md` — справочник по API и точкам расширения.

## Тестирование
- Запуск всех тестов:
  ```bash
  pytest
  ```
- Используйте фикстуру `memory_app` или `TestClient` из `cardforge.testing` для сценарного тестирования.

## Диагностика
- `cardforge-sim` — симуляция выпадения карт и сбор статистики.
- `cardforge-check` — автоматические проверки на предмет дисбаланса.
- `cardforge-validate --catalog <path>` — строгая проверка JSON-каталогов.
- `cardforge-validate --module <package.module>` — проверка готового приложения (сервисы, конфигурация).

## Планы развития
- Дополнительные транспортные адаптеры (например, Pyrogram).
- Набор готовых мини-игр и сценариев.
- Генерация дашбордов с метриками прогресса игроков.
